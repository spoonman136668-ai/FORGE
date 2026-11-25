"""Multi-Objective Pareto Frontier & Ablation Comparator for FORGE F139 (Gate 21).

Compares arbitrary heterogeneous architectures, structures, and training runs
across multiple competing objectives simultaneously (e.g., validation loss,
held-out OOD score, latency in ms, fixed state/checkpoint bytes) to identify
the exact non-dominated Pareto frontier ("what actually stuck").

Strictly deterministic, pure stdlib, zero paid API calls.
"""
from __future__ import annotations

from f139.nci04_native_contract import canonical, digest

PARETO_SCHEMA = "forge.f139.pareto-frontier-report.v1"


class ParetoComparatorDenied(ValueError):
    """Fail-closed denial for invalid objectives or malformed candidate metrics."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise ParetoComparatorDenied("F139_PARETO_" + reason)


def _dominates(a: dict, b: dict, objectives: dict[str, str]) -> bool:
    """Return True if candidate `a` Pareto-dominates `b` across all objectives."""
    strictly_better = False
    for metric, direction in objectives.items():
        va = float(a["metrics"][metric])
        vb = float(b["metrics"][metric])
        if direction == "max":
            if va < vb:
                return False
            if va > vb:
                strictly_better = True
        else:  # "min"
            if va > vb:
                return False
            if va < vb:
                strictly_better = True
    return strictly_better


def compute_pareto_frontier(
    candidates: list[dict],
    *,
    objectives: dict[str, str],
) -> dict:
    """Compute the exact non-dominated Pareto frontier across arbitrary objectives.

    Each candidate dict must have `{"id": str, "metrics": {metric: number, ...}}`.
    `objectives` maps `{metric_name: "min" | "max"}`.
    """
    need(type(candidates) is list and len(candidates) > 0, "EMPTY_CANDIDATES")
    need(type(objectives) is dict and len(objectives) >= 1, "EMPTY_OBJECTIVES")
    for m, d in objectives.items():
        need(type(m) is str and len(m) > 0 and d in ("min", "max"), "OBJECTIVE_INVALID")

    valid: list[dict] = []
    skipped: list[str] = []
    for item in candidates:
        need(type(item) is dict and type(item.get("id")) is str, "CANDIDATE_INVALID")
        metrics = item.get("metrics")
        if type(metrics) is not dict or not all(
            m in metrics and type(metrics[m]) in (int, float) for m in objectives
        ):
            skipped.append(item["id"])
            continue
        valid.append(item)

    frontier: list[dict] = []
    dominated: list[dict] = []
    for i, cand in enumerate(valid):
        is_dom = any(
            i != j and _dominates(other, cand, objectives)
            for j, other in enumerate(valid)
        )
        if is_dom:
            dominated.append(cand)
        else:
            frontier.append(cand)

    first_metric = next(iter(objectives))
    first_dir = objectives[first_metric]
    frontier.sort(
        key=lambda c: (
            -float(c["metrics"][first_metric]) if first_dir == "max" else float(c["metrics"][first_metric]),
            c["id"],
        )
    )

    report = {
        "schema": PARETO_SCHEMA,
        "objectives": dict(objectives),
        "evaluated_count": len(valid),
        "skipped_incomplete_ids": skipped,
        "frontier_count": len(frontier),
        "dominated_count": len(dominated),
        "frontier_ids": [c["id"] for c in frontier],
        "frontier": [
            {"id": c["id"], "metrics": {m: c["metrics"][m] for m in objectives}}
            for c in frontier
        ],
        "dominated_ids": sorted(c["id"] for c in dominated),
        "paid_model_calls": 0,
    }
    report["report_sha256"] = digest(canonical(report))
    return report


def format_pareto_markdown(report: dict) -> str:
    """Render a compact Markdown comparison table of the Pareto frontier."""
    objs = report["objectives"]
    cols = list(objs.keys())
    header = "| Candidate | " + " | ".join(f"{c} ({objs[c]})" for c in cols) + " |"
    sep = "| :--- | " + " | ".join(":---:" for _ in cols) + " |"
    rows = [header, sep]
    for item in report["frontier"]:
        vals = " | ".join(f"{item['metrics'][c]:.6g}" for c in cols)
        rows.append(f"| `{item['id']}` | {vals} |")
    return "\n".join(rows)
