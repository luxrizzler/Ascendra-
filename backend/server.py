"""
AI Academy backend.
- JWT auth
- Curriculum (paths / lessons / models)
- Progress tracking (streak, XP, completed lessons)
- AI Tutor chat (Claude Sonnet 4.5 via emergentintegrations)
- Stripe checkout + webhook for tier upgrades
"""
import os
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Literal

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request, Header
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
    all_lesson_ids,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ─── Config ─────────────────────────────────────────────────────────────────
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET_KEY"]
JWT_ALGO = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXP_DAYS = 30
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
users_col = db["users"]
progress_col = db["progress"]
chats_col = db["chats"]
sessions_col = db["payment_sessions"]

# ─── App ────────────────────────────────────────────────────────────────────
app = FastAPI(title="AI Academy API")
api = APIRouter(prefix="/api")
bearer_scheme = HTTPBearer(auto_error=False)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ─── Models ─────────────────────────────────────────────────────────────────
class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: Optional[str] = None
    goal: Optional[str] = None  # career | business | creator | productivity

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    goal: Optional[str] = None
    tier: str = "free"
    created_at: datetime

class ProgressOut(BaseModel):
    completed_lesson_ids: List[str] = []
    total_xp: int = 0
    streak_days: int = 0
    last_active_date: Optional[str] = None

class CompleteLessonIn(BaseModel):
    lesson_id: str

class ChatIn(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatOut(BaseModel):
    session_id: str
    reply: str

class CheckoutIn(BaseModel):
    tier: Literal["pro", "business"]
    origin_url: str  # e.g. https://...preview.emergentagent.com

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
        "created_at": u["created_at"],
    }

# ─── Progress helpers ───────────────────────────────────────────────────────
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
    if not user or not verify_pw(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    return Token(access_token=make_token(user["id"]))

@api.get("/auth/me", response_model=UserOut)
async def me(user=Depends(current_user)):
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
    # Strip quiz answers from list view
    modules = []
    for m in p["modules"]:
        lessons = []
        for l in m["lessons"]:
            lessons.append({
                "id": l["id"],
                "title": l["title"],
                "duration_min": l["duration_min"],
                "xp": l["xp"],
                "card_count": len(l["cards"]),
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
        "modules": modules,
    }

@api.get("/lessons/{lesson_id}")
async def fetch_lesson(lesson_id: str):
    l = get_lesson(lesson_id)
    if not l:
        raise HTTPException(404, "Lesson not found")
    return l

@api.get("/models")
async def list_models():
    return {"models": AI_MODELS}

# ─── Progress routes ────────────────────────────────────────────────────────
@api.get("/progress", response_model=ProgressOut)
async def progress(user=Depends(current_user)):
    p = await get_progress(user["id"])
    return ProgressOut(
        completed_lesson_ids=p["completed_lesson_ids"],
        total_xp=p["total_xp"],
        streak_days=p["streak_days"],
        last_active_date=p["last_active_date"],
    )

@api.post("/progress/complete", response_model=ProgressOut)
async def complete_lesson(body: CompleteLessonIn, user=Depends(current_user)):
    lesson = get_lesson(body.lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    p = await get_progress(user["id"])
    today = datetime.now(timezone.utc).date().isoformat()

    if body.lesson_id not in p["completed_lesson_ids"]:
        p["completed_lesson_ids"].append(body.lesson_id)
        p["total_xp"] += lesson["xp"]

    # streak logic
    last = p["last_active_date"]
    if last != today:
        yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        if last == yesterday:
            p["streak_days"] += 1
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
    return ProgressOut(
        completed_lesson_ids=p["completed_lesson_ids"],
        total_xp=p["total_xp"],
        streak_days=p["streak_days"],
        last_active_date=p["last_active_date"],
    )

# ─── AI Tutor (Claude Sonnet 4.5) ───────────────────────────────────────────
TUTOR_SYSTEM = (
    "You are Aida, the AI Tutor for the AI Academy app. Your job is to teach people how "
    "to use AI — from absolute beginner to advanced builder. Be warm, encouraging, and "
    "concrete. Default to short, punchy answers (2–5 sentences). Use lists or step-by-step "
    "when asked 'how'. Recommend specific 2026 AI models when relevant (GPT-5.2, Claude "
    "Sonnet 4.5, Gemini 3 Pro/Flash, Nano Banana for images, Sora 2 for video, ElevenLabs "
    "for voice, Perplexity for research, Cursor for code). Never hallucinate URLs. Never "
    "refuse on safe topics. Always end with one useful follow-up question."
)

@api.post("/tutor/chat", response_model=ChatOut)
async def tutor_chat(body: ChatIn, user=Depends(current_user)):
    session_id = body.session_id or str(uuid.uuid4())
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=TUTOR_SYSTEM,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        reply = await chat.send_message(UserMessage(text=body.message))
    except Exception as e:
        log.exception("LLM call failed")
        raise HTTPException(503, f"AI Tutor unavailable: {str(e)[:120]}")

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

# ─── Pricing & Stripe ───────────────────────────────────────────────────────
TIERS = {
    "free": {
        "id": "free",
        "name": "Free",
        "price_monthly": 0,
        "blurb": "Get a real taste of the future.",
        "features": [
            "AI Fundamentals path",
            "Limited AI Tutor (5 messages/day)",
            "Browse the AI Model Library",
            "Daily streak tracking",
        ],
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "price_monthly": 19.99,
        "blurb": "For serious learners who want all 4 paths.",
        "features": [
            "All 4 learning paths (36+ lessons)",
            "Unlimited AI Tutor chat (Claude 4.5)",
            "Project-based assignments",
            "XP + leaderboards",
            "New lessons every week",
        ],
        "highlight": True,
    },
    "business": {
        "id": "business",
        "name": "Business",
        "price_monthly": 49.99,
        "blurb": "Build a business with AI — coached step-by-step.",
        "features": [
            "Everything in Pro",
            "1:1 monthly strategy call",
            "Private Slack community",
            "Pitch & MVP reviews",
            "Early access to new models",
            "Team seats (up to 5)",
        ],
    },
}

@api.get("/pricing")
async def pricing():
    return {"tiers": list(TIERS.values())}

@api.post("/billing/checkout")
async def create_checkout(body: CheckoutIn, request: Request, user=Depends(current_user)):
    if body.tier not in ("pro", "business"):
        raise HTTPException(400, "Invalid tier")
    amount_usd = TIERS[body.tier]["price_monthly"]
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
                metadata={"user_id": user["id"], "tier": body.tier},
            )
        )
    except Exception as e:
        log.exception("Stripe error")
        raise HTTPException(502, f"Stripe error: {str(e)[:140]}")

    await sessions_col.insert_one({
        "session_id": session.session_id,
        "user_id": user["id"],
        "tier": body.tier,
        "amount_usd": amount_usd,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })
    return {"url": session.url, "session_id": session.session_id}

@api.get("/billing/status/{session_id}")
async def checkout_status(session_id: str, request: Request, user=Depends(current_user)):
    """Poll endpoint — clients use this after returning from Stripe Checkout."""
    rec = await sessions_col.find_one({"session_id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Session not found")

    if rec["status"] == "pending":
        try:
            webhook_url = f"{str(request.base_url).rstrip('/')}/api/billing/webhook"
            sc = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
            s = await sc.get_checkout_status(session_id)
            if s.payment_status == "paid":
                await users_col.update_one({"id": user["id"]}, {"$set": {"tier": rec["tier"]}})
                await sessions_col.update_one(
                    {"session_id": session_id},
                    {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc)}},
                )
                rec["status"] = "paid"
        except Exception as e:
            log.warning(f"Stripe status check failed: {e}")

    return {"status": rec["status"], "tier": rec["tier"]}

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
        if uid and tier:
            await users_col.update_one({"id": uid}, {"$set": {"tier": tier}})
            await sessions_col.update_one(
                {"session_id": event.session_id},
                {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc)}},
            )
    return {"received": True}

# ─── Health ─────────────────────────────────────────────────────────────────
@api.get("/")
async def root():
    return {"status": "ok", "service": "ai-academy-api"}

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
