"""T16 information-per-compute, mechanism-diverse research advisory.

Consumes only pre-frozen candidate proposals, never scientific original
cohorts or existing optimizerbridge.LaneEvidence. No dispatch or promotion.
Forecasts are hypothetical, NOT learned transfer observations. Historical
negatives remain negative. A hash-shaped claim is not independent custody.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

LANES = ("Wingless", "Yggdrasil", "Mass")
VALID_BASIS = ("INDEPENDENT_READ_ONLY_PROPOSAL",)
MAX_CANDIDATES_PER_LANE = 8
CPU_LIMIT_MS = 60000
RAM_LIMIT_KIB = 262144
QUERY_LIMIT = 256
PORTFOLIO_CPU_LIMIT_MS = 90000

@dataclass(frozen=True)
class Proposal:
    id: str
    lane: str
    family: str
    parent_source_sha: str
    mechanism_blob_sha: str
    independent_proposal_witness_sha: str
    frozen_control_blob_sha: str
    frozen_original_source_sha: str
    expected_entropy_reduction_millibits: int
    confidence_basis: str
    planned_train_cpu_ms: int
    planned_eval_cpu_ms: int
    planned_validation_cpu_ms: int
    planned_peak_kib: int
    planned_public_queries: int

    def total_cpu_ms(self) -> int:
        return self.planned_train_cpu_ms + self.planned_eval_cpu_ms + self.planned_validation_cpu_ms

    def from_dict(o: dict) -> "Proposal":
        fields = Proposal.__dataclass_fields__
        if set(o) != set(fields):
            raise ValueError("T16_EXACT_PROPOSAL_SCHEMA_REQUIRED")
        if not all(isinstance(o[k], str) for k in (
            "id", "lane", "family", "parent_source_sha",
            "mechanism_blob_sha", "independent_proposal_witness_sha",
            "frozen_control_blob_sha", "frozen_original_source_sha",
            "confidence_basis")):
            raise ValueError("T16_BAD_IDENTITY_STRING")
        nums = ("expected_entropy_reduction_millibits", "planned_train_cpu_ms",
                "planned_eval_cpu_ms", "planned_validation_cpu_ms",
                "planned_peak_kib", "planned_public_queries")
        if not all(type(o[k]) is int for k in nums):
            raise ValueError("T16_INTEGER_COSTS_ONLY")
        return Proposal(**o)

def good_hex(s: str, n: int) -> bool:
    return len(s) == n and all(c in "0123456789abcdef" for c in s)

def explain(proposal: Proposal) -> str | None:
    if proposal.lane not in LANES or not proposal.id or not proposal.family:
        return "UNKNOWN_LANE_OR_MECHANISM"
    if proposal.confidence_basis not in VALID_BASIS:
        return "UNVERIFIED_PROPOSAL_ORIGIN"
    if not good_hex(proposal.independent_proposal_witness_sha, 64):
        return "MISSING_OR_INVALID_SOURCE_WITNESS_CLAIM"
    if not all(good_hex(v, 40) for v in (
        proposal.parent_source_sha, proposal.mechanism_blob_sha,
        proposal.frozen_control_blob_sha, proposal.frozen_original_source_sha)):
        return "SOURCE_OR_CONTROL_IDENTITY_MISSING"
    if proposal.expected_entropy_reduction_millibits <= 0:
        return "NO_POSITIVE_INFORMATION_HYPOTHESIS"
    if min(proposal.planned_train_cpu_ms, proposal.planned_eval_cpu_ms,
           proposal.planned_validation_cpu_ms, proposal.planned_peak_kib,
           proposal.planned_public_queries) < 0:
        return "NEGATIVE_RESOURCE_ESTIMATE"
    if proposal.total_cpu_ms() <= 0 or proposal.total_cpu_ms() > CPU_LIMIT_MS:
        return "CPU_BUDGET_EXCEEDED"
    if proposal.planned_peak_kib > RAM_LIMIT_KIB:
        return "RAM_BUDGET_EXCEEDED"
    if proposal.planned_public_queries > QUERY_LIMIT:
        return "PUBLIC_QUERY_BUDGET_EXCEEDED"
    return None

def dominated(p: Proposal, q: Proposal) -> bool:
    """Two predictions, no science. Prefer higher proposed uncertainty
    reduction for lower costs only when at least one measure strictly wins."""
    if p.lane != q.lane or p.family == q.family:
        return False
    better_or_equal = (
        q.expected_entropy_reduction_millibits >= p.expected_entropy_reduction_millibits
        and q.total_cpu_ms() <= p.total_cpu_ms()
        and q.planned_peak_kib <= p.planned_peak_kib
        and q.planned_public_queries <= p.planned_public_queries)
    strictly = (
        q.expected_entropy_reduction_millibits > p.expected_entropy_reduction_millibits
        or q.total_cpu_ms() < p.total_cpu_ms()
        or q.planned_peak_kib < p.planned_peak_kib
        or q.planned_public_queries < p.planned_public_queries)
    return better_or_equal and strictly

def information_efficiency(p: Proposal) -> int:
    # Millibits per combined 1 ms CPU + 1 KiB peak budget + 1 public query.
    # Memory and query weights are frozen convention; NOT actual utility
    # calibration or scientific superiority. Integer arithmetic is stable.
    denominator = p.total_cpu_ms() + p.planned_peak_kib + p.planned_public_queries
    return p.expected_entropy_reduction_millibits * 1_000_000 // max(1, denominator)

def review(raw: list[dict]) -> dict:
    if not isinstance(raw, list) or len(raw) > len(LANES) * MAX_CANDIDATES_PER_LANE:
        raise ValueError("T16_BOUNDED_PROPOSAL_PORTFOLIO")
    outcomes = []
    eligible = []
    ids = set()
    family_pairs = set()
    for index, payload in enumerate(raw):
        p = Proposal.from_dict(payload)
        if p.id in ids or (p.lane, p.family) in family_pairs:
            reason = "DUPLICATE_ID_OR_MECHANISM_FAMILY"
        else:
            reason = explain(p)
        ids.add(p.id)
        family_pairs.add((p.lane, p.family))
        outcomes.append({"proposal_id": p.id, "lane": p.lane, "family": p.family,
                         "eligibility": "ADVISORY_CANDIDATE" if reason is None else "BLOCKED",
                         "reason": reason})
        if reason is None:
            eligible.append(p)
    for lane in LANES:
        if sum(p.lane == lane for p in eligible) > MAX_CANDIDATES_PER_LANE:
            raise ValueError("T16_PER_LANE_BOUNDED")
    frontier = [p for p in eligible if not any(
        q.id != p.id and dominated(p, q) for q in eligible)]
    # No unbalanced several-small-lanes monopoly. One advisory design per
    # lane, in deterministic order; actual randomized selection remains
    # separately protected by optimizerbridge's signed assignment contract.
    candidates = sorted(frontier, key=lambda p:(-information_efficiency(p), p.id))
    winners = []
    used = set()
    spent = 0
    for p in candidates:
        if p.lane in used:
            continue
        if spent + p.total_cpu_ms() > PORTFOLIO_CPU_LIMIT_MS:
            continue
        winners.append({
            "lane": p.lane, "proposal_id": p.id, "distinct_family": p.family,
            "forecast_information_efficiency_unvalidated": information_efficiency(p),
            "planned_total_cpu_ms": p.total_cpu_ms(),
            "planned_peak_kib": p.planned_peak_kib})
        spent += p.total_cpu_ms()
        used.add(p.lane)
    return {
        "schema": "northstar.t16.optimizer.diverse-readonly-mechanism-review.v1",
        "mode": "UNVALIDATED_PROPOSAL_FORECASTS_ADVISORY_ONLY",
        "proposals_reviewed": len(outcomes),
        "ineligible_and_negative_retained": True,
        "classifications": outcomes,
        "nondominated_ids": [p.id for p in frontier],
        "advisory_designs": winners,
        "estimated_selected_cpu_ms": spent,
        "source_witness_cryptographically_verified": False,
        "prospective_randomization_authenticated": False,
        "scientific_improvement_established": False,
        "scientific_acceptance": False,
        "experiment_dispatch_authorized": False,
        "optimizer_admission": False,
        "accepted_refs_mutated": False,
        "new_controller": False,
        "paid_inference": False,
        "protected_holdouts_used": False
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposals", type=Path)
    args = parser.parse_args()
    if args.proposals is None:
        # Intentional zero-candidate readiness check. Historical negatives
        # are not auto-materialized as speculative proposal successes.
        proposals = []
    else:
        proposals = json.loads(args.proposals.read_text(encoding="utf-8"))
    print(json.dumps(review(proposals), sort_keys=True))

if __name__ == "__main__":
    main()
