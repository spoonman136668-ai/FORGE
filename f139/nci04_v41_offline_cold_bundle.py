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


def verify_sealed_bundle_offline(folder: Path, *, expected_manifest_sha256: str,
                                 target: str, run_id: int,
                                 expected_head_seq: int,
                                 expected_head_sha256: str) -> dict:
    """Independently restore a PINNED bundle without original owner or network.

    The expected root digest and event-head identity must arrive through an
    independently authenticated owner receipt. Passing is data-recovery proof,
    NEVER quiescence, signed release, dispatch, or migration authority.
    """
    import os

    need(type(expected_manifest_sha256) is str
         and _SHA64.fullmatch(expected_manifest_sha256) is not None
         and type(expected_head_sha256) is str
         and _SHA64.fullmatch(expected_head_sha256) is not None
         and type(target) is str and _SHA40.fullmatch(target) is not None
         and type(run_id) is int and run_id > 0
         and type(expected_head_seq) is int and expected_head_seq >= 0,
         "INDEPENDENT_ANCHORS_REQUIRED")
    folder = Path(folder)
    need(folder.is_absolute() and folder.is_dir()
         and folder.name == "f139-v41-before-" + str(run_id)
         and all(not path.is_symlink()
                 and not getattr(path, "is_junction", lambda: False)()
                 for path in (folder, *folder.parents)),
         "CANONICAL_NONLINK_BUNDLE_REQUIRED")
    sealed = folder / "manifest.sha256.json"
    need(sealed.is_file() and not sealed.is_symlink()
         and 0 < sealed.stat().st_size <= 1_000_000,
         "SEALED_MANIFEST_REQUIRED")
    raw = sealed.read_bytes()
    need(digest(raw) == expected_manifest_sha256,
         "INDEPENDENT_MANIFEST_DIGEST_DRIFT")
    try:
        doc = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise V41BundleDenied("F139_V41_COLD_BUNDLE_MANIFEST_UNREADABLE") from exc
    required = {
        "schema", "original_source_sha", "target_source_sha", "run_id",
        "original_head_seq", "original_head_sha256", "files_sha256",
        "restore_sqlite_sha256", "logical_all_tables_sha256",
        "provider_archives_manifest_sha256", "generation_binary_manifest_sha256",
        "owner_quiescence_verified", "release_qualified",
        "source_transition_authorized", "reissue_authorized",
        "scientific_first_use", "hybrid_admission", "new_dispatches",
        "owner_mutations",
    }
    need(type(doc) is dict and set(doc) == required and canonical(doc) == raw
         and doc["schema"] == SCHEMA
         and doc["original_source_sha"] == cold.FROM
         and doc["target_source_sha"] == target
         and type(doc["run_id"]) is int and doc["run_id"] == run_id
         and type(doc["original_head_seq"]) is int
         and doc["original_head_seq"] == expected_head_seq
         and doc["original_head_sha256"] == expected_head_sha256
         and all(type(doc[k]) is str and _SHA64.fullmatch(doc[k])
                 for k in ("restore_sqlite_sha256",
                           "logical_all_tables_sha256",
                           "provider_archives_manifest_sha256",
                           "generation_binary_manifest_sha256"))
         and all(doc[k] is False for k in (
             "owner_quiescence_verified", "release_qualified",
             "source_transition_authorized", "reissue_authorized",
             "scientific_first_use", "hybrid_admission"))
         and type(doc["new_dispatches"]) is int and doc["new_dispatches"] == 0
         and type(doc["owner_mutations"]) is int and doc["owner_mutations"] == 0,
         "FROZEN_MANIFEST_OR_AUTHORITY_FIELDS_DRIFT")
    files = doc["files_sha256"]
    need(type(files) is dict and 3 <= len(files) <= 10000
         and "state.sqlite" in files,
         "BUNDLE_FILE_SET_INVALID")
    archives = {k: v for k, v in files.items()
                if type(k) is str and k.startswith("provider-custody/")}
    binaries = {k: v for k, v in files.items()
                if type(k) is str and k.startswith("prior-generation-custody/")}
    need(bool(archives) and len(binaries) == 1
         and set(files) == {"state.sqlite", *archives, *binaries}
         and digest(canonical(archives)) ==
             doc["provider_archives_manifest_sha256"]
         and digest(canonical(binaries)) ==
             doc["generation_binary_manifest_sha256"],
         "CUSTODY_MANIFEST_DIGEST_OR_SCOPE")
    # Reject unlisted files, junctions and symlinks (including file/dir aliases).
    def actual_file_set():
        observed = set()
        for parent, dirs, names in os.walk(folder, followlinks=False):
            for name in (*dirs, *names):
                entry = Path(parent) / name
                need(not entry.is_symlink()
                     and not getattr(entry, "is_junction", lambda: False)(),
                     "UNTRUSTED_BUNDLE_LINK")
                if name in names:
                    need(entry.is_file(), "UNEXPECTED_FILE_TYPE")
                    observed.add(entry.relative_to(folder).as_posix())
        return observed

    discovered = actual_file_set()
    need(discovered == set(files) | {"manifest.sha256.json"},
         "UNLISTED_OR_MISSING_BUNDLE_FILE")
    for relative, expected in files.items():
        _manifest_entry(folder, relative, expected)

    # Verify the archive-internal manifests, not just aggregate file hashes.
    packages = {}
    for relative in archives:
        parts = relative.split("/")
        need(len(parts) == 4 and parts[0] == "provider-custody"
             and re.fullmatch(r"f139-nci04-[a-z0-9-]{1,180}", parts[1])
             and parts[2].isdigit() and int(parts[2]) > 0
             and parts[3] in ("manifest.json", "ubuntu-latest.zip",
                               "windows-latest.zip"),
             "PROVIDER_ARCHIVE_SCOPE")
        packages.setdefault(tuple(parts[:3]), set()).add(parts[3])
        path = folder.joinpath(*parts)
        need(path.stat().st_size <= (16384 if parts[3] == "manifest.json"
                                    else 2_000_000),
             "PROVIDER_ARCHIVE_OVERSIZE")
    for prefix, names in packages.items():
        need(names == {"manifest.json", "ubuntu-latest.zip",
                        "windows-latest.zip"}, "INCOMPLETE_PROVIDER_ARCHIVE")
        source = folder.joinpath(*prefix, "manifest.json")
        try:
            meta = json.loads(source.read_bytes())
        except (UnicodeError, ValueError) as exc:
            raise V41BundleDenied("F139_V41_COLD_BUNDLE_PROVIDER_MANIFEST_BAD") from exc
        wanted = {platform: archives["/".join((*prefix, platform + ".zip"))]
                  for platform in ("ubuntu-latest", "windows-latest")}
        need(type(meta) is dict and meta.get("ticket") == prefix[1]
             and type(meta.get("run_id")) is int
             and meta["run_id"] == int(prefix[2])
             and meta.get("sha256") == wanted, "PROVIDER_MANIFEST_CONTENT_DRIFT")

    binary_relative = next(iter(binaries))
    binary_parts = binary_relative.split("/")
    need(len(binary_parts) == 3
         and binary_parts[1] == cold.FROM
         and binary_parts[2] == "f139-genenv-source.exe"
         and folder.joinpath(*binary_parts).stat().st_size <= 16_000_000,
         "PRIOR_GENERATION_BINARY_SCOPE")

    backup = folder / "state.sqlite"
    need(0 < backup.stat().st_size <= cold.MAX_BACKUP_BYTES,
         "OFFLINE_SQLITE_SIZE_INVALID")
    cold._require_standalone_sqlite(backup)
    with tempfile.TemporaryDirectory(prefix="f139-v41-independent-restore-") as scratch:
        restored = Path(scratch) / "restored.sqlite"
        with cold._hashed_private_sqlite_snapshot(
                backup, files["state.sqlite"]) as source:
            source.verify()
            meta = source.meta().copy()
            need(meta["source_sha"] == cold.FROM
                 and meta["head_seq"] == expected_head_seq
                 and meta["head_hash"] == expected_head_sha256
                 and digest(canonical(rollback_view(source.conn))) ==
                     doc["logical_all_tables_sha256"],
                 "PINNED_ORIGINAL_HISTORY_DRIFT")
            with closing(sqlite3.connect(str(restored), isolation_level=None)) as dst:
                source.conn.backup(dst)
        cold._require_standalone_sqlite(restored)
        with closing(cold._open_immutable_hashed_backup(restored)) as second:
            second.verify()
            need(second.meta() == meta
                 and second.conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
                 and digest(canonical(rollback_view(second.conn))) ==
                     doc["logical_all_tables_sha256"],
                 "INDEPENDENT_RESTORE_PARITY_FAILURE")
        cold._require_standalone_sqlite(restored)
        second_digest = cold._hash_standalone_sqlite(restored)

    # Re-verify all source bytes at the end, and hold the outer manifest hash.
    for relative, expected in files.items():
        _manifest_entry(folder, relative, expected)
    cold._require_standalone_sqlite(backup)
    need(digest(sealed.read_bytes()) == expected_manifest_sha256
         and actual_file_set() == set(files) | {"manifest.sha256.json"},
         "BUNDLE_CHANGED_DURING_OFFLINE_AUDIT")
    return {
        "schema": "forge.f139.v41.independent-offline-restore-readonly.v1",
        "original_source_sha": cold.FROM,
        "target_source_sha": target, "original_head_seq": expected_head_seq,
        "original_head_sha256": expected_head_sha256,
        "manifest_sha256": expected_manifest_sha256,
        "restored_sqlite_sha256": second_digest,
        "logical_all_tables_sha256": doc["logical_all_tables_sha256"],
        "independent_restore_verified": True,
        "original_owner_host_verified": False,
        "owner_quiescence_verified": False,
        "release_qualified": False,
        "source_transition_authorized": False,
        "reissue_authorized": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_dispatches": 0,
        "owner_mutations": 0,
    }
