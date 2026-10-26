"""R8 comparator coverage gate: fail closed before any original-world cohort."""
import json
from pathlib import Path
from itd02_r8_original_world_preflight import preflight

FROZEN=Path(__file__).with_name("itd02_r8_frozen_original_minigrid_01.json")
REQUIRED={
 "wingless_r8_online_beliefs",
 "wingless_r5_cost_frontier",
 "independent_conditional_beta",
 "sixfield_fit_model_route",
 "fit_dynamics_bfs_equal_information",
 "r8_previous_action_ablated",
}
def validate_comparator_coverage(implementations):
    preflight()
    if not isinstance(implementations,dict) or set(implementations)!=REQUIRED:
        raise ValueError("R8_COMPARATOR_COVERAGE_INCOMPLETE")
    if not all(callable(v) for v in implementations.values()):
        raise ValueError("R8_COMPARATOR_NOT_EXECUTABLE")
    return {"result":"R8_COMPARATOR_COVERAGE_COMPLETE",
            "method_count":len(REQUIRED),
            "protocol_id":json.loads(FROZEN.read_text())["protocol_id"],
            "scientific_first_use":False,"scientific_accepted":False}
