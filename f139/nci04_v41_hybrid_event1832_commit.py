"""Unregistered original-owner event1832 source-only transaction entrypoint.

Requires a distinct owner comment, new successful full cold backup job, exact
precomputed proof hash, merged-source regression and the unchanged disabled
original Windows owner. Never changes the task, lane schema or issue policy.
No caller may replay an uncertain source-commit attempt or override a prior
event. Live execution requires a separately approved workflow registration.
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
from f139 import nci04_v41_hybrid_event1832_owner as owner
from f139 import nci04_v41_hybrid_event1832_cold as cold
from f139 import nci04_v41_hybrid_event1832_successor as successor
from f139 import nci04_v41_hybrid_owner_maintenance as prior_owner
from f139 import nci04_v41_hybrid_forward_owner_profile as profile
from f139 import nci04_v41_hybrid_forward_readiness as shared

PREFIX = "F139-HYBRID-V39-COMMIT "
SCHEMA = "forge.f139.v39.original-event1831-source-commit-intent.v1"
RECEIPT = "forge.f139.v39.original-event1832-source-held.v1"
BACKUP_WORKFLOW = "FORGE F139 V41 guarded original-owner live installation"
BACKUP_JOB = "hybrid-v39-original-event1831-backup"
FIELDS = frozenset({
    "schema", "target_source_sha", "readiness_comment_id",
    "backup_comment_id", "backup_run_id",
    "backup_manifest_sha256", "backup_logical_all_tables_sha256",
    "original_head_seq", "original_head_sha256",
    "expected_proof_sha256", "source_transition_requested",
    "task_resume_authorized", "owner_policy_update_authorized",
    "hybrid_admission", "scientific_first_use", "new_dispatches",
})


class Event1832CommitDenied(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise Event1832CommitDenied("F139_V39_COMMIT_" + why)


def _new_owner_intent(get, env, event):
    need(type(env) is dict and type(event) is dict and callable(get)
         and env.get("GITHUB_REPOSITORY") == owner.REPO
         and env.get("GITHUB_ACTOR") == owner.OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
         and not env.get("OPENAI_API_KEY"),
         "ORIGINAL_WINDOWS_FIRST_ATTEMPT_REQUIRED")
    issue, sender, comment = (event.get(k) for k in (
        "issue", "sender", "comment"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == owner.OWNER
         and type(sender) is dict and sender.get("login") == owner.OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == owner.OWNER
         and comment.get("author_association") == "OWNER"
         and type(comment.get("body")) is str
         and comment["body"].startswith(PREFIX),
         "NEW_SOURCE_COMMIT_OWNER_EVENT_REQUIRED")
    try:
        doc = json.loads(comment["body"][len(PREFIX):],
                         object_pairs_hook=decode_unique)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise Event1832CommitDenied("F139_V39_COMMIT_CANONICAL_INTENT_REQUIRED") from exc
    need(type(doc) is dict and set(doc) == FIELDS
         and comment["body"] == PREFIX + canonical(doc).decode("ascii")
         and doc["schema"] == SCHEMA
         and type(doc["target_source_sha"]) is str
         and successor.SHA40.fullmatch(doc["target_source_sha"]) is not None
         and doc["target_source_sha"] == env.get("GITHUB_SHA")
         and doc["target_source_sha"] != successor.SOURCE
         and all(type(doc[k]) is int and doc[k] > 0 for k in (
             "readiness_comment_id", "backup_comment_id",
             "backup_run_id", "original_head_seq"))
         and len({doc["readiness_comment_id"],
                  doc["backup_comment_id"], comment["id"]}) == 3
         and doc["original_head_seq"] == successor.PREDECESSOR_SEQ
         and doc["original_head_sha256"] == successor.PREDECESSOR_SHA
         and all(type(doc[k]) is str
                 and successor.SHA64.fullmatch(doc[k]) is not None
                 for k in ("original_head_sha256",
                           "backup_manifest_sha256",
                           "backup_logical_all_tables_sha256",
                           "expected_proof_sha256"))
         and doc["source_transition_requested"] is True
         and all(doc[k] is False for k in (
             "task_resume_authorized", "owner_policy_update_authorized",
             "hybrid_admission", "scientific_first_use"))
         and type(doc["new_dispatches"]) is int
         and doc["new_dispatches"] == 0,
         "EXACT_SOURCE_ONLY_COMMIT_INTENT_REQUIRED")
    return issue, sender, comment, doc


def _backup_job(get, doc):
    base = ("repos/" + owner.REPO + "/actions/runs/" +
            str(doc["backup_run_id"]))
    run = get(base)
    need(type(run) is dict and run.get("id") == doc["backup_run_id"]
         and run.get("name") == BACKUP_WORKFLOW
         and run.get("event") == "issue_comment"
         and run.get("head_sha") == doc["target_source_sha"]
         and run.get("run_attempt") == 1
         and run.get("status") == "completed"
         and run.get("conclusion") == "success"
         and run.get("actor", {}).get("login") == owner.OWNER,
         "ACTUAL_PRIOR_BACKUP_RUN_NOT_QUALIFIED")
    jobs = get(base + "/jobs?per_page=100")
    need(type(jobs) is dict
         and type(jobs.get("total_count")) is int
         and type(jobs.get("jobs")) is list
         and jobs["total_count"] == len(jobs["jobs"])
         and len(jobs["jobs"]) <= 100,
         "EXACT_BACKUP_JOBS_NOT_AVAILABLE")
    selected = [row for row in jobs["jobs"] if type(row) is dict
                and row.get("name") == BACKUP_JOB]
    need(len(selected) == 1
         and selected[0].get("status") == "completed"
         and selected[0].get("conclusion") == "success"
         and selected[0].get("run_id") == doc["backup_run_id"]
         and type(selected[0].get("id")) is int
         and selected[0]["id"] > 0,
         "ACTUAL_ORIGINAL_BACKUP_JOB_NOT_SUCCESSFUL")
    return selected[0]["id"]


def authenticate_commit(get, env, event):
    """Re-read the unique intent, distinct readiness, backup and real job."""
    issue, sender, comment, doc = _new_owner_intent(get, env, event)
    stamp = shared._owner_comment(
        get, comment["id"], comment["body"])
    need(stamp == comment.get("created_at"),
         "ORIGINAL_COMMIT_EVENT_TIMESTAMP_DRIFT")
    prefix = "repos/" + owner.REPO + "/issues/comments/"
    ready = get(prefix + str(doc["readiness_comment_id"]))
    backup = get(prefix + str(doc["backup_comment_id"]))
    need(type(ready) is dict and ready.get("body") ==
         owner.READINESS + doc["target_source_sha"] + " " +
         str(owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID)
         and type(backup) is dict and backup.get("body") ==
         owner.BACKUP + doc["target_source_sha"] + " " +
         str(doc["readiness_comment_id"])
         and owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID <
         doc["readiness_comment_id"] < doc["backup_comment_id"] <
         comment["id"],
         "OWNER_READINESS_BACKUP_SOURCE_COMMIT_CHAIN_DRIFT")
    ready_stamp = shared._owner_comment(
        get, doc["readiness_comment_id"], ready["body"])
    backup_stamp = shared._owner_comment(
        get, doc["backup_comment_id"], backup["body"])
    need(ready_stamp < backup_stamp < stamp,
         "SOURCE_OWNER_EVENT_SEQUENCE_INVALID")
    authenticated_ready = owner.authenticate_readiness(get, env, {
        "action": "created", "issue": issue,
        "sender": sender, "comment": ready})
    authenticated_backup = owner.authenticate_backup(get, env, {
        "action": "created", "issue": issue,
        "sender": sender, "comment": backup})
    need(authenticated_ready["readiness_comment_id"] ==
         doc["readiness_comment_id"]
         and authenticated_backup["backup_comment_id"] ==
             doc["backup_comment_id"],
         "BACKUP_NOT_AUTHENTICATED_BY_SAME_OWNER")
    job_id = _backup_job(get, doc)
    return {
        **doc, "source_commit_comment_id": comment["id"],
        "backup_job_id": job_id,
    }


def _fresh_cold(path, req):
    folder = cold.folder_for(path, req["backup_run_id"])
    receipt = cold.verify_detached_restore(
        folder, target=req["target_source_sha"],
        run_id=req["backup_run_id"],
        manifest_sha=req["backup_manifest_sha256"])
    need(receipt["backup_logical_all_tables_sha256"] ==
         req["backup_logical_all_tables_sha256"]
         and receipt["original_source_sha"] == successor.SOURCE
         and receipt["original_head_seq"] == successor.PREDECESSOR_SEQ
         and receipt["original_head_sha256"] == successor.PREDECESSOR_SHA
         and receipt["independent_detached_restore_verified"] is True
         and receipt["negative_custody_bytes_verified"] is True,
         "FULL_EVENT1831_DETACHED_BACKUP_NOT_AUTHENTIC")
    return receipt


def inspect_postcommit(db, req, expected_proof):
    """Independent *read-only* confirmation of exactly one source event 1832."""
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_QUERY_ONLY_POSTCOMMIT_MUTEX_REQUIRED")
    db.verify()
    meta = db.meta()
    row = db.conn.execute(
        "SELECT kind,seq,sha,prior_sha,payload FROM events WHERE seq=?",
        (successor.PREDECESSOR_SEQ + 1,)).fetchone()
    need(meta["source_sha"] == req["target_source_sha"]
         and meta["head_seq"] == successor.PREDECESSOR_SEQ + 1
         and row is not None and row["seq"] == meta["head_seq"]
         and row["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and row["sha"] == meta["head_hash"]
         and row["prior_sha"] == successor.PREDECESSOR_SHA
         and row["payload"] == canonical(expected_proof).decode("ascii")
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and db.dual_native_schema()
         and db.ready() is None and not db.actives()
         and db.conn.execute(
             "SELECT COUNT(*) FROM tasks WHERE stage='VERIFIED'"
         ).fetchone()[0] == 153
         and db.conn.execute(
             "SELECT COUNT(*) FROM tasks WHERE stage='QUARANTINED'"
         ).fetchone()[0] == 56
         and db.conn.total_changes == 0,
         "EVENT1832_ORIGINAL_HISTORY_OR_READBACK_DRIFT")
    return {
        "source_sha": meta["source_sha"],
        "event_seq": meta["head_seq"],
        "event_head_sha256": meta["head_hash"],
        "verified_historical_tasks": 153,
        "custodied_negative_tasks": 56,
        "original_owner_mutations": 0,
        "task_resume_authorized": False,
        "owner_policy_update_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }


def original_source_commit(path, env, event, api):
    """One owner-bound source-only transaction; never auto-retry or activate."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub and isinstance(path, Path),
         "ACTUAL_ORIGINAL_WINDOWS_OWNER_REQUIRED")
    get = api.native_repo_get
    req = authenticate_commit(get, env, event)
    target = req["target_source_sha"]
    qualified = owner.release(get, target)
    path = prior_owner._original_path(path, env)
    prior_owner._candidate_clean_checkout(target)
    policy = prior_owner._owner_policy(get)
    def held():
        return profile.readback(path) is True
    def released():
        return (prior_owner._candidate_clean_checkout(target) is True
                and prior_owner._owner_policy(get) == policy
                and owner.release(get, target) == qualified
                and authenticate_commit(get, env, event) == req)
    need(held() and released(),
         "NEW_SOURCE_OWNER_OR_RELEASE_NOT_STABLE")
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as original:
            before = successor._held_original(original)
            cold_proof = _fresh_cold(path, req)
            candidate = successor.build_proof(
                original, target=target,
                owner_event_id=req["readiness_comment_id"],
                backup_run_id=req["backup_run_id"],
                backup_manifest_sha256=req["backup_manifest_sha256"],
                backup_logical_all_tables_sha256=
                    req["backup_logical_all_tables_sha256"])
            need(digest(canonical(candidate)) ==
                 req["expected_proof_sha256"]
                 and original.meta() == before
                 and original.conn.total_changes == 0,
                 "FROZEN_1831_PRECOMMIT_PROOF_INVALID")
        need(held() and released(), "OWNER_DRIFT_BEFORE_SQLITE_COMMIT")
        with closing(Database(path)) as writer:
            need(writer.meta() == before,
                 "ORIGINAL_PRECOMMIT_MOVED")
            committed = successor.commit_transition(
                writer, candidate,
                disabled_owner_witness=held,
                release_witness=released,
                detached_cold_witness=lambda:
                    _fresh_cold(path, req))
        with closing(Database.open_readonly(path)) as final:
            readback = inspect_postcommit(final, req, candidate)
        need(held() and released()
             and _fresh_cold(path, req) == cold_proof,
             "POSTCOMMIT_HOLD_OR_COLD_DRIFT")
    return {
        "schema": RECEIPT,
        "target_source_sha": target,
        "source_commit_comment_id": req["source_commit_comment_id"],
        "readiness_comment_id": req["readiness_comment_id"],
        "backup_comment_id": req["backup_comment_id"],
        "backup_run_id": req["backup_run_id"],
        "backup_job_id": req["backup_job_id"],
        "backup_manifest_sha256": req["backup_manifest_sha256"],
        "expected_proof_sha256": req["expected_proof_sha256"],
        "commit": committed, "postcommit": readback,
        "original_task_still_disabled": True,
        "original_policy_unchanged": True,
        "task_resume_authorized": False,
        "owner_policy_update_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    need(args.target == env.get("GITHUB_SHA"),
         "EXACT_COMMIT_TARGET_REQUIRED")
    path = env.get("GITHUB_EVENT_PATH")
    need(type(path) is str and Path(path).is_file(),
         "EXACT_OWNER_EVENT_FILE_REQUIRED")
    try:
        event = json.loads(Path(path).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
    except (OSError, ValueError, UnicodeError) as exc:
        raise Event1832CommitDenied("F139_V39_COMMIT_EVENT_PARSE_FAILED") from exc
    need(type(env.get("LOCALAPPDATA")) is str
         and Path(env["LOCALAPPDATA"]).is_absolute(),
         "ORIGINAL_LOCALAPPDATA_REQUIRED")
    original = Path(env["LOCALAPPDATA"]) / "FORGE-F139" / "state.sqlite"
    receipt = original_source_commit(original, env, event, GitHub())
    print("F139_V39_ORIGINAL_SOURCE_HOLD=" +
          canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
