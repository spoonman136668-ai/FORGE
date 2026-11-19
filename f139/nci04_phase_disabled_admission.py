"""Development-only atomic mode admission on a disposable F139 SQLite fixture.

This is NOT the original running owner's mode writer. The only accepted
destination is a newly created, disabled, task-empty database under the OS
temporary directory, with the existing SingleOwner kernel mutex held. A live
F139 database is unconditionally rejected. No remote fetch, no dispatch, no
training, no source mutation, no new controller or scheduler.
"""
from __future__ import annotations

from pathlib import Path
import re
import tempfile

from f139.nci04_phase_manual_intent import inspect_comment, ManualPhaseDenied
from f139.nci04_phase_mode_replay import (
    KIND, SCHEMA, read_original_owner_mode, ModeReplayDenied,
)

SHA64 = re.compile(r"[a-f0-9]{64}\Z")
MAX_PHASE_EVENTS = 128


class DevelopmentAdmissionDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise DevelopmentAdmissionDenied("F139_PHASE_DEV_ADMISSION_" + reason)


def _disposable(db) -> bool:
    """Require an explicitly named direct child fixture of an OS temp folder."""
    from f139.local_controller import Database, SingleOwner
    if type(db) is not Database:
        return False
    path = Path(db.filename)
    try:
        actual = path.resolve(strict=True)
        root = Path(tempfile.gettempdir()).resolve(strict=True)
    except OSError:
        return False
    if (actual.parent.parent != root or
            not actual.parent.name.startswith("f139-phase-dev-") or
            actual.name != "disabled.sqlite" or
            not actual.is_file()):
        return False
    return SingleOwner.held(path.with_suffix(".lock"))


def _idle_disabled(db) -> bool:
    meta = db.meta()
    return (meta["enabled"] == 0 and meta["legacy_suspended"] == 0
            and db.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0)


def admit_disposable_intent(*, db, comment: dict,
                            installed_source_sha: str,
                            protected_main_sha: str, owner_epoch: int,
                            expected_head_sha256: str) -> dict:
    """Commit one source/epoch and expected-head-bound event to fixture SQLite.

    `comment` is synthetic or caller-supplied GitHub-shaped data. This test
    adapter does NOT independently authenticate GitHub or original-owner SID.
    Even a successful fixture commit is never a runtime authorization.
    """
    need(_disposable(db), "EXISTING_SINGLE_OWNER_DISPOSABLE_REQUIRED")
    need(type(expected_head_sha256) is str
         and SHA64.fullmatch(expected_head_sha256) is not None,
         "EXPECTED_HEAD_INVALID")
    db.verify()
    before = db.meta()
    need(_idle_disabled(db)
         and before["source_sha"] == installed_source_sha
         and installed_source_sha == protected_main_sha
         and type(owner_epoch) is int and before["epoch"] == owner_epoch
         and before["head_hash"] == expected_head_sha256,
         "SOURCE_OR_HEAD_DRIFT_OR_OWNER_NOT_DISABLED")
    old = read_original_owner_mode(
        db=db, installed_source_sha=installed_source_sha,
        protected_main_sha=protected_main_sha, owner_epoch=owner_epoch)
    need(len(old["consumed_comment_ids"]) < MAX_PHASE_EVENTS,
         "MODE_BUDGET_EXHAUSTED")
    try:
        candidate = inspect_comment(
            comment=comment, installed_source_sha=installed_source_sha,
            protected_main_sha=protected_main_sha, owner_epoch=owner_epoch,
            consumed_comment_ids=old["consumed_comment_ids"])
    except ManualPhaseDenied as exc:
        raise DevelopmentAdmissionDenied("F139_PHASE_DEV_ADMISSION_REQUEST_INVALID") from exc
    payload = {
        "schema": SCHEMA, "source_sha": installed_source_sha,
        "owner_epoch": owner_epoch, "comment_id": candidate["comment_id"],
        "body_sha256": candidate["body_sha256"],
        "mode": candidate["mode"], "lane": candidate["lane"],
        "prior_event_head_sha256": expected_head_sha256,
        "scientific_first_use": False, "dispatch_authorized": False,
        "self_source_mutation": False, "checkpoint_mutation": False,
        "accepted_ref_mutation": False,
    }
    with db.transaction():
        db.verify()
        current = db.meta()
        need(_disposable(db) and _idle_disabled(db)
             and current == before
             and current["head_hash"] == expected_head_sha256,
             "CONCURRENT_SOURCE_OR_HEAD_DRIFT")
        # Defensive readback inside the SAME BEGIN IMMEDIATE transaction.
        now = read_original_owner_mode(
            db=db, installed_source_sha=installed_source_sha,
            protected_main_sha=protected_main_sha, owner_epoch=owner_epoch)
        need(now["consumed_comment_ids"] == old["consumed_comment_ids"]
             and now["last_mode_event_seq"] == old["last_mode_event_seq"],
             "CONCURRENT_MODE_HISTORY_DRIFT")
        db.event(KIND, payload)
        db.verify()
        committed = read_original_owner_mode(
            db=db, installed_source_sha=installed_source_sha,
            protected_main_sha=protected_main_sha, owner_epoch=owner_epoch)
        need(committed["last_comment_id"] == candidate["comment_id"]
             and committed["mode"] == candidate["mode"]
             and committed["lane"] == candidate["lane"]
             and len(committed["consumed_comment_ids"]) ==
                 len(old["consumed_comment_ids"]) + 1,
             "ATOMIC_COMMIT_READBACK_INVALID")
        final = db.meta()
    return {
        "schema": "forge.f139.phase-mode-disabled-rehearsal.v1",
        "source_sha": installed_source_sha, "owner_epoch": owner_epoch,
        "event_seq": final["head_seq"], "event_head_sha256": final["head_hash"],
        "mode": committed["mode"], "lane": committed["lane"],
        "comment_id": committed["last_comment_id"],
        "disposable_only": True, "owner_live_updated": False,
        "development_only": True, "dispatch_authorized": False,
        "scientific_first_use": False, "self_source_mutation": False,
        "checkpoint_mutation": False, "accepted_ref_mutation": False,
    }
