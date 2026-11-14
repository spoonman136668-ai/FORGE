"""One-shot paired owner intent for V41 Hybrid backup maintenance.

No scheduler, task control, policy mutation or release authority.  The
separate Windows wrapper owns the already-existing task's bounded lifecycle.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_owner_maintenance as owner
from f139 import nci04_v41_hybrid_cold_pair as pair
from f139 import nci04_v41_hybrid_cold_bundle as bundle

PREFIX = "F139-HYBRID-V41-PAUSE-RESUME "
REPO = owner.REPO
OWNER = owner.OWNER
COMMENT_RE = re.compile(
    r"F139-HYBRID-V41-PAUSE-RESUME ([a-f0-9]{40}) ([1-9][0-9]*)\Z")
STAMP_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")


class PairOwnerDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise PairOwnerDenied("F139_HYBRID_V41_PAIRED_OWNER_" + reason)


def _comment_identity(doc, *, id, body, stamp=None):
    need(type(doc) is dict and type(doc.get("id")) is int and doc["id"] == id
         and doc.get("body") == body
         and doc.get("author_association") == "OWNER"
         and type(doc.get("user")) is dict
         and doc["user"].get("login") == OWNER
         and doc.get("issue_url") ==
            "https://api.github.com/repos/" + REPO + "/issues/807"
         and type(doc.get("created_at")) is str
         and STAMP_RE.fullmatch(doc["created_at"]) is not None
         and (stamp is None or doc["created_at"] == stamp),
         "COMMENT_CUSTODY_DRIFT")
    return doc["created_at"]


def authenticate_pair(env, event, get, *, target_sha):
    """Require an earlier backup request followed by a distinct owner approval.

    A single backup comment is never sufficient authority to pause the task.
    Every historical event/receipt remains read-only.  Source checkout/owner
    SID and task lifecycle are checked separately by the maintenance route.
    """
    need(type(env) is dict and type(event) is dict and callable(get)
         and type(target_sha) is str
         and pair.SHA40.fullmatch(target_sha) is not None
         and target_sha != pair.V41_SOURCE
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_SHA") == pair.V41_SOURCE
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"]) is not None
         and not env.get("OPENAI_API_KEY"),
         "EVENT_RUNNER_MAIN_OR_FIRST_ATTEMPT_DRIFT")
    issue, comment, sender = (event.get(x) for x in ("issue", "comment", "sender"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > 0
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and type(comment.get("body")) is str,
         "OWNER_EVENT_OR_ISSUE_SCOPE")
    parsed = COMMENT_RE.fullmatch(comment["body"])
    need(parsed is not None and parsed.group(1) == target_sha
         and int(parsed.group(2)) > 0
         and int(parsed.group(2)) != comment["id"],
         "INDEPENDENT_PAIRED_APPROVAL_REQUIRED")
    backup_id = int(parsed.group(2))
    before_stamp = comment.get("created_at")
    need(type(before_stamp) is str and
         STAMP_RE.fullmatch(before_stamp) is not None,
         "APPROVAL_TIMESTAMP_UNVERIFIED")
    routes = (
        ("repos/" + REPO + "/issues/comments/" + str(backup_id),
         backup_id, owner.PREFIX + target_sha),
        ("repos/" + REPO + "/issues/comments/" + str(comment["id"]),
         comment["id"], comment["body"]),
    )
    for _ in range(2):
        found = []
        for route, number, body in routes:
            found.append(_comment_identity(
                get(route), id=number, body=body,
                stamp=before_stamp if number == comment["id"] else None))
        need(found[0] < found[1],
             "BACKUP_REQUEST_NOT_BEFORE_INDEPENDENT_APPROVAL")
    return {
        "run_id": int(env["GITHUB_RUN_ID"]),
        "backup_comment_id": backup_id,
        "approval_comment_id": comment["id"],
        "source_sha": target_sha,
    }


def _eligible(path, env, event, get, *, target_sha, disabled):
    request = authenticate_pair(env, event, get, target_sha=target_sha)
    db_path = owner._original_path(path, env)
    pair._authenticate_candidate(get, target_sha)
    owner._candidate_clean_checkout(target_sha)
    policy = owner._owner_policy(get)
    owner._task_readback(db_path, disabled=disabled)
    return request, db_path, policy


def preflight_only(path, env, event, get, *, target_sha):
    request, path, policy = _eligible(
        path, env, event, get, target_sha=target_sha, disabled=False)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as original:
            original.verify()
            meta = original.meta().copy()
            need(meta["source_sha"] == pair.V41_SOURCE
                 and type(meta["head_seq"]) is int
                 and meta["head_seq"] >= pair.MIN_V41_HEAD
                 and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
                 and original.dual_native_schema()
                 and pair.verify_native_activation(original)
                 and original.ready() is None
                 and not original.actives()
                 and not pair.is_migrated(original)
                 and original.conn.total_changes == 0,
                 "CURRENT_ORIGINAL_OWNER_LEDGER_UNQUALIFIED")
    need(owner._owner_policy(get) == policy, "POLICY_CHANGED_DURING_PREFLIGHT")
    pair._authenticate_candidate(get, target_sha)
    authenticate_pair(env, event, get, target_sha=target_sha)
    return {
        "schema": "forge.f139.hybrid-v41.paired-owner-preflight.v1",
        "run_id": request["run_id"],
        "backup_comment_id": request["backup_comment_id"],
        "approval_comment_id": request["approval_comment_id"],
        "candidate_sha": target_sha,
        "original_head_seq": meta["head_seq"],
        "original_head_sha256": meta["head_hash"],
        "original_owner_mutations": 0,
        "pause_performed": False, "task_resumed": False,
        "source_transition_authorized": False,
        "hybrid_admission": False, "scientific_first_use": False,
    }


def backup_only(path, env, event, get, *, target_sha):
    request, path, policy = _eligible(
        path, env, event, get, target_sha=target_sha, disabled=True)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as original:
            before = original.meta().copy()
            receipt = bundle.stage_complete_cold_bundle(
                original, get, target_sha=target_sha, run_id=request["run_id"])
            need(original.meta() == before and original.conn.total_changes == 0
                 and receipt["original_head_seq"] == before["head_seq"]
                 and receipt["original_head_sha256"] == before["head_hash"]
                 and receipt["independent_detached_restore_verified"] is True
                 and receipt["provider_archives_bytes_verified"] is True
                 and receipt["generation_binary_bytes_verified"] is True
                 and receipt["source_transition_authorized"] is False
                 and receipt["hybrid_admission"] is False
                 and receipt["scientific_first_use"] is False,
                 "INDEPENDENT_RESTORE_OR_OWNER_DRIFT")
    owner._task_readback(path, disabled=True)
    need(owner._owner_policy(get) == policy, "POLICY_CHANGED_DURING_BACKUP")
    pair._authenticate_candidate(get, target_sha)
    authenticate_pair(env, event, get, target_sha=target_sha)
    return {
        "schema": "forge.f139.hybrid-v41.paired-owner-backup-only.v1",
        "run_id": request["run_id"],
        "backup_comment_id": request["backup_comment_id"],
        "approval_comment_id": request["approval_comment_id"],
        "candidate_sha": target_sha,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "manifest_sha256": receipt["manifest_sha256"],
        "independent_detached_restore_verified": True,
        "provider_archives_bytes_verified": True,
        "generation_binary_bytes_verified": True,
        "original_owner_mutations": 0, "new_dispatches": 0,
        "task_resumed": False, "source_transition_authorized": False,
        "hybrid_admission": False, "scientific_first_use": False,
    }


def main(argv=None, *, env=None, event=None, get=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    values = dict(os.environ if env is None else env)
    need(os.name == "nt", "ORIGINAL_WINDOWS_ONLY")
    if event is None:
        file = values.get("GITHUB_EVENT_PATH")
        need(type(file) is str and Path(file).is_file(),
             "OWNER_EVENT_FILE_MISSING")
        event = json.loads(Path(file).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
    get = GitHub().native_repo_get if get is None else get
    result = (preflight_only(args.db, values, event, get,
                             target_sha=args.target)
              if args.preflight_only else
              backup_only(args.db, values, event, get,
                          target_sha=args.target))
    prefix = ("F139_HYBRID_V41_PAIRED_PREFLIGHT=" if args.preflight_only
              else "F139_HYBRID_V41_PAIRED_BACKUP_ONLY=")
    print(prefix + canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
