"""G54 one-use V9 original-owner source transition after the frozen V8 release.

This validator binds the new source to the exact owner ledger observed by G53.
It does not authorize scientific first-use, production dispatch, or a new
controller, scheduler, or queue.
"""
from __future__ import annotations

import json
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_g49_prepost_negative import KIND, verify_g49_custody
from f139.nci04_owner_ledger import verify_native_activation

SOURCE_V8 = "157d3b545ceda507f4f8fabdf5c7b654a0b2fc84"
EXPECTED_HEAD_SEQ = 229
EXPECTED_HEAD_SHA256 = (
    "26c8a6a0543c75392df845c9716382979df029e5674297cb662469fb71677248"
)
SCHEMA = "forge.f139.nci04.original-owner-source-v9-approval.v1"
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "owner_event_seq", "owner_event_sha256", "v8_terminal_event_sha256",
    "prepost_negative_event_sha256", "quarantined_tickets_sha256",
    "development_only", "scientific_first_use",
    "v2_production_dispatch_authorized", "new_controller",
    "new_scheduler", "new_queue", "paid_api_calls",
})
SHA40 = re.compile(r"[a-f0-9]{40}\\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\\Z")


class V9OwnerDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise V9OwnerDenied("F139_G54_" + reason)


def _v8_rows(db):
    return [
        row for row in db.conn.execute(
            "SELECT sha,payload FROM events "
            "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq"
        )
        if json.loads(row["payload"]).get("schema")
        == "forge.f139.source-transition.v8"
    ]


def _prepost_rows(db):
    return db.conn.execute(
        "SELECT seq,sha,payload FROM events WHERE kind=? ORDER BY seq", (KIND,)
    ).fetchall()


def build_v9_owner_approval(db, target_source_sha: str, owner_event_id: int) -> dict:
    """Build an approval only from the exact frozen G53 owner-ledger preimage."""
    from f139.local_controller import Database
    need(type(db) is Database, "CANONICAL_OWNER_DATABASE_REQUIRED")
    db.verify()
    meta = db.meta()
    transitions = _v8_rows(db)
    negative = _prepost_rows(db)
    quarantined = sorted(row["ticket"] for row in db.conn.execute(
        "SELECT ticket FROM tasks WHERE stage='QUARANTINED'"
    ))
    approval = {
        "schema": SCHEMA,
        "from_source_sha": SOURCE_V8,
        "to_source_sha": target_source_sha,
        "owner_event_id": owner_event_id,
        "owner_event_seq": meta["head_seq"],
        "owner_event_sha256": meta["head_hash"],
        "v8_terminal_event_sha256": transitions[-1]["sha"] if transitions else "",
        "prepost_negative_event_sha256": negative[-1]["sha"] if negative else "",
        "quarantined_tickets_sha256": digest(canonical(quarantined)),
        "development_only": True,
        "scientific_first_use": False,
        "v2_production_dispatch_authorized": False,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
        "paid_api_calls": 0,
    }
    validate_v9_original_owner(db, approval)
    return approval


def validate_v9_original_owner(db, approval: dict) -> dict:
    from f139.local_controller import Database
    need(type(db) is Database, "CANONICAL_OWNER_DATABASE_REQUIRED")
    need(type(approval) is dict and set(approval) == FIELDS,
         "EXACT_APPROVAL_FIELDS_REQUIRED")
    need(approval.get("schema") == SCHEMA
         and approval.get("from_source_sha") == SOURCE_V8
         and isinstance(approval.get("to_source_sha"), str)
         and SHA40.fullmatch(approval["to_source_sha"]) is not None
         and approval["to_source_sha"] != SOURCE_V8,
         "APPROVED_SOURCE_IDENTITY")
    need(type(approval.get("owner_event_id")) is int
         and approval["owner_event_id"] > 0,
         "OWNER_EVENT_ID_REQUIRED")
    for name in ("owner_event_sha256", "v8_terminal_event_sha256",
                 "prepost_negative_event_sha256",
                 "quarantined_tickets_sha256"):
        need(isinstance(approval.get(name), str)
             and SHA64.fullmatch(approval[name]) is not None,
             "APPROVED_SHA_FIELD_" + name.upper())
    need(type(approval.get("owner_event_seq")) is int
         and approval["owner_event_seq"] == EXPECTED_HEAD_SEQ
         and approval.get("owner_event_sha256") == EXPECTED_HEAD_SHA256,
         "FROZEN_G53_LEDGER_HEAD_REQUIRED")
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

    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == SOURCE_V8
         and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1
         and meta["head_seq"] == EXPECTED_HEAD_SEQ
         and meta["head_hash"] == EXPECTED_HEAD_SHA256
         and db.ready() is None and not db.actives()
         and verify_g49_custody(db)
         and verify_native_activation(db),
         "ORIGINAL_V8_HEAD_OR_PENDING_TASK_DRIFT")

    transitions = list(db.conn.execute(
        "SELECT sha,payload FROM events "
        "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq"
    ))
    history = [json.loads(row["payload"]) for row in transitions]
    v8_rows = _v8_rows(db)
    need(len(v8_rows) == 1
         and bool(history)
         and history[-1].get("schema") == "forge.f139.source-transition.v8"
         and history[-1].get("to_source_sha") == SOURCE_V8
         and v8_rows[0]["sha"] == approval["v8_terminal_event_sha256"]
         and not any(event.get("schema") ==
                     "forge.f139.source-transition.v9" for event in history),
         "V8_TERMINAL_SEAL_REQUIRED")

    negative = _prepost_rows(db)
    need(len(negative) == 1
         and negative[0]["sha"] == approval["prepost_negative_event_sha256"],
         "EXACT_G49_PREPOST_CUSTODY_REQUIRED")
    quarantined = sorted(row["ticket"] for row in db.conn.execute(
        "SELECT ticket FROM tasks WHERE stage='QUARANTINED'"
    ))
    stages = list(db.conn.execute(
        "SELECT stage FROM tasks WHERE stage NOT IN ('QUARANTINED','VERIFIED')"
    ))
    need(not stages
         and digest(canonical(quarantined)) ==
             approval["quarantined_tickets_sha256"],
         "NEGATIVE_HISTORY_DRIFT")
    return {
        "schema": SCHEMA,
        "source_from": SOURCE_V8,
        "source_to": approval["to_source_sha"],
        "event_seq": meta["head_seq"],
        "event_head_sha256": meta["head_hash"],
        "quarantined_tasks": len(quarantined),
        "owner_event_id": approval["owner_event_id"],
        "source_transition_only": True,
        "scientific_first_use": False,
    }
