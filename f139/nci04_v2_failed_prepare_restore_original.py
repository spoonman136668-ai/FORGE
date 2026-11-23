"""Read-only, original-lock-held cold gate for V2 PREPARE failure recovery.

This module never changes a task, provider, source ref, SQLite, or worker.
It authenticates the signed original V1 release plus all immutable V1 receipts
before a separately owner-authorized Windows host can start its old task.
"""
from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
import sys

from f139.local_controller import Database, SingleOwner
from f139.nci04_fresh_lifecycle import CUSTODY_KIND, read_lifecycle
from f139.nci04_fresh_owner_source_forward import (
    FIELDS as V1_FIELDS, NAME as V1_NAME, SCHEMA as V1_SCHEMA, sign,
)
from f139.nci04_fresh_owner_source_forward_v2 import NAME as V2_NAME
from f139.nci04_native_contract import canonical

ORIGINAL = "f24251e0d95938e593a54c1577a34efadc8080d8"
ORIGINAL_TREE = "b63e6346b9d665664bb4e248535a60db9473b592"
CHECKPOINT_SEQ = 23
CHECKPOINT_HASH = "b4e2229ce9c8dba9a430c37277bb8630c5d6f6014e429d9b62724130c7f82da1"


class RestoreDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise RestoreDenied("F139_V2_POSTFAIL_RESTORE_" + code)


def validate(db: Database, key: str, folder: Path, seq: int, head: str) -> dict:
    """Prove the exact known old source/certificate and signed cold history."""
    need(type(db) is Database and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_SINGLE_OWNER_LOCK_REQUIRED")
    need(type(seq) is int and seq == CHECKPOINT_SEQ and head == CHECKPOINT_HASH,
         "FAILED_PREPARE_CHECKPOINT_REQUIRED")
    need(folder.is_dir() and not folder.is_symlink()
         and folder.resolve() == db.filename.parent.resolve(),
         "CERTIFICATE_DIRECTORY_DRIFT")
    v1, v2 = folder / V1_NAME, folder / V2_NAME
    need(v1.is_file() and not v1.is_symlink()
         and 0 < v1.stat().st_size <= 8192
         and not v2.exists() and not v2.is_symlink(),
         "V1_SIGNED_CERT_REQUIRED_V2_MUST_BE_ABSENT")
    data = v1.read_bytes()
    try:
        doc = json.loads(data)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise RestoreDenied("F139_V2_POSTFAIL_RESTORE_CERTIFICATE_INVALID") from exc
    need(type(doc) is dict and set(doc) == V1_FIELDS
         and canonical(doc) == data
         and doc["schema"] == V1_SCHEMA
         and doc["pr_number"] == 1865
         and doc["owner_source_sha"] == ORIGINAL
         and doc["owner_source_tree"] == ORIGINAL_TREE
         and doc["task_name"] == "FORGE-F139-UnifiedController"
         and doc["terminal_seq"] == 9
         and doc["development_only"] is True
         and doc["worker_release_unchanged"] is True
         and doc["scientific_first_use"] is False
         and type(doc["paid_model_calls"]) is int
         and doc["paid_model_calls"] == 0
         and type(doc["owner_signature"]) is str,
         "ORIGINAL_V1_CERTIFICATE_SCOPE_INVALID")
    actual_sig = sign({k: v for k, v in doc.items()
                       if k != "owner_signature"}, key)
    need(hmac.compare_digest(actual_sig, doc["owner_signature"]),
         "ORIGINAL_V1_OWNER_SIGNATURE_DRIFT")
    release, entries = read_lifecycle(db, key)
    meta = db.meta()
    need(meta["head_seq"] == seq and meta["head_hash"] == head
         and len(entries) == 3 and all(
             e["stage"] == "VERIFIED" and e.get("negative") is None
             and e.get("custody") is not None for e in entries)
         and doc["admission_source_sha"] == release["admission_source_sha"]
         and doc["worker_release_sha"] == release["worker_release_sha"]
         and doc["worker_release_tree"] == release["worker_release_tree"],
         "SIGNED_COLD_LIFECYCLE_OR_SOURCE_DRIFT")
    event = db.conn.execute(
        "SELECT kind,sha FROM events WHERE seq=?", (seq,)).fetchone()
    old_event = db.conn.execute(
        "SELECT kind,sha FROM events WHERE seq=9").fetchone()
    need(event is not None and event["kind"] == CUSTODY_KIND
         and event["sha"] == head
         and old_event is not None
         and old_event["kind"] == CUSTODY_KIND
         and old_event["sha"] == doc["terminal_hash"],
         "SEALED_PROVIDER_CUSTODY_DRIFT")
    pending = db.conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE stage != 'VERIFIED'").fetchone()[0]
    need(pending == 0 and len(list(db.conn.execute(
         "SELECT ticket FROM tasks"))) == 3,
         "OWNER_HAS_UNSETTLED_WORK")
    return {
        "schema": "forge.f139.v2-failed-prepare-original-cold-recovery.v1",
        "original_source_sha": ORIGINAL,
        "original_source_tree": ORIGINAL_TREE,
        "head_seq": seq,
        "head_hash": head,
        "verified_tasks": len(entries),
        "outstanding": pending,
        "v2_certificate_present": False,
        "owner_task_mutations": 0,
        "sqlite_mutations": 0,
        "worker_dispatches": 0,
        "scientific_first_use": False,
    }


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    need(len(args) == 5 and args[0] == "audit"
         and args[3].isdecimal() and args[4] == CHECKPOINT_HASH,
         "CLI_ARGUMENTS_INVALID")
    dbpath = Path(args[1]).resolve(strict=True)
    folder = Path(args[2]).resolve(strict=True)
    key = os.environ.get("F139_WORKER_HMAC_KEY", "")
    need(len(key) >= 32 and args[3] == str(CHECKPOINT_SEQ),
         "CLI_KEY_OR_CHECKPOINT_INVALID")
    with SingleOwner(dbpath.with_suffix(".lock")):
        db = Database.open_readonly(dbpath)
        try:
            before = db.conn.total_changes
            result = validate(db, key, folder, int(args[3]), args[4])
            need(before == 0 and db.conn.total_changes == 0,
                 "READONLY_DATABASE_MUTATED")
            print("F139_V2_POSTFAIL_COLD=" + canonical(result).decode("utf-8"))
        finally:
            db.close()


if __name__ == "__main__":
    main()
