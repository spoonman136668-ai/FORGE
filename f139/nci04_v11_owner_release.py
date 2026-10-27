"""V11 original Windows owner source successor with G54 #989 negative custody.

A V11 approval is made ONLY against the original, already-activated V10 SQLite.
It seals the unique V10 transition, all original negative and verified task
identities, and the precise G54 ambiguous-start #989 event. It does not install
code, call a model, publish a PR, authorize scientific first-use or mutate SQLite.
"""
from __future__ import annotations

import json
import re

from f139.nci04_g54_ambiguous_start_custody import (
    EVENT_SHA256 as G54_EVENT_SHA256, TICKET as G54_TICKET,
    verified_g54_ambiguous_start,
)
from f139.nci04_g49_prepost_negative import (
    TICKET as G49_TICKET, verify_g49_custody,
)
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_negative_owner_store import (
    TICKET as NEGATIVE_ORIGINAL, verify_original_negative_custody,
)
from f139.nci04_split_negative_owner_store import (
    TICKET as NEGATIVE_SPLIT, verify_second_negative_custody,
)

SOURCE_V10 = "e49569d4a8b74aa5d854caafa92abcdbcf15bc39"
V10_TRANSITION_SCHEMA = "forge.f139.source-transition.v10"
SCHEMA = "forge.f139.nci04.original-owner-source-v11-approval.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
VERIFIED_TICKET_996 = "f139-nci04-i996-e49569d4a8b7-015c3104"
VERIFIED_RUN_996 = 40465676857

FIELDS = frozenset({
    "schema", "from_source_sha", "to_source_sha", "owner_event_id",
    "owner_event_seq", "owner_event_sha256", "v10_terminal_event_sha256",
    "g54_ambiguous_start_event_sha256",
    "quarantined_tickets_sha256", "verified_tickets_sha256",
    "development_only", "scientific_first_use",
    "v2_production_dispatch_authorized",
    "new_controller", "new_scheduler", "new_queue", "paid_api_calls",
})


class V11OwnerDenied(ValueError):
    pass


def need(valid: bool, reason: str) -> None:
    if not valid:
        raise V11OwnerDenied("F139_V11_" + reason)


def _original_state(db) -> dict:
    from f139.local_controller import Database

    need(type(db) is Database, "CANONICAL_ORIGINAL_DATABASE_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == SOURCE_V10
         and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1
         and type(meta["head_seq"]) is int
         and meta["head_seq"] >= 249
         and db.ready() is None and not db.actives(),
         "V10_OWNER_NOT_ACTIVATED_OR_IDLE")
    remaining = list(db.conn.execute(
        "SELECT ticket,stage FROM tasks "
        "WHERE stage NOT IN ('QUARANTINED','VERIFIED')"))
    need(not remaining and verify_native_activation(db),
         "V10_NATIVE_ACTIVATION_OR_OUTSTANDING_WORK")
    transition_rows = list(db.conn.execute(
        "SELECT sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "ORDER BY seq"))
    transitions = [json.loads(row["payload"]) for row in transition_rows]
    v10 = [i for i, value in enumerate(transitions)
           if value.get("schema") == V10_TRANSITION_SCHEMA]
    need(len(v10) == 1 and v10[0] == len(transitions)-1
         and transitions[-1]["to_source_sha"] == SOURCE_V10,
         "EXACT_TERMINAL_V10_TRANSITION_REQUIRED")
    g54 = verified_g54_ambiguous_start(db)
    need(g54["quarantine_event_sha256"] == G54_EVENT_SHA256
         and g54["ticket"] == G54_TICKET,
         "G54_OWNER_AMBIGUOUS_START_NOT_FROZEN")
    need(verify_g49_custody(db)
         and verify_original_negative_custody(db)
         and verify_second_negative_custody(db),
         "ORIGINAL_NEGATIVE_CUSTODY_MISSING")
    failures = db.verified_native_provider_failures()
    allowed = {NEGATIVE_ORIGINAL, NEGATIVE_SPLIT, G49_TICKET, G54_TICKET} | set(failures)
    quarantined = sorted(r["ticket"] for r in db.conn.execute(
        "SELECT ticket FROM tasks WHERE stage='QUARANTINED'"))
    need(bool(failures) and quarantined == sorted(allowed),
         "ORIGINAL_NEGATIVE_SET_DRIFT")
    verified = [dict(r) for r in db.conn.execute(
        "SELECT ticket,run_id,evidence_sha,evidence_dir,source_sha "
        "FROM tasks WHERE stage='VERIFIED' ORDER BY ticket")]
    need(len(verified) >= 21 and
         all(type(t["run_id"]) is int and t["run_id"] > 0
             and isinstance(t["evidence_sha"], str)
             and SHA64.fullmatch(t["evidence_sha"]) is not None
             and isinstance(t["evidence_dir"], str) and t["evidence_dir"]
             for t in verified),
         "VERIFIED_ORIGINAL_RECEIPTS_MISSING")
    fresh = [t for t in verified if t["ticket"] == VERIFIED_TICKET_996]
    need(len(fresh) == 1 and fresh[0]["run_id"] == VERIFIED_RUN_996
         and fresh[0]["source_sha"] == SOURCE_V10,
         "POST_G54_V2_TERMINAL_996_MISSING")
    return {
        "meta": meta,
        "v10_terminal_event_sha256": transition_rows[-1]["sha"],
        "g54_ambiguous_start_event_sha256": g54["quarantine_event_sha256"],
        "quarantined_tickets_sha256": digest(canonical(quarantined)),
        "verified_tickets_sha256": digest(canonical([
            [t["ticket"], t["run_id"], t["evidence_sha"]]
            for t in verified
        ])),
        "historical_transition_sources": {
            value for event in transitions
            for value in (event["from_source_sha"], event["to_source_sha"])
        },
        "quarantined": len(quarantined), "verified": len(verified),
    }


def build_v11_owner_approval(db, to_source_sha: str,
                             owner_event_id: int) -> dict:
    state = _original_state(db)
    need(isinstance(to_source_sha, str)
         and SHA40.fullmatch(to_source_sha) is not None
         and to_source_sha not in state["historical_transition_sources"],
         "SOURCE_REPLAY_OR_INVALID_SHA")
    need(type(owner_event_id) is int and owner_event_id > 0,
         "OWNER_EVENT_ID_REQUIRED")
    meta = state["meta"]
    approval = {
        "schema": SCHEMA,
        "from_source_sha": SOURCE_V10,
        "to_source_sha": to_source_sha,
        "owner_event_id": owner_event_id,
        "owner_event_seq": meta["head_seq"],
        "owner_event_sha256": meta["head_hash"],
        "v10_terminal_event_sha256": state["v10_terminal_event_sha256"],
        "g54_ambiguous_start_event_sha256":
            state["g54_ambiguous_start_event_sha256"],
        "quarantined_tickets_sha256": state["quarantined_tickets_sha256"],
        "verified_tickets_sha256": state["verified_tickets_sha256"],
        "development_only": True,
        "scientific_first_use": False,
        "v2_production_dispatch_authorized": False,
        "new_controller": False, "new_scheduler": False,
        "new_queue": False, "paid_api_calls": 0,
    }
    validate_v11_original_owner(db, approval)
    return approval


def validate_v11_original_owner(db, approval: dict) -> dict:
    from f139.local_controller import Database

    need(type(db) is Database, "CANONICAL_ORIGINAL_DATABASE_REQUIRED")
    need(type(approval) is dict and set(approval) == FIELDS,
         "EXACT_APPROVAL_FIELDS_REQUIRED")
    need(approval["schema"] == SCHEMA
         and approval["from_source_sha"] == SOURCE_V10
         and isinstance(approval["to_source_sha"], str)
         and SHA40.fullmatch(approval["to_source_sha"]) is not None
         and approval["to_source_sha"] != SOURCE_V10,
         "SOURCE_REPLAY_OR_INVALID_SHA")
    need(type(approval["owner_event_id"]) is int
         and approval["owner_event_id"] > 0
         and type(approval["owner_event_seq"]) is int
         and approval["owner_event_seq"] >= 249,
         "OWNER_EVENT_ID_OR_SEQUENCE_INVALID")
    for key in (
        "owner_event_sha256", "v10_terminal_event_sha256",
        "g54_ambiguous_start_event_sha256",
        "quarantined_tickets_sha256", "verified_tickets_sha256",
    ):
        need(type(approval.get(key)) is str
             and SHA64.fullmatch(approval[key]) is not None,
             "PINNED_SHA_INVALID_" + key.upper())
    need(approval["development_only"] is True
         and approval["scientific_first_use"] is False
         and approval["v2_production_dispatch_authorized"] is False
         and approval["new_controller"] is False
         and approval["new_scheduler"] is False
         and approval["new_queue"] is False
         and type(approval["paid_api_calls"]) is int
         and approval["paid_api_calls"] == 0
         and json.loads(canonical(approval)) == approval,
         "NEW_AUTHORITY_NOT_ALLOWED")
    state = _original_state(db)
    meta = state["meta"]
    need(approval["owner_event_seq"] == meta["head_seq"]
         and approval["owner_event_sha256"] == meta["head_hash"],
         "OWNER_EVENT_HEAD_CHANGED")
    for name in (
        "v10_terminal_event_sha256",
        "g54_ambiguous_start_event_sha256",
        "quarantined_tickets_sha256", "verified_tickets_sha256",
    ):
        need(approval[name] == state[name],
             "FROZEN_HISTORY_CHANGED_" + name.upper())
    need(approval["to_source_sha"] not in
         state["historical_transition_sources"],
         "SOURCE_IDENTITY_ALREADY_CONSUMED")
    return {
        "source_from": SOURCE_V10,
        "source_to": approval["to_source_sha"],
        "event_seq": meta["head_seq"],
        "event_head_sha256": meta["head_hash"],
        "quarantined_originals": state["quarantined"],
        "verified_originals": state["verified"],
        "g54_ambiguous_no_replay": True,
        "scientific_first_use": False,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
        "paid_api_calls": 0,
    }
