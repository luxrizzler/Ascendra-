# plan.md (UPDATED)

## 1. Objectives
- Deliver Ascendra as a **standalone responsive website**: React (CRA) + FastAPI + MongoDB.
- Preserve the full product loop:
  - Curriculum (paths → modules → lessons → cards + quiz)
  - Progress (XP, streak, levels)
  - Certificates (auto-issued on path completion)
  - AI Tutor chat (Claude Sonnet 4.5 via `emergentintegrations`)
  - Pricing/checkout (Stripe **LIVE**, recurring subscriptions + Customer Portal)
  - Admin dashboard (stats/users/sales/traffic)
- Web-first UX: sticky nav, responsive grids, accessible lesson player, share/print certificates.
- Ensure **free users can experience the product**: the intro “AI Fundamentals” path is accessible on the free tier.
- Production integrations:
  - Stripe LIVE subscriptions + Customer Portal
  - Resend transactional emails from verified domain `ascendraacademy.com`
  - Emergent-managed Google OAuth
- **Next-phase deliverables (sequential ship)**:
  1) Renewal reminders (monthly + annual) 7 days before renewal
  2) “What’s New” (admin + user-facing) surfacing recent AI-generated lessons + Admin Subscribers list
  - Promo/discount codes: **explicitly out of scope for now**

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

3) **UX polish (recent)**
- Pricing page now **leads with monthly amount**; annual shown as note.
- Landing pricing teaser visibility fixed:
  - Moved pricing teaser higher on the home page.
  - Added fallback tier data so cards render even if `/api/pricing` is slow.
- Verified via `testing_agent_v3` (100% for this specific fix).

---

## 3. Next Actions

### Immediate (Planned, sequential)

#### Phase 5 — Renewal reminders (P1) — NOT STARTED
**Goal:** Send renewal reminder emails **7 days before renewal** for **both monthly and annual** subscriptions.

Implementation approach:
1) **Backend billing logic**
- Add Stripe `invoice.upcoming` (and/or scheduled job logic) handling to calculate the upcoming renewal date and determine if it is 7 days away.
- Store “last renewal reminder sent” markers in MongoDB to avoid duplicates.

2) **Email sending (Resend)**
- Add new HTML email template: renewal reminder.
- Include: plan name, renewal date, amount, manage billing link (Customer Portal), support contact.

3) **Trigger mechanism**
- Implement a safe, idempotent mechanism:
  - Webhook-driven where possible, plus a scheduled fallback (cron-like) to query upcoming invoices daily.
- Ensure resilience to Stripe event retries.

4) **Testing**
- Add test checklist + run `testing_agent_v3` to validate:
  - Reminder logic does not spam
  - Portal link works
  - Emails send from `noreply@ascendraacademy.com`


#### Phase 6 — “What’s New” + Subscribers list (P2) — NOT STARTED
**Goal:** Increase engagement by surfacing newly AI-generated content and providing admin visibility into subscribers.

1) **What’s New (admin + user-facing)**
- Backend:
  - Persist metadata on AI-generated entities (created_by=AI Studio, created_at, published flag).
  - Create endpoints to fetch “recent AI-generated lessons/paths.”
- Admin UI:
  - New section/page (e.g. `/admin/whats-new`) showing recent items with filters.
- User Dashboard:
  - Add “New this week” widget showing latest AI-generated lessons/paths with direct deep links.

2) **Subscribers list (admin)**
- Backend:
  - Add an endpoint to list subscribers with Stripe subscription status and plan:
    - active/canceled/past_due
    - tier, interval, start date, renewal date (where available)
- Admin UI:
  - Add a table view: subscriber email, plan, status, next renewal, created date.

3) **Testing**
- Run `testing_agent_v3` to validate:
  - Subscriber list loads and is admin-protected
  - “What’s New” appears on dashboard for regular users
  - Admin filtering works and doesn’t break existing admin pages


### Explicitly out of scope (for now)
- Discount/promo codes: **skipped per user direction** (no discounts available).

---

## 4. Success Criteria
- ✅ Backend integrations proven: Claude tutor, Stripe LIVE checkout + subscriptions + Customer Portal, certificates.
- ✅ Website supports full learning loop end-to-end:
  - Landing → signup/login → onboarding → paths → lesson player → completion → progress update → certificate.
- ✅ Responsive UI (mobile + desktop) with Celestial Phoenix theme and brand artwork.
- ✅ Real curriculum stored in MongoDB + Admin AI Studio for generation.
- ✅ Resend emails live on verified custom domain.
- ✅ Recent bugfix: pricing teaser cards are visible on home page; pricing display leads with monthly.
- **Next**:
  - ⬜ Renewal reminders sent 7 days before renewal (monthly + annual) without duplicates.
  - ⬜ “What’s New” surfaced to users + admin view + admin subscribers list.