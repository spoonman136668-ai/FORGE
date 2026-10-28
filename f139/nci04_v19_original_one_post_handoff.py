"""V19 original-owner one-time free-model HANDOFF CUSTODY, no POST.

A distinct event in the existing original SQLite chain reserves the single
future transport handoff AFTER the distinct original research intent commit.
The returned receipt is NOT permission to contact a model provider.
Nothing here imports or invokes an HTTP transport, worker, GitHub write, or
the live controller tick. Original-owner source release remains separate.
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable

from f139.local_controller import Database, SingleOwner
from f139.nci04_free_reasoner_provider import (
    MODEL, SCHEMA as PUBLIC_SCHEMA, make_body,
    verify_anonymous_public_source,
)
from f139.nci04_v19_original_attempt_schema import (
    KIND as RESERVATION_KIND, SCHEMA as RESERVATION_SCHEMA,
)
from f139.nci04_v19_research_renewal_shadow import (
    ShadowDenied, day_value, is_sha40, is_sha64,
)

KIND = "NATIVE_RENEWAL_POST_ATTEMPTED"
SCHEMA = "forge.f139.v19.original-free-model-post-handoff.v1"
FIELDS = frozenset({
    "schema", "owner_source_sha", "reservation_seq", "reservation_sha256",
    "terminal_ticket", "lane", "scope_sha256", "target_commit",
    "native_path", "public_tree_sha", "public_source_sha256",
    "public_history_sha256", "public_packet_sha256", "request_body_sha256",
    "utc_day", "model", "prior_event_head_sha256",
    "retry_allowed", "paid_model_calls", "provider_request_authorized",
    "publication_authorized", "scientific_first_use",
})


def deny(code: str) -> None:
    raise ShadowDenied("F139_V19_POST_HANDOFF_" + code)


def audit_v19_post_handoff_events(db: Database) -> None:
    """Cold verify SHA-linked V19 handoffs after Database.verify's chain audit.

    An unrelated event or a second handoff for the same reservation is invalid.
    No provider inference and no mutation occurs here.
    """
    records = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"))
    if not any(r["kind"] == KIND for r in records):
        return
    reservations = {}
    spent = set()
    for r in records:
        kind = r["kind"]
        if kind == RESERVATION_KIND:
            doc = json.loads(r["payload"])
            if doc.get("schema") != RESERVATION_SCHEMA:
                deny("RESERVATION_SCHEMA")
            reservations[r["seq"]] = (r, doc)
        if kind != KIND:
            continue
        doc = json.loads(r["payload"])
        if (type(doc) is not dict or set(doc) != FIELDS
                or doc["schema"] != SCHEMA
                or not is_sha40(doc["owner_source_sha"])
                or type(doc["reservation_seq"]) is not int
                or doc["reservation_seq"] < 1
                or not is_sha64(doc["reservation_sha256"])
                or type(doc["terminal_ticket"]) is not str
                or doc["lane"] not in ("Wingless", "Yggdrasil")
                or not is_sha64(doc["scope_sha256"])
                or not is_sha40(doc["target_commit"])
                or type(doc["native_path"]) is not str
                or not is_sha40(doc["public_tree_sha"])
                or not all(is_sha64(doc[x]) for x in (
                    "public_source_sha256", "public_history_sha256",
                    "public_packet_sha256", "request_body_sha256"))
                or doc["model"] != MODEL
                or doc["prior_event_head_sha256"] != r["prior_sha"]
                or doc["retry_allowed"] is not False
                or type(doc["paid_model_calls"]) is not int
                or doc["paid_model_calls"] != 0
                or doc["provider_request_authorized"] is not False
                or doc["publication_authorized"] is not False
                or doc["scientific_first_use"] is not False):
            deny("COLD_FIELDS_OR_AUTHORITY")
        day_value(doc["utc_day"])
        ref = reservations.get(doc["reservation_seq"])
        if ref is None or doc["reservation_seq"] in spent:
            deny("ORIGINAL_RESERVATION_MISSING_OR_REPLAYED")
        reservation, intent = ref
        if (reservation["seq"] + 1 != r["seq"]
                or reservation["sha"] != r["prior_sha"]
                or intent["owner_source_sha"] != doc["owner_source_sha"]
                or intent["terminal_ticket"] != doc["terminal_ticket"]
                or intent["lane"] != doc["lane"]
                or intent["scope_sha256"] != doc["scope_sha256"]
                or intent["target_commit"] != doc["target_commit"]
                or intent["native_path"] != doc["native_path"]
                or reservation["sha"] != doc["reservation_sha256"]
                or intent["utc_day"] != doc["utc_day"]):
            deny("RESERVATION_BINDING_OR_NONADJACENT_HANDOFF")
        spent.add(reservation["seq"])


def outcome(disposition: str, *, seq: int | None = None,
            sha: str | None = None) -> dict:
    return {
        "schema": SCHEMA, "disposition": disposition,
        "original_post_handoff_event_seq": seq,
        "original_post_handoff_event_sha256": sha,
        "provider_requests": 0, "paid_model_calls": 0,
        "original_owner_request_authorized": False,
        "publication_authorized": False, "worker_dispatched": False,
        "scientific_first_use": False, "accepted_ref_mutations": 0,
    }


def custody_original_post_handoff_without_post(
    db: Database, *, reservation_seq: int, reservation_sha256: str,
    public_packet: dict, public_reader: Callable[[str], dict],
    utc_day: str, owner_witness: Callable[[], bool],
    fault_after_append: bool = False,
) -> dict:
    """Cold-authenticate public payload, then atomically spend its POST handoff.

    Source-only operation; NEVER calls infer_free_once or _post_one.
    Exact predecessor reservation is mandatory: no interleaved original
    events, no cold replay and no separate ledger or payment route.
    """
    if (type(db) is not Database
            or type(reservation_seq) is not int or reservation_seq < 1
            or not is_sha64(reservation_sha256)
            or not callable(owner_witness) or owner_witness() is not True
            or not SingleOwner.held(db.filename.with_suffix(".lock"))):
        deny("ORIGINAL_OWNER_CUSTODY_REQUIRED")
    if (type(public_packet) is not dict
            or not callable(public_reader)
            or type(fault_after_append) is not bool):
        deny("PUBLIC_PACKET_OR_FAULT_FLAG")
    day_value(utc_day)
    if public_packet.get("schema") != PUBLIC_SCHEMA:
        deny("PUBLIC_PACKET_SCHEMA_INVALID")

    # The original, cold-verified ledger is the cheapest and strongest
    # negative witness. Never repeat even anonymous Git fetches for a spent
    # reservation after a lost response, restart or UTC rollover.
    # Revalidate this observation *again* under BEGIN IMMEDIATE below.
    db.verify()
    observed = db.meta()
    if (observed["head_seq"] != reservation_seq
            or observed["head_hash"] != reservation_sha256):
        return outcome("BLOCKED_RESERVATION_ALREADY_SPENT_OR_HISTORY_MOVED")

    # These are source-only and anonymous Git reads; never pass a user token.
    # No pre-POST attempt is emitted if bytes are not publicly verifiable.
    body = make_body(public_packet)
    if verify_anonymous_public_source(public_packet, public_reader) is not True:
        deny("ANONYMOUS_PUBLIC_SOURCE_NOT_PROVEN")
    packet_digest = hashlib.sha256(
        json.dumps(public_packet, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    body_digest = hashlib.sha256(body).hexdigest()

    with db.transaction():
        db.verify()
        meta = db.meta()
        if (meta["enabled"] != 1 or meta["legacy_suspended"] != 1
                or db.ready() is not None or db.actives()):
            return outcome("BLOCKED_OWNER_DISABLED_OR_BUSY")
        reservation = db.conn.execute(
            "SELECT seq,kind,payload,sha FROM events WHERE seq=?",
            (reservation_seq,)).fetchone()
        if (reservation is None or reservation["kind"] != RESERVATION_KIND
                or reservation["sha"] != reservation_sha256):
            return outcome("BLOCKED_UNKNOWN_OR_FORGED_RESERVATION")
        # Any intervening event means the original source/owner/feedback may
        # have moved. Replay after a crash remains spent, even if the caller
        # claims that an earlier model response was lost.
        if (meta["head_seq"] != reservation_seq
                or meta["head_hash"] != reservation_sha256):
            return outcome("BLOCKED_RESERVATION_ALREADY_SPENT_OR_HISTORY_MOVED")
        intent = json.loads(reservation["payload"])
        if (intent.get("schema") != RESERVATION_SCHEMA
                or intent["owner_source_sha"] != meta["source_sha"]
                or intent["utc_day"] != utc_day
                or intent["lane"] != public_packet["lane"]
                or intent["target_commit"] != public_packet["target_commit"]
                or intent["native_path"] != public_packet["path"]
                or owner_witness() is not True):
            return outcome("BLOCKED_SOURCE_OR_OWNER_WITNESS_DRIFT")
        item = {
            "schema": SCHEMA,
            "owner_source_sha": meta["source_sha"],
            "reservation_seq": reservation_seq,
            "reservation_sha256": reservation_sha256,
            "terminal_ticket": intent["terminal_ticket"],
            "lane": intent["lane"],
            "scope_sha256": intent["scope_sha256"],
            "target_commit": intent["target_commit"],
            "native_path": intent["native_path"],
            "public_tree_sha": public_packet["target_tree_sha"],
            "public_source_sha256": public_packet["before_sha256"],
            "public_history_sha256": public_packet["history_sha256"],
            "public_packet_sha256": packet_digest,
            "request_body_sha256": body_digest,
            "utc_day": utc_day,
            "model": MODEL,
            "prior_event_head_sha256": meta["head_hash"],
            "retry_allowed": False, "paid_model_calls": 0,
            "provider_request_authorized": False,
            "publication_authorized": False,
            "scientific_first_use": False,
        }
        db.event(KIND, item)
        db.verify()
        if fault_after_append:
            deny("INJECTED_PRECOMMIT_ROLLBACK")
        event = db.conn.execute(
            "SELECT seq,sha FROM events WHERE seq=? AND kind=?",
            (reservation_seq + 1, KIND)).fetchone()
        if (event is None or db.meta()["head_hash"] != event["sha"]
                or owner_witness() is not True):
            deny("ORIGINAL_OWNER_REVOKED_PRECOMMIT")
        return outcome("ORIGINAL_POST_HANDOFF_SPENT_NO_POST",
                       seq=event["seq"], sha=event["sha"])
