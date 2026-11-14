"""Original V41 PAUSE-HOLD safe-abort preflight (READ ONLY).

A distinct OWNER SAFE-ABORT comment cannot be substituted for PAUSE-HOLD,
PAUSE-RESUME, source-readiness, source-commit or scientific authority. This
module makes no scheduled-task, SQLite, policy or external write. The optional
UNREGISTERED Windows wrapper owns any separately approved same-task restart.
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
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_cold_bundle as cold
from f139 import nci04_v41_hybrid_source_transition as source
from f139 import nci04_v41_hybrid_owner_maintenance as owner
from f139 import nci04_v41_hybrid_successor_release as release
from f139 import nci04_v41_hybrid_pair_owner as pair

SCHEMA = "forge.f139.hybrid-v41.original-safe-abort-preflight.v1"
PREFIX = "F139-HYBRID-V41-SAFE-ABORT "
PATTERN = re.compile(
    re.escape(PREFIX) + r"([a-f0-9]{40}) ([1-9][0-9]*) "
    r"([1-9][0-9]*) ([a-f0-9]{64}) "
    r"([1-9][0-9]*) ([a-f0-9]{64})\Z")


class SafeAbortDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise SafeAbortDenied("F139_HYBRID_V41_SAFE_ABORT_" + reason)


def authenticate_abort(env, event, get):
    """Four unedited comments in chronological order, distinct new ABORT."""
    need(type(env) is dict and type(event) is dict and callable(get)
         and env.get("GITHUB_REPOSITORY") == release.REPO
         and env.get("GITHUB_ACTOR") == release.OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
         and not env.get("OPENAI_API_KEY"),
         "EXACT_FIRST_ATTEMPT_ORIGINAL_OWNER_EVENT_REQUIRED")
    issue, sender, comment = [event.get(key) for key in
                              ("issue", "sender", "comment")]
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == release.OWNER
         and type(sender) is dict and sender.get("login") == release.OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > 0 and type(comment.get("body")) is str
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == release.OWNER
         and comment.get("author_association") == "OWNER"
         and type(comment.get("created_at")) is str
         and release.STAMP.fullmatch(comment["created_at"]),
         "SEPARATE_OWNER_ABORT_COMMENT_REQUIRED")
    match = PATTERN.fullmatch(comment["body"])
    need(match is not None, "CANONICAL_ABORT_REQUEST_REQUIRED")
    target, approval, run, manifest, seq, head = match.groups()
    approval_id, run_id, head_seq = map(int, (approval, run, seq))
    need(env.get("GITHUB_SHA") == target
         and target != source.FROM_V41
         and run_id != int(env["GITHUB_RUN_ID"])
         and approval_id not in (comment["id"], run_id)
         and head_seq >= source.ACTIVATED_SEQ,
         "TARGET_RUN_OR_ORIGINAL_HEAD_INVALID")
    # Four different observations: BACKUP, HOLD approval, new ABORT and
    # the independent release/source identity. No old PAUSE-RESUME reuse.
    for _ in range(2):
        abort_stamp = release._comment(get, comment["id"], comment["body"])
        need(abort_stamp == comment["created_at"],
             "ABORT_OWNER_COMMENT_MOVED")
        raw_hold = get("repos/" + release.REPO + "/issues/comments/" +
                       str(approval_id))
        need(type(raw_hold) is dict and type(raw_hold.get("body")) is str
             and raw_hold.get("updated_at") == raw_hold.get("created_at"),
             "HOLD_OWNER_APPROVAL_EDITED")
        parsed = pair.HOLD_COMMENT_RE.fullmatch(raw_hold["body"])
        need(parsed is not None and parsed.group(1) == target
             and int(parsed.group(2)) not in (approval_id, comment["id"]),
             "EXACT_PAUSE_HOLD_CHAIN_REQUIRED")
        backup_id = int(parsed.group(2))
        hold_stamp = release._comment(get, approval_id, raw_hold["body"])
        backup_stamp = release._comment(
            get, backup_id, owner.PREFIX + target)
        need(backup_stamp < hold_stamp < abort_stamp
             and type(raw_hold.get("id")) is int
             and raw_hold["id"] == approval_id,
             "BACKUP_HOLD_ABORT_ORDER_OR_IDENTITY_DRIFT")
        backup = get("repos/" + release.REPO + "/issues/comments/" +
                     str(backup_id))
        need(type(backup) is dict
             and backup.get("updated_at") == backup.get("created_at"),
             "BACKUP_REQUEST_EDITED")
    return {
        "target_source_sha": target,
        "hold_approval_comment_id": approval_id,
        "backup_request_comment_id": backup_id,
        "abort_owner_comment_id": comment["id"],
        "backup_run_id": run_id,
        "backup_manifest_sha256": manifest,
        "original_head_seq": head_seq,
        "original_head_sha256": head,
        "safe_abort_requested": True,
        "source_transition_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
    }


def inspect_precommit(db, request):
    """Prove V41 and ENTIRE SQLite logical contents match frozen cold backup."""
    need(type(db) is Database and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and type(request) is dict
         and request.get("safe_abort_requested") is True
         and type(request.get("target_source_sha")) is str
         and source.HEX40.fullmatch(request["target_source_sha"]) is not None
         and type(request.get("backup_run_id")) is int
         and request["backup_run_id"] > 0
         and type(request.get("original_head_seq")) is int
         and request["original_head_seq"] >= source.ACTIVATED_SEQ
         and type(request.get("original_head_sha256")) is str
         and source.HEX64.fullmatch(request["original_head_sha256"])
         and type(request.get("backup_manifest_sha256")) is str
         and source.HEX64.fullmatch(request["backup_manifest_sha256"]),
         "ORIGINAL_LOCKED_READONLY_FROZEN_REQUEST_REQUIRED")
    before = source._original(db)
    need(before["head_seq"] == request["original_head_seq"]
         and before["head_hash"] == request["original_head_sha256"]
         and db.conn.execute(
             "SELECT COUNT(*) FROM events WHERE seq>?",
             (before["head_seq"],)).fetchone()[0] == 0,
         "V41_UNCHANGED_PREIMAGE_REQUIRED")
    folder = db.filename.parent / (
        "f139-hybrid-before-" + str(request["backup_run_id"]))
    receipt = cold.verify_detached_restore(
        folder, expected_manifest_sha256=request["backup_manifest_sha256"],
        target_sha=request["target_source_sha"],
        run_id=request["backup_run_id"],
        expected_head_seq=before["head_seq"],
        expected_head_sha256=before["head_hash"])
    need(type(receipt) is dict
         and receipt.get("independent_detached_restore_verified") is True
         and receipt.get("provider_archives_bytes_verified") is True
         and receipt.get("generation_binary_bytes_verified") is True
         and receipt.get("original_owner_mutations") == 0
         and receipt.get("source_transition_authorized") is False
         and receipt.get("hybrid_admission") is False
         and receipt.get("scientific_first_use") is False
         and type(receipt.get("logical_all_tables_sha256")) is str
         and source.HEX64.fullmatch(receipt["logical_all_tables_sha256"]),
         "COMPLETE_FROZEN_DETACHED_RESTORE_REQUIRED")
    actual = digest(canonical(cold.rollback_view(db.conn)))
    need(actual == receipt["logical_all_tables_sha256"],
         "COMPLETE_SQLITE_CONTENT_NOT_IDENTICAL_TO_COLD_BACKUP")
    need(db.meta() == before and db.conn.total_changes == 0
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
         "SQLITE_READONLY_OR_PREIMAGE_DRIFT")
    return {
        "schema": SCHEMA,
        "target_source_sha": request["target_source_sha"],
        "original_source_sha": source.FROM_V41,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "logical_all_tables_sha256": actual,
        "hold_approval_comment_id": request["hold_approval_comment_id"],
        "abort_owner_comment_id": request["abort_owner_comment_id"],
        "backup_run_id": request["backup_run_id"],
        "backup_manifest_sha256": request["backup_manifest_sha256"],
        "frozen_precommit_unchanged": True,
        "complete_detached_restore_verified": True,
        "eligible_for_separately_approved_same_original_task_abort": True,
        "original_owner_mutations": 0,
        "policy_mutation_authorized": False,
        "source_transition_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }


def original_preflight(db_path, env, event, api):
    """No writes. Genuine original Windows task/runner/source required."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub and isinstance(db_path, Path),
         "NATIVE_WINDOWS_ORIGINAL_OWNER_REQUIRED")
    get = api.native_repo_get
    request = authenticate_abort(env, event, get)
    target = request["target_source_sha"]
    source_identity = release.require_successor_source(get, target, env=env)
    path = owner._original_path(db_path, env)
    owner._candidate_clean_checkout(target)
    policy = owner._owner_policy(get)
    owner._task_readback(path, disabled=True)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as db:
            result = inspect_precommit(db, request)
    owner._task_readback(path, disabled=True)
    need(owner._owner_policy(get) == policy
         and release.require_successor_source(get, target, env=env)
             == source_identity
         and authenticate_abort(env, event, get) == request,
         "POSTPREFLIGHT_TASK_POLICY_SOURCE_OR_APPROVAL_DRIFT")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    need(args.target == env.get("GITHUB_SHA"), "TARGET_ENV_DRIFT")
    path = env.get("GITHUB_EVENT_PATH")
    need(type(path) is str and Path(path).is_file(),
         "GITHUB_EVENT_FILE_REQUIRED")
    event = json.loads(Path(path).read_text("utf-8"),
                       object_pairs_hook=decode_unique)
    db_path = Path(env.get("LOCALAPPDATA", "")) / "FORGE-F139" / "state.sqlite"
    receipt = original_preflight(db_path, env, event, GitHub())
    print("F139_HYBRID_V41_SAFE_ABORT_PREFLIGHT=" +
          canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
