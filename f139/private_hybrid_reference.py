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


def public_identity(qualified_reference):
    """Only a digest and target *identity*; never serialize private payload."""
    need(type(qualified_reference) is dict
         and set(qualified_reference) == FIELDS
         and qualified_reference.get("schema") == SCHEMA,
         "VALIDATED_REFERENCE_REQUIRED")
    return {
        "schema": PUBLIC_SCHEMA,
        "lane": LANE,
        "reference_sha256": hashlib.sha256(canonical(qualified_reference)).hexdigest(),
        "controller_source_sha": qualified_reference["controller_source_sha"],
        "private_target_commit": qualified_reference["private_target_commit"],
        "scientific_first_use": False,
        "worker_authorized": False,
        "signed_worker_qualified": False,
    }
