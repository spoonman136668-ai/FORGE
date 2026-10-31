"""H35 inert preimage for a future original-owner model-free provenance signature.

This module never signs anything, reads an owner key/SQLite/provider, performs
a Git write, dispatches work or grants scientific acceptance. Every field here
is *caller-supplied* and must be independently authenticated by the existing
owner. An offline HMAC comparison proves ONLY that the supplied key matches
the supplied preimage; it cannot attest that the key belongs to that owner.
"""
from __future__ import annotations

import hashlib
import hmac
import re

from f139.nci04_model_free_frontier import (
    FrontierDenied, canonical, verify_proposal,
)

SCHEMA = "forge.f139.model-free-frozen-lineage-preimage.v1"
DOMAIN = b"F139-NCI04-MODEL-FREE-FROZEN-LINEAGE-V1\n"
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
OWNER_FIELDS = frozenset({
    "source_sha", "owner_epoch", "native_ticket", "issue_number",
    "issue_id", "issue_body_sha256", "ledger_head_seq",
    "ledger_head_sha256", "ledger_history_sha256", "ledger_history_count",
})
NATIVE_FIELDS = frozenset({
    "intent_sha256", "qualification_key", "native_authorization_sha256",
})
FROZEN_FIELDS = frozenset({
    "seeds_sha256", "resource_budget_sha256", "evaluation_controls_sha256",
    "preregistration_sha256",
})


class ProvenanceDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise ProvenanceDenied("F139_H35_" + reason)


def is64(value: object) -> bool:
    return type(value) is str and HEX64.fullmatch(value) is not None


def make_unsigned_preimage(*, proposal: dict, owner: dict,
                           native: dict, frozen: dict) -> bytes:
    """Return one immutable, domain-separated record, NOT an owner signature.

    This structural encoder cannot establish the correctness/completeness of
    original owner history, first-use provenance or frozen source identities.
    """
    need(type(proposal) is dict and type(owner) is dict
         and type(native) is dict and type(frozen) is dict,
         "RECORD_TYPES")
    need(set(owner) == OWNER_FIELDS and set(native) == NATIVE_FIELDS
         and set(frozen) == FROZEN_FIELDS, "RECORD_FIELDS")
    try:
        checked = verify_proposal(proposal, owner["source_sha"])
    except (FrontierDenied, KeyError, TypeError) as exc:
        raise ProvenanceDenied("F139_H35_PROPOSAL_NOT_FROZEN") from exc
    need(all(is64(owner[k]) for k in (
        "issue_body_sha256", "ledger_head_sha256", "ledger_history_sha256"))
        and all(is64(native[k]) for k in NATIVE_FIELDS)
        and all(is64(frozen[k]) for k in FROZEN_FIELDS),
        "DIGEST_INVALID")
    need(type(owner["owner_epoch"]) is int and owner["owner_epoch"] > 0
         and type(owner["issue_number"]) is int and owner["issue_number"] > 0
         and type(owner["issue_id"]) is int and owner["issue_id"] > 0
         and type(owner["ledger_head_seq"]) is int and owner["ledger_head_seq"] > 0
         and type(owner["ledger_history_count"]) is int
         and 0 <= owner["ledger_history_count"] <= owner["ledger_head_seq"],
         "OWNER_EVENT_METADATA_INVALID")
    expected_ticket = (
        f'f139-nci04-i{owner["issue_number"]}-'
        f'{owner["source_sha"][:12]}-{native["intent_sha256"][:8]}'
    )
    need(type(owner["native_ticket"]) is str
         and owner["native_ticket"] == expected_ticket,
         "OWNER_TICKET_NOT_BOUND")
    record = {
        "schema": SCHEMA,
        "proposal": proposal,
        "candidate_identity": checked["candidate_identity"],
        "owner": owner,
        "native": native,
        "frozen": frozen,
        # Non-elevatable boundaries embedded inside the preimage.
        "development_only": True,
        "scientific_first_use": False,
        "owner_identity_authenticated": False,
        "owner_ledger_completeness_authenticated": False,
        "native_worker_authorized": False,
        "dispatch_authorized": False,
        "publication_authorized": False,
        "scientific_acceptance_authorized": False,
    }
    preimage = DOMAIN + canonical(record)
    need(0 < len(preimage) <= 32768, "PREIMAGE_SIZE")
    return preimage


def verify_detached_mac_math_only(
    *, preimage: bytes, expected_preimage: bytes,
    detached_mac_hex: str, verification_key: bytes,
) -> dict:
    """Test a detached MAC without authenticating the original owner.

    The caller must independently source and authenticate the verification key.
    A matching HMAC NEVER signs a live owner action, accepts science, or grants
    dispatch/publication. This module deliberately has no sign or publish API.
    """
    need(type(preimage) is bytes and type(expected_preimage) is bytes
         and len(preimage) <= 32768
         and preimage.startswith(DOMAIN) and preimage == expected_preimage,
         "PREIMAGE_NOT_INDEPENDENTLY_PINNED")
    need(type(verification_key) is bytes and len(verification_key) >= 32
         and is64(detached_mac_hex), "MAC_INPUT_INVALID")
    actual = hmac.new(verification_key, preimage, hashlib.sha256).hexdigest()
    need(hmac.compare_digest(actual, detached_mac_hex), "MAC_MISMATCH")
    return {
        "schema": "forge.f139.model-free-detached-mac-math-only.v1",
        "mac_mathematically_matches_supplied_key": True,
        "original_owner_authenticated": False,
        "ledger_completeness_authenticated": False,
        "native_qualification_accepted": False,
        "scientific_first_use": False,
        "publication_authorized": False,
        "dispatch_authorized": False,
        "signed_owner_provenance_accepted": False,
    }
