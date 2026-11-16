"""Independent V40 original-owner postcommit readback after source event1833.

Owner-only read-only confirmation. It never updates SQLite, issue 807 policy,
scheduled task, scientific first use or worker dispatch. A separate postcommit
owner comment must follow an authenticated one-time source-commit intent and
successful real backup job; comment alone cannot activate the controller.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sys

from f139.local_controller import Database, GitHub, SingleOwner, canonical as event_canonical
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_event1833_owner as owner
from f139 import nci04_v41_hybrid_event1833_commit as committed
from f139 import nci04_v41_hybrid_event1833_successor as successor
from f139 import nci04_v41_hybrid_owner_maintenance as original_owner
from f139 import nci04_v41_hybrid_forward_owner_profile as profile
from f139 import nci04_v41_hybrid_forward_readiness as old_readiness
from f139.hybrid_owner_admission import is_migrated

PREFIX = "F139-HYBRID-V40-POSTCOMMIT "
SCHEMA = "forge.f139.v40.original-event1833-postcommit-readonly.v1"


class Event1833PostcommitDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise Event1833PostcommitDenied("F139_V40_POSTCOMMIT_" + reason)


def authenticate(get, env, event):
    need(type(env) is dict and type(event) is dict
         and type(event.get("comment")) is dict
         and type(event["comment"].get("body")) is str,
         "POSTCOMMIT_EVENT_REQUIRED")
    target = env.get("GITHUB_SHA")
    need(type(target) is str
         and successor.SHA40.fullmatch(target) is not None,
         "POSTCOMMIT_TARGET_REQUIRED")
    matched = re.fullmatch(
        re.escape(PREFIX + target) + r" ([1-9][0-9]*)",
        event["comment"]["body"])
    need(matched is not None, "EXACT_NEW_POSTCOMMIT_COMMENT_REQUIRED")
    prior_id = int(matched.group(1))
    _, current, stamp, issue, sender = owner._native_event(
        get, env, event, PREFIX, prior_id)
    need(owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID < prior_id <
         current["id"], "FRESH_COMMIT_PRECEDES_POSTCOMMIT_REQUIRED")
    prior = get("repos/" + owner.REPO + "/issues/comments/" +
                str(prior_id))
    need(type(prior) is dict and prior.get("id") == prior_id
         and type(prior.get("body")) is str
         and prior["body"].startswith(committed.PREFIX)
         and old_readiness._owner_comment(
             get, prior_id, prior["body"]) < stamp,
         "AUTHENTICATED_COMMIT_INTENT_MISSING")
    request = committed.authenticate_commit(
        get, env, {
            "action": "created", "issue": issue,
            "sender": sender, "comment": prior,
        })
    need(request["target_source_sha"] == target
         and request["source_commit_comment_id"] == prior_id,
         "POSTCOMMIT_ORIGINAL_SOURCE_NOT_BOUND")
    return request | {
        "postcommit_comment_id": current["id"]
    }


def inspect(db, request):
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and type(request) is dict,
         "READONLY_ORIGINAL_MUTEX_REQUIRED")
    before = db.meta().copy()
    db.verify()
    need(before["source_sha"] == request["target_source_sha"]
         and before["head_seq"] == successor.PREDECESSOR_SEQ + 1
         and before["enabled"] == 1 and before["legacy_suspended"] == 1
         and db.dual_native_schema()
         and not is_migrated(db)
         and db.ready() is None and not db.actives(),
         "EXACT_HELD_1832_PREACTIVATION_REQUIRED")
    row = db.conn.execute(
        "SELECT seq,kind,sha,prior_sha,payload FROM events WHERE seq=?",
        (successor.PREDECESSOR_SEQ + 1,)).fetchone()
    need(row is not None
         and row["seq"] == successor.PREDECESSOR_SEQ + 1
         and row["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and row["prior_sha"] == request["original_head_sha256"]
         and row["sha"] == before["head_hash"],
         "ORIGINAL_COMMITTED_EVENT1833_MISSING")
    try:
        doc = json.loads(row["payload"], object_pairs_hook=decode_unique)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise Event1833PostcommitDenied(
            "F139_V40_POSTCOMMIT_EVENT_NONCANONICAL") from exc
    need(type(doc) is dict and set(doc) == successor.FIELDS
         and doc["schema"] == successor.SCHEMA
         and doc["owner_event_id"] == request["readiness_comment_id"]
         and doc["backup_run_id"] == request["backup_run_id"]
         and doc["backup_manifest_sha256"] ==
             request["backup_manifest_sha256"]
         and doc["backup_logical_all_tables_sha256"] ==
             request["backup_logical_all_tables_sha256"]
         and doc["to_source_sha"] == request["target_source_sha"]
         and digest(canonical(doc)) == request["expected_proof_sha256"]
         and row["payload"] == event_canonical(doc).decode("ascii"),
         "EVENT1833_COLD_APPROVAL_OR_PROOF_DRIFT")
    verified_cold = committed._fresh_cold(db.filename, request)
    need(verified_cold["original_head_seq"] == successor.PREDECESSOR_SEQ
         and verified_cold["original_head_sha256"] ==
             request["original_head_sha256"]
         and verified_cold["negative_custody_bytes_verified"] is True,
         "ORIGINAL_EVENT1831_COLD_NOT_AUTHENTIC")
    readback = committed.inspect_postcommit(db, request, doc)
    need(readback["event_seq"] == successor.PREDECESSOR_SEQ + 1
         and readback["verified_historical_tasks"] == 153
         and readback["custodied_negative_tasks"] == 56
         and readback["scientific_first_use"] is False
         and before == db.meta()
         and db.conn.total_changes == 0,
         "POSTCOMMIT_ORIGINAL_CHANGED_BY_READBACK")
    return {
        "schema": SCHEMA,
        **readback,
        "source_commit_comment_id": request["source_commit_comment_id"],
        "postcommit_comment_id": request["postcommit_comment_id"],
        "backup_run_id": request["backup_run_id"],
        "original_task_still_disabled": True,
        "hybrid_schema_migrated": False,
        "native_activation_performed": False,
    }


def original_postcommit(path, env, event, api):
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub and isinstance(path, Path),
         "EXACT_ORIGINAL_WINDOWS_OWNER_REQUIRED")
    get = api.native_repo_get
    req = authenticate(get, env, event)
    target = req["target_source_sha"]
    qualification = owner.release(get, target)
    path = original_owner._original_path(path, env)
    original_owner._candidate_clean_checkout(target)
    policy = original_owner._owner_policy(get)
    profile.readback(path)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as db:
            result = inspect(db, req)
    need(profile.readback(path) is True
         and original_owner._owner_policy(get) == policy
         and original_owner._candidate_clean_checkout(target) is True
         and owner.release(get, target) == qualification
         and authenticate(get, env, event) == req,
         "POSTCOMMIT_OWNER_SOURCE_OR_POLICY_MOVED")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    need(args.target == env.get("GITHUB_SHA"),
         "EXACT_NEW_SOURCE_REQUIRED")
    event_path = env.get("GITHUB_EVENT_PATH")
    need(type(event_path) is str and Path(event_path).is_file(),
         "OWNER_EVENT_NOT_AVAILABLE")
    try:
        event = json.loads(
            Path(event_path).read_text("utf-8"),
            object_pairs_hook=decode_unique)
    except (OSError, ValueError, UnicodeError) as exc:
        raise Event1833PostcommitDenied(
            "F139_V40_POSTCOMMIT_EVENT_PARSE") from exc
    need(type(env.get("LOCALAPPDATA")) is str
         and Path(env["LOCALAPPDATA"]).is_absolute(),
         "ORIGINAL_LOCALAPPDATA_REQUIRED")
    path = Path(env["LOCALAPPDATA"]) / "FORGE-F139" / "state.sqlite"
    proof = original_postcommit(path, env, event, GitHub())
    print("F139_V40_ORIGINAL_POSTCOMMIT_READONLY=" +
          canonical(proof).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
