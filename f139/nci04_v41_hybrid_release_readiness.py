"""Original Windows read-only v37 release readiness; NO source transition.

Unregistered CLI; requires separately issued exact-target OWNER comment and
new target-bound full cold bundle. No task pause, scheduler, policy, dispatch,
SQLite writer or science first-use. The later real owner source-commit needs
its own independently approved wrapper and source/worker acceptance.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_source_transition as transition
from f139 import nci04_v41_hybrid_owner_maintenance as owner
from f139 import nci04_v41_hybrid_successor_release as release

SCHEMA = "forge.f139.hybrid-v41.original-owner-readiness-only.v1"


def inspect_original(db_path, env, event, get, *, target, run_id,
                     manifest_sha, approval_id):
    release.need(os.name == "nt", "ORIGINAL_WINDOWS_HOST_REQUIRED")
    source = release.require_successor_source(get, target, env=env)
    intent = release.authenticate_owner_intent(
        get, env, event, target=target, run_id=run_id,
        manifest_sha=manifest_sha, approval_id=approval_id)
    db_path = owner._original_path(db_path, env)
    owner._candidate_clean_checkout(target)
    policy = owner._owner_policy(get)
    owner._task_readback(db_path, disabled=True)
    with SingleOwner(db_path.with_suffix(".lock")):
        with closing(Database.open_readonly(db_path)) as db:
            meta = db.meta().copy()
            proof = transition.build_proof(
                db, target, intent["owner_event_id"], run_id, manifest_sha)
            release.need(db.meta() == meta and db.conn.total_changes == 0
                         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
                         "ORIGINAL_DATABASE_CHANGED_DURING_READINESS")
    owner._task_readback(db_path, disabled=True)
    release.need(
        owner._owner_policy(get) == policy
        and release.require_successor_source(get, target, env=env) == source
        and release.authenticate_owner_intent(
            get, env, event, target=target, run_id=run_id,
            manifest_sha=manifest_sha, approval_id=approval_id) == intent,
        "POSTCHECK_OWNER_SOURCE_OR_APPROVAL_DRIFT")
    return {
        "schema": SCHEMA,
        "source_sha": target,
        "original_head_seq": proof["original_head_seq"],
        "original_head_sha256": proof["original_head_sha256"],
        "verified_historical_tasks": proof["verified_historical_tasks"],
        "custodied_negative_tasks": proof["custodied_negative_tasks"],
        "owner_event_id": intent["owner_event_id"],
        "backup_run_id": run_id,
        "backup_manifest_sha256": manifest_sha,
        "independent_detached_restore_verified": True,
        "original_owner_mutations": 0,
        "task_resume_authorized": False,
        "source_transition_authorized": False,
        "policy_update_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--backup-run-id", required=True, type=int)
    parser.add_argument("--backup-manifest", required=True)
    parser.add_argument("--paired-approval-id", required=True, type=int)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    release.need(os.name == "nt", "ORIGINAL_WINDOWS_HOST_REQUIRED")
    event_path = env.get("GITHUB_EVENT_PATH")
    release.need(type(event_path) is str and Path(event_path).is_file(),
                 "EXACT_OWNER_EVENT_FILE_REQUIRED")
    event = json.loads(Path(event_path).read_text("utf-8"),
                       object_pairs_hook=decode_unique)
    db = Path(env.get("LOCALAPPDATA", "")) / "FORGE-F139" / "state.sqlite"
    receipt = inspect_original(
        db, env, event, GitHub().native_repo_get,
        target=args.target, run_id=args.backup_run_id,
        manifest_sha=args.backup_manifest,
        approval_id=args.paired_approval_id)
    print("F139_HYBRID_V41_RELEASE_READINESS_ONLY=" +
          canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
