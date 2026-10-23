"""Independent cross-OS genuine public original source and reward reconciliation."""
import json,sys
from pathlib import Path
from runner import ARMS,BUDGET

def compare(a,b):
    for x in (a,b):
        if (x.get("schema")!="forge.optimizer.o16.original-public-write-evict-v1" or
            x.get("disposition") not in (
              "O16_PUBLIC_LEARNED_EVICTION_NO_GO",
              "O16_PUBLIC_LEARNED_EVICTION_ADVANCEMENT_CANDIDATE_NOT_FIRST_USE") or
            x.get("actual_original_source_resets")!=1440 or
            x.get("actual_original_source_steps")!=73440 or
            x.get("memory_budget_records")!=BUDGET or
            x.get("FSA_Q21_HELD_first_use_consumed")!=0 or
            x.get("scientific_candidate_promoted") is not False or
            len(x.get("scenarios",[]))!=6):
            raise ValueError("O16_SOURCE_OR_SCIENCE_CUSTODY_INVALID")
    if (a["upstream_original_blobs"]!=b["upstream_original_blobs"] or
        a["disposition"]!=b["disposition"]):
        raise ValueError("O16_EXTERNAL_SOURCE_OR_OUTCOME_DRIFT")
    matched=0
    for x,y in zip(a["scenarios"],b["scenarios"]):
        if ((x["k_auditor_only"],x["replica"])!=
            (y["k_auditor_only"],y["replica"]) or
            x["lag_from_shared_real_FIT"]!=y["lag_from_shared_real_FIT"] or
            x["public_shared_lag_FIT_SHA256"]!=y["public_shared_lag_FIT_SHA256"] or
            x["trained_stride_selected"]!=y["trained_stride_selected"]):
            raise ValueError("O16_FIT_OR_ROLE_DRIFT")
        for arm in ARMS:
            if abs(x["DEV_reward_per_original_scored_action"][arm]-
                   y["DEV_reward_per_original_scored_action"][arm])>1e-8:
                raise ValueError("O16_ORIGINAL_REWARD_DRIFT")
            xs=x["DEV_original_source_episode_evidence"][arm]
            ys=y["DEV_original_source_episode_evidence"][arm]
            if (len(xs)!=24 or len(ys)!=24 or
                [(z["public_original_observation_SHA256"],
                  z["actual_source_actions_reward_SHA256"]) for z in xs]!=
                [(z["public_original_observation_SHA256"],
                  z["actual_source_actions_reward_SHA256"]) for z in ys]):
                raise ValueError("O16_ORIGINAL_SOURCE_TRAJECTORY_DRIFT")
            matched+=1
    return {"status":"O16_PUBLIC_CROSS_OS_RECONCILED",
        "matched_original_reward_scalars":matched,
        "original_source_steps":73440,
        "blinded_scientific_first_use":False,"promotion":False}

if __name__=="__main__":
    if len(sys.argv)!=4:
        raise SystemExit("usage compare.py ubuntu.json windows.json output.json")
    a=json.loads(Path(sys.argv[1]).read_text())
    b=json.loads(Path(sys.argv[2]).read_text())
    out=compare(a,b)
    Path(sys.argv[3]).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
