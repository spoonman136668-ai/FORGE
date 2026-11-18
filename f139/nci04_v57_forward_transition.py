"""V47 cold-only forward source proof for exactly one original READY ticket.

This module cannot install source, dispatch a task, authorize first-use, or
change owner policy. Exact original-owner release is a separate authenticated
procedure with quiescence, backup, detached rehearsal and CI.
"""
from __future__ import annotations

from collections import Counter
import json
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_v57_original_pending_preflight import (
    SOURCE, ORIGINAL_SOURCE, TICKET, ANCHOR_SEQ, ANCHOR_SHA,
    ADMISSION_SHA, INTAKE_SHA,
    NATIVE_ACTIVATION_SHA, READY_SOURCE_TRANSITION_SHA,
    original_pending_snapshot,
)

SCHEMA = "forge.f139.source-transition.v47"
PREVIOUS = "forge.f139.source-transition.v46"
PURPOSE = "preserve-v46-original-carried-ticket-development-only"
MIN_OWNER_RUN = 44396465727
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha",
    "prior_event_head_sha256", "event1857_ancestor_sha256",
    "prior_source_transition_sha256", "prior_activation_sha256",
    "owner_run_id", "qualified_main_run_id", "rehearsal_run_id",
    "backup_sqlite_sha256", "genenv_executable_sha256",
    "generation_mechanism_sha256", "terminal_tasks_sha256",
    "verified_historical_tasks", "custodied_negative_tasks",
    "custodied_negative_tickets", "original_ready_ticket",
    "original_ready_lane", "original_ready_source_sha",
    "original_ready_identity_sha256", "original_admission_sha256",
    "original_intake_sha256", "source_transition_purpose",
    "native_development_approved", "scientific_first_use",
    "new_dispatches", "new_controller", "new_scheduler", "new_queue",
    "paid_api_calls",
})


class V47TransitionDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise V47TransitionDenied("F139_V47_" + code)


def frozen_old_terminal_rows(db, previous):
    """Sealed previous sources only. Never absorb the V56 READY ticket.

    The original V56 source was not terminal at transition time, so any
    post-release completion of its READY ticket must not change this digest.
    """
    prior_sources = {
        source for t in previous
        for source in (t["from_source_sha"], t["to_source_sha"])
        if source not in (SOURCE, ORIGINAL_SOURCE)
    }
    history = [
        dict(row) for row in db.conn.execute(
            "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
            "evidence_dir,evidence_sha,quarantine_reason "
            "FROM tasks ORDER BY ticket"
        ) if row["source_sha"] in prior_sources
    ]
    counts = Counter(x["stage"] for x in history)
    need(bool(history) and set(counts).issubset({"VERIFIED", "QUARANTINED"})
         and counts["VERIFIED"] >= 154
         and counts["QUARANTINED"] >= 56,
         "HISTORICAL_NEGATIVE_OR_TERMINAL_DRIFT")
    negatives = sorted(x["ticket"] for x in history
                       if x["stage"] == "QUARANTINED")
    return history, counts, negatives


def _sealed_ticket(db):
    """Rebuild immutable identity from signed native admission and task row.

    Only stage/run metadata may evolve after the cold source transition.
    """
    task = db.conn.execute(
        "SELECT ticket,lane,source_sha,manifest_sha FROM tasks WHERE ticket=?",
        (TICKET,),
    ).fetchone()
    admission = db.conn.execute(
        "SELECT seq,kind,sha,payload FROM events WHERE seq=1854"
    ).fetchone()
    intake = db.conn.execute(
        "SELECT seq,kind,sha,payload FROM events WHERE seq=1855"
    ).fetchone()
    need(task is not None and admission is not None and intake is not None
         and admission["kind"] == "NATIVE_DEVELOPMENT_ADMITTED"
         and admission["sha"] == ADMISSION_SHA
         and intake["kind"] == "TASK_INTAKE"
         and intake["sha"] == INTAKE_SHA
         and task["ticket"] == TICKET and task["lane"] == "Yggdrasil"
         and task["source_sha"] == ORIGINAL_SOURCE,
         "IMMUTABLE_NATIVE_ISSUE_IDENTITY_CHANGED")
    a, i = json.loads(admission["payload"]), json.loads(intake["payload"])
    need(a.get("ticket") == TICKET
         and a.get("source_sha") == ORIGINAL_SOURCE
         and a.get("lane") == "Yggdrasil"
         and a.get("manifest_sha256") == task["manifest_sha"]
         and a.get("scientific_first_use") is False
         and i == {"ticket": TICKET, "lane": "Yggdrasil",
                   "manifest_sha": task["manifest_sha"]},
         "NATIVE_ADMISSION_OR_INTAKE_CHANGED")
    identity = {key: task[key] for key in
                ("ticket", "lane", "source_sha", "manifest_sha")}
    return digest(canonical(identity))


def _historical_pre_dispatch(db, seq):
    before = [
        json.loads(x["payload"]) for x in db.conn.execute(
            "SELECT payload FROM events WHERE kind='BEFORE_DISPATCH_INTENT' "
            "AND seq < ?", (seq,)
        )
    ]
    return any(x.get("ticket") == TICKET for x in before)


def verify_cold_event(db, row, doc, previous):
    """Replay the one original event1858 transition without current-stage pins.

    Valid after the ticket later starts or terminates; its admission, source,
    immutable ticket identity and unspent PRE-transition history remain fixed.
    """
    need(type(doc) is dict and set(doc) == FIELDS
         and doc.get("schema") == SCHEMA
         and doc.get("from_source_sha") == SOURCE
         and type(doc.get("to_source_sha")) is str
         and SHA40.fullmatch(doc["to_source_sha"]) is not None
         and doc["to_source_sha"] != SOURCE
         and doc["to_source_sha"] not in {
             x for t in previous
             for x in (t["from_source_sha"], t["to_source_sha"])
         }
         and not any(t.get("schema") == SCHEMA for t in previous)
         and type(previous) is list and bool(previous)
         and previous[-1].get("schema") == PREVIOUS
         and previous[-1].get("to_source_sha") == SOURCE
         and row["seq"] == ANCHOR_SEQ + 1
         and row["prior_sha"] == ANCHOR_SHA
         and doc.get("prior_event_head_sha256") == ANCHOR_SHA
         and doc.get("event1857_ancestor_sha256") == ANCHOR_SHA
         and doc.get("source_transition_purpose") == PURPOSE,
         "SOURCE_ANCESTRY_OR_SINGLE_USE_INVALID")
    prior_source = db.conn.execute(
        "SELECT seq,sha FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "AND seq < ? ORDER BY seq DESC LIMIT 1", (row["seq"],)
    ).fetchone()
    prior_activation = db.conn.execute(
        "SELECT seq,sha FROM events WHERE kind='NATIVE_DEVELOPMENT_ACTIVATED' "
        "AND seq < ? ORDER BY seq DESC LIMIT 1", (row["seq"],)
    ).fetchone()
    need(prior_source is not None
         and prior_source["seq"] == READY_SOURCE_TRANSITION_SEQ
         and prior_source["sha"] == READY_SOURCE_TRANSITION_SHA
         and prior_activation is not None
         and prior_activation["seq"] == NATIVE_ACTIVATION_SEQ
         and prior_activation["sha"] == NATIVE_ACTIVATION_SHA
         and doc.get("prior_source_transition_sha256") ==
             READY_SOURCE_TRANSITION_SHA
         and doc.get("prior_activation_sha256") == NATIVE_ACTIVATION_SHA,
         "ORIGINAL_V45_TRANSITION_OR_ACTIVATION_DRIFT")

    # Source replay checks every historical native activation; permitting a
    # future separately qualified activation never rewrites the V56 source.
    activation = db.conn.execute(
        "SELECT payload FROM events WHERE kind='NATIVE_DEVELOPMENT_ACTIVATED' "
        "ORDER BY seq DESC LIMIT 1"
    ).fetchone()
    last_source = json.loads(activation["payload"]).get("source_sha") \
        if activation is not None else None
    need(type(last_source) is str and SHA40.fullmatch(last_source) is not None
         and verify_native_activation(db, expected_source=last_source) is True,
         "HISTORICAL_NATIVE_ACTIVATION_DRIFT")
    need(_sealed_ticket(db) == doc.get("original_ready_identity_sha256")
         and doc.get("original_ready_ticket") == TICKET
         and doc.get("original_ready_lane") == "Yggdrasil"
         and doc.get("original_ready_source_sha") == ORIGINAL_SOURCE
         and doc.get("original_admission_sha256") == ADMISSION_SHA
         and doc.get("original_intake_sha256") == INTAKE_SHA
         and not _historical_pre_dispatch(db, row["seq"]),
         "ORIGINAL_READY_IDENTITY_OR_PRE_DISPATCH_SPENT")
    need(type(doc.get("owner_run_id")) is int
         and doc["owner_run_id"] > MIN_OWNER_RUN
         and all(type(doc.get(k)) is int and doc[k] > 0
                 for k in ("qualified_main_run_id", "rehearsal_run_id"))
         and doc["qualified_main_run_id"] != doc["rehearsal_run_id"]
         and all(type(doc.get(k)) is str
                 and SHA64.fullmatch(doc[k]) is not None
                 for k in ("backup_sqlite_sha256", "genenv_executable_sha256",
                           "generation_mechanism_sha256", "terminal_tasks_sha256"))
         and doc.get("native_development_approved") is True
         and doc.get("scientific_first_use") is False
         and type(doc.get("new_dispatches")) is int
         and doc["new_dispatches"] == 0
         and doc.get("new_controller") is False
         and doc.get("new_scheduler") is False
         and doc.get("new_queue") is False
         and type(doc.get("paid_api_calls")) is int
         and doc["paid_api_calls"] == 0,
         "QUALIFICATION_OR_AUTHORITY_SCOPE_INVALID")
    history, counts, negatives = frozen_old_terminal_rows(db, previous)
    need(type(doc.get("verified_historical_tasks")) is int
         and doc["verified_historical_tasks"] == counts["VERIFIED"]
         and type(doc.get("custodied_negative_tasks")) is int
         and doc["custodied_negative_tasks"] == counts["QUARANTINED"]
         and doc.get("custodied_negative_tickets") == negatives
         and set(previous[-1]["custodied_negative_tickets"]).issubset(negatives)
         and doc.get("terminal_tasks_sha256") == digest(canonical(history)),
         "HISTORICAL_TERMINAL_OR_NEGATIVE_CUSTODY_CHANGED")
    return True


def make_proof(db: Database, *, target: str, owner_run_id: int,
               qualified_main_run_id: int, rehearsal_run_id: int,
               backup_sqlite_sha256: str,
               genenv_executable_sha256: str,
               generation_mechanism_sha256: str) -> dict:
    """Build inert proposed proof only under original/detached owner mutex."""
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "EXCLUSIVE_OWNER_LOCK_REQUIRED")
    snapshot = original_pending_snapshot(db)
    previous = [
        json.loads(x["payload"]) for x in db.conn.execute(
            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
            " ORDER BY seq"
        )
    ]
    history, counts, negatives = frozen_old_terminal_rows(db, previous)
    proof = {
        "schema": SCHEMA, "from_source_sha": SOURCE, "to_source_sha": target,
        "prior_event_head_sha256": ANCHOR_SHA,
        "event1857_ancestor_sha256": ANCHOR_SHA,
        "prior_source_transition_sha256": READY_SOURCE_TRANSITION_SHA,
        "prior_activation_sha256": NATIVE_ACTIVATION_SHA,
        "owner_run_id": owner_run_id,
        "qualified_main_run_id": qualified_main_run_id,
        "rehearsal_run_id": rehearsal_run_id,
        "backup_sqlite_sha256": backup_sqlite_sha256,
        "genenv_executable_sha256": genenv_executable_sha256,
        "generation_mechanism_sha256": generation_mechanism_sha256,
        "terminal_tasks_sha256": digest(canonical(history)),
        "verified_historical_tasks": counts["VERIFIED"],
        "custodied_negative_tasks": counts["QUARANTINED"],
        "custodied_negative_tickets": negatives,
        "original_ready_ticket": TICKET,
        "original_ready_lane": "Yggdrasil",
        "original_ready_source_sha": ORIGINAL_SOURCE,
        "original_ready_identity_sha256": snapshot["ticket_identity_sha256"],
        "original_admission_sha256": ADMISSION_SHA,
        "original_intake_sha256": INTAKE_SHA,
        "source_transition_purpose": PURPOSE,
        "native_development_approved": True,
        "scientific_first_use": False, "new_dispatches": 0,
        "new_controller": False, "new_scheduler": False,
        "new_queue": False, "paid_api_calls": 0,
    }
    verify_cold_event(
        db, {"seq": ANCHOR_SEQ + 1, "prior_sha": ANCHOR_SHA},
        proof, previous,
    )
    return proof


def carried_v47_source(db, ticket):
    """Only the sealed V56 ticket can retain its admission SHA after V47.

    Callers must have independently invoked Database.verify. This is not a
    dispatch permit or free-standing transition verifier.
    """
    if ticket != TICKET:
        return None
    rows = [
        json.loads(x["payload"]) for x in db.conn.execute(
            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
        ) if json.loads(x["payload"]).get("schema") == SCHEMA
    ]
    if len(rows) != 1:
        return None
    doc = rows[0]
    try:
        sealed_identity = _sealed_ticket(db)
    except (V47TransitionDenied, ValueError, KeyError, TypeError):
        # An altered native admission cannot acquire carry authority.
        # Database.verify independently rejects the underlying corruption.
        return None
    if (set(doc) != FIELDS
            or doc.get("from_source_sha") != SOURCE
            or doc.get("to_source_sha") != db.meta()["source_sha"]
            or doc.get("original_ready_identity_sha256") != sealed_identity
            or doc.get("original_ready_ticket") != TICKET):
        return None
    return ORIGINAL_SOURCE
