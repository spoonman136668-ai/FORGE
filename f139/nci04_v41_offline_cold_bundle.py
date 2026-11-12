"""Inert V41 offline cold-bundle builder and independent disposable restore.

No CLI, release, task control, owner-policy update, escrow, or first-use path.
An authenticated maintenance caller must separately prove original task quiescence
and exclusive ownership before invoking this source-only library.
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import tempfile

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v38_original_owner_transition_cli import rollback_view
from f139 import nci04_v41_cold_copy_verifier as cold

SCHEMA = "forge.f139.v41.offline-cold-bundle-dev.v1"
_SHA40 = re.compile(r"[a-f0-9]{40}\Z")
_SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class V41BundleDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise V41BundleDenied("F139_V41_COLD_BUNDLE_" + code)


def _manifest_entry(folder: Path, relative: str, expected: str):
    need(type(relative) is str and type(expected) is str
         and _SHA64.fullmatch(expected) is not None
         and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,399}", relative) is not None
         and all(part not in ("", ".", "..") for part in relative.split("/")),
         "MANIFEST_IDENTITY_INVALID")
    path = folder.joinpath(*relative.split("/"))
    need(path.is_file() and not path.is_symlink()
         and path.resolve().is_relative_to(folder.resolve())
         and all(not p.is_symlink() for p in path.parents if p != folder
                 and p.is_relative_to(folder)),
         "MANIFEST_PATH_INVALID")
    need(cold._hash_standalone_sqlite(path) == expected, "MANIFEST_BYTES_CHANGED")


def _disposable_restore(original: Database, backup: Path, expected: str, before: dict,
                        logical_digest: str) -> str:
    """Exercise real SQLite backup-to-fresh-database recovery, never original."""
    with tempfile.TemporaryDirectory(prefix="v41-restore-", dir=backup.parent) as scratch:
        restored = Path(scratch) / "restored.sqlite"
        with cold._hashed_private_sqlite_snapshot(backup, expected) as immutable:
            with closing(sqlite3.connect(str(restored), isolation_level=None)) as dst:
                immutable.conn.backup(dst)
        cold._require_standalone_sqlite(restored)
        with closing(cold._open_immutable_hashed_backup(restored)) as reopened:
            reopened.verify()
            need(reopened.meta() == before
                 and digest(canonical(rollback_view(reopened.conn))) == logical_digest,
                 "RESTORED_HISTORY_OR_TABLES_DRIFT")
        cold._require_standalone_sqlite(restored)
        restored_digest = cold._hash_standalone_sqlite(restored)
        need(_SHA64.fullmatch(restored_digest) is not None
             and original.meta() == before and original.conn.total_changes == 0,
             "ORIGINAL_CHANGED_DURING_RESTORE")
        return restored_digest


def stage_offline_cold_bundle(original: Database, get, *, target: str, run_id: int) -> dict:
    """Create a new never-overwritten bundle from a separately quiesced owner.

    The original connection is query_only and the original owner mutex must be
    held. This does not itself attest that a Windows task is stopped, nor does
    its return value authorize any source transition, restart or issue reissue.
    """
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(original.filename.with_suffix(".lock"))
         and type(run_id) is int and run_id > 0
         and type(target) is str and _SHA40.fullmatch(target) is not None
         and callable(get), "LOCKED_QUERY_ONLY_AND_EXACT_INPUT_REQUIRED")
    origin = Path(original.filename)
    need(origin.is_absolute() and origin.name == "state.sqlite"
         and origin.is_file() and not origin.is_symlink()
         and origin.parent.is_dir() and not origin.parent.is_symlink(),
         "ORIGINAL_DATABASE_IDENTITY")
    original.verify()
    before = original.meta().copy()
    need(original.conn.total_changes == 0, "ORIGINAL_CONNECTION_DIRTY")
    history = cold.original_ledger_preflight(original)
    remote = cold.source_preflight(get, target)
    need(before["source_sha"] == cold.FROM
         and history["source_sha"] == cold.FROM
         and history["original_head_seq"] == before["head_seq"]
         and history["original_head_sha256"] == before["head_hash"]
         and history["source_transition_authorized"] is False
         and history["scientific_first_use"] is False
         and remote["original_source_sha"] == cold.FROM
         and remote["target_source_sha"] == target
         and remote["unique_eligible_issues"] == 200
         and remote["source_transition_authorized"] is False
         and remote["scientific_first_use"] is False,
         "FROZEN_LEDGER_OR_REMOTE_SOURCE_DRIFT")

    folder = origin.parent / ("f139-v41-before-" + str(run_id))
    # Exclusive creation makes partial/failed attempts non-replayable under
    # the same run identifier; no previous backup or receipt is overwritten.
    need(not folder.exists() and not folder.is_symlink(), "RUN_ALREADY_STAGED")
    folder.mkdir(mode=0o700, exist_ok=False)
    backup = folder / "state.sqlite"
    # SQLite's online backup API includes committed WAL state, unlike copying
    # the potentially incomplete source main-file bytes with shutil.copyfile.
    with closing(sqlite3.connect(str(backup), isolation_level=None)) as dst:
        original.conn.backup(dst)
    cold._require_standalone_sqlite(backup)
    need(backup.is_file() and not backup.is_symlink()
         and 0 < backup.stat().st_size <= cold.MAX_BACKUP_BYTES,
         "NONSTANDALONE_OR_OVERSIZE_BACKUP")

    archives = cold.copy_provider_archives(original, folder, copy_files=True)
    executable = cold.copy_generation_executable(original, folder, copy_files=True)
    need(type(archives) is dict and len(archives) > 0
         and type(executable) is dict and len(executable) > 0
         and not (set(archives) & set(executable)),
         "PROVIDER_OR_EXECUTABLE_CUSTODY_MISSING")

    backup_sha = cold._hash_standalone_sqlite(backup)
    receipt = cold.verify_cold_copy(original, backup, get, target=target,
                                    run_id=run_id,
                                    expected_backup_sha256=backup_sha)
    expected_files = {"state.sqlite": backup_sha, **archives, **executable}
    need(len(expected_files) == len(archives) + len(executable) + 1,
         "DUPLICATE_BUNDLE_PATH")
    for relative, expected in expected_files.items():
        _manifest_entry(folder, relative, expected)
    restore_sha = _disposable_restore(
        original, backup, backup_sha, before, receipt["logical_all_tables_sha256"])
    cold._require_standalone_sqlite(backup)
    need(cold._hash_standalone_sqlite(backup) == backup_sha
         and original.meta() == before and original.conn.total_changes == 0,
         "FINAL_ORIGINAL_OR_BACKUP_DRIFT")
    # Receipt written last. A partial staging directory has no sealed manifest
    # and must never be mistaken for an eligible recovery artifact.
    manifest = {
        "schema": SCHEMA, "original_source_sha": cold.FROM,
        "target_source_sha": target, "run_id": run_id,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "files_sha256": dict(sorted(expected_files.items())),
        "restore_sqlite_sha256": restore_sha,
        "logical_all_tables_sha256": receipt["logical_all_tables_sha256"],
        "provider_archives_manifest_sha256": receipt["provider_archives_manifest_sha256"],
        "generation_binary_manifest_sha256": receipt["generation_binary_manifest_sha256"],
        "owner_quiescence_verified": False,
        "release_qualified": False, "source_transition_authorized": False,
        "reissue_authorized": False, "scientific_first_use": False,
        "hybrid_admission": False, "new_dispatches": 0, "owner_mutations": 0,
    }
    encoded = canonical(manifest)
    with (folder / "manifest.sha256.json").open("xb") as handle:
        handle.write(encoded)
        handle.flush()
    need(json.loads((folder / "manifest.sha256.json").read_bytes()) == manifest,
         "MANIFEST_COLD_READBACK_FAILED")
    return dict(manifest, manifest_sha256=digest(encoded))
