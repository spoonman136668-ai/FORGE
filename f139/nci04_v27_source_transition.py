"""One-time V26 maintenance transition; preserves all spent original history.

This module grants no release permission. The existing original-owner task
must be disabled and its canonical database held by SingleOwner separately.
"""
from __future__ import annotations
import json
import re
from f139.local_controller import Database, SingleOwner, g54_original_canonical
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation

FROM_V26 = "49c7b15343bea3c201fb52b498d8c0f397384afe"
SCHEMA = "forge.f139.source-transition.v22"
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "prior_event_head_sha256", "verified_historical_tasks",
    "custodied_negative_tasks", "custodied_negative_tickets",
    "terminal_tasks_sha256", "history_sha256", "v26_transition_sha256",
    "new_dispatches", "scientific_first_use", "v2_receipt_authorized",
})

class MaintenanceDenied(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise MaintenanceDenied("F139_V27_" + reason)

def snapshot(db, row, previous):
    need(previous and previous[-1]["schema"] == "forge.f139.source-transition.v21"
         and previous[-1]["to_source_sha"] == FROM_V26,
         "GENUINE_V26_PREDECESSOR_REQUIRED")
    seal = db.conn.execute(
        "SELECT sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "AND seq<? ORDER BY seq DESC LIMIT 1", (row["seq"],)).fetchone()
    need(seal is not None and json.loads(seal["payload"]) == previous[-1],
         "V26_SEAL_DRIFT")
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
    need(len(positives) >= 24 and len(negatives) >= 15
         and sorted(t["ticket"] for t in negatives) == expected,
         "ORIGINAL_NEGATIVE_CUSTODY_DRIFT")
    history = [dict(e) for e in db.conn.execute(
        "SELECT seq,kind,sha FROM events WHERE seq<? ORDER BY seq", (row["seq"],))]
    need(sum(e["kind"] == "FREE_REASONER_ATTEMPTED" for e in history) == 8,
         "SPENT_ORIGINAL_REQUEST_HISTORY_DRIFT")
    return {
        "verified_historical_tasks": len(positives),
        "custodied_negative_tasks": len(negatives),
        "custodied_negative_tickets": expected,
        "terminal_tasks_sha256": digest(canonical(tasks)),
        "history_sha256": digest(canonical(history)),
        "v26_transition_sha256": seal["sha"],
    }

def verify_cold_event(db, row, doc, previous):
    need(type(doc) is dict and set(doc) == FIELDS and doc["schema"] == SCHEMA
         and doc["from_source_sha"] == FROM_V26
         and type(doc["owner_event_id"]) is int and doc["owner_event_id"] > 0
         and doc["prior_event_head_sha256"] == row["prior_sha"]
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
    need(meta["source_sha"] == FROM_V26 and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1 and meta["head_seq"] >= 350
         and db.ready() is None and not db.actives()
         and verify_native_activation(db) is True,
         "AUTHENTIC_IDLE_V26_REQUIRED")
    previous = [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")]
    row = {"seq": meta["head_seq"] + 1, "prior_sha": meta["head_hash"]}
    doc = {
        "schema": SCHEMA, "from_source_sha": FROM_V26, "to_source_sha": target,
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
