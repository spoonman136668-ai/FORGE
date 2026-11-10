"""Credentialed-side Hybrid HMAC/payload binding (inert, not a worker).

This is a compose-only verifier for the *existing* F139 two-part HMAC
protocol, not a new signer. It must run only on the credentialed original-owner
side, NEVER inside a private-code sandbox. GitHub source and blob observations
must be independently authenticated by the project's native provider before
being supplied to this function. No Git, subprocess, secret retrieval, remote
write, ticket issuance, worker execution, or original SQLite mutation occurs.

Passing synthetic tests proves only the binding algorithm. A real original
owner ticket and independently authenticated private payload readback are
separately required before any operational claim.
"""
from __future__ import annotations

import hashlib

from f139.nci04_signed_native import admit_native_intent
from f139.private_hybrid_reference import (
    LANE, PrivateReferenceDenied, parse_reference, verify_private_payload,
)


class PrivateOwnerBindingDenied(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise PrivateOwnerBindingDenied("F139_PRIVATE_HYBRID_OWNER_" + why)


def verify_credentialed_owner_binding(
    reference_raw, private_payload_raw, *,
    original_ticket_inputs, native_signature, issue_number, issue_id,
    issue_body_sha256, owner_source_sha, private_commit, private_tree,
    authenticated_repository_metadata, provider_file,
):
    """Bind the existing real HMAC verifier to the *same* private payload.

    original_ticket_inputs may contain the owner's HMAC secret: the caller
    must remain inside the existing credentialed authorization compartment.
    This function returns no token, candidate code, private file path, secret,
    private patch, job instruction, or execution authority.
    """
    need(type(original_ticket_inputs) is dict and
         type(reference_raw) is bytes and type(private_payload_raw) is bytes,
         "INPUT_SHAPE")
    # Only the existing verifier can authenticate BOTH the F139 owner ticket
    # and the domain-separated native intent. Never accept caller-supplied
    # NativeAdmission JSON or a bare SHA as evidence of a real signature.
    admission = admit_native_intent(
        original_ticket_inputs, private_payload_raw,
        native_signature=native_signature,
        issue_number=issue_number, issue_id=issue_id,
        issue_body_sha256=issue_body_sha256,
        authenticated_main_sha=owner_source_sha,
        authenticated_target_commit=private_commit,
        authenticated_target_tree=private_tree,
    )
    need(admission.lane == LANE and admission.intent.lane == LANE
         and admission.source_sha == owner_source_sha,
         "SIGNED_LANE_OR_SOURCE_DRIFT")

    reference = parse_reference(
        reference_raw, owner_source_sha=owner_source_sha,
        private_commit=private_commit, private_tree=private_tree,
        authenticated_repository_metadata=authenticated_repository_metadata,
    )
    need(reference["owner_authorization_sha256"] == admission.authorization_sha256,
         "OWNER_AUTHORIZATION_BINDING_DRIFT")
    need(reference["owner_signed_intent_sha256"] ==
         admission.intent.intent_sha256, "OWNER_INTENT_BINDING_DRIFT")
    need(reference["source_path"] == admission.intent.path and
         reference["before_sha256"] == admission.intent.before_sha256 and
         reference["after_sha256"] == admission.intent.after_sha256,
         "SIGNED_PATCH_BINDING_DRIFT")

    # This independently hashes actual private payload bytes but cannot by
    # itself prove the caller's provider_file mapping is genuine. The provider
    # mapping must already have been authenticated inside the private project.
    integrity = verify_private_payload(
        reference_raw, private_payload_raw,
        owner_source_sha=owner_source_sha,
        private_commit=private_commit, private_tree=private_tree,
        authenticated_repository_metadata=authenticated_repository_metadata,
        provider_file=provider_file,
    )
    need(integrity["private_blob_integrity_verified"] is True and
         integrity["owner_signature_verified"] is False and
         integrity["signed_worker_qualified"] is False and
         integrity["private_payload_sha256"] == admission.intent.intent_sha256,
         "PRIVATE_PAYLOAD_OR_AUTHORITY_DRIFT")
    return {
        "schema": "forge.f139.private-hybrid-credentialed-binding.v1",
        "reference_sha256": hashlib.sha256(reference_raw).hexdigest(),
        "private_payload_sha256": admission.intent.intent_sha256,
        "owner_source_sha": owner_source_sha,
        "private_target_commit": private_commit,
        "private_target_tree": private_tree,
        "ticket": admission.ticket,
        "issue_number": admission.issue_number,
        "issue_id": admission.issue_id,
        "authorization_binding_sha256": admission.authorization_sha256,
        # This records only a cryptographic match to the provided original
        # key. Proof of the *live* original owner requires a real issued ticket,
        # its independent ledger and the provider's authentic source.
        "provided_owner_hmac_pair_matched": True,
        "private_blob_bytes_matched": True,
        "original_owner_live_issue_verified": False,
        "private_worker_executed": False,
        "signed_worker_qualified": False,
        "owner_schema_migrated": False,
        "scientific_first_use": False,
        "gpu_used": False,
    }
