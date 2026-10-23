"""Independent Windows/Linux O15 public-original source and result reconciliation."""
import json,math,sys
from pathlib import Path
from runner import ARMS,DELAYS,REPS,FIT_N,DEV_N

def validate(x):
    if (x["schema"]!="forge.optimizer.o15.external-reward-delayed-public-memory-v1" or
        x["FSA_Q21_HELD_first_use_consumed"]!=0 or
        x["scientific_architecture_promoted"] is not False or
        x["original_source_real_total_resets"]!=1296 or
        x["original_source_REAL_legal_step_calls"]!=66096 or
        len(x["scenarios"])!=6 or
        x["disposition"] not in ("O15_PUBLIC_HANDDESIGNED_LOCAL_RELEVANCE_LEARNING_SUPPORTED_NO_SUPERIORITY","O15_PUBLIC_LOCAL_LAG_SELECTION_NO_GO")):
        raise ValueError("O15_ORIGINAL_SCIENCE_CUSTODY_INVALID")
    for sc in x["scenarios"]:
        if (sc["k_true_source_constructor_auditor_only"] not in DELAYS or
            sc["replica"] not in REPS or
            sc["shared_FIT_original_real_reset_episodes"]!=FIT_N or
            set(sc["DEV_original_source_actual_reward_by_arm"])!=set(ARMS)):
            raise ValueError("O15_ORIGINAL_ROLE_ARM_MISMATCH")
        for a in ARMS:
            v=sc["DEV_original_source_actual_reward_by_arm"][a]
            if (v["original_real_DEV_episodes"]!=DEV_N or
                v["source_original_correct_scored_rate"]<0 or
                v["source_original_correct_scored_rate"]>1 or
                not math.isfinite(v["source_original_reward_per_scored_action"])):
                raise ValueError("O15_ORIGINAL_DEV_SCORE_INVALID")

def compare(a,b):
    validate(a);validate(b)
    if (a["disposition"]!=b["disposition"] or
        a["source_git_blobs"]!=b["source_git_blobs"] or
        a["shared_FIT_public_source_SHA256"]!=b["shared_FIT_public_source_SHA256"]):
        raise ValueError("O15_CROSS_OS_SOURCE_IDENTITY_DRIFT")
    matching=0
    for s,t in zip(a["scenarios"],b["scenarios"]):
        if (s["k_true_source_constructor_auditor_only"],s["replica"])!=(
            t["k_true_source_constructor_auditor_only"],t["replica"]):
            raise ValueError("O15_CROSS_OS_SCENARIO_ID_DRIFT")
        if (s["shared_FIT_public_source_identity_SHA256"]!=
            t["shared_FIT_public_source_identity_SHA256"] or
            s["original_SOURCE_actual_learned_lag"]!=t["original_SOURCE_actual_learned_lag"]):
            raise ValueError("O15_CROSS_OS_FIT_OR_LAG_DRIFT")
        for arm in ARMS:
            x=s["DEV_original_source_actual_reward_by_arm"][arm]
            y=t["DEV_original_source_actual_reward_by_arm"][arm]
            if (x["actual_source_PUBLIC_observation_hashes"]!=y["actual_source_PUBLIC_observation_hashes"] or
                abs(x["source_original_reward_per_scored_action"]-
                    y["source_original_reward_per_scored_action"])>1e-8):
                raise ValueError("O15_CROSS_OS_ORIGINAL_REWARD_OR_OBS_DRIFT")
            matching+=1
    return {"source":"POPgym original externally-authored public", 
        "matched_original_science_scenarios":6,
        "matched_original_real_reward_arm_scalars":matching,
        "original_source_REAL_steps":66096,
        "status":"O15_CROSS_OS_PUBLIC_SOURCE_AND_REWARD_RECONCILED",
        "scientific_first_use":False,
        "scientific_candidate_promoted":False}

if __name__=="__main__":
    if len(sys.argv)!=4:
        raise SystemExit("usage compare.py ubuntu.json windows.json receipt.json")
    with open(sys.argv[1],encoding="utf-8") as f:u=json.load(f)
    with open(sys.argv[2],encoding="utf-8") as f:w=json.load(f)
    out=compare(u,w)
    Path(sys.argv[3]).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
