"""G15 original-owner operator approval for ONE V6 source transition.

Does not sign V2 receipts, publish issues, dispatch experiments, open GitHub,
or modify SQLite. The existing original-owner CLI enforces protection and
quiescence, and Database.transition_source independently validates full custody.
"""
from __future__ import annotations

import json
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import SEALED_OWNER_PREFIX_HEAD

APPROVAL_SCHEMA = "forge.f139.nci04.owner-source-transition-approval.v2"
SOURCE_SCHEMA = "forge.f139.source-transition.v6"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
APPROVAL_KEYS = frozenset({
    "schema", "from_source_sha", "to_source_sha",
    "expected_event_head_sha256", "expected_event_head_seq",
    "sealed_23_event_head_sha256", "v5_terminal_event_sha256",
    "custodied_negative_tickets_sha256", "native_development_only",
    "v2_receipt_authorized", "scientific_first_use",
    "new_controller", "new_scheduler", "paid_api_calls",
})


class V6ReleaseDenied(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise V6ReleaseDenied("F139_G15_V6_" + reason)


def validate_v6_owner_approval(db, approval):
    """Pure, *non-mutating* original ledger approval verification.

    The caller must already hold SingleOwner and independently verify the
    installed clean checkout, protected GitHub SHA and disabled dispatchers.
    """
    meta=db.meta()
    require(type(approval) is dict and set(approval)==APPROVAL_KEYS
            and approval.get("schema")==APPROVAL_SCHEMA
            and isinstance(approval.get("from_source_sha"),str)
            and SHA40.fullmatch(approval["from_source_sha"]) is not None
            and isinstance(approval.get("to_source_sha"),str)
            and SHA40.fullmatch(approval["to_source_sha"]) is not None
            and approval["to_source_sha"]!=approval["from_source_sha"]
            and isinstance(approval.get("expected_event_head_sha256"),str)
            and SHA64.fullmatch(approval["expected_event_head_sha256"]) is not None
            and type(approval.get("expected_event_head_seq")) is int
            and approval["expected_event_head_seq"]>=218
            and isinstance(approval.get("v5_terminal_event_sha256"),str)
            and SHA64.fullmatch(approval["v5_terminal_event_sha256"]) is not None
            and isinstance(approval.get("custodied_negative_tickets_sha256"),str)
            and SHA64.fullmatch(approval["custodied_negative_tickets_sha256"]) is not None
            and approval.get("sealed_23_event_head_sha256")==SEALED_OWNER_PREFIX_HEAD
            and approval.get("native_development_only") is True
            and approval.get("v2_receipt_authorized") is False
            and approval.get("scientific_first_use") is False
            and approval.get("new_controller") is False
            and approval.get("new_scheduler") is False
            and type(approval.get("paid_api_calls")) is int
            and approval["paid_api_calls"]==0,
            "APPROVAL_SCHEMA_FIELDS_OR_FLAGS")
    require(meta["source_sha"]==approval["from_source_sha"]
            and meta["head_seq"]==approval["expected_event_head_seq"]
            and meta["head_hash"]==approval["expected_event_head_sha256"]
            and meta["enabled"]==1 and meta["legacy_suspended"]==1,
            "SOURCE_EPOCH_OR_EVENT_HEAD_DRIFT")
    require(not db.actives() and db.ready() is None,
            "PENDING_OR_ACTIVE_TASKS")
    rows=list(db.conn.execute(
        "SELECT seq,sha,payload FROM events "
        "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq"))
    prior=[json.loads(x["payload"]) for x in rows]
    v5=[x for x in rows if json.loads(x["payload"]).get("schema")==
        "forge.f139.source-transition.v5"]
    require(len(v5)==4 and len(rows)>=4
            and prior[-1]["schema"]=="forge.f139.source-transition.v5"
            and rows[-1]["sha"]==v5[-1]["sha"]
            and v5[-1]["sha"]==approval["v5_terminal_event_sha256"]
            and not any(p["schema"]==SOURCE_SCHEMA for p in prior),
            "SEALED_V5_FOUR_OF_FOUR_DRIFT")
    prior_sources={src for doc in prior for src in (
        doc["from_source_sha"],doc["to_source_sha"])}
    require(approval["to_source_sha"] not in prior_sources,
            "PRIOR_SOURCE_REPLAY")
    failures=db.verified_native_provider_failures()
    from f139.nci04_negative_owner_store import TICKET as FIRST
    from f139.nci04_split_negative_owner_store import TICKET as SECOND
    tickets=sorted({FIRST,SECOND}|set(failures))
    current=[r["ticket"] for r in db.conn.execute(
        "SELECT ticket FROM tasks WHERE stage='QUARANTINED'")]
    require(sorted(current)==tickets and len(tickets)>=13,
            "HISTORICAL_NEGATIVE_CUSTODY_DRIFT")
    require(digest(canonical(tickets))==
            approval["custodied_negative_tickets_sha256"],
            "NEGATIVE_TICKET_SEAL_DRIFT")
    return {
        "from_source_sha":meta["source_sha"],
        "to_source_sha":approval["to_source_sha"],
        "head_seq":meta["head_seq"],
        "head_hash":meta["head_hash"],
        "v5_terminal_event_sha256":v5[-1]["sha"],
        "negative_tasks":len(tickets),
        "v2_receipt_authorized":False,
    }
