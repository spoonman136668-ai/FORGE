"""Independent genuine-original-source O17 cross-OS role/custody verification."""
import json,math,sys
from pathlib import Path

ARMS=("O17_PHASE_GATE","O16_LEGACY_EVICTION","FIFO","TRAINED_STRIDE",
      "O17_PHASE_ROTATE_ABLATION")
FIT_ARMS=("phase_gate","legacy","stride_split_16_16_16")
DISPOSITIONS=("O17_PUBLIC_PHASE_RETAIN_NO_GO",
              "O17_PUBLIC_PHASE_RETAIN_CANDIDATE_NOT_FIRST_USE")

def need(ok,reason):
    if not ok:raise ValueError(reason)

def compare(a,b):
    for z in (a,b):
        need(z.get("schema")=="forge.optimizer.o17.original-public-phase-retention-v1" and
             z.get("disposition") in DISPOSITIONS and
             z.get("memory_records_max")==4 and
             z.get("original_real_source_resets")==1872 and
             z.get("original_legal_source_steps")==95472 and
             z.get("scientific_candidate_promoted") is False and
             z.get("original_science_first_use") is False and
             len(z.get("scenarios",[]))==6,
             "O17_INVALID_EXTERNAL_SOURCE_CUSTODY")
    need(a["source_original_git_commit"]==b["source_original_git_commit"] and
         a["source_original_git_blobs"]==b["source_original_git_blobs"] and
         a["frozen_FIRST_protocol_commit"]==b["frozen_FIRST_protocol_commit"] and
         a["disposition"]==b["disposition"],
         "O17_SOURCE_IDENTITY_OR_SCIENCE_DISPOSITION_DRIFT")
    fit_count=0;dev_count=0;scalar_count=0
    for x,y in zip(a["scenarios"],b["scenarios"]):
        need((x["source_k_auditor_only"],x["source_replica"])==
             (y["source_k_auditor_only"],y["source_replica"]) and
             x["learned_lag_from_real_public_reward"]==
             y["learned_lag_from_real_public_reward"] and
             x["original_source_LAG_FIT_SHA256"]==
             y["original_source_LAG_FIT_SHA256"] and
             x["trained_stride_selected"]==y["trained_stride_selected"] and
             x["O17_PUBLIC_ADVANCEMENT_PER_SCENARIO"]==
             y["O17_PUBLIC_ADVANCEMENT_PER_SCENARIO"],
             "O17_SOURCE_ROLE_LAG_OR_STRIDE_DRIFT")
        for arm in FIT_ARMS:
            u=x["genuine_original_POLICY_FIT_action_reward_receipts"][arm]
            v=y["genuine_original_POLICY_FIT_action_reward_receipts"][arm]
            need(len(u)==len(v)==48,"O17_MISSING_ORIGINAL_FIT_EPISODES")
            for p,q in zip(u,v):
                need((p["source_seed"],p["public_original_observation_SHA256"],
                     p["actual_source_actions_reward_SHA256"])==
                     (q["source_seed"],q["public_original_observation_SHA256"],
                      q["actual_source_actions_reward_SHA256"]),
                     "O17_FIT_EXTERNAL_SOURCE_TRAJECTORY_DRIFT")
                fit_count+=1
        for arm in ARMS:
            u=x["genuine_original_DEV_action_reward_receipts"][arm]
            v=y["genuine_original_DEV_action_reward_receipts"][arm]
            need(len(u)==len(v)==24,"O17_MISSING_ORIGINAL_DEV_EPISODES")
            for p,q in zip(u,v):
                need((p["source_seed"],p["public_original_observation_SHA256"],
                      p["actual_source_actions_reward_SHA256"])==
                     (q["source_seed"],q["public_original_observation_SHA256"],
                      q["actual_source_actions_reward_SHA256"]) and
                     p["bounded_memory_peak_items"]<=4 and
                     q["bounded_memory_peak_items"]<=4,
                     "O17_DEV_ORIGINAL_SOURCE_TRAJECTORY_OR_MEMORY_DRIFT")
                dev_count+=1
            delta=(x["source_real_reward_per_scored_action"][arm]-
                   y["source_real_reward_per_scored_action"][arm])
            need(math.isfinite(delta) and abs(delta)<=1e-8,
                 "O17_ORIGINAL_REWARD_SCALAR_DRIFT")
            scalar_count+=1
    need(fit_count==6*3*48 and dev_count==6*5*24 and scalar_count==30,
         "O17_CROSS_OS_COUNTS_MISMATCH")
    return {"status":"O17_ORIGINAL_CROSS_OS_RECONCILED",
        "genuine_original_FIT_episodes_compared":fit_count,
        "genuine_original_DEV_episodes_compared":dev_count,
        "matched_original_reward_scalars":scalar_count,
        "original_source_real_steps_per_OS":95472,
        "scientific_first_use":False,
        "promotion":False,
        "preserved_disposition":a["disposition"]}

if __name__=="__main__":
    if len(sys.argv)!=4:
        raise SystemExit("usage compare.py ubuntu.json windows.json output.json")
    a=json.loads(Path(sys.argv[1]).read_text())
    b=json.loads(Path(sys.argv[2]).read_text())
    out=compare(a,b)
    Path(sys.argv[3]).write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print(json.dumps(out,sort_keys=True))
