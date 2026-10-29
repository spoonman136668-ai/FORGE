"""Read-only original F139 terminal witness for the inert V19 renewal design.

This module is NOT on the original controller's run path. Never accept a
caller-provided chain_verified boolean as a native outcome. Only the genuine
original Database, held SingleOwner lock and cold event-chain verification can
yield an advisory candidate. No SQL writes, external requests, source change,
owner command, model calls, accepted refs or scientific authorization.
"""
from __future__ import annotations

import json
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import R7_TEST_PATHS, model_source_path_allowed
from f139.nci04_v19_research_renewal_shadow import (
    ShadowDenied, LANES, is_sha40, is_sha64, shadow_decision,
)

ADMISSION_KIND = "NATIVE_DEVELOPMENT_ADMITTED"
TERMINAL_KIND = "PROVIDER_VERIFIED_TERMINAL"
LEGACY_ATTEMPT_KINDS = ("FREE_REASONER_ATTEMPTED", "MODEL_DRAFT_ATTEMPTED")


def deny(why: str):
    raise ShadowDenied("F139_V19_ORIGINAL_WITNESS_" + why)


def output(disposition: str, *, owner_source_sha: str, terminal_event_seq: int = 0,
           shadow: dict | None = None) -> dict:
    return {
        "schema": "forge.f139.v19.original-ledger-readonly-witness.v1",
        "disposition": disposition,
        "owner_source_sha": owner_source_sha,
        "terminal_event_seq": terminal_event_seq,
        "shadow": shadow,
        "owner_request_authorized": False,
        "provider_requests": 0,
        "worker_dispatched": False,
        "scientific_first_use": False,
        "paid_model_calls": 0,
        "source_mutations": 0,
        "ledger_mutations": 0,
    }


def project_original_native_terminal(db: Database, *, lane: str, utc_day: str,
                                     hypothetical_v19_attempts: list[dict]) -> dict:
    """Projection only; original owner adapter and request reservation NOT built.

    Even a positive shadow means NO provider request, model decision, scheduler
    activity, authority promotion, or unlock of legacy free-model lifetime.
    Hypothetical V19 history is NOT a substitute for future original-owner
    SHA-chained V19 records. All V17/V18 logic remains unchanged.
    """
    if type(db) is not Database or lane not in LANES:
        deny("DATABASE_OR_LANE_INVALID")
    if not SingleOwner.held(db.filename.with_suffix(".lock")):
        deny("ORIGINAL_MUTEX_NOT_HELD")
    db.verify()  # checks the genuine event chain, native admission and custody
    meta = db.meta()
    if meta["enabled"] != 1 or meta["legacy_suspended"] != 1:
        deny("ORIGINAL_OWNER_NOT_ENABLED")
    if db.ready() is not None or db.actives():
        return output("BLOCKED_ORIGINAL_WORK_IN_FLIGHT",
                      owner_source_sha=meta["source_sha"])
    if type(hypothetical_v19_attempts) is not list:
        deny("HYPOTHETICAL_ATTEMPTS_NOT_LIST")

    rows = db.conn.execute(
        "SELECT seq,kind,payload,sha FROM events WHERE kind IN "
        "('NATIVE_DEVELOPMENT_ADMITTED','PROVIDER_VERIFIED_TERMINAL',"
        "'FREE_REASONER_ATTEMPTED','MODEL_DRAFT_ATTEMPTED') ORDER BY seq"
    ).fetchall()
    admissions = {}
    terminals = {}
    legacy_watermark = 0
    for e in rows:
        kind = e["kind"]
        if kind in LEGACY_ATTEMPT_KINDS:
            legacy_watermark = e["seq"]
            continue
        try:
            data = json.loads(e["payload"])
        except (ValueError, TypeError) as exc:
            raise ShadowDenied("F139_V19_ORIGINAL_WITNESS_EVENT_JSON_INVALID") from exc
        if not isinstance(data, dict):
            deny("EVENT_FIELDS_INVALID")
        if kind == ADMISSION_KIND:
            ticket = data.get("ticket")
            if type(ticket) is not str or ticket in admissions:
                deny("DUPLICATE_NATIVE_ADMISSION")
            admissions[ticket] = (e, data)
        else:
            if set(data) != {"ticket", "run_id", "evidence_sha"}:
                deny("TERMINAL_FIELDS_CHANGED")
            ticket = data["ticket"]
            if type(ticket) is not str or ticket in terminals:
                deny("DUPLICATE_OR_INVALID_TERMINAL")
            terminals[ticket] = (e, data)

    candidates = []
    for ticket, (admission_event, admission) in admissions.items():
        if admission.get("lane") != lane:
            continue
        record = terminals.get(ticket)
        if record is None:
            continue
        terminal_event, terminal = record
        task = db.conn.execute(
            "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
            "evidence_dir,evidence_sha,completed_at FROM tasks WHERE ticket=?",
            (ticket,)
        ).fetchone()
        if task is None:
            deny("TERMINAL_TASK_MISSING")
        if not (terminal_event["seq"] > admission_event["seq"]
                and task["lane"] == lane
                and task["stage"] == "VERIFIED"
                and task["source_sha"] == admission.get("source_sha")
                and is_sha40(task["source_sha"])
                and task["manifest_sha"] == admission.get("manifest_sha256")
                and type(task["run_id"]) is int and task["run_id"] > 0
                and task["run_id"] == terminal["run_id"]
                and is_sha64(task["evidence_sha"])
                and terminal["evidence_sha"] == task["evidence_sha"]
                and isinstance(task["evidence_dir"], str) and task["evidence_dir"]
                and isinstance(task["completed_at"], str)
                and task["completed_at"]):
            deny("NATIVE_TERMINAL_CUSTODY_DRIFT")
        target_commit = admission.get("native_target_commit")
        native_path = admission.get("native_path")
        if not is_sha40(target_commit) or type(native_path) is not str:
            deny("NATIVE_SOURCE_NOT_MODEL_AUTHORABLE")
        if not model_source_path_allowed(lane, native_path):
            # Genuine R7 test-path admissions are permitted native history,
            # but must not be considered renewable model-authorable terminals.
            # All event/task custody was verified above; reject unknown paths.
            if native_path not in R7_TEST_PATHS[lane]:
                deny("NATIVE_SOURCE_NOT_MODEL_AUTHORABLE")
            continue
        candidates.append((terminal_event["seq"], task, target_commit, native_path))

    if not candidates:
        return output("BLOCKED_NO_AUTHENTIC_NATIVE_TERMINAL",
                      owner_source_sha=meta["source_sha"])
    terminal_seq, task, target_commit, native_path = max(
        candidates, key=lambda item: item[0])
    # A source transition, UTC rollover, a renamed target and an old verified
    # ticket are NOT fresh evidence. Original provider attempt custody wins.
    if terminal_seq <= legacy_watermark:
        return output("BLOCKED_NO_NEW_TERMINAL_AFTER_ORIGINAL_ATTEMPT",
                      owner_source_sha=meta["source_sha"],
                      terminal_event_seq=terminal_seq)
    terminal = {
        "ticket": task["ticket"], "lane": lane,
        "seq": terminal_seq, "source_sha": task["source_sha"],
        "evidence_sha256": task["evidence_sha"], "stage": "VERIFIED",
        "chain_verified": True,
    }
    shadow = shadow_decision(
        owner_source_sha=meta["source_sha"], lane=lane,
        target_commit=target_commit, native_path=native_path,
        terminal=terminal, attempts=hypothetical_v19_attempts,
        utc_day=utc_day,
    )
    return output("AUTHENTIC_FRESH_TERMINAL_SHADOW_ONLY_NOT_AUTHORIZED",
                  owner_source_sha=meta["source_sha"],
                  terminal_event_seq=terminal_seq, shadow=shadow)
