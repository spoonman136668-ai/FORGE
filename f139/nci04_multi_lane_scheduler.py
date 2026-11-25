"""Evidence-Conditioned Multi-Lane Scheduler for FORGE F139 (Gate 19).

Coordinates bounded research & training allocation across FORGE's distinct
theoretical tracks (`Yggdrasil`, `Wingless`, `TTT-Hybrid`, `LLM-Experimental`,
`GLM-WorldModel`, `AGI-Kernel`) while preserving strict architectural isolation.

Scheduling policy (deterministic, zero paid API calls):
1. Respects per-lane compute budgets (`lane_budgets`); skips exhausted lanes.
2. Applies automatic failure backoff to lanes with >= `max_consecutive_failures`.
3. Prioritizes under-explored active lanes first, then lanes with the strongest
   recent verified/qualified momentum, breaking ties deterministically.
"""
from __future__ import annotations

from pathlib import Path

from f139.nci04_evidence_store import summarize_evidence_store
from f139.nci04_experiment_runner import SUPPORTED_METHOD_FAMILIES
from f139.nci04_native_contract import canonical, digest

SCHEMA = "forge.f139.multi-lane-schedule-decision.v1"
DEFAULT_LANE_ORDER = (
    "Yggdrasil",
    "Wingless",
    "TTT-Hybrid",
    "LLM-Experimental",
    "GLM-WorldModel",
    "AGI-Kernel",
)


class MultiLaneSchedulerDenied(ValueError):
    """Fail-closed denial for invalid lane budgets or unknown lanes."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise MultiLaneSchedulerDenied("F139_SCHEDULER_" + reason)


def select_next_lane(
    *,
    lane_budgets: dict[str, int] | None = None,
    evidence_store_path: Path | None = None,
    max_consecutive_failures: int = 3,
) -> dict:
    """Deterministically select the next research lane from evidence & budgets."""
    budgets = (
        {lane: 10 for lane in DEFAULT_LANE_ORDER}
        if lane_budgets is None
        else dict(lane_budgets)
    )
    need(type(budgets) is dict and len(budgets) > 0, "EMPTY_LANE_BUDGETS")
    for lane, cap in budgets.items():
        need(lane in SUPPORTED_METHOD_FAMILIES, "UNKNOWN_LANE")
        need(type(cap) is int and 0 <= cap <= 10000, "INVALID_LANE_BUDGET")
    need(type(max_consecutive_failures) is int and 1 <= max_consecutive_failures <= 20,
         "MAX_FAILURES_INVALID")

    summary = (
        summarize_evidence_store(evidence_store_path)
        if evidence_store_path is not None
        else {"by_family": {}, "total_records": 0, "head_record_sha256": "0" * 64}
    )
    by_family = summary["by_family"]

    eligible: list[dict] = []
    skipped: dict[str, str] = {}
    for idx, lane in enumerate(DEFAULT_LANE_ORDER):
        if lane not in budgets:
            continue
        cap = budgets[lane]
        stats = by_family.get(lane, {
            "total": 0, "verified": 0, "negative": 0,
            "qualified": 0, "rejected": 0, "consecutive_failures": 0,
        })
        used = stats["total"]
        remaining = cap - used
        if remaining <= 0:
            skipped[lane] = "budget_exhausted"
            continue
        if stats["consecutive_failures"] >= max_consecutive_failures:
            skipped[lane] = "failure_backoff"
            continue
        eligible.append({
            "lane": lane,
            "used": used,
            "remaining": remaining,
            "verified_or_qualified": stats["verified"] + stats["qualified"],
            "consecutive_failures": stats["consecutive_failures"],
            "tie_index": idx,
        })

    # Prefer least-explored eligible lane with fewest consecutive failures
    eligible.sort(
        key=lambda e: (
            e["consecutive_failures"],
            e["used"],
            -e["verified_or_qualified"],
            e["tie_index"],
        )
    )
    selected = eligible[0]["lane"] if eligible else None

    decision = {
        "schema": SCHEMA,
        "selected_lane": selected,
        "eligible_lanes": [e["lane"] for e in eligible],
        "skipped_lanes": skipped,
        "evidence_records_considered": summary["total_records"],
        "evidence_head_sha256": summary["head_record_sha256"],
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    decision["decision_sha256"] = digest(canonical(decision))
    return decision
