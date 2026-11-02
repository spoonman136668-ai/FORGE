"""One-time V30 maintenance transition; preserves all spent original history.

This module grants no release permission. The existing original-owner task
must be disabled and its canonical database held by SingleOwner separately.
"""
from __future__ import annotations
import json
import re
from f139.local_controller import Database, SingleOwner, g54_original_canonical
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation

FROM_V30 = "b419300f61a86d387bc4b630a9850eced8b8bb75"
SCHEMA = "forge.f139.source-transition.v26"
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "prior_event_head_sha256", "verified_historical_tasks",
    "custodied_negative_tasks", "custodied_negative_tickets",
    "terminal_tasks_sha256", "history_sha256", "v30_transition_sha256",
    "original_v2_custody_sha256",
    "new_dispatches", "scientific_first_use", "v2_receipt_authorized",
})

class MaintenanceDenied(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise MaintenanceDenied("F139_V31_" + reason)

TICKET = "f139-nci04-i1358-79fec85b83e9-6952a94e"
RUN = 41419909421
OLD_WORKER = "79fec85b83e90db0d4b26a2af868db2a8686826f"
WAIT_HEAD = "d72aafc622332266f61fba3c6261a182adb4d780352c1ca6e7b5ed492739c10f"

def validate_waiting(db):
    db.verify()
    meta=db.meta()
    active=db.actives()
    need(meta["source_sha"]==FROM_V30 and meta["head_seq"]==380
         and meta["head_hash"]==WAIT_HEAD and meta["enabled"]==1
         and meta["legacy_suspended"]==1 and db.ready() is None
         and len(active)==1 and active[0]["ticket"]==TICKET
         and active[0]["stage"]=="WAIT_PROVIDER" and active[0]["source_sha"]==OLD_WORKER
         and active[0]["run_id"] is None and verify_native_activation(db),
         "EXACT_ONCE_POSTED_ORIGINAL_REQUIRED")
    return active[0]["started_at"]

def terminal_custody(db):
    rows=[dict(r) for r in db.conn.execute(
        "SELECT seq,sha,payload FROM events WHERE kind='NATIVE_V_TWO_PROVIDER_CUSTODY' ORDER BY seq")
        if json.loads(r["payload"]).get("ticket")==TICKET]
    need(len(rows)==1 and rows[0]["seq"]==382, "EXACT_ORIGINAL_V2_CUSTODY_REQUIRED")
    doc=json.loads(rows[0]["payload"])
    task=db.conn.execute("SELECT stage,source_sha,run_id FROM tasks WHERE ticket=?",(TICKET,)).fetchone()
    old=db.conn.execute("SELECT sha FROM events WHERE seq=380").fetchone()
    need(old is not None and old["sha"]==WAIT_HEAD and doc["outcome"]=="VERIFIED"
         and doc["run_id"]==RUN and doc["source_sha"]==OLD_WORKER
         and doc["original_admission_event_seq"]==375
         and doc["original_claim_event_seq"]==379
         and task is not None and task["stage"]=="VERIFIED"
         and task["source_sha"]==OLD_WORKER and task["run_id"]==RUN,
         "AUTHENTIC_ORIGINAL_TERMINAL_REQUIRED")
    return rows[0]

def snapshot(db, row, previous):
    need(previous and previous[-1]["schema"] == "forge.f139.source-transition.v25"
         and previous[-1]["to_source_sha"] == FROM_V30,
         "GENUINE_V30_PREDECESSOR_REQUIRED")
    seal = db.conn.execute(
        "SELECT sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "AND seq<? ORDER BY seq DESC LIMIT 1", (row["seq"],)).fetchone()
    need(seal is not None and json.loads(seal["payload"]) == previous[-1],
         "V30_SEAL_DRIFT")
    sources = {s for tr in previous for s in (tr["from_source_sha"], tr["to_source_sha"])}
    tasks = [dict(t) for t in db.conn.execute(
        "SELECT ticket,stage,run_id,evidence_sha,evidence_dir,source_sha "
        "FROM tasks ORDER BY ticket") if t["source_sha"] in sources]
    need(all(t["stage"] in ("VERIFIED", "QUARANTINED") for t in tasks),
         "HISTORICAL_TASK_NOT_TERMINAL")
    from f139.nci04_negative_owner_store import TICKET as FIRST
    from f139.nci04_split_negative_owner_store import TICKET as SECOND
    from f139.nci04_g49_prepost_negative import TICKET as PREPOST
    failures = db.verified_native_provider_failures(through_seq=row["seq"])
    expected = sorted({FIRST, SECOND, PREPOST,
                       g54_original_canonical(db, through_seq=row["seq"])["ticket"]}
                      | set(failures))
    positives = [t for t in tasks if t["stage"] == "VERIFIED"]
    negatives = [t for t in tasks if t["stage"] == "QUARANTINED"]
    need(len(positives) >= 32 and len(negatives) >= 15
         and sorted(t["ticket"] for t in negatives) == expected,
         "ORIGINAL_NEGATIVE_CUSTODY_DRIFT")
    history = [dict(e) for e in db.conn.execute(
        "SELECT seq,kind,sha FROM events WHERE seq<? ORDER BY seq", (row["seq"],))]
    need(sum(e["kind"] == "FREE_REASONER_ATTEMPTED" for e in history) == 8,
         "SPENT_ORIGINAL_REQUEST_HISTORY_DRIFT")
    custody = terminal_custody(db)
    return {
        "verified_historical_tasks": len(positives),
        "custodied_negative_tasks": len(negatives),
        "custodied_negative_tickets": expected,
        "terminal_tasks_sha256": digest(canonical(tasks)),
        "history_sha256": digest(canonical(history)),
        "v30_transition_sha256": seal["sha"],
        "original_v2_custody_sha256": custody["sha"],
    }

def verify_cold_event(db, row, doc, previous):
    need(type(doc) is dict and set(doc) == FIELDS and doc["schema"] == SCHEMA
         and row["seq"] == 383
         and doc["from_source_sha"] == FROM_V30
         and type(doc["owner_event_id"]) is int and doc["owner_event_id"] > 0
         and doc["prior_event_head_sha256"] == row["prior_sha"]
         and doc["original_v2_custody_sha256"] == row["prior_sha"]
         and type(doc["new_dispatches"]) is int and doc["new_dispatches"] == 0
         and doc["scientific_first_use"] is False
         and doc["v2_receipt_authorized"] is False
         and type(doc["to_source_sha"]) is str
         and re.fullmatch(r"[a-f0-9]{40}", doc["to_source_sha"]) is not None
         and doc["to_source_sha"] not in {
             s for tr in previous for s in (tr["from_source_sha"], tr["to_source_sha"])}
         and not any(tr["schema"] == SCHEMA for tr in previous),
         "EVENT_IDENTITY_REPLAY_OR_AUTHORITY")
    need(all(doc[k] == v for k, v in snapshot(db, row, previous).items()),
         "FROZEN_ORIGINAL_STATE_CHANGED")

def build_proof(db, target, event_id):
    need(type(db) is Database and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_DATABASE_MUTEX_REQUIRED")
    db.verify()
    meta = db.meta().copy()
    need(meta["source_sha"] == FROM_V30 and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1 and meta["head_seq"] == 382
         and db.ready() is None and not db.actives()
         and verify_native_activation(db) is True,
         "AUTHENTIC_IDLE_V30_REQUIRED")
    previous = [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")]
    row = {"seq": meta["head_seq"] + 1, "prior_sha": meta["head_hash"]}
    doc = {
        "schema": SCHEMA, "from_source_sha": FROM_V30, "to_source_sha": target,
        "owner_event_id": event_id, "prior_event_head_sha256": meta["head_hash"],
        **snapshot(db, row, previous), "new_dispatches": 0,
        "scientific_first_use": False, "v2_receipt_authorized": False,
    }
    verify_cold_event(db, row, doc, previous)
    return doc

def commit_transition(db, proof, *, owner_witness):
    need(type(db) is Database and SingleOwner.held(db.filename.with_suffix(".lock"))
         and callable(owner_witness) and owner_witness() is True,
         "ORIGINAL_MUTEX_AND_DISABLED_OWNER_REQUIRED")
    need(type(proof) is dict and set(proof) == FIELDS, "EXACT_PROOF_REQUIRED")
    with db.transaction():
        expected = build_proof(db, proof["to_source_sha"], proof["owner_event_id"])
        need(canonical(proof) == canonical(expected), "APPROVAL_OR_LEDGER_DRIFT")
        need(owner_witness() is True, "OWNER_REVOKED")
        before = db.meta().copy()
        db.conn.execute("UPDATE meta SET source_sha=? WHERE id=1", (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
        need(owner_witness() is True and db.meta()["head_seq"] == before["head_seq"] + 1,
             "POST_TRANSITION_OWNER_OR_HEAD_DRIFT")
    return {"source_sha": db.meta()["source_sha"], "event_seq": db.meta()["head_seq"],
            "event_head_sha256": db.meta()["head_hash"], "scientific_first_use": False,
            "new_controller": False, "paid_api_calls": 0}
