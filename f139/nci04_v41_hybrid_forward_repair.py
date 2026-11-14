"""Inert forward-only source handoff from the *committed* V37 owner hold.

This module defines replay-verified evidence for one v38 successor. It cannot
read GitHub owner authority, schedule/enable an owner task, patch policy, or
authorize research. An original-owner caller must independently qualify a NEW
source-bound cold backup, owner approval, release, Windows SID and task hold.
No previously committed V37 event or quarantined task can be overwritten.
"""
from __future__ import annotations

import json
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation
from f139.hybrid_owner_admission import is_migrated
from f139 import nci04_v41_hybrid_source_transition as v37

SCHEMA = "forge.f139.source-transition.v38"
FROM = "c611c4362e3cc867984448a03ecdf3be923d2ef1"
V37_SEQ = 1830
V37_HEAD = "aaa60ef381c5a9f1e5296f56540ea9d73cef5a66f2562199d0cab81520abfadf"
PURPOSE = "original-owner-held-hybrid-forward-repair-without-activation"
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "prior_event_head_sha256", "original_head_seq", "original_head_sha256",
    "v37_source_event_sha256", "v37_original_cold_manifest_sha256",
    "verified_historical_tasks", "custodied_negative_tasks",
    "custodied_negative_tickets", "terminal_tasks_sha256",
    "backup_run_id", "backup_manifest_sha256",
    "backup_logical_all_tables_sha256", "qualified_worker_blob",
    "purpose", "new_dispatches", "scientific_first_use", "hybrid_admission",
    "task_resume_authorized", "owner_policy_update_authorized",
})


class ForwardRepairDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise ForwardRepairDenied("F139_HYBRID_FORWARD_" + reason)


def snapshot(db, row, previous):
    """Seal the unchanged original history, including all 56 negatives."""
    need(type(previous) is list and len(previous) > 0
         and previous[-1].get("schema") == v37.SCHEMA
         and previous[-1].get("to_source_sha") == FROM
         and sum(doc.get("schema") == v37.SCHEMA for doc in previous) == 1
         and not any(doc.get("schema") == SCHEMA for doc in previous)
         and row["seq"] == V37_SEQ + 1
         and row["prior_sha"] == V37_HEAD,
         "EXACT_SINGLE_V37_PREDECESSOR_REQUIRED")
    anchor = db.conn.execute(
        "SELECT seq,kind,sha,prior_sha,payload FROM events WHERE seq=?",
        (V37_SEQ,)).fetchone()
    need(anchor is not None and anchor["seq"] == V37_SEQ
         and anchor["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and anchor["sha"] == V37_HEAD
         and anchor["prior_sha"] == v37.ACTIVATED_HASH
         and json.loads(anchor["payload"]) == previous[-1]
         and previous[-1]["original_head_seq"] == v37.ACTIVATED_SEQ
         and previous[-1]["original_head_sha256"] == v37.ACTIVATED_HASH
         and previous[-1]["from_source_sha"] == v37.FROM_V41
         and previous[-1]["hybrid_admission"] is False
         and previous[-1]["scientific_first_use"] is False
         and previous[-1]["new_dispatches"] == 0,
         "IMMUTABLE_COMMITTED_V37_EVENT_REQUIRED")
    sources = {p["from_source_sha"] for p in previous} | {FROM}
    historical = [dict(t) for t in db.conn.execute(
        "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
        "evidence_dir,evidence_sha,quarantine_reason "
        "FROM tasks ORDER BY ticket") if t["source_sha"] in sources]
    good = sum(t["stage"] == "VERIFIED" for t in historical)
    bad = sorted(t["ticket"] for t in historical
                 if t["stage"] == "QUARANTINED")
    need(good == 153 and len(bad) == 56
         and len(historical) == 209
         and all(t["lane"] != "TTT-Hybrid" for t in historical),
         "ORIGINAL_153_56_HISTORY_DRIFT")
    return {
        "v37_source_event_sha256": V37_HEAD,
        "v37_original_cold_manifest_sha256":
            previous[-1]["backup_manifest_sha256"],
        "verified_historical_tasks": good,
        "custodied_negative_tasks": len(bad),
        "custodied_negative_tickets": bad,
        "terminal_tasks_sha256": digest(canonical(historical)),
    }


def verify_cold_event(db, row, doc, previous):
    """Called by full original Database.verify on every replay."""
    need(type(doc) is dict and set(doc) == FIELDS
         and doc["schema"] == SCHEMA
         and doc["from_source_sha"] == FROM
         and type(doc["to_source_sha"]) is str
         and HEX40.fullmatch(doc["to_source_sha"]) is not None
         and doc["to_source_sha"] != FROM
         and type(doc["owner_event_id"]) is int
         and doc["owner_event_id"] > 0
         and doc["original_head_seq"] == V37_SEQ
         and doc["original_head_sha256"] == V37_HEAD
         and doc["prior_event_head_sha256"] == row["prior_sha"]
         and row["seq"] == V37_SEQ + 1
         and row["prior_sha"] == V37_HEAD
         and type(doc["backup_run_id"]) is int
         and doc["backup_run_id"] > 0
         and all(type(doc[k]) is str
                 and HEX64.fullmatch(doc[k]) is not None for k in (
                     "backup_manifest_sha256",
                     "backup_logical_all_tables_sha256",
                     "v37_source_event_sha256",
                     "v37_original_cold_manifest_sha256",
                     "terminal_tasks_sha256"))
         and doc["qualified_worker_blob"] ==
            "74dd90e6d71da6b53898c7a80d5362f1b0e6af27"
         and doc["purpose"] == PURPOSE
         and type(doc["new_dispatches"]) is int
         and doc["new_dispatches"] == 0
         and all(doc[k] is False for k in (
             "scientific_first_use", "hybrid_admission",
             "task_resume_authorized", "owner_policy_update_authorized")),
         "NONCANONICAL_OR_UNAUTHORIZED_FORWARD_EVENT")
    expected = snapshot(db, row, previous)
    need(all(doc[k] == value for k, value in expected.items()),
         "ORIGINAL_COLD_HISTORY_OR_V37_SEAL_DRIFT")


def _held_original(db):
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_OWNER_MUTEX_REQUIRED")
    db.verify()
    meta = db.meta().copy()
    need(meta["source_sha"] == FROM
         and meta["head_seq"] == V37_SEQ
         and meta["head_hash"] == V37_HEAD
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and db.dual_native_schema()
         and not is_migrated(db)
         and db.ready() is None and not db.actives()
         and verify_native_activation(db, expected_source=v37.FROM_V41),
         "EXACT_UNCHANGED_ORIGINAL_V37_HOLD_REQUIRED")
    return meta


def build_proof(db, target, owner_event_id, backup_run_id,
                backup_manifest_sha256, backup_logical_all_tables_sha256):
    """Construct inert candidate only; external cold attestation still required."""
    before = _held_original(db)
    need(type(target) is str and HEX40.fullmatch(target) is not None
         and target != FROM
         and target != v37.FROM_V41
         and type(owner_event_id) is int and owner_event_id > 0
         and type(backup_run_id) is int and backup_run_id > 0
         and all(type(s) is str and HEX64.fullmatch(s) is not None
                 for s in (backup_manifest_sha256,
                           backup_logical_all_tables_sha256)),
         "NEW_TARGET_OWNER_OR_COLD_ATTESTATION_MISSING")
    previous = [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
        " ORDER BY seq")]
    row = {"seq": before["head_seq"] + 1,
           "prior_sha": before["head_hash"]}
    proof = {
        "schema": SCHEMA, "from_source_sha": FROM,
        "to_source_sha": target, "owner_event_id": owner_event_id,
        "prior_event_head_sha256": before["head_hash"],
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        **snapshot(db, row, previous),
        "backup_run_id": backup_run_id,
        "backup_manifest_sha256": backup_manifest_sha256,
        "backup_logical_all_tables_sha256":
            backup_logical_all_tables_sha256,
        "qualified_worker_blob":
            "74dd90e6d71da6b53898c7a80d5362f1b0e6af27",
        "purpose": PURPOSE, "new_dispatches": 0,
        "scientific_first_use": False, "hybrid_admission": False,
        "task_resume_authorized": False,
        "owner_policy_update_authorized": False,
    }
    verify_cold_event(db, row, proof, previous)
    need(db.meta() == before, "PROOF_BUILDER_MODIFIED_ORIGINAL")
    return proof


def commit_transition(db, proof, *, disabled_owner_witness,
                      release_witness, cold_bundle_witness):
    """Atomic write only with three EXTERNAL authenticated owner witnesses.

    No entrypoint is registered; unit-test callbacks never authorize live
    execution. Source only, no schema/policy/task change or research launch.
    """
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and type(proof) is dict and set(proof) == FIELDS
         and callable(disabled_owner_witness)
         and callable(release_witness)
         and callable(cold_bundle_witness)
         and all(witness() is True for witness in (
             disabled_owner_witness, release_witness, cold_bundle_witness)),
         "SEPARATE_SOURCE_OWNER_RELEASE_AND_COLD_APPROVAL_REQUIRED")
    with db.transaction():
        want = build_proof(
            db, proof["to_source_sha"], proof["owner_event_id"],
            proof["backup_run_id"], proof["backup_manifest_sha256"],
            proof["backup_logical_all_tables_sha256"])
        need(canonical(want) == canonical(proof)
             and all(witness() is True for witness in (
                 disabled_owner_witness, release_witness,
                 cold_bundle_witness)),
             "EXACT_PRECOMMIT_SOURCE_OR_WITNESS_DRIFT")
        db.conn.execute(
            "UPDATE meta SET source_sha=? WHERE id=1",
            (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
        need(all(witness() is True for witness in (
            disabled_owner_witness, release_witness,
            cold_bundle_witness)),
            "POSTCOMMIT_OWNER_WITNESS_LOST")
    return {
        "schema": "forge.f139.v38.source-forward-commit-hold.v1",
        "source_sha": db.meta()["source_sha"],
        "event_seq": db.meta()["head_seq"],
        "event_head_sha256": db.meta()["head_hash"],
        "task_resume_authorized": False,
        "owner_policy_update_authorized": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_dispatches": 0,
    }
