"""R5 prospective PUBLIC DEV three-stage causal challenge and cold R4 controls.

No hidden H1/H2, no original scientific first use. This does NOT retrain
the three R4 controls on the new R5 causal laws. Shared-process resource
figures cannot establish matched isolated model efficiency.
"""
import argparse
import hashlib
import json
import time
from public_dev import PUBLIC_FAMILIES,canonical
from r5_causal_dev import public_calibration
from r5_history_boundary import r5_rollout_public_only
from r4_public_experience import public_training
from r4_sequential_controls import (RecurrentPolicy,PredictiveTransitionPlanner,
                                    ExplicitTrajectoryMemory,model_sha,model_bytes)
from run_public_baselines import peak_rss_bytes


def evaluate_frozen(actor, seed, count, mode, offset):
    outcome={}
    for fi,family in enumerate(PUBLIC_FAMILIES):
        results=[]
        for i in range(count):
            task_seed=offset+fi*100000+seed*10000+i
            results.append(r5_rollout_public_only(
                actor,family,task_seed,
                f"DEV-R5-COLD-{mode}-{seed}-{fi}-{i}",mode))
        outcome[family]={
            "n":count,
            "success":sum(x["reward"] for x in results)/count,
            "legal_fraction":sum(x["legal"] for x in results)/count,
            "mean_actions":sum(x["steps"] for x in results)/count,
            "public_rewards_sha256":hashlib.sha256(canonical([x["reward"] for x in results])).hexdigest(),
            "public_trace_heads_sha256":hashlib.sha256(canonical([x["trace_sha256"] for x in results])).hexdigest()}
    return outcome


def run(seed=17, fit_count=240, n_cal=120, n_cold=48, n_ablation=12):
    t0=time.process_time()
    public_oracle=public_calibration(n_cal)
    fit_training,fit_public_sha=public_training(seed,fit_count)
    setup_cpu=time.process_time()-t0
    models=[]
    for actor in (RecurrentPolicy(seed),PredictiveTransitionPlanner(),
                  ExplicitTrajectoryMemory()):
        before=time.process_time()
        actor.train(fit_training)
        cpu=time.process_time()-before
        if actor.updates<=0:
            raise AssertionError("R5_INVALID_UNTRAINED_COLD_CONTROL")
        sha=model_sha(actor)
        infer_start=time.process_time()
        normal=evaluate_frozen(actor,seed,n_cold,"normal",570000)
        infer_cpu=time.process_time()-infer_start
        ablations={}
        for mode in ("erase","blind_delayed"):
            a_start=time.process_time()
            ablations[mode]={
                "results":evaluate_frozen(actor,seed,n_ablation,mode,570000),
                "cpu_seconds":round(time.process_time()-a_start,6),
                "prior_r4_ablations_not_recomputed":True,
                "prospective_r5_public_dev_only":True}
        if model_sha(actor)!=sha:
            raise AssertionError("R5_COLD_EVALUATION_MUTATED_WEIGHTS")
        models.append({
            "class":actor.name,"r4_source_training_updates":actor.updates,
            "cold_trained_checkpoint_sha256":sha,
            "serialized_model_bytes":model_bytes(actor),
            "r4_fit_cpu_seconds":round(cpu,6),
            "r5_inference_cpu_seconds_including_public_world":round(infer_cpu,6),
            "r5_normal":normal,"r5_ablations":ablations,
            "r5_fit_updates":0})
    if any(public_oracle[x]["oracle"]["success"]<.8 for x in PUBLIC_FAMILIES):
        disposition="DEV_IDENTIFIABILITY_NO_GO"
    else:
        disposition="PUBLIC_WORLD_SOLVABLE_R5_BASELINE_ELIGIBILITY_NOT_QUALIFIED"
    return {
        "schema":"itd01.r5.public-three-stage-calibration.v1",
        "evidence_class":"PUBLIC_DEVELOPMENT_ONLY",
        "scientific_first_use":False,"protected_H1_H2_used":False,
        "native_wingless_yggdrasil_executed":False,
        "authority":"NONE_DEV_ONLY",
        "seed":seed,"r4_train_episodes_per_family":fit_count,
        "r5_oracle_fixed_tasks_per_family":n_cal,
        "r5_cold_tasks_per_family":n_cold,
        "r5_ablated_tasks_per_family":n_ablation,
        "r4_public_training_trace_sha256":fit_public_sha,
        "public_oracle_fixed":public_oracle,
        "models":models,
        "developer_eligibility":disposition,
        "two_r5_fully_trained_baselines":"NOT_YET_FITTED",
        "shared_environment_and_training_cpu_seconds":round(time.process_time()-t0,6),
        "shared_process_peak_rss_bytes":peak_rss_bytes(),
        "full_resource_equivalence":"NOT_ESTABLISHED",
        "original_first_use":"BLOCKED"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--seed",type=int,default=17)
    a=p.parse_args()
    n=run(a.seed,8 if a.smoke else 240,
          12 if a.smoke else 120,
          4 if a.smoke else 48,
          2 if a.smoke else 12)
    print(json.dumps(n,sort_keys=True,separators=(",",":")))
    if n["developer_eligibility"]=="DEV_IDENTIFIABILITY_NO_GO":
        raise SystemExit("R5_PUBLIC_DEV_CAUSAL_ORACLE_NO_GO")


if __name__=="__main__":
    main()
