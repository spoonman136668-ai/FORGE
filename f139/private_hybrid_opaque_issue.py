"""Private-safe Hybrid issue commitment, never public source or admission.

The existing public native issue format contains intent_base64 / after_base64
and is categorically forbidden for private TTT-Hybrid payloads. This
alternative issue body is only a typed public commitment to an already-stored
private project-owned Git blob. It omits source bytes, mutable refs, the final
reference digest and owner authorization fields.

Sequencing is essential: (1) private provider owns/stores canonical intent,
(2) public source-free issue with that intent's hash is created by the
ORIGINAL owner, (3) original credentialed owner signs the issue body's digest,
(4) final private reference adds the owner authorization digest. Putting that
*final* reference digest in step (2) creates a circular HMAC dependency.

All functions are read-only, do not mint tickets into an original owner ledger,
make network calls, sign credentials, mutate refs, or execute candidate code.
Authentication of repository/blob observations and original owner admission
must take place in independent original compartments first.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from f139.private_hybrid_reference import (
    LANE, REPOSITORY, canonical, parse_reference,
)

SCHEMA = "forge.f139.private-hybrid-owner-issue-commitment.v1"
KIND = "private-native-reference-only"
LABEL = "f139-private-native-reference-eligible"
LEGACY_LABELS = frozenset({
    "f139-native-development-eligible", "f139-development-eligible",
})
OWNER = "spoonman136668-ai"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
UINT = re.compile(r"[1-9][0-9]*\Z")
FIELDS = frozenset({
    "schema", "kind", "lane", "source_sha", "repository",
    "private_target_commit", "private_target_tree",
    "private_payload_commit", "private_payload_tree",
    "private_payload_sha256", "private_payload_blob_sha",
    "scientific_first_use", "paid_model_calls", "accepted_ref_mutations",
})
MAX_BODY = 2048


class PrivateOpaqueIssueDenied(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise PrivateOpaqueIssueDenied("F139_PRIVATE_HYBRID_ISSUE_" + why)


def unique(pairs):
    doc = {}
    for k, v in pairs:
        need(k not in doc, "DUPLICATE_PUBLIC_FIELD")
        doc[k] = v
    return doc


@dataclass(frozen=True)
class PrivateOpaqueIssue:
    number: int
    issue_id: int
    ticket: str
    source_sha: str
    issue_body_sha256: str
    private_target_commit: str
    private_target_tree: str
    private_payload_commit: str
    private_payload_tree: str
    private_payload_sha256: str
    private_payload_blob_sha: str


def inspect_private_opaque_issue(raw, *, owner_source_sha,
                                 authenticated_repository_metadata,
                                 authenticated_target_commit,
                                 authenticated_target_tree,
                                 authenticated_storage_file):
    """Verify a source-free issue against independent provider observations.

    raw must be the authenticated GitHub Issue API response. The private
    project must separately attest exact commit/tree/path/blob via its own
    provider; an issue-controlled dictionary is not a provider attestation.
    A passing result is still NOT proof of a real owner-created task.
    """
    need(type(raw) is dict and raw.get("state") == "open"
         and "pull_request" not in raw
         and type(raw.get("number")) is int and raw["number"] > 0
         and type(raw.get("id")) is int and raw["id"] > 0
         and type(raw.get("user")) is dict
         and raw["user"].get("login") == OWNER
         and raw.get("author_association") == "OWNER",
         "AUTHENTIC_ISSUE_OWNER_REQUIRED")
    labels = raw.get("labels")
    need(type(labels) is list and all(
         type(x) is dict and type(x.get("name")) is str for x in labels),
         "ISSUE_LABELS_INVALID")
    names = [x["name"] for x in labels]
    need(len(names) == len(set(names)) and LABEL in names
         and not LEGACY_LABELS.intersection(names),
         "PRIVATE_KIND_MIXED_WITH_PUBLIC_NATIVE")
    body = raw.get("body")
    need(type(body) is str and 0 < len(body) <= MAX_BODY
         and body.isascii(), "PUBLIC_BODY_BOUNDED_ASCII")
    try:
        doc = json.loads(body, object_pairs_hook=unique)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise PrivateOpaqueIssueDenied(
            "F139_PRIVATE_HYBRID_ISSUE_PUBLIC_JSON_INVALID") from exc
    need(type(doc) is dict and set(doc) == FIELDS
         and body.encode("ascii") == canonical(doc),
         "PUBLIC_BODY_CANONICAL_ONLY")
    need(doc["schema"] == SCHEMA and doc["kind"] == KIND
         and doc["lane"] == LANE and doc["repository"] == REPOSITORY
         and type(owner_source_sha) is str and SHA40.fullmatch(owner_source_sha)
         and doc["source_sha"] == owner_source_sha,
         "PUBLIC_ISSUE_KIND_SOURCE_DRIFT")
    md = authenticated_repository_metadata
    need(type(md) is dict and set(md) == {"full_name", "private"}
         and md["full_name"] == REPOSITORY and md["private"] is True,
         "PRIVATE_PROVIDER_REPOSITORY_REQUIRED")
    for key, target in (
        ("private_target_commit", authenticated_target_commit),
        ("private_target_tree", authenticated_target_tree),
    ):
        need(type(target) is str and SHA40.fullmatch(target)
             and doc[key] == target,
             "AUTHENTIC_TARGET_COMMIT_TREE_REQUIRED")
    for key in ("private_payload_commit", "private_payload_tree"):
        need(type(doc[key]) is str and SHA40.fullmatch(doc[key]),
             "PRIVATE_STORAGE_SHA_INVALID")
    for key in ("private_payload_sha256",):
        need(type(doc[key]) is str and SHA64.fullmatch(doc[key]),
             "PRIVATE_PAYLOAD_DIGEST_INVALID")
    need(type(doc["private_payload_blob_sha"]) is str
         and SHA40.fullmatch(doc["private_payload_blob_sha"]),
         "PRIVATE_GIT_BLOB_INVALID")
    need(doc["scientific_first_use"] is False
         and type(doc["paid_model_calls"]) is int
         and doc["paid_model_calls"] == 0
         and type(doc["accepted_ref_mutations"]) is int
         and doc["accepted_ref_mutations"] == 0,
         "SCIENCE_OR_REF_AUTHORITY_FORBIDDEN")
    observed = authenticated_storage_file
    need(type(observed) is dict and set(observed) == {
        "repository", "commit_sha", "tree_sha", "path", "git_blob_sha",
    } and observed["repository"] == REPOSITORY
         and observed["commit_sha"] == doc["private_payload_commit"]
         and observed["tree_sha"] == doc["private_payload_tree"]
         and observed["path"] == (
             "f139/private-native/" + doc["private_payload_sha256"] + ".json")
         and observed["git_blob_sha"] == doc["private_payload_blob_sha"],
         "PRIVATE_PROVIDER_STORAGE_MAPPING_DRIFT")
    sha = doc["private_payload_sha256"]
    ticket = (
        "f139-nci04-i" + str(raw["number"]) + "-" +
        owner_source_sha[:12] + "-" + sha[:8]
    )
    need(UINT.fullmatch(str(raw["number"])) is not None
         and UINT.fullmatch(str(raw["id"])) is not None,
         "ISSUE_NUMBER_ID_INVALID")
    return PrivateOpaqueIssue(
        raw["number"], raw["id"], ticket, owner_source_sha,
        hashlib.sha256(body.encode("ascii")).hexdigest(),
        doc["private_target_commit"], doc["private_target_tree"],
        doc["private_payload_commit"], doc["private_payload_tree"],
        doc["private_payload_sha256"], doc["private_payload_blob_sha"],
    )


def bind_private_issue_to_credentialed_reference(issue, binding, ref_raw, *,
                                                 authenticated_repository_metadata):
    """Join a *preverified* original HMAC-bound result and later private ref.

    Neither reference SHA nor owner authorization digest may be in the
    original issue body; they only exist after the signed issue's digest is
    known. The original signer must independently call the existing
    verify_credentialed_owner_binding with THIS issue_body_sha256, exact
    issue number/id, and independently authenticated private bytes.
    """
    need(type(issue) is PrivateOpaqueIssue and type(binding) is dict
         and binding.get("schema") ==
             "forge.f139.private-hybrid-credentialed-binding.v1"
         and binding.get("provided_owner_hmac_pair_matched") is True
         and binding.get("private_blob_bytes_matched") is True
         and binding.get("original_owner_live_issue_verified") is False
         and binding.get("private_worker_executed") is False,
         "ORIGINAL_HMAC_BINDING_REQUIRED")
    need(binding.get("ticket") == issue.ticket
         and binding.get("issue_number") == issue.number
         and binding.get("issue_id") == issue.issue_id
         and binding.get("issue_body_sha256") == issue.issue_body_sha256
         and binding.get("owner_source_sha") == issue.source_sha
         and binding.get("private_target_commit") == issue.private_target_commit
         and binding.get("private_target_tree") == issue.private_target_tree
         and binding.get("private_payload_sha256") == issue.private_payload_sha256
         and type(ref_raw) is bytes
         and binding.get("reference_sha256") ==
             hashlib.sha256(ref_raw).hexdigest(),
         "CREDENTIAL_OR_ISSUE_DIGEST_DRIFT")
    ref = parse_reference(
        ref_raw, owner_source_sha=issue.source_sha,
        private_commit=issue.private_target_commit,
        private_tree=issue.private_target_tree,
        authenticated_repository_metadata=authenticated_repository_metadata,
    )
    for k, value in (
        ("private_payload_commit", issue.private_payload_commit),
        ("private_payload_tree", issue.private_payload_tree),
        ("private_payload_sha256", issue.private_payload_sha256),
        ("private_payload_blob_sha", issue.private_payload_blob_sha),
        ("owner_authorization_sha256", binding["authorization_binding_sha256"]),
        ("owner_signed_intent_sha256", issue.private_payload_sha256),
    ):
        need(ref[k] == value, "PRIVATE_REFERENCE_OR_SIGNED_ISSUE_DRIFT")
    # This is a deterministic join, NOT a live owner ledger record, signed
    # worker receipt, provider credential, or license to activate a lane.
    return {
        "schema": "forge.f139.private-hybrid-issue-reference-join.v1",
        "issue_number": issue.number,
        "issue_id": issue.issue_id,
        "issue_body_sha256": issue.issue_body_sha256,
        "ticket": issue.ticket,
        "private_payload_sha256": issue.private_payload_sha256,
        "reference_sha256": binding["reference_sha256"],
        "owner_hmac_algorithm_pair_matched": True,
        "opaque_issue_reference_binding_verified": True,
        "live_owner_ledger_verified": False,
        "private_worker_execution_verified": False,
        "hybrid_lane_admitted": False,
        "scientific_first_use": False,
    }
