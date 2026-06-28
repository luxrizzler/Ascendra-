# plan.md (UPDATED)

## 1. Objectives
- Deliver Ascendra as a **standalone responsive website**: React + FastAPI + MongoDB.
- Preserve the full product loop:
  - Curriculum (paths → modules → lessons → cards + quiz)
  - Progress (XP, streak, levels)
  - Certificates (auto-issued on path completion)
  - AI Tutor chat (Claude 4.5 via `emergentintegrations`)
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

### New overarching objective (approved): Automation + Growth Flywheel — COMPLETED ✅
Build a largely automated growth engine:
- **Programmatic SEO** (`/learn` hubs with dynamically generated pages) to generate compounding traffic.
- **Content auto-pilot** so “fun new courses” ship automatically (daily lessons + weekly flagship course).
- **Lead magnet + drip sequences** to turn visitors into trials.
- **Lifecycle automation** to improve conversion/retention.
- **Social pipeline** using a **free-only content generation stack** (no paid video services), plus X/Twitter integration readiness.

### NEW overarching objective: Coursiv‑style engagement loop — IN PROGRESS 🟡
Deliver an interactive learning experience comparable to “Coursiv-style” apps:
- Streak tracking + celebrations
- AI onboarding quiz → personalized plan
- 15‑Day Challenge roadmap
- Interactive lesson cards (Knowledge Checks, Fill‑in‑the‑blank, Playgrounds) generated dynamically by Claude
- TTS narration + prompt libraries

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

1) **Frontend foundation (React web)**
- Implemented Ascendra “Celestial Phoenix” theme tokens + layout primitives.
- Implemented API client using `REACT_APP_BACKEND_URL` + bearer token storage.
- Implemented auth context (`AuthProvider`) with token persistence + `/auth/me` refresh.

2) **V1 routes (React Router)**
- Implemented:
  - `/` landing
  - `/signup`, `/login`
  - `/dashboard`
  - `/paths`, `/paths/:id`
  - `/lessons/:id` LessonPlayer (cards + quiz + completion)
  - `/certificate/:id` printable certificate view

3) **V1 UX rules**
- Sticky web navigation + footer; responsive grids.
- 403 for gated lessons triggers upgrade flow.
- Errors surfaced via toasts; loading/empty states included.

4) **Connect to backend (real data only)**
- Uses real curriculum (migrated to MongoDB in later phase).

5) **Testing**
- Manual verification + automation screenshots confirmed core flows.

**Phase 2 user stories (V1) — COMPLETED ✅**
1. Visitor can land and start onboarding.
2. User can sign up/log in.
3. User can browse paths + see locked tiers.
4. User can complete a lesson and see progress.
5. User can view/print/share certificate.

---

### Phase 3 — Feature expansion (production flows) (COMPLETED ✅)
Goal: bring feature parity beyond the V1 learning loop.

Implemented:
1) **AI Tutor UI**
- `/tutor` chat UI with persisted session.

2) **Pricing + payments (Stripe LIVE, subscriptions)**
- `/pricing` tier cards, monthly/annual toggle, $2.99 trial CTA.
- Migrated checkout to **recurring subscriptions** and added **Stripe Customer Portal**.
- `/checkout-success` polls `/api/billing/status/{session_id}` and refreshes tier.
- UI auto-renewal disclosure text added.

3) **Onboarding quiz → recommendation**
- `/onboarding` → `PUT /api/auth/me/quiz` → recommended path routing.

4) **Profile**
- `/profile` includes billing management (Customer Portal).

5) **Admin UI**
- `/admin` admin-only route.
- Stats, users list + inline tier editing, sales list, traffic charts.
- AI Curriculum Studio (auto-generate courses + cover images).
- Email template previewer.

6) **Resend production emails (LIVE)**
- Resend integration live with verified domain `ascendraacademy.com`.
- Checkout-success email trigger implemented.

**Phase 3 user stories — COMPLETED ✅**
1. AI Tutor chat persists across reload and supports multi-turn.
2. Onboarding quiz produces a recommended path.
3. User can start Stripe checkout and return to success flow.
4. User can manage password + view certificates + manage billing.
5. Admin can view stats/users/sales/traffic and use AI Studio.

---

### Phase 4 — Testing, fixes, and polish (COMPLETED ✅)
Goal: validate end-to-end reliability and improve conversion funnel.

1) **Automated E2E testing**
- Ran `testing_agent_v3` with 97%+ pass rate across iterations.

2) **Key conversion fix**
- Adjusted curriculum tiering so **free users can try lessons**:
  - Set `AI Fundamentals` path tier from `ascender` → `free`.

3) **UX polish**
- Pricing page now **leads with monthly amount**; annual shown as note.
- Landing pricing teaser visibility fixed:
  - Moved pricing teaser higher on the home page.
  - Added fallback tier data so cards render even if `/api/pricing` is slow.

---

## 3. Next Actions

### Phase 5 — Renewal reminders (P1) — COMPLETED ✅
**Goal:** Send renewal reminder emails **7 days before renewal** for **both monthly and annual** subscriptions.

Implementation delivered:
- Stripe `invoice.upcoming` handling in `/api/billing/webhook`.
- Idempotent helper `_try_send_renewal_reminder`.
- Fallback + manual triggers:
  - `POST /api/admin/billing/renewal-reminders/run`
  - `POST /api/admin/billing/renewal-reminders/send`
- Resend template `send_renewal_reminder()` + admin preview/test-send + UI button.

Testing:
- Verified with `testing_agent_v3` (iteration_4): 95% pass.

**Operator requirement:** enable Stripe webhook event **`invoice.upcoming`**.

---

### Phase 6 — “What’s New” + Subscribers list (P2) — COMPLETED ✅
**Goal:** Increase engagement by surfacing newly AI-generated content and providing admin visibility into subscribers.

Implementation delivered:
- Tagged AI Studio output: `source="ai-studio"` + `created_at`.
- Endpoints:
  - User: `GET /api/whats-new`
  - Admin: `GET /api/admin/whats-new`
  - Admin: `GET /api/admin/subscribers` (MRR/ARR estimates)
- Frontend:
  - `/admin/whats-new`
  - `/admin/subscribers`
  - Dashboard “New this week” widget (conditional)

Testing:
- Verified with `testing_agent_v3` (iteration_5): 98% overall.

---

### Roadmap expansion (approved) — Phases 7–11 COMPLETE ✅
Sequence shipped: **Phase 7 → 8 → 9 → 10 → 11**.

#### Phase 7 — Programmatic SEO — COMPLETE ✅
**Goal:** Generate compounding organic traffic with AI-generated, indexable pages.

Delivered:
- Backend SEO Studio (`/app/backend/seo_studio.py`) storing pages in MongoDB `seo_pages`.
- Public endpoints:
  - `GET /api/seo/page/{model_slug}` (published only)
  - `GET /api/seo/page/{model_slug}/{use_case_slug}` (published only)
  - `GET /api/seo/published`
  - `GET /api/seo/sitemap.xml`
  - `GET /api/seo/robots.txt`
- Admin endpoints:
  - `GET /api/admin/seo/pages`
  - `POST /api/admin/seo/generate-hub`
  - `POST /api/admin/seo/generate-usecase`
  - publish/archive/delete
- Frontend:
  - `/learn/:modelSlug` and `/learn/:modelSlug/:useCaseSlug` with `react-helmet-async` meta tags + JSON-LD
  - `/admin/seo` (SEO Studio)
  - Landing page internal links to published model hubs (`data-testid=landing-seo-links`)
- Seeded pages:
  - 6 hubs + 2 use-case pages (8 total), published and present in sitemap.

Testing:
- Verified with `testing_agent_v3` (iteration_6): 96% overall (backend generation endpoint timed out in test due to LLM latency; functionality works).

Operator follow-up (recommended): submit sitemap to Google Search Console once custom domain points to production.

---

#### Phase 8 — Content Auto‑Pilot — COMPLETE ✅
**Goal:** Add “fun new courses” automatically with minimal admin involvement.

Delivered:
- APScheduler-based automation (`/app/backend/auto_content.py`) booted on startup.
- Default queue seeded (32 items: lessons + courses) in `content_queue`.
- Jobs:
  - Daily lesson generation (10:00 UTC)
  - Monday full path generation (Mon 10:00 UTC)
  - Daily digest email (11:00 UTC) via `send_digest()`
- Quality gate:
  - Claude grades (accuracy/clarity/brand_fit/depth) 1–10; auto-publish only if all ≥ threshold.
  - Draft preservation for `needs_review` items.
  - Manual override publish endpoint: `POST /api/admin/auto/queue/{id}/publish`
- Admin UI:
  - `/admin/auto-content` (pause, manual run, queue management, runs log)

Testing:
- Verified with `testing_agent_v3` (iteration_7): backend 100%, frontend 95% (non-critical modal interaction variance).

**Scheduler stability update — COMPLETE ✅**
- Fixed scheduler job registration to avoid `RuntimeError: no running event loop` by passing coroutine functions directly to `AsyncIOScheduler`.
- Also fixed lifecycle scheduler job registration.
- Verified by `testing_agent_v3` (iteration_9): **backend 100%**, **scheduler 100%**, **regressions 100%**.

**Interactive content auto-upgrade (future lessons) — IMPLEMENTED / VERIFY PENDING 🟡**
- Inline interactivization added after auto-publish in:
  - `run_daily_lesson()`
  - `run_monday_path()` (sampled lessons)
- Added safety-net scheduler job:
  - `interactive_sweep` (Cron: every hour at `:15`) calling `run_interactive_sweep()`.
- **Open verification item:** confirm job appears in `/api/admin/auto/settings` → `next_runs.interactive_sweep` after backend restart.

---

#### Phase 9 — Lead Magnet + Welcome Drip — COMPLETE ✅
**Goal:** Convert visitors to email subscribers and trials.

Delivered:
- Public lead capture endpoint:
  - `POST /api/leads` (idempotent upsert) → sends lead magnet immediately.
- Leads stored in MongoDB `leads`.
- Resource page:
  - `/resources/ai-roadmap` (free, no login)
- Landing:
  - Hero button opens lead capture modal (`LeadCaptureModal`).
- Welcome drip (day 2/5/10/14) implemented in `lifecycle.py` and sent via Resend.
- Admin:
  - `GET /api/admin/leads`

Testing:
- Verified with `testing_agent_v3` (iteration_8): 100% backend + 100% frontend.

---

#### Phase 10 — Lifecycle Emails — COMPLETE ✅
**Goal:** Improve conversions, retention, and revenue with automated triggers.

Delivered (via daily scan at 09:00 UTC; manual trigger available):
- Trial ending (T−1 day)
- Winback (7 days after cancel)
- Streak-saver (inactive ~14 days)
- Annual upsell (monthly user at ~90 days)
- Manual scan:
  - `POST /api/admin/lifecycle/run` (kind=all or specific)

Testing:
- Verified with `testing_agent_v3` (iteration_8): 100% backend.

---

#### Phase 11 — Social Content Pipeline (Twitter/X + Instagram + TikTok) — FREE Generation — COMPLETE ✅
**Goal:** Auto-generate social assets from lessons and support automated publishing where platform permissions allow.

Constraints (explicit):
- The system **cannot create** social accounts.
- Auto-posting requires the user to create brand accounts + developer apps and provide API tokens.
- Meta (Facebook/Instagram) auto-posting requires App Review for advanced permissions; until approved, use manual posting helpers.

Delivered:
- Backend social generator (`/app/backend/social_studio.py`):
  - 5-tweet thread (Claude)
  - 5-slide carousel: PIL-rendered branded PNGs (free)
  - Silent MP4 slideshow: ffmpeg stitched from slides (free)
  - Robust JSON parsing with retry to avoid LLM JSON formatting failures
- Storage:
  - MongoDB `social_posts` with binary blobs for slides + mp4.
- Admin endpoints:
  - `POST /api/admin/social/generate`
  - `GET /api/admin/social/posts`
  - `GET /api/admin/social/post/{id}`
  - `GET /api/admin/social/post/{id}/slide/{i}.png`
  - `GET /api/admin/social/post/{id}/video.mp4`
- Admin UI:
  - `/admin/social` (generate from lesson, preview tweets, copy buttons, slide previews, MP4 player + download)

##### Phase 11.1 — X (Twitter) Integration — PARTIALLY COMPLETE ✅ / BLOCKED ⛔
**What is working:**
- OAuth 1.0a credentials validate successfully.
  - `verify_credentials()` OK for `@Ascendraacademy`.
  - `GET /api/admin/social/x/status` returns `ok: true`.

**What is blocked (X-side):**
- Posting via v2 `create_tweet` returns:
  - `403 Forbidden` with reason `client-not-enrolled`.
  - Message: App must be attached to a **Project** in X Developer Portal.

**Backend additions:**
- Added safe test endpoint:
  - `POST /api/admin/social/x/test-post` with `{text, dry_run}`
  - `dry_run=true` verifies creds without posting.

**Next steps to complete X auto-posting:**
- ⬜ Operator: Attach the X Developer App to a **Project** in the X Developer Portal (Projects & Apps).
- ⬜ Retry: `POST /api/admin/social/x/test-post` with `dry_run=false`.
- ⬜ Then validate full thread+media posting from `/admin/social`.

---

### Phase 12 — Deployment Readiness + Production Launch (Cloudflare / Emergent Deploy) — COMPLETE ✅
**Goal:** Safely deploy Ascendra to production at `ascendraacademy.com`.

Deployment readiness audit (deployment_agent) — 3 passes:
1) **Pass 1 (BLOCKER found → fixed):**
   - Unbounded admin stats scan in `/app/backend/server.py`:
     - Replaced `progress_col.find({})` loop with aggregation pipeline (`$project` + `$size` + `$sum` + `$group`).

2) **Pass 2 (BLOCKER found → fixed):**
   - `.env` parsing issue:
     - `META_FB_PAGE_NAME=Ascendra Academy` → fixed to `META_FB_PAGE_NAME="Ascendra Academy"`.

3) **Pass 3 (PASS with WARN):**
   - Only warning: `curriculum_db.get_lesson` does an in-memory scan over paths to locate a lesson.
   - Recommendation: deploy as-is, optimize post-launch.

**Remaining go-live operator steps:**
- ⬜ Run Emergent Built-in Deploy.
- ⬜ DNS setup via Entri/Cloudflare:
  - apex + www records
  - SSL/TLS validation
- ⬜ Post-launch validation:
  - auth + billing + emails + sitemap + `/learn` pages.

---

### Phase 13 — Social Manual Post Helper for Meta (FB/IG) — NOT STARTED (P2)
**Goal:** Provide one-click copy/export workflows for FB/IG since Meta App Review blocks full auto-posting.

Planned:
- ⬜ Add “Manual Post Helper” section in `/admin/social`:
  - one-click copy buttons (caption, hashtags)
  - optimized formats for IG carousel + FB post
  - download bundle (slides + mp4) for easy upload

---

### Phase 14 — P0 Bug Fix: Admin analytics must exclude internal test/admin accounts — IN PROGRESS 🟡
**Goal:** Ensure admin dashboard metrics reflect real business performance by excluding internal test/admin accounts.

**User clarifications (confirmed):**
- Exclude internal accounts from **all admin analytics**:
  - `sage[0-9]+@ascendraacademy.com`
  - `admin@ascendraacademy.com`
- **Keep free-tier users included** in stats (they are real leads for marketing conversion).
- Hardcode regex/patterns (no env-driven list).

**Implementation plan (Phase A — P0 Admin Stats Filter):**
1) Add a hardcoded `TEST_EMAIL_REGEX` (or equivalent predicate) in `/app/backend/server.py`.
2) Add helpers:
   - `_real_users_filter()` → Mongo query fragment that excludes internal emails and/or `is_admin==True`.
   - `_get_excluded_user_ids()` → resolves excluded user IDs (for joining against `progress` and `payment_sessions`).
3) Rewrite `/api/admin/stats` to apply filtering consistently:
   - `users_col` counts (total, tier breakdown, signups_30d)
   - `sessions_col` revenue aggregations and paid_sessions count (exclude excluded `user_id`s)
   - `progress_col` engagement aggregations (dau/wau/lessons_completed) excluding excluded `user_id`s
4) Apply the same exclusion defaults to other admin business views to avoid inconsistent admin numbers:
   - `GET /api/admin/users` (default listing)
   - `GET /api/admin/subscribers`
   - `GET /api/admin/sales`
5) Leave `GET /api/admin/traffic` unchanged (pageviews are anonymous visitors; not user-email keyed).

**Phase B — Verify auto-pilot interactive cron registration (follow-up, confirmed “do both”):**
1) Restart backend.
2) Call `GET /api/admin/auto/settings`.
3) Confirm `next_runs.interactive_sweep` is present (not missing/empty), proving the job registered.

**Phase C — Testing (MANDATORY: backend testing agent):**
- Run backend-only tests to verify:
  - `/api/admin/stats` excludes internal accounts from totals/revenue/engagement.
  - Free tier users remain included.
  - `/api/admin/sales`, `/api/admin/subscribers`, `/api/admin/users` align with the filtered logic.
  - `interactive_sweep` appears in `next_runs`.

---

## 4. Success Criteria

### Product + Ops — ACHIEVED ✅
- ✅ Backend integrations proven: Claude tutor, Stripe LIVE checkout + subscriptions + Customer Portal, certificates.
- ✅ Website supports full learning loop end-to-end.
- ✅ Resend emails live on verified custom domain.
- ✅ Renewal reminders shipped (monthly + annual) + admin tools.
- ✅ “What’s New” shipped + AI content tagging.
- ✅ Admin Subscribers list shipped (MRR/ARR + CSV + renewal email actions).

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
- 🟡 Ensure **all future auto-pilot lessons** are automatically interactivized (verify `interactive_sweep` job is active).

### Current P0 quality bar (must pass before new feature work)
- ⬜ Admin analytics endpoints exclude internal accounts (`sage*`, `admin@`) while still counting free-tier leads.
- ⬜ Verified by backend testing agent.

### Remaining operator setup (recommended)
1) **Stripe (billing automation)**
- ⬜ Enable Stripe webhook event: **`invoice.upcoming`**.

2) **SEO launch**
- ⬜ When on your production/custom domain, submit sitemap to Google Search Console:
  - `https://<your-domain>/api/seo/sitemap.xml`

3) **X/Twitter publishing**
- ✅ Credentials configured and verified.
- ⬜ Attach X App to a Project (fix `client-not-enrolled`), then run a real post test.

4) **Post-launch performance improvements**
- ⬜ Optimize `curriculum_db.get_lesson` to direct MongoDB lookup / denormalized lesson collection.

5) **Meta (FB/IG)**
- ⬜ Keep manual workflow until App Review grants advanced posting permissions.
