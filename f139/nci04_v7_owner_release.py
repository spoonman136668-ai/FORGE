"""F139 G39 one-use original-owner V7 release approval, no implicit V2 activation.

The actual original operator must separately approve, stop and lock the ONE
existing Windows controller, back up SQLite, and verify installed source.
This validator cannot dispatch anything, create an issue or enable science.
"""
from __future__ import annotations
import json
import re
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation

OLD = "b2079282fed03df2203807de09b4f3e82bdfe05a"
SCHEMA = "forge.f139.nci04.original-owner-source-v7-approval.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
FIELDS = frozenset((
    "schema","from_source_sha","to_source_sha","owner_event_seq",
    "owner_event_sha256","v6_terminal_event_sha256",
    "original_quarantined_tickets_sha256","development_only",
    "v2_production_dispatch_authorized","scientific_first_use",
    "new_controller","new_scheduler","new_queue","paid_api_calls",
))


class V7OwnerDenied(ValueError):
    pass


def need(ok: bool, reason: str):
    if not ok:
        raise V7OwnerDenied("F139_G39_"+reason)


def validate_v7_original_owner(db, approval: dict) -> dict:
    from f139.local_controller import Database
    need(type(db) is Database and type(approval) is dict
         and set(approval) == FIELDS and approval.get("schema") == SCHEMA
         and approval.get("from_source_sha") == OLD
         and isinstance(approval.get("to_source_sha"),str)
         and SHA40.fullmatch(approval["to_source_sha"]) is not None
         and approval["to_source_sha"] != OLD
         and type(approval.get("owner_event_seq")) is int
         and approval["owner_event_seq"] >= 220
         and isinstance(approval.get("owner_event_sha256"),str)
         and SHA64.fullmatch(approval["owner_event_sha256"]) is not None
         and isinstance(approval.get("v6_terminal_event_sha256"),str)
         and SHA64.fullmatch(approval["v6_terminal_event_sha256"]) is not None
         and isinstance(approval.get("original_quarantined_tickets_sha256"),str)
         and SHA64.fullmatch(approval["original_quarantined_tickets_sha256"]) is not None
         and approval.get("development_only") is True
         and approval.get("v2_production_dispatch_authorized") is False
         and approval.get("scientific_first_use") is False
         and approval.get("new_controller") is False
         and approval.get("new_scheduler") is False
         and approval.get("new_queue") is False
         and type(approval.get("paid_api_calls")) is int
         and approval["paid_api_calls"] == 0,
         "APPROVAL_FORM_UNQUALIFIED")
    # Check canonical file round-trip deterministically, preventing a
    # mutating release from accepting mismatched typed input.
    need(json.loads(canonical(approval)) == approval,
         "APPROVAL_CANONICAL_ROUNDTRIP_DRIFT")
    db.verify()
    meta=db.meta()
    need(meta["source_sha"]==OLD
         and meta["head_seq"]==approval["owner_event_seq"]
         and meta["head_hash"]==approval["owner_event_sha256"]
         and meta["enabled"]==1 and meta["legacy_suspended"]==1
         and db.ready() is None and not db.actives()
         and verify_native_activation(db),
         "ORIGINAL_OWNER_SOURCE_OR_PENDING_STATE_DRIFT")
    history=list(db.conn.execute(
        "SELECT sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq"))
    records=[json.loads(x["payload"]) for x in history]
    v6=[(x,y) for x,y in zip(history,records)
        if y["schema"]=="forge.f139.source-transition.v6"]
    need(len(v6)==1 and history[-1]["sha"]==v6[-1][0]["sha"]
         and records[-1]["to_source_sha"]==OLD
         and v6[-1][0]["sha"]==approval["v6_terminal_event_sha256"]
         and not any(x["schema"]=="forge.f139.source-transition.v7"
                     for x in records),
         "ONE_SHOT_V6_SEAL_REQUIRED")
    failures=db.verified_native_provider_failures()
    from f139.nci04_negative_owner_store import TICKET as FIRST
    from f139.nci04_split_negative_owner_store import TICKET as SECOND
    negatives=sorted({FIRST, SECOND} | set(failures))
    existing=sorted(x["ticket"] for x in db.conn.execute(
        "SELECT ticket FROM tasks WHERE stage='QUARANTINED'"))
    need(len(negatives)>=13 and negatives==existing
         and digest(canonical(negatives))==
             approval["original_quarantined_tickets_sha256"],
         "NEGATIVE_OWNER_CUSTODY_DRIFT")
    return {
        "schema":SCHEMA,
        "from_source_sha":OLD,
        "to_source_sha":approval["to_source_sha"],
        "v6_terminal_event_sha256":v6[-1][0]["sha"],
        "head_seq":meta["head_seq"],"head_sha256":meta["head_hash"],
        "negative_tickets":len(negatives),"source_transition_only":True,
        "v2_production_dispatch_authorized":False,
        "scientific_first_use":False,
    }
