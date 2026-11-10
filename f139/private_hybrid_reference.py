"""Private Hybrid reference-only custody, not a worker authorization or transport.

The public FORGE boundary may describe *opaque hashes* of private artifacts,
never the candidate bytes or a credential. This strict contract cannot turn a
hash/metadata read into an owner signature, task, science, or execution grant.

Private artifact bytes must be read and checked by a separately qualified
private worker under the actual original-owner signed intent. Nothing here
reads a private repository, invokes a subprocess, or publishes a ticket.
"""
from __future__ import annotations

import hashlib
import json
import re

SCHEMA = "forge.f139.private-hybrid-payload-reference.v1"
PUBLIC_SCHEMA = "forge.f139.private-hybrid-public-identity.v1"
REPOSITORY = "spoonman136668-ai/TTT-Hybrid-Lab"
LANE = "TTT-Hybrid"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
PATH = re.compile(r"(?:scripts/native_[a-zA-Z0-9_]+|tests/test_native_[a-zA-Z0-9_]+)\.py\Z")
MAX_BYTES = 2048
FIELDS = frozenset({
    "schema", "lane", "repository", "controller_source_sha",
    "private_target_commit", "private_target_tree", "source_path",
    "before_sha256", "after_sha256", "private_payload_path",
    "private_payload_blob_sha", "private_payload_sha256",
    "owner_signed_intent_sha256", "owner_authorization_sha256",
    "scientific_first_use", "paid_api_calls", "accepted_ref_mutations",
})


class PrivateReferenceDenied(ValueError):
    pass


def need(value, why):
    if not value:
        raise PrivateReferenceDenied("F139_PRIVATE_HYBRID_REF_" + why)


def canonical(doc):
    return json.dumps(doc, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "DUPLICATE_FIELD")
        result[key] = value
    return result


def parse_reference(raw, *, owner_source_sha, private_commit, private_tree,
                    authenticated_repository_metadata):
    """Read-only identity check, with independently obtained source anchors.

    The caller must authenticate the source and repository metadata *before*
    invoking this validator. It does not check original owner signatures;
    `owner_*sha256` fields are only bindings for later independent validation.
    """
    need(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "BOUNDED_BYTES")
    try:
        value = json.loads(raw, object_pairs_hook=_unique)
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise PrivateReferenceDenied("F139_PRIVATE_HYBRID_REF_INVALID_JSON") from exc
    need(type(value) is dict and set(value) == FIELDS, "EXACT_FIELD_SET")
    need(raw == canonical(value), "CANONICAL_BYTES")
    need(value["schema"] == SCHEMA and value["lane"] == LANE
         and value["repository"] == REPOSITORY, "PRIVATE_TARGET_ONLY")
    md = authenticated_repository_metadata
    need(type(md) is dict and set(md) == {"full_name", "private"}
         and md["full_name"] == REPOSITORY and md["private"] is True,
         "AUTHENTICATED_PRIVATE_VISIBILITY_REQUIRED")
    for sha in (owner_source_sha, private_commit, private_tree):
        need(type(sha) is str and SHA40.fullmatch(sha) is not None,
             "AUTHENTICATED_SHA_INVALID")
    for field, anchor in (("controller_source_sha", owner_source_sha),
                          ("private_target_commit", private_commit),
                          ("private_target_tree", private_tree)):
        need(value[field] == anchor, "SOURCE_IDENTITY_DRIFT")
    need(type(value["source_path"]) is str
         and PATH.fullmatch(value["source_path"]) is not None,
         "NARROW_SOURCE_PATH")
    for field in ("before_sha256", "after_sha256", "private_payload_sha256",
                  "owner_signed_intent_sha256", "owner_authorization_sha256"):
        need(type(value[field]) is str
             and SHA64.fullmatch(value[field]) is not None, "DIGEST_INVALID")
    need(value["before_sha256"] != value["after_sha256"],
         "NO_SOURCE_CHANGE")
    need(type(value["private_payload_blob_sha"]) is str
         and SHA40.fullmatch(value["private_payload_blob_sha"]) is not None,
         "PRIVATE_GIT_BLOB_INVALID")
    need(value["private_payload_path"] ==
         "f139/private-native/" + value["private_payload_sha256"] + ".json",
         "PRIVATE_ARTIFACT_PATH_DRIFT")
    need(value["scientific_first_use"] is False
         and type(value["paid_api_calls"]) is int
         and value["paid_api_calls"] == 0
         and type(value["accepted_ref_mutations"]) is int
         and value["accepted_ref_mutations"] == 0,
         "EXECUTION_OR_SCIENCE_FORBIDDEN")
    return value


def public_identity(raw, *, owner_source_sha, private_commit, private_tree,
                    authenticated_repository_metadata):
    """Project only a revalidated reference; never echo private source bytes."""
    ref = parse_reference(raw, owner_source_sha=owner_source_sha,
                          private_commit=private_commit, private_tree=private_tree,
                          authenticated_repository_metadata=authenticated_repository_metadata)
    return {
        "schema": PUBLIC_SCHEMA,
        "lane": LANE,
        "reference_sha256": hashlib.sha256(canonical(ref)).hexdigest(),
        "controller_source_sha": ref["controller_source_sha"],
        "private_target_commit": ref["private_target_commit"],
        "scientific_first_use": False,
        "worker_authorized": False,
        "signed_worker_qualified": False,
    }

def verify_private_payload(ref_raw, payload_raw, *, owner_source_sha,
                           private_commit, private_tree,
                           authenticated_repository_metadata, provider_file):
    """Verify an existing private Git blob against the public hash reference.

    Caller MUST independently authenticate repository metadata and the
    provider_file tree/blob mapping with the private repository's OWN reader.
    This is an inert integrity check only. A hash named owner_* is NOT proof
    of the original owner's signature or worker authorization.
    """
    from f139.nci04_native_contract import (
        NativeContractError, parse_intent,
    )

    ref = parse_reference(ref_raw, owner_source_sha=owner_source_sha,
                          private_commit=private_commit, private_tree=private_tree,
                          authenticated_repository_metadata=authenticated_repository_metadata)
    need(type(payload_raw) is bytes and 0 < len(payload_raw) <= 60000,
         "PRIVATE_PAYLOAD_SIZE")
    need(hashlib.sha256(payload_raw).hexdigest() == ref["private_payload_sha256"],
         "PRIVATE_PAYLOAD_DIGEST_DRIFT")
    # Recompute Git blob SHA-1 as an identity cross-check, not as a substitute
    # for the SHA-256 payload digest or authenticated provider tree lookup.
    blob = hashlib.sha1(b"blob " + str(len(payload_raw)).encode("ascii") +
                        b"\0" + payload_raw).hexdigest()
    observed = provider_file
    need(type(observed) is dict and set(observed) == {
        "repository", "commit_sha", "tree_sha", "path", "git_blob_sha",
    } and observed["repository"] == REPOSITORY
         and observed["commit_sha"] == private_commit
         and observed["tree_sha"] == private_tree
         and observed["path"] == ref["private_payload_path"]
         and observed["git_blob_sha"] == ref["private_payload_blob_sha"]
         and observed["git_blob_sha"] == blob,
         "AUTHENTICATED_PRIVATE_BLOB_DRIFT")
    try:
        parsed = json.loads(payload_raw, object_pairs_hook=_unique)
        need(type(parsed) is dict and canonical(parsed) == payload_raw,
             "PRIVATE_PAYLOAD_NONCANONICAL")
        candidate = parse_intent(payload_raw, protected_main=owner_source_sha,
                                 target_commit=private_commit,
                                 target_tree_sha=private_tree)
    except (NativeContractError, UnicodeError, ValueError, TypeError) as exc:
        raise PrivateReferenceDenied("F139_PRIVATE_HYBRID_REF_NATIVE_INTENT_INVALID") from exc
    need(candidate.lane == LANE
         and candidate.path == ref["source_path"]
         and candidate.before_sha256 == ref["before_sha256"]
         and candidate.after_sha256 == ref["after_sha256"]
         and candidate.intent_sha256 == ref["owner_signed_intent_sha256"],
         "PRIVATE_INTENT_REFERENCE_MISMATCH")
    # Never expose candidate.after_bytes, after_base64 or private source paths
    # in the public projection or receipt. Owner-signature and execution
    # verification are explicitly outside this data-only gate.
    return {
        "schema": "forge.f139.private-hybrid-payload-integrity.v1",
        "reference_sha256": hashlib.sha256(ref_raw).hexdigest(),
        "private_payload_sha256": ref["private_payload_sha256"],
        "private_commit": private_commit,
        "owner_source_sha": owner_source_sha,
        "private_blob_integrity_verified": True,
        "owner_signature_verified": False,
        "signed_worker_qualified": False,
        "candidate_code_executed": False,
        "private_code_emitted": False,
        "scientific_first_use": False,
    }
