"""Read-only original Windows event-1832 proof mismatch classifier.

One exact issue #807 owner diagnostic, on the existing native owner/SQLite
and SingleOwner lock. No source transition, policy write, task control,
scientific first use, credentials, raw task rows or new controller.
This is not an activation receipt and does not grant release authority.
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
from f139 import nci04_v41_hybrid_event1832_commit as committed
from f139 import nci04_v41_hybrid_event1832_successor as successor
from f139 import nci04_v41_hybrid_owner_maintenance as original_owner
from f139 import nci04_v41_hybrid_forward_owner_profile as profile
from f139.hybrid_owner_admission import is_migrated

TARGET = "1479f963160001037566e4cef33582c5293fb773"
COMMIT_COMMENT_ID = 6902472106
POSTCOMMIT_COMMENT_ID = 6902549450
PREFIX = "F139-HYBRID-V39-PROOF-DIAG "
SCHEMA = "forge.f139.v39.event1832-proof-diagnostic-readonly.v1"
REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"


class DiagnosticDenied(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise DiagnosticDenied("F139_V39_PROOF_DIAG_" + why)


def compare_proof(doc, req, raw_payload):
    """Independent per-predicate classification; never changes evidence."""
    need(type(req) is dict and type(raw_payload) is str,
         "FROZEN_REQUEST_AND_CANONICAL_RECORD_REQUIRED")
    doc = doc if type(doc) is dict else {}
    encoded = canonical(doc)
    return {
        "field_set": set(doc) == successor.FIELDS,
        "schema": doc.get("schema") == successor.SCHEMA,
        "owner_event": doc.get("owner_event_id") == req["readiness_comment_id"],
        "backup_run": doc.get("backup_run_id") == req["backup_run_id"],
        "backup_manifest": doc.get("backup_manifest_sha256") ==
                           req["backup_manifest_sha256"],
        "backup_logical_tables": doc.get("backup_logical_all_tables_sha256") ==
                                 req["backup_logical_all_tables_sha256"],
        "target_source": doc.get("to_source_sha") == req["target_source_sha"],
        "approved_proof_digest": digest(encoded) == req["expected_proof_sha256"],
        "canonical_row_payload": raw_payload == encoded.decode("ascii"),
    }


def authenticate(env, event, get):
    """Owner-only, fresh comment is a read-only diagnostic request, not a retry."""
    need(type(env) is dict and type(event) is dict and callable(get)
         and sys.platform == "win32" and os.name == "nt"
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and type(env.get("GITHUB_SHA")) is str
         and successor.SHA40.fullmatch(env["GITHUB_SHA"]) is not None
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
         and not env.get("OPENAI_API_KEY"),
         "ORIGINAL_WINDOWS_OWNER_FIRST_ATTEMPT_ONLY")
    issue, sender, comment = (event.get(k) for k in (
        "issue", "sender", "comment"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > POSTCOMMIT_COMMENT_ID
         and comment.get("body") ==
             PREFIX + TARGET + " " + str(POSTCOMMIT_COMMENT_ID)
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == OWNER
         and comment.get("author_association") == "OWNER",
         "EXACT_NEW_OWNER_DIAGNOSTIC_COMMENT_REQUIRED")
    provider = get("repos/" + REPO + "/issues/comments/" +
                   str(comment["id"]))
    need(type(provider) is dict
         and provider.get("id") == comment["id"]
         and provider.get("body") == comment["body"]
         and provider.get("created_at") == comment.get("created_at")
         and provider.get("user", {}).get("login") == OWNER
         and provider.get("author_association") == "OWNER",
         "ORIGINAL_DIAGNOSTIC_COMMENT_READBACK_DRIFT")
    prior = get("repos/" + REPO + "/issues/comments/" +
                str(COMMIT_COMMENT_ID))
    post = get("repos/" + REPO + "/issues/comments/" +
               str(POSTCOMMIT_COMMENT_ID))
    need(type(prior) is dict and prior.get("id") == COMMIT_COMMENT_ID
         and type(prior.get("body")) is str
         and prior["body"].startswith(committed.PREFIX)
         and prior.get("user", {}).get("login") == OWNER
         and prior.get("author_association") == "OWNER"
         and type(post) is dict and post.get("id") == POSTCOMMIT_COMMENT_ID
         and post.get("body") == (
             "F139-HYBRID-V39-POSTCOMMIT " + TARGET + " " +
             str(COMMIT_COMMENT_ID))
         and post.get("user", {}).get("login") == OWNER
         and post.get("author_association") == "OWNER"
         and prior.get("created_at") < post.get("created_at") <
             comment.get("created_at"),
         "EXACT_PREDECESSOR_OWNER_EVENTS_REQUIRED")
    try:
        req = json.loads(prior["body"][len(committed.PREFIX):],
                         object_pairs_hook=decode_unique)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise DiagnosticDenied(
            "F139_V39_PROOF_DIAG_ORIGINAL_COMMIT_INTENT_NOT_CANONICAL") from exc
    need(type(req) is dict and set(req) == committed.FIELDS
         and prior["body"] == committed.PREFIX + canonical(req).decode("ascii")
         and req["schema"] == committed.SCHEMA
         and req["target_source_sha"] == TARGET
         and req["original_head_seq"] == successor.PREDECESSOR_SEQ
         and req["original_head_sha256"] == successor.PREDECESSOR_SHA
         and req["scientific_first_use"] is False
         and req["hybrid_admission"] is False
         and req["task_resume_authorized"] is False
         and req["owner_policy_update_authorized"] is False
         and req["new_dispatches"] == 0,
         "ORIGINAL_INTENT_SOURCE_OR_SAFETY_DRIFT")
    return req


def inspect(db, req):
    """Cold authentic 1832 ledger; report only which event proof field differs."""
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "COLD_READONLY_SINGLE_OWNER_REQUIRED")
    db.verify()
    before = db.meta().copy()
    need(before["source_sha"] == TARGET
         and before["head_seq"] == successor.PREDECESSOR_SEQ + 1
         and before["enabled"] == 1
         and before["legacy_suspended"] == 1
         and db.dual_native_schema()
         and not is_migrated(db)
         and db.ready() is None and not db.actives(),
         "ORIGINAL_EVENT1832_HELD_SOURCE_NOT_VERIFIED")
    row = db.conn.execute(
        "SELECT kind,seq,sha,prior_sha,payload FROM events WHERE seq=?",
        (successor.PREDECESSOR_SEQ + 1,)).fetchone()
    need(row is not None
         and row["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and row["seq"] == before["head_seq"]
         and row["sha"] == before["head_hash"]
         and row["prior_sha"] == successor.PREDECESSOR_SHA,
         "AUTHENTIC_ORIGINAL_EVENT1832_REQUIRED")
    good = db.conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE stage='VERIFIED'").fetchone()[0]
    bad = db.conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE stage='QUARANTINED'").fetchone()[0]
    need(good == 153 and bad == 56, "ORIGINAL_TASK_CUSTODY_CHANGED")
    try:
        doc = json.loads(row["payload"], object_pairs_hook=decode_unique)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise DiagnosticDenied("F139_V39_PROOF_DIAG_NONCANONICAL_EVENT") from exc
    flags = compare_proof(doc, req, row["payload"])
    need(before == db.meta() and db.conn.total_changes == 0,
         "COLD_DIAGNOSTIC_MODIFIED_LEDGER")
    return {
        "schema": SCHEMA,
        "event_seq": before["head_seq"],
        "source_sha": TARGET,
        "result": "PROOF_MATCH" if all(flags.values()) else "PROOF_MISMATCH",
        "proof_predicates": flags,
        "verified_historical_tasks": good,
        "custodied_negative_tasks": bad,
        "sqlite_changes": 0,
        "original_task_mutations": 0,
        "policy_mutations": 0,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "task_restart": False,
        "activation_authorized": False,
    }


def original_readonly(env, event, api):
    need(type(api) is GitHub, "NATIVE_GITHUB_READONLY_PROVIDER_REQUIRED")
    get = api.native_repo_get
    req = authenticate(env, event, get)
    path = original_owner._original_path(
        Path(env["LOCALAPPDATA"]) / "FORGE-F139" / "state.sqlite", env)
    policy = original_owner._owner_policy(get)
    profile.readback(path)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as db:
            receipt = inspect(db, req)
    need(profile.readback(path) is True
         and original_owner._owner_policy(get) == policy
         and authenticate(env, event, get) == req,
         "POSTREADBACK_ORIGINAL_OWNER_DRIFT")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    env = dict(os.environ)
    event_path = env.get("GITHUB_EVENT_PATH")
    need(type(event_path) is str and Path(event_path).is_file(),
         "ORIGINAL_EVENT_PATH_MISSING")
    try:
        event = json.loads(Path(event_path).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
    except (ValueError, OSError, UnicodeError) as exc:
        raise DiagnosticDenied("F139_V39_PROOF_DIAG_EVENT_PARSE") from exc
    receipt = original_readonly(env, event, GitHub())
    print("F139_V39_EVENT1832_READONLY_PROOF_DIAGNOSTIC=" +
          canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
