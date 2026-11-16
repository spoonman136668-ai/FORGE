"""V44 disposable event1836 migration rehearsal from verified original cold backup.

This module has no live owner entrypoint. A different authenticated owner
adapter must hold the *original* kernel mutex and open it query-only before
calling. All SQLite writes happen only to the newly created copy path.
An exercise on a copy is not authority to install/restart/dispatch anything.
"""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import json
import shutil
import sqlite3

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v41_cold_copy_verifier import (
    _hashed_private_sqlite_snapshot, _require_standalone_sqlite,
    copy_negative_custody, required_negative_custody,
)
from f139 import nci04_v43_event1835_cold as cold
from f139 import nci04_v43_event1836_successor as successor

SCHEMA = "forge.f139.v44.original-event1836-disposable-rehearsal.v1"
BACKUP_RUN = 43866834289
BACKUP_MANIFEST = "d856b21d92772ab0bb9213988447517ac2463c5f6c25e2fdfd06c8e5dd7ed8b8"
BACKUP_TABLES = "5f14fb40039e660f10fe5f49fabcc2c5f4e2875bc1dc287edd415f51a9611812"
RELEASE_SOURCE = "4ccbb84785a43e038453d6f2bda5415ecb364084"


class CopyOnlyDenied(ValueError):
    pass


def need(ok, error):
    if not ok:
        raise CopyOnlyDenied("F139_V44_COPY_" + error)


def rehearse(original, *, owner_comment_id, run_id, copy_path,
             original_witness, release_witness, inject_failure=None):
    """Prove exact event1836 on fresh copy under existing original mutex.

    No automatic retry, cleanup of unknown partial state, original database
    writes, original task operation, policy/API writes or scientific first use.
    """
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(original.filename.with_suffix(".lock"))
         and callable(original_witness)
         and callable(release_witness)
         and original_witness() is True
         and release_witness() is True
         and type(run_id) is int and run_id > BACKUP_RUN
         and type(owner_comment_id) is int
         and owner_comment_id > successor.NEW_OWNER_INTENT_AFTER
         and isinstance(copy_path, Path) and copy_path.is_absolute()
         and copy_path.name == "rehearsal.sqlite"
         and copy_path.parent.name == str(run_id)
         and not copy_path.exists() and not copy_path.is_symlink()
         and not copy_path.parent.exists()
         and inject_failure in (None, "before_commit", "after_source_event",
                                "after_verify"),
         "FROZEN_OWNER_AND_CREATE_ONLY_COPY_REQUIRED")
    original.verify()
    before = original.meta().copy()
    need(before["source_sha"] == successor.ORIGINAL_SOURCE
         and before["head_seq"] == successor.PREDECESSOR_SEQ
         and before["head_hash"] == successor.PREDECESSOR_SHA
         and before["enabled"] == 1 and before["legacy_suspended"] == 1
         and original.conn.total_changes == 0
         and original.ready() is None and not original.actives(),
         "UNALTERED_ORIGINAL_EVENT1835_REQUIRED")
    folder = cold.backup_folder(original.filename, BACKUP_RUN)
    receipt = cold.verify_detached_restore(
        folder, target=RELEASE_SOURCE, run_id=BACKUP_RUN,
        manifest_sha=BACKUP_MANIFEST)
    need(receipt["backup_manifest_sha256"] == BACKUP_MANIFEST
         and receipt["backup_logical_all_tables_sha256"] == BACKUP_TABLES
         and receipt["independent_detached_restore_verified"] is True
         and receipt["original_head_sha256"] == before["head_hash"],
         "EXACT_SEALED_EVENT1835_RESTORE_REQUIRED")
    # Double-check frozen original before creating any copy files.
    need(original_witness() is True and release_witness() is True
         and original.meta() == before and original.conn.total_changes == 0,
         "ORIGINAL_DRIFT_BEFORE_COPY_CREATION")
    root = copy_path.parent
    need(root.parent.is_dir() and not root.parent.is_symlink()
         and not getattr(root.parent, "is_junction", lambda: False)()
         and not root.is_symlink() and not copy_path.is_symlink()
         and not root.exists(), "COPY_ROOT_UNSAFE_OR_ALREADY_EXISTS")
    root.mkdir(parents=False, exist_ok=False)
    backup_db = folder / "state.sqlite"
    sealed = json.loads((folder / "manifest.sha256.json").read_bytes())
    backups, negative = cold.bundle._validate_files(folder, sealed)
    with _hashed_private_sqlite_snapshot(
            backup_db, backups["state.sqlite"]) as frozen:
        need(frozen.meta() == before
             and required_negative_custody(frozen) == negative,
             "IMMUTABLE_BACKUP_NEGATIVE_OR_META_DRIFT")
        with closing(sqlite3.connect(
                str(copy_path), isolation_level=None)) as connection:
            frozen.conn.backup(connection)
    _require_standalone_sqlite(copy_path)
    copy_negative_custody(folder, root, negative, copy_files=True)
    need(original.meta() == before and original.conn.total_changes == 0,
         "ORIGINAL_MUTATED_DURING_COPY")
    with SingleOwner(copy_path.with_suffix(".lock")):
        with closing(Database(copy_path)) as copied:
            need(copied.meta() == before and
                 copied.ready() is None and not copied.actives(),
                 "DISPOSABLE_NOT_FROZEN_ORIGINAL")
            proof = successor.build_proof(
                copied, target=RELEASE_SOURCE,
                owner_event_id=owner_comment_id,
                backup_run_id=BACKUP_RUN,
                backup_manifest_sha256=BACKUP_MANIFEST,
                backup_logical_all_tables_sha256=BACKUP_TABLES)
            proof_sha = digest(canonical(proof))
            before_event = copied.meta().copy()
            try:
                with copied.transaction():
                    copied.verify()
                    need(copied.meta() == before_event
                         and release_witness() is True
                         and original_witness() is True,
                         "ORIGINAL_WITNESS_DRIFT_BEFORE_COPY_COMMIT")
                    if inject_failure == "before_commit":
                        raise CopyOnlyDenied("F139_V44_COPY_INJECTED_PRECOMMIT")
                    copied.conn.execute(
                        "UPDATE meta SET source_sha=? WHERE id=1",
                        (RELEASE_SOURCE,))
                    copied.event("SOURCE_TRANSITION_ADMITTED", proof)
                    if inject_failure == "after_source_event":
                        raise CopyOnlyDenied(
                            "F139_V44_COPY_INJECTED_AFTER_SOURCE_EVENT")
                    copied.verify()
                    need(copied.meta()["head_seq"] ==
                         successor.PREDECESSOR_SEQ + 1
                         and copied.meta()["source_sha"] == RELEASE_SOURCE,
                         "DISPOSABLE_SOURCE_EVENT_NOT_REPLAYABLE")
                    if inject_failure == "after_verify":
                        raise CopyOnlyDenied("F139_V44_COPY_INJECTED_POSTVERIFY")
            except CopyOnlyDenied:
                need(copied.meta() == before_event,
                     "INJECTED_COPY_TRANSACTION_DID_NOT_ROLL_BACK")
                raise
            copied.verify()
            after = copied.meta().copy()
            event = copied.conn.execute(
                "SELECT kind,seq,sha,payload FROM events WHERE seq=?",
                (successor.PREDECESSOR_SEQ + 1,)).fetchone()
            need(event is not None
                 and event["seq"] == after["head_seq"]
                 and event["kind"] == "SOURCE_TRANSITION_ADMITTED"
                 and event["sha"] == after["head_hash"]
                 and json.loads(event["payload"]) == proof,
                 "COPIED_1836_EVENT_DRIFT")
    need(original_witness() is True and release_witness() is True
         and original.meta() == before and original.conn.total_changes == 0,
         "ORIGINAL_WITNESS_CHANGED_AFTER_REHEARSAL")
    return {
        "schema": SCHEMA,
        "original_source_sha": successor.ORIGINAL_SOURCE,
        "target_source_sha": RELEASE_SOURCE,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "copy_head_seq": after["head_seq"],
        "copy_head_sha256": after["head_hash"],
        "event1836_proof_sha256": proof_sha,
        "backup_run_id": BACKUP_RUN,
        "backup_manifest_sha256": BACKUP_MANIFEST,
        "backup_logical_all_tables_sha256": BACKUP_TABLES,
        "owner_comment_id": owner_comment_id,
        "rehearsal_run_id": run_id,
        "separate_copy_only": True,
        "original_sqlite_mutations": 0,
        "original_task_mutations": 0,
        "new_dispatches": 0,
        "live_source_transition_authorized": False,
        "scientific_first_use": False,
        "task_restart_authorized": False,
    }
