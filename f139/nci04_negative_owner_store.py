"""F139 NCI04-A8B: original-owner negative ZIP custody, no work replay.

A single authenticated FAILED native original is durably stored before an
append-only event. On process restart, every database verification checks the
original ZIP bytes. No task stage, run_id, scientific authority, source SHA,
controller scheduler or GitHub issue is mutated by this module.

The first A8B admission is deliberately bound to the owner's original 47-event
history and issue #696. General negative succession is NOT enabled here.
"""
from __future__ import annotations

import os
from pathlib import Path
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_negative_custody import verified_negative_provider_original
from f139.nci04_owner_ledger import frozen_native_issue

KIND = "NATIVE_NEGATIVE_CUSTODIED"
SCHEMA = "forge.f139.nci04.owner-negative-custody.v1"
OWNER_HEAD = "75b24554b43cf1ea807810d9d98bd28a3f2c08585f8a9b811ae62f0c2ad74c4b"
SOURCE_SHA = "5662e3586bc9d12c90033b7c0344ca65ea1ad2a0"
TICKET = "f139-nci04-i696-5662e3586bc9-7bb8f27f"
RUN_ID = 39571372972
ARTIFACT_ID = 12332695987
ARTIFACT_SHA = "2092c9dae526689a4b8ac4392b3b053dd088beb4b83b29ba09ac730aeef63c06"
FIELDS = frozenset({
    "schema","ticket","source_sha","run_id","provider_artifact_id",
    "provider_artifact_sha256","provider_zip_bytes","native_report_sha256",
    "prior_event_head_sha256","quarantine_reason","negative_only",
    "original_owner_durable_custody","scientific_first_use",
    "successor_source_transition_authorized",
})


class OwnerNegativeCustodyDenied(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise OwnerNegativeCustodyDenied("F139_NCI04_A8B_" + reason)


def _paths(db, ticket: str, run_id: int):
    require(ticket == TICKET and run_id == RUN_ID, "ORIGINAL_TICKET_MISMATCH")
    root = Path(db.filename).resolve().parent
    directory = root / "native-negative" / ticket / str(run_id)
    original = directory / "ubuntu-latest.zip"
    return root, directory, original


def _check_dir(root: Path, directory: Path, *, create: bool):
    require(root.is_dir() and not root.is_symlink(), "OWNER_ROOT_INVALID")
    current = root
    for name in ("native-negative", TICKET, str(RUN_ID)):
        current = current / name
        if create:
            current.mkdir(exist_ok=True)
        require(current.is_dir() and not current.is_symlink(),
                "CUSTODY_DIRECTORY_SYMLINK_OR_MISSING")
    require(current == directory, "CUSTODY_ROOT_MISMATCH")


def _durable_zip(db, ticket: str, run_id: int, archive: bytes):
    """Fail closed on partial previous writes and non-identical recovery.

    Filesystem write completes and is flushed *before* the SQLite append;
    a crash between those stages leaves a bounded, byte-identical orphan that
    can be reconciled on the authorized original task, never rerun.
    """
    root, directory, original = _paths(db, ticket, run_id)
    _check_dir(root, directory, create=True)
    require(type(archive) is bytes and 0 < len(archive) <= 2_000_000,
            "ORIGINAL_ZIP_INVALID")
    if original.exists() or original.is_symlink():
        require(original.is_file() and not original.is_symlink()
                and original.read_bytes() == archive,
                "ORIGINAL_ZIP_CONFLICT")
        return original
    partial = directory / "ubuntu-latest.zip.partial"
    require(not partial.exists() and not partial.is_symlink(),
            "PARTIAL_ORIGINAL_NEEDS_REVIEW")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(partial), flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(archive)
        handle.flush()
        os.fsync(handle.fileno())
    require(partial.read_bytes() == archive and not partial.is_symlink(),
            "ORIGINAL_TEMP_BYTES_DRIFT")
    os.replace(str(partial), str(original))
    require(original.is_file() and not original.is_symlink()
            and original.read_bytes() == archive, "ORIGINAL_ATOMIC_RENAME_FAILED")
    if os.name != "nt":
        dfd = os.open(str(directory), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    return original


def _event_records(db):
    return list(db.conn.execute(
        "SELECT seq, prior_sha, payload FROM events WHERE kind=? ORDER BY seq",
        (KIND,)))


def verify_original_negative_custody(db):
    """Executed on EVERY Database.verify, including cold process restart.

    Immutable event + byte-for-byte original artifact identity is mandatory.
    This does not authorize a native successor or classify a failed task PASS.
    """
    import json
    events = _event_records(db)
    require(len(events) <= 1, "DUPLICATE_CUSTODY_EVENT")
    if not events:
        return False
    row = events[0]
    doc = json.loads(row["payload"])
    require(row["seq"] == 48 and row["prior_sha"] == OWNER_HEAD
            and isinstance(doc, dict) and set(doc) == FIELDS
            and doc["schema"] == SCHEMA
            and doc["ticket"] == TICKET and doc["source_sha"] == SOURCE_SHA
            and type(doc["run_id"]) is int and doc["run_id"] == RUN_ID
            and type(doc["provider_artifact_id"]) is int
            and doc["provider_artifact_id"] == ARTIFACT_ID
            and doc["provider_artifact_sha256"] == ARTIFACT_SHA
            and type(doc["provider_zip_bytes"]) is int
            and 0 < doc["provider_zip_bytes"] <= 2_000_000
            and isinstance(doc["native_report_sha256"], str)
            and re.fullmatch(r"[a-f0-9]{64}",doc["native_report_sha256"])
            and doc["prior_event_head_sha256"] == OWNER_HEAD
            and doc["negative_only"] is True
            and doc["original_owner_durable_custody"] is True
            and doc["scientific_first_use"] is False
            and doc["successor_source_transition_authorized"] is False,
            "NEGATIVE_EVENT_AUTHORITY_DRIFT")
    task = db.conn.execute(
        "SELECT stage,source_sha,run_id,evidence_dir,evidence_sha,"
        "quarantine_reason FROM tasks WHERE ticket=?", (TICKET,)).fetchone()
    require(task is not None and task["stage"] == "QUARANTINED"
            and task["source_sha"] == SOURCE_SHA
            and task["run_id"] is None and task["evidence_sha"] is None
            and not task["evidence_dir"]
            and isinstance(task["quarantine_reason"], str)
            and task["quarantine_reason"] == doc["quarantine_reason"]
            and doc["quarantine_reason"] == "FAILED_OR_CANCELLED_NO_REPLAY",
            "ORIGINAL_TASK_QUARANTINE_DRIFT")
    root, directory, original = _paths(db, TICKET, RUN_ID)
    _check_dir(root, directory, create=False)
    require(original.is_file() and not original.is_symlink()
            and original.stat().st_size == doc["provider_zip_bytes"]
            and digest(original.read_bytes()) == ARTIFACT_SHA,
            "ORIGINAL_ZIP_CUSTODY_TAMPERED")
    return True


def admit_original_negative_custody(db, *, run, jobs, artifact, archive,
                                    owner_hmac_key: str, epoch: int):
    """Owner-SingleOwner-only call on original qualified source and 47 head.

    Caller must independently authenticate provider GET results and hold the
    original owner mutex. Negative ZIP is saved BEFORE the append-only event.
    No replay of a provider job is performed.
    """
    db.verify()
    meta = db.meta()
    require(meta["source_sha"] == SOURCE_SHA
            and meta["head_seq"] == 47 and meta["head_hash"] == OWNER_HEAD
            and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
            and not _event_records(db), "OWNER_47_EVENT_HEAD_OR_STATE_DRIFT")
    task = db.conn.execute("SELECT * FROM tasks WHERE ticket=?", (TICKET,)).fetchone()
    require(task is not None and task["stage"] == "QUARANTINED"
            and task["source_sha"] == SOURCE_SHA
            and task["run_id"] is None and not task["evidence_dir"]
            and task["evidence_sha"] is None
            and task["quarantine_reason"] == "FAILED_OR_CANCELLED_NO_REPLAY",
            "UNRECOGNIZED_ORIGINAL_NEGATIVE")
    issue = frozen_native_issue(db, TICKET)
    certificate = verified_negative_provider_original(
        run=run, jobs=jobs, artifact=artifact, archive=archive,
        task=dict(task), issue=issue,
        owner_hmac_key=owner_hmac_key, epoch=epoch)
    require(certificate["ticket"] == TICKET
            and certificate["source_sha"] == SOURCE_SHA
            and certificate["run_id"] == RUN_ID
            and certificate["provider_artifact_id"] == ARTIFACT_ID
            and certificate["provider_artifact_sha256"] == ARTIFACT_SHA
            and certificate["native_qualified"] is False
            and certificate["original_owner_durable_custody"] is False,
            "ORIGINAL_PROVIDER_CERTIFICATE_DRIFT")
    _durable_zip(db, TICKET, RUN_ID, archive)
    event = {
        "schema": SCHEMA, "ticket":TICKET, "source_sha": SOURCE_SHA,
        "run_id": RUN_ID, "provider_artifact_id": ARTIFACT_ID,
        "provider_artifact_sha256": ARTIFACT_SHA,
        "provider_zip_bytes": len(archive),
        "native_report_sha256": certificate["native_report_sha256"],
        "prior_event_head_sha256": OWNER_HEAD,
        "quarantine_reason": task["quarantine_reason"],
        "negative_only": True, "original_owner_durable_custody": True,
        "scientific_first_use": False,
        "successor_source_transition_authorized": False,
    }
    with db.transaction():
        db.verify()
        require(db.meta()["head_hash"] == OWNER_HEAD
                and not _event_records(db), "NEGATIVE_CUSTODY_CONCURRENT_CHANGE")
        db.event(KIND, event)
        db.verify()
    return {
        "original_negative_custody": "PASS",
        "event_head_sha256": db.meta()["head_hash"],
        "original_zip_sha256": ARTIFACT_SHA,
        "run_id":RUN_ID, "task_stage":"QUARANTINED",
        "scientific_first_use":False,
        "successor_source_transition_authorized":False,
    }
