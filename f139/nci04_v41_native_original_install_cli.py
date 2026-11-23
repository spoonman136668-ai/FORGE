"""Original-owner V41 atomic-commit CLI, intentionally NOT a standalone installer.

A separately qualified Windows owner workflow must first quiesce the existing
V40 task, verify its exact original backup and owner approval, and guarantee
a post-commit policy/task activation or forward-repair HOLD. This CLI performs
ONLY the already-implemented once-only SQLite commit and read-only HOLD check.
It must never resume V40 after the source pair has committed. Nothing in
this module schedules, dispatches research, installs a task, or changes policy.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sys

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_native_original_commit as atomic
from f139 import nci04_v41_native_postcommit_hold as hold
from f139 import nci04_v41_source_transition as source
from f139 import nci04_v41_atomic_copy_rehearsal as rehearsal
from f139 import nci04_v41_guarded_release_preflight as release
from f139 import nci04_v41_candidate_stage as stage


SCHEMA = "forge.f139.v41.native-commit-and-hold-cli.v1"
WRAPPER_MARKER = "F139_V41_ACTIVATION_AND_FORWARD_REPAIR_QUALIFIED_V1"


class OriginalInstallEntryDenied(ValueError):
    pass


def need(valid: bool, code: str) -> None:
    if not valid:
        raise OriginalInstallEntryDenied("F139_V41_INSTALL_ENTRY_" + code)


def _event_file(env: dict) -> dict:
    path = env.get("GITHUB_EVENT_PATH")
    need(type(path) is str and Path(path).is_absolute()
         and Path(path).is_file(), "ORIGINAL_ISSUE_EVENT_FILE_REQUIRED")
    try:
        event = json.loads(Path(path).read_bytes(),
                           object_pairs_hook=decode_unique)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise OriginalInstallEntryDenied(
            "F139_V41_INSTALL_ENTRY_NONCANONICAL_EVENT_JSON") from exc
    need(type(event) is dict, "ORIGINAL_EVENT_SHAPE_REQUIRED")
    return event


def original_atomic_commit_and_hold(target: str, *,
                                     env: dict, api: GitHub) -> dict:
    """One-shot inner phase; caller must already guarantee complete cutover.

    Fail closed before any original write if the separate future wrapper's
    authority marker is absent. The marker is NOT authority by itself:
    owner-authenticated, remote double-read GitHub intent plus Windows task
    and ledger custody remain enforced in the existing atomic primitive.
    """
    need(sys.platform == "win32" and os.name == "nt"
         and type(env) is dict and type(api) is GitHub
         and type(target) is str
         and source.HEX40.fullmatch(target) is not None,
         "NATIVE_WINDOWS_EXACT_SOURCE_REQUIRED")
    need(env.get("F139_V41_INSTALL_WRAPPER")
         == WRAPPER_MARKER
         and env.get("GITHUB_SHA") == target
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE",
         "COMPLETE_QUALIFIED_WRAPPER_REQUIRED")
    event = _event_file(env)
    request = atomic.verify_install_dispatch(
        env, event, api.native_repo_get)
    need(request["target_source_sha"] == target
         and request["event_run_id"] == int(env["GITHUB_RUN_ID"]),
         "AUTHENTIC_OWNER_INTENT_REQUIRED")
    appdata = env.get("LOCALAPPDATA")
    need(type(appdata) is str and Path(appdata).is_absolute(),
         "ORIGINAL_PRIVATE_DATA_ROOT_REQUIRED")
    data = Path(appdata) / "FORGE-F139"
    root = data / "release-candidates" / target
    binary = data / "genenv-source" / target / "f139-genenv-source.exe"
    # Module must be executed from the previously staged exact-SHA checkout,
    # not the GitHub Actions scratch checkout or old running V40 tree.
    need(Path(__file__).resolve().parents[1] == root.resolve()
         and root.is_dir() and not root.is_symlink()
         and data.is_dir() and not data.is_symlink(),
         "STAGED_EXACT_SOURCE_NOT_RUNNING")
    original_db = data / "state.sqlite"
    copy_root = data / "isolated-v41-install-rehearsals" / env["GITHUB_RUN_ID"]
    disposable_copy = copy_root / "rehearsal.sqlite"
    need(original_db.is_file() and not original_db.is_symlink()
         and binary.is_file() and not binary.is_symlink()
         and not disposable_copy.exists()
         and not disposable_copy.is_symlink(),
         "CREATE_ONLY_ORIGINAL_AND_COPY_REQUIRED")
    # The already-qualified copy routine strictly forbids a rehearsal in
    # the original data or sealed backup directory. Make a fresh isolated
    # create-only directory; never overwrite or retry a partial rehearsal.
    need(not copy_root.exists() and not copy_root.is_symlink()
         and (not copy_root.parent.exists() or
              (copy_root.parent.is_dir()
               and not copy_root.parent.is_symlink()
               and not getattr(copy_root.parent, "is_junction",
                               lambda: False)())),
         "ISOLATED_REHEARSAL_ALREADY_EXISTS")
    copy_root.mkdir(parents=True, exist_ok=False)
    committed = atomic.original_commit_after_independent_rehearsal(
        original_db, root, binary, disposable_copy,
        env=env, event=event, api=api)
    need(committed.get("schema") == atomic.RECEIPT
         and committed.get("original_sqlite_committed") is True
         and committed.get("owner_task_still_disabled") is True,
         "ATOMIC_COMMIT_RECEIPT_NOT_VERIFIED")
    checked = hold.inspect_original_postcommit_hold(
        original_db, root, receipt=committed, api=api)
    need(checked.get("schema") == hold.SCHEMA
         and checked.get("source_sha") == target
         and checked.get("committed_head_sha256")
             == committed.get("committed_head_sha256")
         and checked.get("original_owner_task_disabled") is True
         and checked.get("postinstall_accepted") is False,
         "COMMITTED_PAIR_READBACK_NOT_VERIFIED")
    return {
        "schema": SCHEMA,
        "target_source_sha": target,
        "commit_receipt": committed,
        "postcommit_hold_receipt": checked,
        "original_owner_task_still_disabled": True,
        "policy_updated": False,
        "task_retargeted": False,
        "live_activation_completed": False,
        "original_database_rollback_authorized": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_dispatches": 0,
    }



COPY_PREFIX = "F139-V41-COPY-REHEARSAL "
COPY_SCHEMA = "forge.f139.v41.owner-copy-rehearsal-request.v1"
COPY_RECEIPT = "forge.f139.v41.original-copy-rehearsal-only.v1"
COPY_FIELDS = frozenset({
    "schema", "target_source_sha", "release_pr_number",
    "backup_run_id", "sealed_manifest_sha256", "owner_approval_comment_id",
    "binary_sha256", "original_head_seq", "original_head_sha256",
    "scientific_first_use", "hybrid_admission", "new_controller",
    "new_scheduler", "new_queue", "paid_model_calls",
})


def original_copy_rehearsal(target: str, *, env: dict, api: GitHub) -> dict:
    """Run only the pre-existing isolated-copied transaction; no owner writes.

    A standalone owner comment authorizes a bounded READ+COPY operation.
    It cannot grant a live install, promotion, scientific first use or reissue.
    """
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub and type(env) is dict
         and type(target) is str
         and source.HEX40.fullmatch(target) is not None
         and all(env.get(k) == v for k, v in {
             "GITHUB_REPOSITORY": "spoonman136668-ai/FORGE",
             "GITHUB_EVENT_NAME": "issue_comment",
             "GITHUB_ACTOR": "spoonman136668-ai",
             "GITHUB_REF": "refs/heads/main",
             "GITHUB_RUN_ATTEMPT": "1",
             "RUNNER_NAME": "FORGE-CODEX-REMOTE",
         }.items())
         and env.get("GITHUB_SHA") == target
         and type(env.get("GITHUB_RUN_ID")) is str
         and env["GITHUB_RUN_ID"].isdigit()
         and int(env["GITHUB_RUN_ID"]) > 0,
         "COPY_REHEARSAL_ORIGINAL_OWNER_EVENT_REQUIRED")
    event = _event_file(env)
    comment, issue, sender = (event.get(k) for k in
                              ("comment", "issue", "sender"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and issue.get("user", {}).get("login") == "spoonman136668-ai"
         and "pull_request" not in issue
         and type(sender) is dict
         and sender.get("login") == "spoonman136668-ai"
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > 0
         and comment.get("author_association") == "OWNER"
         and comment.get("user", {}).get("login") == "spoonman136668-ai"
         and type(comment.get("body")) is str
         and comment["body"].startswith(COPY_PREFIX),
         "COPY_REHEARSAL_OWNER_CREATED_COMMENT_REQUIRED")
    try:
        doc = json.loads(comment["body"][len(COPY_PREFIX):],
                         object_pairs_hook=decode_unique)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise OriginalInstallEntryDenied(
            "F139_V41_COPY_REHEARSAL_CANONICAL_JSON_INVALID") from exc
    need(type(doc) is dict and set(doc) == COPY_FIELDS
         and comment["body"] == COPY_PREFIX + canonical(doc).decode("ascii")
         and doc.get("schema") == COPY_SCHEMA
         and doc.get("target_source_sha") == target
         and all(type(doc.get(k)) is int and doc[k] > 0 for k in
                 ("release_pr_number", "backup_run_id",
                  "owner_approval_comment_id", "original_head_seq"))
         and all(type(doc.get(k)) is str and
                 source.HEX64.fullmatch(doc[k]) is not None for k in
                 ("sealed_manifest_sha256", "binary_sha256",
                  "original_head_sha256"))
         and all(doc.get(k) is False for k in
                 ("scientific_first_use", "hybrid_admission",
                  "new_controller", "new_scheduler", "new_queue"))
         and type(doc.get("paid_model_calls")) is int
         and doc["paid_model_calls"] == 0,
         "COPY_REHEARSAL_EXACT_NONSCIENCE_INPUT_REQUIRED")
    route = ("repos/spoonman136668-ai/FORGE/issues/comments/"
             + str(comment["id"]))
    get = api.native_repo_get
    for _ in range(2):
        remote = get(route)
        need(type(remote) is dict
             and remote.get("id") == comment["id"]
             and remote.get("user", {}).get("login") == "spoonman136668-ai"
             and remote.get("author_association") == "OWNER"
             and remote.get("issue_url") ==
             "https://api.github.com/repos/spoonman136668-ai/FORGE/issues/807"
             and remote.get("body") == comment["body"]
             and remote.get("created_at") == comment.get("created_at")
             and remote.get("updated_at") == comment.get("updated_at"),
             "COPY_REHEARSAL_AUTHENTIC_COMMENT_DRIFT")
    appdata = env.get("LOCALAPPDATA")
    need(type(appdata) is str and Path(appdata).is_absolute(),
         "COPY_REHEARSAL_ORIGINAL_APPDATA")
    data = Path(appdata) / "FORGE-F139"
    db_path = data / "state.sqlite"
    bundle = data / ("f139-v41-before-" + str(doc["backup_run_id"]))
    manifest = bundle / "manifest.sha256.json"
    binary = data / "genenv-source" / target / "f139-genenv-source.exe"
    root = Path(__file__).resolve().parents[1]
    need(type(env.get("GITHUB_WORKSPACE")) is str
         and root == Path(env["GITHUB_WORKSPACE"]).resolve()
         and db_path.is_file() and not db_path.is_symlink()
         and binary.is_file() and not binary.is_symlink()
         and manifest.is_file() and not manifest.is_symlink()
         and digest(binary.read_bytes()) == doc["binary_sha256"]
         and digest(manifest.read_bytes()) == doc["sealed_manifest_sha256"]
         and stage.verify_running_old_task_before_stage(
             db_path, root) is True,
         "COPY_REHEARSAL_TASK_STAGE_OR_MANIFEST_DRIFT")
    first = release._remote_source(get, target=target,
                                   release_pr=doc["release_pr_number"])
    copy_dir = (data / "isolated-v41-copy-rehearsals"
                / env["GITHUB_RUN_ID"])
    need(not copy_dir.exists() and not copy_dir.is_symlink()
         and (not copy_dir.parent.exists() or
              (copy_dir.parent.is_dir()
               and not copy_dir.parent.is_symlink()
               and not getattr(copy_dir.parent, "is_junction",
                               lambda: False)())),
         "COPY_REHEARSAL_CREATE_ONLY_DIRECTORY")
    need(api.protected_main() == target, "COPY_REHEARSAL_MAIN_MOVED")
    # One fresh, disposable copy is permitted. The original SQLite remains
    # query-only while the actual original-owner kernel mutex is held.
    copy_dir.mkdir(parents=True, exist_ok=False)
    with SingleOwner(db_path.with_suffix(".lock")):
        with closing(Database.open_readonly(db_path)) as original:
            before = original.meta().copy()
            need(before["source_sha"] == source.FROM_V40
                 and before["head_seq"] == doc["original_head_seq"]
                 and before["head_hash"] == doc["original_head_sha256"]
                 and original.ready() is None and not original.actives(),
                 "COPY_REHEARSAL_ORIGINAL_HEAD_DRIFT")
            receipt = rehearsal.rehearse_from_sealed_cold_bundle(
                original, bundle, get, api, target=target,
                run_id=doc["backup_run_id"],
                manifest_sha256=doc["sealed_manifest_sha256"],
                original_head_seq=doc["original_head_seq"],
                original_head_sha256=doc["original_head_sha256"],
                owner_comment_id=doc["owner_approval_comment_id"],
                copy_path=copy_dir / "rehearsal.sqlite",
                binary_sha=doc["binary_sha256"],
                toolchain=source.TOOLCHAIN)
            need(original.meta() == before
                 and original.conn.total_changes == 0
                 and receipt.get("original_unchanged") is True
                 and receipt.get("copy_only") is True
                 and receipt.get("source_transition_authorized") is False
                 and receipt.get("scientific_first_use") is False
                 and receipt.get("hybrid_admission") is False
                 and receipt.get("new_dispatches") == 0,
                 "COPY_REHEARSAL_ORIGINAL_CHANGED")
    need(release._remote_source(
             get, target=target,
             release_pr=doc["release_pr_number"]) == first
         and api.protected_main() == target
         and stage.verify_running_old_task_before_stage(
             db_path, root) is True,
         "COPY_REHEARSAL_REMOTE_OR_ORIGINAL_TASK_MOVED")
    return {
        "schema": COPY_RECEIPT,
        "target_source_sha": target,
        "release_pr_number": doc["release_pr_number"],
        "backup_run_id": doc["backup_run_id"],
        "owner_approval_comment_id": doc["owner_approval_comment_id"],
        "rehearsal_run_id": int(env["GITHUB_RUN_ID"]),
        "original_head_seq": doc["original_head_seq"],
        "original_head_sha256": doc["original_head_sha256"],
        "expected_copy_head_sha256": receipt["copy_head_sha256"],
        "expected_escrow_event_sha256": receipt["escrow_event_sha256"],
        "original_sqlite_written": False,
        "original_task_touched": False,
        "original_owner_mutations": 0,
        "copy_only": True,
        "source_transition_authorized": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_dispatches": 0,
    }

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--rehearse-only", action="store_true")
    options = parser.parse_args(argv)
    if options.rehearse_only:
        result = original_copy_rehearsal(
            options.target, env=dict(os.environ), api=GitHub())
        print("F139_V41_COPY_REHEARSAL=" +
              canonical(result).decode("ascii"))
        return 0
    result = original_atomic_commit_and_hold(
        options.target, env=dict(os.environ), api=GitHub())
    print("F139_V41_NATIVE_COMMIT_HOLD=" +
          canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
