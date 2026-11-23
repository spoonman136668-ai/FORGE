"""A8E2A2: exact original #706 split-provider ZIP custody, owner-only.

This module does not expose a CLI, dispatch a workflow, change a task stage or
authorize source transition. Callers must independently GET the original
GitHub run/jobs/artifact and hold the original owner SingleOwner mutex.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re

from f139.nci04_native_contract import digest
from f139.nci04_owner_ledger import frozen_native_issue
from f139.nci04_negative_owner_store import verify_original_negative_custody
from f139.nci04_split_negative_custody import (
    ARTIFACT_BYTES, ARTIFACT_ID, ARTIFACT_SHA256,
    OWNER_HEAD_55, RUN_ID, SOURCE, TICKET,
    verify_706_split_provider_original,
)

KIND = "NATIVE_SPLIT_NEGATIVE_CUSTODIED"
SCHEMA = "forge.f139.nci04.owner-split-negative-custody.v1"
FIELDS = frozenset({
    "schema", "ticket", "source_sha", "run_id",
    "provider_artifact_id", "provider_artifact_sha256", "provider_zip_bytes",
    "issue_body_sha256", "native_intent_sha256",
    "prior_event_head_sha256", "original_55_event_sha256",
    "quarantine_reason", "ubuntu_native_qualified",
    "windows_python_setup_failed", "whole_run_qualified",
    "original_owner_durable_custody", "scientific_first_use",
    "successor_source_transition_authorized",
})
REASON = re.compile(r"[A-Z_]{3,72}\Z")


class SplitOwnerCustodyDenied(ValueError):
    pass


def require(ok: bool, reason: str):
    if not ok:
        raise SplitOwnerCustodyDenied("F139_A8E2A2_" + reason)


def paths(db):
    root = Path(db.filename).resolve().parent
    directory = root / "native-negative" / TICKET / str(RUN_ID)
    return root, directory, directory / "ubuntu-latest.zip"


def check_path(root: Path, directory: Path, *, create: bool):
    require(root.is_dir() and not root.is_symlink(), "OWNER_ROOT_INVALID")
    current = root
    for component in ("native-negative", TICKET, str(RUN_ID)):
        current = current / component
        if create:
            current.mkdir(exist_ok=True)
        require(current.is_dir() and not current.is_symlink(),
                "CUSTODY_DIRECTORY_INVALID")
    require(current == directory, "CUSTODY_PATH_DRIFT")


def write_original_zip(db, archive: bytes):
    """Store exactly original provider bytes before appending the SQL event.

    A durable pre-event orphan is recoverable *only* if its bytes match the
    authenticated original archive; a leftover partial fails closed.
    """
    require(type(archive) is bytes and len(archive) == ARTIFACT_BYTES
            and digest(archive) == ARTIFACT_SHA256, "ORIGINAL_ZIP_IDENTITY")
    root, directory, original = paths(db)
    check_path(root, directory, create=True)
    if original.exists() or original.is_symlink():
        require(original.is_file() and not original.is_symlink()
                and original.read_bytes() == archive,
                "EXISTING_ORIGINAL_ZIP_CONFLICT")
        return original
    partial = directory / "ubuntu-latest.zip.partial"
    require(not partial.exists() and not partial.is_symlink(),
            "PARTIAL_ORIGINAL_REQUIRES_REVIEW")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(partial), flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(archive)
        handle.flush()
        os.fsync(handle.fileno())
    require(partial.is_file() and not partial.is_symlink()
            and partial.read_bytes() == archive, "PARTIAL_ORIGINAL_BYTES_DRIFT")
    os.replace(str(partial), str(original))
    require(original.is_file() and not original.is_symlink()
            and original.read_bytes() == archive, "ATOMIC_ORIGINAL_BYTES_DRIFT")
    if os.name != "nt":
        dfd = os.open(str(directory), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    return original


def records(db):
    return list(db.conn.execute(
        "SELECT seq,sha,prior_sha,payload FROM events WHERE kind=? ORDER BY seq",
        (KIND,)))


def original_frozen(db):
    meta = db.meta()
    require(meta["source_sha"] == SOURCE and meta["enabled"] == 1
            and meta["legacy_suspended"] == 1
            and meta["head_seq"] == 55 and meta["head_hash"] == OWNER_HEAD_55,
            "ORIGINAL_55_HEAD_OR_OWNER_DRIFT")
    require(verify_original_negative_custody(db),
            "FIRST_NEGATIVE_CUSTODY_MISSING")
    require(not records(db), "SECOND_CUSTODY_ALREADY_APPENDED")
    row = db.conn.execute(
        "SELECT * FROM tasks WHERE ticket=?", (TICKET,)).fetchone()
    require(row is not None and row["stage"] == "QUARANTINED"
            and row["source_sha"] == SOURCE
            and row["run_id"] is None and row["evidence_sha"] is None
            and not row["evidence_dir"]
            and isinstance(row["quarantine_reason"], str)
            and REASON.fullmatch(row["quarantine_reason"]) is not None,
            "ORIGINAL_TASK_DRIFT")
    ev = db.conn.execute(
        "SELECT seq,kind,payload,sha FROM events WHERE seq=55").fetchone()
    require(ev is not None and ev["kind"] == "ATTEMPT_QUARANTINED"
            and ev["sha"] == OWNER_HEAD_55
            and json.loads(ev["payload"]) ==
                {"ticket": TICKET, "reason": row["quarantine_reason"]},
            "ORIGINAL_EVENT_55_DRIFT")
    return dict(row), {
        "seq": ev["seq"], "kind": ev["kind"],
        "payload": json.loads(ev["payload"]), "sha": ev["sha"],
    }


def verify_second_negative_custody(db) -> bool:
    """Cold-read check to be wired into Database.verify by A8E2A3.

    Never accepts a stale/forged event as source-transition authority.
    """
    rows = records(db)
    require(len(rows) <= 1, "DUPLICATE_SECOND_CUSTODY")
    if not rows:
        return False
    row = rows[0]
    doc = json.loads(row["payload"])
    require(row["seq"] == 56 and row["prior_sha"] == OWNER_HEAD_55
            and isinstance(doc, dict) and set(doc) == FIELDS
            and doc["schema"] == SCHEMA and doc["ticket"] == TICKET
            and doc["source_sha"] == SOURCE and doc["run_id"] == RUN_ID
            and doc["provider_artifact_id"] == ARTIFACT_ID
            and doc["provider_artifact_sha256"] == ARTIFACT_SHA256
            and doc["provider_zip_bytes"] == ARTIFACT_BYTES
            and doc["prior_event_head_sha256"] == OWNER_HEAD_55
            and doc["original_55_event_sha256"] == OWNER_HEAD_55
            and doc["ubuntu_native_qualified"] is True
            and doc["windows_python_setup_failed"] is True
            and doc["whole_run_qualified"] is False
            and doc["original_owner_durable_custody"] is True
            and doc["scientific_first_use"] is False
            and doc["successor_source_transition_authorized"] is False,
            "SECOND_CUSTODY_EVENT_DRIFT")
    issue = frozen_native_issue(db, TICKET)
    task = db.conn.execute(
        "SELECT * FROM tasks WHERE ticket=?", (TICKET,)).fetchone()
    original_event = db.conn.execute(
        "SELECT kind,payload,sha FROM events WHERE seq=55").fetchone()
    require(task is not None and task["stage"] == "QUARANTINED"
            and task["source_sha"] == SOURCE and task["run_id"] is None
            and task["evidence_sha"] is None and not task["evidence_dir"]
            and doc["quarantine_reason"] == task["quarantine_reason"]
            and REASON.fullmatch(doc["quarantine_reason"]) is not None
            and original_event is not None
            and original_event["kind"] == "ATTEMPT_QUARANTINED"
            and original_event["sha"] == OWNER_HEAD_55
            and json.loads(original_event["payload"]) ==
                {"ticket": TICKET, "reason": doc["quarantine_reason"]}
            and doc["issue_body_sha256"] == issue.issue_body_sha256
            and doc["native_intent_sha256"] == issue.native_intent_sha256,
            "SECOND_CUSTODY_OWNER_IDENTITY_DRIFT")
    require(verify_original_negative_custody(db),
            "FIRST_NEGATIVE_LOST")
    root, directory, original = paths(db)
    check_path(root, directory, create=False)
    require(original.is_file() and not original.is_symlink()
            and original.stat().st_size == ARTIFACT_BYTES
            and digest(original.read_bytes()) == ARTIFACT_SHA256,
            "SECOND_CUSTODY_ZIP_TAMPERED")
    return True


def admit_second_negative_custody(db, *, run: dict, jobs: list[dict],
                                  artifacts: list[dict], archive: bytes,
                                  owner_hmac_key: str, epoch: int) -> dict:
    """Append once under authenticated original SingleOwner lock, never replay.

    This source-only API is intentionally not exposed through an owner CLI.
    A8E2A3 must independently qualify and authorize any operational wiring.
    """
    db.verify()
    task, original_event = original_frozen(db)
    issue = frozen_native_issue(db, TICKET)
    certificate = verify_706_split_provider_original(
        run=run, jobs=jobs, artifacts=artifacts, archive=archive,
        task=task, quarantine_event=original_event,
        owner_head_sha256=OWNER_HEAD_55, issue=issue,
        owner_hmac_key=owner_hmac_key, epoch=epoch)
    require(certificate["whole_run_qualified"] is False
            and certificate["original_owner_durable_custody"] is False
            and certificate["successor_source_transition_authorized"] is False,
            "PROVIDER_CERTIFICATE_NOT_NEGATIVE")
    # File first, then one original-ledger event; never pretend that orphan
    # bytes alone qualify if the SQL transaction failed or was interrupted.
    write_original_zip(db, archive)
    event = {
        "schema": SCHEMA, "ticket": TICKET, "source_sha": SOURCE,
        "run_id": RUN_ID, "provider_artifact_id": ARTIFACT_ID,
        "provider_artifact_sha256": ARTIFACT_SHA256,
        "provider_zip_bytes": ARTIFACT_BYTES,
        "issue_body_sha256": issue.issue_body_sha256,
        "native_intent_sha256": issue.native_intent_sha256,
        "prior_event_head_sha256": OWNER_HEAD_55,
        "original_55_event_sha256": OWNER_HEAD_55,
        "quarantine_reason": task["quarantine_reason"],
        "ubuntu_native_qualified": True,
        "windows_python_setup_failed": True,
        "whole_run_qualified": False,
        "original_owner_durable_custody": True,
        "scientific_first_use": False,
        "successor_source_transition_authorized": False,
    }
    with db.transaction():
        db.verify()
        original_frozen(db)
        db.event(KIND, event)
        require(verify_second_negative_custody(db),
                "POST_APPEND_COLD_READ_FAILED")
        db.verify()
    return {
        "second_negative_custody": "PASS",
        "event_head_sha256": db.meta()["head_hash"],
        "original_run_id": RUN_ID,
        "original_zip_sha256": ARTIFACT_SHA256,
        "task_stage": "QUARANTINED",
        "scientific_first_use": False,
        "source_transition_authorized": False,
    }
