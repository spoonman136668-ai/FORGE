"""R196 content-addressed, authority-free scientific portfolio progression.

Exactly one candidate is proposed per independent research lane. A fresh
screening generation is suggested only after the existing frozen shortlist
has reached terminal scientific classification. A CKB-owned adapter MUST
verify input hashes against trusted immutable receipts before using this
advisory. No queue, runner, network, file or acceptance access exists here.
"""
from __future__ import annotations

from typing import Any

from portfolio import check, digest, identity, identifier
from portfolio_scheduler import candidate_rows, reconcile

LANES = ("Wingless", "Yggdrasil")
# Mirrors the unchanged live CKB Resolve-Successor boundary. "invalid" is
# infrastructure-invalid, NEVER a successful terminal science observation.
SCIENTIFIC_TERMINAL = frozenset(("supported", "mixed", "negative"))
GATE_FIELDS = {
    "schema", "lane", "state", "official_receipt_sha256",
    "independent_source_admitted", "full_preregistration_frozen",
    "sealed_source_set_sha256", "cross_lane_exclusion_receipt_sha256",
    "sealed_outcomes_accessed", "accepted_ref_mutation",
}
GATE_STATES = (
    "AWAITING_POST_EPOCH_SOURCE", "SCIENTIFIC_QUALIFICATION_PENDING",
    "INDEPENDENT_CKB_ADMITTED",
)
NO_AUTH = {
    "ready_research_authority": False,
    "dispatch_authority": False,
    "scientific_classification_authority": False,
    "accepted_ref_mutation": False,
    "production_authority": False,
    "ktrade_access": False,
}


def _sha256(value: str, label: str) -> str:
    identity(value, label)
    check(len(value) == 64, label + "_LENGTH")
    return value


def verify_gate(lane: str, gate: dict, independently_pinned_sha256: str) -> None:
    """Check read-only gate evidence; never mint official science authority."""
    _sha256(independently_pinned_sha256, "GATE_PIN")
    check(type(gate) is dict and set(gate) == GATE_FIELDS, "GATE_SCHEMA")
    check(digest(gate) == independently_pinned_sha256, "GATE_IDENTITY_DRIFT")
    check(gate["schema"] == "ckb.r196-science-gate-advisory.v1" and
          gate["lane"] == lane and gate["state"] in GATE_STATES,
          "GATE_SCOPE")
    _sha256(gate["official_receipt_sha256"], "GATE_OFFICIAL_RECEIPT")
    check(gate["sealed_outcomes_accessed"] is False and
          gate["accepted_ref_mutation"] is False, "GATE_FORBIDDEN_AUTHORITY")
    check(type(gate["independent_source_admitted"]) is bool and
          type(gate["full_preregistration_frozen"]) is bool,
          "GATE_FLAG_TYPE")
    admitted = gate["state"] == "INDEPENDENT_CKB_ADMITTED"
    check(gate["independent_source_admitted"] is admitted and
          gate["full_preregistration_frozen"] is admitted,
          "GATE_UNPROVEN_ADMISSION")
    for name in ("sealed_source_set_sha256",
                 "cross_lane_exclusion_receipt_sha256"):
        if admitted:
            _sha256(gate[name], name.upper())
        else:
            check(gate[name] is None, "GATE_PREMATURE_SOURCE_PROOF")


def plan_lane(advisory: dict, journal: list[dict], gate: dict, *,
              independently_pinned_advisory_sha256: str,
              independently_pinned_last_event_sha256: str | None,
              independently_pinned_gate_sha256: str) -> dict[str, Any]:
    """Advance frozen shortlist order, never reorder on sealed outcomes.

    No QUALIFIED shadow event is an official authorization to execute.
    Candidates retain their original rank regardless of event arrival order.
    """
    check(type(advisory) is dict and advisory.get("program") in LANES,
          "LANE_ADVISORY_INVALID")
    lane = advisory["program"]
    verify_gate(lane, gate, independently_pinned_gate_sha256)
    _sha256(independently_pinned_advisory_sha256, "ADVISORY_PIN")
    check(advisory.get("advisory_sha256") ==
          independently_pinned_advisory_sha256, "ADVISORY_PIN_DRIFT")
    # Hash validation and event-chain/transition validation are performed by
    # the already-qualified R2 shadow reconciler.
    rows = candidate_rows(advisory)
    ledger = reconcile(advisory, journal)
    if independently_pinned_last_event_sha256 is None:
        check(ledger["last_receipt_sha256"] is None,
              "JOURNAL_UNPINNED_EVENTS")
    else:
        _sha256(independently_pinned_last_event_sha256, "JOURNAL_PIN")
        check(ledger["last_receipt_sha256"] ==
              independently_pinned_last_event_sha256, "JOURNAL_HEAD_DRIFT")
    check(type(journal) is list and len(journal) <= 1024,
          "JOURNAL_LENGTH_LIMIT")
    states = {row["candidate_id"]: row for row in ledger["candidates"]}
    frozen_order = advisory["shortlist"]["selected"]
    check(type(frozen_order) is list and
          len(frozen_order) == len(rows) and len(rows) <= 5,
          "FROZEN_SHORTLIST_DRIFT")
    check(len({r["candidate_id"] for r in frozen_order}) == len(rows),
          "FROZEN_ORDER_DUPLICATE")
    check(set(states) == set(rows), "LEDGER_PORTFOLIO_DRIFT")

    current = None
    for finalist in frozen_order:
        row = states[finalist["candidate_id"]]
        if row["status"] == "CLASSIFIED":
            if row["classification"] in SCIENTIFIC_TERMINAL:
                continue
            check(row["classification"] == "invalid",
                  "UNKNOWN_CLASSIFICATION_IN_LEDGER")
        current = row
        break
    terminal = sum(
        row["status"] == "CLASSIFIED" and
        row["classification"] in SCIENTIFIC_TERMINAL
        for row in states.values())
    pending = len(states) - terminal
    if current is None:
        # Screening refresh is an advisory, not a new screen or new budget.
        disposition = "REQUEST_NEW_FROZEN_SCREEN_GENERATION"
    elif current["status"] == "PLANNED":
        disposition = "AWAITING_INDEPENDENT_CANDIDATE_QUALIFICATION"
    elif current["status"] == "BLOCKED":
        disposition = "AWAITING_BOUNDED_INFRASTRUCTURE_REQUALIFICATION"
    elif current["status"] == "RUNNING":
        disposition = "EXISTING_SCIENTIFIC_RUN_ACTIVE"
    elif current["status"] == "CLASSIFIED":
        check(current["classification"] == "invalid",
              "INVALID_RESULT_CLASSIFICATION_DRIFT")
        disposition = "INVALID_RESULT_REQUIRES_EXISTING_CKB_RECOVERY"
    else:
        check(current["status"] == "QUALIFIED", "CANDIDATE_STATE_INVALID")
        disposition = ("PROPOSE_OFFICIAL_CKB_REVIEW" if
                       gate["state"] == "INDEPENDENT_CKB_ADMITTED"
                       else "AWAITING_POST_EPOCH_SOURCE"
                       if gate["state"] == "AWAITING_POST_EPOCH_SOURCE"
                       else "AWAITING_INDEPENDENT_SCIENCE_QUALIFICATION")
    proposal = None
    if disposition == "PROPOSE_OFFICIAL_CKB_REVIEW":
        proposal = {
            "candidate_id": identifier(current["candidate_id"], "CANDIDATE"),
            "family_id": current["family_id"],
            "candidate_code_sha": current["candidate_code_sha"],
            "qualified_package_sha": current["qualified_package_sha"],
            "sealed_manifest_sha": current["sealed_manifest_sha"],
            "authority_receipt_sha": current["authority_receipt_sha"],
            "status": "ADVISORY_ONLY_REQUIRES_EXISTING_CKB_SCIENCE_AUTHORITY",
        }
    body = {
        "schema": "ckb.r196-evolutionary-progression-advisory.v1",
        "lane": lane,
        "frozen_shortlist_advisory_sha256": independently_pinned_advisory_sha256,
        "journal_head_sha256": ledger["last_receipt_sha256"],
        "gate_sha256": independently_pinned_gate_sha256,
        "frozen_shortlist_order": [r["candidate_id"] for r in frozen_order],
        "terminal_count": terminal,
        "pending_count": pending,
        "next_candidate_id": None if current is None else current["candidate_id"],
        "disposition": disposition,
        "next_official_review_proposal": proposal,
        "new_generation_requires_fresh_frozen_contract": True,
        "new_generation_requires_new_budget_authorization": True,
        "no_sealed_outcomes_used_for_selection": True,
        "historical_negatives_preserved": True,
        **NO_AUTH,
    }
    return {**body, "advisory_sha256": digest(body)}


def plan_both_lanes(lanes: dict) -> dict[str, Any]:
    """Separate portfolios and budgets; do not share or pool candidates."""
    check(type(lanes) is dict and set(lanes) == set(LANES),
          "INDEPENDENT_LANES_REQUIRED")
    results: dict[str, dict] = {}
    for lane in LANES:
        packet = lanes[lane]
        check(type(packet) is dict and set(packet) == {
            "advisory", "journal", "gate", "advisory_pin", "journal_pin",
            "gate_pin"}, "LANE_PACKET_SCHEMA")
        check(packet["advisory"].get("program") == lane,
              "CROSS_LANE_ADVISORY")
        results[lane] = plan_lane(
            packet["advisory"], packet["journal"], packet["gate"],
            independently_pinned_advisory_sha256=packet["advisory_pin"],
            independently_pinned_last_event_sha256=packet["journal_pin"],
            independently_pinned_gate_sha256=packet["gate_pin"])
    # Candidate IDs are lane-local names, not globally unique namespaces.
    # Independent signed advisories and source-exclusion evidence guard lanes.
    l, r = (lanes[x]["gate"] for x in LANES)
    if (l["state"] == "INDEPENDENT_CKB_ADMITTED" and
            r["state"] == "INDEPENDENT_CKB_ADMITTED"):
        check(l["sealed_source_set_sha256"] != r["sealed_source_set_sha256"],
              "CROSS_LANE_IDENTICAL_SOURCE_SET")
        check(l["cross_lane_exclusion_receipt_sha256"] ==
              r["cross_lane_exclusion_receipt_sha256"],
              "CROSS_LANE_EXCLUSION_PROOF_DRIFT")
    body = {
        "schema": "ckb.r196-dual-lane-progression-advisory.v1",
        "lanes": results,
        "single_existing_ckb_authority_required": True,
        "concurrent_lane_review_only": True,
        **NO_AUTH,
    }
    return {**body, "advisory_sha256": digest(body)}
