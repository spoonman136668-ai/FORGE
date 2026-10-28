"""V19 atomic research-request reservation REHEARSAL, never a live writer.

The simulated append-only log can exist ONLY in anonymous in-memory SQLite,
not in the original owner's file. The original Database is read-only under the
existing SingleOwner lock. Successful simulation never permits a model request.
No controller tick imports this module, and it cannot dispatch work.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3

from f139.local_controller import Database, SingleOwner, canonical
from f139.nci04_v19_original_legacy_attempt_readonly import (
    FREE, original_legacy_attempt_snapshot,
)
from f139.nci04_v19_original_terminal_witness import (
    project_original_native_terminal,
)
from f139.nci04_v19_research_renewal_shadow import (
    ShadowDenied, LANES, day_value, is_sha64,
    MAX_DAILY_TOTAL, MAX_DAILY_PER_LANE,
    MAX_ROLLING_30D_TOTAL, MAX_ROLLING_30D_PER_LANE,
)

ZERO = "0" * 64
REHEARSAL = "forge.f139.v19.atomic-request-rehearsal.v1"
DDL = (
    "CREATE TABLE attempts (seq INTEGER PRIMARY KEY CHECK(seq>0), "
    "day TEXT NOT NULL, lane TEXT NOT NULL CHECK(lane IN "
    "('Wingless','Yggdrasil')), ticket TEXT NOT NULL UNIQUE, "
    "terminal_seq INTEGER NOT NULL CHECK(terminal_seq>0), "
    "scope_sha256 TEXT NOT NULL UNIQUE, original_head_sha256 TEXT NOT NULL, "
    "legacy_history_sha256 TEXT NOT NULL, prior_sha256 TEXT NOT NULL, "
    "event_sha256 TEXT NOT NULL UNIQUE)"
)
UPDATE_GUARD = (
    "CREATE TRIGGER deny_attempt_update BEFORE UPDATE ON attempts "
    "BEGIN SELECT RAISE(ABORT,'V19_REHEARSAL_APPEND_ONLY'); END"
)
DELETE_GUARD = (
    "CREATE TRIGGER deny_attempt_delete BEFORE DELETE ON attempts "
    "BEGIN SELECT RAISE(ABORT,'V19_REHEARSAL_APPEND_ONLY'); END"
)


def deny(reason: str) -> None:
    raise ShadowDenied("F139_V19_ATOMIC_REHEARSAL_" + reason)


def new_rehearsal():
    """A disposable memory-only simulation: NEVER a production second ledger."""
    con = sqlite3.connect(":memory:", isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute(DDL)
    con.execute(UPDATE_GUARD)
    con.execute(DELETE_GUARD)
    return con


def rows(con: sqlite3.Connection, original: Database) -> list[dict]:
    if type(con) is not sqlite3.Connection or con is original.conn:
        deny("WRONG_CONNECTION")
    dbs = con.execute("PRAGMA database_list").fetchall()
    if len(dbs) != 1 or dbs[0][1] != "main" or dbs[0][2] != "":
        deny("PERSISTENT_OR_ATTACHED_DATABASE_FORBIDDEN")
    expected = {"attempts": DDL, "deny_attempt_update": UPDATE_GUARD,
                "deny_attempt_delete": DELETE_GUARD}
    recorded = {r[0]: r[1] for r in con.execute(
        "SELECT name,sql FROM sqlite_master WHERE type IN ('table','trigger')")}
    if recorded != expected:
        deny("SCHEMA_OR_IMMUTABILITY_DRIFT")
    result = []
    previous = ZERO
    for record in con.execute("SELECT * FROM attempts ORDER BY seq"):
        d = dict(record)
        if (d["seq"] != len(result) + 1 or d["lane"] not in LANES
                or type(d["ticket"]) is not str
                or not is_sha64(d["scope_sha256"])
                or not is_sha64(d["original_head_sha256"])
                or not is_sha64(d["legacy_history_sha256"])
                or d["prior_sha256"] != previous
                or not is_sha64(d["event_sha256"])):
            deny("ATTEMPT_CHAIN_FIELDS")
        day_value(d["day"])
        body = {k: v for k, v in d.items() if k != "event_sha256"}
        current = hashlib.sha256(
            previous.encode("ascii") + canonical({"schema": REHEARSAL, **body})
        ).hexdigest()
        if current != d["event_sha256"]:
            deny("ATTEMPT_CHAIN_DIGEST")
        previous = current
        result.append(d)
    return result


def disposition(code: str, *, reserved: bool = False,
                scope_sha256: str | None = None, count: int = 0) -> dict:
    return {
        "schema": REHEARSAL, "disposition": code,
        "simulated_in_memory_reservation": reserved,
        "simulation_attempt_count": count,
        "scope_sha256": scope_sha256,
        "original_owner_request_authorized": False,
        "real_original_ledger_events_written": 0,
        "paid_model_calls": 0, "provider_requests": 0,
        "worker_dispatched": False, "scientific_first_use": False,
        "accepted_ref_mutations": 0,
    }


def reserve_simulated(owner: Database, simulated: sqlite3.Connection, *,
                      lane: str, utc_day: str,
                      abort_before_commit: bool = False) -> dict:
    """Rehearse one pre-POST atomic attempt, with ZERO POST/real ledger writes.

    Requires an independently verified original terminal newer than every
    legacy free/draft attempt, and rejects spent legacy source/terminal
    histories. The only mutation is the caller-created anonymous memory DB.
    """
    if type(owner) is not Database or lane not in LANES:
        deny("ORIGINAL_OWNER_OR_LANE_INVALID")
    if not SingleOwner.held(owner.filename.with_suffix(".lock")):
        deny("ORIGINAL_MUTEX_REQUIRED")
    today = day_value(utc_day)
    owner.verify()
    origin_before = owner.meta()
    if origin_before["enabled"] != 1 or origin_before["legacy_suspended"] != 1:
        deny("ORIGINAL_OWNER_DISABLED")
    if type(abort_before_commit) is not bool:
        deny("FAULT_FLAG_INVALID")
    # Reject a file-backed or original-owner connection BEFORE beginning any
    # SQLite transaction, even a temporary lock acquisition.
    rows(simulated, owner)
    # BEGIN IMMEDIATE serializes read, budget decision and insert in this
    # INERT MEMORY LAB. Production will require separately qualified original
    # SQLite event kind, cold verifier and real pre-POST owner transaction.
    try:
        simulated.execute("BEGIN IMMEDIATE")
        prior = rows(simulated, owner)
        attempts = [{
            "day": r["day"], "lane": r["lane"], "ticket": r["ticket"],
            "terminal_seq": r["terminal_seq"],
            "scope_sha256": r["scope_sha256"],
        } for r in prior]
        legacy = original_legacy_attempt_snapshot(owner)
        if legacy["original_unresolved_draft_attempts"]:
            simulated.execute("ROLLBACK")
            return disposition("BLOCKED_UNRESOLVED_ORIGINAL_MODEL_WRITE",
                               count=len(prior))
        witness = project_original_native_terminal(
            owner, lane=lane, utc_day=utc_day,
            hypothetical_v19_attempts=attempts)
        if witness["disposition"] != (
                "AUTHENTIC_FRESH_TERMINAL_SHADOW_ONLY_NOT_AUTHORIZED"):
            simulated.execute("ROLLBACK")
            return disposition(witness["disposition"], count=len(prior))
        shadow = witness["shadow"]
        scope = shadow["scope_sha256"]
        if shadow["disposition"] != "ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED":
            simulated.execute("ROLLBACK")
            return disposition(shadow["disposition"],
                               scope_sha256=scope, count=len(prior))
        # The old original free attempts remain budget-consuming, including
        # failures and ambiguous publications. Do not reset on V19 rollover.
        old_days = []
        for event in owner.conn.execute(
                "SELECT payload FROM events WHERE kind=? ORDER BY seq", (FREE,)):
            data = json.loads(event["payload"])
            day = day_value(data["utc_day"])
            if day > today:
                deny("ORIGINAL_CLOCK_ROLLBACK")
            old_days.append((day, data["lane"]))
        both = old_days + [(day_value(x["day"]), x["lane"]) for x in prior]
        today_attempts = [l for day, l in both if day == today]
        recent = [l for day, l in both
                  if dt.timedelta(0) <= today - day < dt.timedelta(days=30)]
        if (len(today_attempts) >= MAX_DAILY_TOTAL
                or today_attempts.count(lane) >= MAX_DAILY_PER_LANE
                or len(recent) >= MAX_ROLLING_30D_TOTAL
                or recent.count(lane) >= MAX_ROLLING_30D_PER_LANE):
            simulated.execute("ROLLBACK")
            return disposition("BLOCKED_COMBINED_ORIGINAL_AND_V19_BUDGET",
                               scope_sha256=scope, count=len(prior))
        seq = witness["terminal_event_seq"]
        event = owner.conn.execute(
            "SELECT payload FROM events WHERE seq=? "
            "AND kind='PROVIDER_VERIFIED_TERMINAL'", (seq,)).fetchone()
        if event is None:
            deny("TERMINAL_EVENT_VANISHED")
        terminal = json.loads(event["payload"])
        ticket = terminal["ticket"]
        if not ticket or not isinstance(ticket, str):
            deny("TERMINAL_TICKET_INVALID")
        owner.verify()
        if owner.meta() != origin_before:
            deny("ORIGINAL_CHANGED_DURING_RESERVATION")
        if legacy["original_event_head_sha256"] != origin_before["head_hash"]:
            deny("ORIGINAL_HISTORY_MOVED")
        predecessor = prior[-1]["event_sha256"] if prior else ZERO
        body = {
            "seq": len(prior) + 1, "day": utc_day,
            "lane": lane, "ticket": ticket, "terminal_seq": seq,
            "scope_sha256": scope,
            "original_head_sha256": origin_before["head_hash"],
            "legacy_history_sha256": legacy["history_sha256"],
            "prior_sha256": predecessor,
        }
        digest = hashlib.sha256(predecessor.encode("ascii") + canonical({
            "schema": REHEARSAL, **body,
        })).hexdigest()
        simulated.execute(
            "INSERT INTO attempts(seq,day,lane,ticket,terminal_seq,"
            "scope_sha256,original_head_sha256,legacy_history_sha256,"
            "prior_sha256,event_sha256) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (*body.values(), digest))
        if abort_before_commit:
            deny("INJECTED_PRECOMMIT_ROLLBACK")
        if len(rows(simulated, owner)) != len(prior) + 1:
            deny("AFTER_INSERT_HISTORY_INVALID")
        simulated.execute("COMMIT")
        return disposition("IN_MEMORY_ATOMIC_RESERVATION_ONLY_NO_POST",
                           reserved=True, scope_sha256=scope,
                           count=len(prior) + 1)
    except BaseException:
        if simulated.in_transaction:
            simulated.execute("ROLLBACK")
        raise
