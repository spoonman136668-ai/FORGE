"""R12-E cold original-issuance attestation; credentialed and READ ONLY.

Verifies original R11 reservation, original R12-C lifetime-one spend, exact
signed R12-B candidate and the authenticated GitHub job on the sole
original-owner SQLite state. No worker ticket, secret, run, source mutation,
queued work, signed deployment, or scientific first-use leaves this function.
"""
from __future__ import annotations

import hashlib
import hmac
import json

from f139.local_controller import canonical
from f139.rsi_r12_candidate_binding import original_owner_database
from f139.rsi_r12b_signed_job import (
    validate_credentialed, sha64, SignedDevelopmentDenied,
)
from f139.rsi_r12c_original_spend import KIND, audit_issuance, OriginalIssueDenied

SCHEMA = "forge.f139.rsi-r12e.credentialed-original-issued-readonly.v1"


class AuthorizationDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise AuthorizationDenied("F139_RSI_R12E_" + reason)


def attest_original_issuance(
        *, db, candidate, owner_source_sha: str, intent: dict,
        signature: str, signing_key: str,
        authenticated_main_sha: str, authenticated_main_tree_sha: str,
        authenticated_run_id: int, authenticated_job_id: int,
        authenticated_attempt: int, authenticated_event: str,
        authenticated_repository: str, authenticated_workflow: str,
        authenticated_runner_os: str) -> dict:
    """Verify consumed issuance under original ledger custody, no authority.

    External GitHub job inputs MUST be independently authenticated by
    the calling original owner. This receipt is not a transferable permit:
    no signature, signing key or credential is returned.
    """
    need(original_owner_database(db), "NOT_ORIGINAL_DATABASE")
    before = db.meta()["head_hash"]
    try:
        db.verify()
        issued = audit_issuance(db)
    except (ValueError, TypeError, KeyError, OriginalIssueDenied) as exc:
        raise AuthorizationDenied(
            "F139_RSI_R12E_ORIGINAL_LEDGER_UNVERIFIED") from exc
    need(len(issued) == 1, "LIFETIME_ISSUANCE_MISSING_OR_DUPLICATE")
    event = issued[0]
    need(type(event) is dict and type(intent) is dict
         and type(signature) is str and sha64(signature)
         and event["intent"] == intent
         and event["owner_source_sha"] == owner_source_sha
         and event["intent_sha256"] == hashlib.sha256(
             canonical(intent)).hexdigest()
         and event["signature_sha256"] == hashlib.sha256(
             signature.encode("ascii")).hexdigest(),
         "ORIGINAL_ISSUANCE_BINDING_DRIFT")
    try:
        verified = validate_credentialed(
            db=db, candidate=candidate, owner_source_sha=owner_source_sha,
            intent=intent, signature=signature, signing_key=signing_key,
            authenticated_main_sha=authenticated_main_sha,
            authenticated_main_tree_sha=authenticated_main_tree_sha,
            authenticated_run_id=authenticated_run_id,
            authenticated_job_id=authenticated_job_id,
            authenticated_attempt=authenticated_attempt,
            authenticated_event=authenticated_event,
            authenticated_repository=authenticated_repository,
            authenticated_workflow=authenticated_workflow,
            authenticated_runner_os=authenticated_runner_os,
        )
    except (SignedDevelopmentDenied, ValueError, TypeError, KeyError) as exc:
        raise AuthorizationDenied(
            "F139_RSI_R12E_SIGNED_PROVIDER_SOURCE_UNVERIFIED") from exc
    need(verified["cryptographic_validation_passed"] is True
         and verified["original_lifetime_spend_verified"] is False
         and verified["credential_free_worker_admitted"] is False,
         "ORIGINAL_NO_EXECUTION_INVARIANT")
    rows = list(db.conn.execute(
        "SELECT seq,payload,sha FROM events WHERE kind=? ORDER BY seq",
        (KIND,)))
    need(len(rows) == 1 and type(rows[0]["sha"]) is str
         and sha64(rows[0]["sha"])
         and json.loads(rows[0]["payload"]) == event,
         "ORIGINAL_ISSUANCE_EVENT_DRIFT")
    need(db.meta()["head_hash"] == before,
         "ORIGINAL_LEDGER_CHANGED_DURING_READ")
    return {
        "schema": SCHEMA,
        "owner_source_sha": owner_source_sha,
        "original_issuance_event_sha256": rows[0]["sha"],
        "original_issuance_seq": rows[0]["seq"],
        "original_reservation_event_sha256":
            event["reservation_event_sha256"],
        "candidate_binding_sha256": event["binding_sha256"],
        "intent_sha256": event["intent_sha256"],
        "signature_sha256": event["signature_sha256"],
        "original_lifetime_spend_verified": True,
        "credentialed_signature_verification_passed": True,
        "credential_free_worker_admitted": False,
        "worker_dispatched": False,
        "source_regression_qualified": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
    }
