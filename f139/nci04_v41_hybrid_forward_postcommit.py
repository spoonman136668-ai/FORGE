"""Read-only, source-bound original owner V38 postcommit acceptance.

Requires a NEW owner-authored postcommit readiness comment after a genuine
source-only commit of event 1831. Reads the same original disabled Windows
task, one fully cold-verified SQLite event chain, 153/56 preserved history,
current protected release and unchanged two-lane policy. No schema migration,
native activation, policy mutation, task retarget, process or science.
This module is deliberately unregistered: no comment alone executes it.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sys

from f139.local_controller import Database, GitHub, SingleOwner, canonical as db_canonical
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_forward_original_commit as committed
from f139 import nci04_v41_hybrid_forward_owner_profile as profile
from f139 import nci04_v41_hybrid_forward_readiness as readiness
from f139 import nci04_v41_hybrid_forward_repair as v38
from f139 import nci04_v41_hybrid_owner_maintenance as owner
from f139.hybrid_owner_admission import is_migrated

SCHEMA = "forge.f139.hybrid-v38.original-postcommit-readiness.v1"
PREFIX = "F139-HYBRID-V41-FORWARD-POSTCOMMIT "
RECEIPT = "forge.f139.hybrid-v38.original-postcommit-readonly.v1"


class PostcommitDenied(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise PostcommitDenied("F139_HYBRID_V38_POSTCOMMIT_" + why)


def authenticate(get, env, event):
    """Prove a NEW owner comment and a prior committed source-only intent.

    This validates readiness only, and is never permission to activate source
    or change the original task's action.
    """
    need(callable(get) and type(env) is dict and type(event) is dict
         and env.get("GITHUB_REPOSITORY") == readiness.REPO
         and env.get("GITHUB_ACTOR") == readiness.OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and type(env.get("GITHUB_SHA")) is str
         and readiness.SHA40.fullmatch(env["GITHUB_SHA"])
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
         and not env.get("OPENAI_API_KEY"),
         "ORIGINAL_OWNER_FIRST_ATTEMPT_REQUIRED")
    issue, sender, comment = (event.get(k) for k in (
        "issue", "sender", "comment"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == readiness.OWNER
         and type(sender) is dict
         and sender.get("login") == readiness.OWNER
         and type(comment) is dict
         and type(comment.get("id")) is int
         and comment["id"] > readiness.OLD_COMMIT_ID
         and type(comment.get("body")) is str
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == readiness.OWNER
         and comment.get("author_association") == "OWNER",
         "DISTINCT_ORIGINAL_OWNER_READINESS_REQUIRED")
    target = env["GITHUB_SHA"]
    match = re.fullmatch(
        re.escape(PREFIX + target) + r" ([1-9][0-9]*)",
        comment["body"])
    need(match is not None, "EXACT_POSTCOMMIT_COMMENT_REQUIRED")
    prior_id = int(match.group(1))
    need(prior_id > readiness.OLD_COMMIT_ID
         and prior_id < comment["id"],
         "NEW_POSTCOMMIT_AFTER_SOURCE_COMMIT_REQUIRED")
    stamp = readiness._owner_comment(
        get, comment["id"], comment["body"])
    need(stamp == comment.get("created_at"),
         "POSTCOMMIT_OWNER_TIMESTAMP_DRIFT")
    original = get("repos/" + readiness.REPO + "/issues/comments/" +
                   str(prior_id))
    need(type(original) is dict
         and type(original.get("body")) is str
         and original["body"].startswith(committed.PREFIX),
         "ORIGINAL_SOURCE_COMMIT_INTENT_UNAVAILABLE")
    earlier = readiness._owner_comment(
        get, prior_id, original["body"])
    need(earlier < stamp, "POSTCOMMIT_BEFORE_SOURCE_COMMIT")
    request = committed.authenticate_commit(
        get, env, {"action": "created", "issue": issue,
                   "sender": sender, "comment": original})
    need(request["target_source_sha"] == target
         and request["source_commit_comment_id"] == prior_id,
         "SOURCE_COMMIT_NOT_BOUND_TO_POSTCOMMIT_OWNER")
    return request


def inspect(db, request):
    """Cold, read-only replay of one exact v38 event; never migrate."""
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and type(request) is dict,
         "ORIGINAL_READONLY_OWNER_MUTEX_REQUIRED")
    before = db.meta().copy()
    db.verify()
    need(before["source_sha"] == request["target_source_sha"]
         and before["head_seq"] == v38.V37_SEQ + 1
         and before["enabled"] == 1
         and before["legacy_suspended"] == 1
         and db.dual_native_schema()
         and not is_migrated(db)
         and db.ready() is None
         and not db.actives(),
         "EXACT_INACTIVE_POSTCOMMIT_HOLD_REQUIRED")
    row = db.conn.execute(
        "SELECT seq,kind,sha,prior_sha,payload FROM events WHERE seq=?",
        (v38.V37_SEQ + 1,)).fetchone()
    need(row is not None
         and row["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and row["seq"] == v38.V37_SEQ + 1
         and row["prior_sha"] == v38.V37_HEAD
         and row["sha"] == before["head_hash"],
         "EXACT_V38_SOURCE_EVENT_REQUIRED")
    try:
        proof = json.loads(row["payload"], object_pairs_hook=decode_unique)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise PostcommitDenied(
            "F139_HYBRID_V38_POSTCOMMIT_EVENT_PARSE") from exc
    need(type(proof) is dict and set(proof) == v38.FIELDS
         and proof["schema"] == v38.SCHEMA
         and proof["owner_event_id"] == request["readiness_comment_id"]
         and proof["backup_run_id"] == request["backup_run_id"]
         and proof["backup_manifest_sha256"] ==
             request["backup_manifest_sha256"]
         and proof["backup_logical_all_tables_sha256"] ==
             request["backup_logical_all_tables_sha256"]
         and row["payload"] == db_canonical(proof).decode("ascii"),
         "SOURCE_EVENT_NOT_BOUND_TO_APPROVED_BACKUP")
    cold = committed._fresh_bundle(db.filename, request)
    need(cold["original_head_seq"] == v38.V37_SEQ
         and cold["original_head_sha256"] == v38.V37_HEAD,
         "PRECOMMIT_COLD_PREIMAGE_CHANGED")
    receipt = {
        "event_head_sha256": row["sha"]
    }
    qualified = committed._postcommit(db, request, proof, receipt)
    need(qualified["event_seq"] == v38.V37_SEQ + 1
         and qualified["source_sha"] == request["target_source_sha"]
         and qualified["verified_historical_tasks"] == 153
         and qualified["custodied_negative_tasks"] == 56
         and qualified["hybrid_admission"] is False
         and qualified["task_resume_authorized"] is False
         and qualified["scientific_first_use"] is False
         and before == db.meta()
         and db.conn.total_changes == 0,
         "ORIGINAL_HISTORY_OR_HOLD_READBACK_DRIFT")
    return {
        "schema": RECEIPT,
        "source_sha": before["source_sha"],
        "event_seq": before["head_seq"],
        "event_head_sha256": before["head_hash"],
        "predecessor_event_seq": v38.V37_SEQ,
        "predecessor_event_head_sha256": v38.V37_HEAD,
        "verified_historical_tasks": 153,
        "custodied_negative_tasks": 56,
        "original_owner_mutations": 0,
        "native_activation_performed": False,
        "hybrid_schema_migrated": False,
        "hybrid_admission": False,
        "task_resume_authorized": False,
        "policy_update_authorized": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }


def original_postcommit(db_path, env, event, api):
    """Original Windows owner readback only; no scheduler or policy effects."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub and isinstance(db_path, Path),
         "ORIGINAL_WINDOWS_OWNER_REQUIRED")
    get = api.native_repo_get
    request = authenticate(get, env, event)
    target = request["target_source_sha"]
    release = readiness._release(get, target)
    path = owner._original_path(db_path, env)
    owner._candidate_clean_checkout(target)
    policy = owner._owner_policy(get)
    profile.readback(path)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as db:
            result = inspect(db, request)
    need(profile.readback(path) is True
         and owner._owner_policy(get) == policy
         and owner._candidate_clean_checkout(target) is True
         and readiness._release(get, target) == release
         and authenticate(get, env, event) == request,
         "POSTREADBACK_OWNER_RELEASE_OR_TASK_DRIFT")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    need(args.target == env.get("GITHUB_SHA"),
         "EXACT_TARGET_REQUIRED")
    event_path = env.get("GITHUB_EVENT_PATH")
    need(type(event_path) is str and Path(event_path).is_file(),
         "ORIGINAL_EVENT_FILE_REQUIRED")
    try:
        event = json.loads(Path(event_path).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
    except (OSError, UnicodeError, ValueError) as exc:
        raise PostcommitDenied(
            "F139_HYBRID_V38_POSTCOMMIT_EVENT_NOT_CANONICAL") from exc
    need(type(env.get("LOCALAPPDATA")) is str
         and Path(env["LOCALAPPDATA"]).is_absolute(),
         "ORIGINAL_OWNER_LOCAL_DATA_REQUIRED")
    path = Path(env["LOCALAPPDATA"]) / "FORGE-F139" / "state.sqlite"
    receipt = original_postcommit(path, env, event, GitHub())
    print("F139_HYBRID_V38_ORIGINAL_POSTCOMMIT_READONLY=" +
          canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
