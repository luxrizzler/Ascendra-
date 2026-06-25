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
- Ensure **free users can experience the product**: the intro “AI Fundamentals” path is accessible on the free tier.
- Production integrations:
  - Stripe LIVE subscriptions + Customer Portal
  - Resend transactional emails from verified domain `ascendraacademy.com`
  - Emergent-managed Google OAuth

### Completed “next-phase” deliverables (sequential ship) — COMPLETED ✅
1) Renewal reminders (monthly + annual) 7 days before renewal
2) “What’s New” (admin + user-facing) surfacing recent AI-generated lessons + Admin Subscribers list
- Promo/discount codes: **explicitly out of scope for now** (per user: “no discount available”)

### New overarching objective (approved): Automation + Growth Flywheel
Build a largely automated growth engine:
- **Programmatic SEO** to generate compounding traffic.
- **Content auto-pilot** so “fun new courses” ship automatically (daily lessons + weekly flagship course).
- **Lead magnet + drip sequences** to turn visitors into trials.
- **Lifecycle automation** to improve conversion/retention.
- **Social pipeline** using a **free-only content generation stack** (no paid video services), with posting integration ready once API tokens are provided.

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

### Immediate (Planned, sequential)

#### Phase 5 — Renewal reminders (P1) — COMPLETED ✅
**Goal:** Send renewal reminder emails **7 days before renewal** for **both monthly and annual** subscriptions.

Implementation delivered:
1) **Backend billing logic (webhook + idempotency)**
- Added Stripe `invoice.upcoming` handling in `/api/billing/webhook`.
- Added helper `_try_send_renewal_reminder` with idempotency fields on user.

2) **Fallback trigger (cron-like) + manual trigger**
- `POST /api/admin/billing/renewal-reminders/run` (scan ~6.5–7.5 day window)
- `POST /api/admin/billing/renewal-reminders/send` (manual per-user; `force=true`)

3) **Email templates (Resend)**
- Added `send_renewal_reminder()` template in `email_service.py`.
- Admin preview + test-send support.
- Admin Email UI includes a “Renewal Reminder” tab + “Run renewal scan” button.

4) **Testing**
- Verified with `testing_agent_v3`: 95% pass (minor 401 vs 403 expectation mismatch; unrelated sage login issue).

**Operational note (LIVE Stripe)**
- Recommended: enable Stripe webhook event **`invoice.upcoming`**.

---

#### Phase 6 — “What’s New” + Subscribers list (P2) — COMPLETED ✅
**Goal:** Increase engagement by surfacing newly AI-generated content and providing admin visibility into subscribers.

Implementation delivered:
- Tagged AI Studio output: `source="ai-studio"` + `created_at`.
- Added endpoints:
  - User: `GET /api/whats-new`
  - Admin: `GET /api/admin/whats-new`
  - Admin: `GET /api/admin/subscribers` (MRR/ARR estimates)
- Added frontend pages:
  - `/admin/whats-new`
  - `/admin/subscribers`
- Dashboard “New this week” widget (conditional).

Testing:
- Verified with `testing_agent_v3`: 98% overall; fixed timezone-naive datetime issue in `/admin/subscribers`.

---

### Roadmap expansion (approved) — NEW PHASES (sequential)
Sequence: **Phase 7 → 8 → 9 → 10 → 11**. User confirms at each phase boundary.

#### Phase 7 — Programmatic SEO (NEW)
**Goal:** Generate compounding organic traffic with AI-generated, indexable pages.

Scope:
- **Route set (decision: both)**:
  - `/learn/{model}` model hub pages
  - `/learn/{model}/{use-case}` sub-pages
- Auto-generated content blocks:
  - Intro + who it’s for
  - Learning outcomes
  - Curated internal links to existing paths/lessons
  - FAQs (schema-ready)
- Technical SEO:
  - `sitemap.xml` (dynamic or generated) + `robots.txt`
  - Canonicals, OpenGraph/Twitter cards
  - Per-page meta title/description
  - JSON-LD (FAQPage, Breadcrumb, Course where relevant)
- Content governance:
  - Admin “SEO Studio” queue: approve/edit/publish pages
  - Anti-duplication: uniqueness checks + similarity scoring

Success criteria:
- Pages render server-side friendly HTML (pre-render or backend-rendered payload).
- Sitemap includes all `/learn/*` pages.

---

#### Phase 8 — Content Auto‑Pilot (NEW)
**Goal:** Add “fun new courses” automatically with minimal admin involvement.

Cadence (user preference):
- **Daily lesson generation** (1 lesson/day)
- **Monday flagship course** (1 full path every Monday morning)

Implementation:
- Admin “Content Queue”:
  - Topic backlog (priority, difficulty, tier, target persona)
  - Per-topic generation settings
- Scheduler:
  - Daily job: generate 1 lesson into an existing path/module or as a micro-path
  - Monday job: generate a complete path (modules + lessons), optionally with cover image
- Quality gate (LLM-based):
  - Checks: clarity, correctness, hallucination risk, duplication, tone
  - Auto-publish if passes; otherwise keep as draft + notify admin
- Tagging:
  - Ensure `source="ai-studio"` + `created_at` for all auto-generated content
  - Ensure it shows up in What’s New

Success criteria:
- Content appears in `/admin/whats-new` and (when within window) on Dashboard widget.

---

#### Phase 9 — Lead Magnet + Welcome Drip (NEW)
**Goal:** Convert visitors to email subscribers and trials.

Scope:
- Landing page email capture with explicit consent + privacy copy.
- Lead magnet: “AI Roadmap PDF”
  - V1 can be a hosted HTML-to-PDF export generated by backend.
- 5-step welcome series via Resend:
  - Mixed short + value content (user preference “c”).
- Admin:
  - Lead list + export
  - Email template preview/test-send

Success criteria:
- Captures emails, sends magnet, starts drip sequence reliably.

---

#### Phase 10 — Lifecycle Emails (NEW)
**Goal:** Improve conversions, retention, and revenue with automated triggers.

Email types:
- Trial ending (T-1 day)
- Renewal reminders (already done; ensure `invoice.upcoming` enabled)
- Winback (7 days after cancel)
- Streak-saver (inactive for N days)
- Annual upsell (monthly user at day 90)

Implementation:
- Event triggers:
  - Stripe webhooks for subscription changes
  - Activity signals from app usage
  - Daily scheduler scan as fallback
- Mixed email format (short/long blend).
- Admin:
  - Template preview + test-send
  - Safety: rate limits and per-user frequency caps

---

#### Phase 11 — Social Pipeline (Twitter/X + Instagram + TikTok) — FREE-ONLY (NEW)
**Goal:** Auto-generate social assets from new content, publish automatically when tokens are provided.

Constraints:
- The system **cannot create** social accounts. User must create accounts + dev apps and provide API tokens.

Scope (free-only stack):
- Content generator:
  - Auto-generate tweet threads / captions from new path/lesson
  - Generate **carousel images** (using available image model via existing stack if free; otherwise template-based SVG → PNG)
  - Generate **silent slideshow MP4** using `ffmpeg` (no paid voice/video services)
- Posting layer:
  - Implement API clients + token storage (disabled until tokens present)
  - Dry-run mode logs payloads to DB + shows preview in admin
- Admin “Social Studio”:
  - Queue, preview, approve, publish
  - Post history + status

Success criteria:
- With tokens absent: assets still generated + queued + previewable.
- With tokens provided: posts publish and are logged.

---

### Explicitly out of scope (for now)
- Discount/promo codes: **skipped per user direction** (no discounts available).
- Automated creation of social accounts: not possible; requires human verification.

---

## 4. Success Criteria
### Product + Ops
- ✅ Backend integrations proven: Claude tutor, Stripe LIVE checkout + subscriptions + Customer Portal, certificates.
- ✅ Website supports full learning loop end-to-end.
- ✅ Resend emails live on verified custom domain.
- ✅ Renewal reminders shipped (monthly + annual) + admin tools.
- ✅ “What’s New” shipped + AI content tagging.
- ✅ Admin Subscribers list shipped (MRR/ARR + CSV + renewal email actions).

### Growth Flywheel (new)
- ⬜ Programmatic SEO pages + sitemap + schema.
- ⬜ Content auto-pilot: daily lessons + Monday flagship paths.
- ⬜ Lead magnet capture + 5-step welcome drip.
- ⬜ Lifecycle automation: trial-ending, winback, streak-saver, annual upsell.
- ⬜ Social pipeline: free-only asset generation now; auto-posting enabled once tokens are supplied.

**Remaining operator setup (recommended):**
- ⬜ Enable Stripe webhook event: **`invoice.upcoming`**.
- ⬜ (Later) Create social accounts + provide API tokens to enable auto-posting.