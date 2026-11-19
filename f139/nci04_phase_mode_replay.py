"""Strict cold projection of FUTURE F139 manual-mode admissions.

This source-only reader is not wired to the original owner, does not create
PHASE_MODE_ADMITTED events and cannot authorize writing or dispatch.
Database.verify() owns the complete SQLite SHA chain; this module validates
every phase event's typed payload even when it was not part of historic F139.
A stale source/epoch never silently returns AUTO or clears HOLD.
"""
from __future__ import annotations

import json
import re

from f139.nci04_phase_manual_intent import SCHEMA as INTENT_SCHEMA
from f139.nci04_phase_steering import LANES, MODES

KIND = "PHASE_MODE_ADMITTED"
SCHEMA = "forge.f139.phase-mode-admission.v1"
FIELDS = frozenset({
    "schema", "source_sha", "owner_epoch", "comment_id",
    "body_sha256", "mode", "lane", "prior_event_head_sha256",
    "scientific_first_use", "dispatch_authorized",
    "self_source_mutation", "checkpoint_mutation",
    "accepted_ref_mutation",
})
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
MAX_EVENTS = 100000


class ModeReplayDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise ModeReplayDenied("F139_PHASE_REPLAY_" + reason)


def project_verified_events(*, events: tuple[dict, ...],
                            current_source_sha: str,
                            current_epoch: int) -> dict:
    """Audit already-SHA-chain-verified phase events; recover latest mode.

    Caller must supply rows from original SQLite after Database.verify.
    Rows here are synthetic-capable for deterministic tests, not an
    authenticated substitute for the original owner or its mutex.
    """
    need(type(current_source_sha) is str
         and SHA40.fullmatch(current_source_sha) is not None
         and type(current_epoch) is int and 1 <= current_epoch < 2**31,
         "OWNER_IDENTITY_INVALID")
    need(type(events) is tuple and len(events) <= MAX_EVENTS,
         "EVENT_COUNT_INVALID")
    last_seq = 0
    used_comments = set()
    latest_mode, latest_lane = "AUTO", None
    last_comment = None
    for event in events:
        need(type(event) is dict and set(event) == {
            "seq", "prior_sha", "sha", "payload"}, "EVENT_SHAPE_INVALID")
        seq = event["seq"]
        payload = event["payload"]
        need(type(seq) is int and seq > last_seq
             and type(event["prior_sha"]) is str
             and SHA64.fullmatch(event["prior_sha"]) is not None
             and type(event["sha"]) is str
             and SHA64.fullmatch(event["sha"]) is not None
             and type(payload) is dict and set(payload) == FIELDS,
             "EVENT_SEQUENCE_OR_FIELDS_INVALID")
        need(payload["schema"] == SCHEMA
             and payload["source_sha"] == current_source_sha
             and type(payload["owner_epoch"]) is int
             and payload["owner_epoch"] == current_epoch
             and payload["prior_event_head_sha256"] == event["prior_sha"],
             "SOURCE_EPOCH_OR_PREVIOUS_HEAD_DRIFT")
        comment_id, body_hash = payload["comment_id"], payload["body_sha256"]
        need(type(comment_id) is int and comment_id > 0
             and comment_id not in used_comments
             and type(body_hash) is str
             and SHA64.fullmatch(body_hash) is not None,
             "COMMENT_REPLAY_OR_HASH_INVALID")
        mode, lane = payload["mode"], payload["lane"]
        need(type(mode) is str and mode in MODES
             and (lane is None or
                  (type(lane) is str and lane in LANES))
             and (mode not in ("HOLD", "SELF_IMPROVE") or lane is None),
             "MODE_OR_LANE_SCOPE_INVALID")
        need(all(payload[flag] is False for flag in (
            "scientific_first_use", "dispatch_authorized",
            "self_source_mutation", "checkpoint_mutation",
            "accepted_ref_mutation")), "PRIVILEGE_FIELD_INVALID")
        last_seq = seq
        used_comments.add(comment_id)
        latest_mode, latest_lane = mode, lane
        last_comment = comment_id
    return {
        "schema": "forge.f139.phase-mode-replay-preview.v1",
        "mode": latest_mode, "lane": latest_lane,
        "status": ("COLD_VERIFIED_MODE_HISTORY" if events else
                   "NO_PERSISTED_OVERRIDE_AUTO_DEFAULT"),
        "last_comment_id": last_comment,
        "consumed_comment_ids": frozenset(used_comments),
        "last_mode_event_seq": last_seq,
        "advisory_only": True,
        "dispatch_authorized": False,
        "scientific_first_use": False,
        "mode_writer_installed": False,
    }


def read_original_owner_mode(*, db, installed_source_sha: str,
                             protected_main_sha: str, owner_epoch: int) -> dict:
    """Observe verified original SQLite only. Never consume a remote comment."""
    from f139.local_controller import Database
    need(type(db) is Database, "ORIGINAL_DATABASE_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == installed_source_sha
         and installed_source_sha == protected_main_sha
         and meta["epoch"] == owner_epoch,
         "ORIGINAL_SOURCE_EPOCH_MISMATCH")
    rows = list(db.conn.execute(
        "SELECT seq, prior_sha, sha, payload FROM events "
        "WHERE kind=? ORDER BY seq", (KIND,)))
    need(len(rows) <= MAX_EVENTS, "EVENT_COUNT_INVALID")
    events = tuple({
        "seq": row["seq"], "prior_sha": row["prior_sha"],
        "sha": row["sha"], "payload": json.loads(row["payload"]),
    } for row in rows)
    # The core verify() already checked the complete ledger event hash chain
    # and canonical payload bytes. This projection additionally validates
    # the mode-event schema and replay uniqueness.
    return project_verified_events(
        events=events, current_source_sha=installed_source_sha,
        current_epoch=owner_epoch)


def gate_original_owner_new_admissions(*, db, db_path,
                                       protected_main_sha: str) -> dict:
    """Source-only original-owner *new-intake* gate, not a dispatch permit.

    Run only at the existing F139 idle intake boundary, after reconciling
    already active jobs. Accepts the already imported __main__.Database used
    by python -m (unlike read_original_owner_mode, whose canonical class
    identity is intentionally strict). Original lock, exact path and
    independently read protected main must match. No provider writes.
    """
    from pathlib import Path
    from f139.local_controller import SingleOwner

    try:
        actual = Path(db.filename).resolve(strict=True)
        expected = Path(db_path).resolve(strict=True)
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        raise ModeReplayDenied("F139_PHASE_REPLAY_OWNER_PATH_UNVERIFIED") from exc
    need(actual == expected
         and SingleOwner.held(expected.with_suffix(".lock")),
         "ORIGINAL_OWNER_LOCK_OR_PATH_MISMATCH")
    db.verify()
    meta = db.meta()
    need(type(protected_main_sha) is str
         and meta["source_sha"] == protected_main_sha,
         "PROTECTED_MAIN_SOURCE_DRIFT")
    rows = list(db.conn.execute(
        "SELECT seq,prior_sha,sha,payload FROM events "
        "WHERE kind=? ORDER BY seq", (KIND,)))
    need(len(rows) <= MAX_EVENTS, "EVENT_COUNT_INVALID")
    events = tuple({
        "seq": r["seq"], "prior_sha": r["prior_sha"],
        "sha": r["sha"], "payload": json.loads(r["payload"])
    } for r in rows)
    history = project_verified_events(
        events=events, current_source_sha=meta["source_sha"],
        current_epoch=meta["epoch"])
    mode, lane = history["mode"], history["lane"]
    # Only existing research development is currently implemented by F139.
    # HOLD stops new admissions, not reconciliation or already READY tasks.
    # TRAIN/SELF_IMPROVE and lane-pinned routing cannot be silently mapped to
    # old development feeder work. Their native permits/adapters do not exist.
    if mode == "HOLD":
        disposition = "PHASE_HOLD_NO_NEW_ADMISSIONS"
    elif mode in ("TRAIN", "SELF_IMPROVE"):
        disposition = "PHASE_EXECUTION_ADAPTER_NOT_QUALIFIED"
    elif lane is not None:
        disposition = "PHASE_LANE_SCOPING_NOT_QUALIFIED"
    else:
        disposition = "PHASE_EXISTING_RESEARCH_INTAKE"
    return {
        "schema": "forge.f139.owner-new-admission-mode-guard.v1",
        "mode": mode, "lane": lane, "disposition": disposition,
        "last_comment_id": history["last_comment_id"],
        "last_mode_event_seq": history["last_mode_event_seq"],
        "allow_existing_intake": disposition == "PHASE_EXISTING_RESEARCH_INTAKE",
        "original_owner_lock_verified": True,
        "advisory_only": True, "dispatch_authorized": False,
        "scientific_first_use": False, "self_source_mutation": False,
        "checkpoint_mutation": False, "accepted_ref_mutation": False,
    }
