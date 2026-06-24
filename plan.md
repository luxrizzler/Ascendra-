# plan.md (UPDATED)

## 1. Objectives
- Deliver Ascendra as a **standalone responsive website**: React (CRA) + FastAPI + MongoDB.
- Preserve the full product loop from the GitHub repo:
  - Curriculum (paths → modules → lessons → cards + quiz)
  - Progress (XP, streak, levels)
  - Certificates (auto-issued on path completion)
  - AI Tutor chat (Claude Sonnet 4.5 via `emergentintegrations`)
  - Pricing/checkout (Stripe sandbox) + tier gating
  - Admin dashboard (stats/users/sales/traffic)
- Web-first UX: sticky top nav, responsive grids, accessible lesson player (buttons + swipe), share/print certificates.
- Ensure **free users can experience the product**: the intro “AI Fundamentals” path is accessible on the free tier.

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
  - `/api/paths` (10 paths) and `/api/models` (22 models)
  - `/api/progress/complete` updates XP/streak/level
  - `/api/tutor/chat` returns live Claude 4.5 output
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
  - `/` landing (brand hero, mission, models marquee, pillars, symbolism, pricing teaser)
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
- Uses real curriculum from `curriculum.py` (no mocked lessons).

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
Goal: bring feature parity with repo beyond the V1 learning loop.

Implemented:
1) **AI Tutor UI**
- `/tutor` chat UI with persisted session in localStorage
- History endpoint support

2) **Pricing + payments**
- `/pricing` full tier cards, monthly/annual toggle, $2.99 trial CTA
- `/checkout-success` polls `/api/billing/status/{session_id}` and refreshes tier

3) **Onboarding quiz → recommendation**
- `/onboarding` (4 steps) → `PUT /api/auth/me/quiz` → route to recommended path

4) **Profile**
- `/profile` account info, tier badge, change password, certificates list, subscription summary

5) **Admin UI**
- `/admin` admin-only route
- Stats, users list + inline tier editing, sales list, traffic charts

**Phase 3 user stories — COMPLETED ✅**
1. AI Tutor chat persists across reload and supports multi-turn.
2. Onboarding quiz produces a recommended path.
3. User can start Stripe checkout and return to success flow.
4. User can manage password + view certificates.
5. Admin can view stats/users/sales/traffic.

---

### Phase 4 — Testing, fixes, and polish (COMPLETED ✅)
Goal: validate end-to-end reliability and improve conversion funnel.

1) **Automated E2E testing**
- Ran `testing_agent_v3`:
  - 45/46 tests passed (97.8% overall)
  - Frontend pass rate: 100%

2) **Key fix from testing**
- Adjusted curriculum tiering so **free users can try lessons**:
  - Set `AI Fundamentals` path tier from `ascender` → `free`
  - Kept specialty paths gated (Pathfinder) and founder paths gated (Sage)
- Verified fresh signup can access `fundamentals` and complete lesson cards → quiz.

3) **Minor polish**
- Updated HTML metadata (title/description/theme-color) and added a minimal inline favicon.

**Phase 4 user stories — COMPLETED ✅**
1. New user can experience at least one full path without upgrading (Fundamentals).
2. Admin dashboard and protected routes validated.
3. Forgot/reset password validated (dev token flow when Resend not configured).

---

## 3. Next Actions
### Immediate (optional)
1) **Decide the free-to-paid funnel**
- Keep only Fundamentals free (current), or make the first module of additional paths free.

2) **Stripe production readiness**
- Add real Stripe keys + webhook secret.
- Confirm webhook signature handling and tier-expiration policy.

3) **Email production readiness**
- Add `RESEND_API_KEY` + verified sender domain.
- Remove `dev_reset_token` response when in production.

4) **Hardening**
- Add rate limiting for `/tutor/chat` and auth endpoints.
- Lock down CORS origins in production.

### Longer-term (optional)
5) **Google OAuth UI parity**
- Add a “Continue with Google” button wired to `/api/auth/google` session-token exchange.

---

## 4. Success Criteria
- ✅ Backend integrations proven: Claude tutor, Stripe checkout URL, certificates.
- ✅ Website supports full learning loop end-to-end:
  - Landing → signup/login → onboarding → paths → lesson player → completion → progress update → certificate.
- ✅ Responsive UI (mobile + desktop) with Celestial Phoenix theme and brand artwork.
- ✅ Real curriculum from backend (no mocks).
- ✅ Automated E2E tests pass at high rate; key conversion issue fixed (Fundamentals now free).
- ✅ Deployed preview available: **https://repo-to-site-2.preview.emergentagent.com**
