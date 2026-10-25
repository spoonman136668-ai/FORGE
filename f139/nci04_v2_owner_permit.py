"""G31: isolated owner-issued, version-bound V2 developmental permit.

No controller, GitHub API, worker CLI, database or remote first-use wiring.
This permits a future original-owner *pre-dispatch* signer to distinguish V2
semantics from previously consumed V1 native work. It does not dispatch work.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_worker_v2 import (
    SOURCE_SHA, SOURCE_TREE, RECEIPT_SCHEMA,
)

SCHEMA = "forge.f139.nci04.owner-execution-v2-permit.v1"
DOMAIN = b"FORGE-F139-NCI04-OWNER-EXECUTION-V2\0"
FIRST_NEW_EVENT = 220
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
TICKET = re.compile(r"f139-nci04-i[1-9][0-9]*-[a-f0-9]{12}-[a-f0-9]{8}\Z")
OUTER_FIELDS = frozenset(("schema", "binding", "hmac_sha256"))
BINDING_FIELDS = frozenset((
    "schema", "ticket", "lane", "source_sha",
    "owner_epoch", "original_admission_event_seq",
    "original_admission_event_sha256", "original_admission_event_kind",
    "provider_run_id", "runner_os", "issue_number", "issue_id",
    "native_intent_sha256", "qualification_key", "target_commit",
    "target_tree_sha", "native_path", "candidate_sha256",
    "original_v1_authorization_sha256", "receipt_protocol",
    "scientific_first_use_authorized", "accepted_ref_mutations",
    "paid_model_calls",
))


class V2OwnerPermitDenied(ValueError):
    pass


def require(value: bool, reason: str) -> None:
    if not value:
        raise V2OwnerPermitDenied("F139_G31_" + reason)


def _owner_key(value: str) -> bytes:
    require(type(value) is str and len(value) >= 32
            and len(value) <= 4096, "OWNER_KEY_INVALID")
    return value.encode("utf-8", "strict")


def _binding(admission: NativeAdmission, *, epoch: int,
             admission_event_seq: int, admission_event_sha256: str,
             authenticated_source_sha: str) -> dict:
    """Bind a NEW historical admission event, not merely a V1 signature.

    Caller must independently authenticate the original owner SQLite event,
    signed native issue, live owner source and provider run/OS. This function
    validates shapes and equality; it cannot itself attest SQLite custody.
    """
    require(isinstance(admission, NativeAdmission),
            "ORIGINAL_SIGNED_ADMISSION_REQUIRED")
    c = admission.intent
    require(c.lane == admission.lane == "Yggdrasil"
            and c.target_commit == SOURCE_SHA
            and c.target_tree_sha == SOURCE_TREE
            and c.path == "yggdrasil/public_causal_cells.py"
            and isinstance(c.intent_sha256, str)
            and SHA64.fullmatch(c.intent_sha256) is not None
            and isinstance(c.qualification_key, str)
            and SHA64.fullmatch(c.qualification_key) is not None
            and isinstance(c.after_sha256, str)
            and SHA64.fullmatch(c.after_sha256) is not None,
            "V2_NATIVE_CANDIDATE_IDENTITY_INVALID")
    require(type(epoch) is int and 0 < epoch < 2**31
            and type(admission_event_seq) is int
            and admission_event_seq > FIRST_NEW_EVENT
            and isinstance(admission_event_sha256, str)
            and SHA64.fullmatch(admission_event_sha256) is not None,
            "NEW_ORIGINAL_OWNER_EVENT_REQUIRED")
    require(isinstance(authenticated_source_sha, str)
            and SHA40.fullmatch(authenticated_source_sha) is not None
            and admission.source_sha == authenticated_source_sha
            and isinstance(admission.authorization_sha256, str)
            and SHA64.fullmatch(admission.authorization_sha256) is not None,
            "ORIGINAL_OWNER_SOURCE_OR_AUTH_DRIFT")
    require(isinstance(admission.ticket, str)
            and TICKET.fullmatch(admission.ticket) is not None
            and type(admission.issue_number) is int
            and 0 < admission.issue_number < 2**31
            and type(admission.issue_id) is int
            and admission.issue_id > 0
            and admission.ticket ==
                ("f139-nci04-i" + str(admission.issue_number) + "-"
                 + authenticated_source_sha[:12] + "-"
                 + c.intent_sha256[:8]),
            "ORIGINAL_NATIVE_TICKET_OR_ISSUE_INVALID")
    require(type(admission.run_id) is int and admission.run_id > 0
            and admission.runner_os in ("ubuntu-latest", "windows-latest"),
            "PROVIDER_RUN_OR_OS_INVALID")
    return {
        "schema": SCHEMA,
        "ticket": admission.ticket,
        "lane": admission.lane,
        "source_sha": authenticated_source_sha,
        "owner_epoch": epoch,
        "original_admission_event_seq": admission_event_seq,
        "original_admission_event_sha256": admission_event_sha256,
        "original_admission_event_kind": "NATIVE_DEVELOPMENT_ADMITTED",
        "provider_run_id": admission.run_id,
        "runner_os": admission.runner_os,
        "issue_number": admission.issue_number,
        "issue_id": admission.issue_id,
        "native_intent_sha256": c.intent_sha256,
        "qualification_key": c.qualification_key,
        "target_commit": c.target_commit,
        "target_tree_sha": c.target_tree_sha,
        "native_path": c.path,
        "candidate_sha256": c.after_sha256,
        "original_v1_authorization_sha256": admission.authorization_sha256,
        "receipt_protocol": RECEIPT_SCHEMA,
        "scientific_first_use_authorized": False,
        "accepted_ref_mutations": 0,
        "paid_model_calls": 0,
    }


def issue_v2_owner_permit(admission: NativeAdmission, *, owner_key: str,
                          epoch: int, admission_event_seq: int,
                          admission_event_sha256: str,
                          authenticated_source_sha: str) -> bytes:
    """Owner-only deterministic constructor; never invoke inside candidate worker."""
    key = _owner_key(owner_key)
    bound = _binding(
        admission, epoch=epoch,
        admission_event_seq=admission_event_seq,
        admission_event_sha256=admission_event_sha256,
        authenticated_source_sha=authenticated_source_sha)
    signature = hmac.new(key, DOMAIN + canonical(bound),
                         hashlib.sha256).hexdigest()
    raw = canonical({
        "schema": SCHEMA, "binding": bound, "hmac_sha256": signature})
    require(len(raw) <= 8192, "PERMIT_OVERSIZE")
    return raw


def _unique(pairs):
    result = {}
    for name, value in pairs:
        require(name not in result, "DUPLICATE_JSON_FIELD")
        result[name] = value
    return result


def verify_v2_owner_permit(raw: bytes, admission: NativeAdmission, *,
                           owner_key: str, epoch: int,
                           admission_event_seq: int,
                           admission_event_sha256: str,
                           authenticated_source_sha: str) -> dict:
    """Verify distinct V2 HMAC against independently authenticated owner inputs.

    This executes ONLY in a privileged original-owner/authorization context.
    The candidate worker must never receive owner_key or treat this dict as
    independent proof of an actual owner event or provider result.
    """
    key = _owner_key(owner_key)
    require(type(raw) is bytes and 0 < len(raw) <= 8192,
            "PERMIT_BYTES_INVALID")
    try:
        value = json.loads(raw, object_pairs_hook=_unique)
    except V2OwnerPermitDenied:
        # Preserve the precise fail-closed duplicate-key diagnostic.
        raise
    except (ValueError, UnicodeError) as exc:
        raise V2OwnerPermitDenied("F139_G31_PERMIT_JSON_INVALID") from exc
    require(isinstance(value, dict) and set(value) == OUTER_FIELDS
            and value["schema"] == SCHEMA
            and isinstance(value["binding"], dict)
            and set(value["binding"]) == BINDING_FIELDS
            and type(value["hmac_sha256"]) is str
            and SHA64.fullmatch(value["hmac_sha256"]) is not None
            and canonical(value) == raw,
            "VERSION_OR_NONCANONICAL_PERMIT")
    bound = _binding(
        admission, epoch=epoch,
        admission_event_seq=admission_event_seq,
        admission_event_sha256=admission_event_sha256,
        authenticated_source_sha=authenticated_source_sha)
    require(value["binding"] == bound, "ORIGINAL_OWNER_BINDING_CHANGED")
    expected = hmac.new(key, DOMAIN + canonical(bound),
                        hashlib.sha256).hexdigest()
    require(hmac.compare_digest(expected, value["hmac_sha256"]),
            "V2_HMAC_MISMATCH")
    return {
        "schema": SCHEMA,
        "verified_binding_sha256": digest(canonical(bound)),
        "verified_permit_sha256": digest(raw),
        "source_sha": authenticated_source_sha,
        "original_admission_event_seq": admission_event_seq,
        "signed_v2_only": True,
        "original_event_custody_independently_verified": False,
        "worker_dispatched": False,
        "scientific_first_use_authorized": False,
    }
