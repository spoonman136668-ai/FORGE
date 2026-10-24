"""Fail-closed, advisory-only provenance for existing F139 owner-authored PR intake.

This module neither originates code nor executes recommendations. It checks a
bounded infogain decision embedded in an already source-authenticated owner PR.
The original F139 single-owner ledger and exact native worker remain unchanged.
"""
from __future__ import annotations

import hashlib
import json
import re

from f139.nci04_native_contract import canonical, digest

SCHEMA = "forge.f139.advisory-pr-handoff.v1"
DECISION_SCHEMA = "forge.infogain.advisory.v1"
RANK_STATUS = "UNTESTED_ESTIMATE_NOT_SCIENTIFIC_ACCEPTANCE"
GENERATORS = frozenset({
    "frozen_control", "dream_rsi", "shinka_pareto", "theta_evolve",
    "promptbreeder", "dgm_genenv",
})
CLASSIFICATIONS = frozenset({
    "SUPPORTED", "NEGATIVE", "MIXED", "INVALID",
    "CONSUMED_INDETERMINATE", "LIMITATION",
})


class AdvisoryHandoffDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise AdvisoryHandoffDenied("F139_ADVISORY_" + reason)


def hex_id(value: object, length: int) -> bool:
    return isinstance(value, str) and re.fullmatch(
        "[a-f0-9]{" + str(length) + "}", value) is not None


def history_digest(records: list[dict], *, nil: bool = False) -> str:
    """Mirror infogain.HistoryDigest's Go JSON field order and nil semantics."""
    rows = None if nil else [{
        "mechanism_sha256": r["mechanism_sha256"],
        "source_sha": r["source_sha"],
        "evidence_sha256": r["evidence_sha256"],
        "classification": r["classification"],
    } for r in records]
    raw = json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(b"FORGE-INFOGAIN-HISTORY-V1\n" + raw).hexdigest()


def inspect_pr_advisory(body: object, *, lane: str,
                        controller_source_sha: str, head_commit: str,
                        target_commit: str, path: str,
                        after_sha256: str) -> dict | None:
    """Return bounded advisory lineage, never execution or science authority.

    Ordinary PR prose retains original F139 behavior. A declared handoff must
    match the independently verified PR commit and after-bytes exactly; any
    mismatch is rejected. The advisory payload is owner-asserted and cannot by
    itself authenticate an independent scientific forecast or outcome.
    """
    if not isinstance(body, str) or not body.strip():
        return None
    try:
        doc = json.loads(body)
    except (ValueError, UnicodeError):
        need(SCHEMA not in body, "DECLARED_PAYLOAD_NOT_JSON")
        return None
    if not isinstance(doc, dict):
        return None
    if doc.get("schema") != SCHEMA:
        need(not (isinstance(doc.get("schema"), str) and
                  doc["schema"].startswith("forge.f139.advisory-pr-handoff")),
             "UNKNOWN_HANDOFF_VERSION")
        return None
    need(len(body.encode("utf-8")) <= 16384, "BODY_TOO_LARGE")
    need(set(doc) == {
        "schema", "lane", "controller_source_sha", "head_commit",
        "target_commit", "path", "after_sha256", "candidate_id", "decision",
    }, "FIELDS_INVALID")
    need(lane in ("Wingless", "Yggdrasil")
         and doc["lane"] == lane
         and doc["controller_source_sha"] == controller_source_sha
         and doc["head_commit"] == head_commit
         and doc["target_commit"] == target_commit
         and doc["path"] == path and doc["after_sha256"] == after_sha256
         and hex_id(controller_source_sha, 40)
         and hex_id(head_commit, 40) and hex_id(target_commit, 40)
         and hex_id(after_sha256, 64), "SOURCE_OR_LANE_DRIFT")
    decision = doc["decision"]
    need(isinstance(decision, dict)
         and decision.get("schema") == DECISION_SCHEMA
         and decision.get("lane") == lane
         and hex_id(decision.get("frozen_sha256"), 64)
         and hex_id(decision.get("history_sha256"), 64)
         and decision.get("estimated_only") is True
         and decision.get("scientific_accepted") is False
         and decision.get("scientific_first_use_authorized") is False
         and decision.get("dispatch_authorized") is False
         and decision.get("policy_promotion_authorized") is False
         and decision.get("accepted_ref_mutation") is False,
         "NOT_UNQUALIFIED_ADVISORY")
    history = decision.get("history_preserved")
    need(isinstance(history, list) and len(history) <= 200
         and type(decision.get("negative_count")) is int
         and type(decision.get("invalid_count")) is int
         and type(decision.get("indeterminate_count")) is int,
         "HISTORY_INVALID")
    historical_sources, historical_mechanisms, historical_evidence = set(), set(), set()
    for record in history:
        need(isinstance(record, dict)
             and set(record) == {
                 "mechanism_sha256", "source_sha", "evidence_sha256",
                 "classification",
             }
             and isinstance(record.get("classification"), str)
             and record["classification"] in CLASSIFICATIONS
             and hex_id(record.get("source_sha"), 40)
             and hex_id(record.get("mechanism_sha256"), 64)
             and hex_id(record.get("evidence_sha256"), 64)
             and record["source_sha"] not in historical_sources
             and record["mechanism_sha256"] not in historical_mechanisms
             and record["evidence_sha256"] not in historical_evidence,
             "HISTORY_SOURCE_INVALID")
        historical_sources.add(record["source_sha"])
        historical_mechanisms.add(record["mechanism_sha256"])
        historical_evidence.add(record["evidence_sha256"])
    need(decision["history_sha256"] in {
        history_digest(history),
        *( [history_digest(history, nil=True)] if not history else [] ),
    }, "HISTORY_PIN_DRIFT")
    need(decision["negative_count"] == sum(
        r["classification"] in ("NEGATIVE", "LIMITATION") for r in history)
         and decision["invalid_count"] == sum(
             r["classification"] == "INVALID" for r in history)
         and decision["indeterminate_count"] == sum(
             r["classification"] == "CONSUMED_INDETERMINATE" for r in history),
         "HISTORY_COUNTERS_DRIFT")
    selected = decision.get("selected")
    need(isinstance(selected, list) and 1 <= len(selected) <= 8,
         "SELECTED_INVALID")
    need(isinstance(doc["candidate_id"], str)
         and re.fullmatch("[A-Za-z0-9_-]{1,72}", doc["candidate_id"])
         and all(isinstance(r, dict) and isinstance(r.get("id"), str)
                 for r in selected), "CANDIDATE_ID_INVALID")
    candidate = [r for r in selected if r["id"] == doc["candidate_id"]]
    need(len(candidate) == 1
         and len({r["id"] for r in selected}) == len(selected),
         "CANDIDATE_NOT_UNIQUELY_SELECTED")
    ranked = candidate[0]
    need(ranked.get("source_sha") == head_commit
         and isinstance(ranked.get("generator"), str)
         and ranked["generator"] in GENERATORS
         and hex_id(ranked.get("mechanism_sha256"), 64)
         and ranked["mechanism_sha256"] not in historical_mechanisms
         and head_commit not in historical_sources
         and ranked.get("status") == RANK_STATUS
         and type(ranked.get("expected_information_microbits")) is int
         and ranked["expected_information_microbits"] > 0
         and type(ranked.get("estimated_compute_units")) is int
         and ranked["estimated_compute_units"] > 0,
         "CANDIDATE_NOT_BOUNDED_NEW_ESTIMATE")
    return {
        "schema": SCHEMA,
        "candidate_id": doc["candidate_id"],
        "generator": ranked["generator"],
        "frozen_sha256": decision["frozen_sha256"],
        "history_sha256": decision["history_sha256"],
        "selected_mechanism_sha256": ranked["mechanism_sha256"],
        "expected_information_microbits": ranked[
            "expected_information_microbits"],
        "estimated_compute_units": ranked["estimated_compute_units"],
        "advisory_identity_sha256": digest(canonical(doc)),
        "advisory_only": True,
        "scientific_first_use": False,
        "dispatch_authorized": False,
    }
