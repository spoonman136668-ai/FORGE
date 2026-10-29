"""F139 V19 one-shot free-model transport adapter (SOURCE-ONLY, not deployed).

Exactly one ORIGINAL SQLite SEND_ATTEMPTED event is committed before invoking
one caller-provided provider transport. Caller transport is mandatory: no
implicit HTTP, environment token lookup, scheduler, GitHub write, or live
controller entrypoint. Even ambiguous transport failures irreversibly spend
the handoff. Responses remain untrusted, never directly published.
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable

from f139.local_controller import Database, SingleOwner
from f139.nci04_free_reasoner_provider import (
    MODEL, FreeReasonerDenied, FreeReasonerUnavailable, infer_free_once,
    make_body, verify_anonymous_public_source,
)
from f139.nci04_v19_original_one_post_handoff import (
    KIND as HANDOFF_KIND, SCHEMA as HANDOFF_SCHEMA,
)
from f139.nci04_v19_research_renewal_shadow import (
    ShadowDenied, day_value, is_sha40, is_sha64,
)

KIND = "NATIVE_RENEWAL_SEND_ATTEMPTED"
SCHEMA = "forge.f139.v19.original-one-shot-free-send.v1"
FIELDS = frozenset({
    "schema", "owner_source_sha", "handoff_seq", "handoff_sha256",
    "terminal_ticket", "lane", "scope_sha256", "model",
    "request_body_sha256", "public_packet_sha256", "utc_day",
    "prior_event_head_sha256", "one_post_maximum",
    "retry_allowed", "paid_model_calls", "publication_authorized",
    "scientific_first_use",
})


def deny(code: str) -> None:
    raise ShadowDenied("F139_V19_ONE_POST_" + code)


def audit_v19_send_events(db: Database) -> None:
    """Cold verify SEND_ATTEMPTED after the original full SHA-chain verifier.

    All history must be valid even if the original remote POST was ambiguous.
    Deliberately no remote/model transport and no SQLite write.
    """
    events = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"))
    if not any(e["kind"] == KIND for e in events):
        return
    handoffs = {}
    spent = set()
    for row in events:
        kind = row["kind"]
        if kind == HANDOFF_KIND:
            doc = json.loads(row["payload"])
            if doc.get("schema") != HANDOFF_SCHEMA:
                deny("HANDOFF_SCHEMA_DRIFT")
            handoffs[row["seq"]] = (row, doc)
        if kind != KIND:
            continue
        doc = json.loads(row["payload"])
        if (type(doc) is not dict or set(doc) != FIELDS
                or doc["schema"] != SCHEMA
                or not is_sha40(doc["owner_source_sha"])
                or type(doc["handoff_seq"]) is not int
                or doc["handoff_seq"] <= 0
                or not is_sha64(doc["handoff_sha256"])
                or type(doc["terminal_ticket"]) is not str
                or doc["lane"] not in ("Wingless", "Yggdrasil")
                or not is_sha64(doc["scope_sha256"])
                or doc["model"] != MODEL
                or not is_sha64(doc["request_body_sha256"])
                or not is_sha64(doc["public_packet_sha256"])
                or doc["prior_event_head_sha256"] != row["prior_sha"]
                or type(doc["one_post_maximum"]) is not int
                or doc["one_post_maximum"] != 1
                or doc["retry_allowed"] is not False
                or type(doc["paid_model_calls"]) is not int
                or doc["paid_model_calls"] != 0
                or doc["publication_authorized"] is not False
                or doc["scientific_first_use"] is not False):
            deny("COLD_SEND_FIELDS_OR_AUTHORITY")
        day_value(doc["utc_day"])
        predecessor = handoffs.get(doc["handoff_seq"])
        if predecessor is None or doc["handoff_seq"] in spent:
            deny("SEND_ORIGINAL_HANDOFF_MISSING_OR_REPLAY")
        original, handoff = predecessor
        if (original["seq"] + 1 != row["seq"]
                or original["sha"] != row["prior_sha"]
                or original["sha"] != doc["handoff_sha256"]
                or handoff["owner_source_sha"] != doc["owner_source_sha"]
                or handoff["terminal_ticket"] != doc["terminal_ticket"]
                or handoff["lane"] != doc["lane"]
                or handoff["scope_sha256"] != doc["scope_sha256"]
                or handoff["request_body_sha256"] != doc["request_body_sha256"]
                or handoff["public_packet_sha256"] != doc["public_packet_sha256"]
                or handoff["utc_day"] != doc["utc_day"]
                or handoff["model"] != doc["model"]):
            deny("SEND_HANDOFF_BINDING_OR_NONADJACENT_EVENT")
        spent.add(original["seq"])


def verdict(disposition: str, *, seq: int | None = None,
            sha: str | None = None, called: int = 0,
            untrusted_response: dict | None = None) -> dict:
    return {
        "schema": SCHEMA, "disposition": disposition,
        "send_attempt_event_seq": seq,
        "send_attempt_event_sha256": sha,
        "provider_calls_in_this_invocation": called,
        "provider_attempt_history_spent": seq is not None,
        "paid_model_calls": 0,
        "publication_authorized": False,
        "worker_dispatched": False,
        "scientific_first_use": False,
        "accepted_ref_mutations": 0,
        "untrusted_response": untrusted_response,
        "original_controller_activated": False,
    }


def one_original_free_send_source_only(
    db: Database, *, handoff_seq: int, handoff_sha256: str,
    public_packet: dict, public_reader: Callable[[str], dict],
    owner_witness: Callable[[], bool],
    token: str, transport: Callable[[bytes, str], bytes],
    fault_after_append: bool = False,
) -> dict:
    """Spend one original SQLite event BEFORE exactly one injected transport.

    The public transport is MANDATORY, never implicitly _post_one. The live
    F139 controller does not import this function. This draft is not an
    operational permission to contact any provider; its regression transports
    are entirely mocked. Future production activation requires independently
    approved source release, credential custody, and free-only transport.
    """
    if (type(db) is not Database
            or type(handoff_seq) is not int or handoff_seq <= 0
            or not is_sha64(handoff_sha256)
            or not callable(owner_witness) or owner_witness() is not True
            or not SingleOwner.held(db.filename.with_suffix(".lock"))):
        deny("ORIGINAL_OWNER_LOCK_OR_WITNESS_REQUIRED")
    if (type(public_packet) is not dict
            or not callable(public_reader) or not callable(transport)
            or type(token) is not str or not token.strip()
            or "\r" in token or "\n" in token or len(token) > 2048
            or type(fault_after_append) is not bool):
        deny("PUBLIC_INPUT_OR_EXPLICIT_CREDENTIAL_REQUIRED")
    # Cold check BEFORE public-source network or token-bearing transport. A
    # spent handoff must not even repeat anonymous source fetching.
    db.verify()
    meta = db.meta()
    if (meta["head_seq"] != handoff_seq
            or meta["head_hash"] != handoff_sha256):
        return verdict("BLOCKED_HANDOFF_ALREADY_SPENT_OR_HEAD_MOVED")
    handoff = db.conn.execute(
        "SELECT kind,payload,sha FROM events WHERE seq=?", (handoff_seq,)
    ).fetchone()
    if handoff is None or handoff["kind"] != HANDOFF_KIND:
        return verdict("BLOCKED_UNKNOWN_HANDOFF")
    item = json.loads(handoff["payload"])
    if item.get("schema") != HANDOFF_SCHEMA:
        deny("ORIGINAL_HANDOFF_SCHEMA_DRIFT")
    packet_bytes = json.dumps(
        public_packet, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")
    packet_sha = hashlib.sha256(packet_bytes).hexdigest()
    body_sha = hashlib.sha256(make_body(public_packet)).hexdigest()
    if (packet_sha != item["public_packet_sha256"]
            or body_sha != item["request_body_sha256"]
            or public_packet["lane"] != item["lane"]
            or public_packet["target_commit"] != item["target_commit"]
            or public_packet["path"] != item["native_path"]
            or public_packet["before_sha256"] != item["public_source_sha256"]
            or public_packet["history_sha256"] != item["public_history_sha256"]
            or public_packet["target_tree_sha"] != item["public_tree_sha"]):
        deny("PUBLIC_BYTES_OR_SCOPE_CHANGED")
    if verify_anonymous_public_source(public_packet, public_reader) is not True:
        deny("PUBLIC_SOURCE_NOT_AUTHENTIC")
    # No external provider call may occur until this transaction has COMMITTED.
    # If process crashes during/after the call, the receipt remains forever
    # spent; there is no retry, even across cold reopen or UTC midnight.
    with db.transaction():
        db.verify()
        meta = db.meta()
        if (meta["enabled"] != 1 or meta["legacy_suspended"] != 1
                or db.ready() is not None or db.actives()
                or meta["head_seq"] != handoff_seq
                or meta["head_hash"] != handoff_sha256
                or meta["source_sha"] != item["owner_source_sha"]
                or owner_witness() is not True
                or not SingleOwner.held(db.filename.with_suffix(".lock"))):
            return verdict("BLOCKED_ORIGINAL_OWNER_OR_HANDOFF_MOVED")
        event_doc = {
            "schema": SCHEMA, "owner_source_sha": meta["source_sha"],
            "handoff_seq": handoff_seq, "handoff_sha256": handoff_sha256,
            "terminal_ticket": item["terminal_ticket"], "lane": item["lane"],
            "scope_sha256": item["scope_sha256"], "model": MODEL,
            "request_body_sha256": body_sha,
            "public_packet_sha256": packet_sha,
            "utc_day": item["utc_day"],
            "prior_event_head_sha256": meta["head_hash"],
            "one_post_maximum": 1, "retry_allowed": False,
            "paid_model_calls": 0, "publication_authorized": False,
            "scientific_first_use": False,
        }
        db.event(KIND, event_doc)
        db.verify()
        if fault_after_append:
            deny("INJECTED_PRECOMMIT_ROLLBACK")
        new = db.conn.execute(
            "SELECT seq,sha FROM events WHERE seq=? AND kind=?",
            (handoff_seq + 1, KIND)).fetchone()
        if (new is None or owner_witness() is not True
                or db.meta()["head_hash"] != new["sha"]):
            deny("ORIGINAL_OWNER_REVOKED_PRECOMMIT")
        final_seq, final_sha = new["seq"], new["sha"]
    # It is now permanently spent, BEFORE the external transport. The caller
    # never supplies its own HTTP URL/model and cannot regain a spent handoff.
    # infer_free_once guarantees exact free model, source and response bounds.
    actual_calls = 0
    def once_only_transport(body: bytes, supplied_token: str) -> bytes:
        nonlocal actual_calls
        # The original event has already committed; count even an
        # ambiguous/failed transport. Any accidental second invocation is
        # rejected in-process and original cold SQLite still denies replay.
        if actual_calls != 0:
            deny("SECOND_PROVIDER_SEND_WITH_SAME_ORIGINAL_HANDOFF")
        # Public-source verification after the committed send receipt can
        # revoke the owner witness. Recheck immediately before any transport;
        # the committed original attempt remains spent on a revoked witness.
        if (owner_witness() is not True
                or not SingleOwner.held(db.filename.with_suffix(".lock"))):
            deny("ORIGINAL_OWNER_REVOKED_BEFORE_PROVIDER_TRANSPORT")
        actual_calls += 1
        return transport(body, supplied_token)

    try:
        response = infer_free_once(
            public_packet, token=token, transport=once_only_transport,
            public_reader=public_reader)
    except (FreeReasonerUnavailable, FreeReasonerDenied):
        return verdict("MODEL_SEND_FAILED_OR_AMBIGUOUS_NO_RETRY",
                       seq=final_seq, sha=final_sha, called=actual_calls)
    except Exception:
        return verdict("MODEL_SEND_FAILED_OR_AMBIGUOUS_NO_RETRY",
                       seq=final_seq, sha=final_sha, called=actual_calls)
    return verdict("ONE_MODEL_RESPONSE_UNTRUSTED_NO_PUBLICATION",
                   seq=final_seq, sha=final_sha, called=actual_calls,
                   untrusted_response=response)
