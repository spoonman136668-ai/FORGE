"""Inert original-owner V38 forward-repair release/readiness qualification.

Read-only: authenticate a NEW owner readiness intent, verified merged release,
original disabled task, sealed V37 #1830 hold and its cold backup. No backup
creation, commit, policy writes, scheduled-task operations or science first-use.
This is NOT a registered workflow or a source-commit approval.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sys

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_successor_release as old_release
from f139 import nci04_v41_hybrid_owner_maintenance as owner
from f139 import nci04_v41_hybrid_forward_owner_profile as profile
from f139 import nci04_v41_hybrid_original_commit as old_commit
from f139 import nci04_v41_hybrid_held_recovery as held
from f139 import nci04_v41_hybrid_forward_repair as forward

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
PR = 1773
BRANCH = "engineering/f139-v38-forward-original-owner-concurrency-v2-20261115"
PREFIX = "F139-HYBRID-V41-FORWARD-READINESS "
OLD_COMMIT_ID = 6883036903
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
CI = old_release.CI


class ForwardReadinessDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise ForwardReadinessDenied("F139_HYBRID_FORWARD_READINESS_" + reason)


def _release(get, target):
    """Require exact protected successor of original V37 hold and source CI."""
    need(callable(get) and type(target) is str
         and SHA40.fullmatch(target) is not None
         and target != forward.FROM,
         "NEW_TARGET_REQUIRED")
    route = "repos/" + REPO + "/"
    main = get(route + "branches/main")
    pr = get(route + "pulls/" + str(PR))
    need(type(main) is dict and main.get("name") == "main"
         and main.get("protected") is True
         and type(main.get("commit")) is dict
         and main["commit"].get("sha") == target
         and type(pr) is dict and pr.get("number") == PR
         and pr.get("merged") is True and pr.get("state") == "closed"
         and pr.get("merge_commit_sha") == target
         and type(pr.get("user")) is dict
         and pr["user"].get("login") == OWNER
         and type(pr.get("head")) is dict
         and pr["head"].get("ref") == BRANCH
         and type(pr["head"].get("repo")) is dict
         and pr["head"]["repo"].get("full_name") == REPO
         and type(pr["head"].get("sha")) is str
         and SHA40.fullmatch(pr["head"]["sha"]) is not None
         and type(pr.get("base")) is dict
         and pr["base"].get("ref") == "main"
         and type(pr["base"].get("repo")) is dict
         and pr["base"]["repo"].get("full_name") == REPO,
         "MERGED_PR1773_PROTECTED_MAIN_REQUIRED")
    head = pr["head"]["sha"]
    compare = get(route + "compare/" + forward.FROM + "..." + target +
                  "?per_page=1&page=2")
    need(type(compare) is dict and compare.get("status") == "ahead"
         and type(compare.get("ahead_by")) is int
         and compare["ahead_by"] > 0
         and compare.get("behind_by") == 0
         and type(compare.get("merge_base_commit")) is dict
         and compare["merge_base_commit"].get("sha") == forward.FROM,
         "COMMITTED_V37_ANCESTRY_REQUIRED")
    original = get(route + "git/commits/" + target)
    qualified = get(route + "git/commits/" + head)
    need(all(type(x) is dict and x.get("sha") == sha
             and type(x.get("tree")) is dict
             and type(x["tree"].get("sha")) is str
             and SHA40.fullmatch(x["tree"]["sha"]) is not None
             for x, sha in ((original, target), (qualified, head)))
         and original["tree"]["sha"] == qualified["tree"]["sha"],
         "MERGED_TREE_DIFFERS_FROM_QUALIFIED_PR")
    runs = old_release._runs(
        get, route + "actions/runs?head_sha=" + head +
        "&event=pull_request&per_page=100")
    passed = {}
    for record in runs:
        if type(record) is dict and record.get("name") in CI:
            name = record["name"]
            need(name not in passed and old_release._ci_run(
                record, head, "pull_request", BRANCH),
                "PR_CI_NOT_UNIQUE_FIRST_ATTEMPT_PASS")
            passed[name] = record["id"]
    need(set(passed) == CI, "ALL_PR_QUALIFICATION_REQUIRED")
    pushes = old_release._runs(
        get, route + "actions/runs?head_sha=" + target +
        "&event=push&branch=main&per_page=100")
    main_ci = [p for p in pushes if type(p) is dict and p.get("name") ==
               "FORGE public Linux and Windows qualification"]
    need(len(main_ci) == 1 and old_release._ci_run(
        main_ci[0], target, "push", "main"),
        "POSTMERGE_FULL_MAIN_REGRESSION_REQUIRED")
    need(get(route + "branches/main").get("commit", {}).get("sha") == target,
         "MAIN_MOVED_DURING_RELEASE_READBACK")
    return {"target_source_sha": target, "qualified_pr_sha": head,
            "tree_sha": qualified["tree"]["sha"],
            "pr_qualification_runs": dict(sorted(passed.items())),
            "main_qualification_run": main_ci[0]["id"]}


def _owner_comment(get, comment_id, body):
    """Use native provider twice; never infer owner authority from a PR."""
    need(type(comment_id) is int and comment_id > 0
         and type(body) is str and bool(body), "OWNER_COMMENT_REQUIRED")
    uri = "repos/" + REPO + "/issues/comments/" + str(comment_id)
    first = get(uri)
    second = get(uri)
    for doc in (first, second):
        need(type(doc) is dict and doc.get("id") == comment_id
             and doc.get("body") == body
             and doc.get("author_association") == "OWNER"
             and type(doc.get("user")) is dict
             and doc["user"].get("login") == OWNER
             and doc.get("issue_url") ==
             "https://api.github.com/repos/" + REPO + "/issues/807"
             and type(doc.get("created_at")) is str,
             "ORIGINAL_OWNER_COMMENT_PROVIDER_DRIFT")
    need(first["created_at"] == second["created_at"],
         "OWNER_COMMENT_TIMESTAMP_MOVED")
    return first["created_at"]


def authenticate_readiness(get, env, event, target):
    """Distinct new first-attempt owner comment; zero mutation authority."""
    need(type(env) is dict and type(event) is dict and callable(get)
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_SHA") == target
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
         and not env.get("OPENAI_API_KEY"),
         "NATIVE_FIRST_ATTEMPT_RUNNER_REQUIRED")
    issue, sender, comment = (event.get(k) for k in ("issue", "sender", "comment"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == OWNER
         and "pull_request" not in issue
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict
         and type(comment.get("id")) is int
         and comment["id"] > OLD_COMMIT_ID
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and type(comment.get("body")) is str
         and comment["body"] == PREFIX + target + " " + str(OLD_COMMIT_ID),
         "NEW_EXACT_FORWARD_READINESS_COMMENT_REQUIRED")
    first = _owner_comment(get, comment["id"], comment["body"])
    prior = get("repos/" + REPO + "/issues/comments/" + str(OLD_COMMIT_ID))
    need(type(prior) is dict and type(prior.get("body")) is str
         and prior["body"].startswith(old_commit.PREFIX)
         and type(prior.get("user")) is dict
         and prior["user"].get("login") == OWNER,
         "V37_ORIGINAL_COMMIT_NOT_AVAILABLE")
    _owner_comment(get, OLD_COMMIT_ID, prior["body"])
    need(prior.get("created_at") < first,
         "FORWARD_APPROVAL_PRECEDES_ORIGINAL_SOURCE_COMMIT")
    try:
        frozen = json.loads(
            prior["body"][len(old_commit.PREFIX):],
            object_pairs_hook=decode_unique)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ForwardReadinessDenied(
            "F139_HYBRID_FORWARD_READINESS_OLD_COMMIT_PARSE") from exc
    need(type(frozen) is dict
         and set(frozen) == old_commit.FIELDS
         and canonical(frozen).decode("ascii") ==
             prior["body"][len(old_commit.PREFIX):]
         and frozen["schema"] == old_commit.SCHEMA
         and frozen["target_source_sha"] == forward.FROM
         and frozen["original_head_seq"] == 1829
         and frozen["original_head_sha256"] ==
             "55ded016778c8430bd4f6e3290972be1c5c5c796cbcb2a2ad38046283f78e3f8"
         and frozen["source_transition_requested"] is True
         and frozen["new_dispatches"] == 0
         and all(frozen[key] is False for key in (
             "task_resume_authorized", "policy_update_authorized",
             "hybrid_admission", "scientific_first_use")),
         "FROZEN_V37_SOURCE_APPROVAL_DRIFT")
    return frozen


def inspect_held_original(db, frozen):
    """Independent original mutex and true full cold backup replay."""
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "READONLY_ORIGINAL_MUTEX_REQUIRED")
    result = held.inspect_held_ledger(db, frozen)
    need(result["classification"] == "COMMITTED_SOURCE_HOLD"
         and result["source_commit_recorded"] is True
         and result["event_seq"] == forward.V37_SEQ
         and result["event_head_sha256"] == forward.V37_HEAD
         and result["full_detached_cold_backup_verified"] is True
         and result["readback_database_mutations"] == 0
         and result["scientific_first_use"] is False
         and db.conn.total_changes == 0,
         "EXACT_SOURCE_COMMITTED_1830_EVENT_REQUIRED")
    return result


def read_only_original_preflight(db_path, env, event, api):
    """Caller-only original native host preflight; no workflow registration."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub and isinstance(db_path, Path),
         "ORIGINAL_WINDOWS_NATIVE_PROVIDER_REQUIRED")
    target = env.get("GITHUB_SHA")
    get = api.native_repo_get
    frozen = authenticate_readiness(get, env, event, target)
    release = _release(get, target)
    original = owner._original_path(db_path, env)
    owner._candidate_clean_checkout(target)
    policy = owner._owner_policy(get)
    profile.readback(original)
    with SingleOwner(original.with_suffix(".lock")):
        with closing(Database.open_readonly(original)) as readonly:
            result = inspect_held_original(readonly, frozen)
    need(profile.readback(original) is True
         and owner._owner_policy(get) == policy
         and _release(get, target) == release
         and authenticate_readiness(get, env, event, target) == frozen,
         "POSTREADBACK_ORIGINAL_TASK_POLICY_OR_SOURCE_DRIFT")
    return {
        "schema": "forge.f139.hybrid-forward.original-readonly-preflight.v1",
        "target_source_sha": target,
        "original_source_sha": forward.FROM,
        "original_event_seq": forward.V37_SEQ,
        "original_event_head_sha256": forward.V37_HEAD,
        "release": release,
        "original": result,
        "fresh_v38_backup_completed": False,
        "forward_source_commit_authorized": False,
        "task_restart_authorized": False,
        "policy_update_authorized": False,
        "native_activated": False,
        "scientific_first_use": False,
        "original_database_mutations": 0,
        "new_dispatches": 0,
    }


def main(argv=None):
    """Read-only manually invoked owner entrypoint, not a job registration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    need(type(env.get("GITHUB_SHA")) is str
         and args.target == env["GITHUB_SHA"]
         and SHA40.fullmatch(args.target) is not None,
         "EXACT_SHA_ARGUMENT_REQUIRED")
    path = env.get("GITHUB_EVENT_PATH")
    need(type(path) is str and Path(path).is_file(),
         "ORIGINAL_OWNER_EVENT_FILE_REQUIRED")
    try:
        event = json.loads(Path(path).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
    except (UnicodeError, ValueError, OSError) as error:
        raise ForwardReadinessDenied(
            "F139_HYBRID_FORWARD_READINESS_EVENT_NOT_CANONICAL") from error
    need(type(env.get("LOCALAPPDATA")) is str
         and Path(env["LOCALAPPDATA"]).is_absolute(),
         "ORIGINAL_OWNER_LOCAL_DATA_REQUIRED")
    database = Path(env["LOCALAPPDATA"]) / "FORGE-F139" / "state.sqlite"
    receipt = read_only_original_preflight(database, env, event, GitHub())
    print("F139_HYBRID_FORWARD_READONLY_PREFLIGHT=" +
          canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
