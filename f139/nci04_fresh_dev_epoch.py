"""Inert F139 fresh DEVELOPMENT epoch from an independently archived original.

No owner task control, activation, GitHub request, worker dispatch, queue
admission, model call or scientific first-use. The caller must independently
quiesce the existing Windows task, hold its ORIGINAL kernel mutex, and finish
the V59 original cold bundle before invoking this source-only library.

An empty new SQLite is NOT evidence that historical experiments are unspent.
The fresh directory is a disconnected, disabled staging artifact. A separate
owner-authenticated no-replay release must qualify any later task rebind.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256, audit_frozen_original_readonly,
)
from f139.nci04_v59_cold_backup_verify import (
    MIN_RUN, verify_original_cold_backup,
)
from f139.nci04_v59_cold_backup_stage import inventory
from f139.nci04_fresh_dev_exclusions import freeze_original_exclusions

SCHEMA = "forge.f139.fresh-development-epoch-inert.v1"
ARCHIVE_SCHEMA = "forge.f139.v59.original-cold-createonly.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")


class FreshDevelopmentDenied(ValueError):
    """Do not treat a failed preparation as permission to retry a write."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise FreshDevelopmentDenied("F139_FRESH_DEV_" + reason)


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def prepare_inert_epoch(
    original: Database,
    archive: Path,
    *,
    target: str,
    owner_run_id: int,
    task_quiescence_witness,
) -> dict:
    """Create only a *disabled*, separate SQLite. Never retarget the owner task.

    Caller owns verification of the original task's Windows SID, Disabled
    state, stopped process, and actual owner-process release. The callable is
    checked both before and after staging, but is not an independent proof.
    Nothing from this return value is source, first-use or launch authority.
    """
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and original.conn.total_changes == 0,
         "ORIGINAL_READONLY_REQUIRED")
    need(type(owner_run_id) is int and owner_run_id > MIN_RUN
         and type(target) is str and SHA40.fullmatch(target) is not None
         and target != SOURCE, "FRESH_TARGET_OR_RUN_INVALID")
    origin = Path(original.filename)
    root = origin.parent
    need(origin.is_absolute() and origin.name == "state.sqlite"
         and root.name == "FORGE-F139"
         and origin.is_file() and not origin.is_symlink()
         and not root.is_symlink()
         and not getattr(root, "is_junction", lambda: False)()
         and SingleOwner.held(origin.with_suffix(".lock")) is True,
         "ORIGINAL_ROOT_OR_MUTEX_INVALID")
    need(callable(task_quiescence_witness)
         and task_quiescence_witness() is True,
         "ORIGINAL_TASK_NOT_QUIESCED")
    original.verify()
    before = audit_frozen_original_readonly(original)
    need(before["source_sha"] == SOURCE
         and before["head_seq"] == HEAD_SEQ
         and before["head_sha256"] == HEAD_SHA256,
         "ORIGINAL_EVENT_PREIMAGE_DRIFT")

    archive = Path(archive)
    expected = root / ("f139-v59-before-" + str(owner_run_id))
    fresh = root / ("f139-fresh-dev-" + str(owner_run_id))
    need(archive.is_absolute() and archive == expected
         and archive.is_dir() and not archive.is_symlink()
         and not getattr(archive, "is_junction", lambda: False)()
         and not fresh.exists() and not fresh.is_symlink(),
         "ARCHIVE_OR_FRESH_PATH_INVALID")
    backup = archive / "state.sqlite"
    seal = archive / "manifest.sha256.json"
    need(backup.is_file() and seal.is_file()
         and not backup.is_symlink() and not seal.is_symlink()
         and backup.stat().st_size > 1024
         and seal.stat().st_size <= 256_000,
         "SEALED_ARCHIVE_MISSING")
    raw_seal = seal.read_bytes()
    try:
        manifest = json.loads(raw_seal)
    except (UnicodeError, ValueError) as exc:
        raise FreshDevelopmentDenied("F139_FRESH_DEV_ARCHIVE_MANIFEST_INVALID") from exc
    need(type(manifest) is dict and raw_seal == canonical(manifest)
         and manifest.get("schema") == ARCHIVE_SCHEMA
         and manifest.get("owner_run_id") == owner_run_id
         and manifest.get("original_source_sha") == SOURCE
         and manifest.get("target_source_sha") == target
         and manifest.get("original_head_seq") == HEAD_SEQ
         and manifest.get("original_head_sha256") == HEAD_SHA256
         and manifest.get("source_transition_authorized") is False
         and manifest.get("scientific_first_use") is False
         and manifest.get("owner_mutations") == 0
         and type(manifest.get("files_sha256")) is dict,
         "ARCHIVE_MANIFEST_PREIMAGE_INVALID")
    files = manifest["files_sha256"]
    need(inventory(archive) == set(files) | {"manifest.sha256.json"},
         "ARCHIVE_INVENTORY_DRIFT")
    for relative, wanted in files.items():
        need(type(relative) is str and relative != "manifest.sha256.json"
             and "\\" not in relative and ":" not in relative
             and all(part not in ("", ".", "..") for part in relative.split("/"))
             and type(wanted) is str and SHA64.fullmatch(wanted) is not None,
             "ARCHIVE_FILE_IDENTITY_INVALID")
        file = archive.joinpath(*relative.split("/"))
        need(file.is_file() and not file.is_symlink()
             and hash_file(file) == wanted,
             "ARCHIVE_FILE_BYTES_DRIFT")
    backup_sha = hash_file(backup)
    need(files.get("state.sqlite") == backup_sha
         and SHA64.fullmatch(backup_sha) is not None,
         "BACKUP_BYTES_DRIFT")
    verified = verify_original_cold_backup(
        original, backup, owner_run_id=owner_run_id,
        target=target, expected_backup_sha256=backup_sha)
    need(type(verified) is dict
         and verified.get("from_source_sha") == SOURCE
         and verified.get("to_source_sha") == target
         and verified.get("original_head_seq") == HEAD_SEQ
         and verified.get("original_head_sha256") == HEAD_SHA256
         and verified.get("backup_sqlite_sha256") == backup_sha
         and verified.get("original_owner_mutations") == 0
         and verified.get("source_transition_authorized") is False
         and verified.get("scientific_first_use") is False,
         "INDEPENDENT_COLD_VERIFIER_REJECTED")
    need(task_quiescence_witness() is True
         and SingleOwner.held(origin.with_suffix(".lock")) is True
         and original.conn.total_changes == 0
         and audit_frozen_original_readonly(original) == before
         and hash_file(backup) == backup_sha,
         "PREPARATION_PREIMAGE_MOVED")

    # Every consumed local ticket/issue/candidate identity is snapshot-bound
    # to the independently cold-verified original; none is made runnable.
    exclusions = freeze_original_exclusions(original)
    exclusions_bytes = canonical(exclusions)
    exclusions_sha = digest(exclusions_bytes)
    need(exclusions.get("release_qualified") is False
         and exclusions.get("fresh_activation_authorized") is False
         and exclusions.get("original_head_seq") == HEAD_SEQ
         and exclusions.get("original_head_sha256") == HEAD_SHA256,
         "CONSUMED_HISTORY_NOT_FROZEN")
    # Never rename, delete, overwrite, initialize or retarget the live original.
    fresh.mkdir(mode=0o700, exist_ok=False)
    state = fresh / "state.sqlite"
    new = Database.initialize(state, target)
    try:
        new.verify()
        meta = new.meta()
        need(meta["source_sha"] == target and meta["epoch"] == 1
             and meta["enabled"] == 0 and meta["legacy_suspended"] == 0
             and meta["head_seq"] == 0
             and new.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
             and new.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0,
             "FRESH_STATE_NOT_DISABLED_AND_EMPTY")
    finally:
        new.close()
    need(state.is_file() and not state.is_symlink()
         and original.conn.total_changes == 0
         and SingleOwner.held(origin.with_suffix(".lock")) is True
         and task_quiescence_witness() is True
         and audit_frozen_original_readonly(original) == before
         and hash_file(backup) == backup_sha,
         "ORIGINAL_OR_BACKUP_DRIFT_AFTER_STAGING")
    state_sha = hash_file(state)
    exclusion_path = fresh / "consumed-development-identities.json"
    with exclusion_path.open("xb") as f:
        f.write(exclusions_bytes)
    need(exclusion_path.read_bytes() == exclusions_bytes,
         "CONSUMED_HISTORY_READBACK_DRIFT")
    receipt = {
        "schema": SCHEMA, "owner_run_id": owner_run_id,
        "historical_consumed_exclusions_sha256": exclusions_sha,
        "historical_consumed_exclusions_path":
            exclusion_path.relative_to(root).as_posix(),
        "previous_source_sha": SOURCE,
        "target_source_sha": target,
        "historical_head_seq": HEAD_SEQ,
        "historical_head_sha256": HEAD_SHA256,
        "historical_cold_manifest_sha256": digest(raw_seal),
        "historical_sqlite_sha256": backup_sha,
        "fresh_sqlite_sha256": state_sha,
        "fresh_state_relative_path": state.relative_to(root).as_posix(),
        "original_sqlite_preserved": True,
        "original_owner_mutations": 0,
        "original_task_mutations": 0,
        "fresh_database_enabled": False,
        "fresh_queue_entries": 0,
        "old_work_replay_authorized": False,
        "scientific_first_use": False,
        "source_transition_authorized": False,
        "owner_task_rebind_authorized": False,
        "new_controller": False,
        "new_scheduler": False,
        "worker_dispatched": False,
        "paid_model_calls": 0,
        "release_qualified": False,
    }
    encoded = canonical(receipt)
    path = fresh / "fresh-dev-manifest.sha256.json"
    with path.open("xb") as f:
        f.write(encoded)
    need(path.read_bytes() == encoded and hash_file(state) == state_sha
         and exclusion_path.read_bytes() == exclusions_bytes
         and digest(exclusion_path.read_bytes()) == exclusions_sha,
         "INERT_MANIFEST_READBACK_DRIFT")
    return dict(receipt, manifest_sha256=digest(encoded))
