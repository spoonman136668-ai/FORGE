"""Fail-closed V20 -> renewable-owner RELEASE PREFLIGHT ONLY, original SQLite.

There is no new release permission, transition event, Windows task action,
model credential access, provider POST or scheduled tick in this module. A
separate guarded protected-source successor must accept and reverify this
exact frozen V20 evidence under the original SingleOwner mutex.
"""
from __future__ import annotations

import json
import re

from f139.local_controller import Database, SingleOwner, v17_original_model_history_valid
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_negative_owner_store import verify_original_negative_custody
from f139.nci04_split_negative_owner_store import verify_second_negative_custody
from f139.nci04_g49_prepost_negative import verify_g49_custody
from f139.nci04_g54_ambiguous_start_custody import verified_g54_ambiguous_start

FROM_V20 = "db7a1d0f324478183c54df417624053448d6b08b"
SCHEMA = "forge.f139.nci04.v24.v20-renewable-original-readonly-preflight.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
MODEL_KINDS = (
    "G3_DRAFT_ATTEMPTED", "G3_DRAFT_AUTHENTICATED",
    "MODEL_DRAFT_ATTEMPTED", "MODEL_DRAFT_AUTHENTICATED",
    "FREE_REASONER_ATTEMPTED",
)
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "event_seq", "event_head_sha256", "v20_terminal_event_sha256",
    "terminal_tasks_sha256", "model_history_sha256",
    "last_original_free_event_seq", "last_original_free_event_sha256",
    "verified_tasks", "quarantined_tasks", "legacy_free_attempts_spent",
    "advisory_only", "scientific_first_use", "production_dispatch_authorized",
    "new_controller", "new_scheduler", "new_queue", "paid_api_calls",
})


class V24ReadOnlyDenied(ValueError):
    pass


def need(ok: bool, reason: str):
    if not ok:
        raise V24ReadOnlyDenied("F139_V24_" + reason)


def original_v20_state(db: Database) -> dict:
    """Read the actual SHA-chained original, never synthetic/foreign history."""
    need(type(db) is Database, "ORIGINAL_DATABASE_REQUIRED")
    need(SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_SINGLE_OWNER_NOT_HELD")
    db.verify()
    meta = db.meta().copy()
    need(meta["source_sha"] == FROM_V20 and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1
         and type(meta["head_seq"]) is int and meta["head_seq"] >= 332
         and db.ready() is None and not db.actives()
         and verify_native_activation(db) is True,
         "V20_ORIGINAL_NOT_IDLE_OR_AUTHENTICATED")

    transitions = list(db.conn.execute(
        "SELECT sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "ORDER BY seq"))
    docs = [json.loads(r["payload"]) for r in transitions]
    v20 = [i for i, doc in enumerate(docs)
           if doc.get("schema") == "forge.f139.source-transition.v20"]
    need(len(v20) == 1 and v20[0] == len(docs) - 1
         and docs[-1]["to_source_sha"] == FROM_V20
         and docs[-1].get("v2_receipt_authorized") is False,
         "ORIGINAL_V20_TRANSITION_SEAL_CHANGED")
    g54 = verified_g54_ambiguous_start(db)
    need(bool(g54) and verify_original_negative_custody(db)
         and verify_second_negative_custody(db)
         and verify_g49_custody(db),
         "ORIGINAL_NEGATIVE_CUSTODY_NOT_AUTHENTIC")

    tasks = [dict(r) for r in db.conn.execute(
        "SELECT ticket,stage,run_id,evidence_sha,source_sha "
        "FROM tasks ORDER BY ticket")]
    need(all(r["stage"] in ("VERIFIED", "QUARANTINED") for r in tasks),
         "ACTIVE_QUARANTINED_OR_UNKNOWN_TASK")
    verified = [r for r in tasks if r["stage"] == "VERIFIED"]
    negatives = [r for r in tasks if r["stage"] == "QUARANTINED"]
    need(len(verified) >= 24 and len(negatives) >= 15
         and any(r["ticket"] == g54["ticket"] for r in negatives),
         "ORIGINAL_NATIVE_NEGATIVE_OR_POSITIVE_SET_DRIFT")
    bad_ticket = "f139-nci04-i1138-0743ca22b76e-8face43d"
    need(any(r["ticket"] == bad_ticket and r["stage"] == "QUARANTINED"
             and r["run_id"] is None and r["evidence_sha"] is None
             for r in negatives)
         and bad_ticket in db.verified_native_provider_failures(),
         "SPENT_FAILED_NATIVE_1138_QUARANTINE_MISSING")

    history = [dict(r) for r in db.conn.execute(
        "SELECT seq,kind,sha FROM events WHERE kind IN (" +
        ",".join("?" for _ in MODEL_KINDS) + ") ORDER BY seq", MODEL_KINDS)]
    counts = {kind: sum(r["kind"] == kind for r in history)
              for kind in MODEL_KINDS}
    need(v17_original_model_history_valid(counts)
         and counts["FREE_REASONER_ATTEMPTED"] == 8
         and counts["MODEL_DRAFT_ATTEMPTED"] ==
             counts["MODEL_DRAFT_AUTHENTICATED"],
         "ORIGINAL_SPENT_OR_UNRESOLVED_MODEL_HISTORY")
    spent = [r for r in history if r["kind"] == "FREE_REASONER_ATTEMPTED"]
    last = spent[-1]
    need(last["seq"] <= meta["head_seq"] and is_hash(last["sha"]),
         "LAST_SPENT_ORIGINAL_ATTEMPT_INVALID")

    historical = {sha for doc in docs
                  for sha in (doc["from_source_sha"], doc["to_source_sha"])}
    return {
        "meta": meta,
        "v20_terminal_event_sha256": transitions[-1]["sha"],
        "terminal_tasks_sha256": digest(canonical(tasks)),
        "model_history_sha256": digest(canonical(history)),
        "last_original_free_event_seq": last["seq"],
        "last_original_free_event_sha256": last["sha"],
        "verified_tasks": len(verified),
        "quarantined_tasks": len(negatives),
        "legacy_free_attempts_spent": counts["FREE_REASONER_ATTEMPTED"],
        "historical_sources": historical,
    }


def is_hash(value) -> bool:
    return type(value) is str and SHA64.fullmatch(value) is not None


def build_v24_readonly_preflight(db: Database, target_sha: str,
                                 owner_event_id: int) -> dict:
    state = original_v20_state(db)
    need(type(target_sha) is str and SHA40.fullmatch(target_sha) is not None
         and target_sha not in state["historical_sources"],
         "TARGET_NOT_NEW_OR_INVALID")
    need(type(owner_event_id) is int and owner_event_id > 0,
         "OWNER_COMMENT_EVENT_ID_REQUIRED")
    m = state["meta"]
    proof = {
        "schema": SCHEMA, "from_source_sha": FROM_V20,
        "to_source_sha": target_sha, "owner_event_id": owner_event_id,
        "event_seq": m["head_seq"], "event_head_sha256": m["head_hash"],
        "v20_terminal_event_sha256": state["v20_terminal_event_sha256"],
        "terminal_tasks_sha256": state["terminal_tasks_sha256"],
        "model_history_sha256": state["model_history_sha256"],
        "last_original_free_event_seq": state["last_original_free_event_seq"],
        "last_original_free_event_sha256": state["last_original_free_event_sha256"],
        "verified_tasks": state["verified_tasks"],
        "quarantined_tasks": state["quarantined_tasks"],
        "legacy_free_attempts_spent": state["legacy_free_attempts_spent"],
        "advisory_only": True, "scientific_first_use": False,
        "production_dispatch_authorized": False, "new_controller": False,
        "new_scheduler": False, "new_queue": False, "paid_api_calls": 0,
    }
    verify_v24_readonly_preflight(db, proof)
    return proof


def verify_v24_readonly_preflight(db: Database, proof: dict) -> dict:
    need(type(db) is Database, "ORIGINAL_DATABASE_REQUIRED")
    need(type(proof) is dict and set(proof) == FIELDS
         and json.loads(canonical(proof)) == proof,
         "NONCANONICAL_OR_UNKNOWN_APPROVAL_FIELDS")
    need(proof["schema"] == SCHEMA and proof["from_source_sha"] == FROM_V20
         and type(proof["to_source_sha"]) is str
         and SHA40.fullmatch(proof["to_source_sha"]) is not None
         and type(proof["owner_event_id"]) is int and proof["owner_event_id"] > 0
         and type(proof["event_seq"]) is int and proof["event_seq"] >= 332
         and type(proof["last_original_free_event_seq"]) is int
         and proof["last_original_free_event_seq"] > 0
         and type(proof["legacy_free_attempts_spent"]) is int
         and proof["legacy_free_attempts_spent"] == 8
         and type(proof["verified_tasks"]) is int
         and proof["verified_tasks"] >= 24
         and type(proof["quarantined_tasks"]) is int
         and proof["quarantined_tasks"] >= 15,
         "INVALID_ORIGINAL_OWNER_OR_FREE_HISTORY_COUNTS")
    for key in ("event_head_sha256", "v20_terminal_event_sha256",
                "terminal_tasks_sha256", "model_history_sha256",
                "last_original_free_event_sha256"):
        need(is_hash(proof[key]), "BAD_SHA256_" + key.upper())
    need(proof["advisory_only"] is True
         and proof["scientific_first_use"] is False
         and proof["production_dispatch_authorized"] is False
         and proof["new_controller"] is False
         and proof["new_scheduler"] is False
         and proof["new_queue"] is False
         and type(proof["paid_api_calls"]) is int
         and proof["paid_api_calls"] == 0, "FORBIDDEN_AUTHORITY_EXPANSION")
    s = original_v20_state(db)
    need(proof["to_source_sha"] not in s["historical_sources"],
         "TARGET_REPLAY_OR_HISTORIC_SOURCE")
    need(proof["event_seq"] == s["meta"]["head_seq"]
         and proof["event_head_sha256"] == s["meta"]["head_hash"],
         "OWNER_LEDGER_HEAD_CHANGED")
    for key in ("v20_terminal_event_sha256", "terminal_tasks_sha256",
                "model_history_sha256", "last_original_free_event_seq",
                "last_original_free_event_sha256", "verified_tasks",
                "quarantined_tasks", "legacy_free_attempts_spent"):
        need(proof[key] == s[key], "CUSTODY_DRIFT_" + key.upper())
    return {
        "read_only": True, "original_source_sha": FROM_V20,
        "target_source_sha": proof["to_source_sha"],
        "original_legacy_free_attempts_spent": 8,
        "release_authorized": False, "model_request_authorized": False,
        "new_controller": False, "scientific_first_use": False,
    }
