"""Inert event-1831 -> 1832 source successor for the SAME held F139 owner.

Not a CLI, workflow, task restart, live migration, policy update or scientific
first use. A future separately authorized native owner adapter must establish a
fresh independent detached backup and three authentic source-bound witnesses.
Never reapply event 1831 or return to event 1830.
"""
from __future__ import annotations

import json
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.hybrid_owner_admission import is_migrated
from f139 import nci04_v41_hybrid_forward_repair as v38

SCHEMA = "forge.f139.source-transition.v39"
SOURCE = "eae38f6d0af27c41181da10c35685c6a3e8c68b4"
PREDECESSOR_SEQ = 1831
PREDECESSOR_SHA = "139dc5ef09ad0fd6891c77c782146ad3febdefd7c0910d46c746aa9966f87c44"
WORKER_BLOB = "74dd90e6d71da6b53898c7a80d5362f1b0e6af27"
PURPOSE = "held-original-source-forward-after-event-1831-no-activation"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha",
    "owner_event_id", "prior_event_head_sha256",
    "original_head_seq", "original_head_sha256",
    "v38_event_sha256", "verified_historical_tasks",
    "custodied_negative_tasks", "terminal_tasks_sha256",
    "backup_run_id", "backup_manifest_sha256",
    "backup_logical_all_tables_sha256", "qualified_worker_blob",
    "purpose", "new_dispatches", "scientific_first_use",
    "hybrid_admission", "task_resume_authorized",
    "owner_policy_update_authorized",
})
COLD_SCHEMA = "forge.f139.v39.original-event1831-cold-attestation.v1"
COLD_FIELDS = frozenset({
    "schema", "original_source_sha", "original_head_seq",
    "original_head_sha256", "target_source_sha", "backup_run_id",
    "backup_manifest_sha256", "backup_logical_all_tables_sha256",
    "independent_detached_restore_verified",
    "provider_archives_bytes_verified", "generation_binary_bytes_verified",
    "negative_custody_bytes_verified", "original_owner_mutations",
    "new_dispatches", "scientific_first_use",
})


class SuccessorDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise SuccessorDenied("F139_V39_SUCCESSOR_" + reason)


def snapshot(db, row, previous):
    """Authenticate one original v38 event and unmodified historical tasks.

    This is replay-time verification of the predecessor; it does not accept
    a matching fabricated witness instead of the original full Database.verify.
    """
    need(type(previous) is list and len(previous) >= 2
         and previous[-1].get("schema") == v38.SCHEMA
         and previous[-1].get("to_source_sha") == SOURCE
         and sum(p.get("schema") == v38.SCHEMA for p in previous) == 1
         and not any(p.get("schema") == SCHEMA for p in previous)
         and row["seq"] == PREDECESSOR_SEQ + 1
         and row["prior_sha"] == PREDECESSOR_SHA,
         "SINGLE_EVENT1831_PREDECESSOR_REQUIRED")
    anchor = db.conn.execute(
        "SELECT seq,kind,sha,prior_sha,payload FROM events WHERE seq=?",
        (PREDECESSOR_SEQ,)).fetchone()
    need(anchor is not None and anchor["seq"] == PREDECESSOR_SEQ
         and anchor["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and anchor["sha"] == PREDECESSOR_SHA
         and anchor["prior_sha"] == v38.V37_HEAD
         and json.loads(anchor["payload"]) == previous[-1],
         "ORIGINAL_EVENT1831_HASH_OR_PAYLOAD_DRIFT")
    legacy = v38.snapshot(db, anchor, previous[:-1])
    need(legacy["verified_historical_tasks"] == 153
         and legacy["custodied_negative_tasks"] == 56
         and previous[-1]["terminal_tasks_sha256"] ==
             legacy["terminal_tasks_sha256"]
         and previous[-1]["qualified_worker_blob"] == WORKER_BLOB
         and previous[-1]["hybrid_admission"] is False
         and previous[-1]["scientific_first_use"] is False
         and previous[-1]["task_resume_authorized"] is False
         and previous[-1]["owner_policy_update_authorized"] is False
         and previous[-1]["new_dispatches"] == 0,
         "ORIGINAL_153_56_OR_AUTHORITY_DRIFT")
    return legacy


def verify_cold_event(db, row, doc, previous):
    """Read-only historical replay after any future restart or task activity."""
    need(type(doc) is dict and set(doc) == FIELDS
         and doc["schema"] == SCHEMA
         and doc["from_source_sha"] == SOURCE
         and type(doc["to_source_sha"]) is str
         and SHA40.fullmatch(doc["to_source_sha"]) is not None
         and doc["to_source_sha"] != SOURCE
         and doc["to_source_sha"] not in {
             value for p in previous
             for value in (p["from_source_sha"], p["to_source_sha"])}
         and type(doc["owner_event_id"]) is int
         and doc["owner_event_id"] > 0
         and doc["prior_event_head_sha256"] == row["prior_sha"]
         and doc["original_head_seq"] == PREDECESSOR_SEQ
         and doc["original_head_sha256"] == PREDECESSOR_SHA
         and doc["v38_event_sha256"] == PREDECESSOR_SHA
         and type(doc["backup_run_id"]) is int
         and doc["backup_run_id"] > 0
         and all(type(doc[k]) is str and SHA64.fullmatch(doc[k])
                 for k in ("backup_manifest_sha256",
                           "backup_logical_all_tables_sha256",
                           "terminal_tasks_sha256"))
         and doc["qualified_worker_blob"] == WORKER_BLOB
         and doc["purpose"] == PURPOSE
         and type(doc["new_dispatches"]) is int
         and doc["new_dispatches"] == 0
         and all(doc[k] is False for k in (
             "scientific_first_use", "hybrid_admission",
             "task_resume_authorized", "owner_policy_update_authorized")),
         "EVENT1832_FIELDS_OR_NO_FIRST_USE_FENCE")
    original = snapshot(db, row, previous)
    need(doc["verified_historical_tasks"] == 153
         and doc["custodied_negative_tasks"] == 56
         and doc["terminal_tasks_sha256"] ==
             original["terminal_tasks_sha256"],
         "HISTORICAL_153_56_CUSTODY_MISMATCH")


def _held_original(db):
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "EXISTING_SINGLE_OWNER_MUTEX_REQUIRED")
    db.verify()
    before = db.meta().copy()
    need(before["source_sha"] == SOURCE
         and before["head_seq"] == PREDECESSOR_SEQ
         and before["head_hash"] == PREDECESSOR_SHA
         and before["enabled"] == 1
         and before["legacy_suspended"] == 1
         and db.dual_native_schema()
         and not is_migrated(db)
         and not db.actives()
         and db.ready() is None,
         "ORIGINAL_COMMITTED_EVENT1831_HOLD_REQUIRED")
    return before


def build_proof(db, *, target, owner_event_id, backup_run_id,
                backup_manifest_sha256, backup_logical_all_tables_sha256):
    """Build exact candidate from a real held event 1831; zero SQLite writes."""
    before = _held_original(db)
    need(type(target) is str and SHA40.fullmatch(target) is not None
         and target != SOURCE
         and type(owner_event_id) is int and owner_event_id > 0
         and type(backup_run_id) is int and backup_run_id > 0
         and all(type(h) is str and SHA64.fullmatch(h) is not None for h in
                 (backup_manifest_sha256, backup_logical_all_tables_sha256)),
         "TARGET_OWNER_OR_NEW_COLD_PROOF_REQUIRED")
    previous = [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "ORDER BY seq")]
    old = snapshot(db, {"seq": PREDECESSOR_SEQ + 1,
                        "prior_sha": PREDECESSOR_SHA}, previous)
    doc = {
        "schema": SCHEMA, "from_source_sha": SOURCE,
        "to_source_sha": target,
        "owner_event_id": owner_event_id,
        "prior_event_head_sha256": PREDECESSOR_SHA,
        "original_head_seq": PREDECESSOR_SEQ,
        "original_head_sha256": PREDECESSOR_SHA,
        "v38_event_sha256": PREDECESSOR_SHA,
        "verified_historical_tasks": 153,
        "custodied_negative_tasks": 56,
        "terminal_tasks_sha256": old["terminal_tasks_sha256"],
        "backup_run_id": backup_run_id,
        "backup_manifest_sha256": backup_manifest_sha256,
        "backup_logical_all_tables_sha256":
            backup_logical_all_tables_sha256,
        "qualified_worker_blob": WORKER_BLOB,
        "purpose": PURPOSE, "new_dispatches": 0,
        "scientific_first_use": False, "hybrid_admission": False,
        "task_resume_authorized": False,
        "owner_policy_update_authorized": False,
    }
    verify_cold_event(
        db, {"seq": PREDECESSOR_SEQ + 1,
             "prior_sha": PREDECESSOR_SHA}, doc, previous)
    need(db.meta() == before, "PROOF_BUILDER_CHANGED_PREIMAGE")
    return doc


def _check_cold_receipt(doc, receipt):
    """Caller-supplied receipt must be from a separately certified adapter.

    This function authenticates field consistency, NOT the backing bytes.
    No live caller/entrypoint or source-transition authority is registered.
    """
    need(type(receipt) is dict and set(receipt) == COLD_FIELDS
         and receipt["schema"] == COLD_SCHEMA
         and receipt["original_source_sha"] == SOURCE
         and receipt["original_head_seq"] == PREDECESSOR_SEQ
         and receipt["original_head_sha256"] == PREDECESSOR_SHA
         and receipt["target_source_sha"] == doc["to_source_sha"]
         and receipt["backup_run_id"] == doc["backup_run_id"]
         and receipt["backup_manifest_sha256"] ==
             doc["backup_manifest_sha256"]
         and receipt["backup_logical_all_tables_sha256"] ==
             doc["backup_logical_all_tables_sha256"]
         and type(receipt["original_owner_mutations"]) is int
         and receipt["original_owner_mutations"] == 0
         and type(receipt["new_dispatches"]) is int
         and receipt["new_dispatches"] == 0
         and receipt["scientific_first_use"] is False
         and all(receipt[k] is True for k in (
             "independent_detached_restore_verified",
             "provider_archives_bytes_verified",
             "generation_binary_bytes_verified",
             "negative_custody_bytes_verified")),
         "DETACHED_COLD_RECEIPT_OR_PROVENANCE_REQUIRED")


def commit_transition(db, proof, *, disabled_owner_witness,
                      release_witness, detached_cold_witness):
    """Atomic internal mechanism, deliberately unregistered and INERT.

    The provided witnesses are necessary but NOT execution authority; a
    privileged native owner adapter must first independently authenticate
    owner intent, actual detached bytes, protected-main release and task.
    """
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and type(proof) is dict and set(proof) == FIELDS
         and callable(disabled_owner_witness)
         and callable(release_witness)
         and callable(detached_cold_witness),
         "NO_LIVE_ADAPTER_OR_UNOWNED_TRANSACTION")
    def witnesses():
        need(disabled_owner_witness() is True
             and release_witness() is True,
             "DISABLED_OWNER_OR_RELEASE_NOT_AUTHENTIC")
        _check_cold_receipt(proof, detached_cold_witness())
    witnesses()
    with db.transaction():
        witnesses()
        expected = build_proof(
            db, target=proof["to_source_sha"],
            owner_event_id=proof["owner_event_id"],
            backup_run_id=proof["backup_run_id"],
            backup_manifest_sha256=proof["backup_manifest_sha256"],
            backup_logical_all_tables_sha256=
                proof["backup_logical_all_tables_sha256"])
        need(canonical(expected) == canonical(proof),
             "PRECOMMIT_APPROVED_INTENT_DRIFT")
        witnesses()
        db.conn.execute("UPDATE meta SET source_sha=? WHERE id=1",
                        (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
        witnesses()
    return {
        "schema": "forge.f139.v39.event1832.source-hold.v1",
        "source_sha": db.meta()["source_sha"],
        "event_seq": db.meta()["head_seq"],
        "event_head_sha256": db.meta()["head_hash"],
        "task_resume_authorized": False,
        "owner_policy_update_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }
