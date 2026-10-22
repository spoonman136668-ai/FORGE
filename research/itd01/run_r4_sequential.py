"""ITD-01 R4: bounded source-free trained sequential control qualification.

All three genuinely fit to identical PUBLIC demonstrator trajectories. No
independently witnessed original first use, no protected H1/H2, no private
target labels, no in-task oracle invocation at inference.
"""
import argparse
import hashlib
import json
import time
from public_dev import PUBLIC_FAMILIES, canonical
from r4_public_experience import public_training, eval_agent
from r4_sequential_controls import (RecurrentPolicy, PredictiveTransitionPlanner,
                                    ExplicitTrajectoryMemory, model_sha, model_bytes)
from run_public_baselines import peak_rss_bytes


def experiment(seed=17, train_per_family=240, val_per_family=80,
               challenge_per_family=80, ablations=True):
    start=time.process_time()
    trajectories, public_training_sha=public_training(seed,train_per_family)
    generation_cpu=time.process_time()-start
    result=[]
    for agent in (RecurrentPolicy(seed), PredictiveTransitionPlanner(),
                  ExplicitTrajectoryMemory()):
        fit_start=time.process_time()
        agent.train(trajectories)
        fit_cpu=time.process_time()-fit_start
        if agent.updates<=0:
            raise AssertionError("ITD01_R4_UNTRAINED_"+agent.name)
        frozen_sha=model_sha(agent)
        eval_start=time.process_time()
        validation=eval_agent(agent,seed,val_per_family,"normal","validation")
        val_cpu=time.process_time()-eval_start
        eval_start=time.process_time()
        challenge=eval_agent(agent,seed,challenge_per_family,"normal","challenge")
        challenge_cpu=time.process_time()-eval_start
        extra={}
        if ablations:
            for ablate in ("erase","blind_delayed"):
                eval_start=time.process_time()
                extra[ablate]={"families":eval_agent(agent,seed,challenge_per_family,
                                                    ablate,"challenge"),
                               "cpu_seconds":round(time.process_time()-eval_start,6)}
        if model_sha(agent)!=frozen_sha:
            raise AssertionError("ITD01_R4_EVAL_TOUCHED_FIT_WEIGHTS")
        result.append({
            "class":agent.name,"training_updates":agent.updates,
            "frozen_model_sha256":frozen_sha,"model_bytes":model_bytes(agent),
            "fit_cpu_seconds":round(fit_cpu,6),
            "validation_cpu_seconds":round(val_cpu,6),
            "challenge_cpu_seconds":round(challenge_cpu,6),
            "validation":validation,"challenge":challenge,"ablations":extra,
            "fit_source_public_only":True
        })
    qualified=sum(all(.40<=a["validation"][fam]["success"]<=.85
                      for fam in PUBLIC_FAMILIES) for a in result)
    return {
        "schema":"itd01.r4.trained-sequential-public-dev.v1",
        "evidence_class":"PUBLIC_DEVELOPMENT_ONLY",
        "scientific_first_use":False,"original_scientific_source_exposure":False,
        "protected_H1_H2_born_or_used":False,"authority":"NONE_DEV_ONLY",
        "train_episodes_per_family":train_per_family,
        "validation_episodes_per_family":val_per_family,
        "challenge_episodes_per_family":challenge_per_family,
        "training_seed":seed,
        "training_public_trace_digest":public_training_sha,
        "public_demo_generation_cpu_seconds":round(generation_cpu,6),
        "models":result,
        "eligible_control_classes_both_worlds":qualified,
        "dev_control_eligibility_disposition":
            ("PUBLIC_DEV_ELIGIBILITY_CONDITION_MET_NOT_SCIENTIFIC"
             if qualified>=2 else
             "BENCHMARK_NOT_QUALIFIED_FEWER_THAN_TWO_FITTED_CONTROLS"),
        "process_cpu_seconds_environment_included":round(time.process_time()-start,6),
        "process_peak_rss_bytes_includes_environment":peak_rss_bytes(),
        "normalized_model_isolated_resource_advantage":"NOT_ESTABLISHED",
        "native_wingless_or_yggdrasil_transfer":"NOT_TESTED",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--seed",type=int,default=17)
    args=p.parse_args()
    out=experiment(args.seed,8 if args.smoke else 240,
                   4 if args.smoke else 80,
                   4 if args.smoke else 80,
                   not args.smoke)
    print(json.dumps(out,sort_keys=True,separators=(",",":")))


if __name__=="__main__":
    main()
