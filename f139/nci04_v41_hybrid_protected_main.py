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
         and pr["base"].get("sha") == V41,
         "MERGED_PR1660_CUSTODY_NOT_PROVEN")
    commit = get(prefix + "git/commits/" + target)
    need(type(commit) is dict and commit.get("sha") == target
         and type(commit.get("tree")) is dict
         and type(commit["tree"].get("sha")) is str
         and SHA40.fullmatch(commit["tree"]["sha"]) is not None,
         "PROTECTED_COMMIT_TREE_INVALID")
    return commit["tree"]["sha"]


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
    tree = _source(get, target_sha)
    rows = get("repos/" + REPO + "/actions/runs?head_sha=" + target_sha
               + "&event=push&branch=main&per_page=100")
    need(type(rows) is dict and type(rows.get("workflow_runs")) is list
         and len(rows["workflow_runs"]) <= 100,
         "POSTMERGE_CI_LIST_INVALID")
    found = {}
    for row in rows["workflow_runs"]:
        need(type(row) is dict, "POSTMERGE_CI_ROW_INVALID")
        name = row.get("name")
        if name not in CI_NAMES:
            continue
        need(name not in found
             and row.get("head_sha") == target_sha
             and row.get("event") == "push"
             and row.get("head_branch") == "main"
             and row.get("status") == "completed"
             and row.get("conclusion") == "success"
             and type(row.get("run_attempt")) is int
             and row["run_attempt"] == 1
             and type(row.get("id")) is int
             and row["id"] > 0
             and type(row.get("actor")) is dict
             and row["actor"].get("login") == OWNER,
             "POSTMERGE_CI_INCOMPLETE_DUPLICATE_OR_REPLAY")
        found[name] = row["id"]
    need(set(found) == CI_NAMES, "POSTMERGE_FOUR_WORKFLOWS_REQUIRED")
    need(_source(get, target_sha) == tree,
         "SOURCE_MOVED_DURING_QUALIFICATION")
    return {
        "schema": "forge.f139.hybrid-v41.protected-main-source.v1",
        "source_sha": target_sha,
        "source_tree_sha": tree,
        "qualification_run_ids": dict(sorted(found.items())),
        "protected_main_verified": True,
        "merged_source_verified": True,
        "postmerge_ci_verified": True,
        "original_owner_mutations": 0,
        "owner_maintenance_authorized": False,
        "source_transition_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
    }
