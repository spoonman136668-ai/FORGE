"""Original-host cold V3 source and signed-history probe. Read-only; no release.

This entry point is for a future, separately authorized original-owner workflow.
It does not stop/start/rebind a task, authenticate SID or DPAPI custody, sign
certificates, authorize a source forward, or dispatch workers. The original
controller lock must already be available and its lock file must exist.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

from f139.local_controller import Database, SingleOwner
from f139.nci04_v3_original_owner_cold_readonly import inspect_original_owner_cold_readonly
from f139.nci04_v3_owner_remote_preflight import GitHubGET, decode_request

OWNER_DIR = "FORGE-F139"
STATUS = "F139_V3_ORIGINAL_COLD_HISTORY"
SCHEMA = "forge.f139.v3-original-host-cold-cli-readonly.v1"


class V3HostColdDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise V3HostColdDenied("F139_V3_HOST_COLD_" + reason)


def _reparse(path: Path) -> bool:
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def inspect_cold_host(encoded: str, *, dbpath: Path, folder: Path,
                      key: str, api=None) -> dict:
    """Only read the existing owner's signed V1 history under its kernel lock.

    No network access or opening of SQLite occurs on malformed input,
    missing/linked owner files, or a missing existing lock.
    """
    request = decode_request(encoded)
    need(isinstance(dbpath, Path) and isinstance(folder, Path)
         and dbpath.is_absolute() and folder.is_absolute()
         and folder == dbpath.parent
         and dbpath.name == "state.sqlite"
         and folder.name == OWNER_DIR
         and type(key) is str and 32 <= len(key) <= 4096,
         "INPUT_OR_OWNER_PATH_INVALID")
    lock = dbpath.with_suffix(".lock")
    need(all(not _reparse(p) for p in (dbpath, folder, folder.parent, lock))
         and dbpath.is_file() and folder.is_dir()
         and lock.is_file() and lock.stat().st_size > 0,
         "OWNER_SOURCE_OR_EXISTING_LOCK_INVALID")

    # Never create the old lock as a surrogate for the original owner.
    with SingleOwner(lock, existing_only=True):
        db = Database.open_readonly(dbpath)
        try:
            before = db.conn.total_changes
            need(getattr(db, "_readonly_opened", False) is True
                 and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
                 and before == 0, "SQLITE_READONLY_REQUIRED")
            proof = inspect_original_owner_cold_readonly(
                db, GitHubGET() if api is None else api, key, folder, **request)
            need(db.conn.total_changes == before
                 and proof.get("remote_evidence") == "VERIFIED_READ_ONLY"
                 and proof.get("signed_v1_cold_history") == "VERIFIED_READ_ONLY"
                 and proof.get("verified_terminal_tasks") == 3
                 and proof.get("source_commit") == request["owner_source_sha"]
                 and proof.get("source_tree") == request["owner_source_tree"]
                 and proof.get("original_windows_sid_and_task") == "NOT_CHECKED"
                 and proof.get("installed_checkout") == "NOT_CHECKED"
                 and proof.get("source_forward_authorized") is False
                 and proof.get("safe_to_disable_task") is False
                 and proof.get("signed_v3_certificate") is False
                 and proof.get("sqlite_mutations") == 0
                 and proof.get("worker_dispatches") == 0
                 and proof.get("scientific_first_use") is False,
                 "UNEXPECTED_CUSTODY_OR_AUTHORITY")
        finally:
            db.close()
    return {
        "schema": SCHEMA,
        "cold_history": "VERIFIED_READ_ONLY",
        "owner_windows_sid_dpapi": "NOT_CHECKED",
        "source_forward_authorized": False,
        "task_mutation_authorized": False,
        "scientific_first_use": False,
    }


def _native_windows() -> bool:
    return sys.platform == "win32"


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        need(len(args) == 1 and _native_windows(), "NATIVE_OWNER_CLI_ONLY")
        profile = os.environ.get("LOCALAPPDATA", "")
        need(bool(profile) and Path(profile).is_absolute(),
             "LOCAL_OWNER_PROFILE_REQUIRED")
        folder = Path(profile) / OWNER_DIR
        report = inspect_cold_host(
            args[0], dbpath=folder / "state.sqlite", folder=folder,
            key=os.environ.get("F139_WORKER_HMAC_KEY", ""))
        need(report["cold_history"] == "VERIFIED_READ_ONLY",
             "COLD_HISTORY_UNVERIFIED")
    except Exception:
        # Fail closed: no path, HMAC, environment, provider response or
        # raw exception goes to stdout/stderr.
        print(STATUS + "=DENIED", file=sys.stderr)
        return 2
    print(STATUS + "=READ_ONLY_PASS")
    print("F139_V3_OWNER_WINDOWS_SID_DPAPI=NOT_CHECKED")
    print("F139_V3_TASK_MUTATION_AUTHORIZED=FALSE")
    print("F139_V3_SCIENTIFIC_FIRST_USE=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
