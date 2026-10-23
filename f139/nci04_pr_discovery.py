"""Read-only, bounded PR-to-native-proposal discovery for original F139.

This module does not enumerate the backlog, authenticate controller operator
identity, create owner GitHub issues, add eligibility labels, admit SQLite work,
dispatch a worker, mutate a ref, or authorize scientific first-use.

Only call with an authenticated read-only GitHub provider (e.g. the original
F139 GitHub.get). Provider replies are checked against exact commits, trees,
Git blob content, a single pre-existing allowlisted source file, and an
unchanged PR snapshot. A returned proposal is never executable authority.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re
from typing import Callable

from f139.nci04_native_contract import REPOS, canonical, digest
from f139.nci04_proposal_compiler import prepare_proposal

SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
OWNER = "spoonman136668-ai"
SEMANTIC_FIELDS = frozenset({
    "dependency_sha256", "qualification_harness_sha256",
    "training_config_sha256", "suite_identity_sha256", "toolchain_identity",
})


class NativePRDiscoveryDenied(ValueError):
    pass


def require(ok: bool, cause: str) -> None:
    if not ok:
        raise NativePRDiscoveryDenied("R36_" + cause)


def _sha(value) -> bool:
    return isinstance(value, str) and SHA40.fullmatch(value) is not None


def _commit(get: Callable[[str], object], repo: str, sha: str) -> str:
    doc = get("repos/" + repo + "/git/commits/" + sha)
    require(isinstance(doc, dict) and doc.get("sha") == sha
            and isinstance(doc.get("tree"), dict)
            and _sha(doc["tree"].get("sha")),
            "PROVIDER_COMMIT_TREE_NOT_AUTHENTICATED")
    return doc["tree"]["sha"]


def _contents(get: Callable[[str], object], repo: str,
              path: str, sha: str) -> tuple[bytes, str]:
    doc = get("repos/" + repo + "/contents/" + path + "?ref=" + sha)
    require(isinstance(doc, dict) and doc.get("type") == "file"
            and doc.get("encoding") == "base64"
            and _sha(doc.get("sha"))
            and type(doc.get("size")) is int and 0 < doc["size"] <= 32768
            and isinstance(doc.get("content"), str),
            "PROVIDER_FILE_NOT_BOUNDED")
    encoded = doc["content"].replace("\n", "")
    require(all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
                for c in encoded),
            "PROVIDER_FILE_BASE64_INVALID")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise NativePRDiscoveryDenied("R36_PROVIDER_FILE_BASE64_INVALID") from exc
    require(base64.b64encode(raw).decode("ascii") == encoded
            and len(raw) == doc["size"],
            "PROVIDER_FILE_BYTES_MISMATCH")
    # Authenticate returned bytes against provider's Git blob object ID.
    header = b"blob " + str(len(raw)).encode("ascii") + b"\x00"
    require(hashlib.sha1(header + raw).hexdigest() == doc["sha"],
            "PROVIDER_GIT_BLOB_IDENTITY_DRIFT")
    return raw, doc["sha"]


def _fingerprint(pr: dict) -> tuple:
    require(isinstance(pr, dict), "PROVIDER_PR_NOT_OBJECT")
    head, base = pr.get("head"), pr.get("base")
    require(isinstance(head, dict) and isinstance(base, dict),
            "PROVIDER_PR_REFS_MISSING")
    return (pr.get("number"), pr.get("id"), pr.get("state"),
            pr.get("changed_files"), head.get("sha"), base.get("sha"),
            head.get("ref"), base.get("ref"))


def prepare_authenticated_pr_proposal(
        *, get: Callable[[str], object], lane: str, pr_number: int,
        controller_source_sha: str, semantics: dict) -> dict:
    """Compile one owner-reviewed *draft* without any mutation or dispatch.

    get must be an already-authenticated, read-only GitHub repository GET
    transport. This function does not supply tokens or follow arbitrary URLs.
    Semantic digests are caller-supplied provenance claims, not independently
    certified by this adapter: later owner review must establish their custody.
    """
    require(callable(get) and lane in REPOS, "PROVIDER_OR_LANE_INVALID")
    require(type(pr_number) is int and pr_number > 0,
            "PR_NUMBER_INVALID")
    require(_sha(controller_source_sha), "CONTROLLER_SHA_INVALID")
    require(isinstance(semantics, dict) and set(semantics) == SEMANTIC_FIELDS
            and all(isinstance(semantics[key], str)
                    and SHA64.fullmatch(semantics[key]) is not None
                    for key in SEMANTIC_FIELDS if key != "toolchain_identity")
            and semantics["toolchain_identity"] ==
            ("go1.25.0" if lane == "Wingless" else "python3.11.11"),
            "SEMANTIC_PROVENANCE_NOT_FROZEN")
    repo, prefixes, suffix = REPOS[lane]
    prefix = "repos/" + repo
    pr = get(prefix + "/pulls/" + str(pr_number))
    require(isinstance(pr, dict) and pr.get("number") == pr_number
            and type(pr.get("id")) is int and pr["id"] > 0
            and pr.get("state") == "open"
            and pr.get("merged_at") is None
            and pr.get("author_association") == "OWNER"
            and isinstance(pr.get("user"), dict)
            and pr["user"].get("login") == OWNER
            and pr.get("changed_files") == 1,
            "PR_OWNER_SCOPE_OR_SINGLE_FILE_INVALID")
    head, base = pr.get("head"), pr.get("base")
    require(isinstance(head, dict) and isinstance(base, dict)
            and isinstance(head.get("repo"), dict)
            and isinstance(base.get("repo"), dict)
            and head["repo"].get("full_name") == repo
            and base["repo"].get("full_name") == repo
            and base.get("ref") == "main"
            and _sha(head.get("sha")) and _sha(base.get("sha"))
            and head["sha"] != base["sha"],
            "PR_BRANCH_OR_REPOSITORY_DRIFT")
    head_sha, base_sha = head["sha"], base["sha"]
    branch = get(prefix + "/branches/main")
    require(isinstance(branch, dict)
            and isinstance(branch.get("commit"), dict)
            and branch["commit"].get("sha") == base_sha,
            "TARGET_MAIN_NOT_PINNED_TO_PR_BASE")
    files = get(prefix + "/pulls/" + str(pr_number) + "/files?per_page=2")
    require(isinstance(files, list) and len(files) == 1
            and isinstance(files[0], dict)
            and files[0].get("status") == "modified"
            and type(files[0].get("changes")) is int
            and files[0]["changes"] > 0
            and _sha(files[0].get("sha")),
            "PR_FILE_LIST_NOT_EXACT_SINGLE_MODIFICATION")
    path = files[0].get("filename")
    # Check the path before interpolating it into any authenticated GET.
    require(isinstance(path, str)
            and len(path) <= 200
            and path.startswith(prefixes)
            and path.endswith(suffix)
            and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]*", path) is not None
            and "\\" not in path
            and all(part not in ("", ".", "..") and not part.startswith(".")
                    for part in path.split("/")),
            "PR_SOURCE_PATH_FORBIDDEN")
    base_tree = _commit(get, repo, base_sha)
    head_tree = _commit(get, repo, head_sha)
    before, before_blob = _contents(get, repo, path, base_sha)
    after, after_blob = _contents(get, repo, path, head_sha)
    require(files[0]["sha"] == after_blob and before_blob != after_blob,
            "PR_FILE_CHANGE_NOT_MATCHED_TO_HEAD")
    # Provider re-read rejects moving PR heads/base during discovery.
    again = get(prefix + "/pulls/" + str(pr_number))
    require(_fingerprint(pr) == _fingerprint(again),
            "PR_MOVED_DURING_DISCOVERY")
    result = prepare_proposal(
        controller_source_sha=controller_source_sha, lane=lane,
        target_commit=base_sha, target_tree_sha=base_tree,
        path=path, before=before, after=after, **semantics)
    evidence = {
        "schema": "forge.f139.r36.immutable-pr-source.v1",
        "repository": repo, "pr_number": pr_number,
        "pr_id": pr["id"], "lane": lane, "source_path": path,
        "base_commit": base_sha, "base_tree": base_tree,
        "head_commit": head_sha, "head_tree": head_tree,
        "before_blob": before_blob, "after_blob": after_blob,
        "before_sha256": digest(before), "after_sha256": digest(after),
        "controller_source_sha": controller_source_sha,
        "qualification_key": result["qualification_key"],
        "semantic_inputs": semantics,
    }
    return {
        **result,
        "source_evidence": evidence,
        "source_evidence_sha256": digest(canonical(evidence)),
        "provider_attestation_read_only": True,
        "automatic_issue_creation": False,
        "eligible": False,
        "dispatch_authorized": False,
        "scientific_first_use": False,
    }
