# Project Status

Source of truth is `/app/plan.md` (the running log). This file summarizes the currently-implemented state as evident from the codebase.

## ✅ Shipped Features

### Core learner experience
- Email/password auth + Emergent Google OAuth (`/api/auth/*`, `AuthCallback.js`)
- Personalized onboarding quiz (`Onboarding.js`) that produces a custom starter path
- Path → Module → Lesson → Card curriculum model (UUIDs, timezone-aware datetimes)
- Interactive lesson cards generated dynamically by Claude via `interactive_generator.py`
- Streak tracking (`components/streak/`, dashboard widgets) with celebration animations
- 15-Day AI Challenge roadmap (`Challenge15Day.js`, `AiRoadmap.js`)
- Prompt library (`PromptLibrary.js`)
- TTS narration + sound effects in lesson player (`LessonPlayer.js`)
- Certificates auto-issued on path completion, shareable & printable (`Certificate.js`)

### Practice-first learning (Layers 1–3)
- **Layer 1 — Try-It-Live:** LLM-graded practice cards; results feed a per-user Portfolio (`Portfolio.js`, `PublicPortfolio.js`) served by `practice_lab.py`.
- **Layer 2 — Module Capstones:** mandatory capstones must be passed before module/path certificates issue (`CapstonePlayer.js`, `/api/capstone/*`).
- **Layer 3 — Spaced Drills:** 3/7/21-day review prompts based on struggle patterns (`DrillWidget.js`).
- **Trophy Case:** aggregates certificates, capstones, medals, streaks (`TrophyCase.js`, `/api/trophy-case/mine`).

### Monetization
- Stripe LIVE mode subscriptions (monthly + annual)
- Stripe Customer Portal integration for self-serve billing
- Renewal reminders (7-day pre-renewal via scheduled jobs)
- Checkout success flow (`CheckoutSuccess.js`)
- Legal compliance pages: `/terms`, `/privacy`, `/no-refunds`

### Admin console
- Curriculum Manager (`AdminCurriculum.js`, `AdminCurriculumEdit.js`)
- AI Course Studio (`AdminStudio.js` ↔ `ai_studio.py`) — generate paths, modules, lessons from prompts
- Path Review queue (`AdminPathsReview.js`)
- Practice management (`AdminPractice.js`)
- Email template previewer (`AdminEmail.js`)
- Auto-content pipeline (`AdminAutoContent.js` ↔ `auto_content.py`) — daily lesson + weekly flagship with **auto-resolve** self-healing
- Content Health autoscanner (`AdminContentHealth.js` ↔ `content_scanner.py`) — detects outdated model references and patches them
- Programmatic SEO Studio (`AdminSeoStudio.js` ↔ `seo_studio.py`) — dynamic `/learn/*` hubs, JSON-LD, sitemap
- Subscribers list (`AdminSubscribers.js`)
- What's New surfacing (`AdminWhatsNew.js`)

### Social distribution (Social Studio)
- Per-lesson generation of: 5-tweet X thread + 5-slide 1080×1080 branded carousel + silent 1080×1080 MP4 slideshow.
- Distribution panel at `/admin/social` with platform-specific action buttons.
- Platform-config Settings page at `/admin/social/settings` with step-by-step walkthroughs.
- **X (Twitter):** Auto-post fully wired (v1.1 media + v2 tweets). Free-tier budget tracker enforces 500/mo + 50/day hard caps (Mongo `x_post_log`).
- **TikTok:** OAuth 2.0 + PKCE flow, Content Posting API `PULL_FROM_URL` publish. Domain verification file present at `/frontend/public/tiktoklkxs3T9JjlCjJNh3jIZzlheOa0um2ntP.txt`.
- **Meta (Facebook + Instagram):** Backend `meta_publisher.py` implemented (Graph API v20, OAuth 2.0, Page Access Tokens, IG carousel/reels). **Admin UI intentionally hidden** per current business priority — backend endpoints preserved for future reactivation.
- **Signed public media URLs:** HMAC-SHA256 short-TTL URLs (`/api/social/media/{token}/...`) so external platforms can pull our assets without Bearer auth.

### Infra / SEO / compliance
- `robots.txt`, `sitemap.xml`, `security.txt` + `.well-known/security.txt` deployed.
- JSON-LD structured data via `SEO.js` component.
- CORS configured via `CORS_ORIGINS`.
- Backend binds to `0.0.0.0:8001`, all routes under `/api/*`.
- Frontend on `3000`. `REACT_APP_BACKEND_URL` env var controls API base URL.
- APScheduler jobs: daily content generation, weekly flagship generation, renewal reminders, auto-resolve stuck queue items.

## 🟡 Known Gaps / Ongoing

- **`backend/server.py` is ~4,900 lines** and needs splitting via FastAPI `APIRouter` (auth / stripe / curriculum / practice / social / admin sub-routers). Deferred; no functional impact.
- **Meta (FB + IG) auto-posting UI is hidden.** Backend fully implemented; requires re-enabling the two `<PlatformSection>` blocks in `AdminSocialSettings.js` and the two `<PlatformCard>` blocks in `AdminSocial.js`, plus re-adding `META_APP_ID` / `META_APP_SECRET` / `META_REDIRECT_URI` in the backend `.env`.
- **TikTok App Audit:** post-to-TikTok defaults to `SELF_ONLY` privacy until TikTok approves public posting (1–4 week audit).
- **X Free tier:** hard-limited to 500 posts/month, 50/day; monitor via the Budget Bar in `/admin/social/settings`.
- **LinkedIn:** discussed but not built.
- **Secret hygiene:** several credentials have transited through the build-agent chat during setup and are flagged for rotation before long-term production use (Meta App Secret, TikTok Client Secret, X Access Token pair).

## Runtime Health (last known)

- Backend and frontend supervisord services healthy.
- MongoDB reachable via `MONGO_URL`.
- Stripe webhook endpoint responsive.
- No production regressions reported.
