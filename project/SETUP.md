# Setup

Accurate to the repository layout. The build environment already has services running under supervisor; this file documents how the pieces fit together and how to run/inspect them.

## Prerequisites

- **Python 3.11+** (the backend uses async FastAPI + Motor)
- **Node.js 18+** with **yarn** — the project is standardized on `yarn` (do **not** use `npm`)
- **MongoDB** reachable via `MONGO_URL` (a preconfigured instance is provided in this environment; you do not need to install one locally when working inside the sandbox)

## Directory conventions

- Backend: `/app/backend`
- Frontend: `/app/frontend`
- Backend loads env from `/app/backend/.env`; frontend from `/app/frontend/.env`.
- **Never modify `MONGO_URL` in `backend/.env` or `REACT_APP_BACKEND_URL` in `frontend/.env`.** Both are set by the platform and changing them will break integration.

## Required environment variables

### Backend (`/app/backend/.env`)

Core (platform-provided, do not change):
- `MONGO_URL` — MongoDB connection string
- `DB_NAME` — database name
- `CORS_ORIGINS` — comma-separated allowed origins
- `JWT_SECRET_KEY`, `JWT_ALGORITHM` — auth token signing

Product integrations (fill in from provider dashboards, values are secrets):
- `EMERGENT_LLM_KEY` — universal LLM key (Anthropic / OpenAI / Google)
- `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET` — Stripe LIVE
- `RESEND_API_KEY`, `EMAIL_FROM_VERIFIED`, `EMAIL_FROM_VERIFIED_ENABLED` — transactional email
- `PUBLIC_WEB_URL` — base URL used in emails/links

Social (optional per platform; each block is independent):
- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`, `X_HANDLE`
- `X_MONTHLY_POST_LIMIT`, `X_DAILY_POST_LIMIT`, `X_WARN_MONTHLY_REMAINING`, `X_WARN_DAILY_REMAINING` (optional overrides)
- `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI`
- `META_APP_ID`, `META_APP_SECRET`, `META_REDIRECT_URI` (currently commented out; re-enable when Meta UI is re-surfaced)

Signing / public base URLs (recommended for production correctness):
- `PUBLIC_BASE_URL` — base for signed media URLs (e.g. `https://ascendraacademy.com`)
- `PUBLIC_FRONTEND_URL` — base for OAuth return redirects
- `SOCIAL_MEDIA_SIGNING_SECRET` — 32+ random chars; falls back to `JWT_SECRET` if unset

### Frontend (`/app/frontend/.env`)

- `REACT_APP_BACKEND_URL` — API base URL (platform-provided, **do not modify**)
- `WDS_SOCKET_PORT` — dev server socket port
- `ENABLE_HEALTH_CHECK` — platform flag

## Install (from scratch)

> These commands are already run for you in the build environment. Only run manually when bootstrapping a fresh clone.

```bash
# Backend
cd /app/backend
pip install -r requirements.txt

# Frontend
cd /app/frontend
yarn install
```

## Running the services

Both services are managed by **supervisor** in this environment. **Do not run them manually with `python server.py` or `yarn start`** — supervisor handles processes, logging, and auto-restart.

```bash
# Restart backend after changing backend/.env or Python dependencies
supervisorctl restart backend

# Restart frontend after changing frontend/.env or yarn deps
supervisorctl restart frontend

# Check status
supervisorctl status

# Tail logs
tail -n 100 /var/log/supervisor/backend.out.log
tail -n 100 /var/log/supervisor/backend.err.log
tail -n 100 /var/log/supervisor/frontend.err.log
```

Hot reloading is enabled for both. You only need to restart when you change env vars or install packages.

## Service ports

| Service  | Bind             | Ingress path routed to it |
|----------|------------------|---------------------------|
| Backend  | `0.0.0.0:8001`   | `/api/*`                  |
| Frontend | `0.0.0.0:3000`   | everything else           |

## Adding dependencies

**Backend (Python):**
```bash
cd /app/backend
pip install some-package
pip freeze > requirements.txt
supervisorctl restart backend
```

**Frontend (JavaScript):**
```bash
cd /app/frontend
yarn add some-package
supervisorctl restart frontend
```

Do **not** hand-edit `requirements.txt` or `package.json`. Use the tools above.

## Running tests

```bash
# Backend tests (pytest)
cd /app
pytest tests/ -v

# Individual runnable test scripts in the repo root
python backend_test.py
python backend_test_interactive.py
```

Frontend has a Jest scaffold via CRA (`yarn test`), but the primary test coverage lives in the pytest suites and integration flows.

## Common gotchas

- Backend routes **must** be prefixed with `/api` — the ingress relies on it.
- All Mongo IDs must be `str(uuid.uuid4())`, never `ObjectId`.
- All datetimes must be `datetime.now(timezone.utc)`.
- Do not use HTML entities (`&lt;`, `&gt;`) in code — use actual characters. Compilers interpret entities literally.
- Do not chain `.with_max_tokens(...)` on `LlmChat` — it throws `AttributeError`. Use `.with_model(...)` only.
- Load env vars **inside** endpoint functions or right before call time; module-level reads before `load_dotenv()` in `server.py` return `None`.
- The TikTok domain verification file at `/app/frontend/public/tiktoklkxs3T9JjlCjJNh3jIZzlheOa0um2ntP.txt` **must remain exactly 68 bytes with no trailing newline** — do not open it in an editor that auto-adds newlines.

## Production vs preview

- **Preview** is the environment the build agent operates in. Code changes here do not affect real users.
- **Production** is [https://ascendraacademy.com](https://ascendraacademy.com). Deployed via the platform's Deploy action, not manual copy. Preview URLs change per fork; never hardcode them.
- Env variables set in preview do **not** propagate to production. Duplicate any secrets you need in production via the platform's env panel.
