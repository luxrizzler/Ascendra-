# plan.md

## 1. Objectives
- Convert `luxrizzler/Ascendra-` into a **standalone responsive website**: React (CRA) + FastAPI + MongoDB.
- Preserve core product flows: curriculum (paths/modules/lessons/cards+quiz), progress (XP/streak/levels), certificates, AI Tutor chat, pricing/checkout, admin.
- Rebuild UX for web: sticky top nav, responsive grids, accessible lesson player (swipe + buttons).

---

## 2. Implementation Steps

### Phase 1 — Core POC (Isolation): prove the “hard parts” work
Goal: validate external integrations + completion→certificate data flow **before** building full UI.

1) **Backend POC wiring (minimal, no frontend yet)**
- Port backend files from repo → `/app/backend/`:
  - `server.py`, `curriculum.py`, `email_service.py`, `seed_accounts.py`
- Remove/disable Expo static-site serving block (serve API only).
- Ensure env vars exist in `/app/backend/.env`:
  - `MONGO_URL`, `DB_NAME`, `JWT_SECRET_KEY`, `EMERGENT_LLM_KEY`, `STRIPE_API_KEY`, `PUBLIC_WEB_URL`
- Install/align backend deps in `/app/backend/requirements.txt` (bcrypt, PyJWT, motor, fastapi, httpx, stripe, emergentintegrations, resend, email-validator, python-dotenv).

2) **POC test scripts (run locally against FastAPI)**
- Write `backend/tests_poc/poc_core_flow.py`:
  - signup/login → fetch paths → fetch lesson → complete lesson → verify progress updates
  - simulate completing all lessons in 1 path → verify cert issued in Mongo + `GET /api/certificates`
- Write `backend/tests_poc/poc_tutor_chat.py`:
  - call `/api/tutor/chat` twice with same session_id → verify multi-turn works and `/api/tutor/history/{session_id}` returns both turns
- Write `backend/tests_poc/poc_stripe_checkout.py`:
  - call `/api/billing/checkout` (or `/subscribe` if configured) → assert checkout URL returned

3) **Websearch + confirm best practices (only for POC-sensitive integrations)**
- Quick websearch checklist for:
  - Stripe Checkout redirect/callback patterns in SPA
  - Claude/Anthropic chat persistence + rate-limit handling patterns

4) **Fix until green**
- Do not proceed until all three POC scripts pass and Mongo records look correct.

**Phase 1 user stories (POC)**
1. As a user, I can sign up and receive a JWT to access protected endpoints.
2. As a user, I can open a lesson and complete it, increasing XP and streak.
3. As a user, completing an entire path issues a certificate automatically.
4. As a user, I can chat with the AI Tutor across multiple turns in one session.
5. As a user, I can start a checkout session and receive a Stripe-hosted payment URL.

---

### Phase 2 — V1 Website (MVP build, minimal bulk passes)
Goal: ship a working website covering the main learning + certificate flow.

1) **Frontend foundation (React web)**
- Implement Tailwind theme tokens (Celestial Phoenix) + layout primitives.
- Create API client (axios/fetch) using `REACT_APP_BACKEND_URL` and bearer token.
- Auth: **defer advanced auth features**; keep simple email/password for V1 UI.

2) **V1 routes (React Router)**
- `/` landing (hero, pillars, pricing teaser CTA)
- `/signup`, `/login`
- `/paths`, `/paths/:id`
- `/lessons/:id` (LessonPlayer: swipe + next/prev buttons, quiz submit, completion)
- `/dashboard` (progress summary, recommended path if present)
- `/certificates` + `/certificate/:id` (printable view)

3) **V1 UX rules**
- Web nav (sticky) + footer; responsive grids for paths/pricing.
- Lock paywalled content: if lesson returns 403 → redirect to `/pricing`.
- All errors as toasts; loading/empty states on every page.

4) **Connect to backend (real data only)**
- Use `/api/paths`, `/api/paths/{id}`, `/api/lessons/{id}`, `/api/progress`, `/api/progress/complete`, `/api/certificates`.

5) **Testing**
- Run `testing_agent_v3` for 1 full pass of:
  - signup → browse paths → open lesson → complete → see XP/streak change → complete path (using small path) → view certificate.

**Phase 2 user stories (V1)**
1. As a visitor, I can land on the homepage and start onboarding via “Begin your ascent”.
2. As a user, I can sign up and log in on the web.
3. As a user, I can browse learning paths and see which are locked by tier.
4. As a user, I can complete a lesson (cards + quiz) and see progress update.
5. As a user, I can view and print/share my issued certificate.

---

### Phase 3 — Feature expansion (production flows)
Goal: bring parity with repo features beyond the V1 learning loop.

1) **AI Tutor UI**
- `/tutor` chat UI with session list/history; persist last session_id in localStorage.

2) **Pricing + payments**
- `/pricing` full tier cards, monthly/annual toggle, trial CTA
- `/checkout-success` polls `/api/billing/status/{session_id}` → updates tier badge

3) **Onboarding quiz → recommendation**
- `/onboarding` quiz UI → `PUT /api/auth/me/quiz` → route to recommended path

4) **Profile**
- `/profile` shows tier, change password, certificates list, billing portal (if enabled)

5) **Testing**
- Run `testing_agent_v3` for:
  - tutor chat, onboarding quiz recommendation, pricing checkout redirect, checkout success tier upgrade simulation.

**Phase 3 user stories**
1. As a user, I can chat with the AI Tutor and see my chat history after reload.
2. As a user, I can take the onboarding quiz and get a recommended learning path.
3. As a user, I can upgrade my plan using Stripe and see my tier updated.
4. As a user, I can view my subscription state and manage billing (when enabled).
5. As a user, I can reset my password via email link if I forget it.

---

### Phase 4 — Admin + hardening
Goal: ship admin dashboard + tighten reliability.

1) **Admin UI**
- `/admin` route guard (admin-only)
- Stats, users CRUD actions, sales list, traffic charts (match backend endpoints)

2) **Auth parity**
- Add Google OAuth (Emergent session token) UI flow.
- Add forgot/reset password UI + Resend integration verification.

3) **Hardening**
- Rate-limit sensitive endpoints (tutor chat, auth) if needed.
- Audit CORS origins for production.

4) **Testing**
- Run `testing_agent_v3` for admin login + stats/users views and key flows.

**Phase 4 user stories**
1. As an admin, I can view product stats (users/revenue/engagement/traffic).
2. As an admin, I can search users and update tier/access.
3. As a user, I can sign in with Google.
4. As a user, I can request a password reset and set a new password.
5. As an admin, I can review sales sessions and basic traffic trends.

---

## 3. Next Actions
1) Port backend into `/app/backend` and align `.env` + `requirements.txt`.
2) Implement and run the 3 POC scripts; fix until green.
3) Build Phase 2 V1 web routes + LessonPlayer + certificate pages.
4) Run `testing_agent_v3` after Phase 2 and iterate on failures.

---

## 4. Success Criteria
- POC passes: tutor chat works multi-turn, checkout returns URL, completion issues certificate.
- V1 website supports end-to-end learning loop: signup/login → path → lesson → complete → progress updated → certificate view.
- Responsive UI (mobile + desktop), with consistent Celestial Phoenix theme.
- No mock curriculum; all content served from backend curriculum.
- Automated test runs (testing_agent_v3) complete without critical failures at the end of each phase.
