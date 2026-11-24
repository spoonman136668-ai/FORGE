"""FORGE Multi-Trial Experimental Research & Training Campaign Orchestrator (Gate 15).

Orchestrates bounded, multi-trial experimental research and training campaigns
across any supported FORGE theoretical method family (`Yggdrasil`, `Wingless`,
`TTT-Hybrid`, `LLM-Experimental`, `GLM-WorldModel`, `AGI-Kernel`) using
Gate 14's isolated `run_bounded_experiment` engine.

Hard boundaries:
- Enforces finite trial caps and total wall-clock budgets.
- Retains 100% of verified and negative (`NEGATIVE`) trial receipts in an
  immutable SHA-256-sealed `CampaignLedger` (never deletes or replays failed trials).
- Zero paid model calls, `auto_promote_checkpoint: False`, `scientific_first_use: False`.
"""
from __future__ import annotations

from pathlib import Path

from f139.nci04_experiment_runner import (
    SPEC_SCHEMA, run_bounded_experiment,
)
from f139.nci04_native_contract import canonical, digest

CAMPAIGN_SCHEMA = "forge.f139.training-campaign-ledger.v1"
MAX_CAMPAIGN_TRIALS = 32
MAX_TOTAL_BUDGET_MS = 1_800_000  # 30 minutes hard ceiling


class TrainingCampaignDenied(ValueError):
    """Fail-closed denial for invalid campaign configuration or budget violation."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise TrainingCampaignDenied("F139_CAMPAIGN_" + reason)


def run_training_campaign(
    *,
    campaign_id: str,
    baseline_spec: dict,
    candidate_specs: list[dict],
    source_root: Path,
    max_total_elapsed_ms: int = 300_000,
) -> dict:
    """Execute a bounded baseline + multi-candidate training/research campaign."""
    need(type(campaign_id) is str and 3 <= len(campaign_id) <= 128, "CAMPAIGN_ID_INVALID")
    need(type(baseline_spec) is dict and baseline_spec.get("schema") == SPEC_SCHEMA,
         "BASELINE_SPEC_INVALID")
    need(type(candidate_specs) is list and 1 <= len(candidate_specs) <= MAX_CAMPAIGN_TRIALS,
         "CANDIDATE_SPECS_INVALID")
    need(type(max_total_elapsed_ms) is int and 1000 <= max_total_elapsed_ms <= MAX_TOTAL_BUDGET_MS,
         "BUDGET_MS_INVALID")

    seen_ids = {baseline_spec["experiment_id"]}
    for spec in candidate_specs:
        need(type(spec) is dict and spec.get("schema") == SPEC_SCHEMA, "CANDIDATE_SPEC_INVALID")
        need(spec["experiment_id"] not in seen_ids, "DUPLICATE_EXPERIMENT_ID")
        need(spec["primary_metric"] == baseline_spec["primary_metric"]
             and spec["higher_is_better"] == baseline_spec["higher_is_better"],
             "METRIC_CONTRACT_MISMATCH")
        seen_ids.add(spec["experiment_id"])

    baseline_receipt = run_bounded_experiment(baseline_spec, source_root=source_root)
    total_elapsed_ms = baseline_receipt["elapsed_ms"]

    trial_receipts: list[dict] = []
    budget_exhausted = False
    for spec in candidate_specs:
        if total_elapsed_ms >= max_total_elapsed_ms:
            budget_exhausted = True
            break
        rcpt = run_bounded_experiment(
            spec, source_root=source_root, baseline_receipt=baseline_receipt
        )
        trial_receipts.append(rcpt)
        total_elapsed_ms += rcpt["elapsed_ms"]

    verified_trials = [r for r in trial_receipts if r["status"] == "VERIFIED"]
    negative_trials = [r for r in trial_receipts if r["status"] != "VERIFIED"]
    winners = [r for r in verified_trials if r["beats_baseline"] is True]

    higher = baseline_spec["higher_is_better"]
    winners.sort(
        key=lambda r: (
            -(r["delta_vs_baseline"] if higher else -r["delta_vs_baseline"]),
            r["experiment_id"],
        )
    )

    ledger = {
        "schema": CAMPAIGN_SCHEMA,
        "campaign_id": campaign_id,
        "method_family": baseline_spec["method_family"],
        "primary_metric": baseline_spec["primary_metric"],
        "higher_is_better": higher,
        "baseline_receipt": baseline_receipt,
        "trial_receipts": trial_receipts,
        "total_trials_executed": len(trial_receipts),
        "verified_count": len(verified_trials),
        "negative_count": len(negative_trials),
        "retained_all_failures": True,
        "budget_exhausted": budget_exhausted,
        "total_elapsed_ms": total_elapsed_ms,
        "winning_experiment_ids": [r["experiment_id"] for r in winners],
        "best_experiment_id": winners[0]["experiment_id"] if winners else None,
        "best_delta_vs_baseline": winners[0]["delta_vs_baseline"] if winners else None,
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    ledger["ledger_sha256"] = digest(canonical(ledger))
    return ledger
