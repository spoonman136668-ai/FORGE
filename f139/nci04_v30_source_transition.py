"""One original-owner maintenance transition carrying the never-claimed #1358.

The existing task, issue, candidate, worker release and signatures keep their
original identities. This neither readmits work nor transfers a spent attempt.
Only the separately guarded installer may commit this source transition.
"""
from __future__ import annotations
import json
import re
from f139.local_controller import Database, SingleOwner, g54_original_canonical
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation

FROM_V29 = "79fec85b83e90db0d4b26a2af868db2a8686826f"
SCHEMA = "forge.f139.source-transition.v25"
TICKET = "f139-nci04-i1358-79fec85b83e9-6952a94e"
HEAD = "5395668fae363cb48bc5c507e1501f4686a833a28d70e3fcf5d2e949ca22426b"
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "prior_event_head_sha256", "verified_historical_tasks",
    "custodied_negative_tasks", "custodied_negative_tickets",
    "terminal_tasks_sha256", "history_sha256", "v29_transition_sha256",
    "pending_native", "new_dispatches", "scientific_first_use",
    "v2_receipt_authorized",
})

class MaintenanceDenied(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise MaintenanceDenied("F139_V30_" + reason)

def _pending(db, boundary, *, unclaimed=False):
    task = db.conn.execute("SELECT * FROM tasks WHERE ticket=?", (TICKET,)).fetchone()
    need(task is not None and task["source_sha"] == FROM_V29
         and task["lane"] == "Yggdrasil", "EXACT_PENDING_TASK_REQUIRED")
    admission = [dict(r) for r in db.conn.execute(
        "SELECT seq,sha,payload FROM events WHERE kind='NATIVE_DEVELOPMENT_ADMITTED' ORDER BY seq")
        if json.loads(r["payload"]).get("ticket") == TICKET]
    need(len(admission) == 1 and admission[0]["seq"] == 375
         and admission[0]["seq"] < boundary, "ORIGINAL_ADMISSION_REQUIRED")
    event = json.loads(admission[0]["payload"])
    need(event["issue_number"] == 1358 and event["source_sha"] == FROM_V29
         and event["manifest_sha256"] == task["manifest_sha"], "PENDING_IDENTITY_DRIFT")
    operations = [dict(r) for r in db.conn.execute(
        "SELECT seq,kind,payload FROM events WHERE kind IN "
        "('BEFORE_DISPATCH_INTENT','DISPATCH_POST_RETURNED',"
        "'PROVIDER_VERIFIED_TERMINAL','ATTEMPT_QUARANTINED') ORDER BY seq")
        if json.loads(r["payload"]).get("ticket") == TICKET]
    need(not any(r["seq"] < boundary for r in operations), "SPENT_ATTEMPT_CANNOT_TRANSFER")
    if unclaimed:
        need(task["stage"] == "READY" and not operations
             and all(task[k] is None for k in
                     ("started_at", "completed_at", "run_id", "evidence_sha", "evidence_dir", "quarantine_reason")),
             "ONLY_NEVER_CLAIMED_READY_TASK")
    else:
        claims = [r for r in operations if r["kind"] == "BEFORE_DISPATCH_INTENT"]
        posts = [r for r in operations if r["kind"] == "DISPATCH_POST_RETURNED"]
        need(len(claims) <= 1 and len(posts) <= 1
             and (not posts or claims and claims[0]["seq"] < posts[0]["seq"])
             and ((task["stage"] == "READY" and not operations)
                  or (task["stage"] in ("START_RISK", "WAIT_PROVIDER", "VERIFIED", "QUARANTINED")
                      and len(claims) == 1)), "PENDING_STATE_OR_REPLAY_DRIFT")
    return {"ticket": TICKET, "source_sha": FROM_V29,
            "manifest_sha256": task["manifest_sha"],
            "admission_event_seq": admission[0]["seq"],
            "admission_event_sha256": admission[0]["sha"]}

def snapshot(db, row, previous):
    need(previous and previous[-1]["schema"] == "forge.f139.source-transition.v24"
         and previous[-1]["to_source_sha"] == FROM_V29, "GENUINE_V29_PREDECESSOR_REQUIRED")
    seal = db.conn.execute("SELECT sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
                           "AND seq<? ORDER BY seq DESC LIMIT 1", (row["seq"],)).fetchone()
    need(seal is not None and json.loads(seal["payload"]) == previous[-1], "V29_SEAL_DRIFT")
    sources = {s for tr in previous for s in (tr["from_source_sha"], tr["to_source_sha"])}
    tasks = [dict(t) for t in db.conn.execute(
        "SELECT ticket,stage,run_id,evidence_sha,evidence_dir,source_sha FROM tasks ORDER BY ticket")
        if t["source_sha"] in sources and t["ticket"] != TICKET]
    need(all(t["stage"] in ("VERIFIED", "QUARANTINED") for t in tasks), "OTHER_WORK_NOT_TERMINAL")
    from f139.nci04_negative_owner_store import TICKET as FIRST
    from f139.nci04_split_negative_owner_store import TICKET as SECOND
    from f139.nci04_g49_prepost_negative import TICKET as PREPOST
    expected = sorted({FIRST, SECOND, PREPOST, g54_original_canonical(db, through_seq=row["seq"])["ticket"]}
                      | set(db.verified_native_provider_failures(through_seq=row["seq"])))
    positives = [t for t in tasks if t["stage"] == "VERIFIED"]
    negatives = [t for t in tasks if t["stage"] == "QUARANTINED"]
    need(len(positives) >= 31 and len(negatives) >= 17
         and sorted(t["ticket"] for t in negatives) == expected, "ORIGINAL_NEGATIVE_CUSTODY_DRIFT")
    history = [dict(e) for e in db.conn.execute(
        "SELECT seq,kind,sha FROM events WHERE seq<? ORDER BY seq", (row["seq"],))]
    need(sum(e["kind"] == "FREE_REASONER_ATTEMPTED" for e in history) == 8,
         "SPENT_ORIGINAL_REQUEST_HISTORY_DRIFT")
    return {"verified_historical_tasks": len(positives), "custodied_negative_tasks": len(negatives),
            "custodied_negative_tickets": expected, "terminal_tasks_sha256": digest(canonical(tasks)),
            "history_sha256": digest(canonical(history)), "v29_transition_sha256": seal["sha"],
            "pending_native": _pending(db, row["seq"])}

def verify_cold_event(db, row, doc, previous):
    need(type(doc) is dict and set(doc) == FIELDS and doc["schema"] == SCHEMA
         and doc["from_source_sha"] == FROM_V29
         and type(doc["owner_event_id"]) is int and doc["owner_event_id"] > 0
         and row["seq"] == 377 and row["prior_sha"] == HEAD
         and doc["prior_event_head_sha256"] == row["prior_sha"]
         and type(doc["new_dispatches"]) is int and doc["new_dispatches"] == 0
         and doc["scientific_first_use"] is False and doc["v2_receipt_authorized"] is False
         and type(doc["to_source_sha"]) is str and re.fullmatch(r"[a-f0-9]{40}", doc["to_source_sha"])
         and doc["to_source_sha"] not in {s for tr in previous for s in (tr["from_source_sha"], tr["to_source_sha"])}
         and not any(tr["schema"] == SCHEMA for tr in previous), "EVENT_IDENTITY_REPLAY_OR_AUTHORITY")
    need(all(doc[k] == v for k, v in snapshot(db, row, previous).items()), "FROZEN_ORIGINAL_STATE_CHANGED")

def carried_source(db, ticket):
    """Return only the explicitly sealed original worker source; no DB writes.

    Callers must already have verified the complete database chain. Database's
    own verifier uses this only after it has validated every transition event.
    """
    if ticket != TICKET:
        return None
    rows = [dict(r) for r in db.conn.execute(
        "SELECT seq,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
        if json.loads(r["payload"]).get("schema") == SCHEMA]
    if len(rows) != 1:
        return None
    row = rows[0]
    event = json.loads(row["payload"])
    if event["to_source_sha"] != db.meta()["source_sha"]:
        return None
    need(event["pending_native"] == _pending(db, row["seq"]), "CARRIED_SOURCE_DRIFT")
    return FROM_V29

def build_proof(db, target, event_id):
    need(type(db) is Database and SingleOwner.held(db.filename.with_suffix(".lock")), "ORIGINAL_DATABASE_MUTEX_REQUIRED")
    db.verify()
    meta = db.meta().copy()
    need(meta["source_sha"] == FROM_V29 and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and meta["head_seq"] == 376 and meta["head_hash"] == HEAD
         and not db.actives() and verify_native_activation(db) is True, "AUTHENTIC_UNCLAIMED_V29_REQUIRED")
    _pending(db, 377, unclaimed=True)
    previous = [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")]
    row = {"seq": 377, "prior_sha": meta["head_hash"]}
    doc = {"schema": SCHEMA, "from_source_sha": FROM_V29, "to_source_sha": target,
           "owner_event_id": event_id, "prior_event_head_sha256": meta["head_hash"],
           **snapshot(db, row, previous), "new_dispatches": 0,
           "scientific_first_use": False, "v2_receipt_authorized": False}
    verify_cold_event(db, row, doc, previous)
    return doc

def commit_transition(db, proof, *, owner_witness):
    need(type(db) is Database and SingleOwner.held(db.filename.with_suffix(".lock"))
         and callable(owner_witness) and owner_witness() is True, "ORIGINAL_MUTEX_AND_DISABLED_OWNER_REQUIRED")
    need(type(proof) is dict and set(proof) == FIELDS, "EXACT_PROOF_REQUIRED")
    with db.transaction():
        expected = build_proof(db, proof["to_source_sha"], proof["owner_event_id"])
        need(canonical(proof) == canonical(expected), "APPROVAL_OR_LEDGER_DRIFT")
        need(owner_witness() is True, "OWNER_REVOKED")
        before = db.meta().copy()
        db.conn.execute("UPDATE meta SET source_sha=? WHERE id=1", (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        db.verify()
        need(owner_witness() is True and db.meta()["head_seq"] == before["head_seq"] + 1, "POST_TRANSITION_OWNER_OR_HEAD_DRIFT")
    return {"source_sha": db.meta()["source_sha"], "event_seq": db.meta()["head_seq"],
            "event_head_sha256": db.meta()["head_hash"], "scientific_first_use": False,
            "new_controller": False, "paid_api_calls": 0}
