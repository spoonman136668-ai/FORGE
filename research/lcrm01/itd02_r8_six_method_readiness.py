"""Source-only audit of the six R8 comparators; no heldout environment access.

This gate deliberately distinguishes an implemented method from an actually
qualified trained method. It must never authorize scientific first use.
"""
from itd02_r8_comparator_gate import REQUIRED
from itd02_r8_original_world_preflight import preflight

STATUS = {
    "wingless_r8_online_beliefs": ("BLOCKED_NATIVE_FIT_SNAPSHOT", "Native R8 FIT update and restored snapshot not qualified"),
    "wingless_r5_cost_frontier": ("BLOCKED_NATIVE_R5_PIN", "R5 source-identity and matched native baseline run not qualified"),
    "independent_conditional_beta": ("BLOCKED_BASE_POLICY", "Independent conventional base policy and equal-information matching not qualified"),
    "sixfield_fit_model_route": ("READY_SOURCE_ONLY", "FIT-trained model hash and preserved-artifact reconstruction verified"),
    "fit_dynamics_bfs_equal_information": ("BLOCKED_EQUAL_INFORMATION_BFS", "Fitted dynamics BFS controller not wired to identical public information"),
    "r8_previous_action_ablated": ("BLOCKED_NATIVE_ABLATION", "Existing statistical ablation is not native R8 previous-action ablation"),
}

def assess_readiness():
    preflight()
    if set(STATUS) != REQUIRED:
        raise ValueError("R8_COMPARATOR_MANIFEST_DRIFT")
    methods = {k: {"status": STATUS[k][0], "reason": STATUS[k][1]}
               for k in sorted(STATUS)}
    blockers = sorted(k for k in STATUS if STATUS[k][0] != "READY_SOURCE_ONLY")
    return {"gate": "ITD02_R8_SIX_METHOD_READINESS",
            "methods": methods,
            "methods_count": len(methods),
            "blocked": blockers,
            "blocked_count": len(blockers),
            "source_only_ready_count": len(methods) - len(blockers),
            "original_check_dev_executed": False,
            "first_use_authorized": False,
            "scientific_accepted": False,
            "full_comparison_ready": False}

def require_complete_readiness():
    result = assess_readiness()
    if result["blocked"]:
        raise RuntimeError("R8_SIX_METHODS_NOT_QUALIFIED:" + ",".join(result["blocked"]))
    return result

if __name__ == "__main__":
    import json
    print(json.dumps(assess_readiness(), sort_keys=True))
