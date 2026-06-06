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
import httpx
import jwt
import stripe as _stripe_mod  # noqa: F401  (used by /billing/subscribe + /portal)
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
    can_access,
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
app = FastAPI(title="Ascendra API")
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
    }


async def auto_downgrade_if_expired(user: dict) -> dict:
    """Downgrade users whose paid subscription has lapsed."""
    if user.get("tier", "free") == "free":
        return user
    exp = user.get("tier_expires_at")
    if exp and exp < datetime.now(timezone.utc):
        await users_col.update_one(
            {"id": user["id"]},
            {"$set": {"tier": "free", "subscription_interval": None}},
        )
        user["tier"] = "free"
        user["subscription_interval"] = None
    return user

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
    if not user or "password_hash" not in user or not verify_pw(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    return Token(access_token=make_token(user["id"]))

@api.post("/auth/google", response_model=Token)
async def auth_google(body: GoogleSessionIn):
    """Exchange an Emergent-managed Google session_token for our own JWT.
    Verifies the token by calling Emergent's session-data endpoint, then
    upserts the user by email."""
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
        # Link Google to existing email account if not yet linked.
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
async def fetch_lesson(lesson_id: str, user=Depends(current_user)):
    l = get_lesson(lesson_id)
    if not l:
        raise HTTPException(404, "Lesson not found")
    p = get_path(l["path_id"])
    if p and not can_access(user.get("tier", "free"), p.get("tier", "free")):
        raise HTTPException(403, f"This lesson requires {p['tier'].upper()} tier. Upgrade to unlock.")
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

    # Replay prior turns so Claude has multi-turn memory across requests.
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
            "★ NEW: Building with Emergent — ship your first app",
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
            "★ NEW: Emergent for Business — ship & monetize on Emergent",
            "Real founder case studies (revenue + tactics)",
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
        # Trial always unlocks the top tier (Sage) for 7 days
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
                interval = rec.get("interval", "monthly")
                days = {"trial": 7, "annual": 365, "monthly": 30}.get(interval, 30)
                expires_at = datetime.now(timezone.utc) + timedelta(days=days)
                # Trial grants Sage; otherwise the tier they picked
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


# ─── Recurring Subscriptions (auto-renew) ───────────────────────────────────
# Activates only when STRIPE_API_KEY is a real live/test key (sk_live_... or
# sk_test_...) — NOT the Emergent proxy key (sk_test_emergent). When the
# customer hits Publish + drops in their live key, /api/billing/subscribe and
# /api/billing/portal start working immediately. No code changes needed.

def _is_real_stripe_key() -> bool:
    k = STRIPE_API_KEY or ""
    return k.startswith("sk_live_") or (k.startswith("sk_test_") and k != "sk_test_emergent")


@api.post("/billing/subscribe")
async def create_subscription(body: CheckoutIn, request: Request, user=Depends(current_user)):
    """Real recurring Stripe Subscription via Checkout (mode=subscription).
    Falls back to one-time payment if no real Stripe key is configured."""
    if not _is_real_stripe_key():
        raise HTTPException(
            501,
            "Recurring subscriptions require a real Stripe key. Add your sk_live_... to backend/.env and redeploy."
        )
    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_API_KEY

        # Lazy-create Stripe Customer for this user
        cust_id = user.get("stripe_customer_id")
        if not cust_id:
            cust = _stripe.Customer.create(email=user["email"], name=user.get("name") or user["email"])
            cust_id = cust.id
            await users_col.update_one({"id": user["id"]}, {"$set": {"stripe_customer_id": cust_id}})

        amount_usd = TIERS[body.tier]["price_annual"] if body.interval == "annual" else TIERS[body.tier]["price_monthly"]
        recur_interval = "year" if body.interval == "annual" else "month"
        origin = body.origin_url.rstrip("/")

        session = _stripe.checkout.Session.create(
            mode="subscription",
            customer=cust_id,
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(round(amount_usd * 100)),
                    "recurring": {"interval": recur_interval},
                    "product_data": {"name": f"Ascendra {TIERS[body.tier]['name']}"},
                },
                "quantity": 1,
            }],
            success_url=f"{origin}/checkout-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{origin}/pricing",
            metadata={"user_id": user["id"], "tier": body.tier, "interval": body.interval},
        )
        return {"url": session.url, "session_id": session.id}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Subscription create failed")
        raise HTTPException(502, f"Subscription error: {str(e)[:140]}")


@api.post("/billing/portal")
async def billing_portal(request: Request, user=Depends(current_user)):
    """Stripe Customer Portal — users manage card, cancel, view invoices."""
    if not _is_real_stripe_key():
        raise HTTPException(501, "Customer Portal requires a real Stripe key.")
    cust_id = user.get("stripe_customer_id")
    if not cust_id:
        raise HTTPException(400, "No Stripe customer on file. Subscribe first.")
    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_API_KEY
        body = await request.json()
        return_url = (body or {}).get("return_url") or "https://ascendra.app/profile"
        portal = _stripe.billing_portal.Session.create(customer=cust_id, return_url=return_url)
        return {"url": portal.url}
    except Exception as e:
        log.exception("Portal failed")
        raise HTTPException(502, f"Portal error: {str(e)[:140]}")

# ─── Health ─────────────────────────────────────────────────────────────────
@api.get("/")
async def root():
    return {"status": "ok", "service": "ascendra-api"}

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
