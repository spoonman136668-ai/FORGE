"""G54 source successor from the installed V9 owner release.

The V10 approval is bound at runtime to the original owner's exact current
SQLite event head, the V9 transition seal, and immutable negative custody.
It authorizes development execution only; it grants no scientific first use,
production dispatch, or additional controller authority.
"""
from __future__ import annotations

import json
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_g49_prepost_negative import KIND as PREPOST_KIND, verify_g49_custody
from f139.nci04_owner_ledger import verify_native_activation

SOURCE_V9 = "3f1a3eba68d6b89e24913ca89df5e9bf8062bee0"
SCHEMA = "forge.f139.nci04.original-owner-source-v10-approval.v1"
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "owner_event_seq", "owner_event_sha256", "v9_terminal_event_sha256",
    "prepost_negative_event_sha256", "quarantined_tickets_sha256",
    "development_only", "scientific_first_use",
    "v2_production_dispatch_authorized", "new_controller",
    "new_scheduler", "new_queue", "paid_api_calls",
})
SHA40 = re.compile(r"[a-f0-9]{40}\\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\\Z")


class V10OwnerDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise V10OwnerDenied("F139_G54_" + reason)


def _transition_rows(db):
    return list(db.conn.execute(
        "SELECT seq,sha,payload FROM events "
        "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq"
    ))


def _v9_rows(db):
    return [
        row for row in _transition_rows(db)
        if json.loads(row["payload"]).get("schema")
        == "forge.f139.source-transition.v9"
    ]


def _prepost_rows(db):
    return db.conn.execute(
        "SELECT seq,sha,payload FROM events WHERE kind=? ORDER BY seq",
        (PREPOST_KIND,),
    ).fetchall()


def _quarantined_tickets(db):
    return sorted(row["ticket"] for row in db.conn.execute(
        "SELECT ticket FROM tasks WHERE stage='QUARANTINED'"
    ))


def _eligible_quiescent_ledger(db) -> dict:
    from f139.local_controller import Database
    need(type(db) is Database, "CANONICAL_OWNER_DATABASE_REQUIRED")
    db.verify()
    meta = db.meta()
    transitions = _transition_rows(db)
    history = [json.loads(row["payload"]) for row in transitions]
    v9 = _v9_rows(db)
    prepost = _prepost_rows(db)
    stages = list(db.conn.execute(
        "SELECT stage FROM tasks WHERE stage NOT IN ('QUARANTINED','VERIFIED')"
    ))
    need(meta["source_sha"] == SOURCE_V9
         and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1
         and db.ready() is None
         and not db.actives()
         and not stages,
         "V9_OWNER_LEDGER_NOT_QUIESCENT")
    need(verify_g49_custody(db) and verify_native_activation(db),
         "V9_ORIGINAL_CUSTODY_OR_ACTIVATION_INVALID")
    need(len(v9) == 1
         and bool(history)
         and history[-1].get("schema") == "forge.f139.source-transition.v9"
         and history[-1].get("to_source_sha") == SOURCE_V9,
         "EXACT_V9_TERMINAL_SEAL_REQUIRED")
    need(len(prepost) == 1,
         "EXACT_G49_PREPOST_CUSTODY_REQUIRED")
    return {
        "meta": meta,
        "v9_terminal_event_sha256": v9[0]["sha"],
        "prepost_negative_event_sha256": prepost[0]["sha"],
        "quarantined_tickets": _quarantined_tickets(db),
        "v9_transition": history[-1],
        "transitions": history,
    }


def build_v10_owner_approval(db, target_source_sha: str, owner_event_id: int) -> dict:
    """Freeze a new successor approval from the live protected owner ledger."""
    state = _eligible_quiescent_ledger(db)
    need(isinstance(target_source_sha, str)
         and SHA40.fullmatch(target_source_sha) is not None
         and target_source_sha != SOURCE_V9,
         "APPROVED_SOURCE_IDENTITY")
    need(all(target_source_sha not in
             (event.get("from_source_sha"), event.get("to_source_sha"))
             for event in state["transitions"]),
         "SOURCE_IDENTITY_ALREADY_CONSUMED")
    need(type(owner_event_id) is int and owner_event_id > 0,
         "OWNER_EVENT_ID_REQUIRED")
    meta = state["meta"]
    approval = {
        "schema": SCHEMA,
        "from_source_sha": SOURCE_V9,
        "to_source_sha": target_source_sha,
        "owner_event_id": owner_event_id,
        "owner_event_seq": meta["head_seq"],
        "owner_event_sha256": meta["head_hash"],
        "v9_terminal_event_sha256": state["v9_terminal_event_sha256"],
        "prepost_negative_event_sha256": state["prepost_negative_event_sha256"],
        "quarantined_tickets_sha256": digest(canonical(state["quarantined_tickets"])),
        "development_only": True,
        "scientific_first_use": False,
        "v2_production_dispatch_authorized": False,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
        "paid_api_calls": 0,
    }
    validate_v10_original_owner(db, approval)
    return approval


def validate_v10_original_owner(db, approval: dict) -> dict:
    from f139.local_controller import Database
    need(type(db) is Database, "CANONICAL_OWNER_DATABASE_REQUIRED")
    need(type(approval) is dict and set(approval) == FIELDS,
         "EXACT_APPROVAL_FIELDS_REQUIRED")
    need(approval.get("schema") == SCHEMA
         and approval.get("from_source_sha") == SOURCE_V9
         and isinstance(approval.get("to_source_sha"), str)
         and SHA40.fullmatch(approval["to_source_sha"]) is not None
         and approval["to_source_sha"] != SOURCE_V9,
         "APPROVED_SOURCE_IDENTITY")
    need(type(approval.get("owner_event_id")) is int
         and approval["owner_event_id"] > 0,
         "OWNER_EVENT_ID_REQUIRED")
    need(type(approval.get("owner_event_seq")) is int
         and approval["owner_event_seq"] > 0,
         "OWNER_EVENT_SEQUENCE_REQUIRED")
    for name in ("owner_event_sha256", "v9_terminal_event_sha256",
                 "prepost_negative_event_sha256", "quarantined_tickets_sha256"):
        need(isinstance(approval.get(name), str)
             and SHA64.fullmatch(approval[name]) is not None,
             "APPROVED_SHA_FIELD_" + name.upper())
    need(approval.get("development_only") is True
         and approval.get("scientific_first_use") is False
         and approval.get("v2_production_dispatch_authorized") is False
         and approval.get("new_controller") is False
         and approval.get("new_scheduler") is False
         and approval.get("new_queue") is False
         and type(approval.get("paid_api_calls")) is int
         and approval["paid_api_calls"] == 0
         and json.loads(canonical(approval)) == approval,
         "APPROVAL_NO_NEW_AUTHORITY")

    state = _eligible_quiescent_ledger(db)
    meta = state["meta"]
    need(approval["owner_event_seq"] == meta["head_seq"]
         and approval["owner_event_sha256"] == meta["head_hash"],
         "OWNER_EVENT_HEAD_DRIFT")
    need(approval["v9_terminal_event_sha256"] ==
             state["v9_terminal_event_sha256"]
         and approval["prepost_negative_event_sha256"] ==
             state["prepost_negative_event_sha256"]
         and approval["quarantined_tickets_sha256"] ==
             digest(canonical(state["quarantined_tickets"]),
         "NEGATIVE_CUSTODY_DRIFT")
    need(all(approval["to_source_sha"] not in
             (event.get("from_source_sha"), event.get("to_source_sha"))
             for event in state["transitions"]),
         "SOURCE_IDENTITY_ALREADY_CONSUMED")
    return {
        "schema": SCHEMA,
        "source_from": SOURCE_V9,
        "source_to": approval["to_source_sha"],
        "event_seq": meta["head_seq"],
        "event_head_sha256": meta["head_hash"],
        "quarantined_tasks": len(state["quarantined_tickets"]),
        "owner_event_id": approval["owner_event_id"],
        "source_transition_only": True,
        "scientific_first_use": False,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
        "paid_api_calls": 0,
    }
