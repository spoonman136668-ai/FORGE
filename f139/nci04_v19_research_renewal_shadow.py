"""F139 V19 shadow-only renewal eligibility, no controller/IO/provider authority.

An inert deterministic feasibility guard for a future owner-led research loop.
Only a separately authenticated original SQLite/SingleOwner adapter can turn a
verified native terminal event into an actual model request. This module cannot
read the ledger, run tasks, make network requests, or authorize dispatch.
Existing V17/V18 lifetime and no-replay behavior is entirely unchanged.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re

LANES = ("Wingless", "Yggdrasil")
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
UTC_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
MAX_DAILY_TOTAL = 2
MAX_DAILY_PER_LANE = 1
MAX_ROLLING_30D_TOTAL = 40
MAX_ROLLING_30D_PER_LANE = 20
TERMINAL_FIELDS = frozenset({
    "ticket", "lane", "seq", "source_sha", "evidence_sha256",
    "stage", "chain_verified",
})
ATTEMPT_FIELDS = frozenset({
    "day", "lane", "ticket", "terminal_seq", "scope_sha256",
})


class ShadowDenied(ValueError):
    """Invalid custodied input; NOT an inference/provider failure."""


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ShadowDenied("F139_V19_SHADOW_" + code)


def day_value(value: str) -> dt.date:
    require(type(value) is str and UTC_DAY.fullmatch(value) is not None,
            "UTC_DAY_FORMAT")
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ShadowDenied("F139_V19_SHADOW_UTC_DAY_INVALID") from exc
    require(parsed.isoformat() == value, "UTC_DAY_CANONICAL")
    return parsed


def is_sha40(value: object) -> bool:
    return type(value) is str and SHA40.fullmatch(value) is not None


def is_sha64(value: object) -> bool:
    return type(value) is str and SHA64.fullmatch(value) is not None


def is_ticket(value: object) -> bool:
    return (type(value) is str and 1 <= len(value) <= 128
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", value) is not None)


def normalized_attempts(attempts: list[dict], today: dt.date) -> list[dict]:
    require(type(attempts) is list and len(attempts) <= 10000,
            "ATTEMPT_HISTORY_SHAPE")
    result = []
    seen_scopes: set[str] = set()
    seen_tickets: set[str] = set()
    prior_date = None
    for item in attempts:
        require(type(item) is dict and set(item) == ATTEMPT_FIELDS
                and item["lane"] in LANES
                and is_ticket(item["ticket"])
                and type(item["terminal_seq"]) is int
                and item["terminal_seq"] > 0
                and is_sha64(item["scope_sha256"]), "ATTEMPT_RECORD_INVALID")
        day = day_value(item["day"])
        require(day <= today and (prior_date is None or day >= prior_date),
                "ATTEMPT_CHRONOLOGY")
        require(item["scope_sha256"] not in seen_scopes
                and item["ticket"] not in seen_tickets,
                "ATTEMPT_REPLAY_OR_DUPLICATE")
        seen_scopes.add(item["scope_sha256"])
        seen_tickets.add(item["ticket"])
        prior_date = day
        result.append({**item, "parsed_day": day})
    return result


def shadow_decision(*, owner_source_sha: str, lane: str, target_commit: str,
                    native_path: str, terminal: dict, attempts: list[dict],
                    utc_day: str) -> dict:
    """Return advisory eligibility for hypothetical NEW native evidence.

    Caller-provided 'chain_verified' is NOT independently authenticated here.
    A future original-owner release MUST authenticate the full original chain,
    owner mutex, lane, stage, unchanged source and admissible path again under
    its own pre-request transaction, and atomically append request-attempt
    custody BEFORE contacting a free provider. Never treat this pure result as
    a release, permission, science result or retry authorization.
    """
    today = day_value(utc_day)
    require(is_sha40(owner_source_sha) and is_sha40(target_commit)
            and lane in LANES
            and type(native_path) is str and 1 <= len(native_path) <= 200
            and not native_path.startswith(("/", "\\"))
            and ".." not in native_path.split("/")
            and "\\" not in native_path,
            "SOURCE_OR_PATH_INVALID")
    require(type(terminal) is dict and set(terminal) == TERMINAL_FIELDS
            and terminal["lane"] == lane
            and is_ticket(terminal["ticket"])
            and type(terminal["seq"]) is int and terminal["seq"] > 0
            and is_sha40(terminal["source_sha"])
            and is_sha64(terminal["evidence_sha256"])
            and terminal["stage"] == "VERIFIED"
            and terminal["chain_verified"] is True,
            "TERMINAL_NOT_CUSTODIED")
    rows = normalized_attempts(attempts, today)
    scope = hashlib.sha256(json.dumps({
        "schema": "forge.f139.v19.shadow-new-native-evidence.v1",
        "owner_source_sha": owner_source_sha,
        "lane": lane,
        "target_commit": target_commit,
        "native_path": native_path,
        "terminal_ticket": terminal["ticket"],
        "terminal_seq": terminal["seq"],
        "terminal_source_sha": terminal["source_sha"],
        "terminal_evidence_sha256": terminal["evidence_sha256"],
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    # A different FORGE release or target path cannot redeem an already
    # consumed terminal. Time rollover alone never buys another request.
    if terminal["ticket"] in {a["ticket"] for a in rows} or scope in {
            a["scope_sha256"] for a in rows}:
        return report("BLOCKED_ALREADY_CONSUMED", scope)
    if any(a["lane"] == lane and a["terminal_seq"] >= terminal["seq"]
           for a in rows):
        return report("BLOCKED_NOT_NEW_LANE_EVIDENCE", scope)
    day_rows = [a for a in rows if a["parsed_day"] == today]
    month_rows = [a for a in rows
                  if dt.timedelta(0) <= today - a["parsed_day"] < dt.timedelta(days=30)]
    if (len(day_rows) >= MAX_DAILY_TOTAL
            or sum(a["lane"] == lane for a in day_rows) >= MAX_DAILY_PER_LANE
            or len(month_rows) >= MAX_ROLLING_30D_TOTAL
            or sum(a["lane"] == lane for a in month_rows) >= MAX_ROLLING_30D_PER_LANE):
        return report("BLOCKED_BOUNDED_FREE_BUDGET", scope)
    return report("ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED", scope)


def report(disposition: str, scope: str) -> dict:
    return {
        "schema": "forge.f139.v19.renewal-shadow-decision.v1",
        "disposition": disposition,
        "scope_sha256": scope,
        "development_only": True,
        "original_owner_request_authorized": False,
        "paid_model_calls": 0,
        "provider_requests": 0,
        "worker_dispatched": False,
        "scientific_first_use": False,
        "accepted_ref_mutations": 0,
        "controller_changes": 0,
    }
