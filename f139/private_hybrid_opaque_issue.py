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



def prepare_private_provider_commitment(payload_raw, before_raw, after_raw, *,
                                        owner_source_sha,
                                        authenticated_repository_metadata,
                                        authenticated_target_commit,
                                        authenticated_target_tree,
                                        authenticated_target_file,
                                        authenticated_storage_file,
                                        authenticated_candidate_file,
                                        authenticated_candidate_comparison):
    """PRIVATE-PROVIDER ONLY: verify original + after source and stored intent.

    The original and *after* file MUST be independently authenticated private
    Git blobs at immutable base/head commits, whose provider comparison proves
    exactly one source-modifying commit and exactly one modified source file.
    Two-file source+test research PRs must be reconciled by their scoped owner;
    neither a source hash nor this function can waive the single-file policy.

    This produces a bounded PUBLIC source-free issue body BEFORE original-owner
    HMAC signing. The caller must prove that both Git file mappings came from
    the private repository's authenticated provider. The function has no
    filesystem/network access, returns no source/path/credentials, and cannot
    attest GitHub-provider authenticity by itself. Never send either raw input
    to the public FORGE issue publisher or original owner telemetry.
    """
    from f139.nci04_native_contract import (
        NativeContractError, parse_intent,
    )
    from f139.private_hybrid_reference import PATH

    need(type(payload_raw) is bytes and 0 < len(payload_raw) <= 60000
         and type(before_raw) is bytes and 0 < len(before_raw) <= 32768
         and type(after_raw) is bytes and 0 < len(after_raw) <= 32768,
         "PRIVATE_PROVIDER_BYTES_BOUNDED")
    need(type(owner_source_sha) is str
         and SHA40.fullmatch(owner_source_sha) is not None
         and type(authenticated_target_commit) is str
         and SHA40.fullmatch(authenticated_target_commit) is not None
         and type(authenticated_target_tree) is str
         and SHA40.fullmatch(authenticated_target_tree) is not None,
         "PRIVATE_PROVIDER_SOURCE_UNQUALIFIED")
    md = authenticated_repository_metadata
    need(type(md) is dict and set(md) == {"full_name", "private"}
         and md["full_name"] == REPOSITORY and md["private"] is True,
         "PRIVATE_PROVIDER_VISIBILITY")
    try:
        doc = json.loads(payload_raw, object_pairs_hook=unique)
        need(type(doc) is dict and canonical(doc) == payload_raw,
             "PRIVATE_INTENT_NONCANONICAL")
        candidate = parse_intent(
            payload_raw, protected_main=owner_source_sha,
            target_commit=authenticated_target_commit,
            target_tree_sha=authenticated_target_tree)
    except (ValueError, TypeError, UnicodeError, NativeContractError) as exc:
        raise PrivateOpaqueIssueDenied(
            "F139_PRIVATE_HYBRID_ISSUE_PRIVATE_INTENT_INVALID") from exc
    need(candidate.lane == LANE and type(candidate.path) is str
         and PATH.fullmatch(candidate.path) is not None
         and candidate.before_sha256 == hashlib.sha256(before_raw).hexdigest()
         and candidate.after_sha256 == hashlib.sha256(after_raw).hexdigest()
         and candidate.after_bytes == after_raw,
         "PRIVATE_BASELINE_OR_AFTER_BYTES_DRIFT")

    def blob_sha(raw):
        return hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

    original = authenticated_target_file
    need(type(original) is dict and set(original) == {
        "repository", "commit_sha", "tree_sha", "path", "git_blob_sha",
    } and original["repository"] == REPOSITORY
         and original["commit_sha"] == authenticated_target_commit
         and original["tree_sha"] == authenticated_target_tree
         and original["path"] == candidate.path
         and original["git_blob_sha"] == blob_sha(before_raw),
         "PRIVATE_BASELINE_GIT_BLOB_NOT_AUTHENTICATED")
    # Compare a real candidate HEAD against the frozen private baseline.
    # The project-owned provider must independently authenticate both Git
    # object identities and the provider comparison, not caller assertions.
    revision = authenticated_candidate_file
    need(type(revision) is dict and set(revision) == {
        "repository", "commit_sha", "tree_sha", "path", "git_blob_sha",
    } and revision["repository"] == REPOSITORY
         and type(revision["commit_sha"]) is str
         and SHA40.fullmatch(revision["commit_sha"]) is not None
         and revision["commit_sha"] != authenticated_target_commit
         and type(revision["tree_sha"]) is str
         and SHA40.fullmatch(revision["tree_sha"]) is not None
         and revision["path"] == candidate.path
         and revision["git_blob_sha"] == blob_sha(after_raw),
         "PRIVATE_CANDIDATE_HEAD_SOURCE_NOT_AUTHENTICATED")
    comparison = authenticated_candidate_comparison
    need(type(comparison) is dict
         and comparison.get("status") == "ahead"
         and type(comparison.get("ahead_by")) is int
         and comparison["ahead_by"] == 1
         and type(comparison.get("behind_by")) is int
         and comparison["behind_by"] == 0
         and type(comparison.get("total_commits")) is int
         and comparison["total_commits"] == 1
         and type(comparison.get("base_commit")) is dict
         and comparison["base_commit"].get("sha") == authenticated_target_commit
         and type(comparison.get("merge_base_commit")) is dict
         and comparison["merge_base_commit"].get("sha") == authenticated_target_commit,
         "PRIVATE_CANDIDATE_COMPARE_ANCESTRY_INVALID")
    commits = comparison.get("commits")
    need(type(commits) is list and len(commits) == 1
         and type(commits[0]) is dict
         and commits[0].get("sha") == revision["commit_sha"]
         and type(commits[0].get("parents")) is list
         and len(commits[0]["parents"]) == 1
         and type(commits[0]["parents"][0]) is dict
         and commits[0]["parents"][0].get("sha") ==
             authenticated_target_commit,
         "PRIVATE_CANDIDATE_COMMIT_NOT_DIRECT_CHILD")
    changed = comparison.get("files")
    need(type(changed) is list and len(changed) == 1
         and type(changed[0]) is dict
         and changed[0].get("filename") == candidate.path
         and changed[0].get("status") == "modified"
         and changed[0].get("sha") == revision["git_blob_sha"]
         and type(changed[0].get("changes")) is int
         and changed[0]["changes"] > 0,
         "PRIVATE_CANDIDATE_NOT_EXACTLY_ONE_SOURCE_FILE")
    observed = authenticated_storage_file
    payload_sha = hashlib.sha256(payload_raw).hexdigest()
    need(type(observed) is dict and set(observed) == {
        "repository", "commit_sha", "tree_sha", "path", "git_blob_sha",
    } and observed["repository"] == REPOSITORY
         and type(observed["commit_sha"]) is str
         and SHA40.fullmatch(observed["commit_sha"]) is not None
         and observed["commit_sha"] != authenticated_target_commit
         and observed["commit_sha"] != revision["commit_sha"]
         and type(observed["tree_sha"]) is str
         and SHA40.fullmatch(observed["tree_sha"]) is not None
         and observed["path"] == "f139/private-native/" + payload_sha + ".json"
         and observed["git_blob_sha"] == blob_sha(payload_raw),
         "PRIVATE_STORAGE_GIT_BLOB_NOT_AUTHENTICATED")
    public = {
        "schema": SCHEMA, "kind": KIND, "lane": LANE,
        "source_sha": owner_source_sha, "repository": REPOSITORY,
        "private_target_commit": authenticated_target_commit,
        "private_target_tree": authenticated_target_tree,
        "private_payload_commit": observed["commit_sha"],
        "private_payload_tree": observed["tree_sha"],
        "private_payload_sha256": payload_sha,
        "private_payload_blob_sha": observed["git_blob_sha"],
        "scientific_first_use": False, "paid_model_calls": 0,
        "accepted_ref_mutations": 0,
    }
    need(set(public) == FIELDS, "PRIVATE_PUBLIC_SCHEMA_DRIFT")
    body = canonical(public)
    need(0 < len(body) <= MAX_BODY, "PUBLIC_ISSUE_BODY_TOO_LARGE")
    return {
        "schema": "forge.f139.private-provider-source-free-issue-preparation.v1",
        "issue_body": body.decode("ascii"),
        "issue_body_sha256": hashlib.sha256(body).hexdigest(),
        "private_payload_sha256": payload_sha,
        "real_baseline_blob_bytes_matched": True,
        "real_after_blob_bytes_matched": True,
        "single_commit_single_source_delta_verified": True,
        "real_storage_blob_bytes_matched": True,
        "public_private_code_emitted": False,
        "original_owner_live_issue_verified": False,
        "private_worker_executed": False,
        "scientific_first_use": False,
    }


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
