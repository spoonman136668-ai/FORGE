"""Guarded original-owner V41 SQLite commit (no task/policy activation route).

Only an authentic first-attempt OWNER issue_comment workflow on the original
Windows host can reach a writer. The source, sealed same-target recovery,
original V40 preimage, candidate executable and independent copied replay
must all match under the genuine original kernel mutex. No new controller or
task is created. The task remains disabled after COMMIT until an independently
qualified source/policy/task activation completes.

No CLI/Actions job invokes this module yet: writing on an actual owner is
FORBIDDEN until the separate native install wrapper and postcommit acceptance
are qualified. The in-process function is already fail-closed on non-Windows
hosts, non-original paths, or absent owner comment custody.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import re
import sys

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_atomic_copy_rehearsal as atomic
from f139 import nci04_v41_catalog_recovery_preflight as source_status
from f139 import nci04_v41_cold_copy_verifier as cold
from f139 import nci04_v41_guarded_release_preflight as release
from f139 import nci04_v41_native_preinstall_profile as native
from f139 import nci04_v41_owner_approval as approval
from f139 import nci04_v41_owner_install_failure_fence as fence
from f139 import nci04_v41_offline_cold_bundle as offline
from f139 import nci04_v41_pending_custody as pending
from f139 import nci04_v41_source_transition as source


REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
POLICY = 807
PREFIX = "F139-V41-LIVE-INSTALL "
SCHEMA = "forge.f139.v41.native-original-install-request.v1"
RECEIPT = "forge.f139.v41.native-original-atomic-commit.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset({
    "schema", "target_source_sha", "release_pr_number",
    "backup_run_id", "sealed_manifest_sha256",
    "owner_approval_comment_id", "original_head_seq",
    "original_head_sha256", "expected_copy_head_sha256",
    "expected_escrow_event_sha256", "binary_sha256",
    "scientific_first_use", "hybrid_admission", "new_controller",
    "new_scheduler", "new_queue", "paid_model_calls",
})


class NativeOriginalCommitDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise NativeOriginalCommitDenied("F139_V41_ORIGINAL_COMMIT_" + code)


def _sha(value, width):
    return type(value) is str and (
        SHA40 if width == 40 else SHA64).fullmatch(value) is not None


def verify_install_dispatch(env, event, get):
    """Authenticate exact, immutable OWNER install intent by two live GETs.

    This receipt is a *request* for the separately qualified original task
    workflow, not a standalone grant to install or conduct experiments.
    """
    required = {
        "GITHUB_REPOSITORY": REPO, "GITHUB_ACTOR": OWNER,
        "GITHUB_EVENT_NAME": "issue_comment", "GITHUB_REF": "refs/heads/main",
        "RUNNER_NAME": "FORGE-CODEX-REMOTE", "GITHUB_RUN_ATTEMPT": "1",
    }
    need(type(env) is dict and type(event) is dict and callable(get)
         and all(env.get(k) == v for k, v in required.items())
         and _sha(env.get("GITHUB_SHA"), 40)
         and type(env.get("GITHUB_RUN_ID")) is str
         and env["GITHUB_RUN_ID"].isdigit()
         and int(env["GITHUB_RUN_ID"]) > 0,
         "ORIGINAL_RUNNER_SOURCE_OR_ATTEMPT_REQUIRED")
    issue, comment, sender = (event.get(k)
                              for k in ("issue", "comment", "sender"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == POLICY
         and "pull_request" not in issue
         and issue.get("user", {}).get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict
         and type(comment.get("id")) is int and comment["id"] > 0
         and comment.get("author_association") == "OWNER"
         and comment.get("user", {}).get("login") == OWNER
         and type(comment.get("body")) is str
         and comment["body"].startswith(PREFIX),
         "OWNER_COMMENT_AND_ORIGINAL_ISSUE_REQUIRED")
    try:
        doc = json.loads(comment["body"][len(PREFIX):],
                         object_pairs_hook=decode_unique)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise NativeOriginalCommitDenied(
            "F139_V41_ORIGINAL_COMMIT_REQUEST_JSON_INVALID") from exc
    need(type(doc) is dict and set(doc) == FIELDS
         and comment["body"] == PREFIX + canonical(doc).decode("ascii")
         and doc.get("schema") == SCHEMA
         and doc.get("target_source_sha") == env["GITHUB_SHA"]
         and doc["target_source_sha"] != source.FROM_V40
         and all(type(doc.get(k)) is int and doc[k] > 0
                 for k in ("release_pr_number", "backup_run_id",
                           "owner_approval_comment_id", "original_head_seq"))
         and all(_sha(doc.get(k), 64) for k in (
             "sealed_manifest_sha256", "original_head_sha256",
             "expected_copy_head_sha256", "expected_escrow_event_sha256",
             "binary_sha256"))
         and all(doc.get(k) is False for k in (
             "scientific_first_use", "hybrid_admission", "new_controller",
             "new_scheduler", "new_queue"))
         and type(doc.get("paid_model_calls")) is int
         and doc["paid_model_calls"] == 0,
         "EXACT_CANONICAL_NONSCIENCE_REQUEST_REQUIRED")
    route = "repos/" + REPO + "/issues/comments/" + str(comment["id"])
    for _ in range(2):
        remote = get(route)
        need(type(remote) is dict
             and remote.get("id") == comment["id"]
             and remote.get("issue_url") ==
                 "https://api.github.com/repos/" + REPO + "/issues/807"
             and remote.get("user", {}).get("login") == OWNER
             and remote.get("author_association") == "OWNER"
             and remote.get("body") == comment["body"]
             and remote.get("created_at") == comment.get("created_at")
             and remote.get("updated_at") == comment.get("updated_at"),
             "OWNER_COMMENT_REMOTE_DRIFT")
    return dict(doc, owner_install_comment_id=comment["id"],
                event_run_id=int(env["GITHUB_RUN_ID"]))


def _read_sealed_manifest(bundle, sha):
    bundle = Path(bundle)
    need(bundle.is_absolute() and bundle.is_dir()
         and not bundle.is_symlink() and
         (bundle / "manifest.sha256.json").is_file(),
         "SEALED_PRIVATE_BUNDLE_MISSING")
    raw = (bundle / "manifest.sha256.json").read_bytes()
    need(digest(raw) == sha, "BACKUP_SEAL_MISMATCH")
    try:
        manifest = json.loads(raw, object_pairs_hook=decode_unique)
    except (TypeError, ValueError, UnicodeError) as exc:
        raise NativeOriginalCommitDenied(
            "F139_V41_ORIGINAL_COMMIT_MANIFEST_JSON") from exc
    need(type(manifest) is dict and canonical(manifest) == raw
         and manifest.get("schema") == offline.SCHEMA
         and type(manifest.get("files_sha256")) is dict
         and _sha(manifest["files_sha256"].get("state.sqlite"), 64),
         "CANONICAL_MANIFEST_AND_SQLITE_REQUIRED")
    return manifest


def original_commit_after_independent_rehearsal(
        db_path, candidate_root, binary_path, copy_path, *,
        env, event, api):
    """Actual original transaction, NEVER task reactivation or policy edit.

    This non-CLI function cannot be entered on GitHub-hosted Windows CI:
    the *original* task SID, old root and disabled state must be genuine.
    The future wrapper must preserve task-disabled state on postcommit errors.
    """
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub
         and isinstance(db_path, Path)
         and isinstance(candidate_root, Path)
         and isinstance(binary_path, Path)
         and isinstance(copy_path, Path),
         "NATIVE_ORIGINAL_ONLY")
    get = api.native_repo_get
    request = verify_install_dispatch(env, event, get)
    target = request["target_source_sha"]
    need(db_path.is_absolute() and db_path.is_file()
         and not db_path.is_symlink()
         and db_path.name == "state.sqlite"
         and copy_path.is_absolute() and copy_path.suffix == ".sqlite"
         and not copy_path.exists() and copy_path.parent.is_dir()
         and binary_path.is_absolute() and binary_path.is_file()
         and not binary_path.is_symlink()
         and binary_path.resolve() ==
             (db_path.parent / "genenv-source" / target /
              "f139-genenv-source.exe").resolve()
         and 0 < binary_path.stat().st_size <= 16_000_000
         and digest(binary_path.read_bytes()) == request["binary_sha256"],
         "ORIGINAL_PATH_COPY_OR_BINARY_CUSTODY")
    need(native.verify_original_task_disabled_for_staged_candidate(
        db_path, candidate_root, target) is True,
        "ORIGINAL_TASK_NOT_DISABLED_OR_OLD_ROOT_DRIFT")
    bundle = db_path.parent / (
        "f139-v41-before-" + str(request["backup_run_id"]))
    manifest = _read_sealed_manifest(bundle, request["sealed_manifest_sha256"])
    need(manifest.get("target_source_sha") == target
         and manifest.get("run_id") == request["backup_run_id"]
         and manifest.get("original_head_seq") == request["original_head_seq"]
         and manifest.get("original_head_sha256") ==
             request["original_head_sha256"],
         "SAME_TARGET_FROZEN_BACKUP_REQUIRED")
    with SingleOwner(db_path.with_suffix(".lock")):
        with closing(Database.open_readonly(db_path)) as original:
            before = original.meta().copy()
            need(before["source_sha"] == source.FROM_V40
                 and before["head_seq"] == request["original_head_seq"]
                 and before["head_hash"] == request["original_head_sha256"]
                 and before["enabled"] == 1
                 and before["legacy_suspended"] == 1,
                 "REAL_ORIGINAL_HEAD_AND_OWNER_DRIFT")
            ledger = source_status.original_ledger_preflight(original)
            cold_receipt = cold.verify_cold_copy(
                original, bundle / "state.sqlite", get, target=target,
                run_id=request["backup_run_id"],
                expected_backup_sha256=manifest["files_sha256"]["state.sqlite"])
            preserved = pending.inspect_never_admitted(original, api)
            owner_intent = approval.verify_owner_comment(
                get, target=target, cold=cold_receipt,
                pending_receipt=preserved,
                comment_id=request["owner_approval_comment_id"])
            readiness = release.qualify_inert_release_preflight(
                get, bundle, target=target,
                release_pr=request["release_pr_number"],
                backup_run_id=request["backup_run_id"],
                sealed_manifest_sha256=request["sealed_manifest_sha256"],
                original_head_seq=request["original_head_seq"],
                original_head_sha256=request["original_head_sha256"],
                cold_receipt=cold_receipt,
                pending_receipt=preserved,
                owner_comment_id=request["owner_approval_comment_id"])
            copied = atomic.rehearse_from_sealed_cold_bundle(
                original, bundle, get, api, target=target,
                run_id=request["backup_run_id"],
                manifest_sha256=request["sealed_manifest_sha256"],
                original_head_seq=request["original_head_seq"],
                original_head_sha256=request["original_head_sha256"],
                owner_comment_id=request["owner_approval_comment_id"],
                copy_path=copy_path, binary_sha=request["binary_sha256"],
                toolchain=source.TOOLCHAIN)
            observed = {
                "schema": "forge.f139.v41.original-locked-readonly-status.v1",
                "installed_source_sha": source.FROM_V40,
                "target_source_sha": target,
                "original_head_seq": ledger["original_head_seq"],
                "original_head_sha256": ledger["original_head_sha256"],
                "verified_historical_tasks": ledger["verified_historical_tasks"],
                "quarantined_historical_tasks":
                    ledger["quarantined_historical_tasks"],
                "pending_issue_number": preserved["issue_number"],
                "sqlite_query_only": True,
                "original_owner_mutations": 0,
                "new_dispatches": 0,
                "reissue_authorized": False,
                "source_transition_authorized": False,
                "source_release_qualified": False,
                "scientific_first_use": False,
                "hybrid_admission": False,
            }
            freeze = fence.inert_handoff(readiness, copied, observed)
            need(freeze["expected_copy_head_seq"] ==
                 request["original_head_seq"] + 2
                 and freeze["expected_copy_head_sha256"] ==
                     request["expected_copy_head_sha256"]
                 and freeze["expected_escrow_sha256"] ==
                     request["expected_escrow_event_sha256"],
                 "EXACT_COPIED_EVENT_PARITY_REQUIRED")
            need(original.meta() == before
                 and original.conn.total_changes == 0,
                 "ORIGINAL_MUTATED_BEFORE_COMMIT")
        # Between RO verification and original COMMIT, retain the one genuine
        # existing owner kernel mutex. No other owner can run concurrently.
        need(native.verify_original_task_disabled_for_staged_candidate(
            db_path, candidate_root, target) is True,
            "ORIGINAL_TASK_MOVED_DURING_REHEARSAL")
        need(verify_install_dispatch(env, event, get) == request,
             "INSTALL_OWNER_COMMENT_CHANGED")
        need(api.protected_main() == target
             and release._remote_source(
                 get, target=target,
                 release_pr=request["release_pr_number"]
             )["tree_sha"] == readiness["source_tree_sha"],
             "QUALIFIED_RELEASE_CHANGED_BEFORE_COMMIT")
        # This is the sole side-effecting SQLite section. Once COMMIT succeeds
        # no old backup may ever replace this ledger, even if later steps fail.
        with closing(Database(db_path)) as original_writer:
            atomic._approval_bound(
                before, cold_receipt, preserved, owner_intent, target)
            need(original_writer.meta() == before
                 and original_writer.conn.total_changes == 0,
                 "ORIGINAL_REOPEN_PREIMAGE_MOVED")
            result = atomic._commit_pair_under_existing_owner_lock(
                original_writer, original_meta=before, target=target,
                binary_sha=request["binary_sha256"],
                toolchain=source.TOOLCHAIN,
                pending_receipt=preserved, owner_intent=owner_intent)
            need(result["copy_head_seq"] == copied["copy_head_seq"]
                 and result["copy_head_sha256"] ==
                     copied["copy_head_sha256"]
                 and result["escrow_event_sha256"] ==
                     copied["escrow_event_sha256"],
                 "POSTCOMMIT_HOLD_FORWARD_REPAIR_PARITY")
        need(native.verify_original_task_disabled_for_staged_candidate(
            db_path, candidate_root, target) is True,
            "POSTCOMMIT_TASK_MUST_REMAIN_DISABLED")
    return {
        "schema": RECEIPT,
        "original_source_sha": source.FROM_V40,
        "target_source_sha": target,
        "original_head_seq": before["head_seq"],
        "committed_head_seq": result["copy_head_seq"],
        "committed_head_sha256": result["copy_head_sha256"],
        "escrow_event_sha256": result["escrow_event_sha256"],
        "sealed_manifest_sha256": request["sealed_manifest_sha256"],
        "release_pr_number": request["release_pr_number"],
        "owner_install_comment_id": request["owner_install_comment_id"],
        "source_event_owner_approval_id":
            request["owner_approval_comment_id"],
        "original_sqlite_committed": True,
        "owner_task_still_disabled": True,
        "policy_activated": False,
        "native_task_retargeted": False,
        "owner_execution_accepted": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_dispatches": 0,
    }
