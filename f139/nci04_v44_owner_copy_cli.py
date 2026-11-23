"""Authenticated one-shot original-host *disposable* event1836 rehearsal.

The live original task, SQLite, policy and source checkout are never mutated.
The only write is a fresh isolated SQLite copy under the owner data root.
The caller must additionally prove the original Windows task/SID/clean root.
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
from f139.nci04_owner_issue import decode_unique
from f139.nci04_native_contract import canonical
from f139.nci04_v41_original_owner_status import _read_only_owner_lease
from f139 import nci04_v42_owner_source_readiness as v42
from f139 import nci04_v44_event1836_copy_rehearsal as copy

PREFIX = "F139-V44-COPY-REHEARSAL "
PREDECESSOR_COMMENT_ID = 6916414055
PRIOR_BACKUP_RUN_ID = copy.BACKUP_RUN
SCHEMA = "forge.f139.v44.original-event1836-owner-copy-only.v1"


class OwnerCopyDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OwnerCopyDenied("F139_V44_OWNER_COPY_" + reason)


def intent(get, env, event):
    need(type(env) is dict and callable(get)
         and type(event) is dict
         and env.get("GITHUB_REPOSITORY") == v42.REPO
         and env.get("GITHUB_ACTOR") == v42.OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and not env.get("OPENAI_API_KEY")
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
         and type(env.get("GITHUB_SHA")) is str
         and copy.successor.SHA40.fullmatch(env["GITHUB_SHA"]) is not None
         and env["GITHUB_SHA"] != copy.RELEASE_SOURCE,
         "EXACT_ORIGINAL_OWNER_EVENT_REQUIRED")
    issue, sender, comment = [event.get(k) for k in (
        "issue", "sender", "comment")]
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and issue.get("user", {}).get("login") == v42.OWNER
         and type(sender) is dict
         and sender.get("login") == v42.OWNER
         and type(comment) is dict
         and type(comment.get("id")) is int
         and comment["id"] > PREDECESSOR_COMMENT_ID
         and comment.get("user", {}).get("login") == v42.OWNER
         and comment.get("author_association") == "OWNER"
         and comment.get("body") ==
             PREFIX + env["GITHUB_SHA"] + " " + copy.RELEASE_SOURCE +
             " " + str(PREDECESSOR_COMMENT_ID),
         "FRESH_OWNER_SOURCE_BOUND_COMMENT_REQUIRED")
    path = "repos/" + v42.REPO + "/issues/comments/"
    remote = get(path + str(comment["id"]))
    previous = get(path + str(PREDECESSOR_COMMENT_ID))
    need(type(remote) is dict
         and remote.get("id") == comment["id"]
         and remote.get("body") == comment["body"]
         and remote.get("created_at") == comment.get("created_at")
         and remote.get("updated_at") == comment.get("updated_at")
         and remote.get("author_association") == "OWNER"
         and remote.get("user", {}).get("login") == v42.OWNER
         and remote.get("issue_url") ==
             "https://api.github.com/repos/" + v42.REPO + "/issues/807"
         and type(previous) is dict
         and previous.get("id") == PREDECESSOR_COMMENT_ID
         and previous.get("user", {}).get("login") == v42.OWNER
         and previous.get("author_association") == "OWNER"
         and previous.get("body") ==
             "F139-V43-COLD-BACKUP " + copy.RELEASE_SOURCE +
             " 6913813568"
         and previous.get("created_at") < comment.get("created_at"),
         "PRIOR_REAL_BACKUP_AND_OWNER_INTENT_NOT_AUTHENTIC")
    source = v42.release_source(get, env["GITHUB_SHA"])
    base = "repos/" + v42.REPO + "/"
    prior = get(base + "actions/runs/" + str(PRIOR_BACKUP_RUN_ID))
    need(type(prior) is dict
         and prior.get("id") == PRIOR_BACKUP_RUN_ID
         and prior.get("head_sha") == copy.RELEASE_SOURCE
         and prior.get("status") == "completed"
         and prior.get("conclusion") == "success"
         and prior.get("run_attempt") == 1
         and prior.get("actor", {}).get("login") == v42.OWNER
         and prior.get("event") == "issue_comment"
         and prior.get("name") ==
             "FORGE G54 guarded V9 original-owner cutover",
         "PREDECESSOR_REAL_WINDOWS_BACKUP_RUN_REQUIRED")
    jobs = get(base + "actions/runs/" + str(PRIOR_BACKUP_RUN_ID) +
               "/jobs?per_page=100")
    need(type(jobs) is dict and type(jobs.get("jobs")) is list
         and type(jobs.get("total_count")) is int
         and jobs["total_count"] == len(jobs["jobs"])
         and sum(j.get("name") == "v43-original-owner-cold-backup"
                 and j.get("conclusion") == "success"
                 and j.get("status") == "completed"
                 and j.get("run_id") == PRIOR_BACKUP_RUN_ID
                 for j in jobs["jobs"] if type(j) is dict) == 1,
         "ORIGINAL_BACKUP_JOB_NOT_SUCCESSFUL")
    return (env["GITHUB_SHA"], int(env["GITHUB_RUN_ID"]),
            comment["id"], source)


def original_copy(path, env, event, api):
    need(sys.platform == "win32" and os.name == "nt"
         and isinstance(path, Path)
         and type(api) is GitHub,
         "ACTUAL_ORIGINAL_WINDOWS_OWNER_REQUIRED")
    get = api.native_repo_get
    request = intent(get, env, event)
    main_sha, run_id, comment_id, released = request
    appdata = env.get("LOCALAPPDATA")
    need(type(appdata) is str and Path(appdata).is_absolute()
         and path.is_absolute() and path.is_file()
         and not path.is_symlink() and path.resolve() ==
             (Path(appdata) / "FORGE-F139" / "state.sqlite").resolve(),
         "EXACT_CANONICAL_ORIGINAL_DATABASE_REQUIRED")
    policy = get("repos/" + v42.REPO + "/issues/807")
    def release_witness():
        return (v42.release_source(get, main_sha) == released
                and get("repos/" + v42.REPO + "/issues/807") == policy
                and intent(get, env, event) == request)
    need(release_witness(), "NEW_SOURCE_OR_ORIGINAL_POLICY_MOVED")
    root = path.parent / "isolated-v44-event1836-copies"
    need(not root.is_symlink()
         and not getattr(root, "is_junction", lambda: False)()
         and (not root.exists() or root.is_dir()),
         "DISPOSABLE_COPY_PARENT_UNSAFE")
    root.mkdir(parents=False, exist_ok=True)
    with _read_only_owner_lease(path):
        with closing(Database.open_readonly(path)) as original:
            before = original.meta().copy()
            def original_witness():
                return (original.meta() == before
                        and original.conn.total_changes == 0)
            receipt = copy.rehearse(
                original, owner_comment_id=comment_id, run_id=run_id,
                copy_path=root / str(run_id) / "rehearsal.sqlite",
                original_witness=original_witness,
                release_witness=release_witness)
            need(receipt["separate_copy_only"] is True
                 and receipt["copy_head_seq"] ==
                     copy.successor.PREDECESSOR_SEQ + 1
                 and receipt["original_sqlite_mutations"] == 0
                 and receipt["original_task_mutations"] == 0
                 and original_witness() is True,
                 "EVENT1836_COPY_FAILED_OR_ORIGINAL_DRIFT")
    need(release_witness(), "RELEASE_MOVED_AFTER_COPY")
    return {
        **receipt, "schema": SCHEMA,
        "workflow_source_sha": main_sha,
        "original_task_not_stopped": True,
        "original_policy_unchanged": True,
        "source_transition_authorized": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--workflow-source", required=True)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    need(args.workflow_source == env.get("GITHUB_SHA"),
         "WORKFLOW_SOURCE_NOT_PINNED")
    event_path = env.get("GITHUB_EVENT_PATH")
    need(type(event_path) is str and Path(event_path).is_absolute()
         and Path(event_path).is_file(), "REAL_OWNER_EVENT_FILE_REQUIRED")
    try:
        event = json.loads(Path(event_path).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
    except (OSError, ValueError, TypeError, UnicodeError) as err:
        raise OwnerCopyDenied(
            "F139_V44_OWNER_COPY_EVENT_PARSE_INVALID") from err
    receipt = original_copy(args.db, env, event, GitHub())
    print("F139_V44_ORIGINAL_COPY_REHEARSAL=" +
          canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        error = str(exc)
        if not re.fullmatch(r"F139_[A-Z0-9_]{1,160}", error):
            error = "F139_V44_OWNER_COPY_UNCLASSIFIED"
        print(error, file=sys.stderr)
        sys.exit(1)
