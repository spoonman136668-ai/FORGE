"""O18 independent original-source FIT and DEV cross-operating-system verifier."""
import json,math,sys
from pathlib import Path
ARMS=("RECORD_CREDIT","O17_PHASE_GATE","O16_LEGACY_EVICTION",
      "TRAINED_STRIDE","FIFO","RECORD_FEATURE_ABLATION")
FIT_ARMS=("RECORD_CREDIT","O17_PHASE_GATE","O16_LEGACY_EVICTION",
          "TRAINED_STRIDE_SPLIT")
DISPOSITIONS=("O18_PUBLIC_RECORD_CREDIT_NO_GO",
              "O18_PUBLIC_RECORD_CREDIT_CANDIDATE_NOT_FIRST_USE")

def need(ok,message):
    if not ok:raise ValueError(message)

def compare(a,b):
    for x in (a,b):
        need(x.get("schema")=="forge.optimizer.o18.original-record-credit-source-v1"
             and x.get("disposition") in DISPOSITIONS
             and x.get("total_original_source_resets")==2304
             and x.get("total_genuine_original_source_legal_steps")==117504
             and x.get("DEV_memory_capacity")==4
             and x.get("science_promotion") is False
             and x.get("independent_scientific_first_use") is False
             and len(x.get("scenarios",[]))==6,
             "O18_CUSTODY_SCHEMA_OR_REAL_SOURCE_COUNT_INVALID")
    for key in ("original_external_source_blobs","original_external_source_commit",
                "O18_FIRST_source_only_commit","immutable_parent_O17_sha",
                "disposition"):
        need(a[key]==b[key],"O18_ORIGINAL_SOURCE_PROVENANCE_DRIFT:"+key)
    fit_episodes=0
    dev_episodes=0
    scalars=0
    lag_scenarios=0
    for x,y in zip(a["scenarios"],b["scenarios"]):
        for key in ("k_original_source_constructor_auditor_only","replica",
                    "shared_FULL_history_LAG_FIT_source_SHA256",
                    "learned_lag_from_real_original_source_reward",
                    "trained_stride_selected","O18_candidate_per_scenario_advance"):
            need(x[key]==y[key],"O18_LAG_OR_GENUINE_SOURCE_ROLE_DRIFT:"+key)
        lag_scenarios+=1
        for arm in FIT_ARMS:
            p=x["original_policy_FIT_all_action_reward_receipts"][arm]
            q=y["original_policy_FIT_all_action_reward_receipts"][arm]
            need(len(p)==len(q)==48,"O18_REAL_ORIGINAL_FIT_EPISODES_MISSING")
            for u,v in zip(p,q):
                for key in ("source_seed","public_original_observation_SHA256",
                            "actual_source_actions_reward_SHA256",
                            "scored","correct","real_source_legal_steps"):
                    need(u[key]==v[key],"O18_ORIGINAL_FIT_TRAJECTORY_DRIFT:"+key)
                need(u["bounded_memory_peak_items"]<=4
                     and v["bounded_memory_peak_items"]<=4,
                     "O18_ORIGINAL_FIT_MEMORY_CAPACITY_BREACH")
                fit_episodes+=1
        for arm in ARMS:
            p=x["original_source_DEV_all_action_reward_receipts"][arm]
            q=y["original_source_DEV_all_action_reward_receipts"][arm]
            need(len(p)==len(q)==24,"O18_ORIGINAL_DEV_EPISODES_MISSING")
            for u,v in zip(p,q):
                for key in ("source_seed","public_original_observation_SHA256",
                            "actual_source_actions_reward_SHA256",
                            "scored","correct","real_source_legal_steps"):
                    need(u[key]==v[key],"O18_ORIGINAL_DEV_TRAJECTORY_DRIFT:"+key)
                need(u["bounded_memory_peak_items"]<=4 and
                     v["bounded_memory_peak_items"]<=4,
                     "O18_ORIGINAL_DEV_CAPACITY_OVERFLOW")
                dev_episodes+=1
            vx=x["original_source_DEV_mean_signed_reward"][arm]
            vy=y["original_source_DEV_mean_signed_reward"][arm]
            need(math.isfinite(vx) and math.isfinite(vy) and
                 abs(vx-vy)<=1e-8,
                 "O18_ORIGINAL_SIGNED_REWARD_CROSS_OS_DRIFT")
            scalars+=1
    need(lag_scenarios==6 and fit_episodes==6*48*len(FIT_ARMS)
         and dev_episodes==6*24*len(ARMS) and scalars==36,
         "O18_INDEPENDENT_CROSS_OS_COUNT_MISMATCH")
    return {
      "status":"O18_ORIGINAL_EXTERNAL_CROSS_OS_RECONCILED",
      "original_source_FIT_arm_episodes_matched":fit_episodes,
      "original_source_DEV_arm_episodes_matched":dev_episodes,
      "original_source_reward_scalars_matched":scalars,
      "original_source_real_steps_per_OS":117504,
      "public_science_disposition":a["disposition"],
      "blinded_independent_first_use":False,
      "promotion":False}

if __name__=="__main__":
    if len(sys.argv)!=4:
        raise SystemExit("usage compare.py ubuntu.json windows.json output.json")
    u=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    w=json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    result=compare(u,w)
    Path(sys.argv[3]).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
