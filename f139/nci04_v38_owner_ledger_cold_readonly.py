"""One owner-authenticated original Windows V38 ledger+cold-backup readback.

This existing-owner route never authorizes a source transition, task restart,
Hybrid admission, schema change, new queue, or scientific first-use. Release
custody is independent of the historical PR1759 source-commit eligibility
function: do not broaden that shared authority check.
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
from f139.nci04_v41_hybrid_original_commit import FIELDS as ORIGINAL_FIELDS
from f139 import nci04_v41_hybrid_original_commit as original_commit
from f139 import nci04_v41_hybrid_forward_owner_profile as profile
from f139 import nci04_v41_hybrid_forward_readiness as readiness
from f139 import nci04_v41_hybrid_forward_repair as forward
from f139 import nci04_v41_hybrid_owner_maintenance as owner

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
PR = 1771
BRANCH = "engineering/f139-v38-original-ledger-cold-readonly-20261115"
BASE = "882806e3d849183651f601b4b319ad95a23864f7"
PREV_COMMENT = 6892848524
PREV_RUN = 43703208070
PREV_SHA = "2e470aaeb061c6c0526e14f12bb89f753228b5a1"
PREV_BODY = ("F139-V38-ORIGINAL-TASK-SNAPSHOT-V5 " + PREV_SHA +
             " 6892675791")
FROZEN_COMMIT = 6883036903
PREFIX = "F139-V38-LEDGER-COLD-READONLY-V1 "
LABEL = "F139_V38_ORIGINAL_LEDGER_COLD="
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
DECIMAL = re.compile(r"[1-9][0-9]*\Z")
EXPECTED_JOBS = frozenset((
    "windows", "linux", "windows_native", "linux_native",
    "windows_f139", "linux_f139", "windows_genenv", "linux_genenv",
))
ALLOWED = frozenset((
    "PASS_READONLY_1830_COLD", "AUTH_DENIED", "PATH_OR_TASK_UNVERIFIED",
    "LEDGER_OR_COLD_UNVERIFIED", "POSTCHECK_UNVERIFIED", "UNCLASSIFIED",
))


class LedgerColdDenied(ValueError):
    pass


def need(condition):
    if not condition:
        raise LedgerColdDenied("F139_V38_LEDGER_COLD_FAIL_CLOSED")


def _comment(get, ident: int, expected: str):
    uri = "repos/" + REPO + "/issues/comments/" + str(ident)
    first, second = get(uri), get(uri)
    for obj in (first, second):
        need(type(obj) is dict and obj.get("id") == ident
             and obj.get("body") == expected
             and obj.get("author_association") == "OWNER"
             and type(obj.get("user")) is dict
             and obj["user"].get("login") == OWNER
             and type(obj.get("created_at")) is str)
    need(first["created_at"] == second["created_at"]
         and first.get("issue_url") == "https://api.github.com/repos/" +
             REPO + "/issues/807")
    return first


def _qualified_release(get, target):
    """Only PR1771 and its *one* protected-main merge can run this read."""
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
         and type(pr.get("base")) is dict
         and pr["base"].get("ref") == "main"
         and type(pr["base"].get("repo")) is dict
         and pr["base"]["repo"].get("full_name") == REPO)
    head = pr["head"].get("sha")
    need(type(head) is str and HEX40.fullmatch(head) is not None)
    merged = get(base + "git/commits/" + target)
    qualified = get(base + "git/commits/" + head)
    need(type(merged) is dict and merged.get("sha") == target
         and type(qualified) is dict and qualified.get("sha") == head
         and type(merged.get("tree")) is dict
         and type(qualified.get("tree")) is dict
         and merged["tree"].get("sha") == qualified["tree"].get("sha")
         and type(merged.get("parents")) is list
         and len(merged["parents"]) == 2
         and merged["parents"][0].get("sha") == BASE
         and merged["parents"][1].get("sha") == head)
    runs = get(base + "actions/runs?head_sha=" + target +
               "&event=push&branch=main&per_page=100")
    need(type(runs) is dict and type(runs.get("workflow_runs")) is list)
    qualified_runs = [r for r in runs["workflow_runs"]
                      if type(r) is dict and
                      r.get("name") == "FORGE public Linux and Windows qualification"]
    need(len(qualified_runs) == 1)
    run = qualified_runs[0]
    need(run.get("head_sha") == target
         and run.get("event") == "push"
         and run.get("status") == "completed"
         and run.get("conclusion") == "success"
         and run.get("run_attempt") == 1
         and type(run.get("id")) is int)
    jobs = get(base + "actions/runs/" + str(run["id"]) + "/jobs?per_page=100")
    need(type(jobs) is dict and jobs.get("total_count") == 8
         and type(jobs.get("jobs")) is list and len(jobs["jobs"]) == 8
         and {job.get("name") for job in jobs["jobs"]} == EXPECTED_JOBS
         and all(job.get("status") == "completed" and
                 job.get("conclusion") == "success" for job in jobs["jobs"]))
    return target


def _frozen_approval(get):
    obj = get("repos/" + REPO + "/issues/comments/" + str(FROZEN_COMMIT))
    need(type(obj) is dict and obj.get("id") == FROZEN_COMMIT
         and obj.get("author_association") == "OWNER"
         and type(obj.get("user")) is dict
         and obj["user"].get("login") == OWNER
         and type(obj.get("body")) is str
         and obj["body"].startswith(original_commit.PREFIX))
    body = obj["body"][len(original_commit.PREFIX):]
    need(len(body) <= 4000)
    try:
        frozen = json.loads(body, object_pairs_hook=decode_unique)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise LedgerColdDenied("F139_V38_FROZEN_APPROVAL_INVALID") from exc
    need(type(frozen) is dict and set(frozen) == ORIGINAL_FIELDS
         and canonical(frozen).decode("ascii") == body
         and frozen["schema"] == original_commit.SCHEMA
         and frozen["target_source_sha"] == forward.FROM
         and frozen["original_head_seq"] == 1829
         and frozen["original_head_sha256"] ==
             "55ded016778c8430bd4f6e3290972be1c5c5c796cbcb2a2ad38046283f78e3f8"
         and frozen["source_transition_requested"] is True
         and frozen["hybrid_admission"] is False
         and frozen["task_resume_authorized"] is False
         and frozen["policy_update_authorized"] is False
         and frozen["scientific_first_use"] is False
         and frozen["new_dispatches"] == 0)
    return frozen


def authenticate(get, env, event):
    """Exact owner comment and prior successful task snapshot, no write token."""
    need(callable(get) and type(env) is dict and type(event) is dict)
    target = env.get("GITHUB_SHA")
    need(type(target) is str and HEX40.fullmatch(target) is not None
         and target != BASE
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and type(env.get("GITHUB_RUN_ID")) is str
         and DECIMAL.fullmatch(env["GITHUB_RUN_ID"]) is not None
         and not env.get("OPENAI_API_KEY"))
    issue, sender, comment = (event.get(k) for k in ("issue", "sender", "comment"))
    body = PREFIX + target + " " + str(PREV_COMMENT)
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > PREV_COMMENT
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and comment.get("body") == body)
    current = _comment(get, comment["id"], body)
    previous = _comment(get, PREV_COMMENT, PREV_BODY)
    need(previous["created_at"] < current["created_at"])
    prev_run = get("repos/" + REPO + "/actions/runs/" + str(PREV_RUN))
    need(type(prev_run) is dict and prev_run.get("id") == PREV_RUN
         and prev_run.get("head_sha") == PREV_SHA
         and prev_run.get("event") == "issue_comment"
         and prev_run.get("run_attempt") == 1
         and prev_run.get("status") == "completed"
         and prev_run.get("conclusion") == "success"
         and type(prev_run.get("actor")) is dict
         and prev_run["actor"].get("login") == OWNER)
    prev_jobs = get("repos/" + REPO + "/actions/runs/" + str(PREV_RUN) +
                    "/jobs?per_page=100")
    need(type(prev_jobs) is dict and prev_jobs.get("total_count") == 1
         and type(prev_jobs.get("jobs")) is list
         and len(prev_jobs["jobs"]) == 1
         and prev_jobs["jobs"][0].get("name") ==
             "original-owner-readonly-task-snapshot"
         and prev_jobs["jobs"][0].get("status") == "completed"
         and prev_jobs["jobs"][0].get("conclusion") == "success")
    policy = owner._owner_policy(get)
    _qualified_release(get, target)
    frozen = _frozen_approval(get)
    return {"target": target, "policy": policy, "frozen": frozen,
            "comment": current["created_at"]}


def inspect_original(db_path, env, event, api, *,
                     readback=profile.readback,
                     inspect_held=readiness.inspect_held_original):
    """One held-lock original DB read; all logs are bounded classifications."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub and isinstance(db_path, Path))
    get = api.native_repo_get
    try:
        before = authenticate(get, env, event)
    except LedgerColdDenied:
        return "AUTH_DENIED"
    except Exception:
        return "AUTH_DENIED"
    try:
        path = owner._original_path(db_path, env)
        need(readback(path) is True)
    except Exception:
        return "PATH_OR_TASK_UNVERIFIED"
    try:
        with SingleOwner(path.with_suffix(".lock")):
            with closing(Database.open_readonly(path)) as db:
                result = inspect_held(db, before["frozen"])
                need(type(result) is dict
                     and result.get("classification") == "COMMITTED_SOURCE_HOLD"
                     and result.get("source_commit_recorded") is True
                     and result.get("event_seq") == forward.V37_SEQ
                     and result.get("event_head_sha256") == forward.V37_HEAD
                     and result.get("full_detached_cold_backup_verified") is True
                     and result.get("readback_database_mutations") == 0
                     and db.conn.total_changes == 0)
    except Exception:
        return "LEDGER_OR_COLD_UNVERIFIED"
    try:
        need(readback(path) is True
             and owner._owner_policy(get) == before["policy"]
             and authenticate(get, env, event) == before)
    except Exception:
        return "POSTCHECK_UNVERIFIED"
    return "PASS_READONLY_1830_COLD"


def main():
    """One-shot owner reading; never reveal private paths, errors or SQLite."""
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--target", required=True)
        args = parser.parse_args()
        env = dict(os.environ)
        need(args.target == env.get("GITHUB_SHA"))
        path = env.get("GITHUB_EVENT_PATH")
        need(type(path) is str and Path(path).is_file())
        event = json.loads(Path(path).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
        local = env.get("LOCALAPPDATA")
        need(type(local) is str and Path(local).is_absolute())
        db = Path(local) / "FORGE-F139" / "state.sqlite"
        result = inspect_original(db, env, event, GitHub())
    except Exception:
        result = "UNCLASSIFIED"
    if result not in ALLOWED:
        result = "UNCLASSIFIED"
    print(LABEL + result)
    return 0 if result == "PASS_READONLY_1830_COLD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
