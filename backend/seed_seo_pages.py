"""
Seed initial SEO landing pages so the site has indexable content immediately.

Generates 6 model hubs + 2 use-case sub-pages = 8 pages total via Claude 4.5.
Idempotent: re-running updates the existing rows.

Usage:
    cd /app/backend && python seed_seo_pages.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))
sys.path.insert(0, ROOT)

import seo_studio  # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "test_database")

HUBS = [
    "Claude Sonnet 4.5",
    "GPT-5.2",
    "Gemini 3",
    "Sora 2",
    "Nano Banana",
    "ElevenLabs",
]

USE_CASES = [
    ("Claude Sonnet 4.5", "For Marketing"),
    ("GPT-5.2", "For Founders"),
]


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    print(f"Seeding SEO pages → DB={DB_NAME}\n")

    for model in HUBS:
        print(f"  ▸ Generating hub: {model}")
        try:
            page = await seo_studio.generate_hub_page(model)
            saved = await seo_studio.upsert_page(db, page, published=True)
            print(f"    ✓ {saved['title']}  (/learn/{saved['model_slug']})")
        except Exception as e:
            print(f"    ✗ FAILED: {e}")

    for model, use_case in USE_CASES:
        print(f"\n  ▸ Generating use-case: {model} {use_case}")
        try:
            page = await seo_studio.generate_usecase_page(model, use_case)
            saved = await seo_studio.upsert_page(db, page, published=True)
            print(f"    ✓ {saved['title']}  (/learn/{saved['model_slug']}/{saved['use_case_slug']})")
        except Exception as e:
            print(f"    ✗ FAILED: {e}")

    print("\nDone.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
