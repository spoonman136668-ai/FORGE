"""V59 original Windows owner cold-backup parity, source-only/read-only.

An independently authenticated original owner must quiesce its task, hold
the original mutex and create a hash-bound backup and custody adjuncts
before this function is called. This function never constructs, changes or
adopts either database, transitions source or dispatches a worker.
"""
from __future__ import annotations

from pathlib import Path
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v38_original_owner_transition_cli import rollback_view
from f139.nci04_v32_original_owner_transition_cli import (
    copy_generation_executable, copy_provider_archives,
)
from f139 import nci04_v41_cold_copy_verifier as cold
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256, audit_frozen_original_readonly,
)

SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
MIN_RUN = 44518016720


class V59ColdBackupDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise V59ColdBackupDenied("F139_V59_BACKUP_" + code)


def frozen_backup_destination(original: Path, backup: Path,
                              owner_run_id: int) -> Path:
    """Accept only an existing, canonical, single-run original-root backup."""
    need(type(owner_run_id) is int and owner_run_id > MIN_RUN,
         "OWNER_RUN_INVALID")
    need(isinstance(original, Path) and isinstance(backup, Path)
         and original.is_absolute() and backup.is_absolute()
         and original.name == "state.sqlite"
         and original.parent.name == "FORGE-F139"
         and original.is_file() and backup.is_file()
         and not original.is_symlink() and not backup.is_symlink()
         and not original.parent.is_symlink()
         and not backup.parent.is_symlink()
         and not getattr(backup.parent, "is_junction", lambda: False)()
         and not getattr(original.parent, "is_junction", lambda: False)(),
         "ORIGINAL_OR_BACKUP_FILE_INVALID")
    expected = original.parent / (
        "f139-v59-before-" + str(owner_run_id)) / "state.sqlite"
    need(backup.parent.name == "f139-v59-before-" + str(owner_run_id)
         and backup.resolve() == expected.resolve()
         and backup.resolve() != original.resolve()
         and backup.parent.parent.resolve() == original.parent.resolve()
         and 1024 < backup.stat().st_size <= cold.MAX_BACKUP_BYTES,
         "BACKUP_PATH_OR_SIZE_INVALID")
    return backup


def verify_original_cold_backup(
        original: Database, backup: Path, *,
        owner_run_id: int, target: str,
        expected_backup_sha256: str) -> dict:
    """Read-only exact original-vs-private-immutable-cold-copy verification."""
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
         "ORIGINAL_READONLY_REQUIRED")
    need(SingleOwner.held(original.filename.with_suffix(".lock")),
         "ORIGINAL_MUTEX_REQUIRED")
    need(type(target) is str and SHA40.fullmatch(target) is not None
         and target != SOURCE and type(expected_backup_sha256) is str
         and SHA64.fullmatch(expected_backup_sha256) is not None,
         "TARGET_OR_SHA_INVALID")
    path = frozen_backup_destination(
        Path(original.filename), Path(backup), owner_run_id)
    cold._require_standalone_sqlite(path)
    need(cold._hash_standalone_sqlite(path) == expected_backup_sha256,
         "BACKUP_BYTES_DRIFT")
    before_changes = original.conn.total_changes
    before = audit_frozen_original_readonly(original)
    need(before["source_sha"] == SOURCE and before["head_seq"] == HEAD_SEQ
         and before["head_sha256"] == HEAD_SHA256
         and before_changes == 0, "ORIGINAL_PREIMAGE_NOT_FROZEN")
    original_view = rollback_view(original.conn)
    with cold._hashed_private_sqlite_snapshot(
            path, expected_backup_sha256) as detached:
        detached.verify()
        snapshot = audit_frozen_original_readonly(detached)
        need(snapshot == before
             and rollback_view(detached.conn) == original_view
             and detached.conn.total_changes == 0,
             "BACKUP_ALL_TABLE_PARITY_INVALID")
    negative = cold.required_negative_custody(original)
    copied = cold.copy_negative_custody(
        original.filename.parent, path.parent,
        negative, copy_files=False)
    archives = copy_provider_archives(
        original, path.parent, copy_files=False)
    binary = copy_generation_executable(
        original, path.parent, copy_files=False)
    need(type(copied) is dict and type(archives) is dict
         and type(binary) is dict and bool(archives) and bool(binary),
         "COLD_ARCHIVE_OR_EXECUTABLE_CUSTODY_INVALID")
    cold._require_standalone_sqlite(path)
    need(cold._hash_standalone_sqlite(path) == expected_backup_sha256
         and original.conn.total_changes == 0
         and audit_frozen_original_readonly(original) == before
         and rollback_view(original.conn) == original_view,
         "SOURCE_OR_BACKUP_CHANGED_DURING_AUDIT")
    return {
        "schema": "forge.f139.v59.original-cold-backup-readonly.v1",
        "from_source_sha": SOURCE, "to_source_sha": target,
        "original_head_seq": HEAD_SEQ, "original_head_sha256": HEAD_SHA256,
        "backup_sqlite_sha256": expected_backup_sha256,
        "logical_all_tables_sha256": digest(canonical(original_view)),
        "negative_custody_sha256": digest(canonical(copied)),
        "provider_archives_sha256": digest(canonical(archives)),
        "genenv_executable_custody_sha256": digest(canonical(binary)),
        "original_owner_mutations": 0, "backup_mutations": 0,
        "source_transition_authorized": False,
        "worker_dispatched": False, "scientific_first_use": False,
        "new_controller": False, "new_scheduler": False,
        "replay_authorized": False,
    }
