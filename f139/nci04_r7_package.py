"""R37 read-only five-file R7 source manifest: evidence, not execution.

A strictly fixed, independently sourced ITD-01 R7 five-file proposal can be
inspected as immutable Git metadata. This is deliberately NOT a widening of
the original F139 V1 native candidate, signed issue, SQLite owner-admission
ledger, provider worker, or source-transition schema. No Git refs, issues,
queues, workflows, or scientific holdouts are mutated or executed.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re
from typing import Callable

from f139.nci04_native_contract import REPOS, canonical, digest

SCHEMA = "forge.f139.nci04.r7-source-package-proposal.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
OWNER = "spoonman136668-ai"
MAX_BLOB = 16_384
MAX_TOTAL = 65_536
PREREG = "research/native/itd01/r7/PREREG.md"
WORKFLOW = ".github/workflows/qualify-itd01-r7-native.yml"
ALLOWED = {
    "Wingless": frozenset({
        WORKFLOW, PREREG, "research/native/itd01/r7/cmd/report/main.go",
        "research/native/itd01/r7/native.go",
        "research/native/itd01/r7/native_test.go",
    }),
    "Yggdrasil": frozenset({
        WORKFLOW, PREREG, "research/native/itd01/r7/native_cells.py",
        "research/native/itd01/r7/report.py",
        "research/native/itd01/r7/test_native_cells.py",
    }),
}
SEMANTICS = frozenset({
    "dependency_sha256", "qualification_harness_sha256",
    "training_config_sha256", "suite_identity_sha256", "toolchain_identity",
})


class R37Denied(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise R37Denied("F139_R37_" + reason)


def _sha40(v) -> bool:
    return isinstance(v, str) and SHA40.fullmatch(v) is not None


def _pr_identity(v: dict) -> tuple:
    require(isinstance(v, dict), "PR_NOT_OBJECT")
    head, base = v.get("head"), v.get("base")
    require(isinstance(head, dict) and isinstance(base, dict),
            "PR_REFS_NOT_OBJECT")
    user = v.get("user")
    require(isinstance(user, dict), "PR_OWNER_INVALID")
    return (v.get("number"), v.get("id"), v.get("state"),
            v.get("merged_at"), v.get("author_association"),
            user.get("login"), v.get("changed_files"),
            head.get("sha"), head.get("ref"),
            head.get("repo", {}).get("full_name") if isinstance(head.get("repo"), dict) else None,
            base.get("sha"), base.get("ref"),
            base.get("repo", {}).get("full_name") if isinstance(base.get("repo"), dict) else None)


def _tree(get: Callable, repo: str, commit_sha: str) -> tuple[str, dict]:
    c = get("repos/" + repo + "/git/commits/" + commit_sha)
    require(isinstance(c, dict) and c.get("sha") == commit_sha
            and isinstance(c.get("tree"), dict)
            and _sha40(c["tree"].get("sha")), "COMMIT_TREE_IDENTITY_INVALID")
    tree_sha = c["tree"]["sha"]
    t = get("repos/" + repo + "/git/trees/" + tree_sha + "?recursive=1")
    require(isinstance(t, dict) and t.get("sha") == tree_sha
            and t.get("truncated") is False
            and isinstance(t.get("tree"), list)
            and len(t["tree"]) <= 100_000,
            "TRUNCATED_OR_UNAUTHENTICATED_TREE")
    entries = {}
    for e in t["tree"]:
        require(isinstance(e, dict)
                and isinstance(e.get("path"), str)
                and isinstance(e.get("type"), str)
                and isinstance(e.get("mode"), str)
                and _sha40(e.get("sha")), "TREE_ENTRY_MALFORMED")
        path = e["path"]
        require(path not in entries, "DUPLICATE_TREE_ENTRY")
        entries[path] = e
    return tree_sha, entries


def _blob(get: Callable, repo: str, blob_sha: str) -> bytes:
    require(_sha40(blob_sha), "BLOB_SHA_INVALID")
    b = get("repos/" + repo + "/git/blobs/" + blob_sha)
    require(isinstance(b, dict) and b.get("sha") == blob_sha
            and b.get("encoding") == "base64"
            and type(b.get("size")) is int and 0 < b["size"] <= MAX_BLOB
            and isinstance(b.get("content"), str),
            "BLOB_PROVIDER_METADATA_INVALID")
    s = b["content"].replace("\n", "")
    try:
        raw = base64.b64decode(s, validate=True)
        raw.decode("utf-8")
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise R37Denied("F139_R37_BLOB_ENCODING_INVALID") from exc
    require(len(raw) == b["size"] and b"\x00" not in raw
            and base64.b64encode(raw).decode("ascii") == s
            and hashlib.sha1(b"blob " + str(len(raw)).encode("ascii")
                             + b"\x00" + raw).hexdigest() == blob_sha,
            "BLOB_BYTES_NOT_CONTENT_ADDRESSED")
    return raw


def freeze_r7_owner_pr(*, get: Callable[[str], object],
                       lane: str, pr_number: int,
                       controller_source_sha: str,
                       semantics: dict) -> dict:
    """Produce one exact-content R7 package for OWNER REVIEW ONLY.

    The injected GET must be the existing authenticated read-only GitHub
    transport; semantic digests require external provenance and are not
    certified by caller assertion. No job scheduling, code execution, or
    issue eligibility is implemented here.
    """
    require(callable(get) and isinstance(lane, str) and lane in ALLOWED,
            "LANE_OR_TRANSPORT_INVALID")
    require(type(pr_number) is int and pr_number > 0
            and _sha40(controller_source_sha),
            "ISSUE_OR_CONTROLLER_SOURCE_INVALID")
    require(isinstance(semantics, dict) and set(semantics) == SEMANTICS,
            "SEMANTIC_INPUTS_INVALID")
    for field in SEMANTICS - {"toolchain_identity"}:
        require(isinstance(semantics[field], str)
                and SHA64.fullmatch(semantics[field]) is not None,
                "SEMANTIC_SHA_INVALID")
    require(semantics["toolchain_identity"] ==
            ("go1.25.0" if lane == "Wingless" else "python3.11.11"),
            "TOOLCHAIN_UNQUALIFIED")

    repo = REPOS[lane][0]
    root = "repos/" + repo
    pr_path = root + "/pulls/" + str(pr_number)
    pr = get(pr_path)
    ident = _pr_identity(pr)
    require(pr.get("number") == pr_number
            and type(pr.get("id")) is int and pr["id"] > 0
            and pr.get("state") == "open"
            and pr.get("merged_at") is None
            and pr.get("user", {}).get("login") == OWNER
            and pr.get("author_association") == "OWNER"
            and pr.get("changed_files") == 5,
            "NOT_OWNER_AUTHORED_EXACT_R7_PR")
    head, base = pr["head"], pr["base"]
    require(isinstance(head.get("repo"), dict)
            and isinstance(base.get("repo"), dict)
            and head["repo"].get("full_name") == repo
            and base["repo"].get("full_name") == repo
            and base.get("ref") == "main"
            and _sha40(head.get("sha")) and _sha40(base.get("sha"))
            and head["sha"] != base["sha"],
            "FORK_OR_PR_BASE_INVALID")
    main_url = root + "/branches/main"
    main = get(main_url)
    require(isinstance(main, dict)
            and isinstance(main.get("commit"), dict)
            and main["commit"].get("sha") == base["sha"],
            "MAIN_MOVED_OR_BASE_NOT_CURRENT")
    files = get(pr_path + "/files?per_page=6")
    require(isinstance(files, list) and len(files) == 5
            and all(isinstance(f, dict)
                    and f.get("status") == "added"
                    and isinstance(f.get("filename"), str)
                    and _sha40(f.get("sha"))
                    and type(f.get("changes")) is int
                    and 0 < f["changes"] <= 1000
                    for f in files),
            "EXACT_ADDITIVE_FIVE_FILE_CHANGE_REQUIRED")
    names = [f["filename"] for f in files]
    require(len(set(names)) == 5 and set(names) == ALLOWED[lane],
            "PR_MANIFEST_ALLOWLIST_MISMATCH")
    base_tree_sha, base_entries = _tree(get, repo, base["sha"])
    head_tree_sha, head_entries = _tree(get, repo, head["sha"])
    manifest = []
    total = 0
    for path in sorted(names):
        f = next(f for f in files if f["filename"] == path)
        entry = head_entries.get(path)
        require(path not in base_entries
                and isinstance(entry, dict)
                and entry.get("type") == "blob"
                and entry.get("mode") == "100644"
                and entry.get("sha") == f["sha"],
                "ADDED_PATH_NOT_AUTHENTICATED_IN_GIT_TREE")
        raw = _blob(get, repo, f["sha"])
        total += len(raw)
        require(total <= MAX_TOTAL, "PACKAGE_OVER_SIZE_BUDGET")
        manifest.append({
            "path": path, "git_blob_sha": f["sha"],
            "sha256": digest(raw), "size": len(raw),
            "role": ("workflow-evidence-only" if path == WORKFLOW else
                     "frozen-preregistration" if path == PREREG else
                     "native-source-or-test-evidence"),
        })
    require(_pr_identity(get(pr_path)) == ident
            and get(main_url).get("commit", {}).get("sha") == base["sha"],
            "PR_OR_MAIN_MOVED_DURING_READ")
    record = {
        "schema": SCHEMA, "lane": lane, "repository": repo,
        "pr_number": pr_number, "pr_id": pr["id"],
        "controller_source_sha": controller_source_sha,
        "target_base_commit": base["sha"], "target_base_tree": base_tree_sha,
        "candidate_head_commit": head["sha"], "candidate_head_tree": head_tree_sha,
        "files": manifest, "semantic_inputs": semantics,
        "worker_contract": "unimplemented-review-only-r7-five-file",
        "scientific_first_use": False, "paid_api_calls": 0,
        "accepted_ref_mutations": 0,
    }
    key = digest(canonical(record))
    return {
        "proposal": record, "qualification_key": key,
        "source_evidence_sha256": key,
        "source_manifest_count": len(manifest),
        "source_manifest_total_bytes": total,
        "requires_independent_semantic_provenance": True,
        "requires_new_owner_issue_and_worker_contract": True,
        "v1_single_file_compatible": False,
        "eligible": False, "dispatch_authorized": False,
        "execute_embedded_workflow": False,
        "scientific_first_use": False,
    }
