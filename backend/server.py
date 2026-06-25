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

from curriculum_db import (
    ensure_seeded as _curric_ensure_seeded,
    list_paths as _curric_list_paths,
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
    paths = await _curric_list_paths(db)
    return {"paths": [path_summary(p) for p in paths]}

@api.get("/paths/{path_id}")
async def get_path_detail(path_id: str):
    p = await _curric_get_path(db, path_id)
    if not p:
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
            })
        modules.append({"id": m["id"], "title": m["title"], "lessons": lessons})
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
    }

@api.get("/lessons/{lesson_id}")
async def fetch_lesson(lesson_id: str, user=Depends(current_user)):
    lsn = await _curric_get_lesson(db, lesson_id)
    if not lsn:
        raise HTTPException(404, "Lesson not found")
    p = await _curric_get_path(db, lsn["path_id"])
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
        "tier": {"$in": ["ascender", "pathfinder", "sage"]},
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
    """Handles Stripe events for both one-time payments and subscriptions."""
    payload = await request.body()
    import stripe as _stripe
    _stripe.api_key = STRIPE_API_KEY
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    try:
        if webhook_secret and stripe_signature:
            event = _stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
        else:
            import json as _json
            event = _json.loads(payload)
    except Exception as e:
        log.warning(f"webhook verify failed: {e}")
        raise HTTPException(400, "Invalid payload")

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
async def admin_subscribers(_admin=Depends(require_admin), include_canceled: bool = False, limit: int = 500):
    """Admin: list of paying subscribers w/ plan, interval, status, renewal date."""
    query: dict = {"tier": {"$in": ["ascender", "pathfinder", "sage"]}}
    if not include_canceled:
        # Show users currently with a non-free tier (active OR canceled-but-still-within-period).
        # Exclude those who have been fully reverted to free already.
        pass
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
    by_tier = {"ascender": 0, "pathfinder": 0, "sage": 0}
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
    tier: Optional[Literal["free", "ascender", "pathfinder", "sage"]] = "free"
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
    tier: Literal["free", "ascender", "pathfinder", "sage"] = "free"
    generate_lessons: bool = False
    auto_cover: bool = True


class CoverGenIn(BaseModel):
    prompt: str
    path_id: Optional[str] = None


# ─── Curriculum CRUD (admin only) ───────────────────────────────────────────
@api.get("/admin/curriculum/paths")
async def admin_list_paths(_admin=Depends(require_admin)):
    paths = await _curric_list_paths(db)
    return {"paths": paths}


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


@app.on_event("shutdown")
async def shutdown():
    client.close()
