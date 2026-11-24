"""Distinct, non-transformer research lane registry for FORGE F139.

Preserves Yggdrasil, Wingless, and TTT-Hybrid as separate architectural tracks.
Enforces fail-closed isolation against:
- collapsing distinct architectures into one model,
- replacing core foundations with conventional transformer/token layers,
- KTRADE or K-Terminal cross-contamination, and
- unauthorized paid model API calls or automatic checkpoint promotion.
"""
from __future__ import annotations

from f139.nci04_native_contract import canonical, digest

SCHEMA = "forge.f139.multi-lane-target-registry.v1"

FORBIDDEN_TERMS = frozenset({
    "ktrade", "k-terminal", "k_terminal",
    "transformer", "multiheadattention", "self_attention", "openai_api_key",
})

LANES: dict[str, dict] = {
    "Yggdrasil": {
        "lane": "Yggdrasil",
        "architecture_class": "non_transformer_local_learning_cells",
        "objectives": (
            "distributed_persistent_memory",
            "local_adaptation_and_specialization",
            "cumulative_knowledge_without_global_weight_copy",
            "cold_restart_retention",
            "unfamiliar_causal_transfer",
        ),
        "active_target_repo": "spoonman136668-ai/Yggdrasil",
        "active_target_path": "yggdrasil/public_causal_cells.py",
        "matched_controls": ("PublicCausalCells.choose", "PublicCausalCells.choose_wilson"),
        "live_hypothesis_enabled": True,
    },
    "Wingless": {
        "lane": "Wingless",
        "architecture_class": "non_transformer_predictive_causal_state",
        "objectives": (
            "learned_entity_bindings",
            "predictive_causal_representation",
            "persistent_structured_knowledge",
            "self_organizing_state_without_global_oracle",
        ),
        "active_target_repo": "spoonman136668-ai/Wingless",
        "active_target_path": None,  # Requires separately pinned target blob before live execution
        "matched_controls": ("predictive_state_baseline",),
        "live_hypothesis_enabled": False,
    },
    "TTT-Hybrid": {
        "lane": "TTT-Hybrid",
        "architecture_class": "hybrid_weight_structure_assimilation",
        "objectives": (
            "weight_and_structure_assimilation",
            "bounded_test_time_adaptation",
            "persistent_memory_integration_without_homogenization",
        ),
        "active_target_repo": "spoonman136668-ai/FORGE",
        "active_target_path": None,  # Requires separately pinned target blob before live execution
        "matched_controls": ("bounded_adaptation_control",),
        "live_hypothesis_enabled": False,
    },
}


class LaneRegistryDenied(ValueError):
    """Fail-closed denial for cross-lane contamination or policy violation."""


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise LaneRegistryDenied("F139_LANE_" + reason)


def get_lane_contract(lane: str) -> dict:
    """Return an immutable copy of a registered research lane contract."""
    need(type(lane) is str and lane in LANES, "UNKNOWN_RESEARCH_LANE")
    entry = dict(LANES[lane])
    entry["objectives"] = list(entry["objectives"])
    entry["matched_controls"] = list(entry["matched_controls"])
    entry["schema"] = SCHEMA
    entry["contract_sha256"] = digest(canonical(entry))
    return entry


def validate_lane_isolation(*, lane: str, candidate_text: str,
                            target_repo: str,
                            paid_model_calls: int = 0,
                            scientific_first_use: bool = False) -> dict:
    """Fail-closed check ensuring candidate respects lane boundaries & constraints."""
    contract = get_lane_contract(lane)
    need(type(candidate_text) is str and 0 < len(candidate_text) <= 65536,
         "CANDIDATE_TEXT_INVALID")
    need(type(target_repo) is str and target_repo == contract["active_target_repo"],
         "CROSS_REPO_OR_LANE_CONTAMINATION")
    need(type(paid_model_calls) is int and paid_model_calls == 0,
         "PAID_MODEL_CALLS_FORBIDDEN")
    need(scientific_first_use is False, "SCIENTIFIC_FIRST_USE_UNQUALIFIED")
    lowered = candidate_text.lower()
    for term in FORBIDDEN_TERMS:
        need(term not in lowered, "FORBIDDEN_CONTAMINATION_OR_TRANSFORMER_TERM")
    return contract
