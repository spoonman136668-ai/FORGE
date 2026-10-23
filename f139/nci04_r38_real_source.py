"""R38: read-only verification of actual upstream Wingless/Yggdrasil R7 Git objects.

Runs ONLY on an isolated qualification branch. Not a scheduler, issue issuer,
owner signature, V2 work admission, science execution, or source promotion.
The GitHub credential is read-only and never logged. Returned provenance has
a deliberately NON-ADMISSIBLE disposition because the current F139 V1 owner
ledger/worker have no approved multi-file contract.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from f139.nci04_native_contract import canonical, digest, REPOS
from f139.nci04_r7_package import (
    ALLOWED, PREREG, WORKFLOW, _tree, _blob, freeze_r7_owner_pr,
)

CURRENT_ORIGINAL_OWNER_SOURCE = "ecbd672f0b3bba34d6e92d2f1475ea6dc80f605f"
FROZEN_R7 = {
    "Wingless": {
        "number": 382,
        "base": "48ba343b403bc9b4389ce1777130e546b3c446bd",
        "head": "3b7ff571964ce819096367e74150d689f6541523",
    },
    "Yggdrasil": {
        "number": 418,
        "base": "9b069040feeddd9f509ab2c8ac9656d0a2c07d77",
        "head": "f3cdabdb3420bb8604e41dda9903ae65eba008e7",
    },
}
MAX_RESPONSE_BYTES = 8_000_000


class SourceReadDenied(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise SourceReadDenied("R38_" + reason)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        raise SourceReadDenied("R38_CROSS_ORIGIN_REDIRECT_FORBIDDEN")


class ReadOnlyGitHub:
    """No mutations, retries, redirect following, branch browsing or generic URLs."""
    def __init__(self, lane):
        require(lane in REPOS, "LANE_INVALID")
        self.repo = REPOS[lane][0]
        self.prefix = "repos/" + self.repo + "/"
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self.opener = urllib.request.build_opener(_NoRedirect)
        self.cache = {}

    def get(self, path):
        require(isinstance(path, str) and path.startswith(self.prefix)
                and ".." not in path and "#" not in path
                and all(32 <= ord(c) < 127 for c in path),
                "REQUEST_NOT_BOUNDED_TO_LANE")
        rest = path[len(self.prefix):]
        # Every read is for one named PR, current main, or SHA-addressed
        # source tree/blob. Caller constructs paths, never arbitrary user URL.
        require(rest.startswith(("pulls/", "branches/main", "git/commits/",
                                 "git/trees/", "git/blobs/")),
                "GITHUB_ENDPOINT_NOT_READ_ONLY_ALLOWLISTED")
        immutable = rest.startswith(("git/commits/", "git/trees/", "git/blobs/"))
        if immutable and path in self.cache:
            return self.cache[path]
        url = "https://api.github.com/" + path
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "FORGE-F139-R38-ReadOnly"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request(url, method="GET", headers=headers)
        try:
            with self.opener.open(request, timeout=25) as response:
                require(response.status == 200, "PROVIDER_HTTP_STATUS")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except (urllib.error.URLError, TimeoutError) as exc:
            raise SourceReadDenied("R38_PROVIDER_READ_FAILED") from exc
        require(len(raw) <= MAX_RESPONSE_BYTES, "PROVIDER_RESPONSE_TOO_LARGE")
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise SourceReadDenied("R38_PROVIDER_JSON_INVALID") from exc
        if immutable:
            self.cache[path] = result
        return result


def confirm_live_r7(lane: str):
    require(lane in FROZEN_R7, "LANE_NOT_PREQUALIFIED")
    source = FROZEN_R7[lane]
    repo = REPOS[lane][0]
    root = "repos/" + repo
    api = ReadOnlyGitHub(lane)
    pr = api.get(root + "/pulls/" + str(source["number"]))
    require(pr.get("head", {}).get("sha") == source["head"]
            and pr.get("base", {}).get("sha") == source["base"],
            "EXACT_FROZEN_R7_PR_CHANGED")
    # Freeze meaningful input identities from actual SHA-authenticated Git
    # blobs. Dependencies use the frozen base TREE identity only and do not
    # constitute a verified whole-runtime transitive dependency closure.
    head_tree, head_entries = _tree(api.get, repo, source["head"])
    base_tree, _ = _tree(api.get, repo, source["base"])
    require(set(ALLOWED[lane]).issubset(head_entries), "HEAD_PATH_ABSENT")
    prereg = _blob(api.get, repo, head_entries[PREREG]["sha"])
    harness = _blob(api.get, repo, head_entries[WORKFLOW]["sha"])
    testpath = ("research/native/itd01/r7/native_test.go" if lane == "Wingless"
                else "research/native/itd01/r7/test_native_cells.py")
    suite = _blob(api.get, repo, head_entries[testpath]["sha"])
    semantics = {
        "dependency_sha256": digest(canonical({
            "kind": "base-tree-source-snapshot-not-transitive-dependency-closure",
            "repo": repo, "commit_sha": source["base"], "tree_sha": base_tree})),
        "qualification_harness_sha256": digest(harness),
        "training_config_sha256": digest(prereg),
        "suite_identity_sha256": digest(suite),
        "toolchain_identity": "go1.25.0" if lane == "Wingless" else "python3.11.11",
    }
    packet = freeze_r7_owner_pr(
        get=api.get, lane=lane, pr_number=source["number"],
        controller_source_sha=CURRENT_ORIGINAL_OWNER_SOURCE,
        semantics=semantics)
    record = packet["proposal"]
    require(record["candidate_head_commit"] == source["head"]
            and record["target_base_commit"] == source["base"]
            and record["candidate_head_tree"] == head_tree
            and record["target_base_tree"] == base_tree
            and len(record["files"]) == 5
            and packet["eligible"] is False
            and packet["dispatch_authorized"] is False
            and packet["execute_embedded_workflow"] is False,
            "PROVENANCE_OR_AUTHORITY_DRIFT")
    return {
        "schema": "forge.f139.r38.readonly-authenticated-real-source.v1",
        "lane": lane, "repo": repo, "pull_request": source["number"],
        "base_commit": source["base"], "base_tree": base_tree,
        "head_commit": source["head"], "head_tree": head_tree,
        "manifest_sha256": packet["source_evidence_sha256"],
        "manifest_files": record["files"],
        "manifest_file_count": packet["source_manifest_count"],
        "manifest_total_bytes": packet["source_manifest_total_bytes"],
        "semantic_sha256": digest(canonical(semantics)),
        "dependency_evidence_scope": "base-tree-only-not-transitive-closure",
        "harness_git_blob_sha": head_entries[WORKFLOW]["sha"],
        "prereg_git_blob_sha": head_entries[PREREG]["sha"],
        "suite_git_blob_sha": head_entries[testpath]["sha"],
        "source_snapshot": "AUTHENTICATED_IMMUTABLE_PROVIDER_GIT",
        "admission": "BLOCKED_UNIMPLEMENTED_V2_OWNER_CONTRACT",
        "worker": "NOT_DISPATCHED",
        "native_science": "NOT_EXECUTED",
        "controller_mutation": False,
        "accepted_ref_mutation": False,
        "paid_api_calls": 0,
        "first_use": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output_dir
    require(not output.exists() and output.parent.is_dir(),
            "REPORT_DIRECTORY_MUST_BE_NEW")
    # Only after BOTH lanes verify completely may nonexecuting reports be
    # created; partial failures do not produce misleading success artifacts.
    records = [confirm_live_r7(lane) for lane in ("Wingless", "Yggdrasil")]
    require(records[0]["manifest_sha256"] != records[1]["manifest_sha256"],
            "CROSS_LANE_MANIFEST_COLLISION")
    output.mkdir(mode=0o700)
    for r in records:
        path = output / (r["lane"].lower() + ".json")
        path.write_bytes(canonical(r) + b"\n")
        print("R38_REAL_PROVIDER_" + r["lane"].upper() + "=PASS")
        print("R38_" + r["lane"].upper() + "_MANIFEST_SHA256=" + r["manifest_sha256"])
    combined = {"schema": "forge.f139.r38.provider-reconciliation.v1",
                "records": [{"lane": r["lane"], "manifest_sha256": r["manifest_sha256"],
                             "base": r["base_commit"], "head": r["head_commit"]}
                            for r in records],
                "admission": "NOT_AUTHORIZED",
                "real_worker_runs": 0,
                "scientific_first_use": False}
    (output / "reconciliation.json").write_bytes(canonical(combined) + b"\n")
    print("R38_REAL_PROVIDER_SOURCE_READ_ONLY=PASS")
    print("R38_NO_OWNER_ADMISSION_OR_SCIENCE=TRUE")


if __name__ == "__main__":
    try:
        main()
    except (SourceReadDenied, ValueError, OSError, TypeError) as exc:
        print("R38_FAIL_CLOSED " + str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
