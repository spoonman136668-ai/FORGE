"""R11 original G54 #989 negative custody: one observed ambiguous start, never replay.

Historical G54 already appended the original ATTEMPT_QUARANTINED event on
the user's Windows SQLite under its sole owner mutex. This module reads that
immutable event and exact task. It MUST NOT append a second quarantine or
convert missing provider evidence into a fabricated terminal receipt.
"""
from __future__ import annotations

import json
import re

TICKET = "f139-nci04-i989-e49569d4a8b7-58834924"
SOURCE_SHA = "e49569d4a8b74aa5d854caafa92abcdbcf15bc39"
STARTED_AT = "2026-10-26T09:27:19.277942Z"
REASON = "AMBIGUOUS_START_NO_PROVIDER_RUN"
EVENT_SEQ = 243
EVENT_SHA256 = "13ef039dd0ef1256bb944bff78532c6c7d86fab4b9fb8f4bfb3e2b809ebc3d54"


class G54AmbiguousCustodyDenied(ValueError):
    pass


def need(valid: bool, reason: str) -> None:
    if not valid:
        raise G54AmbiguousCustodyDenied("F139_G54_AMBIGUOUS_" + reason)


def verified_g54_ambiguous_start(db, *, through_seq: int | None = None) -> dict:
    """Return the single source-bound negative without mutating any owner state.

    The historical event is part of the ORIGINAL hash chain; the caller must
    also run Database.verify() at its top-level entry. Do not call it from here
    because Database.verify uses this historical proof to validate V11 events.
    """
    from f139.local_controller import Database
    from f139.nci04_owner_ledger import frozen_native_issue

    need(type(db) is Database, "CANONICAL_DATABASE_REQUIRED")
    need(through_seq is None or
         (type(through_seq) is int and through_seq > EVENT_SEQ),
         "HISTORICAL_BOUNDARY_INVALID")
    event = db.conn.execute(
        "SELECT seq,sha,kind,payload FROM events WHERE seq=?",
        (EVENT_SEQ,)).fetchone()
    need(event is not None
         and event["seq"] == EVENT_SEQ
         and event["sha"] == EVENT_SHA256
         and event["kind"] == "ATTEMPT_QUARANTINED"
         and json.loads(event["payload"]) ==
             {"ticket": TICKET, "reason": REASON},
         "ORIGINAL_EVENT_NOT_EXACT")
    repeats = list(db.conn.execute(
        "SELECT seq,payload FROM events WHERE kind='ATTEMPT_QUARANTINED'"
    ))
    matches = [x for x in repeats
               if json.loads(x["payload"]).get("ticket") == TICKET]
    need(len(matches) == 1 and matches[0]["seq"] == EVENT_SEQ,
         "ORIGINAL_NEGATIVE_REPLAYED")
    task = db.conn.execute(
        "SELECT ticket,lane,stage,source_sha,started_at,run_id,"
        "evidence_dir,evidence_sha,quarantine_reason FROM tasks WHERE ticket=?",
        (TICKET,)).fetchone()
    need(task is not None
         and task["ticket"] == TICKET
         and task["lane"] == "Yggdrasil"
         and task["stage"] == "QUARANTINED"
         and task["source_sha"] == SOURCE_SHA
         and task["started_at"] == STARTED_AT
         and task["run_id"] is None
         and not task["evidence_dir"]
         and task["evidence_sha"] is None
         and task["quarantine_reason"] == REASON,
         "ORIGINAL_TASK_NOT_FROZEN")
    original = frozen_native_issue(db, TICKET)
    need(original.number == 989
         and original.ticket == TICKET
         and original.lane == "Yggdrasil"
         and original.source_sha == SOURCE_SHA
         and isinstance(original.issue_id, int)
         and original.issue_id > 0,
         "OWNER_ADMISSION_NOT_AUTHENTICATED")
    return {
        "schema": "forge.f139.g54.original-ambiguous-start-negative.v1",
        "ticket": TICKET,
        "source_sha": SOURCE_SHA,
        "quarantine_event_seq": EVENT_SEQ,
        "quarantine_event_sha256": EVENT_SHA256,
        "provider_run_id": None,
        "provider_receipt_authorized": False,
        "replay_authorized": False,
        "scientific_first_use": False,
    }
