"""R36/F3 frozen-method fidelity admission. Fail closed on surrogate implementations.

This guard is deliberately separate from passing method-level unit tests: a
reproducible surrogate is not equivalent to a preregistered scientific method.
"""
import json
from pathlib import Path

METHOD_REQUIREMENTS = {
    "W36-C1": "rank_limited_learned_16_to_8_to_16_projection",
    "W36-C2": "per_source_gradient_conflict_projection",
    "W36-C3": "trainable_two_state_risk_consumer",
    "W36-C4": "hard_example_balanced_memory_32_per_source",
    "YF3-C1": "trained_order_with_pinned_simulator_reads",
    "YF3-C2": "retained_state_online_priority_with_pinned_simulator_reads",
    "YF3-C3": "two_step_online_change_point_with_pinned_simulator_reads",
    "YF3-C4": "adaptive_sparse_gate_with_pinned_simulator_reads",
}
# Explicit current implementation coverage, not assertions of scientific validity.
IMPLEMENTED = {
    "W36-C1": "rank8_trainable_joint_projection_with_source_discrepancy_penalty",
    "W36-C2": "deterministic_pairwise_conflicting_gradient_projection",
    "W36-C3": "learned_soft_two_state_risk_consumer",
    "W36-C4": "hardest_32_examples_source_balanced_episodic_memory",
    "YF3-C1": "development_label_frequency_static_read_plan",
    "YF3-C2": "development_trend_static_read_plan",
    "YF3-C3": "development_delta_static_read_plan",
    "YF3-C4": "development_sparse_static_read_plan",
}
def audit(manifest):
    if manifest.get("schema") != "forge.r36-f3.pre-execution-hypothesis-portfolio.v1":
        raise ValueError("R36_F3_WRONG_FROZEN_SCHEMA")
    expected = {
        **{x["id"]:x["method"] for x in manifest["wingless"]["candidates"]},
        **{x["id"]:x["method"] for x in manifest["yggdrasil"]["candidates"]},
    }
    if set(expected) != set(METHOD_REQUIREMENTS) or set(expected) != set(IMPLEMENTED):
        raise ValueError("R36_F3_CANDIDATE_IDENTITY_DRIFT")
    rows = [{
        "id": key,
        "frozen_method": expected[key],
        "required_mechanism": METHOD_REQUIREMENTS[key],
        "implemented_mechanism": IMPLEMENTED[key],
        "status": "UNQUALIFIED_METHOD_FIDELITY",
    } for key in sorted(expected)]
    return {
        "schema":"forge.r36-f3.method-fidelity-audit.v1",
        "status":"BLOCKED_UNQUALIFIED_METHOD_FIDELITY",
        "candidates":rows,
        "scientific_candidate_selection_authorized":False,
        "sealed_original_authorized":False,
        "originals_executed":0,
        "first_use_claims_consumed":0,
    }
if __name__ == "__main__":
    m = json.loads(Path(__file__).with_name("frozen_portfolio.json").read_bytes())
    result = audit(m)
    print(json.dumps(result,sort_keys=True))
