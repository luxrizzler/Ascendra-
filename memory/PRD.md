# AI Academy — Product Requirements

A premium mobile-first AI learning app (Coursiv-style) with a web marketing landing page.

## Goal
Teach people how to use AI — from absolute beginner to advanced builder — through micro-learning lessons, an AI tutor, and curated curriculum covering 2026 frontier models.

## Tech stack
- Frontend: React Native / Expo Router (mobile + web)
- Backend: FastAPI + MongoDB
- LLM: Claude Sonnet 4.5 via Emergent Universal LLM Key (emergentintegrations)
- Payments: Stripe via emergentintegrations.payments.stripe.checkout

## Core features
1. **Onboarding** — goal selection (career, business, creator, productivity) + signup
2. **Auth** — JWT email/password
3. **4 Learning Paths** — AI Fundamentals · Build a Business with AI · AI for Creators · AI for Productivity (36+ lessons total)
4. **Lesson player** — swipeable cards + end-of-lesson quiz + XP reward
5. **AI Tutor "Aida"** — Claude Sonnet 4.5 chat with conversation memory
6. **AI Model Library** — 22 frontier models (GPT-5.2, Claude 4.5, Gemini 3, Nano Banana, Sora 2, Veo 3, ElevenLabs, Perplexity, Midjourney, Cursor, …) with category filters
7. **Progress tracking** — daily streak, XP, completed lessons
8. **Pricing & paywall** — Free / Pro $19.99 / Business $49.99 with Stripe Checkout
9. **Web marketing landing page** — hero, features, testimonials, pricing, CTA

## Routes
- `/` smart redirect (web → /landing; mobile → /onboarding or /(tabs)/home)
- `/landing` marketing site
- `/onboarding` `/login` `/pricing` `/checkout-success`
- `/(tabs)/home` `/(tabs)/paths` `/(tabs)/tutor` `/(tabs)/models` `/(tabs)/profile`
- `/path/[id]` `/lesson/[id]`

## API
- `POST /api/auth/signup` `POST /api/auth/login` `GET /api/auth/me`
- `GET /api/paths` `GET /api/paths/{id}` `GET /api/lessons/{id}` `GET /api/models`
- `GET /api/progress` `POST /api/progress/complete`
- `POST /api/tutor/chat` `GET /api/tutor/history/{session_id}`
- `GET /api/pricing` `POST /api/billing/checkout` `GET /api/billing/status/{id}` `POST /api/billing/webhook`
