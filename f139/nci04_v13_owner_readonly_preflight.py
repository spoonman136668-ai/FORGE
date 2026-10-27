"""Read-only V13 source preflight for the *original* F139 owner.

Produces no release authorization, ledger write, controller tick or model call.
The separate original-owner cutover must authenticate protected main, the exact
release ref, single owner, running task, quiescence and backup before mutation.
"""
from __future__ import annotations

import json
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_negative_owner_store import verify_original_negative_custody
from f139.nci04_split_negative_owner_store import verify_second_negative_custody
from f139.nci04_g49_prepost_negative import verify_g49_custody
from f139.nci04_g54_ambiguous_start_custody import verified_g54_ambiguous_start

FROM_V12 = "5ba084491ebea16f9c8b21c6deedba791a86fb1d"
SCHEMA = "forge.f139.nci04.v13.original-owner-readonly-preflight.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "event_seq", "event_head_sha256", "v12_terminal_event_sha256",
    "terminal_tasks_sha256", "model_history_sha256", "verified_tasks",
    "quarantined_tasks", "advisory_only", "scientific_first_use",
    "production_dispatch_authorized", "new_controller", "new_scheduler",
    "new_queue", "paid_api_calls",
})
KINDS = (
    "G3_DRAFT_ATTEMPTED", "G3_DRAFT_AUTHENTICATED",
    "MODEL_DRAFT_ATTEMPTED", "MODEL_DRAFT_AUTHENTICATED",
    "FREE_REASONER_ATTEMPTED",
)


class V13PreflightDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise V13PreflightDenied("F139_V13_" + reason)


def _original_state(db) -> dict:
    from f139.local_controller import Database

    need(type(db) is Database, "ORIGINAL_DATABASE_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == FROM_V12 and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1
         and type(meta["head_seq"]) is int and meta["head_seq"] >= 261
         and db.ready() is None and not db.actives()
         and verify_native_activation(db), "V12_OWNER_NOT_IDLE_OR_AUTHENTICATED")
    transitions = list(db.conn.execute(
        "SELECT sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "ORDER BY seq"))
    docs = [json.loads(row["payload"]) for row in transitions]
    v12 = [i for i, doc in enumerate(docs)
           if doc.get("schema") == "forge.f139.source-transition.v12"]
    need(len(v12) == 1 and v12[0] == len(docs) - 1
         and docs[-1]["to_source_sha"] == FROM_V12
         and docs[-1].get("v2_receipt_authorized") is False,
         "TERMINAL_V12_SOURCE_SEAL_CHANGED")
    g54 = verified_g54_ambiguous_start(db)
    need(bool(g54) and verify_original_negative_custody(db)
         and verify_second_negative_custody(db)
         and verify_g49_custody(db), "NEGATIVE_HISTORY_UNVERIFIED")
    rows = [dict(row) for row in db.conn.execute(
        "SELECT ticket,stage,run_id,evidence_sha,source_sha "
        "FROM tasks ORDER BY ticket")]
    need(all(row["stage"] in ("VERIFIED", "QUARANTINED") for row in rows),
         "ACTIVE_OR_UNKNOWN_TASK_STAGE")
    verified = [row for row in rows if row["stage"] == "VERIFIED"]
    negatives = [row for row in rows if row["stage"] == "QUARANTINED"]
    need(len(verified) >= 22 and len(negatives) >= 15
         and any(row["ticket"] == g54["ticket"] for row in negatives),
         "FROZEN_NEGATIVE_OR_POSITIVE_SET_INVALID")
    history = [dict(row) for row in db.conn.execute(
        "SELECT kind,sha FROM events "
        "WHERE kind IN ('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED',"
        "'MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED',"
        "'FREE_REASONER_ATTEMPTED') ORDER BY seq")]
    counts = {kind: sum(row["kind"] == kind for row in history) for kind in KINDS}
    need(all(counts[kind] == 1 for kind in KINDS[:4])
         and counts["FREE_REASONER_ATTEMPTED"] == 0,
         "MODEL_HISTORY_UNRESOLVED_OR_ALREADY_CONSUMED")
    historical = {sha for doc in docs
                  for sha in (doc["from_source_sha"], doc["to_source_sha"])}
    return {
        "meta": meta,
        "v12_terminal_event_sha256": transitions[-1]["sha"],
        "terminal_tasks_sha256": digest(canonical(rows)),
        "model_history_sha256": digest(canonical(history)),
        "verified_tasks": len(verified),
        "quarantined_tasks": len(negatives),
        "historical_sources": historical,
    }


def build_v13_readonly_preflight(db, target_sha: str, owner_event_id: int) -> dict:
    state = _original_state(db)
    need(type(target_sha) is str and SHA40.fullmatch(target_sha)
         and target_sha not in state["historical_sources"],
         "TARGET_INVALID_OR_ALREADY_CONSUMED")
    need(type(owner_event_id) is int and owner_event_id > 0,
         "OWNER_EVENT_ID_REQUIRED")
    meta = state["meta"]
    proof = {
        "schema": SCHEMA, "from_source_sha": FROM_V12,
        "to_source_sha": target_sha, "owner_event_id": owner_event_id,
        "event_seq": meta["head_seq"], "event_head_sha256": meta["head_hash"],
        "v12_terminal_event_sha256": state["v12_terminal_event_sha256"],
        "terminal_tasks_sha256": state["terminal_tasks_sha256"],
        "model_history_sha256": state["model_history_sha256"],
        "verified_tasks": state["verified_tasks"],
        "quarantined_tasks": state["quarantined_tasks"],
        "advisory_only": True, "scientific_first_use": False,
        "production_dispatch_authorized": False, "new_controller": False,
        "new_scheduler": False, "new_queue": False, "paid_api_calls": 0,
    }
    verify_v13_readonly_preflight(db, proof)
    return proof


def verify_v13_readonly_preflight(db, proof: dict) -> dict:
    from f139.local_controller import Database

    need(type(db) is Database, "ORIGINAL_DATABASE_REQUIRED")
    need(type(proof) is dict and set(proof) == FIELDS
         and json.loads(canonical(proof)) == proof,
         "FIELDS_NOT_CANONICAL")
    need(proof["schema"] == SCHEMA and proof["from_source_sha"] == FROM_V12
         and type(proof["to_source_sha"]) is str
         and SHA40.fullmatch(proof["to_source_sha"])
         and type(proof["owner_event_id"]) is int and proof["owner_event_id"] > 0
         and type(proof["event_seq"]) is int and proof["event_seq"] >= 261
         and type(proof["verified_tasks"]) is int and proof["verified_tasks"] >= 22
         and type(proof["quarantined_tasks"]) is int
         and proof["quarantined_tasks"] >= 15,
         "OWNER_IDENTITY_OR_TASK_COUNTS_INVALID")
    for field in ("event_head_sha256", "v12_terminal_event_sha256",
                  "terminal_tasks_sha256", "model_history_sha256"):
        need(type(proof[field]) is str and SHA64.fullmatch(proof[field]),
             "BAD_HASH_" + field.upper())
    need(proof["advisory_only"] is True
         and proof["scientific_first_use"] is False
         and proof["production_dispatch_authorized"] is False
         and proof["new_controller"] is False
         and proof["new_scheduler"] is False
         and proof["new_queue"] is False
         and type(proof["paid_api_calls"]) is int
         and proof["paid_api_calls"] == 0, "AUTHORITY_EXPANSION_DENIED")
    state = _original_state(db)
    need(proof["to_source_sha"] not in state["historical_sources"],
         "TARGET_ALREADY_CONSUMED")
    m = state["meta"]
    need(proof["event_seq"] == m["head_seq"]
         and proof["event_head_sha256"] == m["head_hash"],
         "OWNER_HEAD_CHANGED")
    for field in ("v12_terminal_event_sha256", "terminal_tasks_sha256",
                  "model_history_sha256", "verified_tasks",
                  "quarantined_tasks"):
        need(proof[field] == state[field], "SOURCE_CUSTODY_DRIFT_" + field.upper())
    return {
        "read_only": True, "source_from": FROM_V12,
        "candidate_to": proof["to_source_sha"],
        "event_head_sha256": m["head_hash"],
        "scientific_first_use": False,
        "runtime_cutover_authorized": False,
    }
