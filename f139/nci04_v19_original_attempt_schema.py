"""Cold original-F139 V19 research-attempt event verifier, NO request writer.

Called only at the END of the original Database.verify() after normal historical
SHA-chain, native admission and custody validation. Does not call db.verify,
modify SQLite, send requests, change any task/controller or authorize science.
There is NO live append/activation function for this event kind in this release.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json

from f139.nci04_native_contract import model_source_path_allowed
from f139.nci04_v19_research_renewal_shadow import (
    MAX_DAILY_TOTAL, MAX_DAILY_PER_LANE, MAX_ROLLING_30D_TOTAL,
    MAX_ROLLING_30D_PER_LANE, ShadowDenied, day_value, is_sha40, is_sha64,
    shadow_decision,
)
from f139.local_controller import canonical

KIND = "NATIVE_RENEWAL_ATTEMPTED"
SCHEMA = "forge.f139.v19.original-request-attempt.v1"
FIELDS = frozenset({
    "schema", "owner_source_sha", "lane", "terminal_ticket",
    "terminal_event_seq", "terminal_event_sha256", "terminal_evidence_sha256",
    "target_commit", "native_path", "scope_sha256", "original_legacy_history_sha256",
    "utc_day", "prior_event_head_sha256", "retry_allowed",
    "request_intent_committed", "paid_model_calls", "worker_dispatched",
    "scientific_first_use",
})
LEGACY_KINDS = frozenset({
    "FREE_REASONER_ATTEMPTED", "MODEL_DRAFT_ATTEMPTED",
    "MODEL_DRAFT_AUTHENTICATED",
})


def deny(why: str) -> None:
    raise ShadowDenied("F139_V19_COLD_REQUEST_" + why)


def legacy_digest(events: list[dict]) -> str:
    """Exact source-bound original event identity, never user supplied."""
    return hashlib.sha256(canonical([
        {"seq": e["seq"], "kind": e["kind"], "sha": e["sha"]}
        for e in events if e["kind"] in LEGACY_KINDS
    ])).hexdigest()


def audit_v19_original_request_events(db) -> None:
    """Verify entire chronological V19 request history, including cold reopen.

    Original db.verify() calls this at its final boundary. No V19 event is
    emitted by production runtime: the writer, provider and activation gate
    deliberately do not exist in the original owner source.
    """
    meta = db.meta()
    events = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"))
    if not any(e["kind"] == KIND for e in events):
        return  # original live V17/V18 history is unaffected

    originals = []
    admissions = {}
    terminals = {}
    attempted = []
    consumed = set()
    last_lane_terminal = {}
    legacy_draft_attempts = set()
    legacy_draft_success = set()
    previous_day = None
    source = None
    original_model_last = 0
    for raw in events:
        event = dict(raw)
        kind = event["kind"]
        try:
            doc = json.loads(event["payload"])
        except (ValueError, TypeError) as exc:
            raise ShadowDenied("F139_V19_COLD_REQUEST_EVENT_JSON") from exc
        if not isinstance(doc, dict):
            deny("EVENT_OBJECT_INVALID")
        if source is None:
            source = (doc["from_source_sha"] if kind == "SOURCE_TRANSITION_ADMITTED"
                      else meta["source_sha"])
        if kind == "SOURCE_TRANSITION_ADMITTED":
            if not is_sha40(doc.get("to_source_sha")):
                deny("SOURCE_TRANSITION_INVALID")
            source = doc["to_source_sha"]
        elif kind == "NATIVE_DEVELOPMENT_ADMITTED":
            ticket = doc.get("ticket")
            if not isinstance(ticket, str) or ticket in admissions:
                deny("ORIGINAL_ADMISSION_REPLAY")
            admissions[ticket] = (event, doc)
        elif kind == "PROVIDER_VERIFIED_TERMINAL":
            ticket = doc.get("ticket")
            if not isinstance(ticket, str) or ticket in terminals:
                deny("ORIGINAL_TERMINAL_REPLAY")
            terminals[ticket] = (event, doc)
        if kind in LEGACY_KINDS:
            original_model_last = event["seq"]
            if kind == "MODEL_DRAFT_ATTEMPTED":
                identity = doc.get("candidate_identity")
                if identity in legacy_draft_attempts:
                    deny("ORIGINAL_MODEL_DRAFT_REPLAY")
                legacy_draft_attempts.add(identity)
            elif kind == "MODEL_DRAFT_AUTHENTICATED":
                identity = doc.get("candidate_identity")
                if (identity not in legacy_draft_attempts
                        or identity in legacy_draft_success):
                    deny("ORIGINAL_DRAFT_ORPHAN")
                legacy_draft_success.add(identity)
            originals.append(event)

        if kind != KIND:
            continue
        if (set(doc) != FIELDS or doc["schema"] != SCHEMA
                or doc["owner_source_sha"] != source
                or not is_sha40(doc["owner_source_sha"])
                or doc["lane"] not in ("Wingless", "Yggdrasil")
                or type(doc["terminal_ticket"]) is not str
                or type(doc["terminal_event_seq"]) is not int
                or doc["terminal_event_seq"] <= 0
                or not is_sha64(doc["terminal_event_sha256"])
                or not is_sha64(doc["terminal_evidence_sha256"])
                or not is_sha40(doc["target_commit"])
                or not model_source_path_allowed(doc["lane"], doc["native_path"])
                or not is_sha64(doc["scope_sha256"])
                or not is_sha64(doc["original_legacy_history_sha256"])
                or doc["prior_event_head_sha256"] != event["prior_sha"]
                or doc["retry_allowed"] is not False
                or doc["request_intent_committed"] is not True
                or type(doc["paid_model_calls"]) is not int
                or doc["paid_model_calls"] != 0
                or doc["worker_dispatched"] is not False
                or doc["scientific_first_use"] is not False):
            deny("ATTEMPT_FIELDS_OR_RELEASE_SCOPE")
        day = day_value(doc["utc_day"])
        if previous_day is not None and day < previous_day:
            deny("UTC_CLOCK_ROLLBACK")
        previous_day = day
        if legacy_draft_attempts != legacy_draft_success:
            deny("UNRESOLVED_ORIGINAL_MODEL_PUBLICATION")
        if event["seq"] <= original_model_last:
            deny("ORIGINAL_MODEL_ATTEMPT_AFTER_V19")
        if doc["original_legacy_history_sha256"] != legacy_digest(originals):
            deny("HISTORICAL_MODEL_ATTEMPT_SEAL_DRIFT")
        ticket = doc["terminal_ticket"]
        if ticket in consumed:
            deny("NATIVE_TERMINAL_REPLAY")
        admission = admissions.get(ticket)
        terminal = terminals.get(ticket)
        if admission is None or terminal is None:
            deny("AUTHENTIC_NATIVE_TERMINAL_MISSING")
        a_event, a_doc = admission
        t_event, t_doc = terminal
        if (a_event["seq"] >= t_event["seq"]
                or t_event["seq"] >= event["seq"]
                or t_event["seq"] <= original_model_last
                or t_event["seq"] != doc["terminal_event_seq"]
                or t_event["sha"] != doc["terminal_event_sha256"]
                or a_doc.get("lane") != doc["lane"]
                or a_doc.get("native_target_commit") != doc["target_commit"]
                or a_doc.get("native_path") != doc["native_path"]
                or t_doc.get("evidence_sha") != doc["terminal_evidence_sha256"]
                or last_lane_terminal.get(doc["lane"], 0) >= t_event["seq"]):
            deny("TERMINAL_NOT_NEW_OR_SOURCE_DRIFT")
        task = db.conn.execute(
            "SELECT lane,source_sha,stage,manifest_sha,run_id,evidence_sha,"
            "evidence_dir,completed_at FROM tasks WHERE ticket=?",
            (ticket,)).fetchone()
        if (task is None or task["lane"] != doc["lane"]
                or task["source_sha"] != a_doc.get("source_sha")
                or task["stage"] != "VERIFIED"
                or task["manifest_sha"] != a_doc.get("manifest_sha256")
                or type(task["run_id"]) is not int
                or task["run_id"] != t_doc.get("run_id")
                or task["evidence_sha"] != doc["terminal_evidence_sha256"]
                or not task["evidence_dir"] or not task["completed_at"]):
            deny("ORIGINAL_TASK_CUSTODY_DRIFT")
        terminal_obj = {
            "ticket": ticket, "lane": doc["lane"], "seq": t_event["seq"],
            "source_sha": task["source_sha"],
            "evidence_sha256": task["evidence_sha"], "stage": "VERIFIED",
            "chain_verified": True,
        }
        shadow = shadow_decision(
            owner_source_sha=doc["owner_source_sha"],
            lane=doc["lane"], target_commit=doc["target_commit"],
            native_path=doc["native_path"], terminal=terminal_obj,
            attempts=attempted, utc_day=doc["utc_day"],
        )
        if (shadow["disposition"] != "ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED"
                or shadow["scope_sha256"] != doc["scope_sha256"]):
            deny("SCOPE_ALREADY_ATTEMPTED_OR_INVALID")
        # The V17/V18 free requests count against the new rolling/daily
        # window; original lifetime 8 remains immutable and unmodified.
        old = []
        for legacy in originals:
            if legacy["kind"] != "FREE_REASONER_ATTEMPTED":
                continue
            data = json.loads(legacy["payload"])
            old_day = day_value(data["utc_day"])
            if old_day > day:
                deny("ORIGINAL_DAY_AHEAD_OF_V19_REQUEST")
            old.append((old_day, data["lane"]))
        all_days = old + [
            (day_value(r["day"]), r["lane"]) for r in attempted
        ]
        daily_lanes = [lane for date, lane in all_days if date == day]
        month_lanes = [lane for date, lane in all_days
                       if dt.timedelta(0) <= day - date < dt.timedelta(days=30)]
        if (len(daily_lanes) >= MAX_DAILY_TOTAL
                or daily_lanes.count(doc["lane"]) >= MAX_DAILY_PER_LANE
                or len(month_lanes) >= MAX_ROLLING_30D_TOTAL
                or month_lanes.count(doc["lane"]) >= MAX_ROLLING_30D_PER_LANE):
            deny("COMBINED_LEGACY_AND_V19_BUDGET")
        consumed.add(ticket)
        last_lane_terminal[doc["lane"]] = t_event["seq"]
        attempted.append({
            "day": doc["utc_day"], "lane": doc["lane"],
            "ticket": ticket, "terminal_seq": t_event["seq"],
            "scope_sha256": doc["scope_sha256"],
        })
