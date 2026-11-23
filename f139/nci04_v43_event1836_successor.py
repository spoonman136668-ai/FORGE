"""Inert F139 original event-1835 -> 1836 source-successor schema.

Read-only proof builder and replay verifier for a future *separately authorized*
single-owner installation. This module has NO registered Actions entrypoint,
live task control, source writer, policy mutation, or scientific first-use.
A cold backup *hash field* is not evidence that backup bytes exist.
"""
from __future__ import annotations

import json
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v41_pending_escrow import audit_committed_escrow
from f139 import nci04_v42_owner_source_readiness as v42
from f139 import nci04_v41_hybrid_event1833_successor as predecessor
from f139.hybrid_owner_admission import QUALIFIED_HYBRID_WORKER_BLOB

SCHEMA = "forge.f139.source-transition.v41"
PURPOSE = "held-original-v42-source-successor-no-activation"
PREDECESSOR_SEQ = v42.FROZEN_SEQ
PREDECESSOR_SHA = v42.FROZEN_HEAD
ORIGINAL_SOURCE = v42.BEFORE
NEW_OWNER_INTENT_AFTER = 6913813568
PREVIOUS_OWNER_READ_RUN = 43848805094
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "prior_event_head_sha256", "original_head_seq",
    "original_head_sha256", "v40_source_event_sha256",
    "repair_ancestor_sha", "verified_historical_tasks",
    "custodied_negative_tasks", "custodied_negative_tickets",
    "terminal_tasks_sha256", "backup_run_id",
    "backup_manifest_sha256", "backup_logical_all_tables_sha256",
    "qualified_worker_blob", "escrowed_issue_number",
    "escrow_reissue_authorized", "purpose",
    "new_dispatches", "scientific_first_use", "hybrid_admission",
    "task_resume_authorized", "owner_policy_update_authorized",
})


class OriginalSourceSuccessorDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise OriginalSourceSuccessorDenied("F139_V43_SOURCE_" + code)


def _context(db, row, previous):
    """Authenticate historic source event and frozen live head, no mutations.

    This is called from Database.verify() during cold replay, including after
    future admitted tasks. The historical 209 rows are scoped to earlier
    source SHAs, so new tasks cannot change the historical custody digest.
    """
    need(type(previous) is list and bool(previous)
         and row is not None
         and row["seq"] == PREDECESSOR_SEQ + 1
         and row["prior_sha"] == PREDECESSOR_SHA,
         "EXACT_EVENT1836_PREDECESSOR_REQUIRED")
    latest = previous[-1]
    need(type(latest) is dict
         and latest.get("schema") == predecessor.SCHEMA
         and latest.get("to_source_sha") == ORIGINAL_SOURCE
         and latest.get("scientific_first_use") is False
         and latest.get("hybrid_admission") is False
         and latest.get("new_dispatches") == 0
         and sum(x.get("schema") == predecessor.SCHEMA
                 for x in previous) == 1
         and sum(x.get("schema") == SCHEMA for x in previous) == 0,
         "LATEST_V40_ORIGINAL_SOURCE_REQUIRED")
    anchor = db.conn.execute(
        "SELECT seq,sha FROM events WHERE seq=?", (PREDECESSOR_SEQ,)).fetchone()
    need(anchor is not None and anchor["seq"] == PREDECESSOR_SEQ
         and anchor["sha"] == PREDECESSOR_SHA,
         "ORIGINAL_EVENT1835_HEAD_DRIFT")
    older = db.conn.execute(
        "SELECT seq,sha,payload FROM events "
        "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? "
        "ORDER BY seq DESC LIMIT 1", (PREDECESSOR_SEQ + 1,)).fetchone()
    need(older is not None
         and type(older["seq"]) is int
         and 0 < older["seq"] < PREDECESSOR_SEQ + 1
         and type(older["sha"]) is str
         and SHA64.fullmatch(older["sha"]) is not None
         and type(older["payload"]) is str
         and json.loads(older["payload"]) == latest,
         "ORIGINAL_LAST_SOURCE_EVENT_DRIFT")
    sources = {sha for p in previous
               for sha in (p["from_source_sha"], p["to_source_sha"])}
    need(ORIGINAL_SOURCE in sources, "ORIGINAL_SOURCE_NOT_HISTORICAL")
    historical = [
        dict(x) for x in db.conn.execute(
            "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
            "evidence_dir,evidence_sha,quarantine_reason "
            "FROM tasks ORDER BY ticket")
        if x["source_sha"] in sources
    ]
    positives = sum(t["stage"] == "VERIFIED" for t in historical)
    negatives = sorted(
        t["ticket"] for t in historical if t["stage"] == "QUARANTINED")
    need(len(historical) == 209
         and positives == 153 and len(negatives) == 56
         and all(t["stage"] in ("VERIFIED", "QUARANTINED")
                 and t["lane"] != "TTT-Hybrid" for t in historical)
         and type(latest.get("terminal_tasks_sha256")) is str
         and digest(canonical(historical)) ==
             latest["terminal_tasks_sha256"],
         "HISTORICAL_153_56_TERMINAL_CUSTODY_DRIFT")
    need(audit_committed_escrow(db) == "PAIRED_V41_TRANSITION",
         "PAIRED_ESCROW_1715_REQUIRED")
    return older["sha"], negatives, latest["terminal_tasks_sha256"]


def verify_cold_event(db, row, doc, previous):
    """Pure verification of one future v41 source event during ledger replay.

    The source proof does not authenticate an actual backup, task stop,
    approval, or deployed code. Those belong to an independent native owner
    adapter *before* it may write any SOURCE_TRANSITION_ADMITTED event.
    """
    need(type(doc) is dict and set(doc) == FIELDS
         and doc.get("schema") == SCHEMA
         and doc.get("from_source_sha") == ORIGINAL_SOURCE
         and type(doc.get("to_source_sha")) is str
         and SHA40.fullmatch(doc["to_source_sha"]) is not None
         and doc["to_source_sha"] != ORIGINAL_SOURCE
         and doc["to_source_sha"] not in {
             sha for p in previous
             for sha in (p["from_source_sha"], p["to_source_sha"])}
         and type(doc.get("owner_event_id")) is int
         and doc["owner_event_id"] > NEW_OWNER_INTENT_AFTER
         and type(doc.get("backup_run_id")) is int
         and doc["backup_run_id"] > PREVIOUS_OWNER_READ_RUN
         and all(type(doc.get(k)) is str
                 and SHA64.fullmatch(doc[k]) is not None
                 for k in (
                     "prior_event_head_sha256", "original_head_sha256",
                     "v40_source_event_sha256", "terminal_tasks_sha256",
                     "backup_manifest_sha256",
                     "backup_logical_all_tables_sha256"))
         and doc.get("prior_event_head_sha256") == PREDECESSOR_SHA
         and doc.get("original_head_seq") == PREDECESSOR_SEQ
         and doc.get("original_head_sha256") == PREDECESSOR_SHA
         and doc.get("repair_ancestor_sha") == v42.REPAIR
         and type(doc.get("verified_historical_tasks")) is int
         and doc["verified_historical_tasks"] == 153
         and type(doc.get("custodied_negative_tasks")) is int
         and doc["custodied_negative_tasks"] == 56
         and doc.get("qualified_worker_blob") ==
             QUALIFIED_HYBRID_WORKER_BLOB
         and doc.get("escrowed_issue_number") == 1715
         and doc.get("escrow_reissue_authorized") is False
         and doc.get("purpose") == PURPOSE
         and type(doc.get("new_dispatches")) is int
         and doc["new_dispatches"] == 0
         and all(doc.get(k) is False for k in (
             "scientific_first_use", "hybrid_admission",
             "task_resume_authorized", "owner_policy_update_authorized")),
         "FIELDS_OR_NO_AUTHORITY_DRIFT")
    old_sha, tickets, task_digest = _context(db, row, previous)
    need(doc["v40_source_event_sha256"] == old_sha
         and type(doc.get("custodied_negative_tickets")) is list
         and doc["custodied_negative_tickets"] == tickets
         and doc["terminal_tasks_sha256"] == task_digest,
         "FROZEN_HISTORY_OR_NEGATIVE_TICKETS_DRIFT")
    return True


def build_proof(db, *, target, owner_event_id, backup_run_id,
                backup_manifest_sha256, backup_logical_all_tables_sha256):
    """Make a candidate under the existing owner mutex; no SQLite writes.

    This helper intentionally has no release authority, GitHub API, backup
    creation, task mutation, or live entrypoint.
    """
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "EXISTING_ORIGINAL_MUTEX_REQUIRED")
    db.verify()
    before = db.meta().copy()
    need(before["source_sha"] == ORIGINAL_SOURCE
         and before["head_seq"] == PREDECESSOR_SEQ
         and before["head_hash"] == PREDECESSOR_SHA
         and before["enabled"] == 1 and before["legacy_suspended"] == 1
         and db.dual_native_schema()
         and db.ready() is None and not db.actives(),
         "ORIGINAL_OWNER_EVENT1835_NOT_IDLE")
    need(type(target) is str and SHA40.fullmatch(target) is not None
         and type(owner_event_id) is int
         and owner_event_id > NEW_OWNER_INTENT_AFTER
         and type(backup_run_id) is int
         and backup_run_id > PREVIOUS_OWNER_READ_RUN
         and all(type(x) is str
                 and SHA64.fullmatch(x) is not None
                 for x in (backup_manifest_sha256,
                           backup_logical_all_tables_sha256)),
         "NEW_TARGET_INTENT_OR_COLD_EVIDENCE_REQUIRED")
    previous = [
        json.loads(r["payload"]) for r in db.conn.execute(
            "SELECT payload FROM events "
            "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")]
    old_sha, negatives, task_digest = _context(
        db, {"seq": PREDECESSOR_SEQ + 1, "prior_sha": PREDECESSOR_SHA},
        previous)
    doc = {
        "schema": SCHEMA, "from_source_sha": ORIGINAL_SOURCE,
        "to_source_sha": target, "owner_event_id": owner_event_id,
        "prior_event_head_sha256": PREDECESSOR_SHA,
        "original_head_seq": PREDECESSOR_SEQ,
        "original_head_sha256": PREDECESSOR_SHA,
        "v40_source_event_sha256": old_sha,
        "repair_ancestor_sha": v42.REPAIR,
        "verified_historical_tasks": 153,
        "custodied_negative_tasks": 56,
        "custodied_negative_tickets": negatives,
        "terminal_tasks_sha256": task_digest,
        "backup_run_id": backup_run_id,
        "backup_manifest_sha256": backup_manifest_sha256,
        "backup_logical_all_tables_sha256":
            backup_logical_all_tables_sha256,
        "qualified_worker_blob": QUALIFIED_HYBRID_WORKER_BLOB,
        "escrowed_issue_number": 1715,
        "escrow_reissue_authorized": False,
        "purpose": PURPOSE, "new_dispatches": 0,
        "scientific_first_use": False, "hybrid_admission": False,
        "task_resume_authorized": False,
        "owner_policy_update_authorized": False,
    }
    verify_cold_event(
        db, {"seq": PREDECESSOR_SEQ + 1, "prior_sha": PREDECESSOR_SHA},
        doc, previous)
    need(before == db.meta() and db.conn.total_changes == 0,
         "PRECOMMIT_ORIGINAL_MUTATED")
    return doc
