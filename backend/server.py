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
import logging
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Literal

import bcrypt
import httpx
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest,
)

from curriculum import (
    PATHS,
    AI_MODELS,
    get_path,
    get_lesson,
    path_summary,
    can_access,
)

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
    tier: Literal["ascender", "pathfinder", "sage"]
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


def _path_lesson_index() -> dict:
    idx = {}
    for p in PATHS:
        ids = []
        for m in p["modules"]:
            for lsn in m["lessons"]:
                ids.append(lsn["id"])
        idx[p["id"]] = ids
    return idx


def _compute_path_progress(completed_ids: list) -> tuple[dict, list]:
    completed_set = set(completed_ids)
    path_progress = {}
    completed_paths = []
    for pid, lids in _path_lesson_index().items():
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


def _build_progress_out(p: dict) -> ProgressOut:
    lvl = compute_level(p.get("total_xp", 0))
    path_progress, completed_paths = _compute_path_progress(p.get("completed_lesson_ids", []))
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
    p = get_path(path_id)
    if not p:
        return None
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
    }
    await certs_col.insert_one(dict(cert))
    return cert

# ─── Auth routes ────────────────────────────────────────────────────────────
@api.post("/auth/signup", response_model=Token)
async def signup(body: SignupIn):
    existing = await users_col.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    user = {
        "id": str(uuid.uuid4()),
        "email": body.email.lower(),
        "name": body.name or body.email.split("@")[0],
        "goal": body.goal,
        "tier": "free",
        "password_hash": hash_pw(body.password),
        "created_at": datetime.now(timezone.utc),
    }
    await users_col.insert_one(user)
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
async def list_paths():
    return {"paths": [path_summary(p) for p in PATHS]}

@api.get("/paths/{path_id}")
async def get_path_detail(path_id: str):
    p = get_path(path_id)
    if not p:
        raise HTTPException(404, "Path not found")
    modules = []
    for m in p["modules"]:
        lessons = []
        for lsn in m["lessons"]:
            lessons.append({
                "id": lsn["id"],
                "title": lsn["title"],
                "duration_min": lsn["duration_min"],
                "xp": lsn["xp"],
                "card_count": len(lsn["cards"]),
            })
        modules.append({"id": m["id"], "title": m["title"], "lessons": lessons})
    return {
        "id": p["id"],
        "title": p["title"],
        "subtitle": p["subtitle"],
        "tagline": p["tagline"],
        "color": p["color"],
        "level": p["level"],
        "duration": p["duration"],
        "image": p["image"],
        "tier": p.get("tier", "free"),
        "modules": modules,
    }

@api.get("/lessons/{lesson_id}")
async def fetch_lesson(lesson_id: str, user=Depends(current_user)):
    lsn = get_lesson(lesson_id)
    if not lsn:
        raise HTTPException(404, "Lesson not found")
    p = get_path(lsn["path_id"])
    if p and not can_access(user.get("tier", "free"), p.get("tier", "free")):
        raise HTTPException(403, f"This lesson requires {p['tier'].upper()} tier. Upgrade to unlock.")
    return lsn

@api.get("/models")
async def list_models():
    return {"models": AI_MODELS}

# ─── Progress routes ────────────────────────────────────────────────────────
@api.get("/progress", response_model=ProgressOut)
async def progress(user=Depends(current_user)):
    p = await get_progress(user["id"])
    return _build_progress_out(p)

@api.post("/progress/complete", response_model=CompleteLessonOut)
async def complete_lesson(body: CompleteLessonIn, user=Depends(current_user)):
    lesson = get_lesson(body.lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    p = await get_progress(user["id"])
    today = datetime.now(timezone.utc).date().isoformat()

    awarded_xp = 0
    prev_completed_paths = set(_compute_path_progress(p["completed_lesson_ids"])[1])

    if body.lesson_id not in p["completed_lesson_ids"]:
        p["completed_lesson_ids"].append(body.lesson_id)
        p["total_xp"] += lesson["xp"]
        awarded_xp = lesson["xp"]

    last = p.get("last_active_date")
    if last != today:
        yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        if last == yesterday:
            p["streak_days"] = p.get("streak_days", 0) + 1
        else:
            p["streak_days"] = 1
        p["last_active_date"] = today

    await progress_col.update_one(
        {"user_id": user["id"]},
        {"$set": {
            "completed_lesson_ids": p["completed_lesson_ids"],
            "total_xp": p["total_xp"],
            "streak_days": p["streak_days"],
            "last_active_date": p["last_active_date"],
        }},
    )

    new_completed_paths = set(_compute_path_progress(p["completed_lesson_ids"])[1]) - prev_completed_paths
    issued_ids: list = []
    for pid in new_completed_paths:
        cert = await _issue_certificate_if_complete(user, pid)
        if cert:
            issued_ids.append(cert["id"])

    return CompleteLessonOut(
        progress=_build_progress_out(p),
        awarded_xp=awarded_xp,
        newly_completed_paths=list(new_completed_paths),
        certificates_issued=issued_ids,
    )

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

# ─── Pricing & Stripe ───────────────────────────────────────────────────────
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
}

@api.get("/pricing")
async def pricing():
    return {"tiers": list(TIERS.values())}

@api.post("/billing/checkout")
async def create_checkout(body: CheckoutIn, request: Request, user=Depends(current_user)):
    if body.tier not in TIERS:
        raise HTTPException(400, "Invalid tier")
    if body.interval == "trial":
        if user.get("has_used_trial"):
            raise HTTPException(400, "Trial already used. Pick a plan to keep going.")
        amount_usd = 2.99
        plan_name = "Sage (7-day trial)"
    elif body.interval == "annual":
        amount_usd = TIERS[body.tier]["price_annual"]
        plan_name = f"{TIERS[body.tier]['name']} (Annual)"
    else:
        amount_usd = TIERS[body.tier]["price_monthly"]
        plan_name = f"{TIERS[body.tier]['name']} (Monthly)"
    origin = body.origin_url.rstrip("/")
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
        log.exception("Stripe error")
        raise HTTPException(502, f"Stripe error: {str(e)[:140]}")

    await sessions_col.insert_one({
        "session_id": session.session_id,
        "user_id": user["id"],
        "tier": body.tier,
        "interval": body.interval,
        "amount_usd": amount_usd,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })
    return {"url": session.url, "session_id": session.session_id}

@api.get("/billing/status/{session_id}")
async def checkout_status(session_id: str, request: Request, user=Depends(current_user)):
    rec = await sessions_col.find_one({"session_id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Session not found")

    if rec["status"] == "pending":
        try:
            webhook_url = f"{str(request.base_url).rstrip('/')}/api/billing/webhook"
            sc = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
            s = await sc.get_checkout_status(session_id)
            if s.payment_status == "paid":
                interval = rec.get("interval", "monthly")
                days = {"trial": 7, "annual": 365, "monthly": 30}.get(interval, 30)
                expires_at = datetime.now(timezone.utc) + timedelta(days=days)
                granted_tier = "sage" if interval == "trial" else rec["tier"]
                update = {
                    "tier": granted_tier,
                    "subscription_interval": interval,
                    "tier_expires_at": expires_at,
                }
                if interval == "trial":
                    update["has_used_trial"] = True
                await users_col.update_one({"id": user["id"]}, {"$set": update})
                await sessions_col.update_one(
                    {"session_id": session_id},
                    {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc)}},
                )
                rec["status"] = "paid"
        except Exception as e:
            log.warning(f"Stripe status check failed: {e}")

    return {"status": rec["status"], "tier": rec["tier"], "interval": rec.get("interval", "monthly")}

@api.post("/billing/webhook")
async def stripe_webhook(request: Request, stripe_signature: Optional[str] = Header(None)):
    payload = await request.body()
    try:
        webhook_url = f"{str(request.base_url).rstrip('/')}/api/billing/webhook"
        sc = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
        event = await sc.handle_webhook(payload, stripe_signature)
    except Exception as e:
        log.warning(f"webhook parse failed: {e}")
        raise HTTPException(400, "Invalid payload")
    if getattr(event, "payment_status", None) == "paid" and getattr(event, "metadata", None):
        meta = event.metadata or {}
        uid = meta.get("user_id")
        tier = meta.get("tier")
        interval = meta.get("interval", "monthly")
        if uid and tier:
            days = {"trial": 7, "annual": 365, "monthly": 30}.get(interval, 30)
            expires_at = datetime.now(timezone.utc) + timedelta(days=days)
            granted_tier = "sage" if interval == "trial" else tier
            update = {
                "tier": granted_tier,
                "subscription_interval": interval,
                "tier_expires_at": expires_at,
            }
            if interval == "trial":
                update["has_used_trial"] = True
            await users_col.update_one({"id": uid}, {"$set": update})
            await sessions_col.update_one(
                {"session_id": event.session_id},
                {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc)}},
            )
    return {"received": True}


@api.get("/billing/info")
async def billing_info():
    return {"uses_real_stripe": False}

# ─── Health ─────────────────────────────────────────────────────────────────
@api.get("/")
async def root():
    return {"status": "ok", "service": "ascendra-api"}


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


@api.get("/admin/stats")
async def admin_stats(_admin=Depends(require_admin)):
    now = datetime.now(timezone.utc)
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)
    day_ago = now - timedelta(days=1)

    user_count = await users_col.count_documents({})
    tier_breakdown = {}
    for tier in ["free", "ascender", "pathfinder", "sage"]:
        tier_breakdown[tier] = await users_col.count_documents({"tier": tier})
    paid_count = user_count - tier_breakdown.get("free", 0)
    conversion = (paid_count / user_count * 100) if user_count else 0
    signups_30d = await users_col.count_documents({"created_at": {"$gte": month_ago}})

    paid_sessions = await sessions_col.find({"status": "paid"}, {"_id": 0}).to_list(10000)
    def _amt_usd(s):
        if "amount_usd" in s and s["amount_usd"] is not None:
            return float(s["amount_usd"])
        return float(s.get("amount_cents", 0)) / 100.0
    revenue_total = sum(_amt_usd(s) for s in paid_sessions)
    revenue_mtd = sum(_amt_usd(s) for s in paid_sessions if s.get("paid_at") and s["paid_at"] >= month_ago)
    monthly_rev = 0.0
    annual_rev = 0.0
    for s in paid_sessions:
        if s.get("paid_at") and s["paid_at"] >= month_ago:
            amt = _amt_usd(s)
            if s.get("interval") == "annual":
                annual_rev += amt
            else:
                monthly_rev += amt
    arr_estimate = monthly_rev * 12 + annual_rev

    lessons_completed = 0
    async for p in progress_col.find({}, {"completed_lesson_ids": 1}):
        lessons_completed += len(p.get("completed_lesson_ids", []))
    certs_issued = await certs_col.count_documents({})
    dau = await progress_col.count_documents({"last_active_date": now.date().isoformat()})
    wau = await progress_col.count_documents({
        "last_active_date": {"$gte": (now - timedelta(days=7)).date().isoformat()}
    })

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
            "paid_sessions": len(paid_sessions),
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
    }


@api.get("/admin/users")
async def admin_users(_admin=Depends(require_admin),
                       q: Optional[str] = None,
                       tier: Optional[str] = None,
                       limit: int = 100):
    query: dict = {}
    if q:
        query["$or"] = [{"email": {"$regex": q, "$options": "i"}},
                         {"name": {"$regex": q, "$options": "i"}}]
    if tier:
        query["tier"] = tier
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
async def admin_sales(_admin=Depends(require_admin), limit: int = 100):
    cur = sessions_col.find({"status": "paid"}, {"_id": 0}).sort("paid_at", -1).limit(min(limit, 500))
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


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    client.close()
