"""Frozen R8 cohort adapter for the existing FIT-trained six-field control.

Reuses the original F4 policy and authentic MiniGrid episode implementation.
No FIT training, environment reset, or scientific run occurs on import.
"""
from itd02_r8_episode_contract import validate_episode_request

def run_sixfield(family,seed,learned):
    validate_episode_request(family,seed,"wingless_r8_online_beliefs")  # shared heldout cohort guard only
    if learned is None:
        raise ValueError("R8_SIXFIELD_FIT_MODEL_MISSING")
    from k4t_f4_original_r5_cost import sixfield_episode
    result=sixfield_episode(family,seed,learned)
    if result.get("method")!="sixfield_fit_model_route":
        raise ValueError("R8_SIXFIELD_METHOD_DRIFT")
    result["fit_provenance"]="original_F4_sixfield_policy_fresh_R8_FIT_required"
    result["scientific_accepted"]=False
    return result
