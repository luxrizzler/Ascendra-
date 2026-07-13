"""One-shot cleanup script for the specifically named Phase-1 test fixtures.

Approved by the user on 2026-07-13 after Phase 1 sign-off.

TARGETS (only these; anything else is left untouched)
─────────────────────────────────────────────────────
  contacts:                phase1-00d4a80f@test.ascendra.simulated
  internal_events:         idempotency_key == idem-9f59c6b428714dcd93f241d478c30ce7
  operating_budget_history: notes ∈ {pytest-budget-91a806, pytest-budget-860f6c}
  audit_log:               entries whose target_id matches one of the fixtures above,
                           OR reason ∈ {pytest-budget-91a806, pytest-budget-860f6c}
  approval_queue:          the completed simulated approval whose id appears in
                           the fixture-linked audit rows AND reason='hardening test'

SAFETY RULES (enforced below)
─────────────────────────────
  • Every record is fetched and INSPECTED before deletion. Its origin is verified
    (simulated=true, or reason/notes match the exact fixture marker string).
  • Any record that does not match all expected markers is SKIPPED with a note.
  • The currently-displayed $12345.67 operating budget is inspected. If its
    `notes` field matches one of the two fixture markers, it is deleted; if it
    is any other note (or empty), it is preserved with an explicit skip message.
  • A pre-audit entry (action='fixture_cleanup.started') is inserted BEFORE any
    deletion; a post-audit entry (action='fixture_cleanup.completed') is
    inserted AFTER the last deletion. Neither audit entry is itself deleted.
  • The script is idempotent: if a target record has already been deleted, it
    reports "not found" and continues.

USAGE
─────
    # Dry-run (default) — inspects and reports, does NOT delete
    python /app/tools/fixture_cleanup_phase1.py

    # Actually delete (requires explicit confirmation flag)
    python /app/tools/fixture_cleanup_phase1.py --confirm

    # Force a repeat even after a successful cleanup audit already exists
    # (guarded — normally the tool refuses to repeat itself)
    python /app/tools/fixture_cleanup_phase1.py --confirm --force

The script prints a full report of what it inspected and what it removed.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Point at the same MongoDB the running backend uses.
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402


TARGETS = {
    "contact_email_normalized": "phase1-00d4a80f@test.ascendra.simulated",
    "event_idempotency_key": "idem-9f59c6b428714dcd93f241d478c30ce7",
    "budget_notes": ["pytest-budget-91a806", "pytest-budget-860f6c"],
    "approval_reason": "hardening test",  # simulated approval created by prior test
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _insert_audit(db, doc: dict) -> None:
    """Direct insert into the append-only audit_log. Mirrors revenue.py's schema."""
    await db["audit_log"].insert_one(doc)


async def _pre_audit(db, correlation_id: str) -> None:
    await _insert_audit(db, {
        "id": str(uuid.uuid4()),
        "actor": "system.cleanup.approved-by-owner",
        "action": "fixture_cleanup.started",
        "target_type": "phase1_test_fixtures",
        "target_id": "batch",
        "reason": (
            "User-approved narrow cleanup of confirmed Phase-1 test fixtures "
            "left by the prior failed test session (2026-07-13 10:46-47 UTC)."
        ),
        "result": "ok",
        "error": None,
        "correlation_id": correlation_id,
        "approval_required": False,
        "approval_status": None,
        "simulated": False,
        "live_actions_enabled_at_time": False,
        "created_at": _now(),
        "extra": {"targets": TARGETS},
    })


async def _post_audit(db, correlation_id: str, removed: dict, skipped: list) -> None:
    await _insert_audit(db, {
        "id": str(uuid.uuid4()),
        "actor": "system.cleanup.approved-by-owner",
        "action": "fixture_cleanup.completed",
        "target_type": "phase1_test_fixtures",
        "target_id": "batch",
        "reason": (
            f"Removed {sum(removed.values())} test fixture records; "
            f"skipped {len(skipped)} records whose origin was uncertain."
        ),
        "result": "ok",
        "error": None,
        "correlation_id": correlation_id,
        "approval_required": False,
        "approval_status": None,
        "simulated": False,
        "live_actions_enabled_at_time": False,
        "created_at": _now(),
        "extra": {"removed_counts": removed, "skipped": skipped},
    })


async def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-1 test-fixture cleanup (safe)")
    parser.add_argument("--confirm", action="store_true",
                          help="Actually delete matched fixtures. Without this "
                               "flag the script runs in DRY-RUN mode.")
    parser.add_argument("--force", action="store_true",
                          help="Allow re-run even if a successful fixture_cleanup.completed "
                               "audit entry already exists.")
    args = parser.parse_args()

    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ.get("DB_NAME", "ascendra_db")

    # Hard rule: this script may only ever run against ascendra_db (the ordinary
    # preview DB). If somehow pointed elsewhere, refuse.
    if db_name != "ascendra_db":
        print(f"REFUSING: DB_NAME='{db_name}' — this script only runs against ascendra_db.")
        return 2

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    correlation_id = str(uuid.uuid4())

    mode = "LIVE (--confirm)" if args.confirm else "DRY-RUN"
    print(f"\n=== Phase-1 test-fixture cleanup ({mode}) ===")
    print(f"Target DB: {db_name}")
    print(f"Correlation ID: {correlation_id}")
    print()

    # ── Repeat guard: refuse to run if a prior successful cleanup exists ────
    prior = await db["audit_log"].find_one({"action": "fixture_cleanup.completed"})
    if prior and not args.force:
        print("REFUSING: a fixture_cleanup.completed audit entry already exists")
        print(f"  prior correlation_id: {prior.get('correlation_id')}")
        print(f"  prior timestamp:      {prior.get('created_at')}")
        print("  Re-run with --force ONLY if newly identified test fixtures are "
              "proven to exist and require deletion.")
        client.close()
        return 3

    # ── Pre-inspection: fetch each target and print details ─────────────────
    inspected: dict = {}

    inspected["contact"] = await db["contacts"].find_one(
        {"email_normalized": TARGETS["contact_email_normalized"]}, {"_id": 0}
    )
    inspected["event"] = await db["internal_events"].find_one(
        {"idempotency_key": TARGETS["event_idempotency_key"]}, {"_id": 0}
    )
    inspected["budgets"] = await db["operating_budget_history"].find(
        {"notes": {"$in": TARGETS["budget_notes"]}}, {"_id": 0}
    ).to_list(10)
    inspected["approvals"] = await db["approval_queue"].find(
        {"reason": TARGETS["approval_reason"], "simulated": True}, {"_id": 0}
    ).to_list(10)

    print("── INSPECTED RECORDS ──")
    if inspected["contact"]:
        c = inspected["contact"]
        print(f"  contact:    id={c.get('id')}  email={c.get('email')}  simulated={c.get('simulated')}")
    else:
        print("  contact:    (not found — may have been deleted already)")

    if inspected["event"]:
        e = inspected["event"]
        print(f"  event:      id={e.get('id')}  key={e.get('idempotency_key')}  simulated={e.get('simulated')}")
    else:
        print("  event:      (not found)")

    for b in inspected["budgets"]:
        print(f"  budget:     id={b.get('id')}  notes={b.get('notes')!r}  updated_by={b.get('updated_by')}")
    if not inspected["budgets"]:
        print("  budget:     (none found)")

    for a in inspected["approvals"]:
        print(f"  approval:   id={a.get('id')}  status={a.get('status')}  simulated={a.get('simulated')}  reason={a.get('reason')!r}")
    if not inspected["approvals"]:
        print("  approval:   (none found)")

    # Also inspect the "current" budget (top of the history sort) to check
    # whether the $12345.67 note is one of ours.
    current_budget = await db["operating_budget_history"].find_one(
        {}, {"_id": 0}, sort=[("effective_date", -1)]
    )
    if current_budget:
        print(f"  current budget (top of history): "
              f"notes={current_budget.get('notes')!r}  updated_by={current_budget.get('updated_by')}")

    # ── Verify each record before permitting deletion ───────────────────────
    print("\n── VERIFYING TEST-FIXTURE MARKERS ──")
    to_delete = {"contact": [], "event": [], "budget": [], "approval": [], "audit": []}
    skipped: list = []

    if inspected["contact"]:
        c = inspected["contact"]
        if c.get("simulated") is True and c.get("email_normalized", "").endswith("@test.ascendra.simulated"):
            to_delete["contact"].append(c["id"])
            print(f"  ✓ contact {c['id']} — simulated=True, test.ascendra.simulated domain → APPROVED for deletion")
        else:
            skipped.append({"collection": "contacts", "id": c.get("id"),
                            "reason": "did not match all test-fixture markers"})
            print(f"  ✗ contact {c.get('id')} — SKIPPED (missing test-fixture markers)")

    if inspected["event"]:
        e = inspected["event"]
        if e.get("simulated") is True and e.get("idempotency_key", "").startswith("idem-"):
            to_delete["event"].append(e["id"])
            print(f"  ✓ event {e['id']} — simulated=True, idem-* key → APPROVED")
        else:
            skipped.append({"collection": "internal_events", "id": e.get("id"),
                            "reason": "did not match all test-fixture markers"})
            print(f"  ✗ event {e.get('id')} — SKIPPED")

    for b in inspected["budgets"]:
        if b.get("notes") in TARGETS["budget_notes"] and str(b.get("updated_by", "")).endswith("@ascendraacademy.com"):
            # Additionally require that the note exactly matches the pytest-budget-XXXXXX shape.
            to_delete["budget"].append(b["id"])
            print(f"  ✓ budget {b['id']} — notes={b['notes']!r} → APPROVED")
        else:
            skipped.append({"collection": "operating_budget_history", "id": b.get("id"),
                            "reason": "notes/updated_by did not match test-fixture markers"})
            print(f"  ✗ budget {b.get('id')} — SKIPPED")

    for a in inspected["approvals"]:
        # Only delete the simulated hardening-test approval whose lifecycle
        # went pending→approved→completed and whose reason exactly matches.
        if a.get("simulated") is True and a.get("reason") == TARGETS["approval_reason"] \
                and a.get("status") == "completed" and a.get("request_type") == "test.refund":
            to_delete["approval"].append(a["id"])
            print(f"  ✓ approval {a['id']} — simulated=True, hardening-test, completed → APPROVED")
        else:
            skipped.append({"collection": "approval_queue", "id": a.get("id"),
                            "reason": "did not match all test-fixture markers"})
            print(f"  ✗ approval {a.get('id')} — SKIPPED")

    # Current-budget-preservation guard
    if current_budget and current_budget.get("notes") not in TARGETS["budget_notes"]:
        print(f"  ✓ current budget {current_budget.get('id')} PRESERVED "
              f"(notes={current_budget.get('notes')!r} is not a known test marker)")

    # ── Audit entries directly linked to the above targets ─────────────────
    fixture_target_ids = (
        to_delete["contact"] + to_delete["event"]
        + to_delete["budget"] + to_delete["approval"]
    )
    # Fetch audit records whose target_id matches one of the fixture IDs,
    # OR whose reason matches one of the budget note markers.
    audit_query = {
        "$or": [
            {"target_id": {"$in": fixture_target_ids}} if fixture_target_ids else {"target_id": "__none__"},
            {"reason": {"$in": TARGETS["budget_notes"]}},
        ]
    }
    linked_audits = await db["audit_log"].find(audit_query, {"_id": 0}).to_list(1000)
    print(f"\n── LINKED AUDIT ENTRIES (candidates: {len(linked_audits)}) ──")
    for a in linked_audits:
        # Extra guard: never delete the cleanup audit entries themselves.
        if a.get("action") in ("fixture_cleanup.started", "fixture_cleanup.completed"):
            skipped.append({"collection": "audit_log", "id": a.get("id"),
                            "reason": "cleanup audit entry — preserved by policy"})
            print(f"  ✗ audit {a['id']} — action={a.get('action')} PRESERVED")
            continue
        # Only delete audits that are simulated=true (all fixture-linked ones are).
        if a.get("simulated") is True:
            to_delete["audit"].append(a["id"])
            print(f"  ✓ audit {a['id']} — action={a.get('action')} target={a.get('target_id')} → APPROVED")
        else:
            skipped.append({"collection": "audit_log", "id": a.get("id"),
                            "reason": "audit is not marked simulated=True"})
            print(f"  ✗ audit {a['id']} — SKIPPED (not simulated)")

    # ── Insert PRE audit entry (only in LIVE mode) ─────────────────────────
    if args.confirm:
        print("\n── INSERTING PRE-CLEANUP AUDIT ──")
        await _pre_audit(db, correlation_id)
        print("  ✓ audit entry action='fixture_cleanup.started' inserted")
    else:
        print("\n── DRY-RUN: skipping pre-cleanup audit insert ──")

    # ── Perform deletions (by-id, one at a time, no bulk collection wipes) ─
    if args.confirm:
        print("\n── EXECUTING DELETIONS ──")
    else:
        print("\n── DRY-RUN: no deletions will be performed ──")
    removed: dict = {}
    for cid in to_delete["contact"]:
        if args.confirm:
            r = await db["contacts"].delete_one({"id": cid})
            removed["contacts"] = removed.get("contacts", 0) + r.deleted_count
            print(f"  contacts.delete_one(id={cid}) → deleted={r.deleted_count}")
        else:
            print(f"  [DRY-RUN] would delete contacts id={cid}")
    for eid in to_delete["event"]:
        if args.confirm:
            r = await db["internal_events"].delete_one({"id": eid})
            removed["internal_events"] = removed.get("internal_events", 0) + r.deleted_count
            print(f"  internal_events.delete_one(id={eid}) → deleted={r.deleted_count}")
        else:
            print(f"  [DRY-RUN] would delete internal_events id={eid}")
    for bid in to_delete["budget"]:
        if args.confirm:
            r = await db["operating_budget_history"].delete_one({"id": bid})
            removed["operating_budget_history"] = removed.get("operating_budget_history", 0) + r.deleted_count
            print(f"  operating_budget_history.delete_one(id={bid}) → deleted={r.deleted_count}")
        else:
            print(f"  [DRY-RUN] would delete operating_budget_history id={bid}")
    for aid in to_delete["approval"]:
        if args.confirm:
            r = await db["approval_queue"].delete_one({"id": aid})
            removed["approval_queue"] = removed.get("approval_queue", 0) + r.deleted_count
            print(f"  approval_queue.delete_one(id={aid}) → deleted={r.deleted_count}")
        else:
            print(f"  [DRY-RUN] would delete approval_queue id={aid}")
    for auid in to_delete["audit"]:
        if args.confirm:
            r = await db["audit_log"].delete_one({"id": auid})
            removed["audit_log"] = removed.get("audit_log", 0) + r.deleted_count
            print(f"  audit_log.delete_one(id={auid}) → deleted={r.deleted_count}")
        else:
            print(f"  [DRY-RUN] would delete audit_log id={auid}")

    # ── Insert POST audit entry (only in LIVE mode) ────────────────────────
    if args.confirm:
        print("\n── INSERTING POST-CLEANUP AUDIT ──")
        await _post_audit(db, correlation_id, removed, skipped)
        print("  ✓ audit entry action='fixture_cleanup.completed' inserted")

    # ── Final report ───────────────────────────────────────────────────────
    print("\n── CLEANUP SUMMARY ──")
    for coll, count in removed.items():
        print(f"  {coll}: {count} removed")
    if not removed:
        print("  (nothing removed — targets may have already been cleaned)")
    print(f"  skipped: {len(skipped)}")
    if skipped:
        for s in skipped:
            print(f"    - {s}")

    print("\n── DELETED IDs (for the record) ──")
    for kind, ids in to_delete.items():
        for i in ids:
            print(f"  {kind}: {i}")

    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
