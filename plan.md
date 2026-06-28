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

### NEW product objectives (requested)
**Phase 15: Admin Auto‑Pilot Queue UX Upgrade (P1)**
- Fix immediate admin pain: items show `FAILED` / `NEEDS REVIEW` but operator cannot conveniently regenerate/approve/reject or quickly iterate.
- Add regenerate + review controls (no full manual editor required for v1; optionally add minimal notes/edit in a controlled way).

**Phase 16: User‑Generated Learning Paths (P1/P2 large feature)**
- Paid users can generate custom learning paths (longer than 5–7 lessons) with Beginner/Intermediate/Advanced coverage.
- Generated paths start private and trigger admin review notification.
- Admin can approve to publish globally or reject with a reason.
- Users can take lessons in any order (no forced sequencing), while the app still presents a recommended order.

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

## 3. Next Actions

### Phase 15 — Admin Auto‑Pilot Queue UX Upgrade (P1) — NOT STARTED
**Goal:** Make the Auto‑Pilot queue actionable when items are `FAILED` / `NEEDS REVIEW`.

**Current issue (user report):** On `/admin/auto-content` the operator cannot meaningfully act on queue items (no regenerate/retry workflow visible/available to resolve `FAILED` or `NEEDS REVIEW`).

**Deliverables:**
1) **Backend**
- Add queue item regeneration endpoint:
  - `POST /api/admin/auto/queue/{queue_id}/regenerate`
    - Re-run generation for the same `topic/kind/level`
    - Overwrite `draft` (if any), clear `error`, set `status=needs_review` (or `pending_review`) with new `grades`
    - Increment `regen_count`, store `regen_history` (timestamp, short summary, grades)
- Add reject endpoint:
  - `POST /api/admin/auto/queue/{queue_id}/reject` with optional `{reason}`
    - `status=rejected` and persists reason + timestamp
- Add publish endpoint validation improvements (existing):
  - Keep `POST /api/admin/auto/queue/{queue_id}/publish` but ensure it can publish from `needs_review` reliably

2) **Frontend** (`/app/frontend/src/pages/AdminAutoContent.js`)
- For `FAILED` and `NEEDS REVIEW` items show buttons:
  - **Regenerate** (Refresh icon) → calls regenerate endpoint
  - **Reject** (X icon) → calls reject endpoint
  - **Publish anyway** remains (only for items with drafts)
- Add a small “details drawer/modal” to show:
  - grader notes, error text, last regeneration time

3) **Testing**
- Use backend testing agent:
  - Seed a fake queue item in DB with `needs_review` + `draft`
  - Regenerate → status changes, draft updated, regen_count increments
  - Reject → status rejected
  - Ensure endpoints are admin-protected

**Notes:**
- The user specifically requested “refresh/recreate” over manual editing; manual editing can be added later if needed.

---

### Phase 15.1 — Optional: Minimal Draft Editing (P2) — DEFERRED
If needed after Phase 15:
- `PATCH /api/admin/auto/queue/{id}/draft` to edit title/body only
- Frontend modal editor + preview

---

### Phase 16 — User‑Generated Learning Paths (P1/P2) — NOT STARTED
**Goal:** Paid users can generate a custom path (longer than 5–7 lessons) spanning Beginner/Intermediate/Advanced, start learning immediately, and submit for admin approval to become public.

**Product rules (confirmed):**
- Path generation is **paid-only** (no free users)
- Generated path is **private to creator** initially and **notifies admin** for review
- User **cannot edit** the generated path content, but **can take lessons in any order**
- No caps on personal paths for paying users; however **tier gating controls which public paths are visible**
- Over time, more public paths are added and tier catalog expands:
  - Ascender: X paths
  - Pathfinder: Ascender paths + additional set
  - Sage: everything + sage-exclusive

**Deliverables:**
1) **Schema additions** (`curriculum_paths` documents)
- `visibility`: `private | pending_review | public | rejected`
- `created_by`: user_id
- `creator_email`: cached
- `admin_review_status`: `pending | approved | rejected`
- `admin_review_notes`: optional
- `is_user_generated`: bool (optional convenience)

2) **Backend endpoints**
- `POST /api/paths/generate`
  - Auth required; requires tier != `free`
  - Input: `{ goal: string }`
  - Output: created private path summary + first lesson IDs
  - Generation format:
    - 3 modules: Beginner/Intermediate/Advanced
    - Total lessons: target 15–20 (configurable)
    - Each lesson includes interactive cards (via `interactive_generator` inline)
- `GET /api/paths/mine`
  - Returns user’s private/pending/rejected paths + public ones they created
- Tier gating updates:
  - `GET /api/paths` should return:
    - all `public` paths accessible by tier
    - plus user’s own private/pending paths (regardless of tier gate for public catalog)

3) **Admin review workflow**
- `GET /api/admin/paths/pending-review`
- `POST /api/admin/paths/{path_id}/approve`
  - Sets `visibility=public`, `admin_review_status=approved`
- `POST /api/admin/paths/{path_id}/reject` with `{reason}`
  - Sets `visibility=rejected`, keeps it visible only to creator
- **Notifications**:
  - In-app admin badge (simple count on admin home)
  - Email via Resend to admin address (optional) when a new path is submitted

4) **Frontend UX**
- `/paths`:
  - Add CTA: **“Don’t see your path? Create one”** (paid only; free sees upgrade prompt)
  - Show public catalog + “My generated paths” section (private/pending)
- Add `/paths/create` (or modal) with:
  - goal prompt input
  - generate button + loading state (30–90s)
  - on success → route to newly created path detail
- Update path detail / lesson list to allow “Start any lesson” (no forced order)
- Admin page `/admin/paths-review`:
  - list pending user paths, preview outline, approve/reject

5) **Testing**
- Backend testing agent:
  - Paid user can generate path
  - Free user forbidden
  - Admin pending review list works
  - Approve makes it appear in `/api/paths` for tiered users
  - Reject keeps it private to creator

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
- ✅ Verified by backend testing agent (28/28 = 100%).

### New success criteria (to be achieved)
**Phase 15 (Admin queue UX):**
- ⬜ Admin can regenerate failed/review items and progress queue without leaving the page.
- ⬜ Admin can reject items to keep queue clean and audited.
- ⬜ Verified via backend testing.

**Phase 16 (User-generated paths):**
- ⬜ Paid users can create multi-level (Beginner/Intermediate/Advanced) long-form paths.
- ⬜ Paths are private by default and notify admin for review.
- ⬜ Admin approve/reject works; approved becomes public and tier-gated.
- ⬜ Users can take lessons in any order.

---

## 5. Operator / Environment Notes
- Two environments exist (Preview vs Production). Code changes land in preview; operator redeploy is required to push to production.
- **Stripe keys:** Production should use **Restricted Key (`rk_live_…`)** in deployment secrets; Standard Secret Key (`sk_live_…`) should never be used in deployments.
- Avoid pasting any secrets into chat or screenshots. Rotate immediately if exposed.
