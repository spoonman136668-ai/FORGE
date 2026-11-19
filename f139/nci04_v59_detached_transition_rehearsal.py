"""V59: test a V48 source transition on one *detached copy* only.

No CLI, original owner task control, staging, backup generation, live
SQLite writer, remote API, scientific first-use or source promotion here.
The external owner route must independently create and certify a separate
private rehearsal copy with full adjunct custody before passing its DB.
Even a passing rehearsal grants no original-owner execution authority.
"""
from __future__ import annotations

from contextlib import closing
import os
from pathlib import Path
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import (
    APPROVAL_SCHEMA, activate_native, verify_native_activation,
)
from f139.nci04_v38_original_owner_transition_cli import rollback_view
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256, audit_frozen_original_readonly,
)
from f139.nci04_v59_forward_transition import (
    SCHEMA, FIELDS, EVENT_SEQ, MIN_OWNER_RUN, proposed_cold_proof,
)

SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class V59DetachedRehearsalDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise V59DetachedRehearsalDenied("F139_V59_REHEARSAL_" + reason)


def require_detached_paths(original: Database, detached: Database,
                           owner_run_id: int) -> None:
    """Fail before write unless a non-owner temp copy has its own lock."""
    need(type(owner_run_id) is int and owner_run_id > MIN_OWNER_RUN,
         "RUN_ID_INVALID")
    need(type(original) is Database and type(detached) is Database
         and getattr(original, "_readonly_opened", False) is True
         and not getattr(detached, "_readonly_opened", False),
         "READONLY_OR_WRITER_CLASS_INVALID")
    origin = Path(original.filename)
    copy = Path(detached.filename)
    need(origin.is_absolute() and copy.is_absolute()
         and origin.name == copy.name == "state.sqlite"
         and origin.parent.name == "FORGE-F139"
         and origin.is_file() and copy.is_file()
         and not origin.is_symlink() and not copy.is_symlink()
         and not origin.parent.is_symlink() and not copy.parent.is_symlink()
         and not getattr(origin.parent, "is_junction", lambda: False)()
         and not getattr(copy.parent, "is_junction", lambda: False)(),
         "SOURCE_OR_COPY_PATH_INVALID")
    raw_root = os.environ.get("RUNNER_TEMP", "")
    need(bool(raw_root) and Path(raw_root).is_absolute()
         and Path(raw_root).is_dir()
         and not Path(raw_root).is_symlink()
         and not getattr(Path(raw_root), "is_junction", lambda: False)(),
         "DETACHED_RUNNER_ROOT_UNVERIFIED")
    target = (Path(raw_root) / ("f139-v59-detached-" + str(owner_run_id))
              / "state.sqlite")
    need(copy.resolve() == target.resolve()
         and copy.resolve() != origin.resolve()
         and copy.parent.parent.resolve() != origin.parent.resolve()
         and copy.parent.name == "f139-v59-detached-" + str(owner_run_id),
         "DETACHED_COPY_OR_OWNER_ROOT_INVALID")
    need(original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and detached.conn.execute("PRAGMA query_only").fetchone()[0] == 0
         and SingleOwner.held(copy.with_suffix(".lock")),
         "READONLY_OR_EXCLUSIVE_COPY_MUTEX_REQUIRED")


def _read_copy_proof(copy: Path, **parameters) -> tuple[dict, dict, str]:
    """Verify the detached copy *before* taking its write transaction."""
    with closing(Database.open_readonly(copy)) as read:
        snapshot = audit_frozen_original_readonly(read)
        proof = proposed_cold_proof(read, **parameters)
        rows_hash = digest(canonical(rollback_view(read.conn)))
    return snapshot, proof, rows_hash


def rehearse_detached_v48(
        original: Database, detached: Database, *, target: str,
        owner_run_id: int, qualified_main_run_id: int,
        rehearsal_run_id: int, backup_sqlite_sha256: str,
        genenv_executable_sha256: str,
        generation_mechanism_sha256: str) -> dict:
    """Mutate ONLY one isolated copy; original retained and reread as RO.

    One original-copy pair is never retried after a source event is written,
    even when subsequent activation fails. The caller may NOT interpret any
    outcome as permission to stop, retarget or promote an original task.
    """
    require_detached_paths(original, detached, owner_run_id)
    need(type(target) is str and SHA40.fullmatch(target) is not None
         and target != SOURCE and
         type(qualified_main_run_id) is int and qualified_main_run_id > 0
         and type(rehearsal_run_id) is int and rehearsal_run_id > 0
         and type(backup_sqlite_sha256) is str
         and SHA64.fullmatch(backup_sqlite_sha256) is not None
         and type(genenv_executable_sha256) is str
         and SHA64.fullmatch(genenv_executable_sha256) is not None
         and type(generation_mechanism_sha256) is str
         and SHA64.fullmatch(generation_mechanism_sha256) is not None,
         "TARGET_OR_CUSTODY_INVALID")
    original_changes = original.conn.total_changes
    before = audit_frozen_original_readonly(original)
    original_meta = original.meta()
    original_hash = digest(canonical(rollback_view(original.conn)))
    need(original_changes == 0 and before["source_sha"] == SOURCE
         and before["head_seq"] == HEAD_SEQ
         and before["head_sha256"] == HEAD_SHA256,
         "ORIGINAL_PREIMAGE_INVALID")
    detached.verify()
    copy_meta = detached.meta()
    need(copy_meta == original_meta and detached.ready() is None
         and not detached.actives(),
         "DETACHED_NOT_EXACT_ORIGINAL_IDLE_PREIMAGE")
    preimage, proof, copy_hash = _read_copy_proof(
        Path(detached.filename), target=target, owner_run_id=owner_run_id,
        qualified_main_run_id=qualified_main_run_id,
        rehearsal_run_id=rehearsal_run_id,
        backup_sqlite_sha256=backup_sqlite_sha256,
        genenv_executable_sha256=genenv_executable_sha256,
        generation_mechanism_sha256=generation_mechanism_sha256)
    need(preimage == before and copy_hash == original_hash
         and type(proof) is dict and set(proof) == FIELDS
         and proof["schema"] == SCHEMA
         and proof["from_source_sha"] == SOURCE
         and proof["to_source_sha"] == target
         and proof["backup_sqlite_sha256"] == backup_sqlite_sha256,
         "DETACHED_V48_PREWRITE_PROOF_INVALID")
    # The only source change below is within a writable *copy*.
    with detached.transaction():
        need(detached.meta() == original_meta
             and detached.ready() is None and not detached.actives(),
             "DETACHED_SOURCE_CHANGED_PREWRITE")
        detached.conn.execute("UPDATE meta SET source_sha=? WHERE id=1",
                              (target,))
        detached.event("SOURCE_TRANSITION_ADMITTED", proof)
        detached.verify()
    need(detached.meta()["head_seq"] == EVENT_SEQ
         and detached.meta()["source_sha"] == target,
         "DETACHED_V48_EVENT_NOT_AUTHENTICATED_HOLD")
    activation = {
        "schema": APPROVAL_SCHEMA, "source_sha": target,
        "expected_event_head_sha256": detached.meta()["head_hash"],
        "native_development_approved": True, "scientific_first_use": False,
        "create_controller": False, "paid_api_calls": 0,
    }
    need(activate_native(detached, activation) is True,
         "DETACHED_SOURCE_ADMITTED_ACTIVATION_HOLD")
    detached.verify()
    updated = detached.meta()
    need(updated["head_seq"] == EVENT_SEQ + 1
         and updated["source_sha"] == target
         and verify_native_activation(detached, expected_source=target) is True,
         "DETACHED_POSTACTIVATION_INVALID_HOLD")
    need(original.conn.total_changes == 0
         and original.meta() == original_meta
         and audit_frozen_original_readonly(original) == before
         and digest(canonical(rollback_view(original.conn))) == original_hash,
         "ORIGINAL_MOVED_DURING_DETACHED_REHEARSAL")
    return {
        "schema": "forge.f139.v59.detached-v48-rehearsal.v1",
        "target_source_sha": updated["source_sha"],
        "detached_event_head_seq": updated["head_seq"],
        "detached_event_head_sha256": updated["head_hash"],
        "original_head_seq": HEAD_SEQ,
        "original_head_sha256": HEAD_SHA256,
        "original_mutations": 0,
        "detached_source_transition_verified": True,
        "detached_native_activation_verified": True,
        "source_transition_authorized": False,
        "new_controller": False, "new_scheduler": False,
        "new_dispatches": 0, "scientific_first_use": False,
    }
