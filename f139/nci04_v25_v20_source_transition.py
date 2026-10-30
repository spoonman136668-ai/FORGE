"""Original V20 -> renewable V21 source-transition EVENT custody.

The only production state is the original F139 SQLite SHA event chain.
No new ledger/controller, model POST, worker dispatch, new scheduler, or
scientific promotion. The original Windows task must be quiesced by a
SEPARATE source-pinned release before invoking commit_original_v21.
"""
from __future__ import annotations

import json
from typing import Callable

from f139.local_controller import Database, SingleOwner, v17_original_model_history_valid
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v24_v20_renewable_readonly_preflight import (
    FROM_V20, MODEL_KINDS, verify_v24_readonly_preflight,
)
from f139.nci04_negative_owner_store import TICKET as FIRST
from f139.nci04_split_negative_owner_store import TICKET as SECOND
from f139.nci04_g49_prepost_negative import TICKET as PREPOST

SCHEMA = "forge.f139.source-transition.v21"
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha",
    "prior_event_head_sha256", "owner_event_id",
    "verified_historical_tasks", "custodied_negative_tasks",
    "custodied_negative_tickets", "provider_failures_sha256",
    "v20_terminal_event_sha256", "terminal_tasks_sha256",
    "model_history_sha256", "last_original_free_event_seq",
    "last_original_free_event_sha256", "legacy_free_attempts_spent",
    "new_dispatches", "scientific_first_use", "v2_receipt_authorized",
})


class V21TransitionDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise V21TransitionDenied("F139_V25_" + reason)


def _snapshot(db: Database, row, previous: list[dict]) -> dict:
    """Cold evidence only; does NOT trust user-provided source assertions."""
    from f139.local_controller import g54_original_canonical

    need(len(previous) >= 1 and previous[-1]["schema"] ==
         "forge.f139.source-transition.v20"
         and previous[-1]["to_source_sha"] == FROM_V20,
         "PREDECESSOR_NOT_GENUINE_V20")
    v20 = [t for t in previous if t["schema"] ==
           "forge.f139.source-transition.v20"]
    need(len(v20) == 1, "V20_PREDECESSOR_NOT_UNIQUE")
    prev_event = db.conn.execute(
        "SELECT seq,sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "AND seq<? ORDER BY seq DESC LIMIT 1", (row["seq"],)).fetchone()
    need(prev_event is not None
         and json.loads(prev_event["payload"]).get("schema") ==
             "forge.f139.source-transition.v20",
         "V20_SEAL_EVENT_CHANGED")
    historic_sources = {val for t in previous
                        for val in (t["from_source_sha"], t["to_source_sha"])}
    frozen_tasks = [dict(task) for task in db.conn.execute(
        "SELECT ticket,stage,run_id,evidence_sha,source_sha FROM tasks ORDER BY ticket")
        if task["source_sha"] in historic_sources]
    need(len(frozen_tasks) >= 25
         and all(t["stage"] in ("VERIFIED", "QUARANTINED")
                 for t in frozen_tasks), "HISTORICAL_NATIVE_TASK_STATUS_DRIFT")
    providers = db.verified_native_provider_failures(through_seq=row["seq"])
    g54 = g54_original_canonical(db, through_seq=row["seq"])
    expected = sorted({FIRST, SECOND, PREPOST, g54["ticket"]} | set(providers))
    negatives = [t for t in frozen_tasks if t["stage"] == "QUARANTINED"]
    positive = [t for t in frozen_tasks if t["stage"] == "VERIFIED"]
    need(len(positive) >= 24 and len(negatives) >= 15
         and {t["ticket"] for t in negatives} == set(expected),
         "FROZEN_NEGATIVE_SET_NOT_MATCHING_ORIGINAL")
    history = [dict(e) for e in db.conn.execute(
        "SELECT seq,kind,sha FROM events WHERE kind IN (" +
        ",".join("?" for _ in MODEL_KINDS) + ") AND seq<? ORDER BY seq",
        (*MODEL_KINDS, row["seq"]))]
    kinds = {k: sum(e["kind"] == k for e in history) for k in MODEL_KINDS}
    need(v17_original_model_history_valid(kinds)
         and kinds["FREE_REASONER_ATTEMPTED"] == 8
         and kinds["MODEL_DRAFT_ATTEMPTED"] ==
             kinds["MODEL_DRAFT_AUTHENTICATED"],
         "ORIGINAL_EIGHT_SPENT_AND_RESOLVED_REQUIRED")
    last = [e for e in history if e["kind"] == "FREE_REASONER_ATTEMPTED"][-1]
    return {
        "v20_terminal_event_sha256": prev_event["sha"],
        "terminal_tasks_sha256": digest(canonical(frozen_tasks)),
        "model_history_sha256": digest(canonical(history)),
        "last_original_free_event_seq": last["seq"],
        "last_original_free_event_sha256": last["sha"],
        "legacy_free_attempts_spent": 8,
        "verified_historical_tasks": len(positive),
        "custodied_negative_tasks": len(expected),
        "custodied_negative_tickets": expected,
        "provider_failures_sha256": digest(canonical([
            {"ticket": ticket, "source_sha": providers[ticket][0],
             "event_sha": providers[ticket][1]}
            for ticket in sorted(providers)
        ])),
    }


def verify_v21_cold_source_event(db: Database, row, doc: dict,
                                 previous: list[dict]) -> None:
    """Called by the ORIGINAL Database.verify on every cold reopen."""
    need(type(doc) is dict and set(doc) == FIELDS and doc["schema"] == SCHEMA
         and doc["from_source_sha"] == FROM_V20
         and type(doc["owner_event_id"]) is int and doc["owner_event_id"] > 0
         and doc["new_dispatches"] == 0
         and doc["scientific_first_use"] is False
         and doc["v2_receipt_authorized"] is False
         and doc["prior_event_head_sha256"] == row["prior_sha"]
         and not any(t["schema"] == SCHEMA for t in previous)
         and doc["to_source_sha"] not in {
             val for tr in previous
             for val in (tr["from_source_sha"], tr["to_source_sha"])
         }, "V21_SOURCE_EVENT_IDENTITY_REPLAY_OR_AUTHORITY")
    state = _snapshot(db, row, previous)
    for key, original in state.items():
        need(doc.get(key) == original, "CUSTODY_DRIFT_" + key.upper())


def commit_original_v21(
    db: Database, proof: dict, *,
    owner_witness: Callable[[], bool],
) -> dict:
    """One event/one transaction; source-only API, NO release authorization.

    Only a separately authenticated, quiesced original-owner release may
    supply the disabled-task owner witness. Caller must use canonical DB
    under original SingleOwner. Any verifier exception rolls back source
    and event in the SAME SQLite transaction; no retry of a spent event.
    """
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and callable(owner_witness) and owner_witness() is True,
         "REAL_ORIGINAL_OWNER_MUTEX_AND_WITNESS_REQUIRED")
    need(type(proof) is dict
         and proof.get("from_source_sha") == FROM_V20,
         "EXACT_V20_APPROVAL_REQUIRED")
    with db.transaction():
        verified = verify_v24_readonly_preflight(db, proof)
        before = db.meta().copy()
        need(verified["read_only"] is True
             and owner_witness() is True,
             "OWNER_REVOKED_BEFORE_TRANSITION")
        # The old source's entire verified history remains immutable.
        # This is NOT a replay/reset or creation of another controller.
        old_events = [json.loads(x["payload"]) for x in db.conn.execute(
            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
            "ORDER BY seq")]
        fake_row = {"seq": before["head_seq"]+1}
        state = _snapshot(db, fake_row, old_events)
        event = {
            "schema": SCHEMA,
            "from_source_sha": FROM_V20,
            "to_source_sha": proof["to_source_sha"],
            "prior_event_head_sha256": before["head_hash"],
            "owner_event_id": proof["owner_event_id"],
            **state,
            "new_dispatches": 0, "scientific_first_use": False,
            "v2_receipt_authorized": False,
        }
        for key in ("v20_terminal_event_sha256", "terminal_tasks_sha256",
                    "model_history_sha256", "last_original_free_event_seq",
                    "last_original_free_event_sha256", "legacy_free_attempts_spent"):
            need(event[key] == proof[key],
                 "ORIGINAL_APPROVAL_CHANGED_" + key.upper())
        db.conn.execute("UPDATE meta SET source_sha=? WHERE id=1",
                        (proof["to_source_sha"],))
        db.event("SOURCE_TRANSITION_ADMITTED", event)
        db.verify()
        after = db.meta()
        need(after["source_sha"] == proof["to_source_sha"]
             and after["head_seq"] == before["head_seq"]+1
             and owner_witness() is True,
             "ORIGINAL_TRANSITION_COLD_VERIFIER_OR_OWNER_REVOKED")
        return {
            "schema": "forge.f139.v25.original-v20-source-transition.v1",
            "source_sha": after["source_sha"],
            "event_seq": after["head_seq"],
            "event_head_sha256": after["head_hash"],
            "scientific_first_use": False, "new_controller": False,
            "paid_api_calls": 0,
        }
