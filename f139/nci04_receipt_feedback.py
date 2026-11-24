"""Closed-loop post-receipt scientific feedback and next-generation synthesis.

Ingests immutable SQLite lifecycle entries (V1/V2/V3 VERIFIED and NEGATIVE
terminals) to compute empirical per-axis posteriors, combine executed receipt
feedback with preregistered benchmark rankings, and synthesize evidence-driven
next-generation hypothesis directions once a pool is explored.

Design boundaries:
- Strictly read-only, deterministic, zero network calls, zero paid API calls,
  zero SQLite mutations, and zero automatic checkpoint promotion.
- Retains 100% of failed (`NEGATIVE`) and consumed trials; never deletes or
  replays history.
"""
from __future__ import annotations

import re

from f139.nci04_hypothesis_engine import (
    ESTIMATORS, SUPPORT_GATES, TIE_POLICIES, select_next_hypothesis,
)
from f139.nci04_native_contract import canonical, digest
from f139.nci04_scientific_evaluator import evaluate_and_rank_pool

SCHEMA = "forge.f139.closed-loop-receipt-feedback.v1"
HYP_RECIPE_RE = re.compile(
    r"^ygg-(jeffreys|asymmetric_loss|se_margin|lcb_15)-"
    r"(min1|min4|min8|balanced2x)-"
    r"(abstain|least_observed)-v1\Z"
)
HYP_GEN2_RECIPE_RE = re.compile(
    r"^ygg-gen2-(z_5_4|z_7_4|agresti_coull_1)-"
    r"(min2|balanced_3_2|balanced_3_1)-"
    r"(abstain|least_observed)-v1\Z"
)


class ReceiptFeedbackDenied(ValueError):
    """Fail-closed denial for malformed lifecycle entries or feedback inputs."""


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise ReceiptFeedbackDenied("F139_RECEIPT_FEEDBACK_" + reason)


def parse_hypothesis_recipe(recipe: str) -> dict | None:
    """Parse a V3 Gen-1 or Gen-2 hypothesis recipe ID into its 3 scientific axes."""
    if type(recipe) is not str:
        return None
    m = HYP_RECIPE_RE.fullmatch(recipe) or HYP_GEN2_RECIPE_RE.fullmatch(recipe)
    if not m:
        return None
    return {
        "estimator": m.group(1),
        "support_gate": m.group(2),
        "tie_policy": m.group(3),
    }


def summarize_receipt_ledger(entries: list[dict]) -> dict:
    """Summarize immutable lifecycle entries into per-axis verified/negative stats."""
    need(type(entries) is list and 0 < len(entries) <= 4096, "ENTRIES_INVALID")
    verified_axes: list[dict] = []
    failed_axes: list[dict] = []
    axis_stats: dict[str, dict[str, dict[str, int]]] = {
        "estimator": {k: {"verified": 0, "negative": 0} for k, _ in ESTIMATORS},
        "support_gate": {k: {"verified": 0, "negative": 0} for k, _ in SUPPORT_GATES},
        "tie_policy": {k: {"verified": 0, "negative": 0} for k, _ in TIE_POLICIES},
    }
    total_verified = 0
    total_negative = 0
    v3_verified = 0
    v3_negative = 0

    for entry in entries:
        need(type(entry) is dict, "ENTRY_NOT_DICT")
        is_neg = bool(entry.get("negative")) or entry.get("stage") == "NEGATIVE"
        is_ver = (not is_neg) and entry.get("stage") == "VERIFIED"
        if is_ver:
            total_verified += 1
        elif is_neg:
            total_negative += 1

        # Match recipe either from entry's publication_attempt or record metadata
        attempt = entry.get("publication_attempt")
        recipe = (attempt.get("recipe") if type(attempt) is dict else None)
        if recipe is None and type(entry.get("record")) is dict:
            recipe = entry["record"].get("recipe")
        axes = parse_hypothesis_recipe(recipe) if recipe is not None else None
        if axes is None:
            continue
        if is_ver:
            v3_verified += 1
            verified_axes.append(axes)
            for dim, val in axes.items():
                axis_stats[dim].setdefault(val, {"verified": 0, "negative": 0})
                axis_stats[dim][val]["verified"] += 1
        elif is_neg:
            v3_negative += 1
            failed_axes.append(axes)
            for dim, val in axes.items():
                axis_stats[dim].setdefault(val, {"verified": 0, "negative": 0})
                axis_stats[dim][val]["negative"] += 1

    summary = {
        "schema": SCHEMA,
        "total_entries": len(entries),
        "total_verified": total_verified,
        "total_negative": total_negative,
        "v3_verified": v3_verified,
        "v3_negative": v3_negative,
        "verified_axes": verified_axes,
        "failed_axes": failed_axes,
        "axis_stats": axis_stats,
        "retained_all_failures": True,
    }
    summary["summary_sha256"] = digest(canonical(summary))
    return summary


def rank_pool_with_receipt_feedback(pool: list[dict], entries: list[dict]) -> dict:
    """Combine real executed SQLite receipt outcomes with preregistered evaluation."""
    need(type(pool) is list and len(pool) > 0, "EMPTY_POOL")
    ledger = summarize_receipt_ledger(entries)
    eval_summary = evaluate_and_rank_pool(pool)
    eval_by_after = {e["after_sha256"]: e for e in eval_summary["evaluations"]}

    failed_est = {a["estimator"] for a in ledger["failed_axes"]}
    failed_sup = {a["support_gate"] for a in ledger["failed_axes"]}
    failed_tie = {a["tie_policy"] for a in ledger["failed_axes"]}

    passing_pool = [
        item for item in pool
        if eval_by_after[item["plan"]["after_sha256"]]["negative_control_pass"]
    ]
    if not passing_pool:
        return {
            "schema": SCHEMA,
            "ledger_summary_sha256": ledger["summary_sha256"],
            "selected_hypothesis_id": None,
            "selected_after_sha256": None,
            "passing_candidates": 0,
            "scientific_first_use": False,
        }

    def combined_key(item: dict):
        ev = eval_by_after[item["plan"]["after_sha256"]]
        axes = item["preregistration"]["axes"]
        real_fail_overlap = (
            int(axes["estimator"] in failed_est)
            + int(axes["support_gate"] in failed_sup)
            + int(axes["tie_policy"] in failed_tie)
        )
        return (
            real_fail_overlap,
            not ev["beats_strongest_control"],
            -ev["delta_vs_strongest"],
            ev["candidate"]["action_null_false_choices"],
            item["plan"]["after_sha256"],
        )

    ordered = sorted(passing_pool, key=combined_key)
    top = ordered[0]
    ablation_hint = select_next_hypothesis(
        passing_pool,
        verified_axes=ledger["verified_axes"],
        failed_axes=ledger["failed_axes"],
    )
    decision = {
        "schema": SCHEMA,
        "ledger_summary_sha256": ledger["summary_sha256"],
        "passing_candidates": len(passing_pool),
        "selected_hypothesis_id": top["preregistration"]["hypothesis_id"],
        "selected_after_sha256": top["plan"]["after_sha256"],
        "ablation_recommendation_id": (
            ablation_hint["preregistration"]["hypothesis_id"]
            if ablation_hint is not None else None
        ),
        "scientific_first_use": False,
        "auto_promote_checkpoint": False,
    }
    decision["decision_sha256"] = digest(canonical(decision))
    return decision


def propose_next_generation_axes(ledger_summary: dict) -> dict:
    """Synthesize next-generation research axes from accumulated receipt evidence."""
    need(type(ledger_summary) is dict
         and ledger_summary.get("schema") == SCHEMA
         and type(ledger_summary.get("axis_stats")) is dict,
         "LEDGER_SUMMARY_INVALID")
    stats = ledger_summary["axis_stats"]
    clean_estimators = [
        k for k, v in stats["estimator"].items()
        if v["verified"] > 0 and v["negative"] == 0
    ]
    failed_estimators = [
        k for k, v in stats["estimator"].items() if v["negative"] > 0
    ]
    proposals: list[dict] = []
    if any(e in clean_estimators for e in ("se_margin", "lcb_15")):
        proposals.append({
            "family": "rational_confidence_refinement",
            "rationale": "se_margin/lcb_15 verified without negatives; test z in {1.25, 1.75} with exact integer arithmetic",
            "candidate_parameters": ["z_5_4", "z_7_4"],
        })
    if stats["support_gate"]["balanced2x"]["verified"] > 0 and stats["support_gate"]["balanced2x"]["negative"] == 0:
        proposals.append({
            "family": "imbalance_ratio_sweep",
            "rationale": "balanced2x verified cleanly; test tighter (3:2) and looser (3:1) sampling-imbalance guards",
            "candidate_parameters": ["balanced_3_2", "balanced_3_1"],
        })
    if not proposals:
        proposals.append({
            "family": "orthogonal_local_recency_exploration",
            "rationale": "No verified clean estimator yet; explore bounded local-cell exponential recency with stationary negative controls",
            "candidate_parameters": ["recency_half_4", "recency_half_8"],
        })
    plan = {
        "schema": SCHEMA,
        "source_summary_sha256": ledger_summary["summary_sha256"],
        "clean_verified_estimators": sorted(clean_estimators),
        "retained_failed_estimators": sorted(failed_estimators),
        "next_generation_proposals": proposals,
        "scientific_first_use": False,
        "paid_model_calls": 0,
    }
    plan["plan_sha256"] = digest(canonical(plan))
    return plan
