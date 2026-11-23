"""Exact original V11 -> V12 source-only release for bounded model-free G29.

This module prepares/verifies a development-only approval from original owner
SQLite. It cannot enable science, create a second controller, or write GitHub.
A future guarded original-owner workflow must separately verify protected
main, original Windows task identity, clean checkout, backup, lock and policy.
"""
from __future__ import annotations
import json
import re
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_negative_owner_store import verify_original_negative_custody, TICKET as FIRST
from f139.nci04_split_negative_owner_store import verify_second_negative_custody, TICKET as SECOND
from f139.nci04_g49_prepost_negative import verify_g49_custody, TICKET as PREPOST
from f139.nci04_g54_ambiguous_start_custody import (
    verified_g54_ambiguous_start, EVENT_SHA256 as G54_SEAL,
)

SCHEMA = "forge.f139.nci04.original-owner-source-v12-approval.v1"
SOURCE_V11 = "4ac2320505af361c5959f72fff850f7467a752d9"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "owner_event_seq", "owner_event_sha256", "v11_terminal_event_sha256",
    "g54_ambiguous_start_event_sha256", "quarantined_tickets_sha256",
    "verified_tickets_sha256", "g3_draft_history_sha256",
    "development_only", "scientific_first_use",
    "v2_production_dispatch_authorized", "new_controller",
    "new_scheduler", "new_queue", "paid_api_calls",
})


class V12OwnerDenied(ValueError):
    pass


def need(cond: bool, reason: str):
    if not cond:
        raise V12OwnerDenied("F139_V12_" + reason)


def _original_state(db) -> dict:
    from f139.local_controller import Database
    need(type(db) is Database, "CANONICAL_ORIGINAL_DATABASE_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == SOURCE_V11
         and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1
         and type(meta["head_seq"]) is int
         and meta["head_seq"] >= 251
         and db.ready() is None and not db.actives()
         and verify_native_activation(db),
         "V11_OWNER_NOT_ACTIVATED_OR_QUIESCENT")
    need(not list(db.conn.execute(
        "SELECT ticket FROM tasks WHERE stage NOT IN ('VERIFIED','QUARANTINED')")),
        "OUTSTANDING_OR_INVALID_TASK")
    transition_rows = list(db.conn.execute(
        "SELECT sha,payload FROM events "
        "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq"))
    transitions = [json.loads(row["payload"]) for row in transition_rows]
    v11 = [i for i,t in enumerate(transitions)
           if t.get("schema") == "forge.f139.source-transition.v11"]
    need(len(v11) == 1 and v11[0] == len(transitions) - 1
         and transitions[-1]["to_source_sha"] == SOURCE_V11
         and transitions[-1]["v2_receipt_authorized"] is False,
         "EXACT_TERMINAL_V11_TRANSITION_REQUIRED")
    g54 = verified_g54_ambiguous_start(db)
    need(g54["quarantine_event_sha256"] == G54_SEAL
         and verify_original_negative_custody(db)
         and verify_second_negative_custody(db)
         and verify_g49_custody(db),
         "ORIGINAL_NEGATIVE_CUSTODY_INVALID")
    failures = db.verified_native_provider_failures()
    quarantined = sorted(row["ticket"] for row in db.conn.execute(
        "SELECT ticket FROM tasks WHERE stage='QUARANTINED'"))
    expected = sorted({FIRST, SECOND, PREPOST, g54["ticket"]} | set(failures))
    need(len(failures) >= 1 and quarantined == expected,
         "NEGATIVE_CUSTODY_TICKET_SET_CHANGED")
    verified = [dict(row) for row in db.conn.execute(
        "SELECT ticket,run_id,evidence_sha,source_sha FROM tasks "
        "WHERE stage='VERIFIED' ORDER BY ticket")]
    need(len(verified) >= 21
         and all(type(t["run_id"]) is int and t["run_id"] > 0
                 and isinstance(t["evidence_sha"], str)
                 and SHA64.fullmatch(t["evidence_sha"])
                 for t in verified),
         "ORIGINAL_VERIFIED_TASKS_INVALID")
    from f139.nci04_v11_owner_release import VERIFIED_RUN_996, VERIFIED_TICKET_996
    positive = [t for t in verified if t["ticket"] == VERIFIED_TICKET_996]
    need(len(positive) == 1
         and positive[0]["run_id"] == VERIFIED_RUN_996,
         "SIGNED_ORIGINAL_V2_996_CHANGED")
    g3_rows = list(db.conn.execute(
        "SELECT kind,sha,payload FROM events WHERE kind IN "
        "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED') ORDER BY seq"))
    attempts = [row for row in g3_rows if row["kind"] == "G3_DRAFT_ATTEMPTED"]
    successes = [row for row in g3_rows if row["kind"] == "G3_DRAFT_AUTHENTICATED"]
    need(len(attempts) == 1 and len(successes) <= 1,
         "FINITE_G3_HISTORY_NOT_FROZEN")
    # No fictitious success: pending/ambiguous G3 remains a guarded negative.
    g3 = [{"kind":row["kind"],"sha":row["sha"]} for row in g3_rows]
    return {
        "meta": meta,
        "v11_terminal_event_sha256": transition_rows[-1]["sha"],
        "g54_ambiguous_start_event_sha256": g54["quarantine_event_sha256"],
        "quarantined_tickets_sha256": digest(canonical(quarantined)),
        "verified_tickets_sha256": digest(canonical(
            [[v["ticket"],v["run_id"],v["evidence_sha"]] for v in verified])),
        "g3_draft_history_sha256": digest(canonical(g3)),
        "historical_sources": {value for t in transitions
                              for value in (t["from_source_sha"],t["to_source_sha"])},
        "quarantined": len(quarantined), "verified": len(verified),
    }


def build_v12_owner_approval(db, target_source_sha: str, owner_event_id: int) -> dict:
    state = _original_state(db)
    need(type(target_source_sha) is str and SHA40.fullmatch(target_source_sha)
         and target_source_sha not in state["historical_sources"],
         "SOURCE_REPLAY_OR_INVALID_TARGET")
    need(type(owner_event_id) is int and owner_event_id > 0,
         "OWNER_EVENT_ID_REQUIRED")
    m = state["meta"]
    approval = {
        "schema": SCHEMA,
        "from_source_sha": SOURCE_V11,
        "to_source_sha": target_source_sha,
        "owner_event_id": owner_event_id,
        "owner_event_seq": m["head_seq"],
        "owner_event_sha256": m["head_hash"],
        "v11_terminal_event_sha256": state["v11_terminal_event_sha256"],
        "g54_ambiguous_start_event_sha256": state["g54_ambiguous_start_event_sha256"],
        "quarantined_tickets_sha256": state["quarantined_tickets_sha256"],
        "verified_tickets_sha256": state["verified_tickets_sha256"],
        "g3_draft_history_sha256": state["g3_draft_history_sha256"],
        "development_only": True, "scientific_first_use": False,
        "v2_production_dispatch_authorized": False,
        "new_controller": False, "new_scheduler": False,
        "new_queue": False, "paid_api_calls": 0,
    }
    validate_v12_original_owner(db, approval)
    return approval


def validate_v12_original_owner(db, approval: dict) -> dict:
    from f139.local_controller import Database
    need(type(db) is Database, "CANONICAL_ORIGINAL_DATABASE_REQUIRED")
    need(type(approval) is dict and set(approval) == FIELDS,
         "EXACT_APPROVAL_FIELDS_REQUIRED")
    need(approval["schema"] == SCHEMA
         and approval["from_source_sha"] == SOURCE_V11
         and type(approval["to_source_sha"]) is str
         and SHA40.fullmatch(approval["to_source_sha"])
         and approval["to_source_sha"] != SOURCE_V11
         and type(approval["owner_event_id"]) is int
         and approval["owner_event_id"] > 0
         and type(approval["owner_event_seq"]) is int
         and approval["owner_event_seq"] >= 251,
         "APPROVED_SOURCE_EVENT_INVALID")
    for name in (
        "owner_event_sha256", "v11_terminal_event_sha256",
        "g54_ambiguous_start_event_sha256", "quarantined_tickets_sha256",
        "verified_tickets_sha256", "g3_draft_history_sha256",
    ):
        need(type(approval.get(name)) is str
             and SHA64.fullmatch(approval[name]),
             "APPROVAL_HASH_INVALID_" + name.upper())
    need(approval["development_only"] is True
         and approval["scientific_first_use"] is False
         and approval["v2_production_dispatch_authorized"] is False
         and approval["new_controller"] is False
         and approval["new_scheduler"] is False
         and approval["new_queue"] is False
         and type(approval["paid_api_calls"]) is int
         and approval["paid_api_calls"] == 0
         and json.loads(canonical(approval)) == approval,
         "NEW_AUTHORITY_FORBIDDEN")
    state = _original_state(db)
    m = state["meta"]
    need(approval["owner_event_seq"] == m["head_seq"]
         and approval["owner_event_sha256"] == m["head_hash"],
         "OWNER_EVENT_HEAD_CHANGED")
    for name in (
        "v11_terminal_event_sha256", "g54_ambiguous_start_event_sha256",
        "quarantined_tickets_sha256", "verified_tickets_sha256",
        "g3_draft_history_sha256",
    ):
        need(approval[name] == state[name], "FROZEN_HISTORY_CHANGED_" + name.upper())
    need(approval["to_source_sha"] not in state["historical_sources"],
         "SOURCE_ALREADY_CONSUMED")
    return {
        "source_from": SOURCE_V11,
        "source_to": approval["to_source_sha"],
        "event_head_sha256": m["head_hash"],
        "event_seq": m["head_seq"],
        "verified_originals": state["verified"],
        "quarantined_originals": state["quarantined"],
        "g54_ambiguous_no_replay": True,
        "scientific_first_use": False,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
        "paid_api_calls": 0,
    }
