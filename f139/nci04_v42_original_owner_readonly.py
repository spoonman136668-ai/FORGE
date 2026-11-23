"""Owner-authenticated, single-shot V42 *read-only* original Windows preflight.

This module is called only from the existing F139 G54 workflow's independent
issue-comment status job. It cannot create work, pause/restart the scheduled
task, commit source events, modify policy or authorize scientific first-use.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sys

from f139.local_controller import Database, GitHub
from f139.nci04_v41_original_owner_status import _read_only_owner_lease
from f139 import nci04_v42_owner_source_readiness as readiness

PREFIX = "F139-V42-ORIGINAL-READONLY "
PREDECESSOR_COMMENT_ID = 6912162079
SCHEMA = "forge.f139.v42.original-owner-live-readonly-receipt.v1"


class V42OriginalReadOnlyDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise V42OriginalReadOnlyDenied("F139_V42_OWNER_READONLY_" + reason)


def authenticate(env, event, target):
    """No owner authority inferred from the actor alone or an old comment."""
    need(type(env) is dict and type(event) is dict
         and type(target) is str and readiness.SHA40.fullmatch(target)
         and env.get("GITHUB_REPOSITORY") == readiness.REPO
         and env.get("GITHUB_ACTOR") == readiness.OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_SHA") == target
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
         and not env.get("OPENAI_API_KEY"),
         "EXACT_ORIGINAL_RUNNER_EVENT_REQUIRED")
    issue = event.get("issue")
    sender = event.get("sender")
    comment = event.get("comment")
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and issue.get("user", {}).get("login") == readiness.OWNER
         and type(sender) is dict
         and sender.get("login") == readiness.OWNER
         and type(comment) is dict
         and type(comment.get("id")) is int
         and comment["id"] > PREDECESSOR_COMMENT_ID
         and comment.get("user", {}).get("login") == readiness.OWNER
         and comment.get("author_association") == "OWNER"
         and comment.get("body") ==
             PREFIX + target + " " + str(PREDECESSOR_COMMENT_ID),
         "EXACT_NEW_OWNER_READONLY_INTENT_REQUIRED")
    return True


def inspect(db_path, env, event, *, target, get):
    """Cold single-owner query-only proof; *never* writes owner task or SQLite."""
    authenticate(env, event, target)
    path = Path(db_path)
    expected = Path(env.get("LOCALAPPDATA", "")) / "FORGE-F139" / "state.sqlite"
    need(path.is_absolute() and path.name == "state.sqlite"
         and path.is_file() and not path.is_symlink()
         and expected.is_absolute() and expected.resolve() == path.resolve(),
         "CANONICAL_ORIGINAL_DATABASE_REQUIRED")
    first = readiness.release_source(get, target)
    with _read_only_owner_lease(path):
        with closing(Database.open_readonly(path)) as db:
            with db.conn:
                result = readiness.original_owner_cold_read(db)
    # Repeat moving evidence after exiting exclusive original mutex.
    second = readiness.release_source(get, target)
    need(first == second and first["target_source_sha"] == target
         and result["original_source_sha"] == readiness.BEFORE
         and result["original_head_seq"] == readiness.FROZEN_SEQ
         and result["original_head_sha256"] == readiness.FROZEN_HEAD
         and result["original_owner_mutations"] == 0,
         "ORIGINAL_OR_REMOTE_CHANGED_DURING_READ")
    return {
        "schema": SCHEMA,
        "original_source_sha": readiness.BEFORE,
        "target_source_sha": target,
        "original_head_seq": result["original_head_seq"],
        "original_head_sha256": result["original_head_sha256"],
        "historical_verified": result["verified_tasks"],
        "historical_quarantined": result["quarantined_tasks"],
        "historical_issue_1715_unadmitted": not result["pending_issue_admitted"],
        "main_qualification_run_id": first["main_qualification_run_id"],
        "main_qualification_job_count": first["main_qualification_job_count"],
        "sqlite_query_only": True,
        "original_owner_mutations": 0,
        "source_transition_authorized": False,
        "task_pause_authorized": False,
        "task_restart_authorized": False,
        "new_dispatches": 0,
        "scientific_first_use": False,
    }


def main(argv=None, *, env=None, event=None, get=None):
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--target", required=True)
    args = p.parse_args(argv)
    env = dict(os.environ) if env is None else env
    if event is None:
        try:
            raw = Path(env["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8")
            event = json.loads(raw)
        except (KeyError, OSError, ValueError, UnicodeError) as exc:
            raise V42OriginalReadOnlyDenied(
                "F139_V42_OWNER_READONLY_OWNER_EVENT_FILE_INVALID") from exc
    api = None if get is not None else GitHub()
    report = inspect(args.db, env, event, target=args.target,
                     get=api.native_repo_get if get is None else get)
    print("F139_V42_ORIGINAL_OWNER_READONLY=" +
          json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        reason = str(exc)
        # Never expose private paths, tokens, provider bodies or SQLite content.
        if not re.fullmatch(r"F139_[A-Z0-9_]{1,120}", reason):
            reason = "F139_V42_OWNER_READONLY_UNCLASSIFIED"
        print(reason, file=sys.stderr)
        sys.exit(1)
