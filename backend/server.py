"""
Ascendra Academy backend (web edition).
- JWT auth (email/password) + Google OAuth (Emergent session)
- Curriculum (paths / modules / lessons / models)
- Progress tracking (streak, XP, completed lessons, level, certificates)
- AI Tutor chat (Claude Sonnet 4.5 via emergentintegrations)
- Stripe checkout + webhook for tier upgrades (sandbox + real Stripe)
- Admin endpoints (stats, users, sales, traffic)
"""
import os
import asyncio
import logging
import uuid
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Literal, Dict

import bcrypt
import httpx
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks
from fastapi.responses import Response, PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest,
)

from curriculum_db import (
    ensure_seeded as _curric_ensure_seeded,
    list_paths as _curric_list_paths,
    list_paths_by_creator as _curric_list_paths_by_creator,
    list_paths_pending_review as _curric_list_paths_pending_review,
    get_path as _curric_get_path,
    get_lesson as _curric_get_lesson,
    path_summary,
    can_access,
    create_path as _curric_create_path,
    update_path as _curric_update_path,
    delete_path as _curric_delete_path,
    add_module as _curric_add_module,
    update_module as _curric_update_module,
    delete_module as _curric_delete_module,
    add_lesson as _curric_add_lesson,
    update_lesson as _curric_update_lesson,
    delete_lesson as _curric_delete_lesson,
)
from curriculum import AI_MODELS
import ai_studio
import path_generator
import seo_studio
import auto_content
import lifecycle
import social_studio
import x_publisher
import meta_publisher
import tiktok_publisher
import social_media_signer
import practice_lab
import content_scanner
import revenue as revenue_mod
import revenue_phase2 as revenue_phase2_mod

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ─── Config ─────────────────────────────────────────────────────────────────
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "ascendra_db")
JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "ascendra-dev-secret")
JWT_ALGO = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXP_DAYS = 30
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# ─── Internal account exclusion (admin analytics) ───────────────────────────
# Admin dashboard metrics must reflect REAL customers + REAL leads only.
# Excluded from /api/admin/stats, /admin/users (default), /admin/sales,
# /admin/subscribers:
#   - Internal seed accounts: sage1@…, sage2@…, …, sage9@ascendraacademy.com
#   - Admin operator accounts: admin@ascendraacademy.com (and any is_admin=True)
#   - Automated test artifacts:
#       • webhook_test_*@test.ascendra.com (Stripe webhook QA — appears as fake paid subs)
#       • Any address @test.ascendra.com (whole QA subdomain)
#       • e2e_*@ascendraacademy.com  (E2E automation runs)
#       • smoke_*@ascendraacademy.com  (smoke tests)
#       • final_*@ascendraacademy.com  (release-gate tests)
# Free-tier REAL users (real emails) ARE still counted — they are marketing
# leads we convert via lifecycle emails.
TEST_EMAIL_REGEX = (
    r"^(?:"
    r"sage[0-9]+|"                       # sage1@... sage9@... (internal seeds)
    r"admin|"                             # admin@... (admin operator)
    r"e2e_[0-9a-z]+|"                    # e2e_*@... (automated end-to-end tests)
    r"smoke_[0-9a-z]+|"                  # smoke_*@... (smoke tests)
    r"final_[0-9a-z]+"                   # final_*@... (release-gate tests)
    r")@ascendraacademy\.com$"
    r"|.+@test\.ascendra\.com$"          # entire QA subdomain (e.g. webhook_test_*)
)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
users_col = db["users"]
progress_col = db["progress"]
chats_col = db["chats"]
sessions_col = db["payment_sessions"]
certs_col = db["certificates"]
pageviews_col = db["pageviews"]
password_reset_col = db["password_resets"]

# ─── App ────────────────────────────────────────────────────────────────────
app = FastAPI(title="Ascendra API")
api = APIRouter(prefix="/api")
bearer_scheme = HTTPBearer(auto_error=False)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ascendra")

# ─── Pydantic Models ────────────────────────────────────────────────────────
class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: Optional[str] = None
    goal: Optional[str] = None  # career | business | creator | productivity

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class GoogleSessionIn(BaseModel):
    session_token: str
    goal: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    goal: Optional[str] = None
    tier: str = "free"
    subscription_interval: Optional[str] = None
    tier_expires_at: Optional[datetime] = None
    created_at: datetime
    has_used_trial: bool = False
    quiz_answers: Optional[dict] = None
    recommended_path_id: Optional[str] = None
    is_admin: bool = False
    must_change_password: bool = False
    picture: Optional[str] = None

class ChangePasswordIn(BaseModel):
    current_password: Optional[str] = None
    new_password: str = Field(min_length=6)

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=6)

class AdminUserPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    tier: Optional[str] = None
    subscription_interval: Optional[str] = None
    tier_expires_at: Optional[datetime] = None
    is_admin: Optional[bool] = None
    must_change_password: Optional[bool] = None
    new_password: Optional[str] = None

class PageviewIn(BaseModel):
    path: str
    referrer: Optional[str] = None

class ProgressOut(BaseModel):
    completed_lesson_ids: List[str] = []
    total_xp: int = 0
    streak_days: int = 0
    last_active_date: Optional[str] = None
    level: int = 1
    level_progress_pct: int = 0
    xp_to_next_level: int = 0
    completed_paths: List[str] = []
    path_progress: dict = {}

class CompleteLessonIn(BaseModel):
    lesson_id: str

class CompleteLessonOut(BaseModel):
    progress: ProgressOut
    awarded_xp: int = 0
    newly_completed_paths: List[str] = []
    certificates_issued: List[str] = []
    streak_milestone: Optional[int] = None  # set if user hit 3/7/14/30/60/100 day streak

class QuizAnswers(BaseModel):
    goal: Optional[str] = None
    experience: Optional[str] = None
    time_per_day: Optional[str] = None
    focus: Optional[str] = None

class ChatIn(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatOut(BaseModel):
    session_id: str
    reply: str

class CheckoutIn(BaseModel):
    tier: Literal["ascender", "pathfinder", "sage", "business"]
    interval: Literal["monthly", "annual", "trial"] = "monthly"
    origin_url: str

# ─── Auth helpers ───────────────────────────────────────────────────────────
def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_pw(pw: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), h.encode())
    except Exception:
        return False

def make_token(uid: str) -> str:
    return jwt.encode(
        {"sub": uid, "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DAYS)},
        JWT_SECRET,
        algorithm=JWT_ALGO,
    )

async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        uid = payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    user = await users_col.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user


async def optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[dict]:
    """Like current_user but returns None for missing/invalid tokens instead of 401.
    Use on public endpoints that want to personalize when authenticated.
    """
    if not creds:
        return None
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        uid = payload.get("sub")
    except Exception:
        return None
    if not uid:
        return None
    user = await users_col.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    return user or None

def serialize_user(u: dict) -> dict:
    return {
        "id": u["id"],
        "email": u["email"],
        "name": u.get("name"),
        "goal": u.get("goal"),
        "tier": u.get("tier", "free"),
        "subscription_interval": u.get("subscription_interval"),
        "tier_expires_at": u.get("tier_expires_at"),
        "created_at": u["created_at"],
        "has_used_trial": bool(u.get("has_used_trial", False)),
        "quiz_answers": u.get("quiz_answers"),
        "recommended_path_id": u.get("recommended_path_id"),
        "is_admin": bool(u.get("is_admin", False)),
        "must_change_password": bool(u.get("must_change_password", False)),
        "picture": u.get("picture"),
    }


async def require_admin(user=Depends(current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")
    return user


async def auto_downgrade_if_expired(user: dict) -> dict:
    """Downgrade users whose paid subscription has lapsed."""
    if user.get("tier", "free") == "free":
        return user
    exp = user.get("tier_expires_at")
    if exp is not None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            await users_col.update_one(
                {"id": user["id"]},
                {"$set": {"tier": "free", "subscription_interval": None}},
            )
            user["tier"] = "free"
            user["subscription_interval"] = None
    return user

# ─── Progress / Level / Certificate helpers ─────────────────────────────────
def compute_level(total_xp: int) -> dict:
    """100 * n * (n-1) = floor xp for level n."""
    import math
    if total_xp < 0:
        total_xp = 0
    n = int((1 + math.sqrt(1 + total_xp / 25)) / 2)
    if n < 1:
        n = 1
    floor_xp = 100 * n * (n - 1)
    next_xp = 100 * (n + 1) * n
    span = next_xp - floor_xp
    in_level = total_xp - floor_xp
    pct = int((in_level / span) * 100) if span > 0 else 0
    return {"level": n, "level_progress_pct": max(0, min(100, pct)), "xp_to_next_level": max(0, next_xp - total_xp)}


def _path_lesson_index_sync(paths_list: list) -> dict:
    idx = {}
    for p in paths_list:
        ids = []
        for m in p.get("modules", []):
            for lsn in m.get("lessons", []):
                ids.append(lsn["id"])
        idx[p["id"]] = ids
    return idx


async def _path_lesson_index() -> dict:
    paths = await _curric_list_paths(db)
    return _path_lesson_index_sync(paths)


async def _compute_path_progress(completed_ids: list) -> tuple[dict, list]:
    completed_set = set(completed_ids)
    path_progress = {}
    completed_paths = []
    idx = await _path_lesson_index()
    for pid, lids in idx.items():
        total = len(lids)
        done = sum(1 for x in lids if x in completed_set)
        pct = int((done / total) * 100) if total else 0
        path_progress[pid] = {"completed": done, "total": total, "pct": pct}
        if total > 0 and done == total:
            completed_paths.append(pid)
    return path_progress, completed_paths


async def get_progress(user_id: str) -> dict:
    p = await progress_col.find_one({"user_id": user_id}, {"_id": 0})
    if not p:
        p = {
            "user_id": user_id,
            "completed_lesson_ids": [],
            "total_xp": 0,
            "streak_days": 0,
            "last_active_date": None,
        }
        await progress_col.insert_one(dict(p))
        p.pop("_id", None)
    return p


def _build_progress_out(p: dict, path_progress: dict, completed_paths: list) -> ProgressOut:
    lvl = compute_level(p.get("total_xp", 0))
    return ProgressOut(
        completed_lesson_ids=p.get("completed_lesson_ids", []),
        total_xp=p.get("total_xp", 0),
        streak_days=p.get("streak_days", 0),
        last_active_date=p.get("last_active_date"),
        level=lvl["level"],
        level_progress_pct=lvl["level_progress_pct"],
        xp_to_next_level=lvl["xp_to_next_level"],
        completed_paths=completed_paths,
        path_progress=path_progress,
    )


async def _build_progress_out_async(p: dict) -> ProgressOut:
    path_progress, completed_paths = await _compute_path_progress(p.get("completed_lesson_ids", []))
    return _build_progress_out(p, path_progress, completed_paths)


def _recommend_path(answers: dict) -> str:
    goal = (answers.get("goal") or "").lower()
    exp = (answers.get("experience") or "").lower()
    focus = (answers.get("focus") or "").lower()
    if exp == "beginner":
        return "fundamentals"
    focus_map = {
        "image": "creators",
        "video": "creators",
        "voice": "creators",
        "code": "code-with-ai",
        "agents": "automation",
        "text": "prompt-mastery",
    }
    if focus in focus_map:
        return focus_map[focus]
    goal_map = {
        "business": "business",
        "creator": "creators",
        "productivity": "productivity",
        "career": "prompt-mastery",
    }
    return goal_map.get(goal, "fundamentals")


async def _issue_certificate_if_complete(user: dict, path_id: str) -> Optional[dict]:
    existing = await certs_col.find_one({"user_id": user["id"], "path_id": path_id}, {"_id": 0})
    if existing:
        return None
    p = await _curric_get_path(db, path_id)
    if not p:
        return None
    # Layer 2 · Capstone gating: if this path has any capstones (challenges of
    # task_type="capstone"), the user must have mastered ALL of them before the
    # certificate is issued.
    capstones = []
    async for c in db.practice_challenges.find({"path_id": path_id, "task_type": "capstone"}):
        capstones.append(c)
    if capstones:
        capstone_ids = [c["id"] for c in capstones]
        mastered = await db.practice_attempts.count_documents({
            "user_id": user["id"],
            "challenge_id": {"$in": capstone_ids},
            "mastered": True,
        })
        # Every capstone must have at least one mastered attempt
        mastered_ids = await db.practice_attempts.distinct(
            "challenge_id",
            {"user_id": user["id"], "challenge_id": {"$in": capstone_ids}, "mastered": True},
        )
        missing = [cid for cid in capstone_ids if cid not in mastered_ids]
        if missing:
            return None  # Not yet — capstones still pending
    serial = f"ASC-{path_id[:4].upper()}-{uuid.uuid4().hex[:6].upper()}"
    cert = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_name": user.get("name") or user["email"].split("@")[0],
        "path_id": path_id,
        "path_title": p["title"],
        "path_color": p["color"],
        "issued_at": datetime.now(timezone.utc),
        "serial": serial,
        "capstones_passed": len(capstones) if capstones else 0,
    }
    await certs_col.insert_one(dict(cert))
    return cert

# ─── Auth routes ────────────────────────────────────────────────────────────
@api.post("/auth/signup", response_model=Token)
async def signup(body: SignupIn):
    email_lower = body.email.lower()
    existing = await users_col.find_one({"email": email_lower})
    if existing:
        raise HTTPException(400, "Email already registered")
    user = {
        "id": str(uuid.uuid4()),
        "email": email_lower,
        "name": body.name or email_lower.split("@")[0],
        "goal": body.goal,
        "tier": "free",
        "password_hash": hash_pw(body.password),
        "created_at": datetime.now(timezone.utc),
    }
    # Auto-attach pre-signup quiz answers if this email took the anonymous quiz
    try:
        lead = await db["onboarding_leads"].find_one(
            {"email": email_lower, "consumed": {"$ne": True}},
            sort=[("created_at", -1)],
        )
        if lead:
            user["onboarding_answers"] = lead.get("answers", {})
            user["onboarded_at"] = datetime.now(timezone.utc).isoformat()
            if lead.get("plan"):
                user["onboarding_plan"] = lead["plan"]
                user["recommended_path_id"] = (lead["plan"].get("recommended_path_ids") or [None])[0]
    except Exception as e:
        log.warning(f"signup: lead attach failed for {email_lower}: {e}")
    await users_col.insert_one(user)
    # Mark the lead as consumed so we don't double-attach if signup happens twice
    try:
        if user.get("onboarding_answers"):
            await db["onboarding_leads"].update_many(
                {"email": email_lower},
                {"$set": {"consumed": True, "consumed_user_id": user["id"], "consumed_at": datetime.now(timezone.utc)}},
            )
            # Also seed daily goal from plan
            plan = user.get("onboarding_plan") or {}
            if plan.get("daily_goal_target"):
                await progress_col.update_one(
                    {"user_id": user["id"]},
                    {"$set": {"daily_goal_target": int(plan["daily_goal_target"])}},
                    upsert=True,
                )
    except Exception as e:
        log.warning(f"signup: lead consume failed: {e}")
    return Token(access_token=make_token(user["id"]))

@api.post("/auth/login", response_model=Token)
async def login(body: LoginIn):
    user = await users_col.find_one({"email": body.email.lower()})
    if not user or "password_hash" not in user or not user.get("password_hash") or not verify_pw(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    return Token(access_token=make_token(user["id"]))

@api.post("/auth/google", response_model=Token)
async def auth_google(body: GoogleSessionIn):
    """Exchange an Emergent-managed Google session_token for our own JWT."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            r = await http.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": body.session_token},
            )
        if r.status_code != 200:
            raise HTTPException(401, "Invalid Google session")
        data = r.json()
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Google session-data fetch failed")
        raise HTTPException(502, f"Google verify failed: {str(e)[:120]}")

    email = (data.get("email") or "").lower()
    if not email:
        raise HTTPException(400, "Google account missing email")

    user = await users_col.find_one({"email": email})
    if not user:
        user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "name": data.get("name") or email.split("@")[0],
            "picture": data.get("picture"),
            "google_id": data.get("id"),
            "goal": body.goal,
            "tier": "free",
            "password_hash": None,
            "created_at": datetime.now(timezone.utc),
            "provider": "google",
        }
        await users_col.insert_one(dict(user))
    else:
        updates = {}
        if not user.get("google_id"):
            updates["google_id"] = data.get("id")
        if data.get("picture") and not user.get("picture"):
            updates["picture"] = data.get("picture")
        if updates:
            await users_col.update_one({"id": user["id"]}, {"$set": updates})

    return Token(access_token=make_token(user["id"]))

@api.get("/auth/me", response_model=UserOut)
async def me(user=Depends(current_user)):
    user = await auto_downgrade_if_expired(user)
    return serialize_user(user)

# ─── Curriculum routes ──────────────────────────────────────────────────────
@api.get("/paths")
async def list_paths(user=Depends(optional_user)):
    """Public list of paths. If authenticated, also includes the user's own
    private/pending/rejected user-generated paths so they can see their drafts.
    """
    viewer_id = (user or {}).get("id") if user else None
    is_admin_viewer = bool((user or {}).get("is_admin"))
    paths = await _curric_list_paths(
        db, viewer_id=viewer_id, is_admin=is_admin_viewer,
    )
    return {"paths": [path_summary(p) for p in paths]}


@api.get("/paths/mine")
async def list_my_paths(user=Depends(current_user)):
    """List every path the current user has created (any status)."""
    paths = await _curric_list_paths_by_creator(db, user["id"])
    return {"paths": [path_summary(p) for p in paths]}


class PathGenerateIn(BaseModel):
    goal: str
    # If True, also fills lesson content in the background. Otherwise the path
    # is created with just lesson titles + scaffolding (faster, ~10s).
    fill_lessons: bool = True


@api.post("/paths/generate")
async def generate_user_path(body: PathGenerateIn, background_tasks: BackgroundTasks,
                              user=Depends(current_user)):
    """Paid users generate a custom learning path from a free-text goal.

    Stage 1 (sync, ~10-20s): Claude builds the path outline (title + 3 levels
    × 5-7 lesson titles). Path is saved with visibility=pending_review.
    Stage 2 (background, ~60-120s): every lesson's body + cards are generated
    by Claude in a controlled-concurrency loop. Front-end polls the path
    detail to watch lessons fill in.
    """
    if user.get("tier", "free") == "free":
        raise HTTPException(
            402,
            "Custom path generation is a paid feature. Upgrade to Ascender to create your own learning paths.",
        )
    goal = (body.goal or "").strip()
    if len(goal) < 8:
        raise HTTPException(400, "Tell us a bit more about your goal (at least 8 characters).")
    if len(goal) > 2000:
        raise HTTPException(400, "Goal is too long (max 2000 chars).")
    # Rate-limit: 1 path generation per user per 5 minutes (anti-abuse)
    five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    recent = await db["curriculum_paths"].count_documents({
        "created_by": user["id"],
        "created_at": {"$gte": five_min_ago},
    })
    if recent > 0:
        raise HTTPException(429, "You just generated a path. Please wait ~5 minutes before generating another.")

    try:
        outline = await path_generator.generate_user_path_outline(goal)
    except Exception as e:
        log.exception("user path outline generation failed")
        raise HTTPException(502, f"Couldn't draft your path: {str(e)[:200]}")
    # Persist with pending review status
    outline["source"] = "user-generated"
    outline["visibility"] = "pending_review"
    outline["admin_review_status"] = "pending"
    outline["is_user_generated"] = True
    outline["created_by"] = user["id"]
    outline["creator_email"] = user.get("email")
    outline["tier"] = user.get("tier", "free")   # creator can take it; admin may re-tier on approve
    outline["goal_prompt"] = goal[:2000]
    created = await _curric_create_path(db, outline)

    # Notify admin in background (email digest is daily, so just persist a flag).
    background_tasks.add_task(_notify_admin_new_user_path, created)

    # Optionally fill lessons in background
    if body.fill_lessons:
        background_tasks.add_task(
            path_generator.fill_path_lessons, db, created["id"],
            concurrency=2,
            path_title=created["title"],
            path_tagline=created.get("tagline", ""),
        )
        # And follow up with interactive-card generation
        background_tasks.add_task(_interactivize_path_lessons_after_fill, created["id"])

    return {
        "ok": True,
        "path": path_summary(created),
        "fill_status": "queued" if body.fill_lessons else "skipped",
    }


async def _notify_admin_new_user_path(path: dict) -> None:
    """Record an admin notification + best-effort email."""
    try:
        await db["admin_notifications"].insert_one({
            "id": str(uuid.uuid4()),
            "kind": "user_path_submitted",
            "path_id": path["id"],
            "path_title": path.get("title"),
            "creator_id": path.get("created_by"),
            "creator_email": path.get("creator_email"),
            "created_at": datetime.now(timezone.utc),
            "read": False,
        })
    except Exception as e:
        log.warning(f"admin notif insert failed: {e}")
    # Best-effort: include in next daily digest. We do NOT spam admin email
    # per submission to keep inbox sane.


async def _interactivize_path_lessons_after_fill(path_id: str) -> None:
    """After lesson content is filled, upgrade each lesson with interactive cards.
    Best-effort, sequential, swallows errors per-lesson."""
    try:
        # Small delay to let fill_path_lessons make progress first
        await asyncio.sleep(15)
        p = await db["curriculum_paths"].find_one({"id": path_id}, {"_id": 0})
        if not p:
            return
        for m in p.get("modules", []):
            for lsn in m.get("lessons", []):
                if not lsn.get("cards"):
                    continue
                if int(lsn.get("interactive_v") or 0) >= 1:
                    continue
                try:
                    await auto_content._interactivize_one(
                        db, lsn["id"], path_id=path_id, module_id=m["id"]
                    )
                except Exception as e:
                    log.warning(f"interactivize lesson {lsn['id']} failed: {e}")
    except Exception as e:
        log.warning(f"_interactivize_path_lessons_after_fill error: {e}")

@api.get("/paths/{path_id}")
async def get_path_detail(path_id: str, user=Depends(optional_user)):
    p = await _curric_get_path(db, path_id)
    if not p:
        raise HTTPException(404, "Path not found")
    # Restrict access to private user-generated paths: only creator + admin can view detail
    visibility = p.get("visibility", "public")
    if visibility in ("private", "pending_review", "rejected") and not p.get("admin_review_status") == "approved":
        if not user:
            raise HTTPException(404, "Path not found")
        if user.get("id") != p.get("created_by") and not user.get("is_admin"):
            raise HTTPException(404, "Path not found")
    modules = []
    for m in p["modules"]:
        lessons = []
        for lsn in m.get("lessons", []):
            lessons.append({
                "id": lsn["id"],
                "title": lsn["title"],
                "duration_min": lsn.get("duration_min", 5),
                "xp": lsn.get("xp", 50),
                "card_count": len(lsn.get("cards", [])),
                "interactive_v": lsn.get("interactive_v", 0),
            })
        modules.append({
            "id": m["id"],
            "title": m["title"],
            "level": m.get("level"),
            "lessons": lessons,
        })
    return {
        "id": p["id"],
        "title": p["title"],
        "subtitle": p.get("subtitle", ""),
        "tagline": p.get("tagline", ""),
        "color": p.get("color", "#FFB000"),
        "level": p.get("level", "Beginner"),
        "duration": p.get("duration", ""),
        "image": p.get("image", ""),
        "tier": p.get("tier", "free"),
        "modules": modules,
        "visibility": visibility,
        "is_user_generated": bool(p.get("is_user_generated", False)),
        "created_by": p.get("created_by"),
        "creator_email": p.get("creator_email"),
        "admin_review_status": p.get("admin_review_status", "approved"),
        "admin_review_notes": p.get("admin_review_notes"),
    }

@api.get("/lessons/{lesson_id}")
async def fetch_lesson(lesson_id: str, user=Depends(current_user)):
    lsn = await _curric_get_lesson(db, lesson_id)
    if not lsn:
        raise HTTPException(404, "Lesson not found")
    p = await _curric_get_path(db, lsn["path_id"])
    # Admins bypass the tier gate so they can review/QA every lesson regardless
    # of which paid tier the path is locked behind.
    if p and not user.get("is_admin") and not can_access(user.get("tier", "free"), p.get("tier", "free")):
        raise HTTPException(403, f"This lesson requires {p['tier'].upper()} tier. Upgrade to unlock.")
    return lsn

@api.get("/models")
async def list_models():
    return {"models": AI_MODELS}

# ─── Progress routes ────────────────────────────────────────────────────────
@api.get("/progress", response_model=ProgressOut)
async def progress(user=Depends(current_user)):
    p = await get_progress(user["id"])
    return await _build_progress_out_async(p)

@api.post("/progress/complete", response_model=CompleteLessonOut)
async def complete_lesson(body: CompleteLessonIn, user=Depends(current_user)):
    lesson = await _curric_get_lesson(db, body.lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    p = await get_progress(user["id"])
    today = datetime.now(timezone.utc).date().isoformat()

    awarded_xp = 0
    prev_pp, prev_completed_paths = await _compute_path_progress(p["completed_lesson_ids"])
    prev_completed_set = set(prev_completed_paths)

    if body.lesson_id not in p["completed_lesson_ids"]:
        p["completed_lesson_ids"].append(body.lesson_id)
        p["total_xp"] += lesson.get("xp", 50)
        awarded_xp = lesson.get("xp", 50)

    last = p.get("last_active_date")
    streak_milestone = None
    if last != today:
        yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        if last == yesterday:
            p["streak_days"] = p.get("streak_days", 0) + 1
        else:
            p["streak_days"] = 1
        p["last_active_date"] = today
        # Track longest streak
        if p["streak_days"] > p.get("longest_streak", 0):
            p["longest_streak"] = p["streak_days"]
        # Append today to activity calendar (kept as sorted, deduped ISO date list, last 365 days)
        cal = p.get("activity_calendar") or []
        if today not in cal:
            cal.append(today)
        # Trim to last 365 entries
        if len(cal) > 365:
            cal = sorted(cal)[-365:]
        p["activity_calendar"] = cal
        # Streak milestone detection
        if p["streak_days"] in (3, 7, 14, 30, 60, 100):
            streak_milestone = p["streak_days"]

    await progress_col.update_one(
        {"user_id": user["id"]},
        {"$set": {
            "completed_lesson_ids": p["completed_lesson_ids"],
            "total_xp": p["total_xp"],
            "streak_days": p["streak_days"],
            "last_active_date": p["last_active_date"],
            "longest_streak": p.get("longest_streak", p["streak_days"]),
            "activity_calendar": p.get("activity_calendar", [today]),
        }},
    )

    new_pp, now_completed_paths = await _compute_path_progress(p["completed_lesson_ids"])
    new_completed_paths = set(now_completed_paths) - prev_completed_set
    issued_ids: list = []
    for pid in new_completed_paths:
        cert = await _issue_certificate_if_complete(user, pid)
        if cert:
            issued_ids.append(cert["id"])

    return CompleteLessonOut(
        progress=_build_progress_out(p, new_pp, now_completed_paths),
        awarded_xp=awarded_xp,
        newly_completed_paths=list(new_completed_paths),
        certificates_issued=issued_ids,
        streak_milestone=streak_milestone,
    )


# ─── Streak / Daily goal ─────────────────────────────────────────────────
class StreakOut(BaseModel):
    current_streak: int
    longest_streak: int
    last_active_date: Optional[str]
    today: str
    activity_calendar: List[str]   # ISO dates user completed a lesson on
    daily_goal_target: int
    daily_goal_done: int
    daily_goal_complete: bool
    next_milestone: Optional[int]
    days_to_next_milestone: Optional[int]


MILESTONES = [3, 7, 14, 30, 60, 100, 365]


@api.get("/streak/me", response_model=StreakOut)
async def get_my_streak(user=Depends(current_user)):
    p = await get_progress(user["id"])
    today_iso = datetime.now(timezone.utc).date().isoformat()
    yesterday_iso = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    last = p.get("last_active_date")
    # If the user hasn't completed a lesson today AND not yesterday, their streak should display
    # as broken (the *stored* value is updated lazily on next completion, but we don't want to
    # show a stale current_streak when it's already been more than a day since their last activity).
    raw_current = int(p.get("streak_days") or 0)
    if last and last not in (today_iso, yesterday_iso):
        current = 0
    else:
        current = raw_current
    cal = p.get("activity_calendar") or []
    # Daily goal: 1 lesson per day for free tier, can be customized later
    target = int(p.get("daily_goal_target") or 1)
    done_today = 1 if today_iso in cal else 0
    # Next milestone calculation
    nm = next((m for m in MILESTONES if m > current), None)
    dtnm = (nm - current) if nm else None
    return StreakOut(
        current_streak=current,
        longest_streak=int(p.get("longest_streak") or current),
        last_active_date=last,
        today=today_iso,
        activity_calendar=sorted(cal)[-60:],   # last 60 days for UI
        daily_goal_target=target,
        daily_goal_done=done_today,
        daily_goal_complete=(done_today >= target),
        next_milestone=nm,
        days_to_next_milestone=dtnm,
    )


# ─── Onboarding Quiz → AI-personalized Learning Plan ──────────────────────
class OnboardingIn(BaseModel):
    motivation: str        # career, side_hustle, productivity, business, creator, curiosity
    experience: str        # never, beginner, some, intermediate, expert
    tools_used: List[str] = []  # chatgpt, claude, gemini, midjourney, perplexity, nano_banana, none
    goals: List[str] = []  # build_project, automate, create_content, promotion, fundamentals
    time_per_day: str      # 5, 15, 30, 60
    learning_style: str    # reading, audio, hands_on, all


class OnboardingPlan(BaseModel):
    headline: str
    rationale: str
    recommended_path_ids: List[str]
    first_lesson_id: Optional[str] = None
    daily_goal_target: int = 1
    generated_at: str


class OnboardingOut(BaseModel):
    plan: Optional[OnboardingPlan] = None
    onboarded: bool = False
    answers: Optional[dict] = None


_ONBOARD_SYSTEM = """You are the head of curriculum at Ascendra Academy.
A new learner just finished an onboarding quiz. Your job is to recommend a personalized learning plan from the EXISTING curriculum.

You will be given:
- The learner's quiz answers (motivation, experience, tools used, goals, time/day, learning style)
- A list of available paths (each with id, title, description, and difficulty)

You must respond with a JSON object exactly in this shape — no markdown fences, no commentary:
{
  "headline": "Short punchy 5-8 word personalized headline (e.g., 'Your AI side-hustle launchpad')",
  "rationale": "2-3 sentences explaining WHY these paths fit this learner, written directly to them (use 'you').",
  "recommended_path_ids": ["<path_id_1>", "<path_id_2>", "<path_id_3>"],
  "first_lesson_id": "<the very first lesson ID they should start with — usually the first lesson of the first recommended path>"
}

Rules:
- recommended_path_ids: 2-4 path IDs ranked best-fit first. Must be IDs from the provided list.
- first_lesson_id: should be an ID like 'f1l1', 'b1l1' (path + module + lesson) — pick the entry-point of recommended_path_ids[0].
- Adapt difficulty to experience level (beginners → fundamentals first).
- If they checked 'fundamentals' as a goal OR have 'never'/'beginner' experience, ALWAYS include the fundamentals path first.
- Keep rationale specific to their answers (e.g., 'Since you want to build a side hustle in 15 min/day, ...')
"""


async def _generate_onboarding_plan(answers: dict) -> Optional[OnboardingPlan]:
    """Call Claude to generate a personalized plan. Returns None on failure."""
    paths_docs = await db["curriculum_paths"].find({}, {"_id": 0, "id": 1, "title": 1, "description": 1, "difficulty": 1, "tier": 1}).to_list(50)
    if not paths_docs:
        return None
    paths_text = "\n".join([
        f"- {p['id']} | {p.get('title','?')} | {p.get('description','')[:120]} | difficulty={p.get('difficulty','?')} | tier={p.get('tier','free')}"
        for p in paths_docs
    ])
    user_msg = (
        f"LEARNER QUIZ ANSWERS:\n"
        f"  Motivation: {answers.get('motivation')}\n"
        f"  Experience: {answers.get('experience')}\n"
        f"  Tools used: {', '.join(answers.get('tools_used', [])) or 'none'}\n"
        f"  Goals: {', '.join(answers.get('goals', [])) or 'general'}\n"
        f"  Time per day: {answers.get('time_per_day')} minutes\n"
        f"  Learning style: {answers.get('learning_style')}\n\n"
        f"AVAILABLE PATHS:\n{paths_text}\n\n"
        f"Generate the JSON plan now."
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"onboarding-{uuid.uuid4().hex[:8]}",
            system_message=_ONBOARD_SYSTEM,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        reply = await chat.send_message(UserMessage(text=user_msg))
    except Exception as e:
        log.warning(f"onboarding LLM call failed: {e}")
        return None
    # Extract JSON
    import re as _re, json as _json
    t = (reply or "").strip()
    t = _re.sub(r"^```(?:json)?\s*", "", t)
    t = _re.sub(r"\s*```$", "", t)
    try:
        data = _json.loads(t)
    except Exception:
        # Fall back: find first {...} block
        start = t.find("{")
        if start < 0:
            return None
        depth = 0
        end = -1
        for i, c in enumerate(t[start:], start=start):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i; break
        if end < 0:
            return None
        try:
            data = _json.loads(t[start:end + 1])
        except Exception:
            return None
    # Validate IDs against actual paths
    valid_ids = {p["id"] for p in paths_docs}
    rec_ids = [pid for pid in (data.get("recommended_path_ids") or []) if pid in valid_ids]
    if not rec_ids:
        return None
    # Pick a sensible daily_goal_target from time_per_day
    try:
        mins = int(answers.get("time_per_day", "5"))
    except Exception:
        mins = 5
    daily_goal = 1 if mins <= 5 else (2 if mins <= 15 else 3)
    return OnboardingPlan(
        headline=str(data.get("headline", "Your personalized path"))[:120],
        rationale=str(data.get("rationale", ""))[:1000],
        recommended_path_ids=rec_ids[:4],
        first_lesson_id=str(data.get("first_lesson_id") or "") or None,
        daily_goal_target=daily_goal,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@api.post("/onboarding/submit", response_model=OnboardingOut)
async def submit_onboarding(body: OnboardingIn, user=Depends(current_user)):
    answers = body.model_dump()
    plan = await _generate_onboarding_plan(answers)
    update = {
        "$set": {
            "onboarding_answers": answers,
            "onboarded_at": datetime.now(timezone.utc).isoformat(),
        }
    }
    if plan:
        update["$set"]["onboarding_plan"] = plan.model_dump()
    await users_col.update_one({"id": user["id"]}, update)
    # Update daily goal too
    if plan:
        await progress_col.update_one(
            {"user_id": user["id"]},
            {"$set": {"daily_goal_target": plan.daily_goal_target}},
        )
    return OnboardingOut(plan=plan, onboarded=True, answers=answers)


class OnboardingAnonymousIn(BaseModel):
    email: EmailStr
    motivation: str
    experience: str
    tools_used: List[str] = []
    goals: List[str] = []
    time_per_day: str
    learning_style: str
    source: Optional[str] = None  # e.g. "landing_popup", "landing_button"


@api.post("/onboarding/anonymous")
async def submit_onboarding_anonymous(body: OnboardingAnonymousIn,
                                        background_tasks: BackgroundTasks):
    """Anonymous lead-capture variant of the onboarding quiz.

    Used on the public landing page. Saves answers + email to onboarding_leads
    and generates a personalized plan via Claude (best-effort). When the lead
    later signs up with the same email, the signup endpoint auto-attaches
    these answers so they skip the in-app onboarding.

    Resend email with the plan is sent in the background — does NOT block UI.
    """
    email_lower = body.email.lower()
    # Don't capture a lead for an already-registered user — they should log in.
    existing_user = await users_col.find_one({"email": email_lower}, {"_id": 0, "id": 1})
    if existing_user:
        return {
            "ok": True,
            "already_registered": True,
            "message": "Looks like you already have an account! Sign in to see your plan.",
        }
    answers = body.model_dump(exclude={"email", "source"})
    plan_model = await _generate_onboarding_plan(answers)
    plan_dict = plan_model.model_dump() if plan_model else None
    lead_id = str(uuid.uuid4())
    await db["onboarding_leads"].insert_one({
        "id": lead_id,
        "email": email_lower,
        "answers": answers,
        "plan": plan_dict,
        "source": body.source or "landing",
        "consumed": False,
        "created_at": datetime.now(timezone.utc),
    })
    # Send the plan via email in the background (best-effort).
    if plan_dict:
        background_tasks.add_task(_email_anonymous_plan, email_lower, plan_dict)
    return {
        "ok": True,
        "already_registered": False,
        "plan": plan_dict,
        "lead_id": lead_id,
    }


async def _email_anonymous_plan(email: str, plan: dict) -> None:
    """Best-effort send of the personalized plan email to a quiz-taker lead."""
    try:
        from email_service import send_email
        subject = f"Your personalized AI plan: {plan.get('headline', 'Ascendra')}"
        rationale = plan.get("rationale", "")
        daily = int(plan.get("daily_goal_target", 1) or 1)
        signup_url = f"{_public_web_url()}/signup?prefill={email}"
        html = f"""
        <div style="background:#0A0413;color:#F4F1FF;font-family:Inter,Arial,sans-serif;padding:32px;">
          <div style="max-width:560px;margin:0 auto;">
            <h1 style="color:#FFB000;font-size:28px;margin:0 0 8px 0;">Your AI plan is ready 🎯</h1>
            <div style="font-size:22px;font-weight:800;margin:14px 0;">{plan.get('headline','Your personalized path')}</div>
            <p style="line-height:1.55;color:#C8C5E6;margin:12px 0;">{rationale}</p>
            <div style="background:rgba(255,176,0,0.08);border:1px solid rgba(255,176,0,0.35);border-radius:12px;padding:14px 18px;margin:18px 0;">
              <div style="font-weight:800;color:#FFB000;">Your daily goal</div>
              <div>{daily} lesson{'s' if daily > 1 else ''} per day</div>
            </div>
            <a href="{signup_url}" style="display:inline-block;background:#FFB000;color:#0A0413;padding:14px 28px;border-radius:12px;font-weight:800;text-decoration:none;margin-top:8px;">Create your free account →</a>
            <p style="font-size:12px;color:#9CA0B8;margin-top:36px;">
              You'll automatically start with your personalized plan when you sign up.
            </p>
          </div>
        </div>
        """
        await send_email(to=email, subject=subject, html=html)
    except Exception as e:
        log.warning(f"anonymous plan email failed for {email}: {e}")


@api.get("/onboarding/me", response_model=OnboardingOut)
async def get_onboarding(user=Depends(current_user)):
    u = await users_col.find_one({"id": user["id"]}, {"_id": 0, "onboarding_plan": 1, "onboarded_at": 1, "onboarding_answers": 1})
    if not u:
        return OnboardingOut(onboarded=False)
    plan = u.get("onboarding_plan")
    return OnboardingOut(
        plan=OnboardingPlan(**plan) if plan else None,
        onboarded=bool(u.get("onboarded_at")),
        answers=u.get("onboarding_answers"),
    )


# ─── 15-Day AI Challenge ──────────────────────────────────────────────────
# A hand-curated sequence of 15 lessons spanning fundamentals → builder → prod
# Each "day" unlocks once the prior day is complete.
CHALLENGE_15_LESSONS: List[Dict[str, str]] = [
    {"day": 1,  "lesson_id": "f1l1", "theme": "AI 101: What's actually happening"},
    {"day": 2,  "lesson_id": "f1l2", "theme": "Choosing your AI tool"},
    {"day": 3,  "lesson_id": "f1l3", "theme": "Talking to AI: the prompt"},
    {"day": 4,  "lesson_id": "f2l1", "theme": "Prompting principles"},
    {"day": 5,  "lesson_id": "f2l2", "theme": "Iteration & refinement"},
    {"day": 6,  "lesson_id": "f2l3", "theme": "Tools for thought"},
    {"day": 7,  "lesson_id": "f3l1", "theme": "Where AI fails (and why)"},
    {"day": 8,  "lesson_id": "f3l2", "theme": "Hallucinations & fact-checking"},
    {"day": 9,  "lesson_id": "p1l1", "theme": "5 daily AI moves"},
    {"day": 10, "lesson_id": "p1l2", "theme": "Email & calendar superpowers"},
    {"day": 11, "lesson_id": "p2l1", "theme": "Workflow automation basics"},
    {"day": 12, "lesson_id": "c1l1", "theme": "AI for creative work"},
    {"day": 13, "lesson_id": "c2l1", "theme": "Image generation mastery"},
    {"day": 14, "lesson_id": "b1l1", "theme": "The AI opportunity radar"},
    {"day": 15, "lesson_id": "b1l2", "theme": "Build your first AI workflow"},
]


class ChallengeDay(BaseModel):
    day: int
    lesson_id: str
    theme: str
    title: Optional[str] = None
    duration_min: Optional[int] = None
    xp: Optional[int] = None
    status: str          # "locked", "available", "completed"


class ChallengeOut(BaseModel):
    name: str = "15-Day AI Challenge"
    total_days: int = 15
    days: List[ChallengeDay]
    current_day: int          # 1..15 — the next day they should work on
    completed_count: int
    is_complete: bool


@api.get("/challenge/15day", response_model=ChallengeOut)
async def get_15day_challenge(user=Depends(current_user)):
    p = await get_progress(user["id"])
    done_ids = set(p.get("completed_lesson_ids", []))

    # Resolve lesson metadata in batch (title, duration, xp) for the 15 lessons
    lesson_ids = [d["lesson_id"] for d in CHALLENGE_15_LESSONS]
    meta_map: Dict[str, dict] = {}
    docs = await db["curriculum_paths"].find({"modules.lessons.id": {"$in": lesson_ids}}, {"_id": 0, "modules": 1}).to_list(50)
    for path in docs:
        for m in path.get("modules", []):
            for lsn in m.get("lessons", []):
                if lsn.get("id") in lesson_ids:
                    meta_map[lsn["id"]] = {
                        "title": lsn.get("title"),
                        "duration_min": lsn.get("duration_min"),
                        "xp": lsn.get("xp"),
                    }

    days_out: List[ChallengeDay] = []
    completed = 0
    prev_done = True   # Day 1 starts available
    for entry in CHALLENGE_15_LESSONS:
        lid = entry["lesson_id"]
        meta = meta_map.get(lid, {})
        is_done = lid in done_ids
        if is_done:
            status = "completed"; completed += 1
        elif prev_done:
            status = "available"
        else:
            status = "locked"
        days_out.append(ChallengeDay(
            day=entry["day"],
            lesson_id=lid,
            theme=entry["theme"],
            title=meta.get("title"),
            duration_min=meta.get("duration_min"),
            xp=meta.get("xp"),
            status=status,
        ))
        prev_done = is_done

    # current_day = first non-completed day
    current_day = next((d.day for d in days_out if d.status != "completed"), 15)
    return ChallengeOut(
        days=days_out,
        current_day=current_day,
        completed_count=completed,
        is_complete=completed >= 15,
    )


# ─── Prompt Library (cross-lesson) ────────────────────────────────────────
class PromptLibraryItem(BaseModel):
    lesson_id: str
    lesson_title: str
    path_id: str
    path_title: str
    card_title: str
    instruction: str
    seed_prompt: str


@api.get("/prompts/library")
async def prompts_library(q: Optional[str] = None, path_id: Optional[str] = None,
                          limit: int = 200, user=Depends(current_user)):
    """Returns every `playground` card seed prompt across all lessons,
    searchable by free-text query (matches title, instruction, or prompt body)
    and optionally filterable by path_id.
    """
    items: List[PromptLibraryItem] = []
    paths = await db["curriculum_paths"].find({}, {"_id": 0}).to_list(200)
    needle = (q or "").lower().strip()
    for p in paths:
        if path_id and p.get("id") != path_id:
            continue
        for m in p.get("modules", []):
            for lsn in m.get("lessons", []):
                for card in lsn.get("cards", []):
                    if card.get("kind") != "playground":
                        continue
                    item = PromptLibraryItem(
                        lesson_id=lsn.get("id", ""),
                        lesson_title=lsn.get("title", ""),
                        path_id=p.get("id", ""),
                        path_title=p.get("title", ""),
                        card_title=card.get("title", ""),
                        instruction=card.get("instruction", ""),
                        seed_prompt=card.get("seed_prompt", ""),
                    )
                    if needle:
                        blob = (item.card_title + " " + item.instruction + " " + item.seed_prompt + " " + item.lesson_title).lower()
                        if needle not in blob:
                            continue
                    items.append(item)
                    if len(items) >= limit:
                        break
    # Compose a list of unique path filter options too
    path_options = sorted({(i.path_id, i.path_title) for i in items})
    return {
        "items": [i.model_dump() for i in items],
        "total": len(items),
        "paths": [{"id": pid, "title": ptitle} for pid, ptitle in path_options],
    }

# ─── Quiz / Recommendation ──────────────────────────────────────────────────
@api.put("/auth/me/quiz")
async def save_quiz_answers(body: QuizAnswers, user=Depends(current_user)):
    answers = body.dict(exclude_none=True)
    if not answers:
        raise HTTPException(400, "No answers provided")
    recommended = _recommend_path(answers)
    update = {"quiz_answers": answers, "recommended_path_id": recommended}
    if "goal" in answers:
        update["goal"] = answers["goal"]
    await users_col.update_one({"id": user["id"]}, {"$set": update})
    return {"recommended_path_id": recommended, "quiz_answers": answers}

# ─── Certificates ───────────────────────────────────────────────────────────
def _serialize_cert(c: dict) -> dict:
    return {
        "id": c["id"],
        "user_id": c["user_id"],
        "user_name": c.get("user_name") or "Ascendra Learner",
        "path_id": c["path_id"],
        "path_title": c["path_title"],
        "path_color": c.get("path_color", "#FFB000"),
        "issued_at": c["issued_at"],
        "serial": c["serial"],
    }

@api.get("/certificates")
async def list_certificates(user=Depends(current_user)):
    cursor = certs_col.find({"user_id": user["id"]}, {"_id": 0}).sort("issued_at", -1)
    certs = await cursor.to_list(100)
    return {"certificates": [_serialize_cert(c) for c in certs]}

@api.get("/certificates/{cert_id}")
async def get_certificate(cert_id: str, user=Depends(current_user)):
    c = await certs_col.find_one({"id": cert_id, "user_id": user["id"]}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Certificate not found")
    return _serialize_cert(c)

# Public certificate view (by id) — used for sharing
@api.get("/certificates/public/{cert_id}")
async def get_certificate_public(cert_id: str):
    c = await certs_col.find_one({"id": cert_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Certificate not found")
    return _serialize_cert(c)

# ─── AI Tutor (Claude Sonnet 4.5) ───────────────────────────────────────────
TUTOR_SYSTEM = (
    "You are Ascendra — the AI learning partner inside the Ascendra app. Your job is to teach "
    "people how to use AI from beginner to advanced builder, helping them rise beyond their "
    "limits. Be warm, encouraging, and concrete. Default to short, punchy answers (2–5 "
    "sentences). Use lists or step-by-step when asked 'how'. Recommend specific 2026 AI models "
    "when relevant (GPT-5.2, Claude Sonnet 4.5, Gemini 3 Pro/Flash, Nano Banana for images, "
    "Sora 2 for video, ElevenLabs for voice, Perplexity for research, Cursor for code). Never "
    "hallucinate URLs. Never refuse on safe topics. Always end with one useful follow-up "
    "question."
)

@api.post("/tutor/chat", response_model=ChatOut)
async def tutor_chat(body: ChatIn, user=Depends(current_user)):
    session_id = body.session_id or str(uuid.uuid4())

    prior = await chats_col.find(
        {"user_id": user["id"], "session_id": session_id},
        {"_id": 0, "role": 1, "content": 1, "created_at": 1},
    ).sort("created_at", 1).to_list(200)
    initial = [{"role": "system", "content": TUTOR_SYSTEM}] + [
        {"role": m["role"], "content": m["content"]} for m in prior
    ]

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=TUTOR_SYSTEM,
            initial_messages=initial,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        reply = await chat.send_message(UserMessage(text=body.message))
    except Exception as e:
        log.exception("LLM call failed")
        raise HTTPException(503, f"AI Tutor unavailable: {str(e)[:160]}")

    await chats_col.insert_one({
        "user_id": user["id"],
        "session_id": session_id,
        "role": "user",
        "content": body.message,
        "created_at": datetime.now(timezone.utc),
    })
    await chats_col.insert_one({
        "user_id": user["id"],
        "session_id": session_id,
        "role": "assistant",
        "content": reply,
        "created_at": datetime.now(timezone.utc),
    })
    return ChatOut(session_id=session_id, reply=reply)

@api.get("/tutor/history/{session_id}")
async def tutor_history(session_id: str, user=Depends(current_user)):
    msgs = await chats_col.find(
        {"user_id": user["id"], "session_id": session_id},
        {"_id": 0, "user_id": 0},
    ).sort("created_at", 1).to_list(500)
    return {"session_id": session_id, "messages": msgs}

@api.get("/tutor/sessions")
async def tutor_sessions(user=Depends(current_user)):
    """List distinct chat sessions for the current user."""
    pipeline = [
        {"$match": {"user_id": user["id"]}},
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$session_id",
            "last_message": {"$first": "$content"},
            "last_at": {"$first": "$created_at"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"last_at": -1}},
        {"$limit": 30},
        {"$project": {"_id": 0, "session_id": "$_id", "last_message": 1, "last_at": 1, "count": 1}},
    ]
    sessions = await chats_col.aggregate(pipeline).to_list(30)
    return {"sessions": sessions}

# ─── Lesson Playground (inline AI prompt practice) ───────────────────────
class PlaygroundIn(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    instruction: Optional[str] = Field(None, max_length=600)
    lesson_id: Optional[str] = None


class PlaygroundOut(BaseModel):
    response: str


@api.post("/playground/run", response_model=PlaygroundOut)
async def lesson_playground(body: PlaygroundIn, user=Depends(current_user)):
    """Inline LLM playground used by `playground` cards in the lesson player.
    Stateless — no chat history. Uses Claude Sonnet 4.5 via Emergent LLM key.
    """
    sys_msg = (
        body.instruction
        or "You are an AI tutor inside Ascendra Academy. The user is practicing prompting. "
           "Respond directly to their prompt as a helpful AI assistant would — concise, useful, "
           "and educational. Keep replies under 220 words unless the user asks for more."
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"playground-{user['id']}-{uuid.uuid4().hex[:8]}",
            system_message=sys_msg,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        reply = await chat.send_message(UserMessage(text=body.prompt))
    except Exception as e:
        log.exception("playground LLM call failed")
        raise HTTPException(503, f"AI Playground unavailable: {str(e)[:160]}")
    return PlaygroundOut(response=reply)


# ─── Pricing & Stripe ───────────────────────────────────────────────────────
# Founding-member pricing for the Business tier is granted while the number of
# active Business subscribers is below FOUNDING_BUSINESS_SEATS. After that,
# checkout falls back to the standard $149/mo price. See _load_stripe_config()
# for how price IDs are resolved.
FOUNDING_BUSINESS_SEATS = 25

TIERS = {
    "ascender": {
        "id": "ascender", "name": "Ascender",
        "price_monthly": 9.99, "price_annual": 99.00,
        "blurb": "Start your ascent. The essentials.",
        "features": [
            "AI Fundamentals path (8 lessons)",
            "Unlimited AI Tutor (Claude 4.5)",
            "Browse all 22 AI models",
            "Daily streak + XP tracking",
        ],
    },
    "pathfinder": {
        "id": "pathfinder", "name": "Pathfinder",
        "price_monthly": 19.99, "price_annual": 199.00,
        "blurb": "For serious learners forging the way.",
        "features": [
            "Everything in Ascender, plus:",
            "7 additional paths (Business, Creators, Productivity)",
            "Pro: Prompt Engineering Mastery",
            "Pro: AI Automation Stack (agents, MCP)",
            "Pro: Code With AI (Cursor, Claude Code)",
            "XP + leaderboards",
        ],
        "highlight": True,
    },
    "sage": {
        "id": "sage", "name": "Sage",
        "price_monthly": 29.99, "price_annual": 299.00,
        "blurb": "Master the craft. Build the business.",
        "features": [
            "Everything in Pathfinder, plus:",
            "Sage: AI-First Startup Playbook",
            "Sage: AI Sales & Marketing Engine",
            "Sage: Enterprise AI Strategy",
            "Real founder case studies",
            "Quarterly AI roadmap briefings",
            "Priority AI Tutor response speed",
            "Lifetime price lock",
        ],
    },
    "business": {
        "id": "business", "name": "Business",
        # Standard pricing shown to anyone after founding seats fill.
        "price_monthly": 149.00, "price_annual": 1490.00,
        # Founding-member pricing is displayed as promotional copy on the Pricing
        # page while remaining_seats > 0. It is NOT wired into checkout price
        # selection — the operator is responsible for setting the correct Stripe
        # price in stripe_config.json and rotating it when founding seats fill.
        # The seat counter is informational, driven by count of active business subscribers.
        "founding_price_monthly": 99.00, "founding_price_annual": 990.00,
        "founding_seats_total": FOUNDING_BUSINESS_SEATS,
        "blurb": "Equip your team to learn, govern, and apply AI across everyday business operations.",
        "features": [
            "Up to 5 team members",
            "Business-focused AI learning paths",
            "Employee progress & certificate tracking",
            "Shared company prompt library",
            "Business templates & SOPs",
            "AI-readiness assessment",
            "Responsible-AI policy starter kit",
            "Marketing / Customer Service / Sales / Ops workflow library",
            "Monthly group implementation workshop",
            "One business workflow review per month",
            "Implementation-service discount",
        ],
        "audience": "Small businesses and teams implementing AI in their operations.",
    },
}


async def _business_founding_status() -> dict:
    """How many founding Business seats remain?
    Counts currently-active Business subscribers (any interval).
    Returns {"seats_used": int, "seats_total": int, "seats_remaining": int,
    "founding_active": bool}.
    """
    total = int(TIERS["business"].get("founding_seats_total") or 0)
    try:
        used = await users_col.count_documents({"tier": "business"})
    except Exception as e:
        log.warning(f"business founding count failed: {e}")
        used = 0
    remaining = max(0, total - used)
    return {
        "seats_used": used,
        "seats_total": total,
        "seats_remaining": remaining,
        "founding_active": remaining > 0,
    }


@api.get("/pricing")
async def pricing():
    tiers = [dict(t) for t in TIERS.values()]  # shallow copy so we can annotate
    # Annotate the Business tier with live founding-availability so the UI can
    # render the correct promo state without an extra round-trip.
    biz_status = await _business_founding_status()
    for t in tiers:
        if t["id"] == "business":
            t["founding_seats_used"] = biz_status["seats_used"]
            t["founding_seats_total"] = biz_status["seats_total"]
            t["founding_seats_remaining"] = biz_status["seats_remaining"]
            t["founding_active"] = biz_status["founding_active"]
            # Effective price shown on the pricing page = founding while seats remain,
            # else the standard price.
            if biz_status["founding_active"]:
                t["effective_price_monthly"] = t.get("founding_price_monthly") or t["price_monthly"]
                t["effective_price_annual"] = t.get("founding_price_annual") or t["price_annual"]
            else:
                t["effective_price_monthly"] = t["price_monthly"]
                t["effective_price_annual"] = t["price_annual"]
    return {"tiers": tiers, "business_founding": biz_status}

@api.post("/billing/checkout")
async def create_checkout(body: CheckoutIn, request: Request, user=Depends(current_user)):
    if body.tier not in TIERS:
        raise HTTPException(400, "Invalid tier")
    origin = body.origin_url.rstrip("/")

    # The $2.99 trial stays as a one-time payment (via the emergent wrapper).
    if body.interval == "trial":
        if user.get("has_used_trial"):
            raise HTTPException(400, "Trial already used. Pick a plan to keep going.")
        amount_usd = 2.99
        plan_name = "Sage (7-day trial)"
        webhook_url = f"{str(request.base_url).rstrip('/')}/api/billing/webhook"
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
        try:
            session = await stripe_checkout.create_checkout_session(
                CheckoutSessionRequest(
                    amount=float(amount_usd),
                    currency="usd",
                    success_url=f"{origin}/checkout-success?session_id={{CHECKOUT_SESSION_ID}}",
                    cancel_url=f"{origin}/pricing",
                    metadata={"user_id": user["id"], "tier": body.tier, "interval": body.interval, "plan": plan_name},
                )
            )
        except Exception as e:
            log.exception("Stripe error (trial)")
            raise HTTPException(502, f"Stripe error: {str(e)[:140]}")
        await sessions_col.insert_one({
            "session_id": session.session_id, "user_id": user["id"],
            "tier": body.tier, "interval": body.interval, "amount_usd": amount_usd,
            "status": "pending", "mode": "payment",
            "created_at": datetime.now(timezone.utc),
        })
        return {"url": session.url, "session_id": session.session_id}

    # Recurring subscriptions for monthly + annual — use the native Stripe SDK
    cfg = _load_stripe_config()
    price_id = cfg.get("tiers", {}).get(body.tier, {}).get("prices", {}).get(body.interval)
    if not price_id:
        raise HTTPException(503, "Subscription pricing not configured yet — admin needs to seed Stripe Products/Prices.")
    amount_usd = TIERS[body.tier]["price_annual"] if body.interval == "annual" else TIERS[body.tier]["price_monthly"]
    plan_name = f"{TIERS[body.tier]['name']} ({body.interval.title()})"
    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_API_KEY
        sess = _stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{origin}/checkout-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{origin}/pricing",
            customer_email=(user.get("email") if not user.get("stripe_customer_id") else None),
            customer=user.get("stripe_customer_id"),
            client_reference_id=user["id"],
            metadata={"user_id": user["id"], "tier": body.tier, "interval": body.interval, "plan": plan_name},
            allow_promotion_codes=True,
        )
    except Exception as e:
        log.exception("Stripe subscription checkout error")
        raise HTTPException(502, f"Stripe error: {str(e)[:200]}")

    await sessions_col.insert_one({
        "session_id": sess.id, "user_id": user["id"],
        "tier": body.tier, "interval": body.interval, "amount_usd": amount_usd,
        "status": "pending", "mode": "subscription", "price_id": price_id,
        "created_at": datetime.now(timezone.utc),
    })
    return {"url": sess.url, "session_id": sess.id}


def _load_stripe_config() -> dict:
    """Load Stripe Products/Prices/Portal config (created by setup script)."""
    try:
        cfg_path = ROOT_DIR / "stripe_config.json"
        if cfg_path.exists():
            import json as _json
            return _json.loads(cfg_path.read_text())
    except Exception as e:
        log.warning(f"stripe_config.json load failed: {e}")
    return {}


# ─── Renewal Reminder helpers ───────────────────────────────────────────────
# Triggered by Stripe `invoice.upcoming` webhook (primary) and a daily
# fallback admin cron endpoint. Idempotent via the `last_renewal_reminder_*`
# fields on the user document.
async def _try_send_renewal_reminder(
    customer_id: Optional[str],
    subscription_id: Optional[str],
    amount_usd: float,
    renewal_unix: Optional[int],
    source: str = "webhook",
    user_override: Optional[dict] = None,
    force: bool = False,
) -> dict:
    """Send a renewal-reminder email if not already sent for this renewal cycle.
    Returns a small dict describing the outcome — never raises.
    """
    user = user_override
    if not user and customer_id:
        user = await users_col.find_one({"stripe_customer_id": customer_id}, {"_id": 0})
    if not user:
        return {"ok": False, "reason": "user_not_found", "customer_id": customer_id}
    if not user.get("email"):
        return {"ok": False, "reason": "no_email", "user_id": user.get("id")}
    # Idempotency: don't re-send for the same renewal cycle
    renewal_dt = None
    if renewal_unix:
        try:
            renewal_dt = datetime.fromtimestamp(int(renewal_unix), tz=timezone.utc)
        except Exception:
            renewal_dt = None
    if not renewal_dt:
        renewal_dt = user.get("tier_expires_at")
    if not renewal_dt:
        return {"ok": False, "reason": "no_renewal_date", "user_id": user.get("id")}
    last_for = user.get("last_renewal_reminder_for")
    if not force and last_for and renewal_dt and abs((last_for - renewal_dt).total_seconds()) < 60:
        return {"ok": True, "reason": "already_sent", "user_id": user["id"], "skipped": True}

    # Days until renewal
    days_until = max(0, int(round((renewal_dt - datetime.now(timezone.utc)).total_seconds() / 86400)))
    # Resolve amount: prefer Stripe-provided amount_due, otherwise look up from TIERS
    tier = user.get("tier") or "ascender"
    interval = user.get("subscription_interval") or "monthly"
    if (not amount_usd or amount_usd < 0.01) and tier in TIERS:
        amount_usd = float(TIERS[tier]["price_annual"] if interval == "annual" else TIERS[tier]["price_monthly"])
    portal_url = f"{_public_web_url()}/profile"
    try:
        from email_service import send_renewal_reminder
        r = send_renewal_reminder(
            to=user["email"], name=user.get("name"),
            tier=tier, interval=interval,
            renewal_date_str=renewal_dt.strftime("%B %-d, %Y") if hasattr(renewal_dt, "strftime") else str(renewal_dt),
            amount_usd=float(amount_usd or 0),
            portal_url=portal_url,
            days_until=days_until or 7,
        )
    except Exception as e:
        log.exception(f"renewal reminder send failed for user={user.get('id')}: {e}")
        return {"ok": False, "reason": "send_exception", "error": str(e)[:160]}
    if not r.get("ok"):
        return {"ok": False, "reason": "send_failed", "error": r.get("error")}
    # Mark sent (idempotency)
    await users_col.update_one(
        {"id": user["id"]},
        {"$set": {
            "last_renewal_reminder_sent_at": datetime.now(timezone.utc),
            "last_renewal_reminder_for": renewal_dt,
            "last_renewal_reminder_source": source,
        }},
    )
    log.info(f"renewal_reminder sent user={user.get('email')} source={source} renews={renewal_dt.isoformat() if hasattr(renewal_dt, 'isoformat') else renewal_dt}")
    return {"ok": True, "user_id": user["id"], "email": user["email"], "renewal_at": renewal_dt.isoformat() if hasattr(renewal_dt, "isoformat") else str(renewal_dt)}


async def _scan_and_send_renewal_reminders(window_days_min: float = 6.5, window_days_max: float = 7.5) -> dict:
    """Scan users with an active subscription whose renewal is ~7 days away
    (within the configurable window) and send the reminder email.
    Idempotent via _try_send_renewal_reminder. Returns a summary dict."""
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(days=window_days_min)
    window_end = now + timedelta(days=window_days_max)
    cur = users_col.find({
        "subscription_status": "active",
        "tier": {"$in": ["ascender", "pathfinder", "sage", "business"]},
        "tier_expires_at": {"$gte": window_start, "$lte": window_end},
        "subscription_interval": {"$in": ["monthly", "annual"]},
    }, {"_id": 0})
    candidates = await cur.to_list(1000)
    sent, skipped, failed = [], [], []
    for u in candidates:
        result = await _try_send_renewal_reminder(
            customer_id=u.get("stripe_customer_id"),
            subscription_id=u.get("stripe_subscription_id"),
            amount_usd=0.0,  # let helper resolve from TIERS
            renewal_unix=None,
            source="cron",
            user_override=u,
        )
        if result.get("ok") and not result.get("skipped"):
            sent.append({"user_id": u["id"], "email": u["email"]})
        elif result.get("ok") and result.get("skipped"):
            skipped.append({"user_id": u["id"], "email": u["email"], "reason": "already_sent"})
        else:
            failed.append({"user_id": u.get("id"), "email": u.get("email"), "reason": result.get("reason")})
    return {
        "scanned": len(candidates), "sent": len(sent), "skipped": len(skipped), "failed": len(failed),
        "details": {"sent": sent, "skipped": skipped, "failed": failed},
        "window": [window_start.isoformat(), window_end.isoformat()],
    }

@api.get("/billing/status/{session_id}")
async def checkout_status(session_id: str, request: Request, user=Depends(current_user)):
    rec = await sessions_col.find_one({"session_id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Session not found")

    if rec["status"] == "pending":
        try:
            import stripe as _stripe
            _stripe.api_key = STRIPE_API_KEY
            sess = _stripe.checkout.Session.retrieve(session_id)
            payment_paid = (sess.get("payment_status") == "paid") if isinstance(sess, dict) else (getattr(sess, "payment_status", "") == "paid")
            if payment_paid:
                mode = rec.get("mode", "payment")
                interval = rec.get("interval", "monthly")
                granted_tier = "sage" if interval == "trial" else rec["tier"]

                if mode == "subscription":
                    # Real Stripe subscription — read the subscription period for expiry
                    sub_id = sess.get("subscription") if isinstance(sess, dict) else getattr(sess, "subscription", None)
                    cust_id = sess.get("customer") if isinstance(sess, dict) else getattr(sess, "customer", None)
                    expires_at = None
                    if sub_id:
                        sub = _stripe.Subscription.retrieve(sub_id)
                        cpe = sub.get("current_period_end") if isinstance(sub, dict) else getattr(sub, "current_period_end", None)
                        if cpe:
                            expires_at = datetime.fromtimestamp(int(cpe), tz=timezone.utc)
                    update = {
                        "tier": granted_tier, "subscription_interval": interval,
                        "tier_expires_at": expires_at, "stripe_subscription_id": sub_id,
                        "subscription_status": "active",
                    }
                    if cust_id: update["stripe_customer_id"] = cust_id
                else:
                    # One-time payment (trial)
                    days = {"trial": 7, "annual": 365, "monthly": 30}.get(interval, 30)
                    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
                    update = {"tier": granted_tier, "subscription_interval": interval, "tier_expires_at": expires_at}
                    if interval == "trial": update["has_used_trial"] = True
                    cust_id = sess.get("customer") if isinstance(sess, dict) else getattr(sess, "customer", None)
                    if cust_id: update["stripe_customer_id"] = cust_id

                await users_col.update_one({"id": user["id"]}, {"$set": update})
                await sessions_col.update_one({"session_id": session_id}, {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc)}})
                rec["status"] = "paid"

                if not rec.get("welcome_email_sent"):
                    try:
                        from email_service import send_checkout_success
                        send_checkout_success(
                            to=user["email"], name=user.get("name"),
                            tier=granted_tier, interval=interval,
                            amount_usd=float(rec.get("amount_usd") or 0),
                            dashboard_url=f"{_public_web_url()}/dashboard",
                        )
                        await sessions_col.update_one({"session_id": session_id}, {"$set": {"welcome_email_sent": True, "welcome_email_at": datetime.now(timezone.utc)}})
                    except Exception as e:
                        log.warning(f"welcome email send failed: {e}")
        except Exception as e:
            log.warning(f"Stripe status check failed: {e}")

    return {"status": rec["status"], "tier": rec["tier"], "interval": rec.get("interval", "monthly")}

@api.post("/billing/webhook")
async def stripe_webhook(request: Request, stripe_signature: Optional[str] = Header(None)):
    """Handles Stripe events for both one-time payments and subscriptions.
    SECURITY: signature verification is REQUIRED. We never process unsigned
    payloads — that would allow anyone to forge tier upgrades, subscriptions,
    or grant Sage access for free.
    """
    payload = await request.body()
    import stripe as _stripe
    _stripe.api_key = STRIPE_API_KEY
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        log.error("STRIPE_WEBHOOK_SECRET is not configured — rejecting webhook")
        raise HTTPException(503, "Webhook handler not configured")
    if not stripe_signature:
        log.warning("webhook rejected: missing stripe-signature header")
        raise HTTPException(400, "Missing stripe-signature header")
    try:
        event = _stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
    except Exception as e:
        log.warning(f"webhook verify failed: {e}")
        raise HTTPException(400, "Invalid signature")

    etype = event.get("type") if isinstance(event, dict) else getattr(event, "type", "")
    obj = (event.get("data", {}) or {}).get("object", {}) if isinstance(event, dict) else event.data.object

    try:
        if etype == "checkout.session.completed":
            sess_id = obj.get("id") if isinstance(obj, dict) else getattr(obj, "id", None)
            meta = obj.get("metadata", {}) if isinstance(obj, dict) else (getattr(obj, "metadata", {}) or {})
            uid = meta.get("user_id")
            tier = meta.get("tier")
            interval = meta.get("interval", "monthly")
            mode = obj.get("mode") if isinstance(obj, dict) else getattr(obj, "mode", "payment")
            cust_id = obj.get("customer") if isinstance(obj, dict) else getattr(obj, "customer", None)
            sub_id = obj.get("subscription") if isinstance(obj, dict) else getattr(obj, "subscription", None)
            granted_tier = "sage" if interval == "trial" else tier
            if uid and granted_tier:
                update = {"tier": granted_tier, "subscription_interval": interval}
                if cust_id: update["stripe_customer_id"] = cust_id
                if sub_id:
                    update["stripe_subscription_id"] = sub_id
                    update["subscription_status"] = "active"
                    sub = _stripe.Subscription.retrieve(sub_id)
                    cpe = sub.get("current_period_end") if isinstance(sub, dict) else getattr(sub, "current_period_end", None)
                    if cpe: update["tier_expires_at"] = datetime.fromtimestamp(int(cpe), tz=timezone.utc)
                else:
                    days = {"trial": 7, "annual": 365, "monthly": 30}.get(interval, 30)
                    update["tier_expires_at"] = datetime.now(timezone.utc) + timedelta(days=days)
                    if interval == "trial": update["has_used_trial"] = True
                await users_col.update_one({"id": uid}, {"$set": update})
                await sessions_col.update_one({"session_id": sess_id}, {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc)}})

        elif etype in ("invoice.paid", "invoice.payment_succeeded"):
            sub_id = obj.get("subscription") if isinstance(obj, dict) else getattr(obj, "subscription", None)
            cust_id = obj.get("customer") if isinstance(obj, dict) else getattr(obj, "customer", None)
            if sub_id:
                sub = _stripe.Subscription.retrieve(sub_id)
                cpe = sub.get("current_period_end") if isinstance(sub, dict) else getattr(sub, "current_period_end", None)
                if cpe and cust_id:
                    expires_at = datetime.fromtimestamp(int(cpe), tz=timezone.utc)
                    await users_col.update_one({"stripe_customer_id": cust_id}, {"$set": {"tier_expires_at": expires_at, "subscription_status": "active"}})

        elif etype == "customer.subscription.updated":
            sub_id = obj.get("id") if isinstance(obj, dict) else getattr(obj, "id", None)
            cust_id = obj.get("customer") if isinstance(obj, dict) else getattr(obj, "customer", None)
            status = obj.get("status") if isinstance(obj, dict) else getattr(obj, "status", "active")
            cpe = obj.get("current_period_end") if isinstance(obj, dict) else getattr(obj, "current_period_end", None)
            cancel_at_period_end = obj.get("cancel_at_period_end") if isinstance(obj, dict) else getattr(obj, "cancel_at_period_end", False)
            update = {"subscription_status": status, "stripe_subscription_id": sub_id, "subscription_cancel_at_period_end": bool(cancel_at_period_end)}
            if cpe: update["tier_expires_at"] = datetime.fromtimestamp(int(cpe), tz=timezone.utc)
            # Detect tier change via Price → metadata
            items = obj.get("items", {}).get("data", []) if isinstance(obj, dict) else []
            if items:
                price = items[0].get("price", {}) if isinstance(items[0], dict) else {}
                meta = price.get("metadata", {}) if isinstance(price, dict) else {}
                new_tier = meta.get("ascendra_tier")
                new_interval = meta.get("ascendra_interval")
                if new_tier and status == "active":
                    update["tier"] = new_tier
                    if new_interval: update["subscription_interval"] = new_interval
            if cust_id:
                await users_col.update_one({"stripe_customer_id": cust_id}, {"$set": update})

        elif etype == "customer.subscription.deleted":
            cust_id = obj.get("customer") if isinstance(obj, dict) else getattr(obj, "customer", None)
            if cust_id:
                await users_col.update_one(
                    {"stripe_customer_id": cust_id},
                    {"$set": {"tier": "free", "subscription_interval": None, "subscription_status": "canceled", "tier_expires_at": None}},
                )

        elif etype == "invoice.upcoming":
            # Stripe fires this ~7 days before the next renewal (configurable in dashboard).
            # We use it as the primary renewal-reminder trigger.
            cust_id = obj.get("customer") if isinstance(obj, dict) else getattr(obj, "customer", None)
            sub_id = obj.get("subscription") if isinstance(obj, dict) else getattr(obj, "subscription", None)
            amount_due = obj.get("amount_due") if isinstance(obj, dict) else getattr(obj, "amount_due", 0)
            period_end_ts = obj.get("period_end") if isinstance(obj, dict) else getattr(obj, "period_end", None)
            await _try_send_renewal_reminder(
                customer_id=cust_id,
                subscription_id=sub_id,
                amount_usd=(int(amount_due or 0) / 100.0),
                renewal_unix=int(period_end_ts) if period_end_ts else None,
                source="webhook",
            )
    except Exception as e:
        log.exception(f"webhook handler error for {etype}: {e}")

    return {"received": True}


@api.get("/billing/info")
async def billing_info():
    return {"uses_real_stripe": False}


# ─── Smart subscription status (Phase 17) ───────────────────────────────────
@api.get("/billing/status")
async def billing_status(user=Depends(current_user)):
    """Return the user's current billing state for the dashboard/profile card.

    States:
      - ACTIVE_RENEWING — paid, auto-renews on tier_expires_at
      - ACTIVE_CANCELING — paid, but cancel_at_period_end → access ends on tier_expires_at
      - PAST_DUE — Stripe says payment failed; user must update card
      - LAPSED — was paid before, now on free; access ended
      - FREE_NEVER_PAID — never paid; no stripe_customer_id

    Includes `certificates_count` so the UI can reassure lapsed users that
    their earned certificates remain theirs forever.
    """
    # Auto-downgrade if expired (this is the existing helper)
    fresh = await users_col.find_one({"id": user["id"]}, {"_id": 0})
    if fresh:
        fresh = await auto_downgrade_if_expired(fresh)
    else:
        fresh = user
    tier = fresh.get("tier", "free")
    expires_at = fresh.get("tier_expires_at")
    if expires_at and getattr(expires_at, "tzinfo", None) is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    cust_id = fresh.get("stripe_customer_id")
    sub_status = fresh.get("subscription_status")
    cap_end = bool(fresh.get("subscription_cancel_at_period_end", False))
    interval = fresh.get("subscription_interval")
    # has_ever_paid covers three cases:
    #   1. Real Stripe customer (stripe_customer_id present)
    #   2. Active subscription record (stripe_subscription_id present)
    #   3. User was on a paid tier in the past — tier_expires_at exists even if
    #      now downgraded to free (covers manually-upgraded admin/test users
    #      AND users whose Stripe customer was deleted)
    has_ever_paid = bool(
        cust_id
        or fresh.get("stripe_subscription_id")
        or fresh.get("tier_expires_at") is not None
        or (sub_status and sub_status != "free")
    )

    # Determine state
    if tier == "free":
        state = "LAPSED" if has_ever_paid else "FREE_NEVER_PAID"
    elif sub_status == "past_due":
        state = "PAST_DUE"
    elif cap_end:
        state = "ACTIVE_CANCELING"
    else:
        state = "ACTIVE_RENEWING"

    # Certificate count for lapsed reassurance message
    try:
        cert_count = await certs_col.count_documents({"user_id": fresh["id"]})
    except Exception:
        cert_count = 0

    # Look up renewal amount from TIERS table
    tier_def = TIERS.get(tier) if tier != "free" else None
    amount_usd = None
    if tier_def and interval:
        if interval == "annual":
            amount_usd = float(tier_def.get("price_annual", 0))
        else:
            amount_usd = float(tier_def.get("price_monthly", 0))

    return {
        "state": state,
        "tier": tier,
        "interval": interval,
        "amount_usd": amount_usd,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "renews_at": expires_at.isoformat() if (expires_at and state == "ACTIVE_RENEWING") else None,
        "ends_at": expires_at.isoformat() if (expires_at and state == "ACTIVE_CANCELING") else None,
        "subscription_status": sub_status,
        "cancel_at_period_end": cap_end,
        "can_open_portal": bool(cust_id),
        "can_resume": state == "ACTIVE_CANCELING" and bool(fresh.get("stripe_subscription_id")),
        "has_ever_paid": has_ever_paid,
        "certificates_count": cert_count,
    }


@api.post("/billing/resume")
async def billing_resume(user=Depends(current_user)):
    """Reverse a pending cancellation (cancel_at_period_end → false).

    Requires an active Stripe subscription that is currently scheduled to cancel
    at the end of the billing period. Free / lapsed users should use checkout.
    """
    sub_id = user.get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(400, "No active subscription to resume. Please use the Pricing page to start a new plan.")
    if not user.get("subscription_cancel_at_period_end"):
        return {"ok": True, "message": "Subscription is already set to renew.", "no_op": True}
    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_API_KEY
        sub = _stripe.Subscription.modify(sub_id, cancel_at_period_end=False)
        new_cap_end = sub.get("cancel_at_period_end") if isinstance(sub, dict) else getattr(sub, "cancel_at_period_end", False)
        await users_col.update_one(
            {"id": user["id"]},
            {"$set": {"subscription_cancel_at_period_end": bool(new_cap_end),
                       "subscription_status": "active"}},
        )
        return {
            "ok": True,
            "message": "Your subscription will continue renewing.",
            "cancel_at_period_end": bool(new_cap_end),
        }
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)[:240]
        log.warning(f"resume subscription failed: {msg}")
        raise HTTPException(502, f"Could not resume subscription: {msg}")


# ─── Stripe Customer Portal ─────────────────────────────────────────────────
class PortalIn(BaseModel):
    return_url: Optional[str] = None


@api.post("/billing/portal")
async def billing_portal(body: PortalIn, user=Depends(current_user)):
    """Open the Stripe-hosted customer portal so users can manage billing & invoices."""
    cust_id = user.get("stripe_customer_id")
    if not cust_id:
        raise HTTPException(400, "No billing history found. Make a purchase first to enable the portal.")
    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_API_KEY
        session = _stripe.billing_portal.Session.create(
            customer=cust_id,
            return_url=(body.return_url or f"{_public_web_url()}/profile"),
            configuration=(_load_stripe_config().get("portal_configuration_id") or None),
        )
        url = session.get("url") if isinstance(session, dict) else getattr(session, "url", None)
        if not url:
            raise HTTPException(502, "Portal URL missing")
        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)[:240]
        log.warning(f"customer portal failed: {msg}")
        # Detect the common "no portal configured" case and give a clear message
        if "configuration" in msg.lower() or "no_such_configuration" in msg.lower():
            raise HTTPException(503, "Stripe customer portal isn't configured yet. Admin: enable it at dashboard.stripe.com/settings/billing/portal")
        if "permission" in msg.lower() or "scope" in msg.lower():
            raise HTTPException(503, "Stripe restricted key is missing 'Billing portal: write' permission.")
        raise HTTPException(502, f"Portal error: {msg}")


# ─── Admin email preview & test send ────────────────────────────────────────
class EmailTestIn(BaseModel):
    template: Literal["password_reset", "checkout_success", "invite", "renewal_reminder"]
    to: Optional[EmailStr] = None  # if not provided, sends to the admin


@api.get("/admin/email/preview/{template}")
async def admin_email_preview(template: str, admin=Depends(require_admin)):
    """Return the HTML body of a template so the admin can preview it in an iframe."""
    from email_service import _shell  # internal — fine for admin tooling
    name = admin.get("name") or admin["email"].split("@")[0]
    dashboard_url = f"{_public_web_url()}/dashboard"
    if template == "password_reset":
        from email_service import send_password_reset
        # Render but don't send — build the HTML by calling the template builders directly.
        # Easiest: replicate the body the function would build. We'll re-import its internals.
        reset_url = f"{_public_web_url()}/reset-password?token=PREVIEW_TOKEN_123"
        subject = "Reset your Ascendra password"
        preheader = "Reset your password — link expires in 60 minutes."
        body_html = f"""
          <h1 style="margin:0 0 6px 0;color:#FFFFFF;font-size:28px;line-height:34px;letter-spacing:-0.5px;font-weight:900;">Reset your password</h1>
          <p style="margin:0 0 20px 0;color:#B8B8C2;font-size:15px;line-height:22px;">Hey {name}, we got a request to reset your Ascendra password. Tap the button below to choose a new one. The link expires in <strong style="color:#EDEDED;">60 minutes</strong> and can only be used once.</p>
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:18px 0 22px 0;"><tr><td bgcolor="#FFB000" style="border-radius:12px;"><a href="{reset_url}" style="display:inline-block;padding:14px 26px;color:#000000;font-weight:800;font-size:15px;text-decoration:none;border-radius:12px;">Reset password →</a></td></tr></table>
          <p style="margin:8px 0 0 0;color:#7a7a85;font-size:12px;line-height:18px;">Or copy &amp; paste this URL into your browser:<br><a href="{reset_url}" style="color:#FFB000;text-decoration:none;word-break:break-all;">{reset_url}</a></p>
          <p style="margin:24px 0 0 0;color:#7a7a85;font-size:12px;line-height:18px;">Didn't ask for this? You can safely ignore this email — your password won't change.</p>
        """
        return {"subject": subject, "html": _shell(subject, preheader, body_html)}
    elif template == "checkout_success":
        subject = "You're in. Welcome to Ascendra PATHFINDER."
        preheader = "Your PATHFINDER access is active. Time to rise."
        body_html = f"""
          <h1 style="margin:0 0 6px 0;color:#FFFFFF;font-size:28px;line-height:34px;letter-spacing:-0.5px;font-weight:900;">Welcome to Pathfinder. Seven paths are now yours.</h1>
          <p style="margin:0 0 18px 0;color:#B8B8C2;font-size:15px;line-height:22px;">Hey {name} — your payment came through, and your full Ascendra <strong style="color:#FFB000;">PATHFINDER</strong> access is now live. Open the dashboard to pick up where you left off — or start your first path.</p>
          <div style="margin:18px 0;padding:18px;background:#0d0d12;border:1px solid #26262E;border-radius:12px;">
            <div style="color:#7a7a85;font-size:11px;letter-spacing:1.5px;font-weight:700;">RECEIPT</div>
            <div style="margin-top:10px;color:#EDEDED;font-size:14px;"><span style="color:#7a7a85;">Plan:</span> <strong>Ascendra PATHFINDER</strong></div>
            <div style="margin-top:6px;color:#EDEDED;font-size:14px;"><span style="color:#7a7a85;">Billing:</span> annual (12 months)</div>
            <div style="margin-top:6px;color:#EDEDED;font-size:14px;"><span style="color:#7a7a85;">Amount:</span> <strong style="color:#FFB000;">$199.00 USD</strong></div>
          </div>
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:14px 0 22px 0;"><tr><td bgcolor="#FFB000" style="border-radius:12px;"><a href="{dashboard_url}" style="display:inline-block;padding:14px 26px;color:#000000;font-weight:800;font-size:15px;text-decoration:none;border-radius:12px;">Open my dashboard →</a></td></tr></table>
        """
        return {"subject": subject, "html": _shell(subject, preheader, body_html)}
    elif template == "invite":
        login_url = f"{_public_web_url()}/login"
        subject = "Your Ascendra Academy invite"
        preheader = "Your SAGE access is ready — first-time password inside."
        body_html = f"""
          <h1 style="margin:0 0 6px 0;color:#FFFFFF;font-size:28px;line-height:34px;letter-spacing:-0.5px;font-weight:900;">You're in. Welcome.</h1>
          <p style="margin:0 0 18px 0;color:#B8B8C2;font-size:15px;line-height:22px;">Hey {name} — you've been invited to <strong style="color:#FFB000;">Ascendra Academy</strong> with full <strong>SAGE</strong> access.</p>
          <div style="margin:18px 0;padding:18px;background:#0d0d12;border:1px solid #26262E;border-radius:12px;">
            <div style="color:#7a7a85;font-size:11px;letter-spacing:1.5px;font-weight:700;">YOUR LOGIN</div>
            <div style="margin-top:10px;color:#EDEDED;font-size:14px;"><span style="color:#7a7a85;">Email:</span> <strong>{admin['email']}</strong></div>
            <div style="margin-top:6px;color:#EDEDED;font-size:14px;"><span style="color:#7a7a85;">Temp password:</span> <code style="background:#26262E;padding:3px 8px;border-radius:6px;color:#FFB000;font-family:ui-monospace,Menlo,monospace;">temp_xyz_789</code></div>
          </div>
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:14px 0 22px 0;"><tr><td bgcolor="#FFB000" style="border-radius:12px;"><a href="{login_url}" style="display:inline-block;padding:14px 26px;color:#000000;font-weight:800;font-size:15px;text-decoration:none;border-radius:12px;">Sign in to Ascendra →</a></td></tr></table>
        """
        return {"subject": subject, "html": _shell(subject, preheader, body_html)}
    elif template == "renewal_reminder":
        portal_url = f"{_public_web_url()}/profile"
        renewal_date_str = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%B %-d, %Y")
        subject = "Heads up — your Ascendra PATHFINDER renews in 7 days"
        preheader = "Renewal in 7 days · $19.99 monthly"
        body_html = f"""
          <h1 style="margin:0 0 6px 0;color:#FFFFFF;font-size:28px;line-height:34px;letter-spacing:-0.5px;font-weight:900;">Your plan renews in 7 days</h1>
          <p style="margin:0 0 18px 0;color:#B8B8C2;font-size:15px;line-height:22px;">Hey {name} — quick heads up that your Ascendra <strong style="color:#FFB000;">PATHFINDER</strong> plan will automatically renew on <strong style="color:#EDEDED;">{renewal_date_str}</strong>. No action needed if you'd like to keep climbing.</p>
          <div style="margin:18px 0;padding:18px;background:#0d0d12;border:1px solid #26262E;border-radius:12px;">
            <div style="color:#7a7a85;font-size:11px;letter-spacing:1.5px;font-weight:700;">UPCOMING CHARGE</div>
            <div style="margin-top:10px;color:#EDEDED;font-size:14px;"><span style="color:#7a7a85;">Plan:</span> <strong>Ascendra PATHFINDER</strong></div>
            <div style="margin-top:6px;color:#EDEDED;font-size:14px;"><span style="color:#7a7a85;">Billing:</span> monthly</div>
            <div style="margin-top:6px;color:#EDEDED;font-size:14px;"><span style="color:#7a7a85;">Amount:</span> <strong style="color:#FFB000;">$19.99 USD</strong></div>
            <div style="margin-top:6px;color:#EDEDED;font-size:14px;"><span style="color:#7a7a85;">Charges on:</span> {renewal_date_str}</div>
          </div>
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:14px 0 22px 0;"><tr><td bgcolor="#FFB000" style="border-radius:12px;"><a href="{portal_url}" style="display:inline-block;padding:14px 26px;color:#000000;font-weight:800;font-size:15px;text-decoration:none;border-radius:12px;">Manage billing →</a></td></tr></table>
          <p style="margin:18px 0 0 0;color:#7a7a85;font-size:12px;line-height:18px;">If you cancel before {renewal_date_str}, you keep your PATHFINDER access until that date — and you won't be charged again.</p>
        """
        return {"subject": subject, "html": _shell(subject, preheader, body_html)}
    raise HTTPException(404, "Unknown template")


@api.post("/admin/email/test-send")
async def admin_email_test_send(body: EmailTestIn, admin=Depends(require_admin)):
    """Send a real email of the chosen template to the current admin (or `to`)."""
    target = body.to or admin["email"]
    dashboard_url = f"{_public_web_url()}/dashboard"
    try:
        if body.template == "password_reset":
            from email_service import send_password_reset
            reset_url = f"{_public_web_url()}/reset-password?token=PREVIEW_TEST_TOKEN"
            r = send_password_reset(to=target, name=admin.get("name"), reset_url=reset_url, expires_minutes=60)
        elif body.template == "checkout_success":
            from email_service import send_checkout_success
            r = send_checkout_success(to=target, name=admin.get("name"),
                                       tier="pathfinder", interval="annual",
                                       amount_usd=199.00, dashboard_url=dashboard_url)
        elif body.template == "invite":
            from email_service import send_invite
            r = send_invite(to=target, name=admin.get("name"),
                             temp_password="preview_temp_pass",
                             login_url=f"{_public_web_url()}/login",
                             invited_by="Ascendra Studio", tier="sage")
        elif body.template == "renewal_reminder":
            from email_service import send_renewal_reminder
            renewal_date = datetime.now(timezone.utc) + timedelta(days=7)
            r = send_renewal_reminder(
                to=target, name=admin.get("name"),
                tier="pathfinder", interval="monthly",
                renewal_date_str=renewal_date.strftime("%B %-d, %Y"),
                amount_usd=19.99,
                portal_url=f"{_public_web_url()}/profile",
                days_until=7,
            )
        else:
            raise HTTPException(400, "Unknown template")
    except HTTPException:
        raise
    except Exception as e:
        log.exception("test send failed")
        raise HTTPException(503, f"Send failed: {str(e)[:160]}")
    if not r.get("ok"):
        raise HTTPException(503, r.get("error", "Send failed"))
    return {"ok": True, "to": target, "template": body.template, "id": r.get("id"), "dry_run": r.get("dry_run", False)}


# ─── Renewal-Reminder admin endpoints ───────────────────────────────────────
class RenewalReminderSendIn(BaseModel):
    user_id: str
    force: bool = False  # bypass idempotency check (for manual re-send)


@api.post("/admin/billing/renewal-reminders/run")
async def admin_run_renewal_reminders(_admin=Depends(require_admin),
                                       min_days: float = 6.5, max_days: float = 7.5):
    """Daily/manual fallback. Scans active subs whose renewal is min_days..max_days
    away and sends the reminder email (idempotent)."""
    summary = await _scan_and_send_renewal_reminders(window_days_min=min_days, window_days_max=max_days)
    return summary


@api.post("/admin/billing/renewal-reminders/send")
async def admin_send_renewal_reminder_for_user(body: RenewalReminderSendIn, _admin=Depends(require_admin)):
    """Manually send a renewal-reminder email for a specific user (for testing)."""
    u = await users_col.find_one({"id": body.user_id}, {"_id": 0})
    if not u:
        raise HTTPException(404, "User not found")
    result = await _try_send_renewal_reminder(
        customer_id=u.get("stripe_customer_id"),
        subscription_id=u.get("stripe_subscription_id"),
        amount_usd=0.0,
        renewal_unix=None,
        source="admin_manual",
        user_override=u,
        force=body.force,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("reason", "Could not send reminder") + (f": {result.get('error','')}" if result.get('error') else ""))
    return result


# ─── SEO Studio (Programmatic Landing Pages) ────────────────────────────────
class SeoHubGenIn(BaseModel):
    model_name: str
    model_slug: Optional[str] = None
    publish: bool = False


class SeoUseCaseGenIn(BaseModel):
    model_name: str
    use_case: str
    model_slug: Optional[str] = None
    use_case_slug: Optional[str] = None
    publish: bool = False


class SeoStatusIn(BaseModel):
    status: Literal["draft", "published", "archived"]


@api.get("/seo/page/{model_slug}")
async def seo_get_page(model_slug: str):
    page = await seo_studio.get_page(db, model_slug, None)
    if not page or page.get("status") != "published":
        raise HTTPException(404, "Page not found")
    return page


@api.get("/seo/page/{model_slug}/{use_case_slug}")
async def seo_get_usecase_page(model_slug: str, use_case_slug: str):
    page = await seo_studio.get_page(db, model_slug, use_case_slug)
    if not page or page.get("status") != "published":
        raise HTTPException(404, "Page not found")
    return page


@api.get("/seo/published")
async def seo_list_published(limit: int = 200):
    """Public: enumerate published SEO pages (used by frontend index + sitemap)."""
    pages = await seo_studio.list_pages(db, status="published", limit=min(limit, 500))
    # Slim payload — exclude long body text
    slim = []
    for p in pages:
        slim.append({
            "id": p["id"],
            "kind": p.get("kind"),
            "title": p.get("title"),
            "meta_title": p.get("meta_title"),
            "meta_description": p.get("meta_description"),
            "model_slug": p["model_slug"],
            "model_name": p.get("model_name"),
            "use_case_slug": p.get("use_case_slug"),
            "use_case_name": p.get("use_case_name"),
            "published_at": p.get("published_at"),
            "updated_at": p.get("updated_at"),
        })
    return {"pages": slim, "count": len(slim)}


@api.get("/seo/sitemap.xml", response_class=Response)
async def seo_sitemap():
    pages = await seo_studio.list_pages(db, status="published", limit=2000)
    base = _public_web_url()
    xml = seo_studio.render_sitemap_xml(
        public_base=base,
        pages=pages,
        extra_paths=["/", "/pricing", "/signup", "/login", "/paths", "/models", "/tutor"],
    )
    return Response(content=xml, media_type="application/xml")


@api.get("/seo/robots.txt", response_class=PlainTextResponse)
async def seo_robots():
    base = _public_web_url()
    return PlainTextResponse(seo_studio.render_robots_txt(base))


@api.get("/admin/seo/pages")
async def admin_seo_list(_admin=Depends(require_admin), status: Optional[str] = None, limit: int = 500):
    pages = await seo_studio.list_pages(db, status=status, limit=min(limit, 1000))
    return {"pages": pages, "count": len(pages)}


@api.get("/admin/seo/page/{model_slug}")
async def admin_seo_get(model_slug: str, _admin=Depends(require_admin)):
    page = await seo_studio.get_page(db, model_slug, None)
    if not page:
        raise HTTPException(404, "Page not found")
    return page


@api.get("/admin/seo/page/{model_slug}/{use_case_slug}")
async def admin_seo_get_usecase(model_slug: str, use_case_slug: str, _admin=Depends(require_admin)):
    page = await seo_studio.get_page(db, model_slug, use_case_slug)
    if not page:
        raise HTTPException(404, "Page not found")
    return page


@api.post("/admin/seo/generate-hub")
async def admin_seo_generate_hub(body: SeoHubGenIn, _admin=Depends(require_admin)):
    try:
        page = await seo_studio.generate_hub_page(body.model_name, body.model_slug)
    except Exception as e:
        log.exception("seo hub gen failed")
        raise HTTPException(503, f"AI generation failed: {str(e)[:160]}")
    saved = await seo_studio.upsert_page(db, page, published=body.publish)
    return {"page": saved, "generated": True, "published": body.publish}


@api.post("/admin/seo/generate-usecase")
async def admin_seo_generate_usecase(body: SeoUseCaseGenIn, _admin=Depends(require_admin)):
    try:
        page = await seo_studio.generate_usecase_page(
            body.model_name, body.use_case, body.model_slug, body.use_case_slug,
        )
    except Exception as e:
        log.exception("seo usecase gen failed")
        raise HTTPException(503, f"AI generation failed: {str(e)[:160]}")
    saved = await seo_studio.upsert_page(db, page, published=body.publish)
    return {"page": saved, "generated": True, "published": body.publish}


@api.post("/admin/seo/page/{model_slug}/status")
async def admin_seo_set_status(model_slug: str, body: SeoStatusIn, _admin=Depends(require_admin)):
    page = await seo_studio.set_status(db, model_slug, None, body.status)
    if not page:
        raise HTTPException(404, "Page not found")
    return page


@api.post("/admin/seo/page/{model_slug}/{use_case_slug}/status")
async def admin_seo_set_status_usecase(model_slug: str, use_case_slug: str, body: SeoStatusIn, _admin=Depends(require_admin)):
    page = await seo_studio.set_status(db, model_slug, use_case_slug, body.status)
    if not page:
        raise HTTPException(404, "Page not found")
    return page


@api.delete("/admin/seo/page/{model_slug}")
async def admin_seo_delete(model_slug: str, _admin=Depends(require_admin)):
    ok = await seo_studio.delete_page(db, model_slug, None)
    if not ok:
        raise HTTPException(404, "Page not found")
    return {"ok": True}


@api.delete("/admin/seo/page/{model_slug}/{use_case_slug}")
async def admin_seo_delete_usecase(model_slug: str, use_case_slug: str, _admin=Depends(require_admin)):
    ok = await seo_studio.delete_page(db, model_slug, use_case_slug)
    if not ok:
        raise HTTPException(404, "Page not found")
    return {"ok": True}


# ─── Auto-Pilot Content Engine ──────────────────────────────────────────────
class AutoSettingsIn(BaseModel):
    paused: Optional[bool] = None
    auto_publish: Optional[bool] = None
    quality_threshold: Optional[int] = None
    target_path_id: Optional[str] = None
    target_module_id: Optional[str] = None


class AutoQueueItemIn(BaseModel):
    topic: str
    kind: Literal["lesson", "path"] = "lesson"
    level: Literal["Beginner", "Intermediate", "Advanced"] = "Beginner"
    model_hint: Optional[str] = None
    tier: Optional[Literal["free", "ascender", "pathfinder", "sage", "business"]] = None
    priority: Optional[int] = 9999


class AutoRunIn(BaseModel):
    kind: Literal["daily_lesson", "monday_path", "digest"]


@api.get("/admin/auto/settings")
async def admin_auto_settings(_admin=Depends(require_admin)):
    s = await auto_content.get_settings(db)
    s["next_runs"] = auto_content.next_run_times()
    return s


@api.post("/admin/auto/settings")
async def admin_update_auto_settings(body: AutoSettingsIn, _admin=Depends(require_admin)):
    patch = {k: v for k, v in body.dict().items() if v is not None}
    return await auto_content.update_settings(db, patch)


@api.get("/admin/auto/queue")
async def admin_auto_queue(_admin=Depends(require_admin), status: Optional[str] = None, limit: int = 500):
    items = await auto_content.list_queue(db, status=status, limit=min(limit, 1000))
    return {"items": items, "count": len(items)}


@api.post("/admin/auto/queue")
async def admin_auto_add_queue(body: AutoQueueItemIn, _admin=Depends(require_admin)):
    item = await auto_content.add_queue_item(db, body.dict())
    return item


@api.delete("/admin/auto/queue/{queue_id}")
async def admin_auto_remove_queue(queue_id: str, _admin=Depends(require_admin)):
    ok = await auto_content.remove_queue_item(db, queue_id)
    if not ok:
        raise HTTPException(404, "Item not found")
    return {"ok": True}


@api.get("/admin/auto/runs")
async def admin_auto_runs(_admin=Depends(require_admin), limit: int = 50):
    runs = await auto_content.list_runs(db, limit=min(limit, 200))
    return {"runs": runs, "count": len(runs)}


@api.post("/admin/auto/run")
async def admin_auto_run_manual(body: AutoRunIn, _admin=Depends(require_admin)):
    if body.kind == "daily_lesson":
        return await auto_content.run_daily_lesson(db, source="manual")
    if body.kind == "monday_path":
        return await auto_content.run_monday_path(db, source="manual")
    if body.kind == "digest":
        return await auto_content.send_daily_digest(db)
    raise HTTPException(400, "Unknown kind")



@api.post("/admin/auto/queue/auto-resolve")
async def admin_auto_resolve_queue(_admin=Depends(require_admin), max_items: int = 50):
    """Auto-resolve everything in the Auto-Pilot queue that isn't already
    published or explicitly rejected. Any 'needs_review' drafts get pushed
    live (skipping the human quality gate). Any 'failed' items get reset to
    pending + high priority so the next scheduled run picks them up.

    Returns a summary of what was processed.
    """
    published_ct = 0
    reset_ct = 0
    skipped = []
    # Fetch anything actionable
    cursor = db["content_queue"].find({
        "status": {"$in": ["needs_review", "failed"]}
    }).limit(max_items)
    items = []
    async for q in cursor:
        q.pop("_id", None)
        items.append(q)

    target_path_id, target_module_id = await auto_content._ensure_target_path(db)

    for q in items:
        st = q.get("status")
        qid = q.get("id")
        try:
            if st == "needs_review" and q.get("draft"):
                # Auto-publish the existing draft as-is
                draft = q["draft"]
                if q.get("kind") == "path":
                    outline = dict(draft)
                    outline["source"] = "auto-pilot-auto-resolved"
                    created = await _curric_create_path(db, outline)
                    await db["content_queue"].update_one(
                        {"id": qid},
                        {"$set": {"status": "published", "path_id": created["id"],
                                  "auto_resolved_at": datetime.now(timezone.utc)}},
                    )
                else:
                    draft = dict(draft)
                    draft["source"] = "auto-pilot-auto-resolved"
                    pub = await _curric_add_lesson(db, target_path_id, target_module_id, draft)
                    await db["content_queue"].update_one(
                        {"id": qid},
                        {"$set": {
                            "status": "published",
                            "lesson_id": (pub or {}).get("id"),
                            "path_id": target_path_id,
                            "auto_resolved_at": datetime.now(timezone.utc),
                        }},
                    )
                published_ct += 1
            else:
                # Reset failed / draft-less items to pending for next scheduler cycle
                await db["content_queue"].update_one(
                    {"id": qid},
                    {"$set": {"status": "pending", "priority": -1,
                              "auto_resolved_reset_at": datetime.now(timezone.utc)}},
                )
                reset_ct += 1
        except Exception as e:
            skipped.append({"id": qid, "error": str(e)[:180]})
            log.warning(f"[auto-resolve] failed to resolve {qid}: {e}")

    return {
        "processed": len(items),
        "auto_published": published_ct,
        "reset_to_pending": reset_ct,
        "skipped": skipped,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }



@api.post("/admin/auto/queue/{queue_id}/publish")
async def admin_auto_publish_flagged(queue_id: str, _admin=Depends(require_admin)):
    """Publish a flagged-for-review draft despite a low grade (manual override)."""
    q = await db["content_queue"].find_one({"id": queue_id}, {"_id": 0})
    if not q:
        raise HTTPException(404, "Queue item not found")
    if q.get("status") != "needs_review":
        raise HTTPException(400, f"Queue item is in '{q.get('status')}' state, can only publish 'needs_review' drafts")
    draft = q.get("draft")
    if not draft:
        raise HTTPException(400, "Draft content was not preserved for this item (older run)")
    target_path_id, target_module_id = await auto_content._ensure_target_path(db)
    if q.get("kind") == "path":
        # Re-create the full path from the saved draft
        outline = draft
        outline["source"] = "auto-pilot"
        created = await _curric_create_path(db, outline)
        await db["content_queue"].update_one({"id": queue_id}, {"$set": {"status": "published", "path_id": created["id"]}})
        return {"status": "published", "path_id": created["id"], "kind": "path"}
    # lesson
    draft["source"] = "auto-pilot"
    published = await _curric_add_lesson(db, target_path_id, target_module_id, draft)
    await db["content_queue"].update_one({"id": queue_id}, {"$set": {
        "status": "published",
        "lesson_id": (published.get("id") if published else None),
        "path_id": target_path_id,
    }})
    return {"status": "published", "lesson_id": (published or {}).get("id"), "path_id": target_path_id, "kind": "lesson"}


@api.get("/admin/auto/queue/{queue_id}")
async def admin_auto_get_queue_item(queue_id: str, _admin=Depends(require_admin)):
    q = await db["content_queue"].find_one({"id": queue_id}, {"_id": 0})
    if not q:
        raise HTTPException(404, "Queue item not found")
    return q


@api.post("/admin/auto/queue/{queue_id}/regenerate")
async def admin_auto_regenerate(queue_id: str, _admin=Depends(require_admin)):
    q = await db["content_queue"].find_one({"id": queue_id}, {"_id": 0})
    if not q:
        raise HTTPException(404, "Queue item not found")
    if q.get("status") not in ("failed", "needs_review", "rejected"):
        raise HTTPException(
            400,
            f"Cannot regenerate from status '{q.get('status')}'. "
            f"Allowed: failed, needs_review, rejected.",
        )
    # Reset the item back to pending so the standard run path can grab it.
    # We force it to the front of its kind queue by setting priority = -1.
    regen_history = q.get("regen_history", []) or []
    regen_history.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "from_status": q.get("status"),
        "prior_grades": q.get("grades"),
        "prior_error": q.get("error"),
    })
    await db["content_queue"].update_one(
        {"id": queue_id},
        {
            "$set": {
                "status": "pending",
                "priority": -1,  # jump to head of queue
                "regen_history": regen_history,
                "regen_count": int(q.get("regen_count", 0)) + 1,
                "updated_at": datetime.now(timezone.utc),
            },
            "$unset": {"error": "", "draft": "", "grades": ""},
        },
    )
    # Immediately run generation for this specific kind so the operator sees
    # results without waiting for the next scheduled tick.
    kind = q.get("kind", "lesson")
    try:
        if kind == "path":
            result = await auto_content.run_monday_path(db, source="manual:regenerate", force=True)
        else:
            result = await auto_content.run_daily_lesson(db, source="manual:regenerate")
        # Pull the fresh state so the UI gets the new grades/draft.
        fresh = await db["content_queue"].find_one({"id": queue_id}, {"_id": 0})
        return {"ok": True, "run": result, "item": fresh}
    except Exception as e:
        from llm_retry import is_transient_llm_error, friendly_llm_error
        log.exception("regenerate failed")
        # Keep the queue item visible for another retry. We already reset it to
        # 'pending' above, but the generator may have transitioned it to failed.
        # Surface a clean message to the operator rather than a stack trace.
        msg = friendly_llm_error(e)
        status_code = 503 if is_transient_llm_error(e) else 502
        raise HTTPException(status_code, msg)


class QueueRejectIn(BaseModel):
    reason: Optional[str] = None


@api.post("/admin/auto/queue/{queue_id}/reject")
async def admin_auto_reject(queue_id: str, body: QueueRejectIn,
                              _admin=Depends(require_admin)):
    """Reject a queue item (audit-friendly delete).

    Keeps the queue row for posterity (so we can show audit history)
    but marks status=rejected so it stops cluttering the active queue.
    """
    q = await db["content_queue"].find_one({"id": queue_id}, {"_id": 0})
    if not q:
        raise HTTPException(404, "Queue item not found")
    await db["content_queue"].update_one(
        {"id": queue_id},
        {"$set": {
            "status": "rejected",
            "reject_reason": (body.reason or "").strip()[:500] or None,
            "rejected_at": datetime.now(timezone.utc),
        }},
    )
    return {"ok": True, "status": "rejected"}


class QueueDraftEditIn(BaseModel):
    title: Optional[str] = None
    body_text: Optional[str] = None  # raw body override (replaces all cards)
    cards: Optional[list] = None     # full cards array override


@api.patch("/admin/auto/queue/{queue_id}/draft")
async def admin_auto_edit_draft(queue_id: str, body: QueueDraftEditIn,
                                  _admin=Depends(require_admin)):
    """Manually tweak a NEEDS_REVIEW draft before publishing it."""
    q = await db["content_queue"].find_one({"id": queue_id}, {"_id": 0})
    if not q:
        raise HTTPException(404, "Queue item not found")
    if q.get("status") != "needs_review":
        raise HTTPException(400, "Can only edit drafts in 'needs_review' state")
    draft = q.get("draft") or {}
    if not draft:
        raise HTTPException(400, "No draft attached to this queue item")
    if body.title is not None:
        draft["title"] = body.title.strip()[:200]
    if body.cards is not None:
        draft["cards"] = body.cards
    elif body.body_text is not None:
        # Convert a single body string into one card so the editor stays simple.
        draft["cards"] = [{
            "id": "body",
            "kind": "text",
            "title": draft.get("title", "Lesson"),
            "body": body.body_text.strip()[:8000],
        }]
    draft["edited_by_admin_at"] = datetime.now(timezone.utc).isoformat()
    await db["content_queue"].update_one(
        {"id": queue_id},
        {"$set": {"draft": draft, "updated_at": datetime.now(timezone.utc)}},
    )
    return {"ok": True, "draft": draft}


# ─── Lead capture + Lifecycle ─────────────────────────────────────────────
class LeadCaptureIn(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    source: Optional[str] = "landing"


class LifecycleRunIn(BaseModel):
    kind: Literal["drip", "trial_ending", "winback", "streak_saver", "annual_upsell", "all"] = "all"


@api.post("/leads")
async def capture_lead(body: LeadCaptureIn):
    """Public: capture a lead email + send the lead magnet immediately."""
    lead = await lifecycle.capture_lead(db, body.email, body.name, body.source)
    # Fire-and-forget lead-magnet send
    try:
        await lifecycle.send_lead_magnet_email(db, body.email, body.name)
    except Exception as e:
        log.exception(f"lead magnet send failed: {e}")
    return {"ok": True, "lead_id": lead["id"], "email": lead["email"]}


@api.get("/admin/leads")
async def admin_list_leads(_admin=Depends(require_admin), limit: int = 500):
    col = db["leads"]
    cur = col.find({}, {"_id": 0}).sort("created_at", -1).limit(min(limit, 1000))
    leads = await cur.to_list(min(limit, 1000))
    return {"leads": leads, "count": len(leads)}


@api.post("/admin/lifecycle/run")
async def admin_run_lifecycle(body: LifecycleRunIn, _admin=Depends(require_admin)):
    """Manually trigger lifecycle email scans (normally runs daily at 09:00 UTC)."""
    if body.kind == "all":
        return await lifecycle.run_all_lifecycle(db)
    if body.kind == "drip":
        return await lifecycle.scan_welcome_drip(db)
    if body.kind == "trial_ending":
        return await lifecycle.scan_trial_ending(db)
    if body.kind == "winback":
        return await lifecycle.scan_winback(db)
    if body.kind == "streak_saver":
        return await lifecycle.scan_streak_saver(db)
    if body.kind == "annual_upsell":
        return await lifecycle.scan_annual_upsell(db)
    raise HTTPException(400, "Unknown kind")


# ─── Social Studio (Phase 11) ───────────────────────────────────────────────
class SocialGenerateIn(BaseModel):
    path_id: str
    module_id: str
    lesson_id: str
    include_video: bool = True


@api.get("/admin/social/posts")
async def admin_list_social_posts(_admin=Depends(require_admin), status: Optional[str] = None, limit: int = 100):
    posts = await social_studio.list_posts(db, status=status, limit=limit)
    return {"posts": posts, "count": len(posts)}


@api.get("/admin/social/post/{post_id}")
async def admin_get_social_post(post_id: str, _admin=Depends(require_admin)):
    p = await social_studio.get_post(db, post_id)
    if not p:
        raise HTTPException(404, "Post not found")
    # Strip binary blobs from response
    p.pop("slide_png_bytes", None)
    p.pop("mp4_bytes", None)
    return p


@api.get("/admin/social/post/{post_id}/slide/{slide_idx}.png", response_class=Response)
async def admin_get_social_slide(post_id: str, slide_idx: int, _admin=Depends(require_admin)):
    png = await social_studio.get_slide_bytes(db, post_id, slide_idx)
    if not png:
        raise HTTPException(404, "Slide not found")
    return Response(content=png, media_type="image/png")


@api.get("/admin/social/post/{post_id}/video.mp4", response_class=Response)
async def admin_get_social_mp4(post_id: str, _admin=Depends(require_admin)):
    mp4 = await social_studio.get_mp4_bytes(db, post_id)
    if not mp4:
        raise HTTPException(404, "Video not found for this post")
    return Response(content=mp4, media_type="video/mp4")


@api.post("/admin/social/generate")
async def admin_generate_social(body: SocialGenerateIn, _admin=Depends(require_admin)):
    """Generate social content (tweets + carousel + MP4) for a specific lesson."""
    path = await _curric_get_path(db, body.path_id)
    if not path:
        raise HTTPException(404, "Path not found")
    lesson = None
    for m in path.get("modules", []):
        if m["id"] == body.module_id:
            for lsn in m.get("lessons", []):
                if lsn["id"] == body.lesson_id:
                    lesson = lsn
                    break
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    try:
        post = await social_studio.generate_post_for_lesson(
            db, lesson, path_title=path.get("title"),
            path_id=body.path_id, lesson_id=body.lesson_id,
            include_video=body.include_video,
        )
        return {"post": post, "ok": True}
    except Exception as e:
        log.exception("social generate failed")
        raise HTTPException(503, f"Generation failed: {str(e)[:160]}")


@api.delete("/admin/social/post/{post_id}")
async def admin_delete_social_post(post_id: str, _admin=Depends(require_admin)):
    ok = await social_studio.delete_post(db, post_id)
    if not ok:
        raise HTTPException(404, "Post not found")
    return {"ok": True}


# ─── Platform Settings (unified config status) ────────────────────────────
@api.get("/admin/social/settings")
async def admin_social_settings(_admin=Depends(require_admin)):
    """Report which platform API credentials are configured in .env.
    Returns per-platform status for the Distribution Panel and Settings page.
    """
    # X — fully wired for auto-posting
    x_configured = x_publisher.is_configured()
    x_verify = x_publisher.verify_credentials() if x_configured else {"ok": False}

    # Meta (Facebook + Instagram) — App-level config lives in env.
    # Page/IG access tokens are obtained via OAuth flow and stored in Mongo.
    meta_app_ready = meta_publisher.is_app_configured()

    # TikTok — App-level config in env. Access tokens via OAuth, stored in Mongo.
    tiktok_app_ready = tiktok_publisher.is_app_configured()

    return {
        "x": {
            "configured": x_configured,
            "verified": x_verify.get("ok", False),
            "handle": x_publisher.handle() if x_configured else None,
            "screen_name": x_verify.get("screen_name"),
            "auto_post": bool(x_configured and x_verify.get("ok")),
            "capabilities": ["thread", "images", "auto_post"],
            "env_keys": ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN",
                         "X_ACCESS_TOKEN_SECRET", "X_HANDLE"],
        },
        "facebook": {
            "configured": meta_app_ready,
            "verified": meta_app_ready,
            "auto_post": meta_app_ready,
            "capabilities": ["text", "image", "carousel", "auto_post"],
            "env_keys": ["META_APP_ID", "META_APP_SECRET", "META_REDIRECT_URI"],
        },
        "instagram": {
            "configured": meta_app_ready,
            "verified": meta_app_ready,
            "auto_post": meta_app_ready,
            "capabilities": ["image", "carousel", "reels", "auto_post"],
            "env_keys": ["META_APP_ID", "META_APP_SECRET", "META_REDIRECT_URI"],
        },
        "tiktok": {
            "configured": tiktok_app_ready,
            "verified": tiktok_app_ready,
            "auto_post": tiktok_app_ready,
            "capabilities": ["video", "auto_post"],
            "env_keys": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET",
                         "TIKTOK_REDIRECT_URI"],
        },
    }


# ─── X (Twitter) auto-posting ─────────────────────────────────────────────
@api.get("/admin/social/x/status")
async def admin_x_status(_admin=Depends(require_admin)):
    """Verify the X credentials work + show which account they belong to."""
    return {**x_publisher.verify_credentials(), "handle": x_publisher.handle(),
            "configured": x_publisher.is_configured()}


@api.get("/admin/social/x/budget")
async def admin_x_budget(_admin=Depends(require_admin)):
    """Return current Free-tier budget usage (monthly + daily post counters)."""
    return await x_publisher.get_budget(db)


class XTestPostIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=270)
    dry_run: bool = False


@api.post("/admin/social/x/test-post")
async def admin_x_test_post(body: XTestPostIn, _admin=Depends(require_admin)):
    """Post a single canned tweet for verification. No media, no thread.
    Pass dry_run=true to only verify credentials without actually posting.
    """
    if not x_publisher.is_configured():
        raise HTTPException(400, "X is not configured. Add credentials to .env first.")
    if body.dry_run:
        v = x_publisher.verify_credentials()
        if not v.get("ok"):
            raise HTTPException(502, f"Credentials invalid: {v.get('error')}")
        return {"ok": True, "dry_run": True, "would_post": body.text,
                "as": v.get("screen_name"), "verified": True}
    # Real post → check free-tier budget first
    reason = await x_publisher.check_budget_or_reason(db, needed=1)
    if reason:
        raise HTTPException(429, reason)
    result = x_publisher.post_thread(tweets=[body.text], image_bytes_list=None, hashtags=None)
    if not result.get("ok"):
        # If X itself rejected us for quota, mark with 429
        code = 429 if result.get("quota_error") else 502
        raise HTTPException(code, result.get("error", "X posting failed"))
    await x_publisher.log_tweets_posted(db, result.get("count", 1),
                                          result.get("tweet_ids", []),
                                          source="test")
    return {**result, "budget_after": await x_publisher.get_budget(db)}


@api.post("/admin/social/post/{post_id}/post-to-x")
async def admin_post_to_x(post_id: str, _admin=Depends(require_admin)):
    """Post the saved tweet thread + slide images to X."""
    post = await social_studio.get_post(db, post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    tweets = post.get("tweets") or []
    if not tweets:
        raise HTTPException(400, "No tweets in this post")
    if post.get("platforms", {}).get("twitter") == "posted":
        raise HTTPException(400, "Already posted to X. Delete the post first to re-post.")
    # Free-tier budget check: we need `len(tweets)` slots (each tweet counts as 1)
    reason = await x_publisher.check_budget_or_reason(db, needed=len(tweets))
    if reason:
        raise HTTPException(429, reason)
    # Pull image bytes (first 4 slides — X limit)
    image_bytes = []
    for i in range(min(4, post.get("slide_count") or 0)):
        b = await social_studio.get_slide_bytes(db, post_id, i)
        if b:
            image_bytes.append(b)
    result = x_publisher.post_thread(
        tweets=tweets,
        image_bytes_list=image_bytes,
        hashtags=post.get("hashtags") or [],
    )
    # Log any tweets that DID make it out before an error, so budget stays accurate
    if result.get("tweet_ids"):
        await x_publisher.log_tweets_posted(
            db, len(result["tweet_ids"]), result["tweet_ids"],
            source="social_post", post_id=post_id,
        )
    if not result.get("ok"):
        code = 429 if result.get("quota_error") else 502
        raise HTTPException(code, result.get("error", "X posting failed"))
    # Mark posted
    col = await social_studio._col(db)
    await col.update_one({"id": post_id}, {"$set": {
        "platforms.twitter": "posted",
        "x_tweet_ids": result["tweet_ids"],
        "x_first_url": result["first_url"],
        "x_posted_at": datetime.now(timezone.utc),
    }})
    return {**result, "budget_after": await x_publisher.get_budget(db)}


# ─── Meta (Facebook Page + Instagram Business) auto-posting (Phase B) ────
class _OAuthStateStore:
    """Small helper to store OAuth state / PKCE verifier in-memory + Mongo.

    We keep it in Mongo (collection oauth_states) so restarts don't kill flows in progress.
    """
    col_name = "oauth_states"


async def _oauth_save(admin_id: str, provider: str, state: str, extra: Optional[dict] = None) -> None:
    doc = {
        "admin_id": admin_id, "provider": provider, "state": state,
        "extra": extra or {}, "created_at": datetime.now(timezone.utc),
    }
    await db[_OAuthStateStore.col_name].insert_one(doc)
    # Clean up stale states (>15 min old)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    await db[_OAuthStateStore.col_name].delete_many({"created_at": {"$lt": cutoff}})


async def _oauth_consume(state: str, provider: str) -> Optional[dict]:
    doc = await db[_OAuthStateStore.col_name].find_one_and_delete(
        {"state": state, "provider": provider}
    )
    if not doc:
        return None
    return doc


@api.get("/admin/social/meta/auth-url")
async def admin_meta_auth_url(admin=Depends(require_admin)):
    """Return the URL to redirect the admin to for Meta OAuth."""
    if not meta_publisher.is_app_configured():
        raise HTTPException(400, "Meta app not configured. Set META_APP_ID / META_APP_SECRET / META_REDIRECT_URI in backend .env, then restart backend.")
    state = secrets.token_urlsafe(24)
    await _oauth_save(admin["id"], "meta", state)
    return {"url": meta_publisher.build_auth_url(state), "state": state}


@api.get("/social/meta/callback")
async def meta_oauth_callback(code: Optional[str] = None, state: Optional[str] = None,
                                error: Optional[str] = None, error_reason: Optional[str] = None):
    """Meta redirects the admin's browser here after they grant permissions.

    We accept unauthenticated, look up the pre-stored state to know which admin this belongs to,
    then exchange the code and store credentials. This is public (as required by OAuth), but
    protected by the state parameter (single-use, 15-min TTL, CSRF-proof).
    """
    if error:
        # Redirect back to settings with error banner
        return _oauth_redirect_html("meta", ok=False, msg=f"{error}: {error_reason or ''}")
    if not code or not state:
        return _oauth_redirect_html("meta", ok=False, msg="Missing code or state")
    entry = await _oauth_consume(state, "meta")
    if not entry:
        return _oauth_redirect_html("meta", ok=False, msg="Invalid or expired OAuth state")
    try:
        result = await meta_publisher.exchange_code_and_store(db, entry["admin_id"], code)
        return _oauth_redirect_html("meta", ok=True,
                                     msg=f"Connected Page: {result.get('fb_page_name')}"
                                          + (" + Instagram" if result.get("ig_business_id") else ""))
    except Exception as e:
        log.exception("Meta OAuth callback failed")
        return _oauth_redirect_html("meta", ok=False, msg=str(e)[:400])


@api.get("/admin/social/meta/status")
async def admin_meta_status(admin=Depends(require_admin)):
    creds = await meta_publisher.get_credentials(db, admin["id"])
    if not creds:
        return {"connected": False}
    v = await meta_publisher.verify_connection(db, admin["id"])
    return {
        "connected": True,
        "verified": v.get("ok"),
        "fb_page_id": creds.get("fb_page_id"),
        "fb_page_name": creds.get("fb_page_name"),
        "ig_business_id": creds.get("ig_business_id"),
        "connected_at": creds.get("connected_at"),
        "expires_at": creds.get("expires_at"),
        "verify": v,
    }


@api.post("/admin/social/meta/disconnect")
async def admin_meta_disconnect(admin=Depends(require_admin)):
    ok = await meta_publisher.disconnect(db, admin["id"])
    return {"ok": ok}


def _build_signed_urls_for_post(post: dict, request: Request) -> tuple:
    """Return (image_urls: list, video_url: str|None) signed for external pull."""
    # Prefer explicit PUBLIC_BASE_URL env for signing (in case ingress rewrites host)
    base = os.environ.get("PUBLIC_BASE_URL", "").strip() or str(request.base_url).rstrip("/")
    slide_count = int(post.get("slide_count") or 0)
    imgs = [social_media_signer.make_slide_url(base, post["id"], i) for i in range(slide_count)]
    video = social_media_signer.make_video_url(base, post["id"]) if post.get("has_video") else None
    return imgs, video


@api.post("/admin/social/post/{post_id}/post-to-facebook")
async def admin_post_to_facebook(post_id: str, request: Request, admin=Depends(require_admin)):
    post = await social_studio.get_post(db, post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    if post.get("platforms", {}).get("facebook") == "posted":
        raise HTTPException(400, "Already posted to Facebook.")
    caption = (post.get("caption") or "").strip()
    hashtags = " ".join(post.get("hashtags") or [])
    if hashtags:
        caption = f"{caption}\n\n{hashtags}" if caption else hashtags
    image_urls, _ = _build_signed_urls_for_post(post, request)
    result = await meta_publisher.post_to_facebook_page(
        db, admin["id"], caption=caption, image_urls=image_urls,
    )
    if not result.get("ok"):
        raise HTTPException(502, result.get("error", "Facebook post failed"))
    col = await social_studio._col(db)
    await col.update_one({"id": post_id}, {"$set": {
        "platforms.facebook": "posted",
        "fb_post_id": result.get("post_id"),
        "fb_post_url": result.get("url"),
        "fb_posted_at": datetime.now(timezone.utc),
    }})
    return result


@api.post("/admin/social/post/{post_id}/post-to-instagram")
async def admin_post_to_instagram(post_id: str, request: Request,
                                    as_reel: bool = False, admin=Depends(require_admin)):
    post = await social_studio.get_post(db, post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    if post.get("platforms", {}).get("instagram") == "posted":
        raise HTTPException(400, "Already posted to Instagram.")
    caption = (post.get("caption") or "").strip()
    hashtags = " ".join(post.get("hashtags") or [])
    if hashtags:
        caption = f"{caption}\n\n{hashtags}" if caption else hashtags
    image_urls, video_url = _build_signed_urls_for_post(post, request)
    if as_reel and video_url:
        result = await meta_publisher.post_to_instagram(
            db, admin["id"], caption=caption, video_url=video_url, as_reel=True,
        )
    else:
        result = await meta_publisher.post_to_instagram(
            db, admin["id"], caption=caption, image_urls=image_urls,
        )
    if not result.get("ok"):
        raise HTTPException(502, result.get("error", "Instagram post failed"))
    col = await social_studio._col(db)
    await col.update_one({"id": post_id}, {"$set": {
        "platforms.instagram": "posted",
        "ig_post_id": result.get("post_id"),
        "ig_post_url": result.get("url"),
        "ig_posted_at": datetime.now(timezone.utc),
    }})
    return result


# ─── TikTok Content Posting API (Phase B) ────────────────────────────────
@api.get("/admin/social/tiktok/auth-url")
async def admin_tiktok_auth_url(admin=Depends(require_admin)):
    if not tiktok_publisher.is_app_configured():
        raise HTTPException(400, "TikTok app not configured. Set TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET / TIKTOK_REDIRECT_URI in backend .env, then restart backend.")
    state = secrets.token_urlsafe(24)
    verifier, challenge = tiktok_publisher.make_pkce()
    await _oauth_save(admin["id"], "tiktok", state, extra={"code_verifier": verifier})
    return {"url": tiktok_publisher.build_auth_url(state, challenge), "state": state}


@api.get("/social/tiktok/callback")
async def tiktok_oauth_callback(code: Optional[str] = None, state: Optional[str] = None,
                                  error: Optional[str] = None, error_description: Optional[str] = None):
    if error:
        return _oauth_redirect_html("tiktok", ok=False, msg=f"{error}: {error_description or ''}")
    if not code or not state:
        return _oauth_redirect_html("tiktok", ok=False, msg="Missing code or state")
    entry = await _oauth_consume(state, "tiktok")
    if not entry:
        return _oauth_redirect_html("tiktok", ok=False, msg="Invalid or expired OAuth state")
    verifier = (entry.get("extra") or {}).get("code_verifier")
    if not verifier:
        return _oauth_redirect_html("tiktok", ok=False, msg="Missing PKCE verifier")
    try:
        result = await tiktok_publisher.exchange_code_and_store(db, entry["admin_id"], code, verifier)
        return _oauth_redirect_html("tiktok", ok=True, msg=f"Connected TikTok ({result.get('open_id','')[:8]}…)")
    except Exception as e:
        log.exception("TikTok OAuth callback failed")
        return _oauth_redirect_html("tiktok", ok=False, msg=str(e)[:400])


@api.get("/admin/social/tiktok/status")
async def admin_tiktok_status(admin=Depends(require_admin)):
    creds = await tiktok_publisher.get_credentials(db, admin["id"], refresh=False)
    if not creds:
        return {"connected": False}
    v = await tiktok_publisher.verify_connection(db, admin["id"])
    return {
        "connected": True,
        "verified": v.get("ok"),
        "open_id": creds.get("open_id"),
        "scope": creds.get("scope"),
        "connected_at": creds.get("connected_at"),
        "token_expires_at": creds.get("token_expires_at"),
        "verify": v,
    }


@api.post("/admin/social/tiktok/disconnect")
async def admin_tiktok_disconnect(admin=Depends(require_admin)):
    ok = await tiktok_publisher.disconnect(db, admin["id"])
    return {"ok": ok}


class TikTokPostIn(BaseModel):
    privacy: str = Field(default="SELF_ONLY",
                         pattern="^(SELF_ONLY|MUTUAL_FOLLOW_FRIENDS|PUBLIC_TO_EVERYONE)$")


@api.post("/admin/social/post/{post_id}/post-to-tiktok")
async def admin_post_to_tiktok(post_id: str, body: TikTokPostIn, request: Request,
                                 admin=Depends(require_admin)):
    post = await social_studio.get_post(db, post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    if not post.get("has_video"):
        raise HTTPException(400, "This post has no video. Regenerate with video enabled.")
    if post.get("platforms", {}).get("tiktok") == "posted":
        raise HTTPException(400, "Already posted to TikTok.")
    caption = (post.get("caption") or post.get("lesson_title") or "").strip()
    hashtags = " ".join(post.get("hashtags") or [])
    if hashtags:
        caption = f"{caption}\n\n{hashtags}" if caption else hashtags
    _, video_url = _build_signed_urls_for_post(post, request)
    if not video_url:
        raise HTTPException(400, "Could not sign video URL.")
    result = await tiktok_publisher.direct_post_video(
        db, admin["id"], video_url=video_url, caption=caption, privacy=body.privacy,
    )
    if not result.get("ok"):
        raise HTTPException(502, result.get("error", "TikTok post failed"))
    col = await social_studio._col(db)
    await col.update_one({"id": post_id}, {"$set": {
        "platforms.tiktok": "posted",
        "tiktok_publish_id": result.get("publish_id"),
        "tiktok_privacy": body.privacy,
        "tiktok_posted_at": datetime.now(timezone.utc),
    }})
    return result


@api.get("/admin/social/tiktok/publish/{publish_id}/status")
async def admin_tiktok_publish_status(publish_id: str, admin=Depends(require_admin)):
    return await tiktok_publisher.fetch_publish_status(db, admin["id"], publish_id)


# ─── Signed public media endpoints (for Meta/TikTok PULL_FROM_URL) ───────
@api.get("/social/media/{token}/slide/{idx}.png", response_class=Response)
async def social_signed_slide(token: str, idx: int):
    """Public signed URL for a slide PNG. Verified via HMAC + expiry.
    Meta/TikTok servers hit these anonymously to fetch our assets.
    """
    v = social_media_signer.verify(token)
    if not v or v.get("kind") != "slide" or v.get("index") != idx:
        raise HTTPException(403, "Invalid or expired media token")
    png = await social_studio.get_slide_bytes(db, v["post_id"], idx)
    if not png:
        raise HTTPException(404, "Slide not found")
    return Response(content=png, media_type="image/png",
                     headers={"Cache-Control": "public, max-age=600"})


@api.get("/social/media/{token}/video.mp4", response_class=Response)
async def social_signed_video(token: str):
    v = social_media_signer.verify(token)
    if not v or v.get("kind") != "video":
        raise HTTPException(403, "Invalid or expired media token")
    mp4 = await social_studio.get_mp4_bytes(db, v["post_id"])
    if not mp4:
        raise HTTPException(404, "Video not found")
    return Response(content=mp4, media_type="video/mp4",
                     headers={"Cache-Control": "public, max-age=600"})


def _oauth_redirect_html(provider: str, ok: bool, msg: str) -> Response:
    """After OAuth callback, redirect the admin's browser back to the settings page
    with a query param so the frontend can show a success/error toast.
    """
    from urllib.parse import quote_plus
    base = os.environ.get("PUBLIC_FRONTEND_URL", "").strip() or "/"
    status = "success" if ok else "error"
    dest = f"{base.rstrip('/')}/admin/social/settings?connected={provider}&status={status}&msg={quote_plus(msg[:200])}"
    return Response(status_code=307, headers={"Location": dest})


# ─── Health ─────────────────────────────────────────────────────────────────
@api.get("/")
async def root():
    return {"status": "ok", "service": "ascendra-api"}


# ─── Revenue Control Center (Phase 1) ─────────────────────────────────────
revenue_mod.register_routes(db, require_admin)
api.include_router(revenue_mod.router)

# ─── Revenue Control Center (Phase 2) ─────────────────────────────────────
revenue_phase2_mod.register_routes(db, require_admin)
api.include_router(revenue_phase2_mod.router)

@app.on_event("startup")
async def _revenue_indexes():
    try:
        await revenue_mod.ensure_indexes(db)
        log.info("[revenue] indexes ensured")
    except Exception as e:
        log.warning(f"[revenue] index setup skipped: {e}")
    try:
        await revenue_phase2_mod.ensure_indexes_phase2(db)
        log.info("[revenue-phase2] indexes ensured")
    except Exception as e:
        log.warning(f"[revenue-phase2] index setup skipped: {e}")


# ─── Change password (self-service & forced-on-first-login flow) ────────────
@api.post("/auth/change-password")
async def change_password(body: ChangePasswordIn, user=Depends(current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    u = await users_col.find_one({"id": user["id"]})
    if not u:
        raise HTTPException(404, "User not found")
    if not u.get("must_change_password"):
        if not body.current_password:
            raise HTTPException(400, "Current password required")
        if not verify_pw(body.current_password, u.get("password_hash", "")):
            raise HTTPException(401, "Current password is incorrect")
    if body.current_password and verify_pw(body.new_password, u.get("password_hash", "")):
        raise HTTPException(400, "New password must be different from current")
    await users_col.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_pw(body.new_password), "must_change_password": False}},
    )
    return {"ok": True}


# ─── Forgot / Reset password ────────────────────────────────────────────────
def _public_web_url() -> str:
    return (os.environ.get("PUBLIC_WEB_URL") or "").rstrip("/") or "http://localhost:3000"


@api.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordIn, request: Request):
    email = body.email.lower().strip()
    user = await users_col.find_one({"email": email})
    if user:
        token = uuid.uuid4().hex + uuid.uuid4().hex
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await password_reset_col.insert_one({
            "token": token,
            "user_id": user["id"],
            "email": email,
            "expires_at": expires_at,
            "used_at": None,
            "created_at": datetime.now(timezone.utc),
            "ip": request.client.host if request.client else None,
        })
        reset_url = f"{_public_web_url()}/reset-password?token={token}"
        try:
            from email_service import send_password_reset
            send_password_reset(to=email, name=user.get("name"), reset_url=reset_url, expires_minutes=60)
        except Exception as e:
            log.warning(f"forgot-password email send failed: {e}")
        # In dev (no RESEND_API_KEY): expose token in response so testing can complete
        if not os.environ.get("RESEND_API_KEY"):
            return {"ok": True, "dev_reset_token": token}
    return {"ok": True}


@api.post("/auth/reset-password")
async def reset_password(body: ResetPasswordIn):
    rec = await password_reset_col.find_one({"token": body.token})
    if not rec:
        raise HTTPException(400, "Invalid or expired reset link.")
    if rec.get("used_at"):
        raise HTTPException(400, "This reset link was already used. Request a new one.")
    exp = rec.get("expires_at")
    if exp:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise HTTPException(400, "This reset link expired. Request a new one.")
    await users_col.update_one(
        {"id": rec["user_id"]},
        {"$set": {"password_hash": hash_pw(body.new_password), "must_change_password": False}},
    )
    await password_reset_col.update_one(
        {"token": body.token},
        {"$set": {"used_at": datetime.now(timezone.utc)}},
    )
    return {"ok": True}


# ─── Anonymous page-view tracking ───────────────────────────────────────────
@api.post("/track/pageview")
async def track_pageview(body: PageviewIn, request: Request):
    ua = request.headers.get("user-agent", "")[:240]
    ip = (request.client.host if request.client else "0.0.0.0")
    visitor_hash = hashlib.sha256(f"{ip}|{ua}".encode()).hexdigest()[:32]
    await pageviews_col.insert_one({
        "path": body.path[:200],
        "referrer": (body.referrer or "")[:240],
        "visitor": visitor_hash,
        "ua": ua,
        "ts": datetime.now(timezone.utc),
    })
    return {"ok": True}


# ─── Admin: stats / users / sales / traffic ─────────────────────────────────
def _serialize_user_admin(u: dict) -> dict:
    return {
        "id": u["id"],
        "email": u["email"],
        "name": u.get("name"),
        "tier": u.get("tier", "free"),
        "subscription_interval": u.get("subscription_interval"),
        "tier_expires_at": u.get("tier_expires_at"),
        "is_admin": bool(u.get("is_admin", False)),
        "has_used_trial": bool(u.get("has_used_trial", False)),
        "must_change_password": bool(u.get("must_change_password", False)),
        "auth_provider": u.get("auth_provider", "email"),
        "created_at": u.get("created_at"),
        "last_active_date": None,
        "total_xp": 0,
    }


def _real_users_filter() -> dict:
    """MongoDB filter that excludes internal test/admin accounts from analytics.

    Excluded:
      - Internal seed/test accounts (e.g. sage1@ascendraacademy.com)
      - Admin operator accounts (e.g. admin@ascendraacademy.com, any is_admin=True)

    NOTE: Free-tier real customers are NOT excluded — they are marketing leads
    that contribute to the "leads" tier breakdown and conversion funnel math.
    """
    return {
        "email": {"$not": {"$regex": TEST_EMAIL_REGEX, "$options": "i"}},
        "is_admin": {"$ne": True},
    }


async def _get_excluded_user_ids() -> list:
    """Return the list of user_ids belonging to internal/test/admin accounts.

    Used to filter joined collections (payment_sessions, progress, certificates,
    etc.) since those store user_id but not email.
    """
    cur = users_col.find(
        {"$or": [
            {"email": {"$regex": TEST_EMAIL_REGEX, "$options": "i"}},
            {"is_admin": True},
        ]},
        {"_id": 0, "id": 1},
    )
    docs = await cur.to_list(1000)
    return [d["id"] for d in docs if d.get("id")]


def _and_filters(*filters: dict) -> dict:
    """Combine two MongoDB filter dicts into one. Skips empty filters."""
    parts = [f for f in filters if f]
    if not parts:
        return {}
    if len(parts) == 1:
        return parts[0]
    return {"$and": parts}


@api.get("/admin/stats")
async def admin_stats(_admin=Depends(require_admin)):
    now = datetime.now(timezone.utc)
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)
    day_ago = now - timedelta(days=1)

    # --- Exclusion filters: keep real customers + real leads only ----------
    # Admin/test seed accounts must NOT inflate metrics. Free-tier real users
    # ARE included (they are marketing leads).
    real_users = _real_users_filter()
    excluded_ids = await _get_excluded_user_ids()
    not_excluded_user_id = {"user_id": {"$nin": excluded_ids}} if excluded_ids else {}

    user_count = await users_col.count_documents(real_users)
    tier_breakdown = {}
    for tier in ["free", "ascender", "pathfinder", "sage", "business"]:
        tier_breakdown[tier] = await users_col.count_documents(
            _and_filters(real_users, {"tier": tier})
        )
    paid_count = user_count - tier_breakdown.get("free", 0)
    conversion = (paid_count / user_count * 100) if user_count else 0
    signups_30d = await users_col.count_documents(
        _and_filters(real_users, {"created_at": {"$gte": month_ago}})
    )

    # Aggregate revenue server-side in one query (was: load up to 10,000 docs into memory)
    # Exclude payment_sessions belonging to internal/admin/test user_ids.
    _rev_match: dict = {"status": "paid"}
    if excluded_ids:
        _rev_match["user_id"] = {"$nin": excluded_ids}
    _rev_pipeline = [
        {"$match": _rev_match},
        {"$addFields": {
            "amt": {"$cond": [
                {"$and": [
                    {"$ne": [{"$type": "$amount_usd"}, "missing"]},
                    {"$ne": ["$amount_usd", None]},
                ]},
                {"$toDouble": "$amount_usd"},
                {"$divide": [{"$toDouble": {"$ifNull": ["$amount_cents", 0]}}, 100.0]},
            ]},
            "in_month": {"$cond": [
                {"$gte": [{"$ifNull": ["$paid_at", None]}, month_ago]},
                True, False,
            ]},
        }},
        {"$group": {
            "_id": None,
            "revenue_total": {"$sum": "$amt"},
            "revenue_mtd":  {"$sum": {"$cond": ["$in_month", "$amt", 0]}},
            "monthly_rev": {"$sum": {"$cond": [
                {"$and": ["$in_month", {"$ne": ["$interval", "annual"]}]},
                "$amt", 0,
            ]}},
            "annual_rev":  {"$sum": {"$cond": [
                {"$and": ["$in_month", {"$eq": ["$interval", "annual"]}]},
                "$amt", 0,
            ]}},
        }},
    ]
    _rev_doc = await sessions_col.aggregate(_rev_pipeline).to_list(1)
    _rev = _rev_doc[0] if _rev_doc else {}
    revenue_total = float(_rev.get("revenue_total", 0.0) or 0.0)
    revenue_mtd = float(_rev.get("revenue_mtd", 0.0) or 0.0)
    monthly_rev = float(_rev.get("monthly_rev", 0.0) or 0.0)
    annual_rev = float(_rev.get("annual_rev", 0.0) or 0.0)
    arr_estimate = monthly_rev * 12 + annual_rev
    paid_sessions_count = await sessions_col.count_documents(_rev_match)

    # Engagement metrics — exclude internal/admin/test users.
    lessons_completed = 0
    _lc_pipeline = []
    if excluded_ids:
        _lc_pipeline.append({"$match": {"user_id": {"$nin": excluded_ids}}})
    _lc_pipeline += [
        {"$project": {"_id": 0, "count": {"$size": {"$ifNull": ["$completed_lesson_ids", []]}}}},
        {"$group": {"_id": None, "total": {"$sum": "$count"}}},
    ]
    _lc_doc = await progress_col.aggregate(_lc_pipeline).to_list(1)
    lessons_completed = _lc_doc[0]["total"] if _lc_doc else 0

    # Certificates issued — also exclude internal accounts.
    certs_issued = await certs_col.count_documents(not_excluded_user_id)

    # DAU / WAU — exclude internal accounts.
    dau = await progress_col.count_documents(_and_filters(
        not_excluded_user_id,
        {"last_active_date": now.date().isoformat()},
    ))
    wau = await progress_col.count_documents(_and_filters(
        not_excluded_user_id,
        {"last_active_date": {"$gte": (now - timedelta(days=7)).date().isoformat()}},
    ))

    # Traffic (pageviews) is anonymous — visitor-hash keyed, no user_id — so
    # we leave it unfiltered. Internal QA pageviews are negligible.
    pv_total = await pageviews_col.count_documents({})
    pv_24h = await pageviews_col.count_documents({"ts": {"$gte": day_ago}})
    pv_7d = await pageviews_col.count_documents({"ts": {"$gte": week_ago}})
    uniq_pipeline = [{"$match": {"ts": {"$gte": week_ago}}},
                      {"$group": {"_id": "$visitor"}}, {"$count": "n"}]
    uniq_cur = pageviews_col.aggregate(uniq_pipeline)
    uniq_7d_doc = await uniq_cur.to_list(1)
    uniq_7d = uniq_7d_doc[0]["n"] if uniq_7d_doc else 0

    return {
        "users": {
            "total": user_count,
            "paid": paid_count,
            "conversion_pct": round(conversion, 1),
            "signups_30d": signups_30d,
            "by_tier": tier_breakdown,
        },
        "revenue": {
            "total_usd": round(revenue_total, 2),
            "mtd_usd": round(revenue_mtd, 2),
            "arr_estimate_usd": round(arr_estimate, 2),
            "paid_sessions": paid_sessions_count,
        },
        "engagement": {
            "lessons_completed": lessons_completed,
            "certificates_issued": certs_issued,
            "dau": dau,
            "wau": wau,
        },
        "traffic": {
            "pageviews_total": pv_total,
            "pageviews_24h": pv_24h,
            "pageviews_7d": pv_7d,
            "unique_visitors_7d": uniq_7d,
        },
        "filters": {
            "excludes_internal_accounts": True,
            "excluded_count": len(excluded_ids),
            "test_email_pattern": TEST_EMAIL_REGEX,
        },
    }


@api.get("/admin/users")
async def admin_users(_admin=Depends(require_admin),
                       q: Optional[str] = None,
                       tier: Optional[str] = None,
                       include_internal: bool = False,
                       limit: int = 100):
    query: dict = {}
    if q:
        query["$or"] = [{"email": {"$regex": q, "$options": "i"}},
                         {"name": {"$regex": q, "$options": "i"}}]
    if tier:
        query["tier"] = tier
    # Exclude internal test/admin accounts by default.
    if not include_internal:
        query = _and_filters(query, _real_users_filter())
    cur = users_col.find(query, {"_id": 0}).sort("created_at", -1).limit(min(limit, 500))
    users = await cur.to_list(min(limit, 500))
    user_ids = [u["id"] for u in users]
    progress_map = {}
    if user_ids:
        progress_list = await progress_col.find(
            {"user_id": {"$in": user_ids}}, {"_id": 0}
        ).to_list(len(user_ids))
        progress_map = {p["user_id"]: p for p in progress_list}
    out = []
    for u in users:
        row = _serialize_user_admin(u)
        prog = progress_map.get(u["id"])
        if prog:
            row["last_active_date"] = prog.get("last_active_date")
            row["total_xp"] = prog.get("total_xp", 0)
        out.append(row)
    return {"users": out, "total": await users_col.count_documents(query)}


@api.patch("/admin/users/{uid}")
async def admin_patch_user(uid: str, body: AdminUserPatch, admin=Depends(require_admin)):
    update: dict = {}
    for field in ("name", "email", "tier", "subscription_interval", "tier_expires_at",
                   "is_admin", "must_change_password"):
        val = getattr(body, field, None)
        if val is not None:
            update[field] = val
    if body.new_password:
        if len(body.new_password) < 6:
            raise HTTPException(400, "Password must be at least 6 characters")
        update["password_hash"] = hash_pw(body.new_password)
        update["must_change_password"] = bool(body.must_change_password) if body.must_change_password is not None else True
    if not update:
        raise HTTPException(400, "No fields to update")
    if update.get("is_admin") is False:
        if uid == admin["id"]:
            others = await users_col.count_documents({"is_admin": True, "id": {"$ne": uid}})
            if others == 0:
                raise HTTPException(400, "Cannot remove last admin")
    res = await users_col.update_one({"id": uid}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(404, "User not found")
    u = await users_col.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    return {"user": _serialize_user_admin(u)}


@api.get("/admin/sales")
async def admin_sales(_admin=Depends(require_admin),
                       include_internal: bool = False,
                       limit: int = 100):
    sales_q: dict = {"status": "paid"}
    if not include_internal:
        excluded_ids = await _get_excluded_user_ids()
        if excluded_ids:
            sales_q["user_id"] = {"$nin": excluded_ids}
    cur = sessions_col.find(sales_q, {"_id": 0}).sort("paid_at", -1).limit(min(limit, 500))
    sales = await cur.to_list(min(limit, 500))
    user_ids = list({s.get("user_id") for s in sales if s.get("user_id")})
    users_map = {}
    if user_ids:
        users_list = await users_col.find(
            {"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "email": 1, "name": 1}
        ).to_list(len(user_ids))
        users_map = {u["id"]: u for u in users_list}
    enriched = []
    for s in sales:
        u = users_map.get(s.get("user_id"), {})
        enriched.append({
            "session_id": s.get("session_id"),
            "user_id": s.get("user_id"),
            "user_email": u.get("email"),
            "user_name": u.get("name"),
            "tier": s.get("tier"),
            "interval": s.get("interval"),
            "amount_usd": (s.get("amount_usd") if s.get("amount_usd") is not None
                            else (s.get("amount_cents") or 0) / 100),
            "currency": s.get("currency", "usd"),
            "paid_at": s.get("paid_at"),
            "created_at": s.get("created_at"),
        })
    return {"sales": enriched}


@api.get("/admin/traffic")
async def admin_traffic(_admin=Depends(require_admin), days: int = 14):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    pipeline = [
        {"$match": {"ts": {"$gte": start}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$ts"}},
            "views": {"$sum": 1},
            "uniques": {"$addToSet": "$visitor"},
        }},
        {"$project": {"_id": 0, "date": "$_id", "views": 1, "uniques": {"$size": "$uniques"}}},
        {"$sort": {"date": 1}},
    ]
    daily = await pageviews_col.aggregate(pipeline).to_list(60)

    top_pipeline = [
        {"$match": {"ts": {"$gte": start}}},
        {"$group": {"_id": "$path", "views": {"$sum": 1}}},
        {"$sort": {"views": -1}},
        {"$limit": 10},
        {"$project": {"_id": 0, "path": "$_id", "views": 1}},
    ]
    top_paths = await pageviews_col.aggregate(top_pipeline).to_list(20)

    return {"daily": daily, "top_paths": top_paths, "days": days}


# ─── What's New (recent AI-generated content) ───────────────────────────────
def _collect_whats_new(paths: list, *, since: Optional[datetime] = None, limit: int = 30) -> list:
    """Flatten paths/lessons into a single timeline of AI-generated items."""
    items: list = []
    for p in paths or []:
        # The path itself
        if (p.get("source") or "").lower() == "ai-studio":
            created = p.get("created_at")
            if not since or (created and created >= since):
                items.append({
                    "type": "path",
                    "path_id": p["id"],
                    "path_title": p["title"],
                    "path_color": p.get("color", "#FFB000"),
                    "module_id": None,
                    "module_title": None,
                    "lesson_id": None,
                    "lesson_title": None,
                    "image": p.get("image"),
                    "tier": p.get("tier", "free"),
                    "created_at": created,
                })
        for m in p.get("modules", []) or []:
            for lsn in m.get("lessons", []) or []:
                if (lsn.get("source") or "").lower() == "ai-studio":
                    created = lsn.get("created_at")
                    if not since or (created and created >= since):
                        items.append({
                            "type": "lesson",
                            "path_id": p["id"],
                            "path_title": p["title"],
                            "path_color": p.get("color", "#FFB000"),
                            "module_id": m["id"],
                            "module_title": m["title"],
                            "lesson_id": lsn["id"],
                            "lesson_title": lsn["title"],
                            "image": p.get("image"),
                            "tier": p.get("tier", "free"),
                            "created_at": created,
                        })
    items.sort(key=lambda x: (x.get("created_at") or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    return items[:limit]


@api.get("/whats-new")
async def whats_new(days: int = 14, limit: int = 12, user=Depends(current_user)):
    """User-facing: recent AI-generated lessons/paths (default last 14 days)."""
    paths = await _curric_list_paths(db)
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))
    items = _collect_whats_new(paths, since=since, limit=min(limit, 50))
    return {"items": items, "days": days, "count": len(items)}


@api.get("/admin/whats-new")
async def admin_whats_new(_admin=Depends(require_admin), days: int = 30, limit: int = 100):
    """Admin: more results, broader window."""
    paths = await _curric_list_paths(db)
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 365)))
    items = _collect_whats_new(paths, since=since, limit=min(limit, 500))
    return {"items": items, "days": days, "count": len(items)}


# ─── Subscribers (active billing) ───────────────────────────────────────────
@api.get("/admin/subscribers")
async def admin_subscribers(_admin=Depends(require_admin),
                              include_canceled: bool = False,
                              include_internal: bool = False,
                              limit: int = 500):
    """Admin: list of paying subscribers w/ plan, interval, status, renewal date."""
    query: dict = {"tier": {"$in": ["ascender", "pathfinder", "sage", "business"]}}
    if not include_canceled:
        # Show users currently with a non-free tier (active OR canceled-but-still-within-period).
        # Exclude those who have been fully reverted to free already.
        pass
    if not include_internal:
        query = _and_filters(query, _real_users_filter())
    cur = users_col.find(query, {"_id": 0}).sort("created_at", -1).limit(min(limit, 1000))
    users = await cur.to_list(min(limit, 1000))
    rows = []
    now = datetime.now(timezone.utc)
    # MRR estimate
    mrr = 0.0
    for u in users:
        tier = u.get("tier")
        interval = u.get("subscription_interval") or "monthly"
        # Handle timezone-naive tier_expires_at
        tier_exp = u.get("tier_expires_at")
        if tier_exp and tier_exp.tzinfo is None:
            tier_exp = tier_exp.replace(tzinfo=timezone.utc)
        status = u.get("subscription_status") or ("active" if tier_exp and tier_exp > now else "unknown")
        if not include_canceled and status not in ("active", "trialing", "past_due", "unknown"):
            continue
        price_monthly = 0.0
        if tier in TIERS:
            if interval == "annual":
                price_monthly = float(TIERS[tier]["price_annual"]) / 12.0
            elif interval == "monthly":
                price_monthly = float(TIERS[tier]["price_monthly"])
            else:  # trial
                price_monthly = 0.0
        if status in ("active", "trialing", "past_due"):
            mrr += price_monthly
        rows.append({
            "user_id": u["id"],
            "email": u["email"],
            "name": u.get("name"),
            "tier": tier,
            "interval": interval,
            "status": status,
            "cancel_at_period_end": bool(u.get("subscription_cancel_at_period_end", False)),
            "renews_at": u.get("tier_expires_at"),
            "stripe_customer_id": u.get("stripe_customer_id"),
            "stripe_subscription_id": u.get("stripe_subscription_id"),
            "created_at": u.get("created_at"),
            "auth_provider": u.get("auth_provider", "email"),
        })
    # Counts by tier for the header
    by_tier = {"ascender": 0, "pathfinder": 0, "sage": 0, "business": 0}
    for r in rows:
        if r["tier"] in by_tier:
            by_tier[r["tier"]] += 1
    return {
        "subscribers": rows,
        "count": len(rows),
        "by_tier": by_tier,
        "mrr_usd": round(mrr, 2),
        "arr_usd": round(mrr * 12, 2),
    }


# ─── Pydantic models for Curriculum CMS ─────────────────────────────────────
class CardIn(BaseModel):
    title: str
    body: str


class QuizIn(BaseModel):
    question: str
    options: List[str]
    answer_index: int = 0
    explanation: Optional[str] = ""


class LessonUpsert(BaseModel):
    id: Optional[str] = None
    title: str
    duration_min: int = 5
    xp: int = 50
    cards: List[CardIn] = []
    quiz: QuizIn


class ModuleUpsert(BaseModel):
    id: Optional[str] = None
    title: str
    lessons: Optional[List[LessonUpsert]] = None


class PathUpsert(BaseModel):
    id: Optional[str] = None
    title: str
    subtitle: Optional[str] = ""
    tagline: Optional[str] = ""
    color: Optional[str] = "#FFB000"
    level: Optional[str] = "Beginner"
    duration: Optional[str] = "~2 hours"
    image: Optional[str] = ""
    tier: Optional[Literal["free", "ascender", "pathfinder", "sage", "business"]] = "free"
    modules: Optional[List[ModuleUpsert]] = None


class LessonGenIn(BaseModel):
    topic: str
    level: str = "Beginner"
    path_id: Optional[str] = None
    module_id: Optional[str] = None
    publish: bool = False  # if True, also inserts into the path/module


class PathGenIn(BaseModel):
    concept: str
    level: str = "Beginner"
    tier: Literal["free", "ascender", "pathfinder", "sage", "business"] = "free"
    generate_lessons: bool = False
    auto_cover: bool = True


class CoverGenIn(BaseModel):
    prompt: str
    path_id: Optional[str] = None


# ─── Curriculum CRUD (admin only) ───────────────────────────────────────────
@api.get("/admin/curriculum/paths")
async def admin_list_paths(_admin=Depends(require_admin)):
    paths = await _curric_list_paths(db, is_admin=True)
    return {"paths": paths}


# ─── User-generated path review (admin) ─────────────────────────────────────
@api.get("/admin/paths/pending-review")
async def admin_list_pending_paths(_admin=Depends(require_admin)):
    """List user-generated paths awaiting admin approve/reject."""
    paths = await _curric_list_paths_pending_review(db)
    return {"paths": [path_summary(p) for p in paths], "count": len(paths)}


class PathReviewIn(BaseModel):
    notes: Optional[str] = None
    new_tier: Optional[Literal["free", "ascender", "pathfinder", "sage", "business"]] = None


@api.post("/admin/paths/{path_id}/approve")
async def admin_approve_path(path_id: str, body: PathReviewIn,
                               _admin=Depends(require_admin)):
    """Approve a user-generated path → makes it public for all tiered users.

    Optionally re-tier (e.g., user is on Ascender but admin wants the path
    available to all paid tiers — set new_tier=ascender; or restrict to sage
    by setting new_tier=sage).
    """
    p = await _curric_get_path(db, path_id)
    if not p:
        raise HTTPException(404, "Path not found")
    if not p.get("is_user_generated"):
        raise HTTPException(400, "Only user-generated paths go through review")
    patch = {
        "visibility": "public",
        "admin_review_status": "approved",
        "admin_review_notes": (body.notes or "").strip()[:500] or None,
    }
    if body.new_tier:
        patch["tier"] = body.new_tier
    updated = await _curric_update_path(db, path_id, patch)
    # Mark related admin notifications as read
    try:
        await db["admin_notifications"].update_many(
            {"path_id": path_id, "kind": "user_path_submitted"},
            {"$set": {"read": True, "resolved_at": datetime.now(timezone.utc), "resolution": "approved"}},
        )
    except Exception:
        pass
    return {"ok": True, "path": path_summary(updated)}


@api.post("/admin/paths/{path_id}/reject")
async def admin_reject_path(path_id: str, body: PathReviewIn,
                              _admin=Depends(require_admin)):
    """Reject a user-generated path. The creator keeps private access; not public."""
    p = await _curric_get_path(db, path_id)
    if not p:
        raise HTTPException(404, "Path not found")
    if not p.get("is_user_generated"):
        raise HTTPException(400, "Only user-generated paths go through review")
    patch = {
        "visibility": "rejected",
        "admin_review_status": "rejected",
        "admin_review_notes": (body.notes or "").strip()[:500] or None,
    }
    updated = await _curric_update_path(db, path_id, patch)
    try:
        await db["admin_notifications"].update_many(
            {"path_id": path_id, "kind": "user_path_submitted"},
            {"$set": {"read": True, "resolved_at": datetime.now(timezone.utc), "resolution": "rejected"}},
        )
    except Exception:
        pass
    return {"ok": True, "path": path_summary(updated)}


@api.get("/admin/notifications")
async def admin_list_notifications(_admin=Depends(require_admin), unread_only: bool = False):
    """Admin: list of in-app notifications (e.g., user-path submissions awaiting review)."""
    q: dict = {}
    if unread_only:
        q["read"] = False
    cur = db["admin_notifications"].find(q, {"_id": 0}).sort("created_at", -1).limit(200)
    notifs = await cur.to_list(200)
    return {"notifications": notifs, "unread_count": await db["admin_notifications"].count_documents({"read": False})}


@api.post("/admin/notifications/{notif_id}/mark-read")
async def admin_mark_notification_read(notif_id: str, _admin=Depends(require_admin)):
    r = await db["admin_notifications"].update_one(
        {"id": notif_id}, {"$set": {"read": True}}
    )
    return {"ok": True, "matched": r.matched_count}


@api.get("/admin/curriculum/paths/{path_id}")
async def admin_get_path(path_id: str, _admin=Depends(require_admin)):
    p = await _curric_get_path(db, path_id)
    if not p:
        raise HTTPException(404, "Path not found")
    return p


@api.post("/admin/curriculum/paths")
async def admin_create_path(body: PathUpsert, _admin=Depends(require_admin)):
    p = await _curric_create_path(db, body.dict(exclude_none=True))
    return p


@api.patch("/admin/curriculum/paths/{path_id}")
async def admin_update_path(path_id: str, body: PathUpsert, _admin=Depends(require_admin)):
    p = await _curric_update_path(db, path_id, body.dict(exclude_none=True))
    if not p:
        raise HTTPException(404, "Path not found")
    return p


@api.delete("/admin/curriculum/paths/{path_id}")
async def admin_delete_path(path_id: str, _admin=Depends(require_admin)):
    ok = await _curric_delete_path(db, path_id)
    if not ok:
        raise HTTPException(404, "Path not found")
    return {"ok": True}


@api.post("/admin/curriculum/paths/{path_id}/modules")
async def admin_add_module(path_id: str, body: ModuleUpsert, _admin=Depends(require_admin)):
    m = await _curric_add_module(db, path_id, body.dict(exclude_none=True))
    if not m:
        raise HTTPException(404, "Path not found")
    return m


@api.patch("/admin/curriculum/paths/{path_id}/modules/{module_id}")
async def admin_update_module(path_id: str, module_id: str, body: ModuleUpsert, _admin=Depends(require_admin)):
    m = await _curric_update_module(db, path_id, module_id, body.dict(exclude_none=True))
    if not m:
        raise HTTPException(404, "Module not found")
    return m


@api.delete("/admin/curriculum/paths/{path_id}/modules/{module_id}")
async def admin_delete_module(path_id: str, module_id: str, _admin=Depends(require_admin)):
    ok = await _curric_delete_module(db, path_id, module_id)
    if not ok:
        raise HTTPException(404, "Module not found")
    return {"ok": True}


@api.post("/admin/curriculum/paths/{path_id}/modules/{module_id}/lessons")
async def admin_add_lesson(path_id: str, module_id: str, body: LessonUpsert, _admin=Depends(require_admin)):
    payload = body.dict(exclude_none=True)
    lsn = await _curric_add_lesson(db, path_id, module_id, payload)
    if not lsn:
        raise HTTPException(404, "Path/Module not found")
    return lsn


@api.patch("/admin/curriculum/paths/{path_id}/modules/{module_id}/lessons/{lesson_id}")
async def admin_update_lesson(path_id: str, module_id: str, lesson_id: str, body: LessonUpsert, _admin=Depends(require_admin)):
    lsn = await _curric_update_lesson(db, path_id, module_id, lesson_id, body.dict(exclude_none=True))
    if not lsn:
        raise HTTPException(404, "Lesson not found")
    return lsn


@api.delete("/admin/curriculum/paths/{path_id}/modules/{module_id}/lessons/{lesson_id}")
async def admin_delete_lesson(path_id: str, module_id: str, lesson_id: str, _admin=Depends(require_admin)):
    ok = await _curric_delete_lesson(db, path_id, module_id, lesson_id)
    if not ok:
        raise HTTPException(404, "Lesson not found")
    return {"ok": True}


# ─── AI Studio (admin only) ─────────────────────────────────────────────────
@api.post("/admin/ai/generate-lesson")
async def admin_generate_lesson(body: LessonGenIn, _admin=Depends(require_admin)):
    try:
        path_context = None
        if body.path_id:
            p = await _curric_get_path(db, body.path_id)
            if p:
                path_context = f"This lesson belongs to the path: {p['title']} — {p.get('tagline','')}"
        draft = await ai_studio.generate_lesson_draft(body.topic, body.level, path_context)
    except Exception as e:
        log.exception("generate-lesson failed")
        raise HTTPException(503, f"AI Studio unavailable: {str(e)[:160]}")
    inserted = None
    if body.publish and body.path_id and body.module_id:
        # tag this lesson as AI-generated for "What's New" surfacing
        draft_for_insert = dict(draft)
        draft_for_insert["source"] = "ai-studio"
        inserted = await _curric_add_lesson(db, body.path_id, body.module_id, draft_for_insert)
        if not inserted:
            raise HTTPException(404, "Path/Module not found — could not publish")
    return {"draft": draft, "published": inserted}


@api.post("/admin/ai/generate-path")
async def admin_generate_path(body: PathGenIn, _admin=Depends(require_admin)):
    try:
        outline = await ai_studio.generate_path_outline(body.concept, body.level)
    except Exception as e:
        log.exception("generate-path failed")
        raise HTTPException(503, f"AI Studio unavailable: {str(e)[:160]}")
    outline["tier"] = body.tier
    outline["source"] = "ai-studio"  # tag for What's New
    # Optionally generate cover
    if body.auto_cover:
        try:
            outline["image"] = await ai_studio.generate_cover_image(outline["title"], outline.get("id"))
        except Exception as e:
            log.warning(f"cover gen failed: {e}")
    # Persist as a new path
    created = await _curric_create_path(db, outline)

    generated_lessons = 0
    if body.generate_lessons:
        # For each module / lesson title, ask Claude to fill in the lesson body
        for m in created["modules"]:
            for lsn in m.get("lessons", []):
                try:
                    full = await ai_studio.generate_lesson_draft(
                        lsn["title"], body.level, path_context=f"{created['title']} — {created.get('tagline','')}",
                    )
                    # Keep original lesson id, replace contents
                    full["id"] = lsn["id"]
                    full["title"] = lsn["title"]
                    full["source"] = "ai-studio"
                    full["created_at"] = datetime.now(timezone.utc)
                    await _curric_update_lesson(db, created["id"], m["id"], lsn["id"], full)
                    generated_lessons += 1
                except Exception as e:
                    log.warning(f"per-lesson generation failed for {lsn['id']}: {e}")
    refreshed = await _curric_get_path(db, created["id"])
    return {"path": refreshed, "generated_lessons": generated_lessons}


@api.post("/admin/ai/refresh-lesson/{path_id}/{module_id}/{lesson_id}")
async def admin_refresh_lesson(path_id: str, module_id: str, lesson_id: str, _admin=Depends(require_admin)):
    lsn = await _curric_get_lesson(db, lesson_id)
    if not lsn or lsn.get("path_id") != path_id or lsn.get("module_id") != module_id:
        raise HTTPException(404, "Lesson not found")
    try:
        refreshed = await ai_studio.refresh_lesson(lsn)
    except Exception as e:
        log.exception("refresh-lesson failed")
        raise HTTPException(503, f"AI Studio unavailable: {str(e)[:160]}")
    updated = await _curric_update_lesson(db, path_id, module_id, lesson_id, refreshed)
    return {"lesson": updated, "refreshed": True}


@api.get("/admin/ai/scan-outdated")
async def admin_scan_outdated(_admin=Depends(require_admin)):
    """Scan all lessons for mentions of outdated AI models / tools."""
    paths = await _curric_list_paths(db)
    findings = []
    for p in paths:
        for m in p.get("modules", []):
            for lsn in m.get("lessons", []):
                text_blob = lsn.get("title", "") + "\n"
                for c in lsn.get("cards", []):
                    text_blob += (c.get("title", "") + " " + c.get("body", "") + "\n")
                q = lsn.get("quiz") or {}
                text_blob += q.get("question", "") + "\n"
                for opt in q.get("options", []):
                    text_blob += opt + "\n"
                text_blob += q.get("explanation", "")
                hits = ai_studio.scan_outdated_terms(text_blob)
                if hits:
                    findings.append({
                        "path_id": p["id"], "path_title": p["title"],
                        "module_id": m["id"], "module_title": m["title"],
                        "lesson_id": lsn["id"], "lesson_title": lsn["title"],
                        "outdated_terms": hits,
                    })
    return {"findings": findings, "count": len(findings)}


@api.post("/admin/ai/generate-cover")
async def admin_generate_cover(body: CoverGenIn, _admin=Depends(require_admin)):
    try:
        url = await ai_studio.generate_cover_image(body.prompt, body.path_id)
    except Exception as e:
        log.exception("generate-cover failed")
        raise HTTPException(503, f"Image generation failed: {str(e)[:160]}")
    if body.path_id:
        await _curric_update_path(db, body.path_id, {"image": url})
    return {"url": url}


# ─── Interactive-cards auto-generation (Claude) ────────────────────────────
import interactive_generator as _ig

_INTERACTIVE_PROGRESS = {"running": False, "upgraded": 0, "failed": 0, "total": 0,
                         "last_run_at": None, "last_result": None}


async def _run_interactive_upgrade(force: bool = False) -> dict:
    """Background-safe wrapper. Updates module-level progress state."""
    if _INTERACTIVE_PROGRESS["running"]:
        return {"already_running": True}
    _INTERACTIVE_PROGRESS["running"] = True
    _INTERACTIVE_PROGRESS["upgraded"] = 0
    _INTERACTIVE_PROGRESS["failed"] = 0
    _INTERACTIVE_PROGRESS["total"] = 0
    try:
        def _on_prog(_lid, done, total):
            _INTERACTIVE_PROGRESS["upgraded"] = done
            _INTERACTIVE_PROGRESS["total"] = total
        result = await _ig.upgrade_all_lessons(db, force=force, on_progress=_on_prog)
        _INTERACTIVE_PROGRESS["last_result"] = result
        _INTERACTIVE_PROGRESS["last_run_at"] = datetime.now(timezone.utc).isoformat()
        _INTERACTIVE_PROGRESS["upgraded"] = len(result["upgraded"])
        _INTERACTIVE_PROGRESS["failed"] = len(result["failed"])
        _INTERACTIVE_PROGRESS["total"] = result["total_attempted"]
        log.info(f"interactive upgrade: {len(result['upgraded'])}/{result['total_attempted']} upgraded "
                 f"({len(result['failed'])} failed, {len(result['skipped'])} skipped)")
        return result
    finally:
        _INTERACTIVE_PROGRESS["running"] = False


@api.post("/admin/curriculum/generate-interactive")
async def admin_generate_interactive(force: bool = False, _admin=Depends(require_admin)):
    """Trigger the Claude-powered interactive-card generator for all lessons
    that don't yet have `interactive_v: 1`. Pass `?force=true` to regenerate
    even already-upgraded lessons.

    This runs in the background — poll GET /admin/curriculum/interactive-status
    to see progress. Returns immediately with the current status.
    """
    if _INTERACTIVE_PROGRESS["running"]:
        return {"status": "already_running", **_INTERACTIVE_PROGRESS}
    asyncio.create_task(_run_interactive_upgrade(force=force))
    return {"status": "started", "force": force}


@api.get("/admin/curriculum/interactive-status")
async def admin_interactive_status(_admin=Depends(require_admin)):
    """Returns progress of the most recent interactive-card upgrade run."""
    # Add counts from DB so the admin can see current coverage at a glance
    total_lessons = 0
    interactive_lessons = 0
    async for p in db["curriculum_paths"].find({}, {"modules": 1}):
        for m in p.get("modules", []):
            for lsn in m.get("lessons", []):
                total_lessons += 1
                if int(lsn.get("interactive_v") or 0) >= 1 or any(
                    c.get("kind") in ("knowledge_check", "fill_blank", "playground")
                    for c in lsn.get("cards", [])
                ):
                    interactive_lessons += 1
    return {**_INTERACTIVE_PROGRESS,
            "coverage": {"interactive": interactive_lessons, "total": total_lessons}}


# ─── Practice Lab (Phase 20 · Try It Live + Portfolio) ────────────────────
class PracticeAttemptIn(BaseModel):
    attempt: str = Field(..., min_length=1, max_length=6000)


class PracticeInlineAttemptIn(BaseModel):
    """Attempt submission with the challenge carried inline in the request.
    Used when the practice card in a lesson embeds the full challenge definition
    (title, instruction, rubric) rather than referencing a stored challenge id.
    A stable synthetic challenge_id is derived from the challenge content so
    retries accumulate under the same id.
    """
    attempt: str = Field(..., min_length=1, max_length=6000)
    title: str
    instruction: str
    task_type: str = "prompt"
    rubric: List[Dict] = []
    lesson_id: Optional[str] = None
    path_id: Optional[str] = None


@api.get("/practice/challenges/{challenge_id}")
async def get_practice_challenge(challenge_id: str, user=Depends(current_user)):
    """Fetch a challenge by id (private view — omits solutions/master answers)."""
    ch = await practice_lab.get_challenge(db, challenge_id)
    if not ch:
        raise HTTPException(404, "Practice challenge not found")
    # Also return any prior attempts by this user so the UI can show progress
    attempts = await practice_lab.get_user_attempts_for_challenge(
        db=db, user_id=user["id"], challenge_id=challenge_id, limit=5
    )
    best = max((a for a in attempts), key=lambda a: a.get("score", 0), default=None)
    return {
        "challenge": ch,
        "attempts": attempts,
        "best_score": best.get("score", 0) if best else 0,
        "mastered": bool(best and best.get("mastered")),
    }


@api.get("/practice/challenges/lesson/{lesson_id}")
async def list_practice_challenges_for_lesson(lesson_id: str, user=Depends(current_user)):
    """List all practice challenges attached to a lesson."""
    items = await practice_lab.list_challenges_for_lesson(db, lesson_id)
    return {"lesson_id": lesson_id, "challenges": items, "count": len(items)}


@api.post("/practice/attempt")
async def submit_practice_attempt_inline(
    body: PracticeInlineAttemptIn,
    user=Depends(current_user),
):
    """Grade a practice attempt where the challenge is carried inline.
    Derives a stable challenge_id from the title+instruction so retries of the
    same challenge accumulate together and appear as one portfolio item."""
    import hashlib as _hl
    synth_id = "inline-" + _hl.sha256(
        (body.title + "||" + body.instruction).encode("utf-8")
    ).hexdigest()[:20]
    challenge = {
        "id": synth_id,
        "title": body.title,
        "instruction": body.instruction,
        "task_type": body.task_type,
        "rubric": body.rubric,
        "lesson_id": body.lesson_id,
        "path_id": body.path_id,
    }
    try:
        result = await practice_lab.grade_attempt(
            db=db, user=user, challenge=challenge, attempt_text=body.attempt
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        log.exception(f"practice grade (inline) failed: {e}")
        try:
            from llm_retry import friendly_llm_error
            raise HTTPException(503, friendly_llm_error(e))
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(500, "Could not grade attempt. Please try again.")


@api.post("/practice/challenges/{challenge_id}/attempt")
async def submit_practice_attempt(
    challenge_id: str,
    body: PracticeAttemptIn,
    user=Depends(current_user),
):
    """Grade a user's attempt on a practice challenge."""
    ch = await practice_lab.get_challenge(db, challenge_id)
    if not ch:
        raise HTTPException(404, "Practice challenge not found")
    try:
        result = await practice_lab.grade_attempt(
            db=db, user=user, challenge=ch, attempt_text=body.attempt
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        log.exception(f"practice grade failed: {e}")
        # Prefer friendly retry-oriented message from llm_retry
        try:
            from llm_retry import friendly_llm_error
            raise HTTPException(503, friendly_llm_error(e))
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(500, "Could not grade attempt. Please try again.")


@api.get("/practice/portfolio/mine")
async def get_my_portfolio(user=Depends(current_user)):
    """Return the current user's private portfolio (all mastered attempts)."""
    items = await practice_lab.get_user_portfolio(db=db, user_id=user["id"], only_public=False)
    public_count = sum(1 for i in items if i.get("is_public"))
    return {
        "items": items,
        "count": len(items),
        "public_count": public_count,
    }


@api.post("/practice/portfolio/{attempt_id}/toggle-public")
async def toggle_portfolio_public(attempt_id: str, user=Depends(current_user)):
    """Toggle a portfolio item between public and private."""
    try:
        res = await practice_lab.toggle_portfolio_item_public(
            db=db, user_id=user["id"], attempt_id=attempt_id
        )
        return res
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@api.get("/practice/portfolio/public/{user_slug}")
async def get_public_portfolio(user_slug: str):
    """Public portfolio view — no auth required. Returns only items the user
    has explicitly toggled public. Supports lookup by email or user id."""

# ─── Trophy Case (Phase 22) ────────────────────────────────────────────
STREAK_MILESTONES = [
    {"days": 7,   "name": "Week Warrior",       "icon": "flame"},
    {"days": 30,  "name": "Monthly Master",     "icon": "flame"},
    {"days": 100, "name": "Century Streak",     "icon": "flame"},
    {"days": 365, "name": "Year of Learning",   "icon": "flame"},
]
MASTERY_MILESTONES = [
    {"count": 5,   "name": "Apprentice",     "icon": "target"},
    {"count": 15,  "name": "Journeyman",     "icon": "target"},
    {"count": 30,  "name": "Master Crafter", "icon": "target"},
    {"count": 75,  "name": "Grand Master",   "icon": "target"},
]


async def _build_trophy_case(user: dict, public_only: bool = False) -> dict:
    """Aggregate every award a user has earned into one payload."""
    user_id = user["id"]

    # Certificates
    certs = []
    async for c in certs_col.find({"user_id": user_id}, {"_id": 0}).sort("issued_at", -1):
        if isinstance(c.get("issued_at"), datetime):
            c["issued_at"] = c["issued_at"].isoformat()
        certs.append(c)

    # Capstone badges (mastered capstones)
    capstone_badges = []
    async for a in db.practice_attempts.find({
        "user_id": user_id, "task_type": "capstone", "mastered": True,
    }).sort("created_at", -1):
        a.pop("_id", None)
        capstone_badges.append({
            "attempt_id": a.get("id"),
            "title": a.get("challenge_title"),
            "path_id": a.get("path_id"),
            "score": a.get("score"),
            "earned_at": a.get("created_at").isoformat() if isinstance(a.get("created_at"), datetime) else a.get("created_at"),
        })

    # Mastery medals (based on total mastered practice attempts)
    total_mastered = await db.practice_attempts.count_documents({"user_id": user_id, "mastered": True})
    mastery_medals = [
        {**m, "earned": total_mastered >= m["count"]}
        for m in MASTERY_MILESTONES
    ]

    # Streak trophies (based on longest recorded streak)
    p = user.get("progress") or {}
    longest = int(p.get("longest_streak") or p.get("streak_days") or 0)
    streak_trophies = [
        {**m, "earned": longest >= m["days"]}
        for m in STREAK_MILESTONES
    ]

    # Totals
    total_earned = (
        len(certs)
        + len(capstone_badges)
        + sum(1 for m in mastery_medals if m["earned"])
        + sum(1 for s in streak_trophies if s["earned"])
    )

    payload = {
        "certificates": certs,
        "capstone_badges": capstone_badges,
        "mastery_medals": mastery_medals,
        "streak_trophies": streak_trophies,
        "stats": {
            "total_earned": total_earned,
            "certificates": len(certs),
            "capstones": len(capstone_badges),
            "practices_mastered": total_mastered,
            "longest_streak": longest,
        },
        "user": {
            "name": user.get("name") or (user.get("email") or "").split("@")[0].title(),
            "picture": user.get("picture"),
            "member_since": (user.get("created_at").isoformat() if isinstance(user.get("created_at"), datetime) else user.get("created_at")),
        },
    }
    return payload


@api.get("/trophy-case/mine")
async def get_my_trophy_case(user=Depends(current_user)):
    """Private trophy case — the current user's own awards."""
    return await _build_trophy_case(user)


@api.get("/trophy-case/public/{user_slug}")
async def get_public_trophy_case(user_slug: str):
    """Public trophy case — no auth. Accepts email or user id as slug."""
    u = await users_col.find_one(
        {"email": user_slug.lower()},
        {"_id": 0, "id": 1, "email": 1, "name": 1, "picture": 1, "created_at": 1, "progress": 1},
    )
    if not u:
        u = await users_col.find_one(
            {"id": user_slug},
            {"_id": 0, "id": 1, "email": 1, "name": 1, "picture": 1, "created_at": 1, "progress": 1},
        )
    if not u:
        raise HTTPException(404, "User not found")
    return await _build_trophy_case(u, public_only=True)



    # Try lookup by email first (most common shareable form), then by id
    u = await users_col.find_one(
        {"email": user_slug.lower()},
        {"_id": 0, "id": 1, "email": 1, "name": 1, "picture": 1, "created_at": 1},
    )
    if not u:
        u = await users_col.find_one(
            {"id": user_slug},
            {"_id": 0, "id": 1, "email": 1, "name": 1, "picture": 1, "created_at": 1},
        )
    if not u:
        raise HTTPException(404, "User not found")

    items = await practice_lab.get_user_portfolio(db=db, user_id=u["id"], only_public=True)
    # Trim items to public-safe fields (no rubric_scores, no next_step)
    public_items = [{
        "attempt_id": it["attempt_id"],
        "challenge_title": it["challenge_title"],
        "attempt_text": it["attempt_text"],
        "score": it["score"],
        "strengths": it["strengths"],
        "ai_response": it["ai_response"],
        "created_at": it["created_at"],
    } for it in items]

    return {
        "user": {
            "name": u.get("name") or (u.get("email") or "").split("@")[0].title(),
            "picture": u.get("picture"),
            "member_since": (u.get("created_at").isoformat() if isinstance(u.get("created_at"), datetime) else u.get("created_at")),
        },
        "items": public_items,
        "count": len(public_items),
    }


# --- Admin endpoints for practice lab ----------------------------------
class PracticeChallengeIn(BaseModel):
    id: Optional[str] = None
    title: str
    instruction: str
    task_type: str = "prompt"
    success_criteria: List[str] = []
    rubric: List[Dict] = []
    seed_prompt: Optional[str] = ""
    lesson_id: Optional[str] = None
    path_id: Optional[str] = None
    order: int = 0


@api.post("/admin/practice/challenges")
async def admin_upsert_challenge(body: PracticeChallengeIn, _admin=Depends(require_admin)):
    """Create or update a practice challenge."""
    ch = await practice_lab.upsert_challenge(db, body.model_dump(exclude_none=False))
    ch.pop("_id", None)
    return ch


@api.get("/admin/practice/challenges")
async def admin_list_challenges(_admin=Depends(require_admin), limit: int = 200):
    cursor = db.practice_challenges.find({}).sort("updated_at", -1).limit(min(limit, 500))
    items = []
    async for doc in cursor:
        doc.pop("_id", None)
        items.append(doc)
    return {"challenges": items, "count": len(items)}


@api.post("/admin/practice/generate/{lesson_id}")
async def admin_generate_challenge(lesson_id: str, _admin=Depends(require_admin)):
    """Auto-generate a practice challenge from an existing lesson's content."""

# ─── Layer 2: Capstones ───────────────────────────────────────────────
@api.get("/capstones/module/{path_id}/{module_id}")
async def get_capstone_for_module(path_id: str, module_id: str, user=Depends(current_user)):
    """Return the capstone challenge for a module (if any) plus this user's status on it."""
    ch = await db.practice_challenges.find_one(
        {"path_id": path_id, "module_id": module_id, "task_type": "capstone"},
        {"_id": 0},
    )
    if not ch:
        return {"capstone": None, "mastered": False, "best_score": 0}
    attempts = await practice_lab.get_user_attempts_for_challenge(
        db=db, user_id=user["id"], challenge_id=ch["id"], limit=5
    )
    best = max((a for a in attempts), key=lambda a: a.get("score", 0), default=None)
    return {
        "capstone": ch,
        "attempts": attempts,
        "best_score": best.get("score", 0) if best else 0,
        "mastered": bool(best and best.get("mastered")),
    }


@api.get("/capstones/path/{path_id}")
async def list_path_capstones(path_id: str, user=Depends(current_user)):
    """All capstones for a path with per-capstone mastery status.
    Used by the path detail page to show 'X of Y capstones passed' + certificate progress."""
    capstones = []
    async for c in db.practice_challenges.find({"path_id": path_id, "task_type": "capstone"}, {"_id": 0}):
        # User's best attempt on this capstone
        best = await db.practice_attempts.find_one(
            {"user_id": user["id"], "challenge_id": c["id"]},
            sort=[("score", -1)],
        )
        capstones.append({
            **c,
            "mastered": bool(best and best.get("mastered")),
            "best_score": (best or {}).get("score", 0),
        })
    passed = sum(1 for c in capstones if c["mastered"])
    return {"capstones": capstones, "total": len(capstones), "passed": passed}


class CapstoneUpsertIn(BaseModel):
    id: Optional[str] = None
    title: str
    instruction: str
    success_criteria: List[str] = []
    rubric: List[Dict] = []
    path_id: str
    module_id: str


@api.post("/admin/capstones")
async def admin_upsert_capstone(body: CapstoneUpsertIn, _admin=Depends(require_admin)):
    """Create or update a capstone challenge for a module."""
    data = body.model_dump(exclude_none=False)
    data["task_type"] = "capstone"
    data["seed_prompt"] = ""
    ch = await practice_lab.upsert_challenge(db, data)
    ch.pop("_id", None)
    return ch


@api.post("/admin/capstones/generate/{path_id}/{module_id}")
async def admin_generate_capstone(
    path_id: str, module_id: str, _admin=Depends(require_admin),
):
    """Auto-design a capstone using Claude from the module's lessons."""
    path_doc = await db["curriculum_paths"].find_one({"id": path_id})
    if not path_doc:
        raise HTTPException(404, "Path not found")
    module_doc = next((m for m in path_doc.get("modules", []) if m.get("id") == module_id), None)
    if not module_doc:
        raise HTTPException(404, "Module not found")
    # Combine module title + first 2 lesson titles as context
    combined_lesson = {
        "id": f"capstone-{module_id}",
        "title": f"Module Capstone: {module_doc.get('title')}",
        "path_id": path_id,
        "cards": [{"kind": "text", "title": module_doc.get("title", ""),
                   "body": " · ".join([l.get("title","") for l in module_doc.get("lessons", [])[:6]])}],
    }
    try:
        ch = await practice_lab.auto_generate_challenge_for_lesson(db=db, lesson=combined_lesson)
        # Mark as capstone + attach module
        await db.practice_challenges.update_one(
            {"id": ch["id"]},
            {"$set": {"task_type": "capstone", "module_id": module_id, "path_id": path_id}},
        )
        ch["task_type"] = "capstone"; ch["module_id"] = module_id; ch["path_id"] = path_id
        return ch
    except Exception as e:
        log.exception("capstone generate failed")
        raise HTTPException(503, str(e)[:200])


# ─── Layer 3: Spaced Practice Drills ───────────────────────────────────
@api.get("/practice/drills/today")
async def get_today_drills(user=Depends(current_user)):
    """Return spaced-repetition drills due for this user (now or overdue).
    A drill is the challenge from a prior sub-mastery attempt, ready to retry."""
    now_utc = datetime.now(timezone.utc)
    # Find scheduled drills that are due
    due_cursor = db.practice_attempts.find({
        "user_id": user["id"],
        "drill_status": "scheduled",
        "next_review_at": {"$lte": now_utc},
    }).sort("next_review_at", 1).limit(10)
    drills = []
    seen_challenges = set()
    async for a in due_cursor:
        cid = a.get("challenge_id")
        if not cid or cid in seen_challenges:
            continue
        seen_challenges.add(cid)
        # Look up the challenge — could be a stored one, or synthesized from
        # the attempt itself (for inline challenges we only have the title).
        ch = await practice_lab.get_challenge(db, cid)
        drills.append({
            "drill_id": a.get("id"),
            "challenge_id": cid,
            "challenge_title": a.get("challenge_title") or (ch or {}).get("title", "Practice"),
            "last_score": a.get("score"),
            "scheduled_for": (a.get("next_review_at") or now_utc).isoformat() if isinstance(a.get("next_review_at"), datetime) else a.get("next_review_at"),
            "lesson_id": a.get("lesson_id"),
            "path_id": a.get("path_id"),
            "instruction": (ch or {}).get("instruction", ""),
            "rubric": (ch or {}).get("rubric", []),
            "task_type": (ch or a).get("task_type", "prompt"),
        })

    # Also count "upcoming" (scheduled but not yet due) as motivation
    upcoming = await db.practice_attempts.count_documents({
        "user_id": user["id"], "drill_status": "scheduled",
        "next_review_at": {"$gt": now_utc},
    })
    return {"drills": drills, "due_count": len(drills), "upcoming_count": upcoming}


@api.post("/practice/drills/{drill_id}/snooze")
async def snooze_drill(drill_id: str, days: int = 3, user=Depends(current_user)):
    """Push a drill's next_review_at further into the future."""
    from datetime import timedelta
    new_when = datetime.now(timezone.utc) + timedelta(days=max(1, min(days, 30)))
    r = await db.practice_attempts.update_one(
        {"id": drill_id, "user_id": user["id"]},
        {"$set": {"next_review_at": new_when}},
    )
    if not r.matched_count:
        raise HTTPException(404, "Drill not found")
    return {"snoozed_until": new_when.isoformat()}



    # Find the lesson across curriculum_paths (paths -> modules -> lessons)
    lesson = None
    async for p in db["curriculum_paths"].find({}, {"modules": 1, "id": 1}):
        for m in p.get("modules", []):
            for lsn in m.get("lessons", []):
                if lsn.get("id") == lesson_id:
                    lesson = {**lsn, "path_id": p.get("id")}
                    break
            if lesson: break
        if lesson: break
    if not lesson:
        raise HTTPException(404, f"Lesson {lesson_id} not found")
    try:
        challenge = await practice_lab.auto_generate_challenge_for_lesson(db=db, lesson=lesson)
        challenge.pop("_id", None)
        return challenge
    except Exception as e:
        log.exception(f"auto-gen practice challenge failed: {e}")
        raise HTTPException(500, f"Could not generate: {str(e)[:200]}")




# ─── Content Health / Autoscan (Phase 21) ─────────────────────────────
@api.get("/admin/content-health/scan")
async def admin_content_health_scan(
    _admin=Depends(require_admin),
    stale_days: int = 120,
    check_dead_links: bool = True,
):
    """Full read-only scan report. Doesn't modify anything."""
    r = await content_scanner.scan_all_lessons(
        db=db, stale_days=stale_days, check_dead_links=check_dead_links
    )
    return r


@api.post("/admin/content-health/run")
async def admin_content_health_run(
    _admin=Depends(require_admin),
    stale_days: int = 120,
    check_dead_links: bool = True,
    max_updates: int = 25,
):
    """Trigger scan + auto-update pipeline immediately."""
    r = await content_scanner.scan_and_auto_update(
        db=db, stale_days=stale_days, check_dead_links=check_dead_links,
        max_updates_per_run=max_updates, trigger="admin-manual",
    )
    return r


@api.get("/admin/content-health/status")
async def admin_content_health_status(_admin=Depends(require_admin)):
    return content_scanner.get_last_run_status()


@api.get("/admin/content-health/audit")
async def admin_content_health_audit(_admin=Depends(require_admin), limit: int = 100):
    cursor = db["content_audit"].find({}).sort("created_at", -1).limit(min(limit, 500))
    items = []
    async for doc in cursor:
        doc.pop("_id", None)
        # Convert datetime to iso for JSON
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        items.append(doc)
    return {"audit": items, "count": len(items)}


@api.post("/admin/content-health/revert/{history_id}")
async def admin_content_health_revert(history_id: str, _admin=Depends(require_admin)):
    try:
        r = await content_scanner.revert_lesson(db=db, history_id=history_id)
        return r
    except LookupError as e:
        raise HTTPException(404, str(e))


@api.post("/admin/content-health/update-lesson/{path_id}/{module_id}/{lesson_id}")
async def admin_content_health_update_one(
    path_id: str, module_id: str, lesson_id: str,
    _admin=Depends(require_admin),
):
    """Force-refresh a single lesson (admin-triggered, bypasses scan)."""
    # Build a minimal finding so auto_update_lesson has context
    finding = {
        "path_id": path_id, "module_id": module_id, "lesson_id": lesson_id,
        "outdated_terms": [], "is_stale": True, "dead_links": [],
    }
    try:
        r = await content_scanner.auto_update_lesson(db=db, finding=finding, trigger="admin-manual-one")
        return r
    except LookupError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        log.exception("manual auto-update failed")
        raise HTTPException(503, f"Refresh failed: {str(e)[:200]}")


# ─── Practice Lab admin controls ──────────────────────────────────────
@api.get("/admin/practice/stats")
async def admin_practice_stats(_admin=Depends(require_admin)):
    """Aggregate practice-lab statistics for the admin dashboard."""
    total_challenges = await db["practice_challenges"].count_documents({})
    total_attempts = await db["practice_attempts"].count_documents({})
    mastered = await db["practice_attempts"].count_documents({"mastered": True})
    unique_users = len(await db["practice_attempts"].distinct("user_id"))
    # Score distribution
    pipeline = [
        {"$group": {
            "_id": {
                "$switch": {
                    "branches": [
                        {"case": {"$lt": ["$score", 40]}, "then": "0-39"},
                        {"case": {"$lt": ["$score", 60]}, "then": "40-59"},
                        {"case": {"$lt": ["$score", 80]}, "then": "60-79"},
                    ],
                    "default": "80-100"
                }
            },
            "count": {"$sum": 1}
        }}
    ]
    dist_cursor = db["practice_attempts"].aggregate(pipeline)
    distribution = {"0-39": 0, "40-59": 0, "60-79": 0, "80-100": 0}
    async for d in dist_cursor:
        distribution[d["_id"]] = d["count"]

    # Recent 10 attempts
    recent = []
    async for a in db["practice_attempts"].find({}).sort("created_at", -1).limit(10):
        a.pop("_id", None)
        if isinstance(a.get("created_at"), datetime):
            a["created_at"] = a["created_at"].isoformat()
        recent.append({
            "attempt_id": a.get("id"),
            "user_email": a.get("user_email"),
            "challenge_title": a.get("challenge_title"),
            "score": a.get("score"),
            "mastered": a.get("mastered"),
            "created_at": a.get("created_at"),
        })
    return {
        "total_challenges": total_challenges,
        "total_attempts": total_attempts,
        "mastered_attempts": mastered,
        "unique_users_practicing": unique_users,
        "score_distribution": distribution,
        "recent_attempts": recent,
    }




app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated cover images under /api/static/covers
from fastapi.staticfiles import StaticFiles
STATIC_DIR = ROOT_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "covers").mkdir(exist_ok=True)
app.mount("/api/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
async def startup():
    try:
        await _curric_ensure_seeded(db)
        log.info("Curriculum DB ready.")
    except Exception as e:
        log.exception(f"Curriculum seeding failed: {e}")
    # Boot auto-pilot scheduler (daily lessons + Monday paths + daily digest)
    try:
        await auto_content.seed_default_queue(db)
        await auto_content.get_settings(db)  # ensure settings doc exists
        sched = auto_content.start_scheduler(db)
        # Register lifecycle scan on the same scheduler
        try:
            lifecycle.register_jobs(sched, db)
        except Exception as e:
            log.exception(f"Lifecycle scheduler registration failed: {e}")
        # Register weekly content-health scanner (Sun 03:00 UTC)
        try:
            content_scanner.register_scheduler(sched, db)
        except Exception as e:
            log.exception(f"Content scanner registration failed: {e}")
        # Register daily Auto-Pilot queue auto-resolver (10:20 UTC — runs 20 min
        # after the daily-lesson job. Auto-publishes any 'needs_review' drafts
        # and resets 'failed' items back to pending so nothing sits stuck.)
        try:
            async def _auto_resolve_queue_job():
                try:
                    log.info("[auto-resolve] daily auto-resolve starting")
                    target_path_id, target_module_id = await auto_content._ensure_target_path(db)
                    published = reset = 0
                    async for q in db["content_queue"].find({"status": {"$in": ["needs_review", "failed"]}}).limit(50):
                        try:
                            if q.get("status") == "needs_review" and q.get("draft"):
                                draft = q["draft"]
                                if q.get("kind") == "path":
                                    outline = dict(draft); outline["source"] = "auto-pilot-auto-resolved"
                                    created = await _curric_create_path(db, outline)
                                    await db["content_queue"].update_one({"id": q["id"]}, {"$set": {"status": "published", "path_id": created["id"], "auto_resolved_at": datetime.now(timezone.utc)}})
                                else:
                                    d = dict(draft); d["source"] = "auto-pilot-auto-resolved"
                                    pub = await _curric_add_lesson(db, target_path_id, target_module_id, d)
                                    await db["content_queue"].update_one({"id": q["id"]}, {"$set": {"status": "published", "lesson_id": (pub or {}).get("id"), "path_id": target_path_id, "auto_resolved_at": datetime.now(timezone.utc)}})
                                published += 1
                            else:
                                await db["content_queue"].update_one({"id": q["id"]}, {"$set": {"status": "pending", "priority": -1, "auto_resolved_reset_at": datetime.now(timezone.utc)}})
                                reset += 1
                        except Exception as ie:
                            log.warning(f"[auto-resolve] item {q.get('id')} failed: {ie}")
                    log.info(f"[auto-resolve] done. published={published} reset={reset}")
                except Exception as ee:
                    log.exception(f"[auto-resolve] job crashed: {ee}")

            sched.add_job(
                _auto_resolve_queue_job,
                "cron", hour=10, minute=20,
                id="auto_resolve_queue_daily", replace_existing=True,
                misfire_grace_time=3600,
            )
            log.info("[auto-resolve] daily queue auto-resolver registered (10:20 UTC)")
        except Exception as e:
            log.exception(f"Auto-resolve scheduler registration failed: {e}")
    except Exception as e:
        log.exception(f"Auto-content scheduler failed to start: {e}")

    # Background auto-upgrade: insert interactive cards into any text-only lessons.
    # Runs ONCE on startup, never blocks boot, idempotent (skips lessons already done).
    async def _bg_interactive_upgrade():
        await asyncio.sleep(8)  # let the app fully come up first
        try:
            res = await _run_interactive_upgrade(force=False)
            if res and not res.get("already_running"):
                log.info(f"startup interactive upgrade: {res}")
        except Exception as e:
            log.exception(f"startup interactive upgrade failed: {e}")
    try:
        asyncio.create_task(_bg_interactive_upgrade())
    except Exception as e:
        log.warning(f"could not schedule interactive upgrade task: {e}")


@app.on_event("shutdown")
async def shutdown():
    try:
        auto_content.stop_scheduler()
    except Exception:
        pass
    client.close()
