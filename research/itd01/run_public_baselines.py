"""Public DEV ONLY: fit and independently score three conventional agent types.

This program never constructs independently born H1/H2 held worlds, and
never reads private per-world state. Training signals: public diagnostic
signals and completed PUBLIC action/terminal reward only. Resource reporting
uses process CPU, peak process RSS and serialized learner bytes; shared
environment accounting is disclosed as a combined process, not comparable
isolated model efficiency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time

from public_dev import PUBLIC_FAMILIES, PublicDevWorld, canonical
from public_baselines import (ExplicitEpisodicAgent, PredictiveWorldModelAgent,
                              RecurrentRewardAgent, execute_public_candidate,
                              model_identity, model_state_bytes,
                              obtain_public_probes)

RUN_SCHEMA = "itd01.r2.public-trained-baselines.v1"


def peak_rss_bytes():
    if os.name == "nt":
        try:
            import ctypes
            import ctypes.wintypes as wintypes
            class Mem(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD),
                            ("PageFaultCount", wintypes.DWORD)] + [
                                (name, ctypes.c_size_t) for name in (
                                    "PeakWorkingSetSize", "WorkingSetSize",
                                    "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
                                    "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                                    "PagefileUsage", "PeakPagefileUsage")
                            ]
            counters = Mem()
            counters.cb = ctypes.sizeof(counters)
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel.GetCurrentProcess.restype = ctypes.c_void_p
            psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Mem), wintypes.DWORD]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),
                                              ctypes.byref(counters), counters.cb):
                return None
            return int(counters.PeakWorkingSetSize)
        except (OSError, AttributeError, ValueError):
            return None
    try:
        import resource
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(raw * (1 if sys.platform == "darwin" else 1024))
    except (ImportError, OSError):
        return None


def gather(seed: int, n_per_family: int) -> tuple[list[dict], str]:
    """Shared train episodes, identical observations and rewards for all baselines."""
    rng = random.Random(seed ^ 0x1C4D)
    episodes = []
    custody = hashlib.sha256(b"ITD01_R2_PUBLIC_DEV_EXPERIENCES").digest()
    for family_index, family in enumerate(PUBLIC_FAMILIES):
        for i in range(n_per_family):
            world = PublicDevWorld(family, f"DEV-R2-TRAIN-{family_index}-{i}",
                                   71000 + family_index * 100000 + i)
            obs = world.reset()
            seq, names = obtain_public_probes(obs, world.step)
            chosen = rng.randrange(6)
            reward = execute_public_candidate(obs, world.step, names, chosen)
            receipt = world.public_trace_receipt()
            if not receipt["done"] or receipt["steps"] > 40 or receipt["scientific_first_use"]:
                raise RuntimeError("ITD01_PUBLIC_TRAIN_CUSTODY_INVALID")
            episodes.append({"probes": seq, "pair": chosen, "reward": reward})
            custody = hashlib.sha256(custody + canonical({
                "family_index": family_index, "episode": i, "pair": chosen,
                "reward": reward, "trace_head": receipt["trace_head_sha256"]
            })).digest()
    return episodes, custody.hex()


def evaluate(agent, tasks_per_family: int) -> dict:
    results = {}
    for family_index, family in enumerate(PUBLIC_FAMILIES):
        outcomes = []
        trace_heads = []
        for i in range(tasks_per_family):
            world = PublicDevWorld(family, f"DEV-R2-EVAL-{family_index}-{i}",
                                   830000 + family_index * 100000 + i)
            obs = world.reset()
            seq, names = obtain_public_probes(obs, world.step)
            pair = agent.choose(seq)
            reward = execute_public_candidate(obs, world.step, names, pair)
            receipt = world.public_trace_receipt()
            if receipt["steps"] != 22 or not receipt["done"]:
                raise RuntimeError("ITD01_DEV_PUBLIC_EVAL_BUDGET_INVALID")
            outcomes.append(reward)
            trace_heads.append(receipt["trace_head_sha256"])
        results[family] = {"tasks": len(outcomes), "completed_goals": sum(outcomes),
                           "success_rate": round(sum(outcomes) / len(outcomes), 6),
                           "rewards_sha256": hashlib.sha256(canonical(outcomes)).hexdigest(),
                           "public_trace_heads_sha256": hashlib.sha256(canonical(trace_heads)).hexdigest()}
    return results


def run(ntrain: int, neval: int, seed: int) -> dict:
    start_cpu, start_wall = time.process_time(), time.perf_counter()
    training, birth = gather(seed, ntrain)
    fitted = []
    for name, model in (
        ("recurrent_bptt", RecurrentRewardAgent(seed)),
        ("predictive_public_forward_model", PredictiveWorldModelAgent()),
        ("explicit_reward_memory", ExplicitEpisodicAgent(max_cases=2 * ntrain)),
    ):
        t0 = time.process_time()
        model.train(training)
        fit_cpu = time.process_time() - t0
        if model.updates <= 0:
            raise RuntimeError("ITD01_BASELINE_UNTRAINED_" + name)
        identity_before = model_identity(model)
        t1 = time.process_time()
        evaluations = evaluate(model, neval)
        evaluate_cpu = time.process_time() - t1
        if model_identity(model) != identity_before:
            raise RuntimeError("ITD01_DEV_EVAL_MUTATED_WEIGHTS")
        fitted.append({"name": name, "training_updates": model.updates,
                       "trained_state_sha256": identity_before,
                       "trained_serialized_bytes": model_state_bytes(model),
                       "fit_cpu_seconds": round(fit_cpu, 6),
                       "evaluation_cpu_seconds_including_environment": round(evaluate_cpu, 6),
                       "evaluation": evaluations})
    return {"schema": RUN_SCHEMA, "scientific_first_use": False,
            "status": "ENGINEERING_DEV_BASELINES_NOT_TRANSFER_SCIENCE",
            "original_held_families_used": False, "source_birth_attested": False,
            "train_tasks_per_family": ntrain, "validation_tasks_per_family": neval,
            "seed": seed, "public_experience_chain_sha256": birth,
            "trained_agent_classes": fitted,
            "shared_process_total_cpu_seconds": round(time.process_time() - start_cpu, 6),
            "shared_process_wall_seconds": round(time.perf_counter() - start_wall, 6),
            "peak_process_rss_bytes_includes_shared_environment": peak_rss_bytes(),
            "resource_limit_qualification": "NOT_ESTABLISHED_SHARED_PROCESS_ACCOUNTING",
            "authority": "NONE_DEV_ONLY"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    report = run(18 if args.smoke else 350, 6 if args.smoke else 60, args.seed)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    if any(agent["training_updates"] == 0 for agent in report["trained_agent_classes"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
