"""Native V41 post-COMMIT HOLD witness; READ ONLY, NO ACTIVATION.

This checks the genuine original Windows SQLite after the atomic two-event
commit, while the old original task remains disabled. It never retargets or
enables that task, changes policy, restores an old DB, reissues #1715, or
grants scientific first use. A later separate owner release route must
independently qualify activation and native post-install acceptance.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import sys

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_native_original_commit as commit
from f139 import nci04_v41_native_preinstall_profile as native
from f139 import nci04_v41_pending_escrow as escrow
from f139 import nci04_v41_source_transition as source

SCHEMA = "forge.f139.v41.native-postcommit-held-readonly.v1"


class V41PostcommitDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise V41PostcommitDenied("F139_V41_POSTCOMMIT_" + code)


def verify_pair_readonly(db, receipt):
    """Verify exact previously committed pair, not just meta head numbers."""
    need(type(db) is Database and getattr(db, "_readonly_opened", False)
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_LOCKED_QUERY_ONLY_REQUIRED")
    need(type(receipt) is dict and receipt.get("schema") == commit.RECEIPT
         and receipt.get("original_source_sha") == source.FROM_V40
         and type(receipt.get("target_source_sha")) is str
         and source.HEX40.fullmatch(receipt["target_source_sha"])
         and receipt["target_source_sha"] != source.FROM_V40
         and receipt.get("original_sqlite_committed") is True
         and receipt.get("owner_task_still_disabled") is True
         and receipt.get("policy_activated") is False
         and receipt.get("native_task_retargeted") is False
         and receipt.get("owner_execution_accepted") is False
         and receipt.get("scientific_first_use") is False
         and receipt.get("hybrid_admission") is False
         and receipt.get("new_dispatches") == 0
         and type(receipt.get("original_head_seq")) is int
         and receipt["original_head_seq"] >= escrow.OBSERVED_SEQ
         and type(receipt.get("committed_head_seq")) is int
         and receipt["committed_head_seq"] ==
             receipt["original_head_seq"] + 2
         and all(type(receipt.get(k)) is str
                 and source.HEX64.fullmatch(receipt[k]) for k in (
                     "committed_head_sha256", "escrow_event_sha256",
                     "sealed_manifest_sha256"))
         and all(type(receipt.get(k)) is int and receipt[k] > 0 for k in (
             "owner_install_comment_id", "source_event_owner_approval_id",
             "release_pr_number")),
         "NON_AUTHORIZING_ORIGINAL_COMMIT_RECEIPT_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == receipt["target_source_sha"]
         and meta["head_seq"] == receipt["committed_head_seq"]
         and meta["head_hash"] == receipt["committed_head_sha256"]
         and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1
         and db.ready() is None and not db.actives(),
         "EXACT_ORIGINAL_COMMITTED_HEAD_OR_IDLE_DRIFT")
    rows = db.conn.execute(
        "SELECT seq,kind,sha,prior_sha,payload FROM events "
        "WHERE seq IN (?,?) ORDER BY seq",
        (receipt["original_head_seq"]+1,
         receipt["original_head_seq"]+2)).fetchall()
    need(len(rows) == 2 and rows[0]["seq"]+1 == rows[1]["seq"]
         and rows[0]["kind"] == escrow.KIND
         and rows[1]["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and rows[0]["sha"] == receipt["escrow_event_sha256"]
         and rows[1]["sha"] == receipt["committed_head_sha256"]
         and rows[1]["prior_sha"] == rows[0]["sha"]
         and escrow.audit_committed_escrow(db) ==
             "PAIRED_V41_TRANSITION",
         "MISSING_MISMATCHED_OR_REPLAYED_EVENT_PAIR")
    try:
        pending = json.loads(rows[0]["payload"], object_pairs_hook=decode_unique)
        transition = json.loads(rows[1]["payload"],
                                object_pairs_hook=decode_unique)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise V41PostcommitDenied(
            "F139_V41_POSTCOMMIT_NONCANONICAL_EVENT_JSON") from exc
    need(canonical(pending).decode("ascii") == rows[0]["payload"]
         and canonical(transition).decode("ascii") == rows[1]["payload"]
         and pending.get("issue_number") == 1715
         and pending.get("issue_id") == 6333201763
         and pending.get("owner_comment_id") ==
             receipt["source_event_owner_approval_id"]
         and pending.get("reissue_authorized") is False
         and pending.get("scientific_first_use") is False
         and transition.get("owner_event_id") ==
             receipt["source_event_owner_approval_id"]
         and transition.get("to_source_sha") ==
             receipt["target_source_sha"]
         and transition.get("pending_1715_escrow_sha256") ==
             receipt["escrow_event_sha256"]
         and transition.get("new_dispatches") == 0
         and transition.get("scientific_first_use") is False
         and transition.get("hybrid_admission") is False
         and db.conn.execute(
             "SELECT COUNT(*) FROM events WHERE kind=?",
             (escrow.KIND,)).fetchone()[0] == 1
         and db.conn.execute(
             "SELECT COUNT(*) FROM tasks WHERE ticket=?",
             (pending["ticket"],)).fetchone()[0] == 0,
         "ESCROW_1715_OR_TRANSITION_AUTHORITY_DRIFT")
    return {
        "schema": SCHEMA,
        "source_sha": receipt["target_source_sha"],
        "original_head_seq": receipt["original_head_seq"],
        "committed_head_seq": meta["head_seq"],
        "committed_head_sha256": meta["head_hash"],
        "escrow_event_sha256": rows[0]["sha"],
        "pending_1715_issue_id": pending["issue_id"],
        "pending_1715_body_sha256": pending["issue_body_sha256"],
        "pending_1715_unadmitted": True,
        "original_sqlite_cold_verified": True,
        "original_owner_task_disabled": True,
        "original_owner_mutations": 0,
        "source_transition_authorized": False,
        "postinstall_accepted": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_dispatches": 0,
    }


def inspect_original_postcommit_hold(db_path, candidate_root, *,
                                     receipt, api):
    """Genuine native readback; only qualified Windows owner may enter."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub
         and isinstance(db_path, Path)
         and isinstance(candidate_root, Path)
         and db_path.is_absolute() and db_path.is_file()
         and not db_path.is_symlink()
         and db_path.name == "state.sqlite"
         and type(receipt) is dict,
         "NATIVE_ORIGINAL_HOST_ONLY")
    target = receipt.get("target_source_sha")
    need(type(target) is str
         and source.HEX40.fullmatch(target)
         and native.verify_original_task_disabled_for_staged_candidate(
             db_path, candidate_root, target) is True,
         "DISABLED_ORIGINAL_TASK_AND_CANDIDATE_REQUIRED")
    get = api.native_repo_get
    need(api.protected_main() == target,
         "PROTECTED_MAIN_MOVED")
    policy = get("repos/" + commit.REPO + "/issues/807")
    try:
        p = json.loads(policy["body"], object_pairs_hook=decode_unique)
    except (KeyError, ValueError, TypeError, UnicodeError) as exc:
        raise V41PostcommitDenied("F139_V41_POSTCOMMIT_POLICY_JSON") from exc
    need(type(p) is dict
         and p.get("schema") ==
             "forge.f139.native-autonomy-feed-owner-policy.v1"
         and p.get("source_sha") == source.FROM_V40
         and p.get("enabled") is True
         and p.get("lanes") == ["Wingless", "Yggdrasil"]
         and p.get("scientific_first_use") is False
         and p.get("paid_model_calls") == 0,
         "OLD_POLICY_STILL_REQUIRED_BEFORE_ACTIVATION")
    # Preserve the existing native Yggdrasil proposal; this is an audit of
    # its source-bound evidence, never a dispatch or postcommit reissue.
    issue_route = "repos/" + commit.REPO + "/issues/1715"
    issue = get(issue_route)
    need(type(issue) is dict and issue.get("number") == 1715
         and issue.get("id") == 6333201763
         and issue.get("state") == "open"
         and not issue.get("pull_request")
         and issue.get("user", {}).get("login") == commit.OWNER
         and issue.get("author_association") == "OWNER",
         "PENDING_1715_REMOTE_OWNER_DRIFT")
    with SingleOwner(db_path.with_suffix(".lock")):
        with closing(Database.open_readonly(db_path)) as original:
            before = original.meta().copy()
            changes = original.conn.total_changes
            result = verify_pair_readonly(original, receipt)
            need(original.meta() == before
                 and original.conn.total_changes == changes == 0,
                 "ORIGINAL_CHANGED_DURING_READBACK")
    try:
        issue_doc = json.loads(issue["body"], object_pairs_hook=decode_unique)
    except (KeyError, ValueError, TypeError, UnicodeError) as exc:
        raise V41PostcommitDenied("F139_V41_POSTCOMMIT_PENDING_BODY_JSON") from exc
    need(type(issue_doc) is dict
         and issue_doc.get("source_sha") == source.FROM_V40
         and issue_doc.get("lane") == "Yggdrasil"
         and issue_doc.get("scientific_first_use") is False
         and issue_doc.get("paid_model_calls") == 0
         and digest(canonical(issue_doc)) ==
             result["pending_1715_body_sha256"]
         and api.protected_main() == target
         and get("repos/" + commit.REPO + "/issues/807") == policy
         and get(issue_route) == issue
         and native.verify_original_task_disabled_for_staged_candidate(
             db_path, candidate_root, target) is True,
         "TASK_SOURCE_POLICY_OR_PENDING_DRIFT_AFTER_READ")
    return result
