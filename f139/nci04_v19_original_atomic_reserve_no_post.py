"""V19 original-owner SQLite atomic research attempt reservation, NO POST.

NOT connected to original F139 run_once, schedule, free-model transport, or
GitHub write. A successful local reservation *spends* authentic native evidence
but does NOT authorize a request, worker dispatch, publication, or science.

Production activation requires a separate protected exact-source release and
a separately qualified single-POST operator, neither included here. No new
controller, no second ledger, no model credentials and no network imports.
"""
from __future__ import annotations

import datetime as dt
import json
from typing import Callable

from f139.local_controller import Database, SingleOwner
from f139.nci04_v19_original_attempt_schema import (
    KIND, SCHEMA, legacy_digest,
)
from f139.nci04_v19_original_legacy_attempt_readonly import (
    FREE, original_legacy_attempt_snapshot,
)
from f139.nci04_v19_original_terminal_witness import (
    project_original_native_terminal,
)
from f139.nci04_v19_research_renewal_shadow import (
    LANES, ShadowDenied, day_value, MAX_DAILY_TOTAL,
    MAX_DAILY_PER_LANE, MAX_ROLLING_30D_TOTAL,
    MAX_ROLLING_30D_PER_LANE,
)

RESULT_SCHEMA = "forge.f139.v19.original-atomic-no-post.v1"


def deny(code: str) -> None:
    raise ShadowDenied("F139_V19_ORIGINAL_ATOMIC_RESERVE_" + code)


def result(disposition: str, *, scope: str | None = None,
           original_event_seq: int | None = None,
           original_event_sha256: str | None = None) -> dict:
    """The SHA-chain reservation is NOT a provider POST authorization."""
    return {
        "schema": RESULT_SCHEMA,
        "disposition": disposition,
        "scope_sha256": scope,
        "original_request_attempt_event_seq": original_event_seq,
        "original_request_attempt_event_sha256": original_event_sha256,
        "original_owner_request_authorized": False,
        "provider_requests": 0, "paid_model_calls": 0,
        "worker_dispatched": False, "scientific_first_use": False,
        "accepted_ref_mutations": 0,
        "original_controller_entrypoint_changed": False,
    }


def original_attempts(db: Database) -> list[dict]:
    """Read previous attempts only AFTER complete original DB cold verify.

    Do not substitute caller-provided, in-memory, shadow or foreign-ledger
    histories. The same verified event records are used for cold verification.
    """
    history = []
    for row in db.conn.execute(
        "SELECT payload FROM events WHERE kind=? ORDER BY seq", (KIND,)):
        payload = json.loads(row["payload"])
        history.append({
            "day": payload["utc_day"], "lane": payload["lane"],
            "ticket": payload["terminal_ticket"],
            "terminal_seq": payload["terminal_event_seq"],
            "scope_sha256": payload["scope_sha256"],
        })
    return history


def combined_budget(db: Database, attempts: list[dict], lane: str,
                    utc_day: str) -> bool:
    """True only if genuine original FREE and V19 history leave one slot."""
    today = day_value(utc_day)
    consumed = []
    for row in db.conn.execute(
        "SELECT payload FROM events WHERE kind=? ORDER BY seq", (FREE,)):
        p = json.loads(row["payload"])
        date = day_value(p["utc_day"])
        if date > today:
            deny("OLD_ORIGINAL_CLOCK_AHEAD")
        consumed.append((date, p["lane"]))
    for a in attempts:
        date = day_value(a["day"])
        if date > today:
            deny("PREVIOUS_V19_CLOCK_AHEAD")
        consumed.append((date, a["lane"]))
    daily = [l for d, l in consumed if d == today]
    recent = [l for d, l in consumed
              if dt.timedelta(0) <= today - d < dt.timedelta(days=30)]
    return (len(daily) < MAX_DAILY_TOTAL
            and daily.count(lane) < MAX_DAILY_PER_LANE
            and len(recent) < MAX_ROLLING_30D_TOTAL
            and recent.count(lane) < MAX_ROLLING_30D_PER_LANE)


def reserve_original_intent_without_post(
    db: Database, *, lane: str, utc_day: str,
    owner_witness: Callable[[], bool],
    fault_after_append: bool = False,
) -> dict:
    """Atomic owner-only original SQLite event append, no external POST.

    This function is NOT an F139 tick path and should not be invoked on a
    deployed original owner by a source-only draft. Independent release/cutover
    and a distinct credential-gated provider function remain absent.
    A fault after append rolls the entire original SHA chain back.
    """
    if type(db) is not Database or lane not in LANES:
        deny("ORIGINAL_DB_OR_LANE")
    if not SingleOwner.held(db.filename.with_suffix(".lock")):
        deny("ORIGINAL_SINGLE_OWNER_MUTEX_NOT_HELD")
    if not callable(owner_witness) or owner_witness() is not True:
        deny("ORIGINAL_OWNER_WITNESS_NOT_ATTESTED")
    if type(fault_after_append) is not bool:
        deny("FAULT_MODE_INVALID")
    day_value(utc_day)

    # One, and only one, original SQLite BEGIN IMMEDIATE transaction. All
    # original evidence, history, scope and quota checks happen while held.
    # The outer SingleOwner belongs to the existing F139 controller.
    with db.transaction():
        db.verify()
        meta = db.meta()
        if (meta["enabled"] != 1 or meta["legacy_suspended"] != 1
                or db.ready() is not None or db.actives()):
            return result("BLOCKED_ORIGINAL_OWNER_DISABLED_OR_BUSY")
        previous = original_attempts(db)
        legacy = original_legacy_attempt_snapshot(db)
        if legacy["original_unresolved_draft_attempts"]:
            return result("BLOCKED_ORIGINAL_DRAFT_PUBLICATION_AMBIGUOUS")
        witness = project_original_native_terminal(
            db, lane=lane, utc_day=utc_day,
            hypothetical_v19_attempts=previous)
        if witness["disposition"] != (
                "AUTHENTIC_FRESH_TERMINAL_SHADOW_ONLY_NOT_AUTHORIZED"):
            return result(witness["disposition"])
        shadow = witness["shadow"]
        scope = shadow["scope_sha256"]
        if shadow["disposition"] != "ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED":
            return result(shadow["disposition"], scope=scope)
        if not combined_budget(db, previous, lane, utc_day):
            return result("BLOCKED_COMBINED_ORIGINAL_AND_V19_BUDGET",
                          scope=scope)
        seq = witness["terminal_event_seq"]
        terminal = db.conn.execute(
            "SELECT seq,payload,sha FROM events "
            "WHERE seq=? AND kind='PROVIDER_VERIFIED_TERMINAL'",
            (seq,)).fetchone()
        if terminal is None:
            deny("TERMINAL_EVENT_DISAPPEARED")
        terminal_doc = json.loads(terminal["payload"])
        admission = db.conn.execute(
            "SELECT payload FROM events "
            "WHERE kind='NATIVE_DEVELOPMENT_ADMITTED' "
            "ORDER BY seq DESC").fetchall()
        native = None
        for record in admission:
            data = json.loads(record["payload"])
            if data.get("ticket") == terminal_doc["ticket"]:
                native = data
                break
        if native is None or native.get("lane") != lane:
            deny("NATIVE_ADMISSION_LOST")
        if (legacy["original_event_head_sha256"] != meta["head_hash"]
                or legacy["owner_source_sha"] != meta["source_sha"]):
            deny("LEGACY_HISTORY_OR_OWNER_SOURCE_MOVED")
        events = [dict(r) for r in db.conn.execute(
            "SELECT seq,kind,sha FROM events ORDER BY seq")]
        old_head = db.meta()
        if (old_head != meta
                or owner_witness() is not True
                or not SingleOwner.held(db.filename.with_suffix(".lock"))):
            deny("ORIGINAL_OWNER_CHANGED_PRE_APPEND")
        packet = {
            "schema": SCHEMA, "owner_source_sha": meta["source_sha"],
            "lane": lane, "terminal_ticket": terminal_doc["ticket"],
            "terminal_event_seq": seq,
            "terminal_event_sha256": terminal["sha"],
            "terminal_evidence_sha256": terminal_doc["evidence_sha"],
            "target_commit": native["native_target_commit"],
            "native_path": native["native_path"],
            "scope_sha256": scope,
            "original_legacy_history_sha256": legacy_digest(events),
            "utc_day": utc_day,
            "prior_event_head_sha256": old_head["head_hash"],
            "retry_allowed": False, "request_intent_committed": True,
            "paid_model_calls": 0, "worker_dispatched": False,
            "scientific_first_use": False,
        }
        db.event(KIND, packet)
        # Validate the new event on the same original cold verifier BEFORE
        # COMMIT. Any error, including injected power-loss equivalent, rolls
        # back both original events and meta head atomically.
        db.verify()
        if fault_after_append:
            deny("INJECTED_AFTER_APPEND_PRECOMMIT_ROLLBACK")
        appended = db.conn.execute(
            "SELECT seq,sha FROM events WHERE seq=? AND kind=?",
            (old_head["head_seq"] + 1, KIND)).fetchone()
        if (appended is None or db.meta()["head_hash"] != appended["sha"]
                or owner_witness() is not True):
            deny("PRECOMMIT_OWNER_OR_SHA_CHANGED")
        return result("ORIGINAL_ATOMIC_INTENT_COMMITTED_NO_POST",
                      scope=scope, original_event_seq=appended["seq"],
                      original_event_sha256=appended["sha"])
