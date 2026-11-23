"""GET-only first gate for a future F139 original-owner V3 source forward.

This verifies merged source, exact qualification and protected-main custody
BEFORE any owner-host PREPARE. It creates no certificate and grants no task,
worker, scientific, or source-forward authority. A separate owner-qualified
cold-ledger/DPAPI/Windows-SID path must perform any actual cutover.
"""
from __future__ import annotations

import re

from f139.local_controller import F139Error
from f139.nci04_fresh_owner_source_forward_v2 import (
    CI_JOBS, ForwardV2Denied, _qualified_run,
)

REPO = "repos/spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
BASE_MAIN = "10cd8266e67309ee9aacf1964875e0451f11101a"
BASE_TREE = "190ab39868e971116ae49a653d8541a6f52280ae"
SCHEMA = "forge.f139.fresh-owner-v3-remote-readonly-preflight.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")


class V3RemotePreflightDenied(ValueError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
        raise V3RemotePreflightDenied("F139_V3_READONLY_" + code)


def _sha(value: object) -> bool:
    return type(value) is str and SHA40.fullmatch(value) is not None


def _positive(value: object) -> bool:
    return type(value) is int and 0 < value < (1 << 63)


def inspect_merged_source_readonly(api, *, owner_source_sha: str,
                                    owner_source_tree: str,
                                    pr_number: int, pr_head_sha: str,
                                    regression_run_id: int,
                                    source_run_id: int,
                                    rehearsal_run_id: int) -> dict:
    """Validate provider evidence before a future separate owner-host operation.

    Only GET is permitted on the supplied API object. This deliberately does
    not accept historical PRs, synthetic owner comments, signed certificates,
    live task state, or any caller assertion as execution authority. All
    evidence must be reverified under the original host's lock later.
    """
    need(_sha(owner_source_sha) and _sha(owner_source_tree)
         and _sha(pr_head_sha) and type(pr_number) is int
         and pr_number > 1870
         and all(_positive(v) for v in (
             regression_run_id, source_run_id, rehearsal_run_id))
         and owner_source_sha not in (BASE_MAIN, pr_head_sha),
         "INPUT_SCOPE_INVALID")
    try:
        branch = api.get(REPO + "/branches/main")
        base = api.get(REPO + "/git/commits/" + BASE_MAIN)
        commit = api.get(REPO + "/git/commits/" + owner_source_sha)
        pr = api.get(REPO + "/pulls/" + str(pr_number))
        need(type(branch) is dict and branch.get("name") == "main"
             and branch.get("protected") is True
             and branch.get("commit", {}).get("sha") == owner_source_sha,
             "CURRENT_PROTECTED_MAIN_MISMATCH")
        need(type(base) is dict and base.get("sha") == BASE_MAIN
             and base.get("tree", {}).get("sha") == BASE_TREE,
             "PINNED_BASE_TREE_CHANGED")
        parents = commit.get("parents") if type(commit) is dict else None
        need(type(commit) is dict and commit.get("sha") == owner_source_sha
             and commit.get("tree", {}).get("sha") == owner_source_tree
             and type(parents) is list and len(parents) == 2
             and parents[0].get("sha") == BASE_MAIN
             and parents[1].get("sha") == pr_head_sha,
             "MERGE_PARENT_OR_TREE_MISMATCH")
        need(type(pr) is dict and pr.get("number") == pr_number
             and pr.get("merged") is True and pr.get("state") == "closed"
             and pr.get("merge_commit_sha") == owner_source_sha
             and pr.get("user", {}).get("login") == OWNER
             and pr.get("head", {}).get("sha") == pr_head_sha
             and pr.get("head", {}).get("repo", {}).get("full_name")
                 == "spoonman136668-ai/FORGE"
             and pr.get("base", {}).get("sha") == BASE_MAIN
             and pr.get("base", {}).get("ref") == "main"
             and pr.get("base", {}).get("repo", {}).get("full_name")
                 == "spoonman136668-ai/FORGE",
             "MERGED_OWNER_PR_CUSTODY_INVALID")
        runs = {
            "regression_run_id": regression_run_id,
            "source_run_id": source_run_id,
            "rehearsal_run_id": rehearsal_run_id,
        }
        for name, expected in CI_JOBS:
            _qualified_run(api, runs[name], pr_head_sha, expected)
        need(api.get(REPO + "/branches/main") == branch,
             "PROTECTED_MAIN_MOVED_DURING_READ")
    except (OSError, KeyError, TypeError, AttributeError, F139Error,
            ForwardV2Denied) as exc:
        raise V3RemotePreflightDenied(
            "F139_V3_READONLY_REMOTE_EVIDENCE_UNAVAILABLE_OR_INVALID") from exc
    return {
        "schema": SCHEMA,
        "owner_source_sha": owner_source_sha,
        "owner_source_tree": owner_source_tree,
        "pr_number": pr_number,
        "pr_head_sha": pr_head_sha,
        **runs,
        "remote_evidence": "VERIFIED_READ_ONLY",
        "original_owner_cold_custody": "NOT_CHECKED",
        "safe_to_disable_task": False,
        "signed_source_forward": False,
        "worker_dispatches": 0,
        "scientific_first_use": False,
    }
