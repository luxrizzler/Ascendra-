# Decisions

Architectural and product decisions that are already reflected in the codebase. This file does **not** invent facts; every entry is traceable to code, config, or `/app/plan.md`.

## D-001 — Web-first responsive product, not native mobile

**Context:** Fastest path to a paying audience without app-store review overhead.
**Decision:** Ship Ascendra as a single responsive React web app (`/app/frontend`) with the marketing landing page, learner UX, and admin console all on one domain.
**Consequence:** No React Native. Mobile UX is handled via Tailwind breakpoints and touch-target rules in the design system.

## D-002 — FastAPI + async Motor, not sync SQLAlchemy

**Context:** Heavy LLM / third-party HTTP workloads plus scheduled jobs.
**Decision:** FastAPI as the ASGI framework, Motor for async MongoDB access, `httpx.AsyncClient` for outbound HTTP.
**Consequence:** All DB and I/O in route handlers is `async`. Blocking library calls (e.g., `tweepy`) are called synchronously but from within async handlers; long-running tweepy media upload is acceptable because it's bounded by request lifetime.

## D-003 — UUIDs everywhere, no MongoDB ObjectIds

**Context:** Portability, easier API surfacing.
**Decision:** All primary keys are `uuid.uuid4()` strings (paths, lessons, users, social posts, etc.). No `_id` fields ever leaked in API responses.
**Consequence:** MongoDB queries always filter by `id`, not `_id`. Pydantic response models use `str` IDs.

## D-004 — All API routes prefixed `/api`

**Context:** Kubernetes ingress routes `/api/*` to backend, everything else to frontend.
**Decision:** Every FastAPI route lives under `/api/...`. Static assets, HTML, and client-side routing are served by the React app on the other side.
**Consequence:** Never add a top-level `/foo` route to the backend.

## D-005 — Emergent Universal LLM Key

**Context:** Single billing surface across Anthropic, OpenAI, and Google.
**Decision:** Use `EMERGENT_LLM_KEY` via `emergentintegrations` library for **all** LLM calls (text and image). `.with_model(...)` on `LlmChat`; do **not** chain `.with_max_tokens(...)` (it raises AttributeError).
**Consequence:** No provider SDKs installed for OpenAI / Anthropic / Google directly.

## D-006 — Stripe LIVE mode from day 1

**Context:** Real revenue path required.
**Decision:** `STRIPE_API_KEY` is a live-mode key; webhook signed with `STRIPE_WEBHOOK_SECRET`. Subscriptions + Customer Portal.
**Consequence:** All tests that touch billing must use test-mode substitutes; do not exercise production endpoints during development.

## D-007 — Resend for transactional email from custom domain

**Context:** Deliverability + branding.
**Decision:** `email_service.py` sends via Resend using `EMAIL_FROM_VERIFIED` on the verified `ascendraacademy.com` domain.
**Consequence:** DMARC/SPF/DKIM already published (per `plan.md`); no Gmail-relay fallback in production paths.

## D-008 — Practice-first learning as primary differentiator

**Context:** Positioning against Coursiv-style passive video courses.
**Decision:** Every learner path enforces Try-It-Live cards (rubric-graded), Module Capstones (must-pass gate for certification), and Spaced Drills (3/7/21-day review).
**Consequence:** Certificates cannot be issued from purely-passive completion; `practice_lab.py` gates it.

## D-009 — Auto-heal preferred over hard failures

**Context:** Content pipeline runs unattended.
**Decision:** Auto-content queue has an **Auto-resolve** admin button + daily scheduled auto-resolver that unblocks stuck items. `llm_retry.py` wraps LLM calls with tenacity retries for transient rate limits.
**Consequence:** Silent recovery is preferred to alerting; queue state is inspectable in `AdminAutoContent.js`.

## D-010 — Signed public URLs for external media pulls, not global anonymous endpoints

**Context:** Meta and TikTok fetch media by URL from their servers, without Authorization headers.
**Decision:** `social_media_signer.py` mints HMAC-SHA256 short-TTL (30 min) URLs. Endpoints `/api/social/media/{token}/slide/{i}.png` + `/video.mp4` validate signature + TTL before serving bytes.
**Consequence:** Even after Meta/TikTok have fetched an asset, the URL can't be enumerated or replayed after 30 min. Signing key falls back to `JWT_SECRET` if `SOCIAL_MEDIA_SIGNING_SECRET` is unset.

## D-011 — X free-tier budget enforcement in the app, not just at X

**Context:** X free tier is 500 posts/month; hitting it forces a Basic subscription ($200/mo).
**Decision:** Every successful tweet is logged in Mongo `x_post_log`. Before any post, `check_budget_or_reason(db, needed=len(tweets))` runs; on exhaustion the endpoint returns HTTP 429 with a clear explanation. UI disables the button and shows remaining count.
**Consequence:** Impossible to accidentally overshoot the free tier via manual admin actions.

## D-012 — OAuth 1.0a User Context for X (not OAuth 2.0)

**Context:** X's media upload endpoint (`/1.1/media/upload.json`) only accepts OAuth 1.0a. We attach images to tweet threads.
**Decision:** `x_publisher.py` uses `tweepy.OAuth1UserHandler` for v1.1 media + `tweepy.Client(access_token=...)` for v2 tweet creation and `get_me()` verification.
**Consequence:** The 4 env vars are `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`. OAuth 2.0 Client ID/Secret are **not** used; users who paste them are steered back to OAuth 1.0a during setup.

## D-013 — TikTok OAuth uses PKCE, tokens stored in Mongo

**Context:** TikTok mandates PKCE for OAuth 2.0. Access tokens live 24h, refresh 365d.
**Decision:** `tiktok_publisher.py` builds PKCE code verifier/challenge, stores `code_verifier` in a short-lived `oauth_states` Mongo doc, refreshes access tokens transparently when within 5 min of expiry.
**Consequence:** No refresh-token knowledge required from the operator after initial connect.

## D-014 — Meta re-enablement kept warm, not deleted

**Context:** Meta App Review is a multi-day process; requirements shift.
**Decision:** `meta_publisher.py` remains fully implemented and wired into `server.py`. UI cards are commented out in `AdminSocial.js` and `AdminSocialSettings.js` with a pointer note. Env vars are commented in `.env`, not deleted.
**Consequence:** Restoring Meta is a targeted uncomment (~4 blocks + 3 env lines) rather than a rebuild.

## D-015 — No refunds, no discounts

**Context:** Simplifies revenue accounting for a solo operator.
**Decision:** Public `/no-refunds` page is part of the ToS acceptance flow. Promo/discount codes explicitly out of scope per `plan.md`.
**Consequence:** No Stripe coupon logic anywhere in `server.py`; if a customer disputes, direct them to Terms.
