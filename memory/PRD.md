# Ascendra — Product Requirements

**Tagline**: AI-Powered Learning. Boundless Growth.
**Mission**: To empower every learner to rise beyond limits through AI-driven education and human potential.

A premium mobile-first AI learning app (Coursiv-style) with a web marketing landing page. Designed to take learners from absolute beginner to advanced AI builder.

## Tech stack
- Frontend: React Native / Expo Router (mobile + web)
- Backend: FastAPI + MongoDB
- LLM: Claude Sonnet 4.5 via Emergent Universal LLM Key (emergentintegrations.llm.chat)
- Payments: Stripe via emergentintegrations.payments.stripe.checkout
- Auth: JWT (email/password, bcrypt) + Emergent-managed Google Social Login

## Brand
- **Palette (Celestial Phoenix)**: Deep Navy `#070B1F` · Celestial `#1A1F3D` · Champagne `#E8C572` · Amber Gold `#FFB000` · Phoenix Coral `#FF6B35` · Lavender Mist `#BFB4FF` · Celestial Violet `#7C3AED`
- **Gradients**: Golden Dawn (champagne → amber → coral) & Celestial Violet (navy → violet → lavender)
- **AI Tutor**: Named "Ascendra" (the brand IS the partner)
- **Slogan**: LEARN. GROW. TRANSFORM. ASCEND.

## Core features
1. **Onboarding** — goal selection (career, business, creator, productivity) + signup
2. **Auth** — JWT email/password + Google Social Login
3. **4 Learning Paths** — AI Fundamentals · Build a Business with AI · AI for Creators · AI for Productivity (36+ micro-lessons)
4. **Lesson player** — swipeable cards + end-of-lesson quiz + XP reward
5. **AI Tutor "Ascendra"** — Claude Sonnet 4.5 chat with persistent multi-turn memory (MongoDB replay)
6. **AI Model Library** — 22 frontier models (GPT-5.2, Claude 4.5, Gemini 3, Nano Banana, Sora 2, Veo 3, ElevenLabs, Perplexity, Midjourney, Cursor, …) with category filters & detail sheets
7. **Progress tracking** — daily streak, XP, completed lessons, member-since
8. **Pricing & paywall** — Free / Pro $19.99 / Business $49.99 with Stripe Checkout
9. **Web marketing landing page** — hero, models marquee, features, testimonials, pricing, final CTA

## Routes
- `/` smart redirect (web → /landing · mobile → /onboarding or /(tabs)/home)
- `/landing` marketing site (web-focused, responsive)
- `/onboarding` `/login` `/auth` (Google callback) `/pricing` `/checkout-success`
- `/(tabs)/home` `/(tabs)/paths` `/(tabs)/tutor` `/(tabs)/models` `/(tabs)/profile`
- `/path/[id]` `/lesson/[id]`

## API
- `POST /api/auth/signup` `POST /api/auth/login` `POST /api/auth/google` `GET /api/auth/me`
- `GET /api/paths` `GET /api/paths/{id}` `GET /api/lessons/{id}` `GET /api/models`
- `GET /api/progress` `POST /api/progress/complete`
- `POST /api/tutor/chat` `GET /api/tutor/history/{session_id}`
- `GET /api/pricing` `POST /api/billing/checkout` `GET /api/billing/status/{id}` `POST /api/billing/webhook`
