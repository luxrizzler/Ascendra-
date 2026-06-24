# Ascendra — Product Requirements

**Tagline**: AI-Powered Learning. Boundless Growth.
**Mission**: To empower every learner to rise beyond limits through AI-driven education and human potential.

A premium **web-first AI learning platform** (Coursiv-style web SaaS) with a public marketing landing page and authenticated browser dashboard. Designed to take learners from absolute beginner to advanced AI builder. Fully responsive — desktop & mobile-browser layouts. iOS/Android native builds are out of scope for this phase.

## Tech stack
- Frontend: Expo Router + React Native Web (exported to static HTML/JS via `yarn expo export -p web`)
- Backend: FastAPI + MongoDB — also serves the static web build from `/app/backend/static`
- LLM: Claude Sonnet 4.5 via Emergent Universal LLM Key (emergentintegrations.llm.chat)
- Payments: Stripe (native SDK for real subs + Customer Portal; emergentintegrations wrapper as fallback)
- Auth: JWT (email/password, bcrypt) + Emergent-managed Google Social Login
- Email: Resend (transactional — password reset + admin invite)
- Hosting: Emergent Publish (web + backend + DB bundled at one URL)

## Brand
- **Palette (Celestial Phoenix)**: Deep Navy `#070B1F` · Celestial `#1A1F3D` · Champagne `#E8C572` · Amber Gold `#FFB000` · Phoenix Coral `#FF6B35` · Lavender Mist `#BFB4FF` · Celestial Violet `#7C3AED`
- **Gradients**: Golden Dawn (champagne → amber → coral) & Celestial Violet (navy → violet → lavender)
- **AI Tutor**: Named "Ascendra" (the brand IS the partner)
- **Slogan**: LEARN. GROW. TRANSFORM. ASCEND.

## Core features
1. **Onboarding quiz** — 4-question Coursiv-style quiz (goal · experience · time/day · focus area) → personalized path recommendation card before signup
2. **Auth** — JWT email/password + Emergent-managed Google Social Login
3. **10 Learning Paths** — Fundamentals · Business · Creators · Productivity · Prompt Mastery · Automation · Code With AI · Startup Playbook · Sales Engine · Enterprise AI (100+ micro-lessons across Ascender/Pathfinder/Sage tiers)
4. **Lesson player** — swipeable cards + end-of-lesson quiz + XP reward + auto-celebration when path completes
5. **AI Tutor "Ascendra"** — Claude Sonnet 4.5 chat with persistent multi-turn memory (MongoDB replay)
6. **AI Model Library** — 22 frontier models with category filters & detail sheets
7. **Progress / Levels / Streaks** — daily streak, XP, computed level (curve: cumulative XP = 100·n·(n−1)), per-path progress bars, "FOR YOU" badge on recommended path
8. **Certificates of Mastery** — auto-issued (idempotent) when all lessons in a path complete; beautiful Ascendra-branded cert page with share + serial ID
9. **Pricing & paywall** — Ascender $9.99 · Pathfinder $19.99 · Sage $29.99 with annual toggle (17% off) + Stripe Checkout + $2.99 7-day trial for Sage
10. **Real auto-renewing Stripe subscriptions** — `POST /api/billing/subscribe` (recurring) + `POST /api/billing/portal` (Customer Portal). Auto-activates when user adds real `sk_test_`/`sk_live_` Stripe key + `STRIPE_WEBHOOK_SECRET` to backend/.env. Native webhook handles `invoice.paid`, `customer.subscription.updated/.deleted`.
11. **Web marketing landing page** — hero, models marquee, features, testimonials, pricing, final CTA

## Routes
- `/` smart redirect (web → /landing · mobile → /onboarding or /(tabs)/home)
- `/landing` marketing site (web-focused, responsive)
- `/onboarding` `/login` `/auth` (Google callback) `/pricing` `/checkout-success`
- `/(tabs)/home` `/(tabs)/paths` `/(tabs)/tutor` `/(tabs)/models` `/(tabs)/profile`
- `/path/[id]` `/lesson/[id]` `/certificate/[id]`

## API
- `POST /api/auth/signup` `POST /api/auth/login` `POST /api/auth/google` `GET /api/auth/me` `PUT /api/auth/me/quiz`
- `GET /api/paths` `GET /api/paths/{id}` `GET /api/lessons/{id}` `GET /api/models`
- `GET /api/progress` `POST /api/progress/complete` (returns awarded_xp + certificates_issued)
- `GET /api/certificates` `GET /api/certificates/{id}`
- `POST /api/tutor/chat` `GET /api/tutor/history/{session_id}`
- `GET /api/pricing` `POST /api/billing/checkout` `GET /api/billing/status/{id}` `POST /api/billing/webhook`
- `GET /api/billing/info` (returns `uses_real_stripe`) — frontend uses to switch endpoints
- `POST /api/billing/subscribe` (real recurring Stripe — 501 until real key added)
- `POST /api/billing/portal` (Customer Portal — 501 until real key added)
