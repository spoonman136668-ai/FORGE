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
import json
import os
from pathlib import Path
import sys

from f139.local_controller import GitHub
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_native_original_commit as atomic
from f139 import nci04_v41_native_postcommit_hold as hold
from f139 import nci04_v41_source_transition as source


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
    disposable_copy = data / (
        "f139-v41-live-install-copy-" + env["GITHUB_RUN_ID"] + ".sqlite")
    need(original_db.is_file() and not original_db.is_symlink()
         and binary.is_file() and not binary.is_symlink()
         and not disposable_copy.exists()
         and not disposable_copy.is_symlink(),
         "CREATE_ONLY_ORIGINAL_AND_COPY_REQUIRED")
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


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    options = parser.parse_args(argv)
    result = original_atomic_commit_and_hold(
        options.target, env=dict(os.environ), api=GitHub())
    print("F139_V41_NATIVE_COMMIT_HOLD=" +
          canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
