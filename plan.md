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
- **Social pipeline** using a **free-only content generation stack** (no paid video services).

### NEW overarching objective: Coursiv‑style engagement loop — LARGELY ACHIEVED ✅ / ONGOING 🟡
Deliver an interactive learning experience comparable to “Coursiv-style” apps:
- Streak tracking + celebrations
- AI onboarding quiz → personalized plan
- 15‑Day Challenge roadmap
- Interactive lesson cards (Knowledge Checks, Fill‑in‑the‑blank, Playgrounds) generated dynamically by Claude
- TTS narration + prompt libraries

### NEW overarching objective: Practice-first learning (better-than-Coursiv) — IN PROGRESS 🟡
Add **applied practice** throughout courses so users learn by doing, not just reading + quizzes:
- Layer 1: **Try It Live** (rubric-graded practice tasks with AI feedback) + Portfolio
- Layer 2: **Module Capstones** (mandatory to earn module/path certificates)
- Layer 3: **Spaced Practice Drills** (3/7/21-day review prompts based on struggles)
- Bonus: **Trophy Case** (publicly shareable showcase of achievements)

### NEW operational objective: Trustworthy business metrics — ACHIEVED ✅
Ensure admin analytics reflect **real-world performance** by excluding internal QA/admin accounts from key dashboards.

### NEW operational objective: Stripe key hygiene — IN PROGRESS 🟡
Reduce risk of revenue loss / account compromise by:
- Ensuring production deployments use **Stripe Restricted Keys (`rk_live_…`)** only
- Ensuring rotated/revoked keys are not reused
- Ensuring no secrets are ever pasted into chat/screenshots/logs

### NEW operational objective: Legal compliance baseline — ACHIEVED ✅
Meet minimum legal/compliance expectations for:
- Stripe payments review
- Social platform developer portals (X, TikTok)
- Email compliance (Resend footers / lawful basis)

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
- Phase 11 Social content pipeline + X integration readiness (later impacted by X Pay-Per-Use migration)

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

4) **Testing**
- Verified by backend testing agent — 28/28 pass overall.

---

### Phase 16 — User‑Generated Learning Paths (P1/P2) — COMPLETED ✅
**Goal:** Paid users can generate multi-level long-form paths and submit for admin approval.

**Product rules (confirmed):**
- Path generation is **paid-only** (`tier != free`)
- Generated path is `pending_review` and not visible publicly until approved
- User **cannot edit** the generated path content, but **can take lessons in any order**
- No caps on personal paths for paying users (rate-limit exists to prevent abuse)

**What shipped:**
1) **New backend module**
- `/app/backend/path_generator.py`

2) **Schema + queries** (`/app/backend/curriculum_db.py`)
- Added visibility + admin review status fields

3) **Backend endpoints** (`/app/backend/server.py`)
- `POST /api/paths/generate` (paid-only)
- `GET /api/paths/mine`
- Updated listing/detail endpoints to protect non-public paths

4) **Admin review workflow**
- Pending-review list + approve/reject

5) **Frontend UX**
- User UI: `/paths` custom path generator
- Admin UI: `/admin/paths-review`

6) **Testing**
- Verified by backend testing agent — 28/28 pass.

---

### Phase 17 — Smart Subscription Management Card (P0/P1 retention) — COMPLETED ✅
**Goal:** Let users renew/reactivate/resume from inside the app without confusion, while keeping Stripe handling secure.

**Shipped:**
- Backend: `/api/billing/status`, `/api/billing/resume` (plus related status logic)
- Frontend: `/app/frontend/src/components/SubscriptionCard.js` embedded in Dashboard
- Certificate retention preserved for lapsed users

---

### Phase 18 — Landing-page onboarding quiz popup (COMPLETED ✅)
- Moved onboarding quiz to a Landing Page popup with anonymous plan generation via `/api/onboarding/anonymous`.

---

### Phase 19 — Legal + Security Compliance (P0) — COMPLETED ✅
**Goal:** Add compliance pages and verification/security artifacts to satisfy payment + platform requirements.

**What shipped:**
1) **Frontend pages (NEW)**
- `/terms`, `/privacy`, `/no-refunds`

2) **Routing + footer + signup enforcement (UPDATED)**
- Routes added, footer Legal links, signup agreement checkbox

3) **security.txt (NEW)**
- `/.well-known/security.txt` + `/security.txt` (RFC 9116)

4) **Terms enhancement (UPDATED)**
- Added **Section 11: Social Media Integrations** covering platform terms, posting limitations, authorization/revocation, content warranties, third-party costs.

5) **TikTok domain verification artifact (NEW)**
- Added `tiktoklkxs3T9JjlCjJNh3jIZzlheOa0um2ntP.txt` at site root.
- Updated to be **byte-for-byte exact** match with TikTok-provided original (no trailing newline).

6) **SEO / reach hardening (UPDATED)**
- Updated `robots.txt` to explicitly allow Googlebot, Bingbot, etc. and disallow private routes.
- Added `robots` + `googlebot` meta tags and JSON-LD schema to `public/index.html` (Organization + WebSite SearchAction).

---

### Phase 20 — Practice Lab (Try It Live + Portfolio) — IN PROGRESS 🟡
**Goal:** Add applied practice throughout lessons with AI feedback, then expand to capstones and spaced repetition.

#### Product decisions (user-confirmed)
- **Grading tone:** Balanced (encouraging opening + honest critique + actionable next step)
- **Portfolio default:** **Private**; user can toggle items public per attempt/item
- **Certificates:** Require **lesson completion + capstone pass**
- **Rollout:** Ship Layer 1 first → user review → then Layer 2 and 3
- **Future:** Add a **Trophy Case** to show off awards

#### Layer 1 — Try It Live + Portfolio MVP (ship first)
**Backend**
- NEW module: `/app/backend/practice_lab.py`
  - Rubric-based grading using Claude (via `emergentintegrations`)
  - Must use `llm_retry.py` for transient retries + friendly errors
  - Stores attempts + scores + feedback + “best attempt” pointers
- NEW MongoDB collections:
  - `practice_challenges` (per lesson/card; includes rubric + expected behaviors)
  - `practice_attempts` (user submissions, scores, feedback, timestamps)
- NEW API endpoints (server.py):
  - `POST /api/practice/{challenge_id}/attempt` — submit attempt, receive score + feedback
  - `GET /api/practice/portfolio/mine` — list mastered attempts + best artifacts
  - `POST /api/practice/portfolio/{attempt_id}/toggle-public` — privacy toggle
  - `GET /api/practice/portfolio/public/{user_slug}` — public portfolio page data
  - `POST /api/admin/practice/generate/{lesson_id}` — generate a practice challenge for an existing lesson (admin tool)

**Frontend**
- NEW card kind: `try_it_live`
  - New component: `PracticeCard.js`
  - Update `CardRouter.js` + `isInteractive()` to include `try_it_live`
  - UX: attempt box → Run → AI feedback panel → allow retries → “Mastery” threshold gate
- NEW pages:
  - `/portfolio` — private portfolio (mastered items, best attempts, copy/share)
  - `/portfolio/:userSlug` — public portfolio (SEO-friendly)
- Navigation:
  - Add Portfolio entry in user menu/dashboard

**Content rollout**
- Add Try-It-Live practice cards to 2–3 high-traffic demo lessons first for immediate feel.
- Then expand via automated generation in the content pipeline.

**Success criteria (Layer 1)**
- Users can complete a practice task, get a score, iterate, and “master” it.
- Best attempt saved privately; can be toggled public.
- Public portfolio page is crawlable and SEO-safe (no private content leaks).

#### Layer 2 — Module Capstones (queued; after Layer 1 approval)
- New capstone at end of each module (multi-step mini-project)
- **Mandatory** to earn module/path certificates (per decision 3a)

Backend
- New `capstones` collection + capstone submissions collection
- Endpoints:
  - `GET /api/capstones/{module_id}`
  - `POST /api/capstones/{capstone_id}/submit`
  - Admin review/override endpoints if needed
- Certificate unlock logic updates: requires capstone pass

Frontend
- `CapstoneSubmission.js` (structured submission + rubric + AI feedback)
- Module UI: show capstone requirements + pass/fail + retry

#### Layer 3 — Spaced Practice Drills (queued; after Layer 2)
- Reinforce weak areas at 3/7/21 day intervals

Backend
- Drill scheduler (APScheduler): selects “weak skills” from attempts and schedules prompts
- Endpoints:
  - `GET /api/practice/drills/today`
  - `POST /api/practice/drills/{drill_id}/attempt`

Frontend
- `DrillWidget.js` on dashboard + optional lesson warm-up
- Streak synergy: drills can count as “practice streak” (separate from lesson streak) or blended

#### Bonus — Trophy Case (future phase; after Layer 1–3)
- Shareable “trophy case” showing:
  - Certificates earned
  - Capstone badges
  - Streak milestones
  - Top portfolio items
- Public URL: `/trophies/:userSlug` (optional) + privacy controls

---

## 3. Next Actions

### Immediate (P0): Practice Lab Layer 1 kickoff
- Implement new Practice Lab backend module + collections
- Add `try_it_live` card type to the lesson UI
- Ship `/portfolio` (private) + public portfolio toggle
- Seed 2–3 demo lessons with practice cards
- Request user review after Layer 1 ships

### X (Twitter) posting (P1) — Platform decision + security action required
- **Pricing reality:** X is now **Pay-Per-Use** (Free tier removed Feb 2026). Decide whether to pay per post or switch to manual copy workflow.
- **Security:** Rotate all exposed OAuth 2.0 credentials immediately (client secret, access token, refresh token) since they were pasted in chat.

### TikTok posting (P2) — Feasibility & audit gating
- TikTok posting API is dollar-free but requires:
  - Business account
  - App audit (1–4 weeks) for public posting
  - Token refresh flow + domain verification
- Domain verification file now hosted correctly; complete portal verification.

### Phase 13 — Meta manual post helper (P2)
- Build one-click copy/export helpers for FB/IG (full automation blocked by Meta app review)

### Code health (P3)
- Refactor `server.py` (~4,000 lines) into FastAPI `APIRouter` modules.

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
- ✅ Programmatic SEO pages + sitemap.
- ✅ Content auto-pilot: daily lessons + Monday flagship paths + quality gate.
- ✅ Lead magnet capture + AI Roadmap resource + welcome drip.
- ✅ Lifecycle automation: trial-ending, winback, streak-saver, annual upsell.
- ✅ Social pipeline content generation and admin preview.

### Coursiv-style engagement loop — LARGELY ACHIEVED ✅ / ONGOING 🟡
- ✅ Streak tracking + milestone celebrations.
- ✅ AI onboarding quiz + personalized plan.
- ✅ 15-day challenge roadmap.
- ✅ Interactive lesson cards + prompt libraries + browser-native TTS.

### Practice-first learning — TARGET STATE (Phase 20)
- 🟡 Layer 1: Try-It-Live practice + Portfolio ships and measurably increases lesson completion and retention.
- 🔜 Layer 2: Capstones required for certificates.
- 🔜 Layer 3: Spaced practice drills improve long-term retention.
- 🔜 Trophy Case enables shareable outcomes (social proof).

### Business metrics quality bar — ACHIEVED ✅
- ✅ Admin analytics endpoints exclude internal accounts while keeping real free-tier leads.

### Legal + security baseline — ACHIEVED ✅
- ✅ Terms / Privacy / No Refunds pages exist and are linked in footer.
- ✅ Signup flow enforces agreement.
- ✅ security.txt hosted.
- ✅ TikTok verification file hosted.

### Social auto-posting — STATUS (platform-driven)
- 🟡 X posting requires Pay-Per-Use credits (business decision) and credential rotation (security).
- 🟡 TikTok posting requires audit approval and a full integration build; verification in progress.

---

## 5. Operator / Environment Notes
- Two environments exist (Preview vs Production). Code changes land in preview; operator redeploy is required to push to production.
- **Stripe keys:** Production should use **Restricted Key (`rk_live_…`)** in deployment secrets; Standard Secret Key (`sk_live_…`) should never be used in deployments.
- Avoid pasting any secrets into chat or screenshots. Rotate immediately if exposed.
- **Active security action:** X OAuth 2.0 credentials were exposed in chat; rotate them in the X Developer Portal and update deployment env vars (do not share in chat).
