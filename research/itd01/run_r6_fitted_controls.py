"""ITD-01 R6: actual three conventional R5-FITTED public causal learners.

This is a PUBLIC DEVELOPMENT experiment, not original/protected science.
All training and scoring inputs come solely from copied PUBLIC transcripts.
No hidden world state or original science first-use is accessed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import time

from public_dev import PUBLIC_FAMILIES, canonical
from r4_public_experience import PublicTranscript, action_label
from r4_sequential_controls import (RecurrentPolicy, PredictiveTransitionPlanner,
                                    ExplicitTrajectoryMemory, model_sha, model_bytes)
from r5_causal_dev import R5CausalWorld, public_causal_oracle
from r5_history_boundary import r5_rollout_public_only
from run_public_baselines import peak_rss_bytes

SCHEMA = "itd01.r6.fitted-public-causal-dev.v1"
SOURCE_PARENT = "ec2e2d88d06c7c8141949b9858c42c2d77849ff9"
ROLE_ID = {"FIT": 0, "VALID": 1, "DEV": 2, "ABLATE": 3}
ALLOWED_SEEDS = (17, 31, 47)


def role_seed(role, model_seed, fi, index):
    if role not in ROLE_ID or type(model_seed) is not int or model_seed < 0:
        raise ValueError("ITD01_R6_ROLE_OR_SEED_INVALID")
    if fi not in (0, 1) or type(index) is not int or not 0 <= index < 10000:
        raise ValueError("ITD01_R6_ROLE_OR_EPISODE_INVALID")
    return 6100000 + ROLE_ID[role] * 1000000 + model_seed * 10000 + fi * 100000 + index


def episode_key(role, model_seed, fi, index):
    return f"R6-PUBLIC:{role}:{model_seed}:{fi}:{index}"


def public_teacher_trajectory(family, seed, episode_id):
    """Teacher gets only copied reset and copied public action callback."""
    world = R5CausalWorld(family, episode_id, seed)
    first = json.loads(canonical(world.reset()))
    def step(public_action):
        return json.loads(canonical(world.step(public_action)))
    result = public_causal_oracle(first, step)
    if result["reward"] != 1:
        raise ValueError("ITD01_R6_PUBLIC_ORACLE_FAILED")
    history = PublicTranscript(first)
    previous = first
    rows = []
    for record in world.public_trace_records():
        chosen = json.loads(canonical(record["action"]))
        rows.append({"x": history.features(previous),
                     "key": history.memory_key(),
                     "y": action_label(previous, chosen)})
        next_obs = json.loads(canonical(record["result"]["observation"]))
        history.ingest(chosen, next_obs)
        previous = next_obs
    if not rows or rows[-1]["y"] != 9 or not world.public_trace_receipt()["done"]:
        raise ValueError("ITD01_R6_INCOMPLETE_PUBLIC_TEACHER_TRACE")
    return rows, world.public_trace_receipt()["trace_head_sha256"]


def training_rows(seed, episodes_per_family):
    sha = hashlib.sha256(b"ITD01_R6_PUBLIC_FIT_V1").digest()
    groups = []
    for fi, family in enumerate(PUBLIC_FAMILIES):
        for i in range(episodes_per_family):
            rows, trace = public_teacher_trajectory(
                family, role_seed("FIT", seed, fi, i),
                episode_key("FIT", seed, fi, i))
            groups.append(rows)
            sha = hashlib.sha256(sha + bytes.fromhex(trace)).digest()
    return groups, sha.hex()


def score(agent, seed, role, episodes_per_family, mode="normal"):
    if role not in ("VALID", "DEV", "ABLATE"):
        raise ValueError("ITD01_R6_ROLE_NOT_EVALUABLE")
    if mode != "normal" and role != "ABLATE":
        raise ValueError("ITD01_R6_ABLATION_ON_PRIMARY_ROLE")
    out = {}
    for fi, family in enumerate(PUBLIC_FAMILIES):
        trials = [r5_rollout_public_only(
            agent, family, role_seed(role, seed, fi, i),
            episode_key(role, seed, fi, i), mode=mode)
            for i in range(episodes_per_family)]
        out[family] = {
            "n": episodes_per_family,
            "success": sum(t["reward"] for t in trials) / len(trials),
            "legal_fraction": sum(int(t["legal"]) for t in trials) / len(trials),
            "mean_actions": sum(t["steps"] for t in trials) / len(trials),
            "public_trace_heads_sha256": hashlib.sha256(
                canonical([t["trace_sha256"] for t in trials])).hexdigest()
        }
    return out


def experiment(seed, train_n=240, val_n=80, dev_n=80, ablate_n=40,
               developer_smoke=False):
    if seed not in ALLOWED_SEEDS and not developer_smoke:
        raise ValueError("ITD01_R6_UNPREREGISTERED_SEED")
    if not developer_smoke and (train_n,val_n,dev_n,ablate_n)!=(240,80,80,40):
        raise ValueError("ITD01_R6_FROZEN_BUDGET_DRIFT")
    if any(type(n) is not int or not 0 < n <= 240 for n in
           (train_n,val_n,dev_n,ablate_n)):
        raise ValueError("ITD01_R6_INVALID_EPISODE_COUNT")
    start = time.process_time()
    train, source_sha = training_rows(seed, train_n)
    gen_cpu = time.process_time() - start
    agents = (RecurrentPolicy(seed), PredictiveTransitionPlanner(),
              ExplicitTrajectoryMemory())
    trained = []
    # Fitting and validation are completed for every arm before ANY DEV role
    # is born. This prevents checkpoint selection by DEV.
    for agent in agents:
        start_fit = time.process_time()
        agent.train(train)
        fit_cpu = time.process_time() - start_fit
        if agent.updates <= 0:
            raise ValueError("ITD01_R6_UNTRAINED_" + agent.name)
        checkpoint = model_sha(agent)
        bytes_fitted = model_bytes(agent)
        if bytes_fitted > 32*1024*1024:
            raise ValueError("ITD01_R6_MODEL_MEMORY_LIMIT")
        start_val = time.process_time()
        val = score(agent, seed, "VALID", val_n)
        val_cpu = time.process_time() - start_val
        if model_sha(agent) != checkpoint:
            raise ValueError("ITD01_R6_VALID_CHANGED_WEIGHTS")
        trained.append((agent, {
            "class": agent.name, "training_updates": agent.updates,
            "checkpoint_sha256": checkpoint, "checkpoint_bytes": bytes_fitted,
            "fit_cpu_seconds": round(fit_cpu, 6),
            "validation_cpu_seconds": round(val_cpu, 6),
            "validation": val, "fit_source_public_only": True
        }))
    for agent, row in trained:
        frozen = row["checkpoint_sha256"]
        start_dev = time.process_time()
        row["development"] = score(agent, seed, "DEV", dev_n)
        row["development_cpu_seconds"] = round(time.process_time()-start_dev,6)
        start_ablate = time.process_time()
        # Use the same independently allocated ABLATE episode IDs for each mode.
        # Never call this a same-episode causal effect against the DEV split.
        row["diagnostic_normal"] = score(agent, seed, "ABLATE", ablate_n)
        row["diagnostic_erased"] = score(agent, seed, "ABLATE", ablate_n, "erase")
        row["diagnostic_blinded"] = score(agent, seed, "ABLATE", ablate_n,
                                           "blind_delayed")
        row["diagnostic_cpu_seconds"] = round(time.process_time()-start_ablate,6)
        if model_sha(agent) != frozen:
            raise ValueError("ITD01_R6_EVAL_CHANGED_WEIGHTS")
    models=[row for _,row in trained]
    eligible=sum(all(
        .40 <= model["validation"][f]["success"] <= .85 and
        model["validation"][f]["legal_fraction"] == 1.0
        for f in PUBLIC_FAMILIES) for model in models)
    elapsed=time.process_time()-start
    if not math.isfinite(elapsed) or elapsed > 5400:
        raise ValueError("ITD01_R6_CPU_BUDGET_EXCEEDED")
    rss=peak_rss_bytes()
    if rss <= 0 or rss > 2*1024*1024*1024:
        raise ValueError("ITD01_R6_PROCESS_RSS_LIMIT")
    return {
        "schema": SCHEMA, "r5_parent_source_sha": SOURCE_PARENT,
        "source_role": "NEW_SOURCE_FREE_PUBLIC_DEV_ONLY",
        "frozen_seed": seed, "fits_per_family": train_n,
        "validation_per_family":val_n, "development_per_family":dev_n,
        "diagnostic_per_family":ablate_n,
        "public_teacher_trace_sha256":source_sha,
        "generation_cpu_seconds":round(gen_cpu,6),
        "all_in_process_cpu_seconds":round(elapsed,6),
        "shared_process_peak_rss_bytes":rss,
        "normalized_model_isolated_resource_parity":False,
        "models":models,"fully_r5_fitted_eligible_models":eligible,
        "development_disposition":(
            "BENCHMARK_CALIBRATED_PUBLIC_DEV_ONLY" if eligible>=2 else
            "BENCHMARK_NOT_QUALIFIED_RETAIN_NEGATIVE"),
        "scientific_first_use":False, "protected_h1_h2_used":False,
        "native_wingless_yggdrasil_executed":False,
        "scientific_admission":"NOT_GRANTED_BY_THIS_DEV_MODULE"
    }


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--seed", type=int, default=17)
    cli.add_argument("--smoke", action="store_true")
    opts=cli.parse_args()
    if opts.smoke:
        result=experiment(7,3,2,2,1,developer_smoke=True)
    else:
        result=experiment(opts.seed)
    print(json.dumps(result,sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    main()
