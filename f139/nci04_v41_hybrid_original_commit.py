"""Separate V41->Hybrid original-source commit command; unregistered owner route.

This module is inert without a NEW exact-source original OWNER COMMIT comment,
a fresh target-bound full cold backup, source/readiness approvals, a disabled
original Windows task, and protected-main release CI. No task/policy activation
or scientific first-use. Never register this entrypoint with Actions here.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sys

from f139.local_controller import Database, GitHub, SingleOwner, canonical as ledger_canonical
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_source_transition as source
from f139 import nci04_v41_hybrid_owner_maintenance as owner
from f139 import nci04_v41_hybrid_successor_release as release

SCHEMA = "forge.f139.hybrid-v41.original-source-commit-intent.v1"
PREFIX = "F139-HYBRID-V41-SOURCE-COMMIT "
RECEIPT = "forge.f139.hybrid-v41.original-source-commit-held.v1"
POSTCOMMIT = "forge.f139.hybrid-v41.original-postcommit-readonly.v1"
FIELDS = frozenset({
    "schema", "target_source_sha", "backup_run_id",
    "backup_manifest_sha256", "paired_approval_id", "readiness_comment_id",
    "original_head_seq", "original_head_sha256", "expected_proof_sha256",
    "source_transition_requested", "task_resume_authorized",
    "policy_update_authorized", "hybrid_admission",
    "scientific_first_use", "new_dispatches",
})


class OriginalCommitDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OriginalCommitDenied("F139_HYBRID_V41_COMMIT_" + reason)


def authenticate_commit_request(env, event, get):
    """Explicit NEW owner comment, unlike the old READINESS-ONLY comment."""
    need(type(env) is dict and type(event) is dict and callable(get)
         and env.get("GITHUB_REPOSITORY") == release.REPO
         and env.get("GITHUB_ACTOR") == release.OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and type(env.get("GITHUB_RUN_ID")) is str
         and env["GITHUB_RUN_ID"].isdigit()
         and int(env["GITHUB_RUN_ID"]) > 0
         and not env.get("OPENAI_API_KEY"),
         "FIRST_ATTEMPT_ORIGINAL_RUNNER_REQUIRED")
    issue, sender, comment = (event.get(k) for k in ("issue", "sender", "comment"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == release.OWNER
         and type(sender) is dict and sender.get("login") == release.OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > 0
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == release.OWNER
         and comment.get("author_association") == "OWNER"
         and type(comment.get("body")) is str
         and comment["body"].startswith(PREFIX),
         "EXPLICIT_SEPARATE_SOURCE_COMMIT_EVENT_REQUIRED")
    try:
        doc = json.loads(comment["body"][len(PREFIX):],
                         object_pairs_hook=decode_unique)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise OriginalCommitDenied("F139_HYBRID_V41_COMMIT_CANONICAL_JSON_REQUIRED") from exc
    need(type(doc) is dict and set(doc) == FIELDS
         and comment["body"] == PREFIX + canonical(doc).decode("ascii")
         and doc["schema"] == SCHEMA
         and type(doc["target_source_sha"]) is str
         and source.HEX40.fullmatch(doc["target_source_sha"]) is not None
         and doc["target_source_sha"] == env.get("GITHUB_SHA")
         and doc["target_source_sha"] != source.FROM_V41
         and all(type(doc[k]) is int and doc[k] > 0 for k in (
             "backup_run_id", "paired_approval_id", "readiness_comment_id",
             "original_head_seq"))
         and len({doc["readiness_comment_id"], doc["paired_approval_id"],
                  comment["id"]}) == 3
         and doc["original_head_seq"] >= source.ACTIVATED_SEQ
         and all(type(doc[k]) is str and
                 source.HEX64.fullmatch(doc[k]) is not None for k in (
                     "backup_manifest_sha256", "original_head_sha256",
                     "expected_proof_sha256"))
         and doc["source_transition_requested"] is True
         and all(doc[k] is False for k in (
             "task_resume_authorized", "policy_update_authorized",
             "hybrid_admission", "scientific_first_use"))
         and type(doc["new_dispatches"]) is int
         and doc["new_dispatches"] == 0,
         "EXACT_NONSCIENCE_SOURCE_COMMIT_INTENT_REQUIRED")
    # Authentic live owner comment is checked twice; do not trust event alone.
    body = comment["body"]
    for _ in range(2):
        stamp = release._comment(get, comment["id"], body)
        need(stamp == comment.get("created_at"),
             "COMMIT_COMMENT_TIMESTAMP_OR_IDENTITY_DRIFT")
    readiness_body = (
        release.PREFIX + doc["target_source_sha"] + " " +
        str(doc["backup_run_id"]) + " " + doc["backup_manifest_sha256"] +
        " " + str(doc["paired_approval_id"]))
    readiness_time = release._comment(
        get, doc["readiness_comment_id"], readiness_body)
    need(readiness_time < comment["created_at"],
         "READINESS_COMMENT_NOT_BEFORE_SOURCE_COMMIT")
    readiness_comment = get(
        "repos/" + release.REPO + "/issues/comments/" +
        str(doc["readiness_comment_id"]))
    readiness_event = {
        "action": "created", "issue": issue, "sender": sender,
        "comment": readiness_comment,
    }
    initial = release.authenticate_owner_intent(
        get, env, readiness_event, target=doc["target_source_sha"],
        run_id=doc["backup_run_id"],
        manifest_sha=doc["backup_manifest_sha256"],
        approval_id=doc["paired_approval_id"])
    need(initial["owner_event_id"] == doc["readiness_comment_id"],
         "READINESS_COMMENT_SOURCE_DRIFT")
    return doc | {"source_commit_comment_id": comment["id"],
                  "readiness_owner_event_id": initial["owner_event_id"]}


def verify_postcommit_readonly(db, proof, receipt):
    """Read-only V37 event, old task counts and exact held-source verification."""
    need(type(db) is Database and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_LOCKED_READONLY_REQUIRED")
    need(type(proof) is dict and set(proof) == source.FIELDS
         and type(receipt) is dict
         and receipt.get("schema") == "forge.f139.hybrid-v41.source-commit-hold.v1"
         and receipt.get("source_sha") == proof["to_source_sha"]
         and receipt.get("event_seq") == proof["original_head_seq"] + 1
         and type(receipt.get("event_head_sha256")) is str
         and source.HEX64.fullmatch(receipt["event_head_sha256"])
         and receipt.get("task_resume_authorized") is False
         and receipt.get("policy_update_authorized") is False
         and receipt.get("hybrid_admission") is False
         and receipt.get("scientific_first_use") is False
         and receipt.get("new_dispatches") == 0,
         "EXACT_SOURCE_COMMIT_RECEIPT_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == proof["to_source_sha"]
         and meta["head_seq"] == receipt["event_seq"]
         and meta["head_hash"] == receipt["event_head_sha256"]
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and db.ready() is None and not db.actives(),
         "POSTCOMMIT_ORIGINAL_SOURCE_HEAD_OR_IDLE_DRIFT")
    rows = db.conn.execute(
        "SELECT seq,kind,sha,prior_sha,payload FROM events "
        "WHERE seq=?", (receipt["event_seq"],)).fetchall()
    need(len(rows) == 1 and rows[0]["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and rows[0]["sha"] == receipt["event_head_sha256"]
         and rows[0]["prior_sha"] == proof["original_head_sha256"]
         and rows[0]["payload"] == ledger_canonical(proof).decode("ascii"),
         "POSTCOMMIT_EVENT_HASH_OR_PAYLOAD_DRIFT")
    before = db.conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE stage='VERIFIED'").fetchone()[0]
    quarantined = db.conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE stage='QUARANTINED'").fetchone()[0]
    need(before >= proof["verified_historical_tasks"]
         and quarantined == proof["custodied_negative_tasks"],
         "POSTCOMMIT_HISTORY_OR_NEGATIVE_CUSTODY_DRIFT")
    return {
        "schema": POSTCOMMIT,
        "source_sha": proof["to_source_sha"],
        "event_seq": receipt["event_seq"],
        "event_head_sha256": receipt["event_head_sha256"],
        "verified_historical_tasks": before,
        "custodied_negative_tasks": quarantined,
        "original_owner_mutations": 0,
        "task_resume_authorized": False,
        "policy_update_authorized": False,
        "source_transition_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }


def original_commit(db_path, env, event, api):
    """Real one-shot source-only transaction; old original task stays DISABLED.

    Not callable from any registered workflow. Must be invoked separately on
    authorized original owner AFTER a fresh target-bound backup/restore.
    """
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub
         and isinstance(db_path, Path),
         "WINDOWS_ORIGINAL_HOST_AND_NATIVE_PROVIDER_REQUIRED")
    get = api.native_repo_get
    req = authenticate_commit_request(env, event, get)
    target = req["target_source_sha"]
    identity = release.require_successor_source(get, target, env=env)
    original_path = owner._original_path(db_path, env)
    owner._candidate_clean_checkout(target)
    old_policy = owner._owner_policy(get)
    owner._task_readback(original_path, disabled=True)
    with SingleOwner(original_path.with_suffix(".lock")):
        with closing(Database.open_readonly(original_path)) as readonly:
            head = readonly.meta().copy()
            need(head["head_seq"] == req["original_head_seq"]
                 and head["head_hash"] == req["original_head_sha256"],
                 "OWNER_PREIMAGE_MOVED")
            proof = source.build_proof(
                readonly, target, req["readiness_comment_id"],
                req["backup_run_id"], req["backup_manifest_sha256"])
            need(digest(canonical(proof)) == req["expected_proof_sha256"]
                 and readonly.meta() == head
                 and readonly.conn.total_changes == 0,
                 "FROZEN_PROOF_MISMATCH_OR_ORIGINAL_CHANGED")

        def disabled():
            # Independently recheck original task, SID, source path, and quiescence.
            return owner._task_readback(original_path, disabled=True) is True

        def release_witness():
            return (
                owner._candidate_clean_checkout(target) is True
                and owner._owner_policy(get) == old_policy
                and release.require_successor_source(
                    get, target, env=env) == identity
                and authenticate_commit_request(env, event, get) == req
            )

        need(disabled() and release_witness(),
             "PRECOMMIT_OWNER_OR_REMOTE_RELEASE_CHANGED")
        with closing(Database(original_path)) as writer:
            need(writer.meta() == head,
                 "WRITER_PREIMAGE_MOVED")
            receipt = source.commit_transition(
                writer, proof,
                disabled_owner_witness=disabled,
                verified_release_witness=release_witness)
        need(disabled(), "POSTCOMMIT_OWNER_TASK_NOT_DISABLED")
        with closing(Database.open_readonly(original_path)) as final:
            post = verify_postcommit_readonly(final, proof, receipt)
        need(disabled() and owner._owner_policy(get) == old_policy,
             "POSTCOMMIT_ORIGINAL_TASK_OR_POLICY_CHANGED")
    return {"schema": RECEIPT,
            "target_source_sha": target,
            "source_commit_comment_id": req["source_commit_comment_id"],
            "readiness_comment_id": req["readiness_comment_id"],
            "backup_run_id": req["backup_run_id"],
            "backup_manifest_sha256": req["backup_manifest_sha256"],
            "commit": receipt,
            "postcommit": post,
            "original_task_still_disabled": True,
            "original_policy_unchanged": True,
            "owner_activation_authorized": False,
            "hybrid_admission": False,
            "scientific_first_use": False,
            "new_dispatches": 0}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    need(args.target == env.get("GITHUB_SHA"),
         "EXACT_TRIGGERING_SOURCE_REQUIRED")
    path = env.get("GITHUB_EVENT_PATH")
    need(type(path) is str and Path(path).is_file(),
         "OWNER_EVENT_FILE_REQUIRED")
    e = json.loads(Path(path).read_text("utf-8"),
                   object_pairs_hook=decode_unique)
    db_path = Path(env.get("LOCALAPPDATA", "")) / "FORGE-F139" / "state.sqlite"
    receipt = original_commit(db_path, env, e, GitHub())
    print("F139_HYBRID_V41_SOURCE_COMMIT_HOLD=" +
          canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
