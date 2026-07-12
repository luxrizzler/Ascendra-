# Ascendra Academy — Project Docs

> **Note:** This `project/` folder is documentation-only. It does not change application behavior, config, database contents, secrets, dependencies, or deployment. See `CHANGELOG.md` in this folder for the introduction of these docs.

## What Ascendra Academy Is

Ascendra Academy is a **subscription-based AI education platform** delivered as a responsive web application. It teaches AI/LLM fundamentals through a **practice-first, interactive learning experience** and monetizes via recurring Stripe subscriptions.

The product bundles a full learner journey — onboarding quiz, personalized paths, interactive lessons, AI-graded practice, streaks, module capstones, portfolio, certificates, trophy case — with an **operator/admin console** that automates curriculum generation, content quality-checking, transactional email, programmatic SEO, and social distribution.

**Preview environment:** internal (used by the build agent).
**Production:** [https://ascendraacademy.com](https://ascendraacademy.com)

## Tech Stack (evident from repo)

- **Frontend:** React 19 + React Router v6 + TailwindCSS + Shadcn/UI + lucide-react icons + Sonner toasts. Served on port `3000`.
- **Backend:** FastAPI (Python 3), Motor async MongoDB driver, APScheduler for background jobs, tweepy for X, httpx for HTTP integrations. Served on port `8001`, all routes prefixed with `/api`.
- **Database:** MongoDB (a preconfigured URL is provided via `MONGO_URL`). All identifiers are UUID strings, not ObjectIds.
- **LLMs:** Anthropic Claude, OpenAI GPT, and Google Gemini — accessed via `emergentintegrations` using a universal `EMERGENT_LLM_KEY`.
- **Payments:** Stripe LIVE mode — recurring subscriptions + Customer Portal.
- **Transactional email:** Resend, sending from the verified custom domain `ascendraacademy.com`.
- **Auth:** Local email/password (JWT-based) + Emergent-managed Google OAuth callback (`/auth/callback`).
- **Deployment:** Kubernetes ingress routes `/api/*` to backend, everything else to frontend. Processes managed by `supervisor`.

## Repo Layout (high level)

```
/app
├── backend/                    # FastAPI application
│   ├── server.py                # Main API surface (~4,900 lines)
│   ├── curriculum_db.py         # Path/module/lesson data access
│   ├── path_generator.py        # AI-driven custom learning path creation
│   ├── interactive_generator.py # Interactive lesson card generator (Claude)
│   ├── practice_lab.py          # Try-It-Live grading, capstones, drills
│   ├── content_scanner.py       # Auto-scan/patch outdated lesson content
│   ├── auto_content.py          # Scheduled daily/weekly content pipeline
│   ├── lifecycle.py             # Lifecycle email automation
│   ├── seo_studio.py            # Programmatic SEO page generator
│   ├── ai_studio.py             # Admin AI Course Studio
│   ├── social_studio.py         # Tweet threads + carousels + MP4s
│   ├── x_publisher.py           # X auto-post w/ free-tier budget tracking
│   ├── meta_publisher.py        # Facebook + Instagram Graph API
│   ├── tiktok_publisher.py      # TikTok Content Posting API (OAuth 2 + PKCE)
│   ├── social_media_signer.py   # HMAC-signed public URLs for platform pulls
│   ├── email_service.py         # Resend transactional email
│   ├── llm_retry.py             # Tenacity wrappers for LLM rate limits
│   └── requirements.txt         # Python dependencies
├── frontend/                   # React application (Create React App base)
│   ├── src/pages/               # 43 route-level page components
│   ├── src/components/          # Shared UI (lesson/, streak/, ui/ Shadcn)
│   ├── src/lib/api.js           # API client (Bearer auth)
│   └── public/                  # robots.txt, sitemap.xml, security.txt, TikTok verification
├── tests/                      # Pytest suites
├── plan.md                     # Running product/architecture log (source of truth)
└── project/                    # ← this folder
```

## Where to Look for What

- **What's implemented right now:** `project/STATUS.md`
- **What's next:** `project/ROADMAP.md`
- **Concrete next actions:** `project/TASKS.md`
- **Why things were built the way they were:** `project/DECISIONS.md`
- **How to run locally:** `project/SETUP.md`
- **Historical context of the running plan:** `/app/plan.md` (the master log used by the build agent)
