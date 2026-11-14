"""Inert, one-shot V38 source-only original-owner forward commit.

After authenticating a NEW distinct owner source-commit intent, an earlier
successful backup-owner run, a fresh exact-source detached event-1830 bundle,
the preserved disabled original Windows task and protected postmerge CI,
advance the SAME SQLite source one event only. Never restart the task, change
issue policy, admit Hybrid science, repair by replay or create a controller.

NOT registered in Actions: no live execution authority is granted by this file.
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
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_forward_readiness as readiness
from f139 import nci04_v41_hybrid_forward_cold_bundle as cold
from f139 import nci04_v41_hybrid_forward_repair as forward
from f139 import nci04_v41_hybrid_forward_backup as previous_backup
from f139 import nci04_v41_hybrid_owner_maintenance as owner
from f139.hybrid_owner_admission import is_migrated

SCHEMA = "forge.f139.hybrid-forward.original-source-commit-intent.v1"
PREFIX = "F139-HYBRID-V41-FORWARD-COMMIT "
RECEIPT = "forge.f139.hybrid-forward.original-source-commit-held.v1"
BACKUP_JOB = "hybrid-v38-original-forward-backup"
BACKUP_WORKFLOW = "FORGE F139 V38 guarded original-owner forward installation"
FIELDS = frozenset({
    "schema", "target_source_sha", "readiness_comment_id",
    "backup_comment_id", "backup_run_id", "backup_manifest_sha256",
    "backup_logical_all_tables_sha256", "original_head_seq",
    "original_head_sha256", "expected_proof_sha256",
    "source_transition_requested", "task_resume_authorized",
    "policy_update_authorized", "hybrid_admission",
    "scientific_first_use", "new_dispatches",
})


class ForwardCommitDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise ForwardCommitDenied("F139_HYBRID_FORWARD_COMMIT_" + code)


def _new_comment(get, env, event):
    need(type(env) is dict and type(event) is dict and callable(get)
         and env.get("GITHUB_REPOSITORY") == readiness.REPO
         and env.get("GITHUB_ACTOR") == readiness.OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
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
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == readiness.OWNER
         and "pull_request" not in issue
         and type(sender) is dict
         and sender.get("login") == readiness.OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > readiness.OLD_COMMIT_ID
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == readiness.OWNER
         and comment.get("author_association") == "OWNER"
         and type(comment.get("body")) is str
         and comment["body"].startswith(PREFIX),
         "ORIGINAL_OWNER_NEW_COMMIT_INTENT_REQUIRED")
    try:
        doc = json.loads(comment["body"][len(PREFIX):],
                         object_pairs_hook=decode_unique)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise ForwardCommitDenied(
            "F139_HYBRID_FORWARD_COMMIT_CANONICAL_JSON_REQUIRED") from exc
    need(type(doc) is dict and set(doc) == FIELDS
         and comment["body"] == PREFIX + canonical(doc).decode("ascii")
         and doc["schema"] == SCHEMA
         and type(doc["target_source_sha"]) is str
         and readiness.SHA40.fullmatch(doc["target_source_sha"])
         and doc["target_source_sha"] == env.get("GITHUB_SHA")
         and doc["target_source_sha"] != forward.FROM
         and all(type(doc[k]) is int and doc[k] > 0 for k in (
             "readiness_comment_id", "backup_comment_id", "backup_run_id",
             "original_head_seq"))
         and len({doc["readiness_comment_id"], doc["backup_comment_id"],
                  comment["id"]}) == 3
         and doc["original_head_seq"] == forward.V37_SEQ
         and doc["original_head_sha256"] == forward.V37_HEAD
         and all(type(doc[k]) is str and
                 forward.HEX64.fullmatch(doc[k]) for k in (
                     "backup_manifest_sha256",
                     "backup_logical_all_tables_sha256",
                     "original_head_sha256", "expected_proof_sha256"))
         and doc["source_transition_requested"] is True
         and all(doc[k] is False for k in (
             "task_resume_authorized", "policy_update_authorized",
             "hybrid_admission", "scientific_first_use"))
         and type(doc["new_dispatches"]) is int
         and doc["new_dispatches"] == 0,
         "EXACT_SOURCE_ONLY_NONSCIENCE_INTENT_REQUIRED")
    return issue, sender, comment, doc


def _historical_backup_run(get, doc):
    """One successful native backup JOB; no synthetic comment-as-proof."""
    route = "repos/" + readiness.REPO + "/actions/runs/" + str(
        doc["backup_run_id"])
    run = get(route)
    need(type(run) is dict
         and run.get("id") == doc["backup_run_id"]
         and run.get("name") == BACKUP_WORKFLOW
         and run.get("event") == "issue_comment"
         and run.get("head_sha") == doc["target_source_sha"]
         and run.get("run_attempt") == 1
         and run.get("status") == "completed"
         and run.get("conclusion") == "success"
         and type(run.get("actor")) is dict
         and run["actor"].get("login") == readiness.OWNER,
         "ORIGINAL_BACKUP_RUN_NOT_SUCCESSFUL")
    listing = get(route + "/jobs?per_page=100")
    need(type(listing) is dict
         and type(listing.get("total_count")) is int
         and type(listing.get("jobs")) is list
         and listing["total_count"] == len(listing["jobs"])
         and len(listing["jobs"]) <= 100,
         "ORIGINAL_BACKUP_JOB_INVENTORY_NOT_EXACT")
    matches = [j for j in listing["jobs"] if type(j) is dict
               and j.get("name") == BACKUP_JOB]
    need(len(matches) == 1
         and matches[0].get("run_id") == doc["backup_run_id"]
         and matches[0].get("status") == "completed"
         and matches[0].get("conclusion") == "success"
         and type(matches[0].get("id")) is int
         and matches[0]["id"] > 0,
         "ORIGINAL_BACKUP_OWNER_JOB_NOT_QUALIFIED")
    return {"run_id": run["id"], "job_id": matches[0]["id"]}


def authenticate_commit(get, env, event):
    """Recheck every owner comment and full backup run before any SQLite work."""
    issue, sender, comment, doc = _new_comment(get, env, event)
    commit_stamp = readiness._owner_comment(get, comment["id"],
                                             comment["body"])
    need(commit_stamp == comment.get("created_at"),
         "OWNER_COMMIT_EVENT_TIMESTAMP_DRIFT")
    lookup = "repos/" + readiness.REPO + "/issues/comments/"
    backup = get(lookup + str(doc["backup_comment_id"]))
    need(type(backup) is dict and backup.get("body") ==
         previous_backup.PREFIX + doc["target_source_sha"] + " " +
         str(doc["readiness_comment_id"]),
         "BACKUP_COMMENT_NOT_QUALIFIED_FOR_SOURCE")
    backup_stamp = readiness._owner_comment(
        get, doc["backup_comment_id"], backup["body"])
    ready = get(lookup + str(doc["readiness_comment_id"]))
    need(type(ready) is dict and ready.get("body") ==
         readiness.PREFIX + doc["target_source_sha"] + " " +
         str(readiness.OLD_COMMIT_ID),
         "READINESS_COMMENT_NOT_QUALIFIED_FOR_SOURCE")
    ready_stamp = readiness._owner_comment(
        get, doc["readiness_comment_id"], ready["body"])
    need(ready_stamp < backup_stamp < commit_stamp,
         "READINESS_BACKUP_COMMIT_ORDER_REQUIRED")
    ready_event = {
        "action": "created", "issue": issue, "sender": sender,
        "comment": ready,
    }
    frozen = readiness.authenticate_readiness(
        get, env, ready_event, doc["target_source_sha"])
    job = _historical_backup_run(get, doc)
    return doc | {
        "source_commit_comment_id": comment["id"],
        "frozen_v37_commit": frozen,
        "backup_job_id": job["job_id"],
    }


def _fresh_bundle(db_path, req):
    new_folder = db_path.parent / (
        "f139-v38-before-" + str(req["backup_run_id"]))
    receipt = cold.verify_detached_restore(
        new_folder, target=req["target_source_sha"],
        run_id=req["backup_run_id"],
        manifest_sha=req["backup_manifest_sha256"])
    need(type(receipt) is dict
         and receipt.get("candidate_sha") == req["target_source_sha"]
         and receipt.get("original_source_sha") == forward.FROM
         and receipt.get("original_head_seq") == forward.V37_SEQ
         and receipt.get("original_head_sha256") == forward.V37_HEAD
         and receipt.get("manifest_sha256") ==
             req["backup_manifest_sha256"]
         and receipt.get("logical_all_tables_sha256") ==
             req["backup_logical_all_tables_sha256"]
         and receipt.get("independent_detached_restore_verified") is True
         and receipt.get("original_owner_mutations") == 0
         and receipt.get("new_dispatches") == 0
         and receipt.get("source_transition_authorized") is False
         and receipt.get("hybrid_admission") is False
         and receipt.get("scientific_first_use") is False,
         "NEW_SOURCE_COMMIT_COLD_BUNDLE_NOT_VERIFIED")
    return receipt


def _postcommit(db, req, proof, receipt):
    """Verify appended event and all frozen task bytes after commit, read only."""
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_READONLY_MUTEX_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == req["target_source_sha"]
         and meta["head_seq"] == forward.V37_SEQ + 1
         and meta["head_hash"] == receipt["event_head_sha256"]
         and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1
         and db.dual_native_schema()
         and not is_migrated(db)
         and db.ready() is None
         and not db.actives(),
         "POSTCOMMIT_SOURCE_OR_IDLE_DRIFT")
    row = db.conn.execute(
        "SELECT seq,kind,sha,prior_sha,payload FROM events WHERE seq=?",
        (forward.V37_SEQ + 1,)).fetchone()
    need(row is not None
         and row["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and row["prior_sha"] == forward.V37_HEAD
         and row["sha"] == meta["head_hash"]
         and row["payload"] == db_canonical(proof).decode("ascii"),
         "POSTCOMMIT_SOURCE_EVENT_NOT_EXACT")
    good = db.conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE stage='VERIFIED'").fetchone()[0]
    bad = db.conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE stage='QUARANTINED'").fetchone()[0]
    need(good == 153 and bad == 56 and db.conn.total_changes == 0,
         "POSTCOMMIT_ORIGINAL_153_56_HISTORY_DRIFT")
    return {
        "event_seq": meta["head_seq"], "event_head_sha256": meta["head_hash"],
        "source_sha": meta["source_sha"],
        "verified_historical_tasks": good, "custodied_negative_tasks": bad,
        "hybrid_admission": False, "task_resume_authorized": False,
        "policy_update_authorized": False, "scientific_first_use": False,
        "new_dispatches": 0,
    }


def original_source_commit(db_path, env, event, api):
    """Single exact source-only transaction; no policy/task mutation."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub and isinstance(db_path, Path),
         "WINDOWS_ORIGINAL_NATIVE_PROVIDER_REQUIRED")
    get = api.native_repo_get
    req = authenticate_commit(get, env, event)
    target = req["target_source_sha"]
    release = readiness._release(get, target)
    db_path = owner._original_path(db_path, env)
    owner._candidate_clean_checkout(target)
    policy = owner._owner_policy(get)
    owner._task_readback(db_path, disabled=True)

    def disabled():
        return owner._task_readback(db_path, disabled=True) is True

    def released():
        return (
            owner._candidate_clean_checkout(target) is True
            and owner._owner_policy(get) == policy
            and readiness._release(get, target) == release
            and authenticate_commit(get, env, event) == req
        )

    need(disabled() and released(),
         "PRECOMMIT_OWNER_RELEASE_OR_EVENT_MOVED")
    with SingleOwner(db_path.with_suffix(".lock")):
        with closing(Database.open_readonly(db_path)) as original:
            before = original.meta().copy()
            readiness.inspect_held_original(
                original, req["frozen_v37_commit"])
            cold_receipt = _fresh_bundle(db_path, req)
            proof = forward.build_proof(
                original, target, req["source_commit_comment_id"],
                req["backup_run_id"], req["backup_manifest_sha256"],
                req["backup_logical_all_tables_sha256"])
            need(digest(canonical(proof)) ==
                 req["expected_proof_sha256"]
                 and original.meta() == before
                 and original.conn.total_changes == 0,
                 "FROZEN_SOURCE_PROOF_MISMATCH")
        need(disabled() and released(),
             "PREWRITE_OWNER_OR_COMMENT_CHANGED")
        with closing(Database(db_path)) as writer:
            need(writer.meta() == before,
                 "WRITER_COMMITTED_SOURCE_PREIMAGE_MOVED")
            result = forward.commit_transition(
                writer, proof,
                disabled_owner_witness=disabled,
                release_witness=released,
                cold_bundle_witness=lambda: (
                    _fresh_bundle(db_path, req) == cold_receipt))
        with closing(Database.open_readonly(db_path)) as final:
            post = _postcommit(final, req, proof, result)
        need(disabled() and owner._owner_policy(get) == policy,
             "POSTCOMMIT_ORIGINAL_TASK_OR_POLICY_CHANGED")
    return {
        "schema": RECEIPT, "target_source_sha": target,
        "source_commit_comment_id": req["source_commit_comment_id"],
        "readiness_comment_id": req["readiness_comment_id"],
        "backup_comment_id": req["backup_comment_id"],
        "backup_run_id": req["backup_run_id"],
        "backup_manifest_sha256": req["backup_manifest_sha256"],
        "proof_sha256": req["expected_proof_sha256"],
        "release": release,
        "commit": result, "postcommit": post,
        "original_task_still_disabled": True,
        "original_policy_unchanged": True,
        "task_resume_authorized": False,
        "policy_update_authorized": False,
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
         "EXACT_PROTECTED_MAIN_TARGET_REQUIRED")
    event_path = env.get("GITHUB_EVENT_PATH")
    need(type(event_path) is str and Path(event_path).is_file(),
         "ORIGINAL_OWNER_EVENT_FILE_REQUIRED")
    try:
        event = json.loads(Path(event_path).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
    except (ValueError, UnicodeError, OSError) as exc:
        raise ForwardCommitDenied(
            "F139_HYBRID_FORWARD_COMMIT_NONCANONICAL_EVENT") from exc
    need(type(env.get("LOCALAPPDATA")) is str
         and Path(env["LOCALAPPDATA"]).is_absolute(),
         "ORIGINAL_OWNER_DATA_DIRECTORY_REQUIRED")
    path = Path(env["LOCALAPPDATA"]) / "FORGE-F139" / "state.sqlite"
    receipt = original_source_commit(path, env, event, GitHub())
    print("F139_HYBRID_FORWARD_SOURCE_COMMIT_HOLD=" +
          canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
