"""Inert future original Windows V38 forward-only cold backup owner entrypoint.

No source, SQLite, task, policy, runner registration or science mutation.
Stage a NEW event-1830 backup only after a distinct owner-authored backup
comment and earlier independently authenticated read-only readiness comment.
No replay of unknown-effect backup attempts or old V41 database replacement.
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
from f139 import nci04_v41_hybrid_forward_readiness as readiness
from f139 import nci04_v41_hybrid_forward_cold_bundle as bundle
from f139 import nci04_v41_hybrid_forward_repair as forward
from f139 import nci04_v41_hybrid_owner_maintenance as owner
from f139 import nci04_v41_hybrid_forward_owner_profile as profile

PREFIX = "F139-HYBRID-V41-FORWARD-BACKUP "
SCHEMA = "forge.f139.hybrid-forward.original-backup-only.v1"


class ForwardBackupDenied(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise ForwardBackupDenied("F139_HYBRID_FORWARD_BACKUP_" + why)


def authenticate_backup(get, env, event, target):
    """The readiness comment and backup comment are separate owner actions."""
    need(callable(get) and type(env) is dict and type(event) is dict
         and type(target) is str
         and readiness.SHA40.fullmatch(target) is not None
         and env.get("GITHUB_REPOSITORY") == readiness.REPO
         and env.get("GITHUB_ACTOR") == readiness.OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_SHA") == target
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
         and not env.get("OPENAI_API_KEY"),
         "ORIGINAL_FIRST_ATTEMPT_REQUIRED")
    issue, sender, comment = (event.get(k) for k in (
        "issue", "sender", "comment"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == readiness.OWNER
         and "pull_request" not in issue
         and type(sender) is dict and sender.get("login") == readiness.OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == readiness.OWNER
         and comment.get("author_association") == "OWNER"
         and type(comment.get("body")) is str
         and comment["body"].startswith(PREFIX + target + " "),
         "SEPARATE_OWNER_BACKUP_COMMENT_REQUIRED")
    match = re.fullmatch(
        re.escape(PREFIX + target) + r" ([1-9][0-9]*)",
        comment["body"])
    need(match is not None, "EXACT_BACKUP_INTENT_FORMAT_REQUIRED")
    previous_id = int(match.group(1))
    need(previous_id > readiness.OLD_COMMIT_ID
         and previous_id != comment["id"], "DISTINCT_OWNER_EVENTS_REQUIRED")
    backup_time = readiness._owner_comment(
        get, comment["id"], comment["body"])
    prior = get("repos/" + readiness.REPO + "/issues/comments/" +
                str(previous_id))
    need(type(prior) is dict and prior.get("body") ==
         readiness.PREFIX + target + " " + str(readiness.OLD_COMMIT_ID),
         "ORIGINAL_FORWARD_READINESS_NOT_FOUND")
    ready_time = readiness._owner_comment(
        get, previous_id, prior["body"])
    need(ready_time < backup_time, "READINESS_MUST_PRECEDE_BACKUP")
    prior_event = {
        "action": "created", "issue": issue,
        "sender": sender, "comment": prior,
    }
    frozen = readiness.authenticate_readiness(
        get, env, prior_event, target)
    return {
        "backup_run_id": int(env["GITHUB_RUN_ID"]),
        "backup_comment_id": comment["id"],
        "readiness_comment_id": previous_id,
        "target_source_sha": target,
        "frozen_v37_commit": frozen,
    }



def _frozen_source_proof_sha(db, approval, receipt):
    """Compute before SOURCE-COMMIT exists, using the prior owner readiness ID.

    A commit comment ID cannot be an input to a proof hash that must be
    included in that same comment; this breaks the circular dependency.
    """
    need(type(approval) is dict and type(receipt) is dict
         and type(approval.get("readiness_comment_id")) is int
         and approval["readiness_comment_id"] > readiness.OLD_COMMIT_ID
         and type(approval.get("backup_run_id")) is int
         and approval["backup_run_id"] > 0
         and type(approval.get("target_source_sha")) is str
         and readiness.SHA40.fullmatch(approval["target_source_sha"])
         and type(receipt.get("manifest_sha256")) is str
         and forward.HEX64.fullmatch(receipt["manifest_sha256"])
         and type(receipt.get("logical_all_tables_sha256")) is str
         and forward.HEX64.fullmatch(receipt["logical_all_tables_sha256"])
         and receipt.get("candidate_sha") ==
             approval["target_source_sha"]
         and receipt.get("original_source_sha") == forward.FROM
         and receipt.get("original_head_seq") == forward.V37_SEQ
         and receipt.get("original_head_sha256") == forward.V37_HEAD,
         "BACKUP_NOT_BOUND_TO_FROZEN_READINESS")
    proof = forward.build_proof(
        db, approval["target_source_sha"],
        approval["readiness_comment_id"], approval["backup_run_id"],
        receipt["manifest_sha256"],
        receipt["logical_all_tables_sha256"])
    need(proof["owner_event_id"] == approval["readiness_comment_id"]
         and proof["to_source_sha"] == approval["target_source_sha"]
         and proof["backup_run_id"] == approval["backup_run_id"]
         and proof["backup_manifest_sha256"] ==
             receipt["manifest_sha256"],
         "FROZEN_SOURCE_PROOF_NOT_PRECOMPUTABLE")
    return digest(canonical(proof))


def original_backup(db_path, env, event, api):
    """Fresh original source event-1830 backup, with no original writes."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub and type(db_path) is Path,
         "NATIVE_WINDOWS_ORIGINAL_PROVIDER_REQUIRED")
    get = api.native_repo_get
    target = env.get("GITHUB_SHA")
    approval = authenticate_backup(get, env, event, target)
    release = readiness._release(get, target)
    original = owner._original_path(db_path, env)
    owner._candidate_clean_checkout(target)
    old_policy = owner._owner_policy(get)
    profile.readback(original)

    def disabled():
        return profile.readback(original) is True

    def released():
        return (
            owner._candidate_clean_checkout(target) is True
            and owner._owner_policy(get) == old_policy
            and readiness._release(get, target) == release
            and authenticate_backup(get, env, event, target) == approval
        )

    need(disabled() and released(), "PRIOR_OWNER_OR_NEW_RELEASE_CHANGED")
    with SingleOwner(original.with_suffix(".lock")):
        with closing(Database.open_readonly(original)) as db:
            before = db.meta().copy()
            readiness.inspect_held_original(
                db, approval["frozen_v37_commit"])
            receipt = bundle.stage_complete_cold_bundle(
                db, approval["frozen_v37_commit"],
                target=target, run_id=approval["backup_run_id"],
                owner_disabled_witness=disabled,
                release_witness=released)
            expected_proof_sha = _frozen_source_proof_sha(
                db, approval, receipt)
            need(db.meta() == before and db.conn.total_changes == 0,
                 "ORIGINAL_LEDGER_CHANGED_BY_BACKUP")
        need(disabled(), "ORIGINAL_TASK_RESUMED_DURING_BACKUP")
    need(disabled() and released(),
         "POSTBACKUP_OWNER_SOURCE_OR_APPROVAL_DRIFT")
    need(receipt["original_source_sha"] ==
         readiness.forward.FROM
         and receipt["original_head_seq"] ==
         readiness.forward.V37_SEQ
         and receipt["original_head_sha256"] ==
         readiness.forward.V37_HEAD
         and receipt["provider_archives_bytes_verified"] is True
         and receipt["generation_binary_bytes_verified"] is True
         and receipt["independent_detached_restore_verified"] is True
         and receipt["original_owner_mutations"] == 0,
         "DETACHED_FRESH_1830_BACKUP_NOT_QUALIFIED")
    return {
        "schema": SCHEMA,
        "backup_run_id": approval["backup_run_id"],
        "backup_comment_id": approval["backup_comment_id"],
        "readiness_comment_id": approval["readiness_comment_id"],
        "original_source_sha": readiness.forward.FROM,
        "candidate_sha": target,
        "original_event_seq": readiness.forward.V37_SEQ,
        "original_event_head_sha256": readiness.forward.V37_HEAD,
        "manifest_sha256": receipt["manifest_sha256"],
        "expected_proof_sha256": expected_proof_sha,
        "logical_all_tables_sha256":
            receipt["logical_all_tables_sha256"],
        "detached_restore": receipt,
        "original_task_still_disabled": True,
        "original_policy_unchanged": True,
        "forward_source_commit_authorized": False,
        "task_resume_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
        "original_owner_mutations": 0,
        "new_dispatches": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    env = dict(os.environ)
    need(args.target == env.get("GITHUB_SHA"),
         "EXACT_TARGET_REQUIRED")
    event_path = env.get("GITHUB_EVENT_PATH")
    need(type(event_path) is str and Path(event_path).is_file(),
         "ORIGINAL_OWNER_EVENT_REQUIRED")
    try:
        event = json.loads(Path(event_path).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
    except (ValueError, UnicodeError, OSError) as exc:
        raise ForwardBackupDenied(
            "F139_HYBRID_FORWARD_BACKUP_EVENT_INVALID") from exc
    need(type(env.get("LOCALAPPDATA")) is str and
         Path(env["LOCALAPPDATA"]).is_absolute(),
         "ORIGINAL_OWNER_USER_DATA_REQUIRED")
    db = Path(env["LOCALAPPDATA"]) / "FORGE-F139" / "state.sqlite"
    result = original_backup(db, env, event, GitHub())
    print("F139_HYBRID_FORWARD_ORIGINAL_BACKUP=" +
          canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
