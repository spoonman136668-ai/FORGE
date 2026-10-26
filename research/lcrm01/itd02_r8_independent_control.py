"""Independent conventional control runner: never impersonates native R5 custody.

Base policy must be a separately qualified conventional action function.
This adapter cannot claim matched native R5 fallback or scientific acceptance.
"""
from itd02_r8_statistical_episode import run_statistical_episode
from itd02_r8_conditional_beta import ConditionalBeta
from itd02_r8_previous_action_ablation import PreviousActionAblatedBeta

MODELS={
    "independent_conditional_beta":ConditionalBeta,
    "r8_previous_action_ablated":PreviousActionAblatedBeta,
}

def run_independent_control(family,seed,method,conventional_base_action):
    if method not in MODELS:
        raise ValueError("R8_INDEPENDENT_CONTROL_UNREGISTERED")
    if not callable(conventional_base_action):
        raise ValueError("R8_CONVENTIONAL_BASE_REQUIRED")
    row=run_statistical_episode(family,seed,MODELS[method](),
                                conventional_base_action,method)
    row["fallback_provenance"]="independent_conventional_not_native_r5"
    row["native_r5_matched"]=False
    row["scientific_accepted"]=False
    return row
