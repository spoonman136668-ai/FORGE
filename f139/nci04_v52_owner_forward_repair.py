"""V52 original F139 owner source repair after authentic event 1837.

This module ONLY supplies a replay verifier and a one-shot, mutex-held
copy/live source-transition primitive. It does not select an execution host,
grant owner authority, change any task, authenticate GitHub, or promote science.
The original owner workflow separately establishes those boundaries.
"""
from __future__ import annotations

from collections import Counter
import json
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import (
    APPROVAL_SCHEMA, ACTIVATION_KIND, activate_native, verify_native_activation,
)

SCHEMA = "forge.f139.source-transition.v42"
FROM_SOURCE = "4ccbb84785a43e038453d6f2bda5415ecb364084"
HEAD_SEQ = 1837
HEAD_SHA = "5a1ec5be32c4604e1c355629daf0f7f05749fb8201b161308d3606f0d3b6b8c6"
PREVIOUS_TRANSITION_SHA = "dbc4e12862c819812121adf1df905f74023c65633067bcabe906488d37468964"
READONLY_RUN = 43996174295
MIN_OWNER_COMMENT = 6935011550
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha",
    "prior_event_head_sha256", "original_activation_sha256",
    "previous_source_transition_sha256",
    "owner_comment_id", "qualified_main_run_id", "rehearsal_run_id",
    "original_readonly_run_id", "backup_sqlite_sha256",
    "terminal_tasks_sha256", "custodied_negative_tickets",
    "verified_historical_tasks", "custodied_negative_tasks",
    "source_repair_purpose", "new_dispatches", "scientific_first_use",
    "native_development_approved", "new_controller", "new_scheduler",
    "new_queue", "paid_api_calls",
})
PURPOSE = "correct-canonical-python-main-module-original-owner-development-only"


class ForwardRepairDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise ForwardRepairDenied("F139_V52_" + code)


def _history(db, transitions):
    historical_sources = {
        source for transition in transitions
        for source in (transition["from_source_sha"], transition["to_source_sha"])
    }
    history = [
        dict(row) for row in db.conn.execute(
            "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
            "evidence_dir,evidence_sha,quarantine_reason "
            "FROM tasks ORDER BY ticket")
        if row["source_sha"] in historical_sources
    ]
    return history, historical_sources


def original_snapshot(db):
    """Read-only authentic preimage, before any V52 source mutation."""
    db.verify()
    m = db.meta().copy()
    need(m["source_sha"] == FROM_SOURCE and
         m["head_seq"] == HEAD_SEQ and m["head_hash"] == HEAD_SHA and
         m["enabled"] == 1 and m["legacy_suspended"] == 1 and
         db.ready() is None and not db.actives(),
         "ORIGINAL_EVENT1837_SOURCE_OR_PENDING_DRIFT")
    rows = list(db.conn.execute(
        "SELECT seq,kind,sha,prior_sha FROM events WHERE seq IN (?,?)",
        (HEAD_SEQ - 1, HEAD_SEQ)))
    need(len(rows) == 2 and
         rows[0]["seq"] == HEAD_SEQ - 1 and
         rows[0]["kind"] == "SOURCE_TRANSITION_ADMITTED" and
         rows[0]["sha"] == PREVIOUS_TRANSITION_SHA and
         rows[1]["seq"] == HEAD_SEQ and
         rows[1]["kind"] == "NATIVE_DEVELOPMENT_ACTIVATED" and
         rows[1]["prior_sha"] == PREVIOUS_TRANSITION_SHA and
         rows[1]["sha"] == HEAD_SHA and
         verify_native_activation(db) is True,
         "ORIGINAL_EVENT1836_TO_1837_ANCHOR_DRIFT")
    counts = Counter(row["stage"] for row in db.conn.execute(
        "SELECT stage FROM tasks"))
    need(counts == Counter({"VERIFIED": 153, "QUARANTINED": 56}),
         "ORIGINAL_153_56_TASKS_CHANGED")
    prior = list(db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
        " ORDER BY seq DESC LIMIT 1"))
    need(len(prior) == 1, "MISSING_V41_TRANSITION")
    last = json.loads(prior[0]["payload"])
    need(last.get("schema") == "forge.f139.source-transition.v41"
         and last.get("to_source_sha") == FROM_SOURCE
         and last.get("verified_historical_tasks") == 153
         and last.get("custodied_negative_tasks") == 56,
         "FROZEN_V41_PREDECESSOR_DRIFT")
    return last


def verify_cold_event(db, row, doc, previous):
    """Verify append-only V52 event from frozen historical evidence only.

    This is invoked by Database.verify on every later cold read. Runtime
    authorization and backup-file existence are checked before commit by the
    separate, original-owner guarded workflow, never inferred from this event.
    """
    need(type(previous) is list and bool(previous)
         and type(doc) is dict and set(doc) == FIELDS
         and doc.get("schema") == SCHEMA
         and row["seq"] == HEAD_SEQ + 1
         and row["prior_sha"] == HEAD_SHA
         and doc.get("from_source_sha") == FROM_SOURCE
         and type(doc.get("to_source_sha")) is str
         and SHA40.fullmatch(doc["to_source_sha"]) is not None
         and doc["to_source_sha"] != FROM_SOURCE
         and doc["to_source_sha"] not in {
             s for t in previous
             for s in (t["from_source_sha"], t["to_source_sha"])}
         and doc.get("prior_event_head_sha256") == HEAD_SHA
         and doc.get("original_activation_sha256") == HEAD_SHA
         and doc.get("previous_source_transition_sha256") ==
             PREVIOUS_TRANSITION_SHA
         and doc.get("original_readonly_run_id") == READONLY_RUN
         and type(doc.get("owner_comment_id")) is int
         and doc["owner_comment_id"] > MIN_OWNER_COMMENT
         and all(type(doc.get(k)) is int and doc[k] > 0
                 for k in ("qualified_main_run_id", "rehearsal_run_id"))
         and doc["rehearsal_run_id"] != doc["qualified_main_run_id"]
         and all(type(doc.get(k)) is str and SHA64.fullmatch(doc[k])
                 for k in ("backup_sqlite_sha256", "terminal_tasks_sha256"))
         and doc.get("source_repair_purpose") == PURPOSE
         and type(doc.get("verified_historical_tasks")) is int
         and doc["verified_historical_tasks"] == 153
         and type(doc.get("custodied_negative_tasks")) is int
         and doc["custodied_negative_tasks"] == 56
         and type(doc.get("new_dispatches")) is int
         and doc["new_dispatches"] == 0
         and doc.get("scientific_first_use") is False
         and doc.get("native_development_approved") is True
         and doc.get("new_controller") is False
         and doc.get("new_scheduler") is False
         and doc.get("new_queue") is False
         and type(doc.get("paid_api_calls")) is int
         and doc["paid_api_calls"] == 0
         and not any(x.get("schema") == SCHEMA for x in previous),
         "SOURCE_REPAIR_FIELDS_OR_SINGLE_USE_DRIFT")
    older = previous[-1]
    need(older.get("schema") == "forge.f139.source-transition.v41"
         and older.get("to_source_sha") == FROM_SOURCE
         and older.get("verified_historical_tasks") == 153
         and older.get("custodied_negative_tasks") == 56,
         "V41_SOURCE_PREDECESSOR_CHANGED")
    anchor = db.conn.execute(
        "SELECT seq,kind,sha,prior_sha,payload FROM events WHERE seq=?",
        (HEAD_SEQ,)).fetchone()
    original_activation = (json.loads(anchor["payload"])
                           if anchor is not None else {})
    need(anchor is not None and
         anchor["seq"] == HEAD_SEQ and
         anchor["kind"] == "NATIVE_DEVELOPMENT_ACTIVATED" and
         anchor["sha"] == HEAD_SHA and
         anchor["prior_sha"] == PREVIOUS_TRANSITION_SHA and
         original_activation.get("schema") ==
             "forge.f139.nci04.owner-native-activation.v1" and
         original_activation.get("source_sha") == FROM_SOURCE and
         original_activation.get("development_only") is True and
         original_activation.get("scientific_first_use") is False and
         original_activation.get("new_dispatches") == 0,
         "V50_ACTIVATION_ANCESTRY_MISSING")
    history, sources = _history(db, previous)
    ticket_list = sorted(t["ticket"] for t in history
                         if t["stage"] == "QUARANTINED")
    need(len(history) == 209
         and sum(t["stage"] == "VERIFIED" for t in history) == 153
         and len(ticket_list) == 56
         and doc["custodied_negative_tickets"] == ticket_list
         and older["custodied_negative_tickets"] == ticket_list
         and doc["terminal_tasks_sha256"] ==
             older["terminal_tasks_sha256"]
         and digest(canonical(history)) == doc["terminal_tasks_sha256"],
         "HISTORIC_TERMINAL_CUSTODY_CHANGED")
    return True


def make_proof(db, *, target, owner_comment_id, main_run_id,
               rehearsal_run_id, backup_sha256):
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_MUTEX_REQUIRED")
    old = original_snapshot(db)
    need(type(target) is str and SHA40.fullmatch(target) is not None
         and target != FROM_SOURCE
         and type(owner_comment_id) is int
         and owner_comment_id > MIN_OWNER_COMMENT
         and type(main_run_id) is int and main_run_id > 0
         and type(rehearsal_run_id) is int and rehearsal_run_id > 0
         and main_run_id != rehearsal_run_id
         and type(backup_sha256) is str
         and SHA64.fullmatch(backup_sha256) is not None,
         "RELEASE_INPUTS_INVALID")
    previous = [json.loads(t["payload"]) for t in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
        " ORDER BY seq")]
    proof = {
        "schema": SCHEMA,
        "from_source_sha": FROM_SOURCE, "to_source_sha": target,
        "prior_event_head_sha256": HEAD_SHA,
        "original_activation_sha256": HEAD_SHA,
        "previous_source_transition_sha256": PREVIOUS_TRANSITION_SHA,
        "owner_comment_id": owner_comment_id,
        "qualified_main_run_id": main_run_id,
        "rehearsal_run_id": rehearsal_run_id,
        "original_readonly_run_id": READONLY_RUN,
        "backup_sqlite_sha256": backup_sha256,
        "terminal_tasks_sha256": old["terminal_tasks_sha256"],
        "custodied_negative_tickets": old["custodied_negative_tickets"],
        "verified_historical_tasks": 153,
        "custodied_negative_tasks": 56,
        "source_repair_purpose": PURPOSE,
        "new_dispatches": 0, "scientific_first_use": False,
        "native_development_approved": True,
        "new_controller": False, "new_scheduler": False,
        "new_queue": False, "paid_api_calls": 0,
    }
    verify_cold_event(db, {"seq": HEAD_SEQ+1, "prior_sha": HEAD_SHA},
                      proof, previous)
    return proof


def apply_copy_or_original(db, proof):
    """Irreversible on the supplied DB; call on a detached copy in rehearsal.

    On an original database this must run ONLY after the separate owner
    workflow quiesces the one genuine scheduled task and verifies a backup.
    """
    need(type(db) is Database and
         SingleOwner.held(db.filename.with_suffix(".lock")),
         "EXCLUSIVE_ORIGINAL_MUTEX_REQUIRED")
    old = original_snapshot(db)
    previous = [json.loads(t["payload"]) for t in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
        " ORDER BY seq")]
    verify_cold_event(db, {"seq": HEAD_SEQ+1, "prior_sha": HEAD_SHA},
                      proof, previous)
    need(proof["terminal_tasks_sha256"] == old["terminal_tasks_sha256"],
         "FROZEN_TASK_CUSTODY_CHANGED")
    with db.transaction():
        need(db.meta()["head_seq"] == HEAD_SEQ
             and db.meta()["head_hash"] == HEAD_SHA,
             "ORIGINAL_LEDGER_CHANGED_AT_COMMIT")
        db.conn.execute(
            "UPDATE meta SET source_sha=? WHERE id=1",
            (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
    need(db.meta()["head_seq"] == HEAD_SEQ+1
         and db.meta()["source_sha"] == proof["to_source_sha"],
         "POSTCOMMIT_SOURCE_NOT_FROZEN")
    # A second activation is legitimate only because event1838 is a new,
    # qualified source. Existing native authority performs all checks.
    approval = {
        "schema": APPROVAL_SCHEMA,
        "source_sha": proof["to_source_sha"],
        "expected_event_head_sha256": db.meta()["head_hash"],
        "native_development_approved": True,
        "scientific_first_use": False, "create_controller": False,
        "paid_api_calls": 0,
    }
    need(activate_native(db, approval) is True,
         "POSTCOMMIT_NATIVE_ACTIVATION_MISSING")
    db.verify()
    m = db.meta()
    need(m["head_seq"] == HEAD_SEQ+2
         and m["source_sha"] == proof["to_source_sha"]
         and verify_native_activation(db) is True,
         "ACTIVATION_1839_OR_SOURCE_DRIFT")
    return {
        "schema": "forge.f139.v52.original-forward-repair-result.v1",
        "target_source_sha": m["source_sha"],
        "head_seq": m["head_seq"], "head_sha256": m["head_hash"],
        "previous_activation_sha256": HEAD_SHA,
        "scientific_first_use": False, "new_dispatches": 0,
    }
