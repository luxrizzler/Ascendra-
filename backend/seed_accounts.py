"""
Seed admin + Sage test accounts for Ascendra.

Idempotent: running this multiple times will UPDATE existing rows rather than
create duplicates. Safe to re-run after deploy.

Usage:
    cd /app/backend && python seed_accounts.py
"""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN_EMAIL = "admin@ascendraacademy.com"
ADMIN_TEMP_PASSWORD = "AscendraAdmin2026!"  # forced-change on first login

# Sage accounts for friends — they'll change password on first login.
SAGE_ACCOUNTS = [
    {"email": "sage1@ascendraacademy.com", "password": "test1", "name": "Sage Friend 1"},
    {"email": "sage2@ascendraacademy.com", "password": "test2", "name": "Sage Friend 2"},
    {"email": "sage3@ascendraacademy.com", "password": "test3", "name": "Sage Friend 3"},
    {"email": "sage4@ascendraacademy.com", "password": "test4", "name": "Sage Friend 4"},
    {"email": "sage5@ascendraacademy.com", "password": "test5", "name": "Sage Friend 5"},
    {"email": "sage6@ascendraacademy.com", "password": "test6", "name": "Sage Friend 6"},
]


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


async def upsert_user(users, email, password, name, *, tier="free",
                       is_admin=False, must_change_password=True,
                       tier_expires_at=None, subscription_interval=None):
    existing = await users.find_one({"email": email})
    doc = {
        "email": email,
        "name": name,
        "password_hash": hash_pw(password),
        "tier": tier,
        "subscription_interval": subscription_interval,
        "tier_expires_at": tier_expires_at,
        "is_admin": is_admin,
        "must_change_password": must_change_password,
        "auth_provider": "email",
        "has_used_trial": False,
    }
    if existing:
        await users.update_one({"email": email}, {"$set": doc})
        print(f"  ↻ updated  {email}  (tier={tier}, admin={is_admin})")
    else:
        doc["id"] = str(uuid.uuid4())
        doc["created_at"] = datetime.now(timezone.utc)
        await users.insert_one(doc)
        print(f"  ＋ created  {email}  (tier={tier}, admin={is_admin})")


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    users = db["users"]

    print("Seeding Ascendra Academy accounts…\n")

    # Admin
    await upsert_user(
        users,
        ADMIN_EMAIL,
        ADMIN_TEMP_PASSWORD,
        "Ascendra Admin",
        is_admin=True,
        must_change_password=True,
    )

    # 6 Sage friends — 90 days of full Sage access
    expires = datetime.now(timezone.utc) + timedelta(days=90)
    for acc in SAGE_ACCOUNTS:
        await upsert_user(
            users,
            acc["email"],
            acc["password"],
            acc["name"],
            tier="sage",
            subscription_interval="annual",
            tier_expires_at=expires,
            must_change_password=True,
        )

    print("\nDone. Admins logging in will be prompted to set a new password.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
