# Revenue Control Center — Phase 1 Documentation

**Scope**: foundation layer only. No financial calculations, no live external actions, no revenue data.

## Modules delivered

| Module | File | Purpose |
|---|---|---|
| Master safety gate | `backend/revenue.py::live_actions_enabled()` | Reads `AUTOMATION_LIVE_ACTIONS_ENABLED`. Default false. |
| Contacts + Organizations skeleton | `backend/revenue.py` (routes + Pydantic) | UUID-keyed, normalized-email uniqueness, lifecycle stage enum. |
| Internal event engine | `backend/revenue.py::create_event` | Idempotent via `idempotency_key` unique index. |
| Approval queue | `backend/revenue.py::create_approval / decide_approval` | Validated state machine: `pending → approved → completed` or `→ rejected/cancelled/expired`. |
| Audit log | `backend/revenue.py::_audit` | Append-only; no update/delete route exposed. |
| Integration status | `backend/revenue.py::integration_status` | Env-var-driven reporting. No live API calls. |
| Operating budget | `backend/revenue.py::set_budget / get_budget` | Decimal-safe versioned history (Phase 3 will consume). |
| Admin UI | `frontend/src/pages/AdminRevenue.js` at `/admin/revenue` | Overview, Approval Queue, Audit Log, Budget, Integrations tabs. |

## MongoDB collections created

- `contacts` — unique index on `email_normalized`; indexed on `lifecycle_stage`, `created_at`
- `organizations` — unique index on `name_normalized`
- `internal_events` — unique on `id`; **unique sparse on `idempotency_key`**; indexed on `event_type`, `correlation_id`, `created_at`
- `approval_queue` — unique on `id`; indexed on `status`, `created_at`
- `audit_log` — indexed on `created_at`, `actor`, `action`, `correlation_id` (no update/delete route ⇒ append-only by convention)
- `integration_status` — unique on `provider`
- `operating_budget_history` — indexed on `effective_date`, `created_at`

## API endpoints added (all under `/api/admin/revenue/*`, admin JWT required)

| Verb | Path | Purpose |
|---|---|---|
| GET | `/system/state` | Safety-gate snapshot |
| GET | `/summary` | Counts overview |
| POST | `/contacts` | Create/dedupe contact |
| GET | `/contacts` | List contacts (filter by lifecycle) |
| POST | `/events` | Create idempotent internal event |
| GET | `/events` | List events |
| POST | `/approvals` | Create approval request |
| GET | `/approvals` | List approvals |
| POST | `/approvals/{id}/decision` | Transition approval state (validated) |
| GET | `/audit` | Filter audit entries |
| GET | `/audit/export` | Bulk export JSON (records the export in audit log) |
| GET | `/integrations` | Env-driven integration status |
| GET | `/budget` | Current + full history |
| POST | `/budget` | Record new approved budget (audit-logged) |

## Admin route

- `/admin/revenue` — protected via existing `RequireAuth admin` wrapper. Five tabs: Overview, Approval Queue, Audit Log, Operating Budget, Integrations.

## Idempotency + safety guarantees (Phase 1)

- Events with matching `idempotency_key` return the original record. Race-condition-safe via unique sparse Mongo index.
- Contact creation with a duplicate normalized email returns the existing record with `duplicate: true` (no new insert).
- Approval state transitions validated server-side; illegal transitions return HTTP 400.
- Audit log is append-only by convention — no update/delete route exists. Attempting `DELETE /audit/{id}` returns 404/405.
- All budget history rows are additive; prior values are never overwritten.
- No integration performs live API calls in Phase 1. Every integration action, if a live actions flag is enabled, would still route through the approval queue for authorization.

## What Phase 1 explicitly does NOT do

- Does not compute reserves, allocations, or owner-draw amounts.
- Does not read Stripe events (existing webhook untouched).
- Does not send email, social posts, or any external message.
- Does not display revenue figures.
- Does not create Stripe products/prices.
- Does not seed any records (all data is admin-created; simulated records are labeled).
