"""Bounded owner-PR feeder for the existing F139 native development queue.

This is NOT a scheduler, controller, science authority, or executable queue.
It converts only explicitly owner-authored draft PRs whose titles begin with
"F139 autonomy DEV:" into the already-qualified owner issue schema. The
existing F139 SQLite ledger remains the only execution/admission queue.

The feeder is inert unless the fixed owner policy issue is enabled and pinned
to the exact deployed FORGE source SHA. It accepts only the final single-commit,
single-existing-file delta of a PR, then independently authenticates the Git
commit/tree/blob bytes before compiling an ordinary V1 native issue payload.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Callable

from f139.nci04_native_contract import REPOS, canonical, digest
from f139.nci04_proposal_compiler import prepare_proposal
from f139.nci04_advisory_handoff import (AdvisoryHandoffDenied, inspect_pr_advisory)

OWNER = "spoonman136668-ai"
FORGE_REPO = "spoonman136668-ai/FORGE"
POLICY_ISSUE = 807
POLICY_SCHEMA = "forge.f139.native-autonomy-feed-owner-policy.v1"
TITLE_PREFIX = "F139 autonomy DEV:"
LABEL = "f139-native-development-eligible"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
POLICY_KEYS = frozenset({
    "schema", "enabled", "source_sha", "title_prefix", "lanes",
    "max_issue_creations_per_cycle", "require_owner_authored_pr",
    "require_single_head_commit_delta", "require_single_allowed_source_file",
    "scientific_first_use", "paid_model_calls", "accepted_ref_mutations",
    "new_controller", "new_scheduler", "new_queue",
})


class NativeFeedDenied(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise NativeFeedDenied("F139_NATIVE_FEED_" + reason)


def _sha40(value) -> bool:
    return isinstance(value, str) and SHA40.fullmatch(value) is not None

def candidate_identity(lane: str, target_commit: str, path: str,
                       after_sha256: str) -> str:
    require(lane in REPOS and _sha40(target_commit)
            and isinstance(path, str)
            and isinstance(after_sha256, str)
            and re.fullmatch(r"[a-f0-9]{64}", after_sha256) is not None,
            "CANDIDATE_IDENTITY_INPUT_INVALID")
    return digest(canonical({
        "schema": "forge.f139.native-autonomy-feed-candidate-identity.v1",
        "lane": lane, "target_commit": target_commit,
        "path": path, "after_sha256": after_sha256,
    }))


def candidate_identity_from_intent_base64(encoded: str) -> str:
    require(isinstance(encoded, str) and 0 < len(encoded) <= 60000,
            "HISTORICAL_INTENT_INVALID")
    try:
        raw = base64.b64decode(encoded, validate=True)
        doc = json.loads(raw)
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise NativeFeedDenied("F139_NATIVE_FEED_HISTORICAL_INTENT_INVALID") from exc
    require(isinstance(doc, dict), "HISTORICAL_INTENT_INVALID")
    return candidate_identity(
        doc.get("lane"), doc.get("target_commit"),
        doc.get("path"), doc.get("after_sha256"))



def _decode_content(doc: dict, *, allow_empty: bool = False) -> tuple[bytes, str]:
    require(isinstance(doc, dict) and doc.get("type") == "file"
            and doc.get("encoding") == "base64"
            and _sha40(doc.get("sha"))
            and type(doc.get("size")) is int
            and 0 <= doc["size"] <= 32768
            and isinstance(doc.get("content"), str),
            "PROVIDER_FILE_INVALID")
    encoded = doc["content"].replace("\n", "")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise NativeFeedDenied("F139_NATIVE_FEED_PROVIDER_BASE64") from exc
    require(base64.b64encode(raw).decode("ascii") == encoded
            and len(raw) == doc["size"]
            and (allow_empty or len(raw) > 0),
            "PROVIDER_FILE_BYTES_INVALID")
    header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
    require(hashlib.sha1(header + raw).hexdigest() == doc["sha"],
            "PROVIDER_BLOB_IDENTITY_DRIFT")
    return raw, doc["sha"]


def _pr_fingerprint(pr: dict) -> tuple:
    head, base = pr.get("head"), pr.get("base")
    return (
        pr.get("number"), pr.get("id"), pr.get("state"), pr.get("draft"),
        pr.get("title"), head.get("sha") if isinstance(head, dict) else None,
        base.get("sha") if isinstance(base, dict) else None,
    )


def inspect_policy(raw: dict, source_sha: str) -> dict:
    require(_sha40(source_sha) and isinstance(raw, dict)
            and raw.get("state") == "open"
            and "pull_request" not in raw
            and raw.get("number") == POLICY_ISSUE
            and isinstance(raw.get("user"), dict)
            and raw["user"].get("login") == OWNER
            and raw.get("author_association") == "OWNER",
            "POLICY_OWNER_IDENTITY")
    try:
        doc = json.loads(raw.get("body", ""))
    except (TypeError, ValueError, UnicodeError) as exc:
        raise NativeFeedDenied("F139_NATIVE_FEED_POLICY_JSON") from exc
    require(isinstance(doc, dict) and set(doc) == POLICY_KEYS
            and doc["schema"] == POLICY_SCHEMA
            and type(doc["enabled"]) is bool
            and doc["source_sha"] == source_sha
            and doc["title_prefix"] == TITLE_PREFIX
            and doc["lanes"] == ["Wingless", "Yggdrasil"]
            and doc["max_issue_creations_per_cycle"] == 2
            and doc["require_owner_authored_pr"] is True
            and doc["require_single_head_commit_delta"] is True
            and doc["require_single_allowed_source_file"] is True
            and doc["scientific_first_use"] is False
            and doc["paid_model_calls"] == 0
            and doc["accepted_ref_mutations"] == 0
            and doc["new_controller"] is False
            and doc["new_scheduler"] is False
            and doc["new_queue"] is False,
            "POLICY_SCOPE_DRIFT")
    return doc


def _semantic_identities(source_sha: str, lane: str, target_tree: str,
                         path: str) -> dict:
    """Deterministic provenance identities; no claim of scientific sufficiency."""
    toolchain = "go1.25.0" if lane == "Wingless" else "python3.11.11"
    return {
        "dependency_sha256": digest(canonical({
            "schema": "forge.f139.feed.target-tree-dependency-identity.v1",
            "target_tree_sha": target_tree,
        })),
        "qualification_harness_sha256": digest(canonical({
            "schema": "forge.f139.feed.fixed-native-worker-identity.v1",
            "controller_source_sha": source_sha,
            "worker": "forge-f139-development-worker.yml",
        })),
        "training_config_sha256": digest(canonical({
            "schema": "forge.f139.feed.development-only-config.v1",
            "lane": lane, "scientific_first_use": False,
        })),
        "suite_identity_sha256": digest(canonical({
            "schema": "forge.f139.feed.fixed-suite-identity.v1",
            "lane": lane, "target_tree_sha": target_tree, "path": path,
        })),
        "toolchain_identity": toolchain,
    }


def _candidate_from_pr(get: Callable[[str], object], *, lane: str,
                       pr: dict, source_sha: str) -> dict:
    repo, prefixes, suffix = REPOS[lane]
    require(isinstance(pr, dict)
            and type(pr.get("number")) is int and pr["number"] > 0
            and type(pr.get("id")) is int and pr["id"] > 0
            and pr.get("state") == "open" and pr.get("draft") is True
            and isinstance(pr.get("title"), str)
            and pr["title"].startswith(TITLE_PREFIX)
            and isinstance(pr.get("user"), dict)
            and pr["user"].get("login") == OWNER
            and pr.get("author_association") == "OWNER",
            "PR_NOT_EXPLICIT_OWNER_CANDIDATE")
    head = pr.get("head")
    require(isinstance(head, dict) and _sha40(head.get("sha"))
            and isinstance(head.get("repo"), dict)
            and head["repo"].get("full_name") == repo,
            "PR_HEAD_REPOSITORY_DRIFT")
    head_sha = head["sha"]
    head_commit = get("repos/" + repo + "/git/commits/" + head_sha)
    parents = head_commit.get("parents") if isinstance(head_commit, dict) else None
    require(head_commit.get("sha") == head_sha
            and isinstance(head_commit.get("tree"), dict)
            and _sha40(head_commit["tree"].get("sha"))
            and isinstance(parents, list) and len(parents) == 1
            and isinstance(parents[0], dict) and _sha40(parents[0].get("sha")),
            "HEAD_NOT_SINGLE_COMMIT_DELTA")
    target_commit = parents[0]["sha"]
    target_doc = get("repos/" + repo + "/git/commits/" + target_commit)
    require(isinstance(target_doc, dict) and target_doc.get("sha") == target_commit
            and isinstance(target_doc.get("tree"), dict)
            and _sha40(target_doc["tree"].get("sha")),
            "TARGET_COMMIT_TREE_INVALID")
    target_tree = target_doc["tree"]["sha"]
    compare = get("repos/" + repo + "/compare/" + target_commit + "..." + head_sha)
    files = compare.get("files") if isinstance(compare, dict) else None
    require(compare.get("status") == "ahead"
            and compare.get("ahead_by") == 1 and compare.get("behind_by") == 0
            and compare.get("total_commits") == 1
            and isinstance(files, list) and len(files) == 1,
            "HEAD_DELTA_NOT_EXACTLY_ONE_COMMIT_FILE")
    changed = files[0]
    path = changed.get("filename") if isinstance(changed, dict) else None
    require(changed.get("status") == "modified"
            and type(changed.get("changes")) is int
            and 0 < changed["changes"] <= 2000
            and _sha40(changed.get("sha"))
            and isinstance(path, str) and len(path) <= 200
            and path.startswith(prefixes) and path.endswith(suffix)
            and "\\" not in path
            and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]*", path) is not None
            and all(part not in ("", ".", "..") and not part.startswith(".")
                    for part in path.split("/")),
            "HEAD_FILE_NOT_ALLOWED_MODIFICATION")
    before_doc = get("repos/" + repo + "/contents/" + path + "?ref=" + target_commit)
    after_doc = get("repos/" + repo + "/contents/" + path + "?ref=" + head_sha)
    before, before_blob = _decode_content(before_doc)
    after, after_blob = _decode_content(after_doc)
    require(before_blob != after_blob and changed["sha"] == after_blob
            and before != after,
            "HEAD_FILE_BYTES_NOT_CHANGED")
    current = get("repos/" + repo + "/pulls/" + str(pr["number"]))
    require(_pr_fingerprint(current) == _pr_fingerprint(pr),
            "PR_MOVED_DURING_AUTHENTICATION")
    semantics = _semantic_identities(source_sha, lane, target_tree, path)
    proposal = prepare_proposal(
        controller_source_sha=source_sha, lane=lane,
        target_commit=target_commit, target_tree_sha=target_tree,
        path=path, before=before, after=after, **semantics)
    # Advisory lineage cannot grant authority. Original Git-tree and before/
    # after-byte authentication above always runs first. Malformed declared
    # advisory provenance rejects the PR; missing provenance preserves the
    # existing separately qualified owner-only intake.
    try:
        advisory = inspect_pr_advisory(
            pr.get("body"), lane=lane, controller_source_sha=source_sha,
            head_commit=head_sha, target_commit=target_commit, path=path,
            after_sha256=digest(after))
    except AdvisoryHandoffDenied as exc:
        raise NativeFeedDenied("F139_NATIVE_FEED_ADVISORY_HANDOFF_INVALID") from exc
    evidence = {
        "schema": "forge.f139.native-autonomy-feed-source.v1",
        "lane": lane, "repository": repo, "pr_number": pr["number"],
        "pr_id": pr["id"], "head_commit": head_sha,
        "head_tree": head_commit["tree"]["sha"],
        "target_commit": target_commit, "target_tree": target_tree,
        "path": path, "before_blob": before_blob, "after_blob": after_blob,
        "before_sha256": digest(before), "after_sha256": digest(after),
        "controller_source_sha": source_sha,
        "qualification_key": proposal["qualification_key"],
        "scientific_first_use": False,
    }
    if advisory is not None:
        evidence["advisory_handoff"] = advisory
    return {
        "lane": lane, "pr_number": pr["number"], "head_commit": head_sha,
        "advisory_handoff": advisory,
        "issue_title": ("F139 auto-feed " + lane + " PR#" +
                        str(pr["number"]) + ": " +
                        pr["title"][len(TITLE_PREFIX):].strip())[:180],
        "issue_body": proposal["issue_body"],
        "intent_base64": json.loads(proposal["issue_body"])["intent_base64"],
        "candidate_identity": candidate_identity(
            lane, target_commit, path, digest(after)),
        "qualification_key": proposal["qualification_key"],
        "source_evidence_sha256": digest(canonical(evidence)),
        "scientific_first_use": False,
    }


def prepare_feed(get: Callable[[str], object], *, source_sha: str,
                 existing_candidate_identities: set[str]) -> dict:
    """Return up to two issue drafts; caller decides whether to create them."""
    require(callable(get) and _sha40(source_sha)
            and isinstance(existing_candidate_identities, set)
            and all(isinstance(x, str)
                    and re.fullmatch(r"[a-f0-9]{64}", x) is not None
                    for x in existing_candidate_identities),
            "CALLER_INPUT_INVALID")
    policy_raw = get("repos/" + FORGE_REPO + "/issues/" + str(POLICY_ISSUE))
    policy = inspect_policy(policy_raw, source_sha)
    if not policy["enabled"]:
        return {"enabled": False, "candidates": [], "rejected": []}
    candidates, rejected = [], []
    for lane in policy["lanes"]:
        repo = REPOS[lane][0]
        docs = get("repos/" + repo + "/pulls?state=open&per_page=100&page=1")
        require(isinstance(docs, list) and len(docs) <= 100,
                "PR_CATALOG_INVALID")
        for pr in docs:
            if not (isinstance(pr, dict)
                    and isinstance(pr.get("title"), str)
                    and pr["title"].startswith(TITLE_PREFIX)):
                continue
            try:
                candidate = _candidate_from_pr(
                    get, lane=lane, pr=pr, source_sha=source_sha)
            except NativeFeedDenied as exc:
                rejected.append({
                    "lane": lane, "pr_number": pr.get("number"),
                    "reason": str(exc),
                })
                continue
            if candidate["candidate_identity"] in existing_candidate_identities:
                continue
            candidates.append(candidate)
            existing_candidate_identities.add(candidate["candidate_identity"])
            if len(candidates) >= policy["max_issue_creations_per_cycle"]:
                return {"enabled": True, "candidates": candidates,
                        "rejected": rejected}
    return {"enabled": True, "candidates": candidates, "rejected": rejected}
