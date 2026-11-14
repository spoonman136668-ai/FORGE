"""Original V41->Hybrid source-commit uncertainty: READ-ONLY classification.

Never retry an uncertain commit, restore old SQLite, resume the original
scheduled task, edit policy, or enable Hybrid. Only classify genuine original
V41 (no source commit) versus one fully authenticated V37 committed event.
Unknown/inconsistent states FAIL CLOSED. This module registers no workflow.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sys

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_original_commit as commit
from f139 import nci04_v41_hybrid_owner_maintenance as owner
from f139 import nci04_v41_hybrid_source_transition as source
from f139 import nci04_v41_hybrid_successor_release as release
from f139 import nci04_v41_hybrid_cold_bundle as bundle

SCHEMA = "forge.f139.hybrid-v41.original-source-uncertain-recovery-readonly.v1"


class HeldRecoveryDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise HeldRecoveryDenied("F139_HYBRID_V41_RECOVERY_" + code)


def _cold(db, req):
    """Read fresh immutable full-bundle proof, never stage or rewrite it."""
    folder = db.filename.parent / (
        "f139-hybrid-before-" + str(req["backup_run_id"]))
    result = bundle.verify_detached_restore(
        folder,
        expected_manifest_sha256=req["backup_manifest_sha256"],
        target_sha=req["target_source_sha"],
        run_id=req["backup_run_id"],
        expected_head_seq=req["original_head_seq"],
        expected_head_sha256=req["original_head_sha256"],
    )
    need(type(result) is dict and
         result.get("independent_detached_restore_verified") is True
         and result.get("provider_archives_bytes_verified") is True
         and result.get("generation_binary_bytes_verified") is True
         and result.get("original_owner_mutations") == 0
         and result.get("source_transition_authorized") is False
         and result.get("hybrid_admission") is False
         and result.get("scientific_first_use") is False
         and type(result.get("logical_all_tables_sha256")) is str
         and source.HEX64.fullmatch(result["logical_all_tables_sha256"]) is not None,
         "FROZEN_FULL_COLD_BUNDLE_REQUIRED")
    return result


def inspect_held_ledger(db, req):
    """Determine PRECOMMIT or COMMITTED from the actual source-event chain.

    This is a read-only observation, not a source-release or replay receipt.
    The caller must separately verify original Windows SID, disabled task,
    signed protected main, exact owner comment and unchanged owner policy.
    """
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and type(req) is dict and
         type(req.get("target_source_sha")) is str
         and source.HEX40.fullmatch(req["target_source_sha"]) is not None
         and req["target_source_sha"] != source.FROM_V41
         and type(req.get("original_head_seq")) is int
         and req["original_head_seq"] >= source.ACTIVATED_SEQ
         and type(req.get("original_head_sha256")) is str
         and source.HEX64.fullmatch(req["original_head_sha256"]) is not None
         and type(req.get("readiness_comment_id")) is int
         and req["readiness_comment_id"] > 0
         and type(req.get("backup_run_id")) is int
         and req["backup_run_id"] > 0
         and type(req.get("backup_manifest_sha256")) is str
         and source.HEX64.fullmatch(req["backup_manifest_sha256"]) is not None,
         "AUTHENTICATED_READONLY_OR_FROZEN_REQUEST_REQUIRED")
    db.verify()
    before = db.meta().copy()
    need(before["enabled"] == 1
         and before["legacy_suspended"] == 1
         and db.ready() is None and not db.actives(),
         "NONIDLE_ORIGINAL_OWNER_HOLD")
    cold = _cold(db, req)
    target = req["target_source_sha"]
    prior_seq = req["original_head_seq"]
    prior_hash = req["original_head_sha256"]

    if before["source_sha"] == source.FROM_V41:
        source._original(db)
        need(before["head_seq"] == prior_seq
             and before["head_hash"] == prior_hash
             and db.conn.execute(
                 "SELECT COUNT(*) FROM events WHERE seq>?",
                 (prior_seq,)).fetchone()[0] == 0,
             "UNCOMMITTED_ORIGINAL_PREIMAGE_MOVED")
        classification = "PRECOMMIT_UNCHANGED_HOLD"
        committed_event = False
        event_seq = prior_seq
        event_hash = prior_hash
    elif before["source_sha"] == target:
        need(before["head_seq"] == prior_seq + 1,
             "COMMITTED_SOURCE_MUST_BE_ONE_EVENT")
        row = db.conn.execute(
            "SELECT seq,kind,sha,prior_sha,payload FROM events WHERE seq=?",
            (prior_seq + 1,)).fetchone()
        need(row is not None and row["kind"] == "SOURCE_TRANSITION_ADMITTED"
             and row["sha"] == before["head_hash"]
             and row["prior_sha"] == prior_hash,
             "EXACT_COMMITTED_SOURCE_EVENT_REQUIRED")
        try:
            proof = json.loads(row["payload"], object_pairs_hook=decode_unique)
        except (UnicodeError, ValueError, TypeError) as exc:
            raise HeldRecoveryDenied(
                "F139_HYBRID_V41_RECOVERY_NONCANONICAL_EVENT") from exc
        need(type(proof) is dict and set(proof) == source.FIELDS
             and proof["schema"] == source.SCHEMA
             and proof["to_source_sha"] == target
             and proof["owner_event_id"] == req["readiness_comment_id"]
             and proof["original_head_seq"] == prior_seq
             and proof["original_head_sha256"] == prior_hash
             and proof["backup_run_id"] == req["backup_run_id"]
             and proof["backup_manifest_sha256"] ==
                 req["backup_manifest_sha256"]
             and proof["backup_logical_all_tables_sha256"] ==
                 cold["logical_all_tables_sha256"],
             "SOURCE_EVENT_NOT_BOUND_TO_COLD_APPROVED_PREIMAGE")
        previous = [json.loads(pr["payload"], object_pairs_hook=decode_unique)
                    for pr in db.conn.execute(
                        "SELECT payload FROM events "
                        "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? "
                        "ORDER BY seq", (row["seq"],))]
        source.verify_cold_event(db, row, proof, previous)
        reconstructed = {
            "schema": "forge.f139.hybrid-v41.source-commit-hold.v1",
            "source_sha": target,
            "event_seq": row["seq"],
            "event_head_sha256": row["sha"],
            "task_resume_authorized": False,
            "policy_update_authorized": False,
            "hybrid_admission": False,
            "scientific_first_use": False,
            "new_dispatches": 0,
        }
        verified = commit.verify_postcommit_readonly(
            db, proof, reconstructed)
        need(verified["event_seq"] == row["seq"]
             and verified["custodied_negative_tasks"] ==
                 proof["custodied_negative_tasks"],
             "POSTCOMMIT_HISTORY_OR_NEGATIVE_DRIFT")
        classification = "COMMITTED_SOURCE_HOLD"
        committed_event = True
        event_seq = row["seq"]
        event_hash = row["sha"]
    else:
        raise HeldRecoveryDenied(
            "F139_HYBRID_V41_RECOVERY_UNKNOWN_OR_MIXED_SOURCE_HOLD")

    need(db.meta() == before and db.conn.total_changes == 0
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
         "READONLY_INSPECTION_CHANGED_SOURCE")
    return {
        "schema": SCHEMA,
        "classification": classification,
        "target_source_sha": target,
        "event_seq": event_seq,
        "event_head_sha256": event_hash,
        "source_commit_recorded": committed_event,
        "full_detached_cold_backup_verified": True,
        "readback_database_mutations": 0,
        "original_task_resume_authorized": False,
        "source_commit_retry_authorized": False,
        "source_policy_activation_authorized": False,
        "restore_older_sqlite_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }


def inspect_original(db_path, env, event, api):
    """Original Windows OWNER read-only diagnostic; no mutations permitted."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub
         and isinstance(db_path, Path),
         "ORIGINAL_WINDOWS_NATIVE_PROVIDER_REQUIRED")
    get = api.native_repo_get
    req = commit.authenticate_commit_request(env, event, get)
    target = req["target_source_sha"]
    release.require_successor_source(get, target, env=env)
    path = owner._original_path(db_path, env)
    owner._candidate_clean_checkout(target)
    policy = owner._owner_policy(get)
    owner._task_readback(path, disabled=True)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as db:
            result = inspect_held_ledger(db, req)
    need(owner._task_readback(path, disabled=True) is True
         and owner._owner_policy(get) == policy
         and release.require_successor_source(get, target, env=env)["source_sha"]
             == target
         and commit.authenticate_commit_request(env, event, get) == req,
         "OWNER_DISABLED_POLICY_OR_APPROVAL_DRIFT")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    need(args.target == env.get("GITHUB_SHA"),
         "TARGET_CANDIDATE_MISMATCH")
    path = env.get("GITHUB_EVENT_PATH")
    need(type(path) is str and Path(path).is_file(),
         "EXACT_ORIGINAL_OWNER_EVENT_REQUIRED")
    event = json.loads(Path(path).read_text("utf-8"),
                       object_pairs_hook=decode_unique)
    db = Path(env.get("LOCALAPPDATA", "")) / "FORGE-F139" / "state.sqlite"
    receipt = inspect_original(db, env, event, GitHub())
    print("F139_HYBRID_V41_UNCERTAIN_COMMIT_READONLY=" +
          canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
