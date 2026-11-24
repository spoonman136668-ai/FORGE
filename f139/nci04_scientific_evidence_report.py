"""Unified cross-architecture scientific evidence ledger for FORGE F139.

Aggregates reproducible DEV and independent held-out OOD qualification across
all three strictly distinct non-transformer architectures:
  1. Yggdrasil  (local-learning cells, 164-byte cold-restart invariance)
  2. Wingless   (predictive causal state, learned entity bindings)
  3. TTT-Hybrid (weight/structure assimilation, bounded test-time adaptation)

Strictly read-only, deterministic, zero network calls, zero paid API calls,
`scientific_first_use: False`, `auto_promote_checkpoint: False`.
"""
from __future__ import annotations

from f139.nci04_heldout_qualifier import HELDOUT_SEEDS, qualify_pool_heldout
from f139.nci04_multi_lane_targets import get_lane_contract
from f139.nci04_native_contract import canonical, digest
from f139.nci04_scientific_evaluator import evaluate_and_rank_pool
from f139.nci04_ttt_hybrid_hypothesis import (
    qualify_ttt_hybrid_heldout, run_ttt_hybrid_preregistered_eval,
)
from f139.nci04_wingless_gen2 import (
    qualify_wingless_gen2_heldout, run_wingless_gen2_dev_eval,
)

SCHEMA = "forge.f139.cross-architecture-scientific-evidence.v1"


def build_cross_architecture_evidence_report(
    *, yggdrasil_gen1_pool: list[dict], yggdrasil_gen2_pool: list[dict],
    heldout_seeds: tuple[int, ...] = HELDOUT_SEEDS,
) -> dict:
    """Build a single SHA-256-sealed evidence snapshot across all 3 architectures."""
    ygg_contract = get_lane_contract("Yggdrasil")
    wing_contract = get_lane_contract("Wingless")
    ttt_contract = get_lane_contract("TTT-Hybrid")

    # Enforce strict architectural separation across all 3 lanes
    arch_classes = {
        ygg_contract["architecture_class"],
        wing_contract["architecture_class"],
        ttt_contract["architecture_class"],
    }
    if len(arch_classes) != 3:
        raise ValueError("F139_EVIDENCE_ARCHITECTURE_COLLAPSE")

    ygg_g1_dev = evaluate_and_rank_pool(yggdrasil_gen1_pool)
    ygg_g2_dev = evaluate_and_rank_pool(yggdrasil_gen2_pool)
    ygg_g1_ho = qualify_pool_heldout(yggdrasil_gen1_pool, heldout_seeds=heldout_seeds)
    ygg_g2_ho = qualify_pool_heldout(yggdrasil_gen2_pool, heldout_seeds=heldout_seeds)

    wing_dev = run_wingless_gen2_dev_eval()
    wing_ho = qualify_wingless_gen2_heldout(heldout_seeds=heldout_seeds)

    ttt_dev = run_ttt_hybrid_preregistered_eval()
    ttt_ho = qualify_ttt_hybrid_heldout(heldout_seeds=heldout_seeds)

    report = {
        "schema": SCHEMA,
        "distinct_architecture_count": 3,
        "heldout_seeds": list(heldout_seeds),
        "lanes": {
            "Yggdrasil": {
                "architecture_class": ygg_contract["architecture_class"],
                "gen1_dev_winners": ygg_g1_dev["winners_count"],
                "gen2_dev_winners": ygg_g2_dev["winners_count"],
                "gen1_heldout_qualified_count": ygg_g1_ho["qualified_count"],
                "gen2_heldout_qualified_count": ygg_g2_ho["qualified_count"],
                "top_gen2_heldout_id": ygg_g2_ho["top_result"]["hypothesis_id"],
                "top_gen2_heldout_utility": ygg_g2_ho["top_result"]["candidate"]["composite_utility"],
                "top_gen2_heldout_delta": ygg_g2_ho["top_result"]["total_delta_vs_strongest"],
                "top_gen2_heldout_wins": ygg_g2_ho["top_result"]["seed_wins"],
                "heldout_summary_sha256": ygg_g2_ho["summary_sha256"],
            },
            "Wingless": {
                "architecture_class": wing_contract["architecture_class"],
                "target_commit": wing_contract["active_target_commit"],
                "dev_winners": wing_dev["winners_vs_baseline"],
                "heldout_qualified_policies": wing_ho["qualified_policies"],
                "top_heldout_policy": wing_ho["evaluations"][0]["policy"],
                "top_heldout_delta": wing_ho["evaluations"][0]["total_delta_vs_baseline"],
                "top_heldout_wins": wing_ho["evaluations"][0]["seed_wins"],
                "heldout_qualification_sha256": wing_ho["qualification_sha256"],
            },
            "TTT-Hybrid": {
                "architecture_class": ttt_contract["architecture_class"],
                "dev_winners": ttt_dev["winners_vs_controls"],
                "heldout_qualified_policies": ttt_ho["qualified_policies"],
                "top_heldout_policy": ttt_ho["evaluations"][0]["policy"],
                "top_heldout_mean_delta": ttt_ho["evaluations"][0]["mean_delta_vs_strongest"],
                "top_heldout_wins": ttt_ho["evaluations"][0]["seed_wins"],
                "heldout_qualification_sha256": ttt_ho["qualification_sha256"],
            },
        },
        "paid_model_calls": 0,
        "scientific_first_use": False,
        "auto_promote_checkpoint": False,
    }
    report["evidence_sha256"] = digest(canonical(report))
    return report
