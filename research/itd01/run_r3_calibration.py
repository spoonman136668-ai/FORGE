"""ITD-01 R3 full DEV-only calibration, actual public-only terminal executions.

Cold-transfer R2 policies are FROZEN old-task comparators, NOT fully R3-trained
controls and never count toward the R3 benchmark eligibility decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time

from public_dev import PUBLIC_FAMILIES, canonical
from public_dev_r3 import PublicCausalDevWorld, development_calibration
from public_baselines import (ExplicitEpisodicAgent, PredictiveWorldModelAgent,
                              RecurrentRewardAgent, execute_public_candidate,
                              model_identity, obtain_public_probes)
from run_public_baselines import gather, peak_rss_bytes


def cold_reuse(seed: int, episodes_per_family: int, fit_per_family: int) -> list[dict]:
    original_r2_train, original_r2_public_hash = gather(seed, fit_per_family)
    actors = (("frozen_R2_recurrent", RecurrentRewardAgent(seed)),
              ("frozen_R2_predictive", PredictiveWorldModelAgent()),
              ("frozen_R2_explicit_memory", ExplicitEpisodicAgent(2 * fit_per_family)))
    reports = []
    for actor_name, actor in actors:
        actor.train(original_r2_train)
        original_sha = model_identity(actor)
        family_scores = {}
        for fi, family in enumerate(PUBLIC_FAMILIES):
            outcomes, chains = [], []
            for i in range(episodes_per_family):
                world = PublicCausalDevWorld(family, f"DEV-R3-COLD-{fi}-{i}",
                                             413000 + fi * 100000 + i)
                obs = world.reset()
                probes, labels = obtain_public_probes(obs, world.step)
                selected = actor.choose(probes)
                done = execute_public_candidate(obs, world.step, labels, selected)
                rec = world.public_trace_receipt()
                if rec["steps"] != 22 or not rec["done"]:
                    raise RuntimeError("ITD01_R3_COLD_CONTROL_INCONSISTENT")
                outcomes.append(done)
                chains.append(rec["trace_head_sha256"])
            family_scores[family] = {"n":len(outcomes),
                "success":sum(outcomes)/len(outcomes),
                "public_rewards_sha256":hashlib.sha256(canonical(outcomes)).hexdigest(),
                "public_episode_chains_sha256":hashlib.sha256(canonical(chains)).hexdigest()}
        if model_identity(actor) != original_sha:
            raise RuntimeError("ITD01_R3_COLD_MODEL_MODIFIED")
        reports.append({"actor":actor_name,"frozen_r2_model_sha256":original_sha,
                        "r2_source_public_train_chain_sha256":original_r2_public_hash,
                        "frozen_model_fit_updates":actor.updates,
                        "r3_unseen_public_developer_results":family_scores})
    return reports


def run(n: int = 120, seed: int = 17, cold_n: int = 36,
        cold_fit: int = 350) -> dict:
    t0, w0 = time.process_time(),time.perf_counter()
    controlled = development_calibration(n, seed_start=410000)
    cold = cold_reuse(seed, cold_n, cold_fit)
    return {
        "schema":"itd01.r3.calibration-receipt.v1",
        "scientific_first_use":False,
        "source_birth_attested":False,
        "held_world_families_used":False,
        "source_only_public_dev":True,
        "oracle_is_structured_public_ceiling_not_trained":True,
        "previous_R2_actors_are_cold_reuse_not_R3_trained":True,
        "dev_worlds":controlled["family_results"],
        "cold_r2_baseline_results":cold,
        "dev_oracle_calibration_min_success":.8,
        "dev_control_eligibility_low":.4,
        "dev_control_eligibility_high":.85,
        "developer_eligibility_disposition":"NOT_QUALIFIED_NO_TWO_FULLY_R3_TRAINED_CONTROLS",
        "cpu_seconds_including_shared_world":round(time.process_time()-t0,6),
        "wall_seconds_including_shared_world":round(time.perf_counter()-w0,6),
        "process_peak_rss_bytes_including_environment":peak_rss_bytes(),
        "authority":"NONE_DEV_ONLY",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--seed",type=int,default=17)
    args=p.parse_args()
    r=run(16 if args.smoke else 120,args.seed,
          4 if args.smoke else 36,18 if args.smoke else 350)
    print(json.dumps(r,sort_keys=True,separators=(",", ":")))
    if not all(p["public_oracle"]["success_rate"]>=.8
               for p in r["dev_worlds"].values()):
        raise SystemExit("R3 PUBLIC ORACLE IDENTIFIABILITY FAILED")


if __name__=="__main__":
    main()
