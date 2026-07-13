# Revenue Control Center — Environment Variable Template

Copy the placeholders below into `/app/backend/.env`. **Do NOT paste real credentials into this file.** Set real values via your secret-management workflow.

All integrations remain simulated while `AUTOMATION_LIVE_ACTIONS_ENABLED=false`.

```dotenv
# ─── Master safety gate ──────────────────────────────────────────────
# When "false" (default), the Revenue Control Center simulates all external
# side effects and routes irreversible actions to the approval queue.
AUTOMATION_LIVE_ACTIONS_ENABLED=false

# ─── Cash allocation policy (Phase 3 will consume these) ─────────────
ASCENDRA_DEFAULT_CURRENCY=USD
ASCENDRA_OWNER_DRAW_DAY=5
ASCENDRA_STARTUP_OWNER_PERCENT=25
ASCENDRA_STARTUP_GROWTH_PERCENT=25
ASCENDRA_STARTUP_WORKING_CAPITAL_PERCENT=50
ASCENDRA_ESTABLISHED_OWNER_PERCENT=50
ASCENDRA_ESTABLISHED_GROWTH_PERCENT=25
ASCENDRA_ESTABLISHED_WORKING_CAPITAL_PERCENT=25
ASCENDRA_RESERVE_MONTHS_TARGET=3

# ─── Integration placeholders (Phase 4 wires adapters) ───────────────
# Leave blank in preview. Fill only when live actions are authorized.
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
RESEND_API_KEY=
BUFFER_ACCESS_TOKEN=
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GOOGLE_CALENDAR_CLIENT_ID=
GOOGLE_CALENDAR_CLIENT_SECRET=
```

## Rules of engagement

1. If any placeholder is unset, the integration reports `state: unavailable` in `/api/admin/revenue/integrations`. Missing credentials never crash the app.
2. If credentials are present but `AUTOMATION_LIVE_ACTIONS_ENABLED=false`, the integration reports `state: simulated`. No external API calls are made.
3. Only when both credentials are present AND `AUTOMATION_LIVE_ACTIONS_ENABLED=true` does the integration report `state: live` — and even then, actions requiring human authorization still route through the approval queue.
4. Secrets are never returned in API responses. The status endpoint only reports which env keys are expected, not their values.
