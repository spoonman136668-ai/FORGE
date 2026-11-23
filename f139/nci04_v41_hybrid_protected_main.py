"""Trusted protected-main bridge for a future original-owner Hybrid maintenance.

Source-only, no workflow registration, task control, database or GitHub writes.
Never execute unmerged PR source on the original Windows owner runner.
"""
from __future__ import annotations

import re

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
V41 = "1a40fe4e3ec6e93a1631d59863b95e90981d734e"
PR = 1660
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
CI_NAMES = frozenset((
    "FORGE F139 native Windows controller qualification",
    "FORGE public Linux and Windows qualification",
    "FORGE F139-NCI04 native source rehearsal",
    "FORGE F139-D hosted development rehearsal",
))


class ProtectedHybridSourceDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise ProtectedHybridSourceDenied("F139_HYBRID_MAIN_BRIDGE_" + reason)


def _source(get, target):
    prefix = "repos/" + REPO + "/"
    main = get(prefix + "branches/main")
    pr = get(prefix + "pulls/1660")
    # Preserve all original PR #1660 checks for that release. For the
    # successor, require *separate* PR #1757 source/tree/CI custody.
    if (type(main) is dict and type(main.get("commit")) is dict
            and main["commit"].get("sha") == target
            and type(pr) is dict and pr.get("state") == "closed"
            and pr.get("merged") is True
            and pr.get("merge_commit_sha") ==
                "b98dae4c6b0a78b145cfca06aeb465d6d85d3597"
            and target != pr["merge_commit_sha"]):
        from f139.nci04_v41_hybrid_successor_release import (
            require_successor_source)
        return ("successor", require_successor_source(get, target))
    need(type(main) is dict and main.get("name") == "main"
         and main.get("protected") is True
         and type(main.get("commit")) is dict
         and main["commit"].get("sha") == target,
         "PROTECTED_MAIN_IDENTITY_DRIFT")
    need(type(pr) is dict and type(pr.get("number")) is int
         and pr["number"] == PR and pr.get("state") == "closed"
         and pr.get("merged") is True
         and pr.get("merge_commit_sha") == target
         and type(pr.get("user")) is dict
         and pr["user"].get("login") == OWNER
         and type(pr.get("head")) is dict
         and type(pr["head"].get("repo")) is dict
         and pr["head"]["repo"].get("full_name") == REPO
         and type(pr.get("base")) is dict
         and pr["base"].get("ref") == "main"
         and type(pr["base"].get("repo")) is dict
         and pr["base"]["repo"].get("full_name") == REPO
         and pr["base"].get("sha") in (V41, target),
         "MERGED_PR1660_CUSTODY_NOT_PROVEN")
    # GitHub may advance a merged PR's base.sha to the merge commit;
    # verify original-V41 ancestry independently instead of trusting that
    # mutable branch pointer as the pre-merge base.
    ancestry = get(prefix + "compare/" + V41 + "..." + target
                   + "?per_page=1&page=2")
    need(type(ancestry) is dict
         and ancestry.get("status") == "ahead"
         and type(ancestry.get("ahead_by")) is int
         and ancestry["ahead_by"] > 0
         and type(ancestry.get("behind_by")) is int
         and ancestry["behind_by"] == 0
         and type(ancestry.get("merge_base_commit")) is dict
         and ancestry["merge_base_commit"].get("sha") == V41,
         "V41_SOURCE_ANCESTRY_NOT_VERIFIED")
    need(type(pr["head"].get("sha")) is str
         and SHA40.fullmatch(pr["head"]["sha"]) is not None
         and type(pr["head"].get("ref")) is str
         and pr["head"]["ref"] == "engineering/f139-hybrid-reader-route-20261110",
         "ORIGINAL_QUALIFIED_PR_HEAD_MISSING")
    main_commit = get(prefix + "git/commits/" + target)
    original_pr_commit = get(prefix + "git/commits/" + pr["head"]["sha"])
    for commit, expected in ((main_commit, target),
                             (original_pr_commit, pr["head"]["sha"])):
        need(type(commit) is dict and commit.get("sha") == expected
             and type(commit.get("tree")) is dict
             and type(commit["tree"].get("sha")) is str
             and SHA40.fullmatch(commit["tree"]["sha"]) is not None,
             "SOURCE_COMMIT_TREE_INVALID")
    need(main_commit["tree"]["sha"] == original_pr_commit["tree"]["sha"],
         "PROTECTED_MAIN_TREE_DIFFERS_FROM_QUALIFIED_PR")
    return (main_commit["tree"]["sha"], pr["head"]["sha"])


def require_protected_main_release(get, env, *, target_sha):
    """Verify post-merge exact source and completed push CI before owner read.

    A synthetic candidate check result is NOT proof of release.  The genuine
    owner event must execute FROM protected main, after a qualified #1660
    merge and original-main post-merge Linux/Windows workflows.  No ability
    to merge, promote, pause or admit a new lane is granted by this receipt.
    """
    need(callable(get) and type(env) is dict and type(target_sha) is str
         and SHA40.fullmatch(target_sha) is not None
         and target_sha != V41
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_SHA") == target_sha
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and not env.get("OPENAI_API_KEY"),
         "ORIGINAL_OWNER_EVENT_OR_PROTECTED_SHA_DRIFT")
    source = _source(get, target_sha)
    if source[0] == "successor":
        return source[1]
    tree, pr_head_sha = source
    # Only the public Linux/Windows qualification runs on main push today.
    # The three additional native/development workflows run on PR events.
    # Exact source-tree parity binds the PR full regression to protected main.
    pr_runs = get("repos/" + REPO + "/actions/runs?head_sha=" + pr_head_sha
                  + "&event=pull_request&per_page=100")
    need(type(pr_runs) is dict
         and type(pr_runs.get("workflow_runs")) is list
         and len(pr_runs["workflow_runs"]) <= 100,
         "PREMERGE_CI_LIST_INVALID")
    found = {}
    for row in pr_runs["workflow_runs"]:
        need(type(row) is dict, "PREMERGE_CI_ROW_INVALID")
        name = row.get("name")
        if name not in CI_NAMES:
            continue
        need(name not in found
             and row.get("head_sha") == pr_head_sha
             and row.get("event") == "pull_request"
             and row.get("head_branch") ==
                 "engineering/f139-hybrid-reader-route-20261110"
             and row.get("status") == "completed"
             and row.get("conclusion") == "success"
             and type(row.get("run_attempt")) is int
             and row["run_attempt"] == 1
             and type(row.get("id")) is int and row["id"] > 0
             and type(row.get("actor")) is dict
             and row["actor"].get("login") == OWNER,
             "PREMERGE_CI_INCOMPLETE_DUPLICATE_OR_REPLAY")
        found[name] = row["id"]
    need(set(found) == CI_NAMES, "PREMERGE_FOUR_WORKFLOWS_REQUIRED")
    main_runs = get("repos/" + REPO + "/actions/runs?head_sha=" + target_sha
                    + "&event=push&branch=main&per_page=100")
    need(type(main_runs) is dict
         and type(main_runs.get("workflow_runs")) is list
         and len(main_runs["workflow_runs"]) <= 100,
         "POSTMERGE_CI_LIST_INVALID")
    main_public = [
        row for row in main_runs["workflow_runs"]
        if type(row) is dict
        and row.get("name") == "FORGE public Linux and Windows qualification"
    ]
    need(len(main_public) == 1, "POSTMERGE_MAIN_QUALIFICATION_REQUIRED")
    row = main_public[0]
    need(row.get("head_sha") == target_sha
         and row.get("event") == "push"
         and row.get("head_branch") == "main"
         and row.get("status") == "completed"
         and row.get("conclusion") == "success"
         and type(row.get("run_attempt")) is int
         and row["run_attempt"] == 1
         and type(row.get("id")) is int and row["id"] > 0
         and type(row.get("actor")) is dict
         and row["actor"].get("login") == OWNER,
         "POSTMERGE_MAIN_QUALIFICATION_FAILED_OR_REPLAY")
    need(_source(get, target_sha) == (tree, pr_head_sha),
         "SOURCE_MOVED_DURING_QUALIFICATION")
    return {
        "schema": "forge.f139.hybrid-v41.protected-main-source.v1",
        "source_sha": target_sha,
        "source_tree_sha": tree,
        "qualified_pr_source_sha": pr_head_sha,
        "qualification_run_ids": dict(sorted(found.items())),
        "protected_main_qualification_run_id": row["id"],
        "protected_main_verified": True,
        "merged_source_verified": True,
        "postmerge_ci_verified": True,
        "qualified_source_tree_parity": True,
        "original_owner_mutations": 0,
        "owner_maintenance_authorized": False,
        "source_transition_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
    }
