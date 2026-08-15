# Ascendra Revenue Control Center — Governance Runbook

**Version:** 1.0  ·  **Status:** Operator-facing  ·  **Environment:** Preview + Production

This runbook is the printable operator reference for the Revenue Control Center (RCC).
It documents the three governance flows that must be followed for every irreversible
financial, legal, security, privacy, or reputation action:

1. **Approval flow** — how a sensitive action is queued, decided, and consumed.
2. **Corrections flow** — how prior owner-draw payments are adjusted or reversed
   without ever mutating history.
3. **Constitutional amendments** — how the Financial Constitution is updated while
   preserving immutable prior versions.

---

## 0. Non-negotiable safety invariants

Before executing any procedure below, verify these invariants hold:

| Invariant | How to verify |
| --- | --- |
| `AUTOMATION_LIVE_ACTIONS_ENABLED=false` in `/app/backend/.env` | Executive → banner reads **Live actions are DISABLED** |
| Financial math uses `Decimal128` / Python `Decimal` (never float) | `pytest tests/` — 179 tests must pass |
| Append-only integrity holds on `audit_log`, `financial_ledger`, `owner_draw_payments`, `financial_constitution` | No UPDATE/DELETE routes exist for these collections |
| Simulated rows never enter actual aggregates | Executive → all metrics carry `source_state=actual` and exclude `simulated=true` |

If ANY invariant is violated, **stop** and reach out to engineering before proceeding.

---

## 1. Approval flow (sensitive Phase 3 actions)

The following endpoints refuse to execute unless a matching, unconsumed approval
record is presented in the request body:

| Endpoint | request_type |
| --- | --- |
| `POST /api/admin/revenue/tax-policies/{policy_id}/activate` | `tax_policy.activate` |
| `POST /api/admin/revenue/allocation-policies/{policy_id}/activate` | `allocation_policy.activate` |
| `POST /api/admin/revenue/owner-draws/decision` | `owner_draw.approved` / `owner_draw.rejected` |
| `POST /api/admin/revenue/reconciliations/close` | `reconciliation.close` |
| `POST /api/admin/revenue/owner-draws/{id}/adjustment` | `owner_draw.adjustment` |
| `POST /api/admin/revenue/owner-draws/{id}/reversal` | `owner_draw.reversal` |

### 1.1 Step-by-step

1. **Draft** — Prepare the target artifact (a candidate allocation policy version,
   a tax policy version, a monthly reconciliation, or an owner-draw payment).
2. **Queue approval** — Create an approval row via
   `POST /api/admin/revenue/approvals` with:
   - `request_type` matching the endpoint above
   - `supporting_records.target_id = <artifact id>`
   - optionally `financial_amount_usd` for money-bearing actions
3. **Review** — Two humans should independently review the draft. The reviewer of
   record decides via `POST /api/admin/revenue/approvals/{id}/decision` with
   `decision=approved`.
4. **Execute** — Call the sensitive endpoint above, passing `approval_id` in the
   request body. The endpoint runs `enforce_approval()` internally:
   - `request_type` must match exactly
   - `target_id` must match exactly
   - `status` must be `approved`
   - `execution_completed` must be `false` (never re-consumed)
5. **Consume** — On success, `mark_approval_completed()` stamps the approval as
   consumed (`execution_completed=true`, `status=completed`) and records the
   execution reference. The approval row is **never deleted**.
6. **Audit** — Both the approval decision and the execution write append-only rows
   to `audit_log` with `approval_enforcement=enforced`.

### 1.2 What can go wrong

| Symptom | Cause | Remediation |
| --- | --- | --- |
| `HTTP 409 approval mismatch: approval request_type mismatch` | Wrong `request_type` on the approval row | Create a new approval with correct `request_type` |
| `HTTP 409 approval mismatch: approval target_id mismatch` | Approval was created for a different artifact | Create a new approval matching the target |
| `HTTP 409 approval mismatch: approval has already been consumed` | Approval was already used to execute an action | Create a fresh approval; each execution consumes exactly one approval |
| `HTTP 409 approval mismatch: approval has expired` | Approval `expires_at` has passed | Create a new approval |

---

## 2. Corrections flow (owner-draw adjustments & reversals)

Owner-draw payments are stored append-only in `owner_draw_payments`. Prior rows
must **never** be updated or deleted. All corrections write NEW rows that link
back to the original via a correction-type field.

### 2.1 Adjustment (partial correction)

Use an adjustment when a prior payment was recorded with the wrong amount.

- **Endpoint:** `POST /api/admin/revenue/owner-draws/{draw_id}/adjustment`
- **Requires:** an approval with `request_type=owner_draw.adjustment` and
  `target_id=<original_payment_id>`
- **Payload:**
  ```json
  {
    "draw_id": "<draw uuid>",
    "original_payment_id": "<original payment uuid>",
    "adjustment_amount": "-25.00",
    "reason": "reason with at least 8 characters",
    "payment_date": "<iso datetime>",
    "payment_reference": "<unique idempotency ref>",
    "approval_id": "<matching approval uuid>"
  }
  ```
- **Effect:** a new row is appended with `adjustment_of_payment_id=<original>` and
  the signed delta amount. The cumulative paid is recomputed from the sum of all
  rows (original + all corrections).

### 2.2 Reversal (full correction)

Use a reversal when a prior payment was fully invalid (e.g. duplicate).

- **Endpoint:** `POST /api/admin/revenue/owner-draws/{draw_id}/reversal`
- **Requires:** an approval with `request_type=owner_draw.reversal` and
  `target_id=<original_payment_id>`, `financial_amount_usd=<-original_amount>`
- **Payload:** identical shape to the adjustment payload, minus
  `adjustment_amount` (the reversal amount is computed as `-original.amount`).
- **Effect:** a new row is appended with `reverses_payment_id=<original>` and the
  opposite signed amount. Attempting to reverse a payment twice returns HTTP 409.

### 2.3 History audit

At any time, retrieve the full append-only history:

```
GET /api/admin/revenue/owner-draws/{draw_id}/payments
```

The response includes every original, adjustment, and reversal row in insert
order and the current cumulative total. **This is the source of truth** for
owner-draw payments — the summary field on the draw record is a derived cache
only.

---

## 3. Constitutional amendments

The Financial Constitution is stored in `financial_constitution` and is treated as
immutable. Amendments MUST produce a NEW version — prior versions are never
edited or deleted.

### 3.1 Amendment procedure

1. Draft the new principle set. Include ALL existing principles (removing one is
   itself a governance decision) plus any additions/edits.
2. Insert a NEW row into `financial_constitution` with:
   - `version = latest_version + 1`
   - `effective_date = <target date>`
   - `principles = [...]` (full new list)
   - `immutable = true`
   - `approved_by = <human decision-maker>`
3. The endpoint `GET /api/admin/revenue/constitution` will surface all versions,
   with the highest version marked as `current`.
4. **Never** update the row for version N after it has been inserted. If a
   correction is needed, publish version N+1.

### 3.2 Verification

After each amendment, verify:

- The Executive → Financial Constitution panel lists the new version as `current`
- `constitution_versions[0].version == N+1` (highest first)
- No prior version was modified — inspect `audit_log` for `constitution.updated`
  entries; there should be **none**

---

## 4. Simulation harness (Phase 5b)

The Simulation Harness (Executive → Simulation Harness) is a **safe** rehearsal
tool for the state machine. It refuses to run against any database whose name
does not contain the substring `test`.

Every record the harness creates is tagged `simulated=true`, and every executive
aggregate (revenue totals, funnel, cohorts) excludes simulated rows.

Use it to:
- Rehearse the state machine before major releases
- Train new operators on the approval + corrections flows
- Exercise integration adapters without any live external side effect

**Never rely on the harness to test live external integrations.** Live execution
is intentionally not implemented in preview.

---

## 5. Sign-off / rollback

### 5.1 Marking a phase complete

Phase sign-off is a deliberate act. To mark a phase as complete:

1. Verify all invariants in §0
2. Run the full pytest suite — must be 100% green
3. Bump `COMPLETED_PHASES` in `/app/backend/revenue.py`
4. Deploy
5. Verify `GET /api/admin/revenue/system/state` returns the expected
   `completed_phases`

### 5.2 Rollback

If a phase must be rolled back:

1. Do NOT delete rows from `financial_ledger`, `audit_log`,
   `owner_draw_payments`, or `financial_constitution`. All rollbacks are
   forward-only.
2. Publish new correction rows / new constitution version / new allocation
   policy version as appropriate.
3. Update `COMPLETED_PHASES` only after the rollback is verified.

---

## 6. Contact matrix

| Role | Responsibility | Notes |
| --- | --- | --- |
| **Owner** | Final approver for all high-risk actions | Cannot delegate approvals for `initiate_bank_transfer` |
| **Reviewer of record** | Independent approval decision | Must be a different human than the executor |
| **Executor** | Calls sensitive endpoints with approval_id | May be an automated queue processor once safety gate flips |
| **Auditor** | Reads audit_log for compliance | Read-only access; never writes |

---

*This runbook is maintained in `/app/docs/governance_runbook.md`. Every change
must be reviewed and reflected in the Financial Constitution when applicable.*
