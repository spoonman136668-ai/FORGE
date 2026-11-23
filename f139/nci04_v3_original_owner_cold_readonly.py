"""Read-only V3 handoff: qualified GitHub source + original signed cold V1 history.

This is an inert *composition* of the already-merged V3 remote verifier and
the existing V2-failure V1 cold-restoration verifier. It does not grant source
forward, stop a Windows task, sign a certificate, create a worker, or admit
scientific first-use. An independent original-owner action must verify the
actual Windows task/SID/DPAPI and source checkout before any live transition.
"""
from __future__ import annotations

from pathlib import Path

from f139.local_controller import Database, SingleOwner
from f139.nci04_fresh_owner_source_forward import NAME as V1_NAME
from f139.nci04_native_contract import digest
from f139.nci04_v2_failed_prepare_restore_original import (
    CHECKPOINT_HASH, CHECKPOINT_SEQ, ORIGINAL, ORIGINAL_TREE, validate,
)
from f139.nci04_v3_remote_readonly_preflight import (
    REPO, inspect_merged_source_readonly,
)

SCHEMA = "forge.f139.v3-original-owner-cold-readonly.v1"
V3_CERT_NAME = "fresh-original-owner-source-forward-v3.json"


class V3ColdReadDenied(ValueError):
    """Reject an incomplete or unauthenticated read-only original-owner handoff."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise V3ColdReadDenied("F139_V3_COLD_READONLY_" + reason)


def _bounded_original_certificate(path: Path) -> bytes:
    """Reject absent, linked, or oversized V1 files before reading bytes."""
    need(path.is_file() and not path.is_symlink(),
         "ORIGINAL_CERTIFICATE_FILE_INVALID")
    need(0 < path.stat().st_size <= 8192,
         "ORIGINAL_CERTIFICATE_SIZE_DRIFT")
    with path.open("rb") as stream:
        data = stream.read(8193)
    need(0 < len(data) <= 8192, "ORIGINAL_CERTIFICATE_SIZE_DRIFT")
    return data

def inspect_original_owner_cold_readonly(
    db: Database, api, key: str, folder: Path, *,
    owner_source_sha: str, owner_source_tree: str, pr_number: int,
    pr_head_sha: str, regression_run_id: int, source_run_id: int,
    rehearsal_run_id: int,
) -> dict:
    """Combine two existing verifiers without granting any mutation authority.

    The caller must already hold the original Windows owner's exclusive
    kernel lock and open SQLite *read-only*. This does not acquire that lock,
    quiesce an owner process, authenticate an OS SID, or touch Task Scheduler.
    """
    need(type(db) is Database and isinstance(folder, Path)
         and type(key) is str and 32 <= len(key) <= 4096,
         "INPUT_INVALID")
    need(getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
         "READONLY_DATABASE_REQUIRED")
    need(SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_OWNER_LOCK_REQUIRED")
    need(not (folder / V3_CERT_NAME).exists()
         and not (folder / V3_CERT_NAME).is_symlink(),
         "V3_CERTIFICATE_ALREADY_PRESENT")
    before = db.conn.total_changes
    try:
        remote = inspect_merged_source_readonly(
            api, owner_source_sha=owner_source_sha,
            owner_source_tree=owner_source_tree, pr_number=pr_number,
            pr_head_sha=pr_head_sha,
            regression_run_id=regression_run_id,
            source_run_id=source_run_id,
            rehearsal_run_id=rehearsal_run_id,
        )
        # The original V2 PREPARE failed after disabling the task, before V2
        # signing. Reuse the restored V1 exact-source and all-receipt cold
        # verifier; no V2 failure is silently promoted to signed custody.
        original_certificate = _bounded_original_certificate(folder / V1_NAME)
        cold = validate(db, key, folder, CHECKPOINT_SEQ, CHECKPOINT_HASH)
        need(cold["original_source_sha"] == ORIGINAL
             and cold["original_source_tree"] == ORIGINAL_TREE
             and cold["verified_tasks"] == 3
             and cold["v2_certificate_present"] is False
             and remote["remote_evidence"] == "VERIFIED_READ_ONLY"
             and remote["owner_source_sha"] == owner_source_sha,
             "SOURCE_OR_COLD_CHECKPOINT_MISMATCH")
        # validate() checked canonical bytes and original owner HMAC. Digest
        # exactly those immutable bytes for a future, separately versioned V3
        # certificate; this reader never creates or signs that certificate.
        need(_bounded_original_certificate(folder / V1_NAME) == original_certificate,
             "ORIGINAL_CERTIFICATE_CHANGED_DURING_AUDIT")
        last = api.get(REPO + "/branches/main")
        need(type(last) is dict and last.get("name") == "main"
             and last.get("protected") is True
             and last.get("commit", {}).get("sha") == owner_source_sha,
             "MAIN_MOVED_DURING_COLD_READ")
        need(getattr(db, "_readonly_opened", False) is True
             and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
             and db.conn.total_changes == before
             and db.meta()["head_seq"] == CHECKPOINT_SEQ
             and db.meta()["head_hash"] == CHECKPOINT_HASH
             and SingleOwner.held(db.filename.with_suffix(".lock")),
             "ORIGINAL_LEDGER_OR_LOCK_MOVED")
    except Exception as exc:
        raise V3ColdReadDenied(
            "F139_V3_COLD_READONLY_REMOTE_OR_SIGNED_HISTORY_UNVERIFIED"
        ) from exc

    return {
        "schema": SCHEMA,
        "source_commit": remote["owner_source_sha"],
        "source_tree": remote["owner_source_tree"],
        "pr_number": remote["pr_number"],
        "qualified_head": remote["pr_head_sha"],
        "regression_run_id": regression_run_id,
        "source_run_id": source_run_id,
        "rehearsal_run_id": rehearsal_run_id,
        "previous_owner_source_sha": ORIGINAL,
        "previous_owner_source_tree": ORIGINAL_TREE,
        "previous_certificate_sha256": digest(original_certificate),
        "cold_terminal_seq": CHECKPOINT_SEQ,
        "cold_terminal_hash": CHECKPOINT_HASH,
        "verified_terminal_tasks": cold["verified_tasks"],
        "remote_evidence": "VERIFIED_READ_ONLY",
        "signed_v1_cold_history": "VERIFIED_READ_ONLY",
        "original_windows_sid_and_task": "NOT_CHECKED",
        "installed_checkout": "NOT_CHECKED",
        "source_forward_authorized": False,
        "safe_to_disable_task": False,
        "signed_v3_certificate": False,
        "sqlite_mutations": 0,
        "worker_dispatches": 0,
        "scientific_first_use": False,
    }
