"""Inert V41 -> Hybrid source transition v37 for the original F139 owner.

No CLI, issue publisher, scheduled-task manipulation, or automatic invocation.
Only a separately qualified original-owner caller can supply a frozen complete
cold bundle, authenticated release and an independently checked disabled-task
witness. Hybrid admission and scientific first-use are deliberately excluded.
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation
from f139.hybrid_owner_admission import is_migrated
from f139 import nci04_v41_source_transition as v41
from f139 import nci04_v41_hybrid_cold_bundle as bundle

SCHEMA = "forge.f139.source-transition.v37"
FROM_V41 = "1a40fe4e3ec6e93a1631d59863b95e90981d734e"
ACTIVATED_SEQ = 1829
ACTIVATED_HASH = "55ded016778c8430bd4f6e3290972be1c5c5c796cbcb2a2ad38046283f78e3f8"
PURPOSE = "hybrid-development-source-handoff-without-admission"
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "prior_event_head_sha256", "original_head_seq", "original_head_sha256",
    "v36_event_sha256", "v41_activation_head_sha256",
    "verified_historical_tasks", "custodied_negative_tasks",
    "custodied_negative_tickets", "terminal_tasks_sha256",
    "backup_run_id", "backup_manifest_sha256",
    "backup_logical_all_tables_sha256", "qualified_worker_blob", "purpose",
    "new_dispatches", "scientific_first_use", "hybrid_admission",
    "v2_receipt_authorized",
})


class HybridSourceDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise HybridSourceDenied("F139_HYBRID_V41_SOURCE_" + reason)


def snapshot(db, row, previous):
    """Replay-safe immutable historic V41 prefix; never reads today's policy."""
    need(type(previous) is list and bool(previous)
         and type(row["seq"]) is int and row["seq"] > ACTIVATED_SEQ
         and type(row["prior_sha"]) is str
         and HEX64.fullmatch(row["prior_sha"]) is not None
         and previous[-1].get("schema") == v41.SCHEMA
         and previous[-1].get("to_source_sha") == FROM_V41
         and sum(p.get("schema") == v41.SCHEMA for p in previous) == 1
         and not any(p.get("schema") == SCHEMA for p in previous),
         "UNIQUE_V41_PREDECESSOR_REQUIRED")
    anchor = db.conn.execute(
        "SELECT sha FROM events WHERE seq=?", (ACTIVATED_SEQ,)).fetchone()
    need(anchor is not None and anchor["sha"] == ACTIVATED_HASH,
         "V41_ACTIVATION_HISTORY_DRIFT")
    v36 = [r for r in db.conn.execute(
        "SELECT seq,sha,payload FROM events "
        "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? ORDER BY seq",
        (row["seq"],))
        if json.loads(r["payload"]).get("schema") == v41.SCHEMA]
    need(len(v36) == 1 and v36[0]["seq"] < ACTIVATED_SEQ
         and json.loads(v36[0]["payload"]) == previous[-1]
         and HEX64.fullmatch(v36[0]["sha"]) is not None,
         "V36_EVENT_CUSTODY_DRIFT")
    # Future target-source tasks may grow without invalidating the immutable
    # predecessor. Historic tasks may never be rewritten after this event.
    sources = {p["from_source_sha"] for p in previous} | {FROM_V41}
    rows = [dict(t) for t in db.conn.execute(
        "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
        "evidence_dir,evidence_sha,quarantine_reason FROM tasks ORDER BY ticket")
        if t["source_sha"] in sources]
    good = sum(t["stage"] == "VERIFIED" for t in rows)
    bad = sorted(t["ticket"] for t in rows if t["stage"] == "QUARANTINED")
    need(good >= 153 and len(bad) == 56
         and len(rows) == good + len(bad)
         and all(t["source_sha"] in sources for t in rows),
         "HISTORIC_TERMINAL_CUSTODY_DRIFT")
    return {
        "v36_event_sha256": v36[0]["sha"],
        "v41_activation_head_sha256": ACTIVATED_HASH,
        "verified_historical_tasks": good,
        "custodied_negative_tasks": len(bad),
        "custodied_negative_tickets": bad,
        "terminal_tasks_sha256": digest(canonical(rows)),
    }


def verify_cold_event(db, row, doc, previous):
    """Called on every full Database.verify replay, including future reopens."""
    need(type(doc) is dict and set(doc) == FIELDS
         and doc["schema"] == SCHEMA
         and doc["from_source_sha"] == FROM_V41
         and type(doc["to_source_sha"]) is str
         and HEX40.fullmatch(doc["to_source_sha"]) is not None
         and doc["to_source_sha"] != FROM_V41
         and type(doc["owner_event_id"]) is int and doc["owner_event_id"] > 0
         and type(doc["original_head_seq"]) is int
         and doc["original_head_seq"] >= ACTIVATED_SEQ
         and row["seq"] == doc["original_head_seq"] + 1
         and type(doc["prior_event_head_sha256"]) is str
         and doc["prior_event_head_sha256"] == row["prior_sha"]
         and doc["original_head_sha256"] == row["prior_sha"]
         and type(doc["backup_run_id"]) is int
         and doc["backup_run_id"] > 0
         and all(type(doc[k]) is str and HEX64.fullmatch(doc[k]) is not None
                 for k in ("backup_manifest_sha256",
                           "backup_logical_all_tables_sha256",
                           "v36_event_sha256",
                           "v41_activation_head_sha256",
                           "terminal_tasks_sha256"))
         and doc["qualified_worker_blob"] ==
             "74dd90e6d71da6b53898c7a80d5362f1b0e6af27"
         and doc["purpose"] == PURPOSE
         and type(doc["new_dispatches"]) is int and doc["new_dispatches"] == 0
         and doc["scientific_first_use"] is False
         and doc["hybrid_admission"] is False
         and doc["v2_receipt_authorized"] is False,
         "EVENT_FIELDS_OR_AUTHORITY_DRIFT")
    before = snapshot(db, row, previous)
    need(all(doc[k] == v for k, v in before.items()),
         "FROZEN_PREDECESSOR_CUSTODY_DRIFT")


def _original(db):
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "EXISTING_OWNER_MUTEX_REQUIRED")
    db.verify()
    meta = db.meta().copy()
    need(meta["source_sha"] == FROM_V41
         and type(meta["head_seq"]) is int
         and meta["head_seq"] >= ACTIVATED_SEQ
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and db.dual_native_schema()
         and verify_native_activation(db)
         and db.ready() is None and not db.actives()
         and not is_migrated(db),
         "IDLE_ORIGINAL_V41_REQUIRED")
    return meta


def build_proof(db, target, owner_event_id, backup_run_id,
                backup_manifest_sha256):
    """Verify the full cold bundle before constructing a release *proposal*.

    Caller additionally authenticates the target main, owner comment, SID,
    task-disabled state, immutable release ref and worker CI. No such claims
    are inferred from this method or the backup itself.
    """
    meta = _original(db)
    need(type(target) is str and HEX40.fullmatch(target) is not None
         and target != FROM_V41
         and type(owner_event_id) is int and owner_event_id > 0
         and type(backup_run_id) is int and backup_run_id > 0
         and type(backup_manifest_sha256) is str
         and HEX64.fullmatch(backup_manifest_sha256) is not None,
         "TARGET_OWNER_OR_SEAL_INVALID")
    folder = db.filename.parent / ("f139-hybrid-before-" + str(backup_run_id))
    detached = bundle.verify_detached_restore(
        folder, expected_manifest_sha256=backup_manifest_sha256,
        target_sha=target, run_id=backup_run_id,
        expected_head_seq=meta["head_seq"],
        expected_head_sha256=meta["head_hash"])
    need(detached["independent_detached_restore_verified"] is True
         and detached["provider_archives_bytes_verified"] is True
         and detached["generation_binary_bytes_verified"] is True
         and detached["original_owner_mutations"] == 0
         and detached["source_transition_authorized"] is False
         and detached["hybrid_admission"] is False
         and detached["scientific_first_use"] is False,
         "DETACHED_FULL_COLD_RESTORE_REQUIRED")
    previous = [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")]
    row = {"seq": meta["head_seq"] + 1, "prior_sha": meta["head_hash"]}
    proof = {
        "schema": SCHEMA, "from_source_sha": FROM_V41,
        "to_source_sha": target, "owner_event_id": owner_event_id,
        "prior_event_head_sha256": meta["head_hash"],
        "original_head_seq": meta["head_seq"],
        "original_head_sha256": meta["head_hash"],
        **snapshot(db, row, previous),
        "backup_run_id": backup_run_id,
        "backup_manifest_sha256": backup_manifest_sha256,
        "backup_logical_all_tables_sha256":
            detached["logical_all_tables_sha256"],
        "qualified_worker_blob":
            "74dd90e6d71da6b53898c7a80d5362f1b0e6af27",
        "purpose": PURPOSE, "new_dispatches": 0,
        "scientific_first_use": False, "hybrid_admission": False,
        "v2_receipt_authorized": False,
    }
    verify_cold_event(db, row, proof, previous)
    need(db.meta() == meta, "PREVIEW_CHANGED_ORIGINAL_LEDGER")
    return proof


def commit_transition(db, proof, *, disabled_owner_witness,
                      verified_release_witness):
    """Single original transaction. A caller MUST keep the old task stopped.

    Neither witness is provided by this module. No CLI or workflow calls it;
    the real owner installer must independently authenticate both witnesses,
    the sealed backup and the exact source-specific operation before use.
    """
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and type(proof) is dict and set(proof) == FIELDS
         and callable(disabled_owner_witness)
         and callable(verified_release_witness)
         and disabled_owner_witness() is True
         and verified_release_witness() is True,
         "SEPARATELY_APPROVED_ORIGINAL_OWNER_REQUIRED")
    with db.transaction():
        expected = build_proof(
            db, proof["to_source_sha"], proof["owner_event_id"],
            proof["backup_run_id"], proof["backup_manifest_sha256"])
        need(canonical(expected) == canonical(proof)
             and disabled_owner_witness() is True
             and verified_release_witness() is True,
             "PRECOMMIT_AUTHORITY_OR_FROZEN_PROOF_DRIFT")
        db.conn.execute(
            "UPDATE meta SET source_sha=? WHERE id=1",
            (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
        need(disabled_owner_witness() is True
             and verified_release_witness() is True
             and db.meta()["head_seq"] == proof["original_head_seq"] + 1,
             "POSTCOMMIT_OWNER_HOLD_REQUIRED")
    return {
        "schema": "forge.f139.hybrid-v41.source-commit-hold.v1",
        "source_sha": db.meta()["source_sha"],
        "event_seq": db.meta()["head_seq"],
        "event_head_sha256": db.meta()["head_hash"],
        "task_resume_authorized": False,
        "policy_update_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False, "new_dispatches": 0,
    }
