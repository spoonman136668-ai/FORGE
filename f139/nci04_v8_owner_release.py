"""G50 one-use V8 original owner source transition after G49 #970 custody.

Only the authenticated existing Windows owner may conduct this release, under
its existing mutex and quiesced scheduler. This validator is read-only.
"""
from __future__ import annotations

import json
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_g49_prepost_negative import (
    SOURCE_V7, CLAIM_SEQ, TICKET, KIND, verify_g49_custody,
)
from f139.nci04_owner_ledger import verify_native_activation

SCHEMA = "forge.f139.nci04.original-owner-source-v8-approval.v1"
FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_seq",
    "owner_event_sha256", "v7_terminal_event_sha256",
    "prepost_negative_event_sha256", "original_quarantined_tickets_sha256",
    "development_only", "scientific_first_use",
    "v2_production_dispatch_authorized", "new_controller",
    "new_scheduler", "new_queue", "paid_api_calls",
})
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class V8OwnerDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise V8OwnerDenied("F139_G50_" + reason)


def validate_v8_original_owner(db, approval: dict) -> dict:
    from f139.local_controller import Database
    need(type(db) is Database, "CANONICAL_OWNER_DATABASE_REQUIRED")
    need(type(approval) is dict and set(approval)==FIELDS,
         "EXACT_APPROVAL_FIELDS_REQUIRED")
    need(approval.get("schema")==SCHEMA
         and approval.get("from_source_sha")==SOURCE_V7
         and isinstance(approval.get("to_source_sha"),str)
         and SHA40.fullmatch(approval["to_source_sha"]) is not None
         and approval["to_source_sha"] != SOURCE_V7,
         "APPROVED_SOURCE_IDENTITY")
    for name in ("owner_event_sha256", "v7_terminal_event_sha256",
                 "prepost_negative_event_sha256",
                 "original_quarantined_tickets_sha256"):
        need(isinstance(approval.get(name),str)
             and SHA64.fullmatch(approval[name]) is not None,
             "APPROVED_SHA_FIELD_" + name.upper())
    need(type(approval.get("owner_event_seq")) is int
         and approval["owner_event_seq"] == CLAIM_SEQ+2,
         "CERTIFICATE_SEQUENCE")
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
    meta=db.meta()
    need(meta["source_sha"]==SOURCE_V7 and meta["enabled"]==1
         and meta["legacy_suspended"]==1
         and meta["head_seq"]==CLAIM_SEQ+2
         and meta["head_hash"]==approval["owner_event_sha256"]
         and db.ready() is None and not db.actives()
         and verify_g49_custody(db)
         and verify_native_activation(db),
         "ORIGINAL_V7_HEAD_OR_PENDING_TASK_DRIFT")
    negative=db.conn.execute(
        "SELECT seq,sha,payload FROM events WHERE kind=?", (KIND,)).fetchall()
    need(len(negative)==1 and negative[0]["seq"]==CLAIM_SEQ+2
         and negative[0]["sha"]==approval["prepost_negative_event_sha256"],
         "EXACT_G49_CERTIFICATE_REQUIRED")
    transitions=list(db.conn.execute(
        "SELECT sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
        " ORDER BY seq"))
    history=[json.loads(r["payload"]) for r in transitions]
    need(bool(transitions) and history[-1]["schema"]==
         "forge.f139.source-transition.v7"
         and history[-1]["to_source_sha"]==SOURCE_V7
         and transitions[-1]["sha"]==
             approval["v7_terminal_event_sha256"]
         and not any(t["schema"]=="forge.f139.source-transition.v8"
                     for t in history),
         "V7_ONE_TIME_TERMINAL_SEAL_REQUIRED")
    quarantined=sorted(r["ticket"] for r in db.conn.execute(
        "SELECT ticket FROM tasks WHERE stage='QUARANTINED'"))
    not_verified=list(db.conn.execute(
        "SELECT stage FROM tasks WHERE stage NOT IN ('QUARANTINED','VERIFIED')"))
    need(len(quarantined)==14 and TICKET in quarantined
         and not not_verified
         and digest(canonical(quarantined))==
             approval["original_quarantined_tickets_sha256"],
         "NEGATIVE_HISTORY_NOT_COMPLETELY_CERTIFIED")
    return {"schema":SCHEMA, "source_from":SOURCE_V7,
            "source_to":approval["to_source_sha"],
            "head_seq":meta["head_seq"],
            "head_hash":meta["head_hash"],
            "certified_prepost_ticket":TICKET,
            "quarantined_tasks":len(quarantined),
            "source_transition_only":True,
            "scientific_first_use":False}
