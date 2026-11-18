"""F139 V55 source-transition v45 COLD replay verifier and proof constructor.

Strictly development-only source authentication. This module has NO SQLite
writes, no owner task changes, no release runner and no deployment entrypoint.
A future ORIGINAL owner workflow must independently authenticate exact source
and CI, owner SID/task, fresh backup, detached commit/rollback and release
authority; passing this verifier grants none of those permissions.
"""
from __future__ import annotations

from collections import Counter
import json
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_v54_original_owner_readonly_preflight import SHA40
SOURCE = "d57245af9005a5b9f9e553ab9093bce94a64dcd7"
ANCHOR_SEQ = 1849
ANCHOR_SHA = "81c90038088bb22f11fa848f12bca963734edf6fc9bd720948c96af77ac1fb35"

SCHEMA = "forge.f139.source-transition.v45"
PREVIOUS = "forge.f139.source-transition.v44"
PURPOSE = "repair-original-f139-pr-history-transport-development-only"
MIN_OWNER_RUN = 44273248969
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha",
    "prior_event_head_sha256", "event1849_ancestor_sha256",
    "prior_source_transition_sha256", "prior_activation_sha256",
    "owner_run_id", "qualified_main_run_id", "rehearsal_run_id",
    "backup_sqlite_sha256", "terminal_tasks_sha256",
    "genenv_executable_sha256", "generation_mechanism_sha256",
    "custodied_negative_tickets", "verified_historical_tasks",
    "custodied_negative_tasks", "source_transition_purpose",
    "native_development_approved", "scientific_first_use",
    "new_dispatches", "new_controller", "new_scheduler", "new_queue",
    "paid_api_calls",
})


class ForwardTransitionDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise ForwardTransitionDenied("F139_V55_" + code)


def terminal_rows(db, previous):
    """Freeze only PRE-transition sources; future new-source work is excluded.

    Later owner ticks may add tasks bound to the new release. Those additions
    must not retroactively change the sealed earlier terminal-task digest.
    """
    sources = {s for t in previous
               for s in (t["from_source_sha"], t["to_source_sha"])}
    sources.add(SOURCE)
    history = [
        dict(row) for row in db.conn.execute(
            "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
            "evidence_dir,evidence_sha,quarantine_reason "
            "FROM tasks ORDER BY ticket")
        if row["source_sha"] in sources
    ]
    states = Counter(row["stage"] for row in history)
    need(bool(history)
         and set(states).issubset({"VERIFIED", "QUARANTINED"})
         and states["VERIFIED"] >= 154
         and states["QUARANTINED"] >= 56,
         "HISTORICAL_TERMINAL_TASKS_UNQUALIFIED")
    negatives = sorted(t["ticket"] for t in history
                       if t["stage"] == "QUARANTINED")
    return history, states, negatives


def witness(db, row, previous):
    need(type(previous) is list and bool(previous)
         and previous[-1].get("schema") == PREVIOUS
         and previous[-1].get("to_source_sha") == SOURCE
         and type(row["seq"]) is int and row["seq"] > ANCHOR_SEQ
         and type(row["prior_sha"]) is str
         and SHA64.fullmatch(row["prior_sha"]) is not None,
         "PREDECESSOR_LINEAGE_INVALID")
    prior = db.conn.execute(
        "SELECT seq,sha FROM events WHERE seq=?", (row["seq"] - 1,)
    ).fetchone()
    anchor = db.conn.execute(
        "SELECT seq,kind,sha FROM events WHERE seq=?", (ANCHOR_SEQ,)
    ).fetchone()
    transition = db.conn.execute(
        "SELECT seq,sha,payload FROM events "
        "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq < ? "
        "ORDER BY seq DESC LIMIT 1", (row["seq"],)
    ).fetchone()
    activation = db.conn.execute(
        "SELECT seq,sha,payload FROM events "
        "WHERE kind='NATIVE_DEVELOPMENT_ACTIVATED' AND seq < ? "
        "ORDER BY seq DESC LIMIT 1", (row["seq"],)
    ).fetchone()
    # Cold replay may run after a separately authorized later activation.
    # Verify ALL genuine activation events against the actual last activation,
    # but continue to bind this v45 proof to the original pre-v45 event below.
    # Assuming SOURCE is always the last activation would fail legitimate
    # post-transition cold reads and strand the one original owner.
    last_activation = db.conn.execute(
        "SELECT payload FROM events WHERE kind='NATIVE_DEVELOPMENT_ACTIVATED'"
        " ORDER BY seq DESC LIMIT 1"
    ).fetchone()
    last_source = (json.loads(last_activation["payload"]).get("source_sha")
                   if last_activation is not None else None)
    need(type(last_source) is str
         and SHA40.fullmatch(last_source) is not None
         and verify_native_activation(db, expected_source=last_source) is True,
         "ACTIVATION_HISTORY_INVALID")
    need(prior is not None and prior["sha"] == row["prior_sha"]
         and anchor is not None
         and anchor["kind"] == "NATIVE_DEVELOPMENT_ACTIVATED"
         and anchor["sha"] == ANCHOR_SHA
         and transition is not None
         and transition["seq"] == ANCHOR_SEQ - 1
         and json.loads(transition["payload"]) == previous[-1]
         and activation is not None
         and json.loads(activation["payload"]).get("source_sha") == SOURCE
         and activation["seq"] == ANCHOR_SEQ
         and json.loads(activation["payload"]).get("schema")
             == "forge.f139.nci04.owner-native-activation.v1",
         "ORIGINAL_EVENT1847_OR_ACTIVATION_DRIFT")
    return transition, activation


def verify_cold_event(db, row, doc, previous):
    """Replay from the unchanged historic chain on every subsequent read."""
    need(type(doc) is dict and set(doc) == FIELDS
         and doc.get("schema") == SCHEMA
         and doc.get("from_source_sha") == SOURCE
         and type(doc.get("to_source_sha")) is str
         and SHA40.fullmatch(doc["to_source_sha"]) is not None
         and doc["to_source_sha"] != SOURCE
         and doc["to_source_sha"] not in {
             s for t in previous
             for s in (t["from_source_sha"], t["to_source_sha"])
         }
         and not any(t.get("schema") == SCHEMA for t in previous)
         and doc.get("event1849_ancestor_sha256") == ANCHOR_SHA
         and doc.get("source_transition_purpose") == PURPOSE,
         "V45_IDENTITY_OR_SINGLE_USE_INVALID")
    prev, activated = witness(db, row, previous)
    need(doc.get("prior_event_head_sha256") == row["prior_sha"]
         and doc.get("prior_source_transition_sha256") == prev["sha"]
         and doc.get("prior_activation_sha256") == activated["sha"]
         and type(doc.get("owner_run_id")) is int
         and doc["owner_run_id"] > MIN_OWNER_RUN
         and all(type(doc.get(k)) is int and doc[k] > 0
                 for k in ("qualified_main_run_id", "rehearsal_run_id"))
         and doc["qualified_main_run_id"] != doc["rehearsal_run_id"]
         and all(type(doc.get(k)) is str
                 and SHA64.fullmatch(doc[k]) is not None
                 for k in ("backup_sqlite_sha256", "terminal_tasks_sha256",
                           "genenv_executable_sha256", "generation_mechanism_sha256"))
         and doc.get("native_development_approved") is True
         and doc.get("scientific_first_use") is False
         and type(doc.get("new_dispatches")) is int
         and doc["new_dispatches"] == 0
         and doc.get("new_controller") is False
         and doc.get("new_scheduler") is False
         and doc.get("new_queue") is False
         and type(doc.get("paid_api_calls")) is int
         and doc["paid_api_calls"] == 0,
         "V45_QUALIFICATION_OR_SCOPE_INVALID")
    tasks, counts, negatives = terminal_rows(db, previous)
    need(type(doc.get("verified_historical_tasks")) is int
         and doc["verified_historical_tasks"] == counts["VERIFIED"]
         and type(doc.get("custodied_negative_tasks")) is int
         and doc["custodied_negative_tasks"] == counts["QUARANTINED"]
         and doc.get("custodied_negative_tickets") == negatives
         and set(previous[-1]["custodied_negative_tickets"]).issubset(negatives)
         and digest(canonical(tasks)) == doc["terminal_tasks_sha256"],
         "V45_HISTORICAL_TERMINAL_CUSTODY_DRIFT")
    return True


def make_proof(db: Database, *, target: str, owner_run_id: int,
               qualified_main_run_id: int, rehearsal_run_id: int,
               backup_sqlite_sha256: str,
               genenv_executable_sha256: str,
               generation_mechanism_sha256: str) -> dict:
    """Construct inert proof while an authenticated original mutex is held.

    This function NEVER writes to the database. It is NOT permission to
    quiesce or retarget the real owner. All inputs remain non-authorizing
    unless an independent existing-owner release workflow validates them.
    """
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "SINGLE_ORIGINAL_OWNER_MUTEX_REQUIRED")
    db.verify()
    m = db.meta()
    need(m["source_sha"] == SOURCE
         and m["enabled"] == 1 and m["legacy_suspended"] == 1
         and m["head_seq"] >= ANCHOR_SEQ
         and db.ready() is None and not db.actives(),
         "ORIGINAL_OWNER_SOURCE_OR_PENDING_DRIFT")
    prev = [
        json.loads(r["payload"]) for r in db.conn.execute(
            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
            " ORDER BY seq")]
    transition = db.conn.execute(
        "SELECT sha FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
        " ORDER BY seq DESC LIMIT 1").fetchone()
    activation = db.conn.execute(
        "SELECT sha FROM events WHERE kind='NATIVE_DEVELOPMENT_ACTIVATED'"
        " ORDER BY seq DESC LIMIT 1").fetchone()
    need(transition is not None and activation is not None,
         "NATIVE_SOURCE_OR_ACTIVATION_MISSING")
    tasks, counts, negatives = terminal_rows(db, prev)
    doc = {
        "schema": SCHEMA,
        "from_source_sha": SOURCE, "to_source_sha": target,
        "prior_event_head_sha256": m["head_hash"],
        "event1849_ancestor_sha256": ANCHOR_SHA,
        "prior_source_transition_sha256": transition["sha"],
        "prior_activation_sha256": activation["sha"],
        "owner_run_id": owner_run_id,
        "qualified_main_run_id": qualified_main_run_id,
        "rehearsal_run_id": rehearsal_run_id,
        "backup_sqlite_sha256": backup_sqlite_sha256,
        "genenv_executable_sha256": genenv_executable_sha256,
        "generation_mechanism_sha256": generation_mechanism_sha256,
        "terminal_tasks_sha256": digest(canonical(tasks)),
        "verified_historical_tasks": counts["VERIFIED"],
        "custodied_negative_tasks": counts["QUARANTINED"],
        "custodied_negative_tickets": negatives,
        "source_transition_purpose": PURPOSE,
        "native_development_approved": True,
        "scientific_first_use": False, "new_dispatches": 0,
        "new_controller": False, "new_scheduler": False,
        "new_queue": False, "paid_api_calls": 0,
    }
    verify_cold_event(db,
                      {"seq": m["head_seq"] + 1,
                       "prior_sha": m["head_hash"]}, doc, prev)
    return doc
