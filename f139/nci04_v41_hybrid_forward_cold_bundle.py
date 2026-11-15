"""Source-only full cold backup of the committed V37 original before V38.

This is NOT a workflow, scheduler, policy writer or owner authority. It must
only be called under an independently authorized existing Windows owner hold
and original SingleOwner mutex, after authenticating a NEW target release.
The original V41 backup is preserved as a separate immutable generation;
its provider/negative/binary evidence is copied byte-for-byte after verification.
The new SQLite copy is taken from event #1830, NEVER from old event #1829.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v38_original_owner_transition_cli import rollback_view
from f139 import nci04_v41_cold_copy_verifier as cold
from f139 import nci04_v41_hybrid_cold_bundle as v41_bundle
from f139 import nci04_v41_hybrid_forward_repair as forward

SCHEMA = "forge.f139.v38.hybrid-forward.complete-cold-bundle.v1"
RESTORE_SCHEMA = "forge.f139.v38.hybrid-forward.detached-restore.v1"
FILES = frozenset({
    "schema", "original_source_sha", "candidate_sha", "run_id",
    "original_head_seq", "original_head_sha256",
    "predecessor_backup_run_id", "predecessor_backup_manifest_sha256",
    "files_sha256", "logical_all_tables_sha256",
    "provider_archives_manifest_sha256",
    "generation_binary_manifest_sha256",
    "negative_custody_manifest_sha256",
    "restored_sqlite_sha256",
    "original_owner_mutations", "new_dispatches",
    "owner_quiescence_verified", "source_transition_authorized",
    "owner_policy_modified", "worker_dispatched",
    "hybrid_admission", "scientific_first_use",
})


class ForwardColdDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise ForwardColdDenied("F139_HYBRID_FORWARD_COLD_" + reason)


def _name(run_id):
    need(type(run_id) is int and run_id > 0, "RUN_ID_REQUIRED")
    return "f139-v38-before-" + str(run_id)


def _folder(folder, run_id):
    folder = Path(folder)
    need(folder.is_absolute() and folder.name == _name(run_id)
         and folder.is_dir()
         and all(v41_bundle._nonlink(p) for p in (folder, *folder.parents)),
         "CANONICAL_NONLINK_FOLDER_REQUIRED")
    return folder


def _validate_manifest(manifest, target, run_id):
    need(type(manifest) is dict and set(manifest) == FILES
         and manifest["schema"] == SCHEMA
         and manifest["original_source_sha"] == forward.FROM
         and type(target) is str and forward.HEX40.fullmatch(target) is not None
         and target != forward.FROM
         and manifest["candidate_sha"] == target
         and manifest["run_id"] == run_id
         and type(manifest["original_head_seq"]) is int
         and manifest["original_head_seq"] == forward.V37_SEQ
         and manifest["original_head_sha256"] == forward.V37_HEAD
         and type(manifest["predecessor_backup_run_id"]) is int
         and manifest["predecessor_backup_run_id"] > 0
         and all(type(manifest[k]) is str and
                 v41_bundle.SHA64.fullmatch(manifest[k]) is not None
                 for k in (
                     "predecessor_backup_manifest_sha256",
                     "logical_all_tables_sha256",
                     "provider_archives_manifest_sha256",
                     "generation_binary_manifest_sha256",
                     "negative_custody_manifest_sha256",
                     "restored_sqlite_sha256"))
         and type(manifest["original_owner_mutations"]) is int
         and manifest["original_owner_mutations"] == 0
         and type(manifest["new_dispatches"]) is int
         and manifest["new_dispatches"] == 0
         and all(manifest[key] is False for key in (
             "owner_quiescence_verified", "source_transition_authorized",
             "owner_policy_modified", "worker_dispatched",
             "hybrid_admission", "scientific_first_use")),
         "MANIFEST_OR_AUTHORITY_DRIFT")


def verify_detached_restore(folder, *, target, run_id, manifest_sha):
    """Independent cold replay of event 1830 and its exact external evidence."""
    need(type(manifest_sha) is str
         and v41_bundle.SHA64.fullmatch(manifest_sha) is not None,
         "MANIFEST_HASH_REQUIRED")
    folder = _folder(folder, run_id)
    sealed = folder / "manifest.sha256.json"
    need(sealed.is_file() and v41_bundle._nonlink(sealed)
         and 0 < sealed.stat().st_size <= 1_000_000,
         "MANIFEST_MISSING_OR_UNSAFE")
    raw = sealed.read_bytes()
    need(digest(raw) == manifest_sha, "FROZEN_MANIFEST_HASH_MISMATCH")
    try:
        manifest = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise ForwardColdDenied(
            "F139_HYBRID_FORWARD_COLD_MANIFEST_UNREADABLE") from exc
    need(canonical(manifest) == raw, "NONCANONICAL_MANIFEST")
    _validate_manifest(manifest, target, run_id)
    files, negatives = v41_bundle._validate_files(folder, manifest)
    original_sqlite = folder / "state.sqlite"
    cold._require_standalone_sqlite(original_sqlite)
    # No original owner/runner connection: independently restore the WAL
    # inclusive copy from its *hashed bytes* and replay all original events.
    with tempfile.TemporaryDirectory(prefix="f139-v38-detached-") as temporary:
        restored = Path(temporary) / "state.sqlite"
        with cold._hashed_private_sqlite_snapshot(
                original_sqlite, files["state.sqlite"]) as sealed_sqlite:
            sealed_sqlite.verify()
            meta = sealed_sqlite.meta()
            need(meta["source_sha"] == forward.FROM
                 and meta["head_seq"] == forward.V37_SEQ
                 and meta["head_hash"] == forward.V37_HEAD
                 and cold.required_negative_custody(sealed_sqlite) == negatives
                 and digest(canonical(rollback_view(sealed_sqlite.conn))) ==
                     manifest["logical_all_tables_sha256"],
                 "COMMITTED_SOURCE_SQLITE_NOT_RESTORABLE")
            with closing(sqlite3.connect(
                    str(restored), isolation_level=None)) as destination:
                sealed_sqlite.conn.backup(destination)
        cold._require_standalone_sqlite(restored)
        cold.copy_negative_custody(
            folder, Path(temporary), negatives, copy_files=True)
        with closing(cold._open_immutable_hashed_backup(restored)) as final:
            final.verify()
            meta = final.meta()
            need(meta["source_sha"] == forward.FROM
                 and meta["head_seq"] == forward.V37_SEQ
                 and meta["head_hash"] == forward.V37_HEAD
                 and digest(canonical(rollback_view(final.conn))) ==
                     manifest["logical_all_tables_sha256"],
                 "INDEPENDENT_RESTORED_SOURCE_OR_HISTORY_DRIFT")
        need(cold._hash_standalone_sqlite(restored) ==
             manifest["restored_sqlite_sha256"],
             "RESTORED_SQLITE_SHA_DRIFT")
    v41_bundle._validate_files(folder, manifest)
    need(digest(sealed.read_bytes()) == manifest_sha,
         "MANIFEST_CHANGED_DURING_DETACHED_REPLAY")
    return {
        "schema": RESTORE_SCHEMA,
        "original_source_sha": forward.FROM,
        "candidate_sha": target, "run_id": run_id,
        "original_head_seq": forward.V37_SEQ,
        "original_head_sha256": forward.V37_HEAD,
        "manifest_sha256": manifest_sha,
        "logical_all_tables_sha256": manifest["logical_all_tables_sha256"],
        "predecessor_backup_manifest_sha256":
            manifest["predecessor_backup_manifest_sha256"],
        "provider_archives_bytes_verified": True,
        "generation_binary_bytes_verified": True,
        "independent_detached_restore_verified": True,
        "original_owner_mutations": 0,
        "new_dispatches": 0,
        "source_transition_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
    }


def stage_complete_cold_bundle(original, frozen_old_request, *,
                               target, run_id, owner_disabled_witness,
                               release_witness):
    """Create-only, no retry. WITNESSES MUST be supplied by qualified caller.

    No task or source mutation is permitted. On any partial copy, fail closed
    and leave a colliding folder: never overwrite unknown-effect evidence.
    """
    from f139 import nci04_v41_hybrid_forward_readiness as readiness
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and original.filename.is_absolute()
         and original.filename.name == "state.sqlite"
         and SingleOwner.held(original.filename.with_suffix(".lock"))
         and callable(owner_disabled_witness)
         and callable(release_witness)
         and owner_disabled_witness() is True
         and release_witness() is True
         and type(frozen_old_request) is dict
         and type(run_id) is int and run_id > 0,
         "INDEPENDENT_OWNER_RELEASE_AND_LOCK_REQUIRED")
    readiness.inspect_held_original(original, frozen_old_request)
    before = original.meta().copy()
    need(before["source_sha"] == forward.FROM
         and before["head_seq"] == forward.V37_SEQ
         and before["head_hash"] == forward.V37_HEAD,
         "COMMITTED_1830_SOURCE_ONLY_REQUIRED")
    old_backup = original.filename.parent / (
        "f139-hybrid-before-" + str(frozen_old_request["backup_run_id"]))
    old_manifest_raw = (old_backup / "manifest.sha256.json").read_bytes()
    need(digest(old_manifest_raw) ==
         frozen_old_request["backup_manifest_sha256"],
         "PREDECESSOR_SEALED_BUNDLE_CHANGED")
    old_manifest = json.loads(old_manifest_raw)
    old_files, _ = v41_bundle._validate_files(old_backup, old_manifest)
    new_folder = original.filename.parent / _name(run_id)
    need(not new_folder.exists() and not new_folder.is_symlink(),
         "UNKNOWN_RESULT_BACKUP_REPLAY_FORBIDDEN")
    need(all(v41_bundle._nonlink(parent) for parent
             in (original.filename.parent, *original.filename.parents)),
         "ORIGINAL_FOLDER_SYMLINK_FORBIDDEN")
    new_folder.mkdir(mode=0o700, exist_ok=False)
    backup = new_folder / "state.sqlite"
    with closing(sqlite3.connect(
            str(backup), isolation_level=None)) as destination:
        original.conn.backup(destination)
    cold._require_standalone_sqlite(backup)
    sqlite_sha = cold._hash_standalone_sqlite(backup)
    # Carry provider archives, old source-generation binary and all frozen
    # negatives from their previously sealed backup. Do not regenerate
    # consumed evidence or rebase the historical executable onto new source.
    for relative, expected in sorted(old_files.items()):
        if relative == "state.sqlite":
            continue
        components = relative.split("/")
        old_path = old_backup.joinpath(*components)
        new_path = new_folder.joinpath(*components)
        need(old_path.is_file() and v41_bundle._nonlink(old_path)
             and digest(old_path.read_bytes()) == expected
             and not new_path.exists(), "PREDECESSOR_BYTES_CHANGED")
        new_path.parent.mkdir(parents=True, exist_ok=True)
        with old_path.open("rb") as source, new_path.open("xb") as sink:
            shutil.copyfileobj(source, sink, length=1024 * 1024)
        need(digest(new_path.read_bytes()) == expected,
             "FROZEN_PROVIDER_OR_BINARY_COPY_DRIFT")
    files = dict(old_files)
    files["state.sqlite"] = sqlite_sha
    logical = digest(canonical(rollback_view(original.conn)))
    with tempfile.TemporaryDirectory(prefix="f139-v38-cold-staged-") as temporary:
        restored = Path(temporary) / "state.sqlite"
        with cold._hashed_private_sqlite_snapshot(
                backup, sqlite_sha) as copied:
            copied.verify()
            need(copied.meta() == before
                 and digest(canonical(rollback_view(copied.conn))) == logical,
                 "CURRENT_SQLITE_NOT_SAME_AS_COLD_COPY")
            with closing(sqlite3.connect(
                    str(restored), isolation_level=None)) as destination:
                copied.conn.backup(destination)
        cold._require_standalone_sqlite(restored)
        negatives = cold.required_negative_custody(original)
        cold.copy_negative_custody(
            new_folder, Path(temporary), negatives, copy_files=True)
        with closing(cold._open_immutable_hashed_backup(restored)) as final:
            final.verify()
            need(final.meta() == before
                 and digest(canonical(rollback_view(final.conn))) == logical,
                 "NEW_DETACHED_HISTORY_OR_TABLES_DRIFT")
        restored_sha = cold._hash_standalone_sqlite(restored)
    manifest = {
        "schema": SCHEMA,
        "original_source_sha": forward.FROM,
        "candidate_sha": target,
        "run_id": run_id,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "predecessor_backup_run_id": frozen_old_request["backup_run_id"],
        "predecessor_backup_manifest_sha256":
            frozen_old_request["backup_manifest_sha256"],
        "files_sha256": dict(sorted(files.items())),
        "logical_all_tables_sha256": logical,
        "provider_archives_manifest_sha256":
            old_manifest["provider_archives_manifest_sha256"],
        "generation_binary_manifest_sha256":
            old_manifest["generation_binary_manifest_sha256"],
        "negative_custody_manifest_sha256":
            old_manifest["negative_custody_manifest_sha256"],
        "restored_sqlite_sha256": restored_sha,
        "original_owner_mutations": 0,
        "new_dispatches": 0,
        "owner_quiescence_verified": False,
        "source_transition_authorized": False,
        "owner_policy_modified": False,
        "worker_dispatched": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
    }
    _validate_manifest(manifest, target, run_id)
    encoded = canonical(manifest)
    with (new_folder / "manifest.sha256.json").open("xb") as output:
        output.write(encoded)
        output.flush()
    manifest_sha = digest(encoded)
    receipt = verify_detached_restore(
        new_folder, target=target, run_id=run_id,
        manifest_sha=manifest_sha)
    need(owner_disabled_witness() is True
         and release_witness() is True
         and original.meta() == before
         and original.conn.total_changes == 0,
         "ORIGINAL_SOURCE_OR_OWNER_CHANGED_DURING_COPY")
    return receipt
