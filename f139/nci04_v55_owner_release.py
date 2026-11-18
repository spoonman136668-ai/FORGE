"""Original F139 V55 source-only forward repair: existing owner, no new task.

Development activation ONLY after independently authenticated original-owner
workflow, exact protected main/CI, cold copy, immutable negative custody, and
same SID/task quiescence. This module grants none of those authorities itself.
The original must remain held after an ambiguous post-commit result.
"""
from __future__ import annotations

import json
from collections import Counter

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import (
    APPROVAL_SCHEMA, activate_native, verified_historical_foundation,
    verify_native_activation,
)
from f139.nci04_v55_forward_transition import (
    SOURCE, ANCHOR_SEQ, ANCHOR_SHA, PREVIOUS, SCHEMA, make_proof,
    need, terminal_rows,
)


def original_snapshot(db: Database) -> dict:
    """Read the exact original pre-v45 ledger without modifying it."""
    need(type(db) is Database, "ORIGINAL_DATABASE_CLASS_REQUIRED")
    db.verify()
    verified_historical_foundation(db)
    m = db.meta()
    need(m["source_sha"] == SOURCE
         and m["enabled"] == 1 and m["legacy_suspended"] == 1
         and m["head_seq"] == ANCHOR_SEQ
         and db.ready() is None and not db.actives()
         and verify_native_activation(db, expected_source=SOURCE) is True,
         "ORIGINAL_SOURCE_OR_ACTIVATION_DRIFT")
    anchor = db.conn.execute(
        "SELECT kind,sha FROM events WHERE seq=?", (ANCHOR_SEQ,)
    ).fetchone()
    need(anchor is not None and anchor["kind"] == "NATIVE_DEVELOPMENT_ACTIVATED"
         and anchor["sha"] == ANCHOR_SHA, "ORIGINAL_EVENT1849_MISSING")
    prior = [
        json.loads(row["payload"]) for row in db.conn.execute(
            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
            " ORDER BY seq"
        )
    ]
    need(bool(prior) and prior[-1]["schema"] == PREVIOUS
         and prior[-1]["to_source_sha"] == SOURCE,
         "PREDECESSOR_V44_SOURCE_DRIFT")
    tasks, counts, negatives = terminal_rows(db, prior)
    return {
        "source_sha": m["source_sha"],
        "head_seq": m["head_seq"],
        "head_sha256": m["head_hash"],
        "terminal_tasks_sha256": digest(canonical(tasks)),
        "verified_historical_tasks": counts["VERIFIED"],
        "custodied_negative_tasks": counts["QUARANTINED"],
        "custodied_negative_tickets": negatives,
    }


def apply_copy_or_original(db: Database, proof: dict) -> dict:
    """Apply one v45 transition and native activation under exclusive mutex.

    Caller must separately prove actual original release authority, task SID,
    exact CI, backup and no running child, or use a *detached* cold rehearsal.
    If anything fails after the first commit, caller MUST HOLD the original:
    never automatically retry or assume rollback from a partial write.
    """
    need(type(db) is Database
         and not getattr(db, "_readonly_opened", False)
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 0,
         "ORIGINAL_OR_DETACHED_EXCLUSIVE_WRITER_REQUIRED")
    before = original_snapshot(db)
    need(type(proof) is dict and proof.get("schema") == SCHEMA
         and proof.get("from_source_sha") == SOURCE
         and proof.get("prior_event_head_sha256") == before["head_sha256"]
         and proof.get("terminal_tasks_sha256") == before["terminal_tasks_sha256"]
         and proof.get("verified_historical_tasks")
             == before["verified_historical_tasks"]
         and proof.get("custodied_negative_tasks")
             == before["custodied_negative_tasks"]
         and proof.get("custodied_negative_tickets")
             == before["custodied_negative_tickets"],
         "PRECOMMIT_ORIGINAL_CUSTODY_CHANGED")
    # The original complete Database.verify() replays the historic chain and
    # v45's proof. Do not create a successor source without that verifier.
    with db.transaction():
        need(original_snapshot(db) == before, "PREWRITE_LEDGER_MOVED")
        db.conn.execute(
            "UPDATE meta SET source_sha=? WHERE id=1",
            (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
    # This is the EXISTING native activation function, not a parallel owner.
    # A failed post-transition activation is an uncertain live state: hold,
    # retain the cold backup and require independent authenticated recovery.
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
    need(m["head_seq"] == before["head_seq"] + 2
         and m["source_sha"] == proof["to_source_sha"]
         and verify_native_activation(db) is True,
         "POSTCOMMIT_NATIVE_ACTIVATION_DRIFT_HOLD")
    return {
        "schema": "forge.f139.v55.original-owner-release-result.v1",
        "target_source_sha": m["source_sha"],
        "head_seq": m["head_seq"],
        "head_sha256": m["head_hash"],
        "prior_event_head_sha256": before["head_sha256"],
        "previous_native_source": SOURCE,
        "original_ledger_verified": True,
        "scientific_first_use": False,
        "new_dispatches": 0,
        "new_controller": False,
        "new_scheduler": False,
    }
