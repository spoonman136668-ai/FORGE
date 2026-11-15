"""Inert held original event-1832 -> 1833 source successor, NOT a live route.

The original event 1832 already happened. Its source, complete owner intent,
provider backup and exact 153/56 history are authenticated, never recreated.
Any future single-owner transition needs a *new* real detached backup from
1832, a separately qualified protected-main release and owner witnesses.
This code registers no scheduler, GitHub comment, controller or activation.
"""
from __future__ import annotations

import json
import re

from f139.local_controller import Database, SingleOwner, canonical as event_canonical
from f139.nci04_native_contract import canonical as proof_canonical, digest
from f139.hybrid_owner_admission import is_migrated
from f139 import nci04_v41_hybrid_event1832_successor as v39

SCHEMA = "forge.f139.source-transition.v40"
SOURCE = "1479f963160001037566e4cef33582c5293fb773"
PREDECESSOR_SEQ = 1832
PREDECESSOR_PROOF_SHA256 = "27b07005a6ed3a430669321822efb9d70deb464ef29c89a77981da0f5d2225d9"
PREDECESSOR_OWNER_EVENT_ID = 6902399422
PREDECESSOR_BACKUP_RUN_ID = 43769577997
PREDECESSOR_BACKUP_MANIFEST_SHA256 = "4fb018d0a6eef636e56379e8f64a72d74c41a54ed06796247a938ef5cbafa90c"
PREDECESSOR_BACKUP_TABLES_SHA256 = "626bf57eb086c848be70d03bfc1ebcff0a9012a39595e7b3c5c4788865e919c7"
WORKER_BLOB = v39.WORKER_BLOB
PURPOSE = "held-original-source-forward-after-event-1832-no-activation"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha",
    "owner_event_id", "prior_event_head_sha256",
    "original_head_seq", "original_head_sha256",
    "v39_predecessor_proof_sha256", "verified_historical_tasks",
    "custodied_negative_tasks", "terminal_tasks_sha256",
    "backup_run_id", "backup_manifest_sha256",
    "backup_logical_all_tables_sha256", "qualified_worker_blob",
    "purpose", "new_dispatches", "scientific_first_use",
    "hybrid_admission", "task_resume_authorized",
    "owner_policy_update_authorized",
})
COLD_SCHEMA = "forge.f139.v40.original-event1832-cold-attestation.v1"
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


def need(value, reason):
    if not value:
        raise SuccessorDenied("F139_V40_SUCCESSOR_" + reason)


def predecessor(db, previous):
    """Certify the authentic already-committed event1832, not its run result."""
    need(type(previous) is list and len(previous) >= 3
         and type(previous[-1]) is dict
         and previous[-1].get("schema") == v39.SCHEMA
         and previous[-1].get("to_source_sha") == SOURCE
         and sum(p.get("schema") == v39.SCHEMA for p in previous) == 1
         and not any(p.get("schema") == SCHEMA for p in previous),
         "UNIQUE_EXISTING_V39_PREDECESSOR_REQUIRED")
    row = db.conn.execute(
        "SELECT seq,kind,sha,prior_sha,payload FROM events WHERE seq=?",
        (PREDECESSOR_SEQ,)).fetchone()
    need(row is not None and row["seq"] == PREDECESSOR_SEQ
         and row["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and row["prior_sha"] == v39.PREDECESSOR_SHA
         and type(row["sha"]) is str
         and SHA64.fullmatch(row["sha"]) is not None
         and row["payload"] ==
             event_canonical(previous[-1]).decode("ascii")
         and digest(proof_canonical(previous[-1])) ==
             PREDECESSOR_PROOF_SHA256,
         "FROZEN_EVENT1832_EVENT_OR_CANONICAL_PROOF_DRIFT")
    old = previous[-1]
    need(set(old) == v39.FIELDS
         and old["owner_event_id"] == PREDECESSOR_OWNER_EVENT_ID
         and old["backup_run_id"] == PREDECESSOR_BACKUP_RUN_ID
         and old["backup_manifest_sha256"] ==
             PREDECESSOR_BACKUP_MANIFEST_SHA256
         and old["backup_logical_all_tables_sha256"] ==
             PREDECESSOR_BACKUP_TABLES_SHA256
         and old["original_head_seq"] == v39.PREDECESSOR_SEQ
         and old["original_head_sha256"] == v39.PREDECESSOR_SHA
         and old["qualified_worker_blob"] == WORKER_BLOB
         and old["hybrid_admission"] is False
         and old["scientific_first_use"] is False
         and old["task_resume_authorized"] is False
         and old["owner_policy_update_authorized"] is False
         and old["new_dispatches"] == 0,
         "OWNER_EVENT1832_SOURCE_INTENT_OR_SCIENCE_FENCE_DRIFT")
    earlier = v39.snapshot(db, row, previous[:-1])
    need(earlier["verified_historical_tasks"] == 153
         and earlier["custodied_negative_tasks"] == 56
         and old["terminal_tasks_sha256"] ==
             earlier["terminal_tasks_sha256"],
         "FROZEN_153_56_ORIGINAL_HISTORY_DRIFT")
    return row["sha"], earlier["terminal_tasks_sha256"]


def snapshot(db, row, previous):
    need(type(row) is not type(None)
         and row["seq"] == PREDECESSOR_SEQ + 1,
         "EXACT_EVENT1833_SEQUENCE_REQUIRED")
    sha, historical_digest = predecessor(db, previous)
    need(row["prior_sha"] == sha,
         "ORIGINAL_EVENT1832_CHAIN_HASH_MISMATCH")
    return sha, historical_digest


def verify_cold_event(db, row, doc, previous):
    need(type(doc) is dict and set(doc) == FIELDS
         and doc["schema"] == SCHEMA
         and doc["from_source_sha"] == SOURCE
         and type(doc["to_source_sha"]) is str
         and SHA40.fullmatch(doc["to_source_sha"]) is not None
         and doc["to_source_sha"] != SOURCE
         and doc["to_source_sha"] not in {
             x for p in previous
             for x in (p["from_source_sha"], p["to_source_sha"])}
         and type(doc["owner_event_id"]) is int
         and doc["owner_event_id"] > 0
         and type(doc["backup_run_id"]) is int
         and doc["backup_run_id"] > 0
         and all(type(doc[k]) is str
                 and SHA64.fullmatch(doc[k]) is not None
                 for k in ("prior_event_head_sha256",
                           "original_head_sha256",
                           "v39_predecessor_proof_sha256",
                           "backup_manifest_sha256",
                           "backup_logical_all_tables_sha256",
                           "terminal_tasks_sha256"))
         and doc["original_head_seq"] == PREDECESSOR_SEQ
         and doc["v39_predecessor_proof_sha256"] ==
             PREDECESSOR_PROOF_SHA256
         and doc["verified_historical_tasks"] == 153
         and doc["custodied_negative_tasks"] == 56
         and doc["qualified_worker_blob"] == WORKER_BLOB
         and doc["purpose"] == PURPOSE
         and type(doc["new_dispatches"]) is int
         and doc["new_dispatches"] == 0
         and all(doc[k] is False for k in (
             "scientific_first_use", "hybrid_admission",
             "task_resume_authorized", "owner_policy_update_authorized")),
         "EVENT1833_FIELDS_OR_AUTHORITY_DRIFT")
    sha, task_digest = snapshot(db, row, previous)
    need(doc["prior_event_head_sha256"] == sha
         and doc["original_head_sha256"] == sha
         and doc["terminal_tasks_sha256"] == task_digest,
         "FROZEN_V39_PREDECESSOR_IDENTITY_DRIFT")


def _held_original(db):
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "EXISTING_ORIGINAL_OWNER_MUTEX_REQUIRED")
    db.verify()
    meta = db.meta().copy()
    need(meta["source_sha"] == SOURCE
         and meta["head_seq"] == PREDECESSOR_SEQ
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and db.dual_native_schema()
         and not is_migrated(db)
         and db.ready() is None and not db.actives(),
         "HELD_ORIGINAL_EVENT1832_REQUIRED")
    source_transitions = [
        json.loads(r["payload"]) for r in db.conn.execute(
            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
            "ORDER BY seq")]
    head, _ = predecessor(db, source_transitions)
    need(meta["head_hash"] == head,
         "ORIGINAL_EVENT1832_HEAD_DRIFT")
    return meta


def build_proof(db, *, target, owner_event_id, backup_run_id,
                backup_manifest_sha256, backup_logical_all_tables_sha256):
    before = _held_original(db)
    need(type(target) is str and SHA40.fullmatch(target) is not None
         and target != SOURCE
         and type(owner_event_id) is int and owner_event_id > 0
         and type(backup_run_id) is int and backup_run_id > 0
         and all(type(v) is str and SHA64.fullmatch(v) is not None for v in (
             backup_manifest_sha256, backup_logical_all_tables_sha256)),
         "FRESH_APPROVED_SOURCE_AND_COLD_BACKUP_REQUIRED")
    previous = [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "ORDER BY seq")]
    sha, task_digest = snapshot(
        db, {"seq": PREDECESSOR_SEQ + 1,
             "prior_sha": before["head_hash"]}, previous)
    proof = {
        "schema": SCHEMA, "from_source_sha": SOURCE,
        "to_source_sha": target, "owner_event_id": owner_event_id,
        "prior_event_head_sha256": sha, "original_head_seq": PREDECESSOR_SEQ,
        "original_head_sha256": sha,
        "v39_predecessor_proof_sha256": PREDECESSOR_PROOF_SHA256,
        "verified_historical_tasks": 153, "custodied_negative_tasks": 56,
        "terminal_tasks_sha256": task_digest,
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
        db, {"seq": PREDECESSOR_SEQ + 1, "prior_sha": sha},
        proof, previous)
    need(db.meta() == before, "PROOF_CHANGED_ORIGINAL_OWNER")
    return proof


def _check_cold_receipt(doc, receipt):
    """Validate declared fields; live adapter must verify actual cold bytes."""
    need(type(receipt) is dict and set(receipt) == COLD_FIELDS
         and receipt["schema"] == COLD_SCHEMA
         and receipt["original_source_sha"] == SOURCE
         and receipt["original_head_seq"] == PREDECESSOR_SEQ
         and receipt["original_head_sha256"] ==
             doc["original_head_sha256"]
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
         "REAL_EVENT1832_COLD_CUSTODY_REQUIRED")


def commit_transition(db, proof, *, disabled_owner_witness,
                      release_witness, detached_cold_witness):
    """Inert internal primitive. Not wired to any owner command or workflow.

    Witnesses alone do not authorize use: only a separately qualified
    original-owner native adapter can establish real release and cold custody.
    """
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and type(proof) is dict and set(proof) == FIELDS
         and callable(disabled_owner_witness)
         and callable(release_witness)
         and callable(detached_cold_witness),
         "ORIGINAL_MUTEX_AND_EXTERNAL_RELEASE_AUTHORITY_REQUIRED")
    def witnesses():
        need(disabled_owner_witness() is True
             and release_witness() is True,
             "DISABLED_ORIGINAL_OWNER_AND_RELEASE_REQUIRED")
        _check_cold_receipt(proof, detached_cold_witness())
    witnesses()
    with db.transaction():
        witnesses()
        want = build_proof(
            db, target=proof["to_source_sha"],
            owner_event_id=proof["owner_event_id"],
            backup_run_id=proof["backup_run_id"],
            backup_manifest_sha256=proof["backup_manifest_sha256"],
            backup_logical_all_tables_sha256=
                proof["backup_logical_all_tables_sha256"])
        need(proof_canonical(want) == proof_canonical(proof),
             "EXACT_PRECOMMIT_PROOF_DRIFT")
        witnesses()
        db.conn.execute(
            "UPDATE meta SET source_sha=? WHERE id=1",
            (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
        witnesses()
    return {
        "schema": "forge.f139.v40.event1833.source-hold.v1",
        "source_sha": db.meta()["source_sha"],
        "event_seq": db.meta()["head_seq"],
        "event_head_sha256": db.meta()["head_hash"],
        "task_resume_authorized": False,
        "owner_policy_update_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False, "new_dispatches": 0,
    }
