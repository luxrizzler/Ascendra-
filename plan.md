# plan.md (UPDATED)

## 1. Objectives
- Deliver Ascendra as a **standalone responsive website**: React + FastAPI + MongoDB.
- Preserve the full product loop:
  - Curriculum (paths → modules → lessons → cards)
  - Progress (XP, streak, levels)
  - Certificates (auto-issued on path completion)
  - AI Tutor chat (Claude via `emergentintegrations`)
  - Pricing/checkout (Stripe **LIVE**, recurring subscriptions + Customer Portal)
  - Admin dashboard (stats/users/sales/traffic)
- Web-first UX: responsive layout, navigation, accessible lesson player, share/print certificates.
- Ensure **free users can experience the product**: intro “AI Fundamentals” path is accessible on the free tier.
- Production integrations:
  - Stripe LIVE subscriptions + Customer Portal
  - Resend transactional emails from verified domain `ascendraacademy.com`
  - Emergent-managed Google OAuth

### Completed “next-phase” deliverables (sequential ship) — COMPLETED ✅
1) Renewal reminders (monthly + annual) 7 days before renewal
2) “What’s New” (admin + user-facing) surfacing recent AI-generated lessons + Admin Subscribers list
- Promo/discount codes: **explicitly out of scope for now** (per user: “no discount available”)

### New overarching objective: Automation + Growth Flywheel — COMPLETED ✅
Build a largely automated growth engine:
- **Programmatic SEO** (`/learn` hubs with dynamically generated pages) to generate compounding traffic.
- **Content auto-pilot** so “fun new courses” ship automatically (daily lessons + weekly flagship course).
- **Lead magnet + drip sequences** to turn visitors into trials.
- **Lifecycle automation** to improve conversion/retention.
- **Social pipeline** using a **free-only content generation stack** (no paid video services), plus X/Twitter integration readiness.

### NEW overarching objective: Coursiv‑style engagement loop — LARGELY ACHIEVED ✅ / ONGOING 🟡
Deliver an interactive learning experience comparable to “Coursiv-style” apps:
- Streak tracking + celebrations
- AI onboarding quiz → personalized plan
- 15‑Day Challenge roadmap
- Interactive lesson cards (Knowledge Checks, Fill‑in‑the‑blank, Playgrounds) generated dynamically by Claude
- TTS narration + prompt libraries

### NEW operational objective: Trustworthy business metrics — ACHIEVED ✅
Ensure admin analytics reflect **real-world performance** by excluding internal QA/admin accounts from key dashboards.

### NEW operational objective: Stripe key hygiene — IN PROGRESS 🟡
Reduce risk of revenue loss / account compromise by:
- Ensuring production deployments use **Stripe Restricted Keys (`rk_live_…`)** only
- Ensuring rotated/revoked keys are not reused
- Ensuring no secrets are ever pasted into chat/screenshots/logs

### NEW product objectives (requested) — SHIPPED ✅
**Phase 15: Admin Auto‑Pilot Queue UX Upgrade (P1) — COMPLETED ✅**
- Provide actionable controls for `FAILED` / `NEEDS REVIEW` items:
  - Regenerate (re-run Claude)
  - Reject (clean queue, keep audit)
  - Minimal draft edit before publishing

**Phase 16: User‑Generated Learning Paths (P1/P2 large feature) — COMPLETED ✅**
- Paid users can generate custom multi-level paths (Beginner/Intermediate/Advanced).
- Generated paths start private/pending and notify admin for review.
- Admin can approve (publish + choose tier) or reject (keeps private, optional notes).
- Users can take lessons in any order (no forced sequencing), while UI presents recommended order.

---

## 2. Implementation Steps

### Phase 1 — Core POC (Isolation): prove the “hard parts” work (COMPLETED ✅)
Goal: validate external integrations + completion→certificate data flow before building full UI.

1) **Backend POC wiring**
- Ported backend files from repo → `/app/backend/`.
- Disabled Expo static-site serving; API-only backend.
- Added and verified `/app/backend/.env` variables:
  - `MONGO_URL`, `DB_NAME`, `JWT_SECRET_KEY`, `EMERGENT_LLM_KEY`, `STRIPE_API_KEY`, `PUBLIC_WEB_URL`
- Installed/validated backend dependencies; backend runs under supervisor.

2) **POC smoke tests**
- Verified with curl:
  - Signup/login/JWT + `/api/auth/me`
  - `/api/paths` (paths) and `/api/models` (models)
  - `/api/progress/complete` updates XP/streak/level
  - `/api/tutor/chat` returns live Claude output
  - `/api/billing/checkout` returns Stripe hosted checkout URL

**Phase 1 user stories (POC) — COMPLETED ✅**
1. Sign up and receive a JWT.
2. Open a lesson and complete it, increasing XP and streak.
3. Completing a full path issues a certificate.
4. Chat with AI Tutor multi-turn in one session.
5. Start a checkout session and receive a Stripe URL.

---

### Phase 2 — V1 Website (MVP build, minimal bulk passes) (COMPLETED ✅)
Goal: ship a working website covering the main learning + certificate flow.

- Implemented Ascendra theme + layout primitives.
- Implemented API client using `REACT_APP_BACKEND_URL` + bearer token storage.
- Implemented auth context (`AuthProvider`) with token persistence + `/auth/me` refresh.

Routes:
- `/` landing
- `/signup`, `/login`
- `/dashboard`
- `/paths`, `/paths/:id`
- `/lessons/:id` LessonPlayer
- `/certificate/:id` printable certificate view

---

### Phase 3 — Feature expansion (production flows) (COMPLETED ✅)
- AI Tutor UI (`/tutor`)
- Pricing + payments (Stripe LIVE subscriptions)
- Onboarding quiz → recommendation
- Profile billing portal
- Admin UI (stats/users/sales/traffic, curriculum studio, email previewer)
- Resend production emails

---

### Phase 4 — Testing, fixes, and polish (COMPLETED ✅)
- E2E testing via `testing_agent_v3`
- Free tier conversion fix (AI Fundamentals tier)
- UX polish on landing/pricing

---

### Phase 5 — Renewal reminders (P1) — COMPLETED ✅
- Stripe `invoice.upcoming` handling in `/api/billing/webhook`
- Admin triggers + Resend templates

---

### Phase 6 — “What’s New” + Subscribers list (P2) — COMPLETED ✅
- AI Studio tagging + endpoints + admin pages

---

### Phases 7–11 Roadmap expansion — COMPLETE ✅
- Phase 7 Programmatic SEO
- Phase 8 Content Auto‑Pilot (APScheduler) + quality gate
- Phase 9 Lead magnet + welcome drip
- Phase 10 Lifecycle emails
- Phase 11 Social content pipeline + X integration readiness (blocked on X Project enrollment)

**Interactive content auto-upgrade (future lessons) — VERIFIED ✅**
- Inline interactivization after publish in `run_daily_lesson()` and sampled lessons in `run_monday_path()`
- Safety-net: `interactive_sweep` hourly cron

---

### Phase 12 — Deployment readiness + production launch — COMPLETE ✅
- Deployment blockers fixed (admin stats aggregation, .env parsing)

---

### Phase 13 — Social manual post helper for Meta — NOT STARTED (P2)
- Planned manual copy/export helpers

---

### Phase 14 — P0 Bug Fix: Admin analytics must exclude internal accounts — COMPLETED ✅
- Added `TEST_EMAIL_REGEX` + helper filters
- Updated `/api/admin/stats`, `/api/admin/users`, `/api/admin/sales`, `/api/admin/subscribers`
- Verified with backend tests (28/28 = 100%)

---

### Phase 15 — Admin Auto‑Pilot Queue UX Upgrade (P1) — COMPLETED ✅
**Goal:** Make the Auto‑Pilot queue actionable when items are `FAILED` / `NEEDS REVIEW`.

**What shipped:**
1) **Backend** (`/app/backend/server.py`)
- `POST /api/admin/auto/queue/{queue_id}/regenerate`
  - Allowed statuses: `failed`, `needs_review`, `rejected`
  - Clears prior `draft/error/grades`, increments `regen_count`, appends `regen_history`
  - Forces generation immediately via `run_daily_lesson()` / `run_monday_path(force=True)`
- `POST /api/admin/auto/queue/{queue_id}/reject`
  - Sets `status=rejected`, persists `reject_reason` + timestamp
- `PATCH /api/admin/auto/queue/{queue_id}/draft`
  - Minimal draft editor for `needs_review` items (title + body override)

2) **Auto-pilot engine** (`/app/backend/auto_content.py`)
- `run_monday_path(..., force=True)` added to bypass once-per-day dedup for manual regenerate.

3) **Frontend** (`/app/frontend/src/pages/AdminAutoContent.js`)
- Added buttons for queue items:
  - **Regenerate** (FAILED / NEEDS REVIEW / REJECTED)
  - **Edit** (NEEDS REVIEW + has draft)
  - **Publish** (NEEDS REVIEW + has draft)
  - **Reject** (non-pending/non-published)
- Added `rejected` status pill.
- Verified via screenshots.

4) **Testing**
- Verified by backend testing agent (iteration_17) — 28/28 pass overall.

---

### Phase 16 — User‑Generated Learning Paths (P1/P2) — COMPLETED ✅
**Goal:** Paid users can generate multi-level long-form paths and submit for admin approval.

**Product rules (confirmed):**
- Path generation is **paid-only** (`tier != free`)
- Generated path is `pending_review` and not visible publicly until approved
- User **cannot edit** the generated path content, but **can take lessons in any order**
- No caps on personal paths for paying users (rate-limit exists to prevent abuse)
- Tier catalog expansion continues over time:
  - Ascender: baseline paid catalog
  - Pathfinder: Ascender + additional
  - Sage: everything + sage-exclusive

**What shipped:**
1) **New backend module**
- `/app/backend/path_generator.py`
  - Stage 1: outline generation (3 modules × 5–7 lessons each)
  - Stage 2: background fill lesson content (controlled concurrency)

2) **Schema + queries** (`/app/backend/curriculum_db.py`)
- Added fields:
  - `visibility` (`public | pending_review | rejected | private`)
  - `created_by`, `creator_email`
  - `admin_review_status` (`pending | approved | rejected`)
  - `admin_review_notes`
  - `is_user_generated`
- Added functions:
  - `list_paths(viewer_id, is_admin, include_private)` — visibility-aware
  - `list_paths_by_creator(creator_id)`
  - `list_paths_pending_review()`

3) **Backend endpoints** (`/app/backend/server.py`)
- `POST /api/paths/generate` (paid-only)
  - Validates goal length, rate-limits (1 per user / 5 minutes)
  - Creates path with `visibility=pending_review`, `admin_review_status=pending`
  - Creates `admin_notifications` record
  - Background-tasks: fill lessons + interactivize (best-effort)
- `GET /api/paths/mine`
- Updated `GET /api/paths` (anonymous: public+approved only; authed: also include own)
- Updated `GET /api/paths/{id}` to protect non-public paths

4) **Admin review workflow**
- `GET /api/admin/paths/pending-review`
- `POST /api/admin/paths/{id}/approve` (optional tier override)
- `POST /api/admin/paths/{id}/reject` (notes)
- In-app notifications:
  - `GET /api/admin/notifications`
  - `POST /api/admin/notifications/{id}/mark-read`

5) **Frontend UX**
- `/app/frontend/src/pages/Paths.js`
  - “Create your own path” CTA + modal goal prompt
  - “Your custom paths” section + status badges (Pending/Approved/Needs work)
- `/app/frontend/src/pages/AdminPathsReview.js`
  - Review list + approve/reject modal + tier override
- `/app/frontend/src/pages/Admin.js`
  - Added **PATHS REVIEW** tab with pending-count badge
- `/app/frontend/src/App.js`
  - Registered route `/admin/paths-review`

6) **Testing**
- Verified by backend testing agent (iteration_17) — 28/28 pass.

**Known minor limitations (non-blockers):**
- LLM rate limits may cause some background lesson-fill failures under load; the hourly sweep/retries mitigate this.
- 5-minute per-user generation rate limit is strict; can be relaxed later.

---

## 3. Next Actions

### Immediate (P0/P1): Deploy Phase 15 + 16 to production
- User action: Redeploy via Emergent Deploy dashboard to push preview → `ascendraacademy.com`.
- After redeploy:
  - Verify `/admin/auto-content` shows Regenerate/Edit/Publish/Reject
  - Verify `/paths` shows the Create Path CTA
  - Verify `/admin/paths-review` exists and lists pending submissions

### Phase 17 — Stripe key hygiene hardening (P0) — IN PROGRESS 🟡
Goal: eliminate risk of deploying Standard Secret keys and ensure key rotation hygiene.
- Ensure production deployment secrets use `STRIPE_API_KEY=rk_live_…` (Restricted Key)
- Verify `STRIPE_WEBHOOK_SECRET=whsec_…` set in production
- Confirm no secret keys are ever pasted into chat/screenshots
- Optional improvement: add a startup log check that validates key prefix (`rk_` only) and refuses to start if `sk_` is detected (preview-safe, production-safe).

### Phase 18 — X (Twitter) auto-posting unblock (P1) — USER ACTION REQUIRED
- Fix 403 `client-not-enrolled` by attaching X App to a Project in X Developer Portal.
- Once done, re-test `/api/admin/social/x/test-post`.

### Phase 19 — Meta (FB/IG) manual post helper (P2) — NOT STARTED
- Add one-click copy/export helpers for FB/IG posting.

---

## 4. Success Criteria

### Product + Ops — ACHIEVED ✅
- ✅ Backend integrations proven: Claude tutor, Stripe LIVE checkout + subscriptions + Customer Portal, certificates.
- ✅ Website supports full learning loop end-to-end.
- ✅ Resend emails live on verified custom domain.
- ✅ Renewal reminders shipped (monthly + annual) + admin tools.
- ✅ “What’s New” shipped + AI content tagging.
- ✅ Admin Subscribers list shipped.

### Growth Flywheel — ACHIEVED ✅
- ✅ Programmatic SEO pages + sitemap + schema.
- ✅ Content auto-pilot: daily lessons + Monday flagship paths + quality gate.
- ✅ Lead magnet capture + AI Roadmap resource + welcome drip.
- ✅ Lifecycle automation: trial-ending, winback, streak-saver, annual upsell.
- ✅ Social pipeline: free-only asset generation + admin preview + MP4 export.

### Coursiv-style engagement loop — LARGELY ACHIEVED ✅ / ONGOING 🟡
- ✅ Streak tracking + milestone celebrations.
- ✅ AI onboarding quiz + personalized plan.
- ✅ 15-day challenge roadmap.
- ✅ Interactive lesson cards + prompt libraries + browser-native TTS.
- ✅ Future auto-generated lessons auto-interactivized via `interactive_sweep`.

### Business metrics quality bar — ACHIEVED ✅
- ✅ Admin analytics endpoints exclude internal accounts while keeping real free-tier leads.
- ✅ Verified by backend testing agent (iteration_16).

### Phase 15 (Admin queue UX) — ACHIEVED ✅
- ✅ Admin can regenerate failed/review items and progress queue without leaving the page.
- ✅ Admin can reject items to keep queue clean and audited.
- ✅ Minimal draft edit available for needs_review.
- ✅ Verified via backend testing (iteration_17) + UI screenshot.

### Phase 16 (User-generated paths) — ACHIEVED ✅
- ✅ Paid users can create multi-level (Beginner/Intermediate/Advanced) long-form paths.
- ✅ Paths are pending by default and notify admin for review.
- ✅ Admin approve/reject works; approved becomes public and tier-gated.
- ✅ Users can take lessons in any order.
- ✅ Verified via backend testing (iteration_17) + UI screenshots.

---

## 5. Operator / Environment Notes
- Two environments exist (Preview vs Production). Code changes land in preview; operator redeploy is required to push to production.
- **Stripe keys:** Production should use **Restricted Key (`rk_live_…`)** in deployment secrets; Standard Secret Key (`sk_live_…`) should never be used in deployments.
- Avoid pasting any secrets into chat or screenshots. Rotate immediately if exposed.
