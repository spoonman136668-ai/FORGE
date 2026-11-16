"""Bounded original-owner event-1832 readiness and cold-backup admission.

These functions are *not registered* in Actions. A PR, a passing CI run, or
an issue comment grants no authority to activate, migrate, promote, schedule
or write any source event. Only a separately reviewed native owner entrypoint
may invoke them on FORGE-CODEX-REMOTE after full protected-main qualification.
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import re
import sys
import os
import shutil
import subprocess

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_event1833_successor as successor
from f139 import nci04_v41_hybrid_event1833_cold as cold
from f139 import nci04_v41_hybrid_event1832_postcommit as postcommit
from f139 import nci04_v41_hybrid_forward_readiness as previous_release
from f139 import nci04_v41_hybrid_owner_maintenance as owner
from f139 import nci04_v41_hybrid_forward_owner_profile as profile
from f139 import nci04_v41_hybrid_successor_release as shared

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
PR = 1777
BRANCH = "engineering/f139-v39-event1832-postwrite-canonical-readback-20261115"
PREDECESSOR_POSTCOMMIT_COMMENT_ID = 6902549450
PREDECESSOR_SOURCE_COMMIT_COMMENT_ID = 6902472106
READINESS = "F139-HYBRID-V40-READINESS "
BACKUP = "F139-HYBRID-V40-BACKUP "
CI = shared.CI


class Event1833OwnerDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise Event1833OwnerDenied("F139_V40_OWNER_" + reason)


def release(get, target):
    """Only owner PR #1774 after exact merged tree and full main regression."""
    need(callable(get) and type(target) is str
         and successor.SHA40.fullmatch(target) is not None
         and target != successor.SOURCE,
         "NEW_PROTECTED_SOURCE_REQUIRED")
    base = "repos/" + REPO + "/"
    main = get(base + "branches/main")
    pr = get(base + "pulls/" + str(PR))
    need(type(main) is dict and main.get("name") == "main"
         and main.get("protected") is True
         and type(main.get("commit")) is dict
         and main["commit"].get("sha") == target
         and type(pr) is dict and pr.get("number") == PR
         and pr.get("state") == "closed" and pr.get("merged") is True
         and pr.get("merge_commit_sha") == target
         and type(pr.get("user")) is dict
         and pr["user"].get("login") == OWNER
         and type(pr.get("head")) is dict
         and pr["head"].get("ref") == BRANCH
         and type(pr["head"].get("repo")) is dict
         and pr["head"]["repo"].get("full_name") == REPO
         and type(pr["head"].get("sha")) is str
         and successor.SHA40.fullmatch(pr["head"]["sha"]) is not None
         and type(pr.get("base")) is dict
         and pr["base"].get("ref") == "main"
         and type(pr["base"].get("repo")) is dict
         and pr["base"]["repo"].get("full_name") == REPO,
         "PR1776_MERGED_PROTECTED_MAIN_REQUIRED")
    cmp = get(base + "compare/" + successor.SOURCE + "..." + target +
              "?per_page=1&page=2")
    need(type(cmp) is dict and cmp.get("status") == "ahead"
         and type(cmp.get("ahead_by")) is int and cmp["ahead_by"] > 0
         and cmp.get("behind_by") == 0
         and type(cmp.get("merge_base_commit")) is dict
         and cmp["merge_base_commit"].get("sha") == successor.SOURCE,
         "EVENT1832_SOURCE_ANCESTRY_REQUIRED")
    head = pr["head"]["sha"]
    after = get(base + "git/commits/" + target)
    qualified = get(base + "git/commits/" + head)
    need(all(type(q) is dict and q.get("sha") == sha
             and type(q.get("tree")) is dict
             and type(q["tree"].get("sha")) is str
             and successor.SHA40.fullmatch(q["tree"]["sha"]) is not None
             for q, sha in ((after, target), (qualified, head)))
         and after["tree"]["sha"] == qualified["tree"]["sha"],
         "PROTECTED_RELEASE_TREE_NOT_QUALIFIED")
    runs = shared._runs(
        get, base + "actions/runs?head_sha=" + head +
        "&event=pull_request&per_page=100")
    passed = {}
    for run in runs:
        if type(run) is dict and run.get("name") in CI:
            name = run["name"]
            need(name not in passed and
                 shared._ci_run(run, head, "pull_request", BRANCH),
                 "NONUNIQUE_OR_UNQUALIFIED_PR_CI")
            passed[name] = run["id"]
    need(set(passed) == CI, "THREE_FINAL_PR_QUALIFICATIONS_REQUIRED")
    pushes = shared._runs(
        get, base + "actions/runs?head_sha=" + target +
        "&event=push&branch=main&per_page=100")
    main_ci = [x for x in pushes if type(x) is dict
               and x.get("name") == "FORGE public Linux and Windows qualification"]
    need(len(main_ci) == 1 and shared._ci_run(
        main_ci[0], target, "push", "main"),
        "PROTECTED_MAIN_FULL_REGRESSION_REQUIRED")
    need(get(base + "branches/main").get("commit", {}).get("sha") == target,
         "MAIN_MOVED_DURING_RELEASE_PROOF")
    return {
        "source_sha": target, "qualified_head_sha": head,
        "qualified_tree_sha": qualified["tree"]["sha"],
        "pr_qualification_runs": dict(sorted(passed.items())),
        "main_qualification_run": main_ci[0]["id"],
    }


def _native_event(get, env, event, prefix, suffix):
    need(callable(get) and type(env) is dict and type(event) is dict
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
         and not env.get("OPENAI_API_KEY"),
         "EXACT_ORIGINAL_OWNER_FIRST_ATTEMPT_REQUIRED")
    target = env.get("GITHUB_SHA")
    need(type(target) is str
         and successor.SHA40.fullmatch(target) is not None
         and target != successor.SOURCE,
         "FRESH_TARGET_SHA_REQUIRED")
    issue, sender, comment = (event.get(key) for key in (
        "issue", "sender", "comment"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and issue.get("user", {}).get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict
         and type(comment.get("id")) is int
         and comment["id"] > PREDECESSOR_POSTCOMMIT_COMMENT_ID
         and type(comment.get("body")) is str
         and comment["body"] == prefix + target + " " + str(suffix)
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == OWNER
         and comment.get("author_association") == "OWNER",
         "NEW_OWNER_EVENT_NOT_SOURCE_BOUND")
    timestamp = previous_release._owner_comment(
        get, comment["id"], comment["body"])
    need(timestamp == comment.get("created_at"),
         "EVENT_TIMESTAMP_NOT_AUTHENTIC")
    return target, comment, timestamp, issue, sender


def authenticate_readiness(get, env, event):
    target, comment, stamp, issue, sender = _native_event(
        get, env, event, READINESS, PREDECESSOR_POSTCOMMIT_COMMENT_ID)
    old_body = (postcommit.PREFIX + successor.SOURCE + " " +
                str(PREDECESSOR_SOURCE_COMMIT_COMMENT_ID))
    old_id = PREDECESSOR_POSTCOMMIT_COMMENT_ID
    old = get("repos/" + REPO + "/issues/comments/" + str(old_id))
    need(type(old) is dict and old.get("body") == old_body
         and previous_release._owner_comment(get, old_id, old_body) < stamp,
         "AUTHENTIC_EVENT1832_POSTCOMMIT_REQUIRED")
    return {
        "target_source_sha": target,
        "readiness_comment_id": comment["id"],
        "event1832_postcommit_comment_id": old_id,
    }


def authenticate_backup(get, env, event):
    need(type(event) is dict
         and type(event.get("comment")) is dict
         and type(event["comment"].get("body")) is str
         and type(env) is dict
         and type(env.get("GITHUB_SHA")) is str,
         "BACKUP_OWNER_EVENT_REQUIRED")
    target = env["GITHUB_SHA"]
    text = event["comment"]["body"]
    match = re.fullmatch(
        re.escape(BACKUP + target) + r" ([1-9][0-9]*)", text)
    need(match is not None, "EXACT_BACKUP_COMMENT_REQUIRED")
    previous_id = int(match.group(1))
    _, comment, stamp, issue, sender = _native_event(
        get, env, event, BACKUP, previous_id)
    need(PREDECESSOR_POSTCOMMIT_COMMENT_ID < previous_id < comment["id"],
         "DISTINCT_SEQUENTIAL_SOURCE_OWNER_EVENTS_REQUIRED")
    prior = get("repos/" + REPO + "/issues/comments/" + str(previous_id))
    prior_body = (
        READINESS + target + " " +
        str(PREDECESSOR_POSTCOMMIT_COMMENT_ID))
    need(type(prior) is dict and prior.get("body") == prior_body
         and previous_release._owner_comment(
             get, previous_id, prior_body) < stamp,
         "READINESS_AND_BACKUP_ORDER_OR_SCOPE_DRIFT")
    frozen = authenticate_readiness(get, env, {
        "action": "created", "issue": issue,
        "sender": sender, "comment": prior})
    need(frozen["target_source_sha"] == target
         and frozen["readiness_comment_id"] == previous_id,
         "BACKUP_NOT_BOUND_TO_NEW_READINESS")
    return {
        **frozen, "backup_comment_id": comment["id"],
        "backup_run_id": int(env["GITHUB_RUN_ID"]),
    }


def original_readiness(path, env, event, api):
    """Read-only actual original ledger/identity, never inferred from CI."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub and isinstance(path, Path),
         "WINDOWS_ORIGINAL_OWNER_REQUIRED")
    get = api.native_repo_get
    frozen = authenticate_readiness(get, env, event)
    target = frozen["target_source_sha"]
    release_proof = release(get, target)
    path = owner._original_path(path, env)
    owner._candidate_clean_checkout(target)
    policy = owner._owner_policy(get)
    profile.readback(path)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as db:
            before = successor._held_original(db)
            need(db.conn.total_changes == 0,
                 "READINESS_MODIFIED_ORIGINAL")
    need(profile.readback(path) is True
         and owner._owner_policy(get) == policy
         and owner._candidate_clean_checkout(target) is True
         and release(get, target) == release_proof
         and authenticate_readiness(get, env, event) == frozen,
         "ORIGINAL_READINESS_OWNER_SOURCE_MOVED")
    return {
        "schema": "forge.f139.v40.original-event1832-readiness.v1",
        **frozen,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "verified_historical_tasks": 153,
        "custodied_negative_tasks": 56,
        "original_owner_mutations": 0,
        "original_task_still_disabled": True,
        "hybrid_admission": False,
        "task_resume_authorized": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }



def stage_original_candidate(path, target):
    """Create-only or exact-key reuse of the existing owner's release checkout.

    The V40 activation job later verifies this exact clean local stage before
    changing the original task. Do not use an arbitrary mutable worktree.
    """
    need(sys.platform == "win32" and os.name == "nt"
         and type(path) is Path and path.is_absolute()
         and type(target) is str
         and successor.SHA40.fullmatch(target) is not None
         and SingleOwner.held(path.with_suffix(".lock")),
         "ORIGINAL_OWNER_STAGE_MUTEX_REQUIRED")
    from f139 import nci04_v41_hybrid_cold_bundle as bundles
    stage_root = path.parent / "release-candidates"
    stage = stage_root / target
    original = Path(__file__).resolve().parents[1]
    git = shutil.which("git")
    need(git is not None
         and stage.resolve().parent == stage_root.resolve()
         and all(bundles._nonlink(p) for p in (
             path.parent, *path.parents)),
         "NATIVE_RELEASE_STAGE_PARENT_UNSAFE")

    def run(*cmd):
        try:
            receipt = subprocess.run(
                [git, *cmd], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                timeout=240, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Event1833OwnerDenied(
                "F139_V40_OWNER_STAGE_GIT_UNQUALIFIED") from exc
        need(receipt.returncode == 0,
             "NATIVE_RELEASE_STAGE_GIT_FAILED")
        return receipt.stdout.decode("utf-8").strip()

    # Before staging, authenticate the exact fully committed native checkout.
    owner._candidate_clean_checkout(target)
    if not stage.exists() and not stage.is_symlink():
        need(not stage_root.is_symlink()
             and not getattr(stage_root, "is_junction", lambda: False)(),
             "NATIVE_STAGE_PARENT_LINK_DENIED")
        stage_root.mkdir(parents=True, exist_ok=True)
        need(not stage.exists() and not stage.is_symlink(),
             "NATIVE_STAGE_UNKNOWN_COLLISION")
        run("clone", "--quiet", "--no-hardlinks", "--no-checkout",
            str(original), str(stage))
        run("-C", str(stage), "checkout", "--quiet", "--detach", target)
    need(stage.is_dir() and not stage.is_symlink()
         and not getattr(stage, "is_junction", lambda: False)(),
         "NATIVE_STAGE_DIRECTORY_UNQUALIFIED")
    need(run("-C", str(stage), "rev-parse", "HEAD") == target
         and run("-C", str(stage), "status", "--porcelain",
                 "--untracked-files=all") == "",
         "NATIVE_STAGE_SOURCE_OR_CLEAN_TREE_DRIFT")
    return True

def original_backup(path, env, event, api):
    """One create-only real event-1832 backup, no source/task/policy mutation."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub and isinstance(path, Path),
         "WINDOWS_ORIGINAL_OWNER_REQUIRED")
    get = api.native_repo_get
    req = authenticate_backup(get, env, event)
    target = req["target_source_sha"]
    released = release(get, target)
    path = owner._original_path(path, env)
    owner._candidate_clean_checkout(target)
    policy = owner._owner_policy(get)
    def held_task():
        return profile.readback(path) is True
    def frozen_release():
        return (
            owner._candidate_clean_checkout(target) is True
            and owner._owner_policy(get) == policy
            and release(get, target) == released
            and authenticate_backup(get, env, event) == req)
    need(held_task() and frozen_release(),
         "ORIGINAL_OWNER_BACKUP_PRECONDITIONS_CHANGED")
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as db:
            before = successor._held_original(db)
            need(stage_original_candidate(path, target) is True
                 and held_task() and frozen_release(),
                 "STAGED_SOURCE_OR_ORIGINAL_HOLD_DRIFT")
            evidence = cold.stage_complete_cold_bundle(
                db, target=target, run_id=req["backup_run_id"],
                disabled_owner_witness=held_task,
                release_witness=frozen_release)
            proof = successor.build_proof(
                db, target=target, owner_event_id=req["readiness_comment_id"],
                backup_run_id=req["backup_run_id"],
                backup_manifest_sha256=evidence["backup_manifest_sha256"],
                backup_logical_all_tables_sha256=
                    evidence["backup_logical_all_tables_sha256"])
            want_hash = digest(canonical(proof))
            need(db.meta() == before and db.conn.total_changes == 0,
                 "BACKUP_MODIFIED_ORIGINAL_EVENT1832")
    need(held_task() and frozen_release(),
         "POSTBACKUP_NATIVE_OWNER_OR_RELEASE_MOVED")
    return {
        "schema": "forge.f139.v40.original-event1832-backup-only.v1",
        **req, "source_sha": successor.SOURCE,
        "original_head_seq": successor.PREDECESSOR_SEQ,
        "original_head_sha256": before["head_hash"],
        "backup_manifest_sha256": evidence["backup_manifest_sha256"],
        "backup_logical_all_tables_sha256":
            evidence["backup_logical_all_tables_sha256"],
        "expected_proof_sha256": want_hash,
        "detached_restore": evidence,
        "clean_candidate_staged": True,
        "original_owner_mutations": 0,
        "original_task_still_disabled": True,
        "task_resume_authorized": False,
        "owner_policy_update_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }


def main(argv=None):
    """Operator event only; not a runner, scheduler or background controller."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", choices=("readiness", "backup"),
                        required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    need(args.target == env.get("GITHUB_SHA"),
         "EXACT_PROTECTED_TARGET_REQUIRED")
    path = env.get("GITHUB_EVENT_PATH")
    need(type(path) is str and Path(path).is_file(),
         "EXACT_NATIVE_EVENT_REQUIRED")
    try:
        event = json.loads(Path(path).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
    except (ValueError, UnicodeError, OSError) as exc:
        raise Event1833OwnerDenied("F139_V40_OWNER_EVENT_PARSE") from exc
    need(type(env.get("LOCALAPPDATA")) is str
         and Path(env["LOCALAPPDATA"]).is_absolute(),
         "NATIVE_ORIGINAL_LOCALAPPDATA_REQUIRED")
    db = Path(env["LOCALAPPDATA"]) / "FORGE-F139" / "state.sqlite"
    if args.operation == "readiness":
        receipt = original_readiness(db, env, event, GitHub())
        marker = "F139_V39_ORIGINAL_EVENT1832_READINESS="
    else:
        receipt = original_backup(db, env, event, GitHub())
        marker = "F139_V39_ORIGINAL_EVENT1832_BACKUP="
    print(marker + canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
