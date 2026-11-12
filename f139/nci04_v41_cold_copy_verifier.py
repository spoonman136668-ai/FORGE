"""V41 original-owner cold-copy integrity proof: read-only, source-only.

An externally authorized original owner produces the SQLite backup and copied
custody material. This verifier reads them, but never constructs or mutates
a backup, owner task, source transition, owner policy, ref, or worker action.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
from pathlib import Path
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v38_original_owner_transition_cli import rollback_view
from f139.nci04_v32_original_owner_transition_cli import (
    copy_provider_archives, copy_generation_executable)
from f139.nci04_v41_recovery_preflight import (
    RecoveryPreflightDenied, FROM, inspect_original, need)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_BACKUP_BYTES = 1_000_000_000


def verify_cold_copy(original: Database, backup: Path, get, *, target: str,
                     run_id: int, expected_backup_sha256: str) -> dict:
    """Authenticate actual unchanged original/cold-copy state under owner lock.

    The original owner must already be quiesced, and must hold its real kernel
    lease before opening the original with Database.open_readonly. This proof
    is not an approval or an executable migration plan.
    """
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(original.filename.with_suffix(".lock")),
         "ORIGINAL_MUTEX_READONLY_REQUIRED")
    need(type(run_id) is int and run_id > 0
         and type(expected_backup_sha256) is str
         and _SHA256.fullmatch(expected_backup_sha256) is not None,
         "RUN_OR_BACKUP_DIGEST_INVALID")
    origin = Path(original.filename)
    backup = Path(backup)
    canonical_backup = origin.parent / ("f139-v41-before-" + str(run_id)) / "state.sqlite"
    # Database.open_readonly resolves the original path. Windows temp roots
    # can have different but equivalent lexical spellings; compare resolved
    # identity, while still requiring the exact run folder/name and refusing
    # filesystem links/junctions before reading any backup bytes.
    need(origin.is_absolute() and origin.is_file() and not origin.is_symlink()
         and backup.is_absolute() and backup.name == "state.sqlite"
         and backup.parent.name == "f139-v41-before-" + str(run_id)
         and backup.parent.parent.resolve() == origin.parent.resolve()
         and backup.resolve() == canonical_backup.resolve()
         and backup.resolve() != origin.resolve()
         and backup.is_file() and not backup.is_symlink()
         and backup.parent.is_dir() and not backup.parent.is_symlink()
         and not getattr(backup.parent, "is_junction", lambda: False)()
         and not origin.parent.is_symlink()
         and 0 < backup.stat().st_size <= MAX_BACKUP_BYTES,
         "CANONICAL_COLD_BACKUP_REQUIRED")
    before_changes = original.conn.total_changes
    historical = inspect_original(original, get, target=target)
    before = original.meta()
    need(historical["installed_source_sha"] == FROM
         and historical["head_seq"] == before["head_seq"]
         and historical["head_sha256"] == before["head_hash"]
         and historical["protected_target_sha"] == target
         and historical["source_transition_authorized"] is False
         and historical["scientific_first_use"] is False,
         "ORIGINAL_PREFLIGHT_NOT_AUTHENTIC")
    sha = hashlib.sha256()
    with backup.open("rb") as data:
        for chunk in iter(lambda: data.read(1024 * 1024), b""):
            sha.update(chunk)
    need(sha.hexdigest() == expected_backup_sha256,
         "ORIGINAL_BACKUP_BYTES_DRIFT")
    with closing(Database.open_readonly(backup)) as cold:
        need(getattr(cold, "_readonly_opened", False) is True
             and cold.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
             "COLD_QUERY_ONLY_REQUIRED")
        cold.verify()
        need(cold.meta() == before, "COLD_EVENT_HEAD_DRIFT")
        original_view = rollback_view(original.conn)
        cold_view = rollback_view(cold.conn)
        need(original_view == cold_view, "COLD_ALL_TABLE_LOGICAL_DRIFT")
        need(cold.conn.total_changes == 0,
             "COLD_COPY_WAS_MUTATED")
    # Reuse actual owner backup-custody readers. copy_files=False cannot write.
    archives = copy_provider_archives(original, backup.parent, copy_files=False)
    generation = copy_generation_executable(original, backup.parent, copy_files=False)
    need(type(archives) is dict and type(generation) is dict
         and len(archives) > 0 and len(generation) > 0,
         "ORIGINAL_ARCHIVE_OR_BINARY_MISSING")
    need(original.meta() == before and original.conn.total_changes == before_changes
         and before_changes == 0, "ORIGINAL_CHANGED_DURING_BACKUP_READ")
    return {
        "schema": "forge.f139.v41.original-owner-cold-copy-readonly.v1",
        "source_sha": FROM,
        "candidate_sha": target,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "backup_sha256": expected_backup_sha256,
        "logical_all_tables_sha256": digest(canonical(original_view)),
        "provider_archives_manifest_sha256": digest(canonical(archives)),
        "generation_binary_manifest_sha256": digest(canonical(generation)),
        "preserved_verified_tasks": historical["terminal_verified"],
        "preserved_quarantined_tasks": historical["terminal_quarantined"],
        "original_owner_mutations": 0,
        "source_transition_authorized": False,
        "new_dispatches": 0,
        "scientific_first_use": False,
        "hybrid_admission": False,
    }
