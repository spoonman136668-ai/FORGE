"""Compose existing V19 original-owner renewal custody, SOURCE-ONLY V21 candidate.

No live run_once import, task, scheduler, transport default, credential lookup,
queue, deployment or accepted-ref mutation. This module is deliberately
unreachable from the installed V20 owner. A separately authorized protected
release must bind it to the original owner after complete qualification.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from f139.local_controller import Database, SingleOwner
from f139.nci04_v19_research_renewal_shadow import day_value, LANES
from f139.nci04_v19_original_terminal_witness import project_original_native_terminal
from f139.nci04_v19_original_atomic_reserve_no_post import (
    original_attempts, combined_budget, reserve_original_intent_without_post,
)
from f139.nci04_v19_original_one_post_handoff import (
    custody_original_post_handoff_without_post,
)
from f139.nci04_v19_original_one_shot_free_send import (
    one_original_free_send_source_only,
)
from f139.nci04_v19_original_proposal_validation_custody import (
    validate_original_response_without_publication,
)
from f139.nci04_v19_original_publication_once import (
    publish_original_v19_candidate_once,
)


class RenewalCycleDenied(ValueError):
    """Missing original owner/source/explicit caller capability."""


def _report(disposition: str, *, lane: str | None = None,
            provider_calls: int = 0, draft_pr: int | None = None) -> dict:
    # No raw response, public model output, token, source bytes or HMAC.
    return {
        "schema": "forge.f139.v21.source-only-renewal-composition.v1",
        "disposition": disposition, "lane": lane,
        "provider_calls_this_invocation": provider_calls,
        "draft_pr_number": draft_pr, "paid_model_calls": 0,
        "worker_dispatched": False, "scientific_first_use": False,
        "accepted_ref_mutations": 0, "runtime_activated": False,
    }


def run_original_renewal_source_only(
    db: Database, *, utc_day: str,
    packet_for_terminal: Callable[[dict], dict],
    public_reader: Callable[[str], dict],
    original_get: Callable[[str], object],
    original_write: Callable[[str, str, dict], object],
    owner_witness: Callable[[], bool],
    token: str,
    transport: Callable[[bytes, str], bytes],
) -> dict:
    """At most one V19-style original terminal -> draft cycle, no live hook.

    Callers must have independently established the original SingleOwner,
    canonical imported Database and source identity. ALL V19 original-ledger
    verifier, exact-predecessor, no-replay, quota and provider checks still
    execute in their existing modules. A release SHA/UTC rollover alone cannot
    renew an attempt. Never invoke this source candidate against live SQLite
    until a separate guarded original-owner release/acceptance authorizes it.
    """
    if (type(db) is not Database
            or not isinstance(getattr(db, "filename", None), Path)
            or not SingleOwner.held(db.filename.with_suffix(".lock"))
            or not callable(owner_witness) or owner_witness() is not True
            or not all(callable(x) for x in (
                packet_for_terminal, public_reader,
                original_get, original_write, transport))
            or type(token) is not str or not token.strip()
            or "\r" in token or "\n" in token or len(token) > 2048):
        raise RenewalCycleDenied("F139_V21_ORIGINAL_OWNER_OR_EXPLICIT_CAPABILITY_REQUIRED")
    day_value(utc_day)
    db.verify()
    pre = db.meta()
    if (pre["enabled"] != 1 or pre["legacy_suspended"] != 1
            or db.ready() is not None or db.actives()):
        return _report("BLOCKED_ORIGINAL_OWNER_NOT_QUIESCENT")
    # Legacy FREE_REASONER_ATTEMPTED remains spent. The new rolling 30-day
    # admission is independent; it is not an extension of lifetime-8.
    attempts = original_attempts(db)
    selected = None
    budget_exhausted_lane = None
    for lane in LANES:
        witness = project_original_native_terminal(
            db, lane=lane, utc_day=utc_day,
            hypothetical_v19_attempts=attempts)
        if witness["disposition"] != (
                "AUTHENTIC_FRESH_TERMINAL_SHADOW_ONLY_NOT_AUTHORIZED"):
            continue
        if (not isinstance(witness.get("shadow"), dict)
                or witness["shadow"].get("disposition") !=
                    "ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED"):
            continue
        if not combined_budget(db, attempts, lane, utc_day):
            # One lane's spent daily slot must not starve a separately
            # eligible native lane; still use the same original ledger.
            budget_exhausted_lane = lane
            continue
        selected = (lane, witness)
        break
    if selected is None:
        if budget_exhausted_lane is not None:
            return _report("BLOCKED_ORIGINAL_PLUS_RENEWAL_ROLLING_BUDGET",
                           lane=budget_exhausted_lane)
        # An old terminal, including V20 seq330 followed by model attempts
        # seq331/332, may NEVER be re-purchased by changing source or time.
        return _report("BLOCKED_NO_FRESH_ELIGIBLE_NATIVE_TERMINAL")
    lane, witness = selected
    # Build only an authenticated public-source proposal packet; underlying
    # V19 handoff/send independently authenticate exact public source bytes.
    packet = packet_for_terminal(witness)
    if (type(packet) is not dict or packet.get("lane") != lane):
        raise RenewalCycleDenied("F139_V21_PUBLIC_PACKET_LANE_INVALID")
    if (db.meta() != pre or owner_witness() is not True):
        return _report("BLOCKED_OWNER_ORIGINAL_STATE_MOVED", lane=lane)
    reserved = reserve_original_intent_without_post(
        db, lane=lane, utc_day=utc_day, owner_witness=owner_witness)
    if reserved["disposition"] != "ORIGINAL_ATOMIC_INTENT_COMMITTED_NO_POST":
        return _report(reserved["disposition"], lane=lane)
    handoff = custody_original_post_handoff_without_post(
        db, reservation_seq=reserved["original_request_attempt_event_seq"],
        reservation_sha256=reserved["original_request_attempt_event_sha256"],
        public_packet=packet, public_reader=public_reader,
        utc_day=utc_day, owner_witness=owner_witness)
    if handoff["disposition"] != "ORIGINAL_POST_HANDOFF_SPENT_NO_POST":
        return _report(handoff["disposition"], lane=lane)
    sent = one_original_free_send_source_only(
        db, handoff_seq=handoff["original_post_handoff_event_seq"],
        handoff_sha256=handoff["original_post_handoff_event_sha256"],
        public_packet=packet, public_reader=public_reader,
        owner_witness=owner_witness, token=token, transport=transport)
    calls = sent.get("provider_calls_in_this_invocation", 0)
    if sent["disposition"] != "ONE_MODEL_RESPONSE_UNTRUSTED_NO_PUBLICATION":
        return _report(sent["disposition"], lane=lane, provider_calls=calls)
    validated = validate_original_response_without_publication(
        db, send_receipt=sent, public_packet=packet,
        owner_witness=owner_witness)
    if validated["disposition"] != "ORIGINAL_PROPOSAL_VALIDATED_DATA_ONLY":
        return _report(validated["disposition"], lane=lane, provider_calls=calls)
    # Only the existing verified bounded writer can publish an owner DRAFT.
    # Neither this composition nor a model response accepts the candidate.
    published = publish_original_v19_candidate_once(
        db, validation_seq=validated["validation_event_seq"],
        validation_sha256=validated["validation_event_sha256"],
        candidate_source=validated["candidate"]["candidate_source"],
        public_packet=packet, original_get=original_get,
        public_reader=public_reader, original_write=original_write,
        owner_witness=owner_witness)
    return _report(published["disposition"], lane=lane, provider_calls=calls,
                   draft_pr=published.get("pr_number"))
