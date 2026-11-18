"""V57 original-owner forward release of one carried, still-READY V55 ticket.

This module has no runtime entrypoint or power to pause a task. Caller MUST
authenticate existing Windows owner SID, single-owner mutex, exact protected
main + full CI, an independent detached rehearsal and a cold SHA-bound backup.
A post-first-write failure is an uncertain-effect HOLD, never automatic retry.
"""
from __future__ import annotations

import json

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import (
    APPROVAL_SCHEMA, activate_native, verify_native_activation,
)
from f139.nci04_v57_original_pending_preflight import (
    SOURCE, ORIGINAL_SOURCE, TICKET, ANCHOR_SEQ, ANCHOR_SHA,
    original_pending_snapshot,
)
from f139.nci04_v57_forward_transition import (
    FIELDS, SCHEMA, PREVIOUS, PURPOSE, make_proof,
    frozen_old_terminal_rows, need,
)


def original_snapshot(db: Database) -> dict:
    """Re-read original exact-head READY custody; no task or SQLite writes."""
    need(type(db) is Database, "DATABASE_CLASS_REQUIRED")
    pending = original_pending_snapshot(db, require_mutex=False)
    need(pending["source_sha"] == SOURCE
         and pending["head_seq"] == ANCHOR_SEQ
         and pending["head_sha256"] == ANCHOR_SHA
         and pending["ticket"] == TICKET
         and pending["ticket_stage"] == "READY"
         and pending["ticket_run_id"] is None
         and pending["new_dispatches"] == 0,
         "PREDECESSOR_READY_CHANGED")
    transitions = [
        json.loads(x["payload"]) for x in db.conn.execute(
            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
            " ORDER BY seq"
        )
    ]
    need(bool(transitions) and transitions[-1].get("schema") == PREVIOUS
         and transitions[-1].get("to_source_sha") == SOURCE
         and verify_native_activation(db, expected_source=SOURCE) is True,
         "V46_PREDECESSOR_NOT_ACTIVATED")
    rows, counts, negatives = frozen_old_terminal_rows(db, transitions)
    return {
        "source_sha": SOURCE, "head_seq": ANCHOR_SEQ,
        "head_sha256": ANCHOR_SHA,
        "ready_ticket": TICKET,
        "ready_identity_sha256": pending["ticket_identity_sha256"],
        "verified_historical_tasks": counts["VERIFIED"],
        "custodied_negative_tasks": counts["QUARANTINED"],
        "custodied_negative_tickets": negatives,
        "terminal_tasks_sha256": digest(canonical(rows)),
    }


def apply_copy_or_original(db: Database, proof: dict) -> dict:
    """Commit one source event then separately activate existing native owner.

    The two transactions preserve historical release semantics. If second
    activation fails, original source may have changed: fail closed and HOLD.
    """
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and not getattr(db, "_readonly_opened", False)
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 0,
         "ORIGINAL_OR_DETACHED_EXCLUSIVE_WRITER_REQUIRED")
    prior = original_snapshot(db)
    need(type(proof) is dict and set(proof) == FIELDS
         and proof.get("schema") == SCHEMA
         and proof.get("from_source_sha") == SOURCE
         and proof.get("prior_event_head_sha256") == ANCHOR_SHA
         and proof.get("source_transition_purpose") == PURPOSE
         and proof.get("original_ready_ticket") == TICKET
         and proof.get("original_ready_identity_sha256")
            == prior["ready_identity_sha256"]
         and proof.get("terminal_tasks_sha256")
            == prior["terminal_tasks_sha256"]
         and proof.get("verified_historical_tasks")
            == prior["verified_historical_tasks"]
         and proof.get("custodied_negative_tasks")
            == prior["custodied_negative_tasks"]
         and proof.get("custodied_negative_tickets")
            == prior["custodied_negative_tickets"],
         "PRECOMMIT_ORIGINAL_READY_OR_NEGATIVE_DRIFT")
    with db.transaction():
        need(original_snapshot(db) == prior, "ORIGINAL_SOURCE_MOVED_PREWRITE")
        db.conn.execute("UPDATE meta SET source_sha=? WHERE id=1",
                        (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
    # Existing owner activation MUST succeed before owner task is retargeted.
    approval = {
        "schema": APPROVAL_SCHEMA,
        "source_sha": proof["to_source_sha"],
        "expected_event_head_sha256": db.meta()["head_hash"],
        "native_development_approved": True,
        "scientific_first_use": False,
        "create_controller": False,
        "paid_api_calls": 0,
    }
    need(activate_native(db, approval) is True,
         "SOURCE_ADMITTED_BUT_NATIVE_ACTIVATION_FAILED_HOLD")
    db.verify()
    m = db.meta()
    need(m["head_seq"] == ANCHOR_SEQ + 2
         and m["source_sha"] == proof["to_source_sha"]
         and verify_native_activation(db) is True,
         "POSTACTIVATION_SOURCE_OR_LEDGER_DRIFT_HOLD")
    original = db.conn.execute(
        "SELECT ticket,source_sha,manifest_sha FROM tasks WHERE ticket=?",
        (TICKET,)
    ).fetchone()
    need(original is not None and original["source_sha"] == ORIGINAL_SOURCE,
         "ORIGINAL_READY_TASK_DISAPPEARED_HOLD")
    return {
        "schema": "forge.f139.v57.original-owner-release-result.v1",
        "target_source_sha": m["source_sha"], "head_seq": m["head_seq"],
        "head_sha256": m["head_hash"], "previous_native_source": ORIGINAL_SOURCE,
        "carried_ticket": TICKET, "original_ledger_verified": True,
        "scientific_first_use": False, "new_dispatches": 0,
        "new_controller": False, "new_scheduler": False,
    }
