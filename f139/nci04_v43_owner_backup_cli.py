"""One-shot V43 native original-owner cold backup; never task/source mutation.

Authorized only by a fresh owner-authored issue #807 comment. The workflow
authenticates the actual Windows task SID and source root independently.
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
from f139.nci04_v41_original_owner_status import _read_only_owner_lease
from f139 import nci04_v42_owner_source_readiness as readiness
from f139 import nci04_v43_event1835_cold as cold

SCHEMA = "forge.f139.v43.original-event1835-cold-backup-only.v1"
PREFIX = "F139-V43-COLD-BACKUP "
PREVIOUS_READ_COMMENT_ID = 6913813568


class OriginalBackupDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise OriginalBackupDenied("F139_V43_OWNER_BACKUP_" + code)


def intent(get, env, event):
    need(type(env) is dict and type(event) is dict
         and callable(get)
         and env.get("GITHUB_REPOSITORY") == readiness.REPO
         and env.get("GITHUB_ACTOR") == readiness.OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
         and not env.get("OPENAI_API_KEY"),
         "EXACT_ORIGINAL_OWNER_RUNNER_REQUIRED")
    target = env.get("GITHUB_SHA")
    need(type(target) is str
         and readiness.SHA40.fullmatch(target) is not None
         and target != readiness.BEFORE,
         "QUALIFIED_MAIN_TARGET_REQUIRED")
    issue, sender, comment = (
        event.get(k) for k in ("issue", "sender", "comment"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and issue.get("user", {}).get("login") == readiness.OWNER
         and type(sender) is dict
         and sender.get("login") == readiness.OWNER
         and type(comment) is dict
         and type(comment.get("id")) is int
         and comment["id"] > PREVIOUS_READ_COMMENT_ID
         and comment.get("user", {}).get("login") == readiness.OWNER
         and comment.get("author_association") == "OWNER"
         and comment.get("body") ==
             PREFIX + target + " " + str(PREVIOUS_READ_COMMENT_ID),
         "FRESH_ISSUE807_OWNER_COMMENT_REQUIRED")
    route = ("repos/" + readiness.REPO + "/issues/comments/" +
             str(comment["id"]))
    remote = get(route)
    need(type(remote) is dict
         and remote.get("id") == comment["id"]
         and remote.get("issue_url") ==
             "https://api.github.com/repos/" + readiness.REPO +
             "/issues/807"
         and remote.get("user", {}).get("login") == readiness.OWNER
         and remote.get("author_association") == "OWNER"
         and remote.get("body") == comment["body"]
         and remote.get("created_at") == comment.get("created_at")
         and remote.get("updated_at") == comment.get("updated_at"),
         "REMOTE_OWNER_INTENT_NOT_AUTHENTICATED")
    # The fresh comment must follow the actual previous successful readback.
    previous = get("repos/" + readiness.REPO +
                   "/issues/comments/" + str(PREVIOUS_READ_COMMENT_ID))
    need(type(previous) is dict
         and previous.get("user", {}).get("login") == readiness.OWNER
         and previous.get("body") ==
             "F139-V42-ORIGINAL-READONLY "
             "42ddb373b4dbbf31ea36b08f585e5c5cdc706b9f "
             "6912162079"
         and previous.get("created_at") < comment.get("created_at"),
         "EXACT_PRIOR_OWNER_READBACK_NOT_AUTHENTICATED")
    return target, int(env["GITHUB_RUN_ID"]), comment["id"]


def original_backup(db_path, env, event, api):
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub
         and isinstance(db_path, Path),
         "ACTUAL_WINDOWS_OWNER_REQUIRED")
    get = api.native_repo_get
    target, run_id, comment_id = intent(get, env, event)
    source = readiness.release_source(get, target)
    path = db_path
    expected = Path(env.get("LOCALAPPDATA", "")) / "FORGE-F139" / "state.sqlite"
    need(path.is_absolute() and path.name == "state.sqlite"
         and path.is_file() and not path.is_symlink()
         and expected.is_absolute()
         and expected.resolve() == path.resolve(),
         "ORIGINAL_DATABASE_CANONICAL_PATH")
    before_policy = get("repos/" + readiness.REPO + "/issues/807")
    def still_released():
        return (readiness.release_source(get, target) == source
                and get("repos/" + readiness.REPO + "/issues/807") ==
                    before_policy
                and intent(get, env, event) == (
                    target, run_id, comment_id))
    need(still_released(), "REMOTE_SOURCE_OR_OWNER_POLICY_DRIFT")
    with _read_only_owner_lease(path):
        with closing(Database.open_readonly(path)) as original:
            before = original.meta().copy()
            def still_original():
                return (original.meta() == before
                        and original.conn.total_changes == 0)
            receipt = cold.stage_full_backup(
                original, target=target, run_id=run_id,
                release_witness=still_released,
                original_witness=still_original)
            need(original.meta() == before
                 and original.conn.total_changes == 0
                 and receipt["source_transition_authorized"] is False
                 and receipt["independent_detached_restore_verified"] is True,
                 "ORIGINAL_BACKUP_NOT_VERIFIED")
    need(still_released(), "REMOTE_OR_POLICY_CHANGED_AFTER_BACKUP")
    return {
        "schema": SCHEMA, "target_source_sha": target,
        "original_source_sha": readiness.BEFORE,
        "original_head_seq": readiness.FROZEN_SEQ,
        "original_head_sha256": readiness.FROZEN_HEAD,
        "owner_comment_id": comment_id, "backup_run_id": run_id,
        "backup_manifest_sha256": receipt["backup_manifest_sha256"],
        "backup_logical_all_tables_sha256":
            receipt["backup_logical_all_tables_sha256"],
        "independent_detached_restore_verified": True,
        "original_owner_mutations": 0,
        "owner_task_mutations": 0,
        "source_transition_authorized": False,
        "task_restart_authorized": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    need(args.target == env.get("GITHUB_SHA"), "TARGET_EVENT_DRIFT")
    path = env.get("GITHUB_EVENT_PATH")
    need(type(path) is str and Path(path).is_absolute()
         and Path(path).is_file(), "ISSUE_EVENT_FILE_REQUIRED")
    try:
        event = json.loads(Path(path).read_text(encoding="utf-8"),
                           object_pairs_hook=decode_unique)
    except (ValueError, UnicodeError, OSError, TypeError) as exc:
        raise OriginalBackupDenied(
            "F139_V43_OWNER_BACKUP_EVENT_INVALID") from exc
    receipt = original_backup(args.db, env, event, GitHub())
    print("F139_V43_ORIGINAL_BACKUP=" +
          json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        error = str(exc)
        if not re.fullmatch(r"F139_[A-Z0-9_]{1,150}", error):
            error = "F139_V43_OWNER_BACKUP_UNCLASSIFIED"
        print(error, file=sys.stderr)
        sys.exit(1)
