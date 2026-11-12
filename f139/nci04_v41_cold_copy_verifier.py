"""V41 original-owner cold-copy integrity proof: read-only, source-only.

An externally authorized original owner produces the SQLite backup and copied
custody material. This verifier reads them, but never constructs or mutates
a backup, owner task, source transition, owner policy, ref, or worker action.
"""
from __future__ import annotations

from contextlib import closing, contextmanager
import hashlib
from pathlib import Path
import re
import sqlite3
import tempfile

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v38_original_owner_transition_cli import rollback_view
from f139.nci04_v32_original_owner_transition_cli import (
    copy_provider_archives, copy_generation_executable)
from f139.nci04_v41_catalog_recovery_preflight import (
    V41ReadOnlyDenied as RecoveryPreflightDenied,
    OWNER_SOURCE as FROM, original_ledger_preflight, source_preflight, need)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_BACKUP_BYTES = 1_000_000_000


def _require_standalone_sqlite(backup: Path) -> None:
    """The main file digest cannot attest to WAL/journal sidecar contents.

    Deny even an empty or dangling symlink sidecar: restore must succeed
    using ONLY the separately hashed main SQLite file.
    """
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(backup) + suffix)
        need(not sidecar.exists() and not sidecar.is_symlink(),
             "COLD_BACKUP_SQLITE_SIDECAR_PRESENT")


def _hash_standalone_sqlite(backup: Path) -> str:
    value = hashlib.sha256()
    with backup.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _open_immutable_hashed_backup(backup: Path) -> Database:
    """Open ONLY main-file bytes; never create or read WAL/SHM sidecars.

    The original Database.open_readonly uses mode=ro, which on WAL-format
    standalone SQLite may create a -shm sidecar. immutable=1 guarantees the
    audited cold copy is exactly the independently SHA-256-hashed main file.
    This is for an ALREADY frozen backup, never for the live original owner.
    """
    path = backup.resolve()
    conn = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1",
                           uri=True, isolation_level=None, timeout=10)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        need(conn.execute("PRAGMA query_only").fetchone()[0] == 1,
             "IMMUTABLE_BACKUP_NOT_QUERY_ONLY")
        db = object.__new__(Database)
        db.filename = path
        db.conn = conn
        db._readonly_opened = True
        return db
    except BaseException:
        conn.close()
        raise


@contextmanager
def _hashed_private_sqlite_snapshot(backup: Path, expected_sha256: str):
    """Read an owner-independent snapshot whose *own bytes* are hash-bound.

    A main-file pathname can be atomically swapped between two endpoint
    hashes (ABA). Copy and hash bytes in one stream into a private, exclusive
    verifier-owned temp file; open ONLY that file with immutable query_only.
    This scratch copy is not a release backup and is deleted after auditing.
    """
    with tempfile.TemporaryDirectory(prefix="f139-v41-cold-snapshot-") as root:
        private = Path(root) / "state.sqlite"
        digest_stream = hashlib.sha256()
        with backup.open("rb") as original_file, private.open("xb") as owned:
            for chunk in iter(lambda: original_file.read(1024 * 1024), b""):
                digest_stream.update(chunk)
                owned.write(chunk)
            owned.flush()
        need(digest_stream.hexdigest() == expected_sha256,
             "ORIGINAL_BACKUP_BYTES_DRIFT")
        need(_hash_standalone_sqlite(private) == expected_sha256,
             "PRIVATE_SNAPSHOT_BYTES_DRIFT")
        _require_standalone_sqlite(private)
        with closing(_open_immutable_hashed_backup(private)) as cold:
            yield cold
        # The attested database is this immutable private snapshot, not the
        # independently mutable external backup path.
        _require_standalone_sqlite(private)
        need(_hash_standalone_sqlite(private) == expected_sha256,
             "PRIVATE_SNAPSHOT_CHANGED_DURING_VERIFICATION")


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
    historical = original_ledger_preflight(original)
    remote = source_preflight(get, target)
    before = original.meta()
    need(historical["source_sha"] == FROM
         and historical["original_head_seq"] == before["head_seq"]
         and historical["original_head_sha256"] == before["head_hash"]
         and historical["source_transition_authorized"] is False
         and historical["scientific_first_use"] is False
         and remote["original_source_sha"] == FROM
         and remote["target_source_sha"] == target
         and remote["unique_eligible_issues"] == 200
         and remote["source_transition_authorized"] is False
         and remote["scientific_first_use"] is False,
         "ORIGINAL_PREFLIGHT_NOT_AUTHENTIC")
    _require_standalone_sqlite(backup)
    with _hashed_private_sqlite_snapshot(backup, expected_backup_sha256) as cold:
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
    # A sidecar or new main-file bytes appearing DURING the read invalidate
    # the receipt, even if cold.query_only and logical table parity passed.
    _require_standalone_sqlite(backup)
    need(_hash_standalone_sqlite(backup) == expected_backup_sha256,
         "COLD_BACKUP_CHANGED_DURING_VERIFICATION")
    need(original.meta() == before and original.conn.total_changes == before_changes
         and before_changes == 0, "ORIGINAL_CHANGED_DURING_BACKUP_READ")
    return {
        "schema": "forge.f139.v41.original-owner-cold-copy-readonly.v1",
        "source_sha": FROM,
        "candidate_sha": target,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "backup_sha256": expected_backup_sha256,
        "verified_isolated_snapshot_sha256": expected_backup_sha256,
        "logical_all_tables_sha256": digest(canonical(original_view)),
        "provider_archives_manifest_sha256": digest(canonical(archives)),
        "generation_binary_manifest_sha256": digest(canonical(generation)),
        "preserved_verified_tasks": historical["verified_historical_tasks"],
        "preserved_quarantined_tasks": historical["quarantined_historical_tasks"],
        "original_owner_mutations": 0,
        "source_transition_authorized": False,
        "new_dispatches": 0,
        "scientific_first_use": False,
        "hybrid_admission": False,
    }
