"""ITD-01 R3: measured *public DEV-only* trained-vs-reset ablations.

Measures whether an already qualified conventional learner's acquired weights
or public-feedback memory contribute to performance on identical public tasks.
This is not an independent scientific first use, a held-out transfer test,
or a FORGE Scientific Authority admission. No protected H1/H2 sources exist
in this runner; no CKB-plane/Mind-Palace imports or shared research controller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time

from public_dev import PUBLIC_FAMILIES, PublicDevWorld, canonical
from public_baselines import (
    ExplicitEpisodicAgent, PredictiveWorldModelAgent, RecurrentRewardAgent,
    execute_public_candidate, model_identity, model_state_bytes,
    obtain_public_probes,
)
from run_public_baselines import gather, peak_rss_bytes

SCHEMA = "itd01.r3.public-learned-state-ablation.v1"
NAME_ORDER = (
    "recurrent_bptt", "predictive_public_forward_model",
    "explicit_reward_memory",
)


def agents(seed: int, ntrain: int):
    return (
        ("recurrent_bptt", RecurrentRewardAgent(seed)),
        ("predictive_public_forward_model", PredictiveWorldModelAgent()),
        ("explicit_reward_memory", ExplicitEpisodicAgent(max_cases=2 * ntrain)),
    )


def public_evaluate(agent, neval: int):
    """Paired tasks are fixed by public family and task identity, not outcomes."""
    if not (0 < neval <= 60):
        raise ValueError("ITD01_R3_DEV_EVALUATION_BUDGET")
    family_results = {}
    for family_index, family in enumerate(PUBLIC_FAMILIES):
        outcomes = []
        decisions = []
        traces = []
        for i in range(neval):
            world = PublicDevWorld(
                family, f"DEV-R2-EVAL-{family_index}-{i}",
                830000 + family_index * 100000 + i,
            )
            obs = world.reset()
            probes, names = obtain_public_probes(obs, world.step)
            pair = agent.choose(probes)
            reward = execute_public_candidate(obs, world.step, names, pair)
            receipt = world.public_trace_receipt()
            if (receipt["steps"] != 22 or not receipt["done"]
                    or receipt["scientific_first_use"]
                    or receipt["source_birth_attested"]):
                raise RuntimeError("ITD01_R3_PUBLIC_DEV_CUSTODY_VIOLATION")
            decisions.append(pair)
            outcomes.append(reward)
            traces.append(receipt["trace_head_sha256"])
        family_results[family] = {
            "tasks": neval,
            "reward_sum": sum(outcomes),
            "rewards": outcomes,
            "chosen_pairs": decisions,
            "public_trace_receipts_sha256":
                hashlib.sha256(canonical(traces)).hexdigest(),
        }
    return family_results


def run(seed: int, ntrain: int, neval: int):
    if seed not in (17, 31, 47) or not (0 < ntrain <= 350):
        raise ValueError("ITD01_R3_PUBLIC_DEV_TRAINING_BUDGET")
    started = time.process_time()
    training, public_experience_head = gather(seed, ntrain)
    if len(training) != len(PUBLIC_FAMILIES) * ntrain:
        raise RuntimeError("ITD01_R3_TRAINING_COHORT_MISSING")
    rows = []
    for (name, trained), (_, reset) in zip(agents(seed, ntrain), agents(seed, ntrain)):
        if name not in NAME_ORDER:
            raise RuntimeError("ITD01_R3_UNKNOWN_BASELINE")
        state_before = model_identity(trained)
        if model_identity(reset) != state_before or reset.updates != 0:
            raise RuntimeError("ITD01_R3_RESET_IDENTITY_DRIFT")
        t0 = time.process_time()
        trained.train(training)
        train_cpu = time.process_time() - t0
        if trained.updates <= 0 or model_identity(trained) == state_before:
            raise RuntimeError("ITD01_R3_NO_LEARNED_STATE")
        state_after = model_identity(trained)
        t1 = time.process_time()
        learned = public_evaluate(trained, neval)
        learned_cpu = time.process_time() - t1
        t2 = time.process_time()
        ablated = public_evaluate(reset, neval)
        reset_cpu = time.process_time() - t2
        if model_identity(trained) != state_after or model_identity(reset) != state_before:
            raise RuntimeError("ITD01_R3_EVALUATION_MUTATED_STATE")

        by_family = {}
        for family in PUBLIC_FAMILIES:
            good, null = learned[family], ablated[family]
            if good["tasks"] != null["tasks"] or good["tasks"] != neval:
                raise RuntimeError("ITD01_R3_UNMATCHED_PUBLIC_TASKS")
            wins = sum(a > b for a, b in zip(good["rewards"], null["rewards"]))
            losses = sum(a < b for a, b in zip(good["rewards"], null["rewards"]))
            same = sum(a == b for a, b in zip(good["rewards"], null["rewards"]))
            if wins + losses + same != neval:
                raise RuntimeError("ITD01_R3_PUBLIC_TASK_PAIR_MISMATCH")
            by_family[family] = {
                "public_tasks": neval,
                "trained_rewards": good["reward_sum"],
                "reset_rewards": null["reward_sum"],
                "paired_trained_wins": wins,
                "paired_reset_wins": losses,
                "paired_ties": same,
                "paired_reward_delta": good["reward_sum"] - null["reward_sum"],
                "trained_reward_vector_sha256":
                    hashlib.sha256(canonical(good["rewards"])).hexdigest(),
                "reset_reward_vector_sha256":
                    hashlib.sha256(canonical(null["rewards"])).hexdigest(),
                "trained_action_vector_sha256":
                    hashlib.sha256(canonical(good["chosen_pairs"])).hexdigest(),
                "reset_action_vector_sha256":
                    hashlib.sha256(canonical(null["chosen_pairs"])).hexdigest(),
                "trained_public_trace_sha256": good["public_trace_receipts_sha256"],
                "reset_public_trace_sha256": null["public_trace_receipts_sha256"],
            }
        rows.append({
            "agent": name,
            "training_updates": trained.updates,
            "original_untrained_state_sha256": state_before,
            "fitted_state_sha256": state_after,
            "retained_learned_state_bytes": model_state_bytes(trained),
            "reset_state_bytes": model_state_bytes(reset),
            "training_cpu_seconds": round(train_cpu, 6),
            "trained_eval_cpu_includes_public_environment_seconds":
                round(learned_cpu, 6),
            "reset_eval_cpu_includes_public_environment_seconds":
                round(reset_cpu, 6),
            "public_family_outcomes": by_family,
        })
    if [v["agent"] for v in rows] != list(NAME_ORDER):
        raise RuntimeError("ITD01_R3_MISSING_CONVENTIONAL_CONTROLS")
    return {
        "schema": SCHEMA,
        "authority": "NONE_PUBLIC_DEV_ONLY",
        "scientific_first_use": False,
        "source_birth_attested": False,
        "independent_transfer_qualified": False,
        "protected_h1_h2_accessed": False,
        "ckb_plane_accessed": False,
        "accepted_ref_mutations": 0,
        "development_evidence_only": True,
        "training_tasks_per_family": ntrain,
        "eval_tasks_per_family": neval,
        "seed": seed,
        "shared_training_public_experience_chain_sha256": public_experience_head,
        "agents": rows,
        "whole_process_cpu_seconds": round(time.process_time() - started, 6),
        "peak_rss_bytes_shared_process_not_isolated_per_agent": peak_rss_bytes(),
        "resource_comparability": "INCOMPLETE_SHARED_PUBLIC_PROCESS",
        "interpretation": "PUBLIC_DEVELOPMENT_ABLATION_NOT_SCIENTIFIC_TRANSFER",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    doc = run(args.seed, 8 if args.smoke else 350, 2 if args.smoke else 60)
    print(json.dumps(doc, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
