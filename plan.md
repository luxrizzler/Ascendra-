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

### Production integrations
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
- **Social pipeline** using a free-only content generation stack **plus** a practical distribution workflow.

### NEW overarching objective: Coursiv‑style engagement loop — LARGELY ACHIEVED ✅ / ONGOING 🟡
Deliver an interactive learning experience comparable to “Coursiv-style” apps:
- Streak tracking + celebrations
- AI onboarding quiz → personalized plan
- 15‑Day Challenge roadmap
- Interactive lesson cards (Knowledge Checks, Fill‑in‑the‑blank, Playgrounds) generated dynamically by Claude
- TTS narration + prompt libraries

### NEW overarching objective: Practice-first learning (better-than-Coursiv) — ACHIEVED ✅ (Layers 1–3) + ONGOING 🟡
Add **applied practice** throughout courses so users learn by doing:
- Layer 1: **Try It Live** (rubric-graded practice tasks with AI feedback) + Portfolio
- Layer 2: **Module Capstones** (mandatory to earn module/path certificates)
- Layer 3: **Spaced Practice Drills** (3/7/21-day review prompts based on struggles)
- Bonus: **Trophy Case** (shareable showcase of achievements)

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

### NEW objective: Social distribution + auto-posting where feasible — Phase A ✅, Phase B ✅ (code) / 🟡 (operator setup)
- Phase A: Manual post helper + export tooling for X/FB/IG/TikTok.
- Phase B: Full OAuth + auto-posting for Meta (FB + IG) and TikTok, plus signed media URLs for platform pull.
- Remaining: operator must create platform apps + paste credentials in `.env` + complete audits/reviews.

### NEW objective: Centralized, secure Revenue Control Center (RCC) backend governance
- Build a centralized, audit-ledger-driven admin backend to manage approvals, financial integrity, workflows, and automation *without permitting live actions*.
- Current status (as of this update):
  - RCC Phases 1–4 are **built + integrated + heavily tested**.
  - ✅ Phase 21 (Phase 3/4 Control-Integrity Hardening) is **complete**.
  - ✅ Phase 22 (Phase 5 Executive RCC — minimal) is **complete**.
  - ✅ Phase 24 (Phase 5 sign-off) is **complete** — `COMPLETED_PHASES` now includes `phase_5`.
  - ✅ Phase 25 (Phase 5b scripted simulation harness) is **complete**.
  - ✅ Phase 26 (Cohort analytics: MRR + retention) is **complete**.
  - ✅ Phase 27 (Governance runbook + printable UI) is **complete**.

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

### Phases 7–12 — Growth, automation, deployment readiness — COMPLETED ✅
- Phase 7 Programmatic SEO
- Phase 8 Content Auto‑Pilot (APScheduler) + quality gate
- Phase 9 Lead magnet + welcome drip
- Phase 10 Lifecycle emails
- Phase 11 Social content generation pipeline (tweets + carousel + MP4)
- Phase 12 Deployment readiness + production launch blockers fixed

**Interactive content auto-upgrade — VERIFIED ✅**
- Inline interactivization after publish in `run_daily_lesson()` and sampled lessons in `run_monday_path()`
- Safety-net: `interactive_sweep` hourly cron

---

### Phase 13 — Social Studio Distribution + Platform Integrations

#### Phase 13A — Social Studio bug fixes + Manual Distribution Helper — COMPLETED ✅
**Goal:** Make `/admin/social` immediately usable for consistent posting across platforms without needing expensive APIs.

**What shipped:**
1) **Bug fixes / gaps closed**
- Added Facebook to platform status and distribution UI.
- Wired the existing backend X auto-post route into the UI (previously dead code).

2) **Manual Distribution Panel (multi-platform)**
- `/admin/social` now includes a Distribution Panel for:
  - X: copy thread + compose link + auto-post button when configured
  - Facebook: copy caption + download slides + open composer
  - Instagram: copy caption + download slides + open Business Suite
  - TikTok: download MP4 + copy caption + open upload

3) **Platform Settings page**
- Added `/admin/social/settings`:
  - Shows platform configuration status
  - Provides step-by-step token/app setup instructions
  - Offers connection tests for X

4) **Backend support**
- Added `GET /api/admin/social/settings` to report per-platform `.env` configuration readiness.

---

#### Phase 13B — Auto-posting integrations (Meta + TikTok) — COMPLETED ✅ (code) / 🟡 (operator setup)
**Goal:** Implement real OAuth-based auto-posting for Facebook Pages, Instagram Business, and TikTok.

**Key technical blocker solved:**
- Meta/TikTok must fetch media directly by URL (no admin JWT). Added **signed media URL** system.

**Status:**
- ✅ Code shipped and smoke-tested in Preview.
- 🟡 Operator must complete developer portal setup + add `.env` variables + complete platform reviews/audits.

---

### Phase 14 — P0 Bug Fix: Admin analytics must exclude internal accounts — COMPLETED ✅
- Added `TEST_EMAIL_REGEX` + helper filters
- Updated `/api/admin/stats`, `/api/admin/users`, `/api/admin/sales`, `/api/admin/subscribers`
- Verified with backend tests

---

### Phase 15 — Admin Auto‑Pilot Queue UX Upgrade (P1) — COMPLETED ✅
- Regenerate / reject / draft editing endpoints
- Admin UI controls
- Self-healing queue support

---

### Phase 16 — User‑Generated Learning Paths — COMPLETED ✅
- Paid-only generation, pending review, admin approve/reject

---

### Phase 17 — Smart Subscription Management Card — COMPLETED ✅
- In-app resume/reactivate logic while preserving cert retention

---

### Phase 18 — Landing-page onboarding quiz popup — COMPLETED ✅

---

### Phase 19 — Legal + Security Compliance — COMPLETED ✅
- `/terms`, `/privacy`, `/no-refunds` + footer + signup checkbox
- security.txt
- TikTok domain verification file (byte-exact)
- SEO/robots updates + JSON-LD

---

### Phase 20 — Practice Lab + Capstones + Drills + Trophy Case — COMPLETED ✅
- Layer 1: Try-It-Live + Portfolio
- Layer 2: Module Capstones
- Layer 3: Spaced Drills
- Trophy Case UI
- Admin content health autoscan + auto-pilot queue self-healing

---

### Phase 21 — Revenue Control Center (RCC): Phase 3/4 Control-Integrity Hardening (P0) — COMPLETED ✅
**Mandatory order followed:** Hardening → Phase 5 → Tests → Report.

**Delivered (all shipped + tested):**

#### 21.1 Approval enforcement on sensitive Phase 3 endpoints
- `enforce_approval()` wired on:
  - Tax-policy activate
  - Allocation-policy activate (**new endpoint**)
  - Owner-draw decision
  - Reconciliation close
- Strict verification: request_type + target_id match; approved; not-yet-consumed
- On success: approval is consumed append-only via `mark_approval_completed()`

#### 21.2 Allocation-policy status semantic split
- Added: `approved`, `enabled_for_phase`, `currently_applied`
- Startup migration: `migrate_allocation_policy_semantics()`
- Invariant: exactly one `currently_applied=true` policy per phase
- Legacy `active` preserved

#### 21.3 Append-only owner-draw corrections
- New endpoints:
  - `POST /api/admin/revenue/owner-draws/{id}/adjustment`
  - `POST /api/admin/revenue/owner-draws/{id}/reversal`
  - `GET  /api/admin/revenue/owner-draws/{id}/payments`
- Requires approvals; never mutates prior rows; link fields enforce traceability

#### 21.4 Stripe shadow webhook verification hardened
- Official Stripe SDK verification:
  - `stripe.Webhook.construct_event(payload, sig_header, secret, tolerance=300)`
  - signature header: `t=<ts>,v1=<sig>`
- Secret precedence:
  - `STRIPE_WEBHOOK_SECRET_TEST` → `STRIPE_WEBHOOK_SECRET` → `test-shadow-secret`
- Legacy HMAC fallback preserved and labeled `verification_mode=legacy_hmac`

#### 21.5 Hardening test coverage
- Added `/app/tests/test_revenue_phase_hardening.py` (8 tests)

---

### Phase 22 — RCC: Phase 5 Executive RCC (minimal) (P1) — COMPLETED ✅
- `revenue_phase5.py` wired into `server.py` + startup seed of Financial Constitution
- Executive endpoints label `source_state` and `is_stub`
- Funnel reporting endpoint:
  - `GET /api/admin/revenue/executive/funnel` (simulated rows excluded)
- Frontend Executive tab shipped

---

### Phase 23 — RCC Phase 5 Completion Report (P2) — COMPLETED ✅
- Hardening-first requirement satisfied
- Phase 5 shipped, tested, and signed off
- Plan updated to reflect completed work and safety invariants

---

### Phase 24 — RCC Phase 5 Sign-Off (Operator acceptance) — COMPLETED ✅
- Updated `/app/backend/revenue.py`:
  - `COMPLETED_PHASES` now includes `phase_5`
- Updated stale tests that asserted `phase_5` was not complete
- Updated `AdminRevenue.js` header kicker:
  - “Phase 1 + 2 + 3 + 4 + 5 approved · executive layer signed off”

---

### Phase 25 — RCC Phase 5b Scripted Simulation Harness — COMPLETED ✅
- Replaced audit-only simulation stub with **10 scripted scenarios** that create real Phase 2/3/4 records in the **test DB only**, each tagged `simulated=True`:
  - `successful_subscription`
  - `failed_payment_recovery`
  - `abandoned_checkout`
  - `qualified_business_lead`
  - `refund_adjustment`
  - `chargeback_adjustment`
  - `reserve_transition`
  - `reserve_reversion`
  - `unsupported_question_escalation`
  - `prohibited_action_blocked`
- Simulation harness invariants:
  - Refuses non-test DB
  - Emits real records with `simulated=True`
  - Actual executive totals remain unchanged
- Frontend simulation badge updated:
  - “SCRIPTED · Phase 5b”

---

### Phase 26 — RCC Cohort Analytics (MRR + Retention) — COMPLETED ✅
- New endpoint:
  - `GET /api/admin/revenue/executive/cohorts`
- Outputs:
  - `mrr_by_cohort` (real cleared ledger payments only)
  - `mrr_deltas` (MoM deltas)
  - `retention_by_cohort` (real contacts only; simulated excluded)
- Frontend Executive tab:
  - Cohort Analytics panel with mini visualizations and empty state
- Tests added:
  - Shape/labels
  - Simulated ledger excluded from MRR
  - Simulated contacts excluded from retention

---

### Phase 27 — RCC Governance Runbook (Printable Operator Reference) — COMPLETED ✅
- Created:
  - `/app/docs/governance_runbook.md`
- New endpoint:
  - `GET /api/admin/revenue/executive/runbook` (reads markdown from disk)
- Frontend:
  - New “Governance Runbook” tab
  - Print button (browser print) + Download `.md` button
  - Print-friendly rendering

---

## 3. Next Actions

### Immediate (P0): Operator deployment + smoke test
1) Deploy preview → production (if desired)
2) Smoke test RCC tabs:
   - Executive summary renders
   - Simulation harness refuses non-test DB in production
   - Runbook tab loads and downloads

### Immediate (P0): Turn on Phase 13B in production (operator steps) — PENDING 🟡
1) **Meta setup**
- Create Meta App (Business type)
- Configure redirect:
  - `https://ascendraacademy.com/api/social/meta/callback`
- Add `.env`: `META_APP_ID`, `META_APP_SECRET`, `META_REDIRECT_URI`
- Restart backend → `/admin/social/settings` → Connect

2) **TikTok setup**
- Configure redirect:
  - `https://ascendraacademy.com/api/social/tiktok/callback`
- Add `.env`: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI`
- Restart backend → Connect → Submit audit

3) Optional: stable base URLs
- `PUBLIC_BASE_URL=https://ascendraacademy.com`
- `PUBLIC_FRONTEND_URL=https://ascendraacademy.com`

### Code health (P2)
- Refactor `server.py` into routers/modules (quality-of-life)

---

## 4. Success Criteria

### Product + Ops — ACHIEVED ✅
- ✅ Backend integrations proven: Claude tutor, Stripe LIVE checkout + subscriptions + Customer Portal, certificates.
- ✅ Website supports full learning loop end-to-end.
- ✅ Resend emails live on verified custom domain.

### Growth Flywheel — ACHIEVED ✅
- ✅ Programmatic SEO + sitemap.
- ✅ Content auto-pilot + quality gate.
- ✅ Lifecycle automation.
- ✅ Social studio generation + distribution helpers.

### RCC governance and integrity — ACHIEVED ✅ (Phases 21–27)
- ✅ Approval enforcement on sensitive Phase 3 actions
- ✅ Allocation policy semantic split + invariant
- ✅ Owner-draw corrections append-only
- ✅ Stripe shadow webhook uses official Stripe SDK signature verification
- ✅ Executive dashboard ships with honest labeling (`source_state`, `is_stub`)
- ✅ Simulation harness: scripted scenarios, test-only, quarantined `simulated=True`
- ✅ Cohort analytics: simulated rows excluded
- ✅ Printable governance runbook shipped + served via API + UI
- ✅ Tests pass:
  - `pytest`: **162/162**

### Legal + security baseline — ACHIEVED ✅
- ✅ Terms / Privacy / No Refunds pages exist and are linked in footer.
- ✅ Signup flow enforces agreement.

---

## 5. Operator / Environment Notes
- Two environments exist (Preview vs Production). Code changes land in preview; **click Deploy** to push to production.
- **Do not hardcode preview URLs** in code. Use env vars.
- Avoid pasting any secrets into chat or screenshots. Rotate immediately if exposed.

### Non-negotiable safety gates (recurring)
- `AUTOMATION_LIVE_ACTIONS_ENABLED=false` must remain false unless explicitly authorized.
- No live external API calls are permitted while safety gate is off.
- Financial math stays on `Decimal128` / Python `Decimal`.
- Tests remain isolated to `ascendra_revenue_test` via existing `conftest.py` patterns.

### Notes on design/dev workflow
- Design agent not invoked:
  - `AdminRevenue.js` already establishes the visual system.
  - Executive + Runbook tabs follow existing Tabs/Card patterns.
