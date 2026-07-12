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
- Meta/TikTok must fetch media directly by URL (no admin JWT). We added a **signed media URL** system.

**What shipped:**
1) **Meta Graph API publisher (Facebook + Instagram)**
- New backend module: `/app/backend/meta_publisher.py`
- OAuth start + callback
- Stores long-lived Page token + linked IG Business ID in Mongo `social_credentials`
- Posting endpoints:
  - `POST /api/admin/social/post/{post_id}/post-to-facebook`
  - `POST /api/admin/social/post/{post_id}/post-to-instagram?as_reel=...`

2) **TikTok Content Posting API publisher**
- New backend module: `/app/backend/tiktok_publisher.py`
- OAuth + **PKCE** support
- Refresh-token handling (auto refresh within 5 minutes of expiry)
- Posting endpoint:
  - `POST /api/admin/social/post/{post_id}/post-to-tiktok`
  - plus publish status polling `GET /api/admin/social/tiktok/publish/{publish_id}/status`

3) **Signed public media URLs for platform pulls**
- New backend module: `/app/backend/social_media_signer.py`
- Public endpoints (HMAC + TTL):
  - `GET /api/social/media/{token}/slide/{idx}.png`
  - `GET /api/social/media/{token}/video.mp4`

4) **OAuth wiring in FastAPI**
- Callback endpoints (no auth, protected by single-use state):
  - `GET /api/social/meta/callback`
  - `GET /api/social/tiktok/callback`
- OAuth state stored in Mongo `oauth_states`

5) **Admin UI wiring (React)**
- `/admin/social/settings`
  - Connect + Reconnect + Disconnect buttons for Meta + TikTok
  - Success/error toast handling via redirect query params
- `/admin/social`
  - “Post to Facebook / Instagram / TikTok” buttons unlock once connected
  - TikTok supports private post default; public post button gated on `can_public`

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

## 3. Next Actions

### Immediate (P0): Turn on Phase 13B in production (operator steps) — PENDING 🟡
1) **Meta setup**
- Create Meta App (Business type) in Meta Developer Portal
- Add Facebook Login for Business + Instagram Graph API
- Set redirect URI to:
  - `https://ascendraacademy.com/api/social/meta/callback` (production)
- Add `.env`:
  - `META_APP_ID`, `META_APP_SECRET`, `META_REDIRECT_URI` (must match above)
- Restart backend, then go to `/admin/social/settings` → **Connect Facebook + Instagram**

2) **TikTok setup**
- Create TikTok app in TikTok Developer Portal
- Add Login Kit + Content Posting API
- Set redirect URI to:
  - `https://ascendraacademy.com/api/social/tiktok/callback` (production)
- Add `.env`:
  - `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI`
- Restart backend, then `/admin/social/settings` → **Connect TikTok**
- Submit TikTok App Audit for public posting (expect 1–4 weeks)

3) **Optional: set stable base URLs**
- Configure these env vars (recommended):
  - `PUBLIC_BASE_URL=https://ascendraacademy.com`
  - `PUBLIC_FRONTEND_URL=https://ascendraacademy.com`
  (Used for signed media URLs + OAuth callback redirects)

4) **Live smoke test**
- Generate a post in `/admin/social`
- Post to Facebook Page
- Post carousel to Instagram
- Post MP4 to TikTok (SELF_ONLY)

### X (Twitter) posting — BUSINESS DECISION 🟡
- X credentials may be invalid/expired (401 observed).
- Decide whether to pay for X API usage or keep X manual-only.
- If using X auto-posting, add/rotate `.env` keys:
  - `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`, `X_HANDLE`

### Code health (P2)
- Refactor `server.py` (~4,900 lines) into FastAPI `APIRouter` modules.

---

## 4. Success Criteria

### Product + Ops — ACHIEVED ✅
- ✅ Backend integrations proven: Claude tutor, Stripe LIVE checkout + subscriptions + Customer Portal, certificates.
- ✅ Website supports full learning loop end-to-end.
- ✅ Resend emails live on verified custom domain.
- ✅ Renewal reminders shipped (monthly + annual) + admin tools.
- ✅ “What’s New” shipped + AI content tagging.

### Growth Flywheel — ACHIEVED ✅
- ✅ Programmatic SEO pages + sitemap.
- ✅ Content auto-pilot: daily lessons + Monday flagship paths + quality gate.
- ✅ Lead magnet capture + AI Roadmap resource + welcome drip.
- ✅ Lifecycle automation: trial-ending, winback, streak-saver, annual upsell.
- ✅ Social Studio generates multi-format assets (thread + carousel + MP4).

### Social distribution + auto-posting — STATUS
- ✅ Phase A manual distribution workflow (copy/export) for X/FB/IG/TikTok.
- ✅ Phase B auto-posting code shipped for Meta + TikTok (OAuth, token storage, signed media URLs).
- 🟡 Awaiting operator setup: create apps + set env vars + connect accounts.
- 🟡 Awaiting platform approvals:
  - Meta App Review for advanced permissions
  - TikTok App Audit for public posting

### Practice-first learning — ACHIEVED ✅ / ONGOING 🟡
- ✅ Try-It-Live + Portfolio
- ✅ Capstones
- ✅ Spaced Drills
- ✅ Trophy Case

### Business metrics quality bar — ACHIEVED ✅
- ✅ Admin analytics endpoints exclude internal accounts while keeping real free-tier leads.

### Legal + security baseline — ACHIEVED ✅
- ✅ Terms / Privacy / No Refunds pages exist and are linked in footer.
- ✅ Signup flow enforces agreement.
- ✅ security.txt hosted.
- ✅ TikTok verification file hosted.

---

## 5. Operator / Environment Notes
- Two environments exist (Preview vs Production). Code changes land in preview; **click Deploy** to push to production.
- **Do not hardcode preview URLs** in code. Use env vars (`PUBLIC_BASE_URL`, `PUBLIC_FRONTEND_URL`, `REACT_APP_BACKEND_URL`).
- **Stripe keys:** Production should use **Restricted Key (`rk_live_…`)** in deployment secrets; Standard Secret Key (`sk_live_…`) should never be used in deployments.
- Avoid pasting any secrets into chat or screenshots. Rotate immediately if exposed.
- TikTok verification file must remain byte-for-byte exact (68 bytes, no newline).
- Social integrations:
  - Meta/TikTok OAuth callbacks are public endpoints by necessity; they are protected by one-time state + TTL.
  - Media for platform pull is protected by HMAC signed URLs with short TTL.
