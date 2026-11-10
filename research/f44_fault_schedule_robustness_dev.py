#!/usr/bin/env python3
"""F44 original MountainCar physics, heldout externally faulted actuator schedules.

Frozen evaluator only. Imports the unchanged F43 trained policy and full controls.
No model, threshold, F43 source, owner, first-use or simulator physics edits.
"""
from pathlib import Path
import json
import math
import sys
import time

import f41_original_mountaincar_dev as f41
import f42_original_actuator_reversal_dev as f42
import f43_train_calibrated_contradiction_dev as f43

SOURCE = f41.SOURCE
TRAIN_SHA256 = f43.TRAIN_SHA256
FAULT_WORLDS = {
    1501: ((20, 65), (100, 145)),
    1511: ((25, 75), (110, 150)),
    1523: ((70, 115), (155, 190)),
    1531: ((65, 110), (150, 190)),
    1543: ((25, 145),),
    1553: ((38, 155),),
    1567: ((18, 48), (86, 116), (154, 184)),
    1571: ((22, 58), (92, 126), (158, 188)),
}
RETENTION_WORLDS = (1583, 1597, 1601, 1613)
FORBIDDEN = (59, 83)
KINDS = f43.KINDS
CONVENTIONAL = f43.CONVENTIONAL
ABLATIONS = f43.ABLATIONS


def canonical(value):
    return f41.canonical(value)


def digest(value):
    return f41.digest(value)


def public_seed(seed):
    if (type(seed) is not int or seed in FORBIDDEN
            or seed not in (*FAULT_WORLDS, *RETENTION_WORLDS)):
        raise ValueError("F44_PROTECTED_OR_UNAUTHORIZED_DEV_SEED")


def run_episode(gym, seed, kind, model, tau):
    public_seed(seed)
    if kind not in KINDS:
        raise ValueError("F44_UNREGISTERED_CONTROL")
    windows = FAULT_WORLDS.get(seed, ())
    policy = f43.policy_for(kind, model, tau)
    environment = gym.make("MountainCar-v0", render_mode=None)
    try:
        if environment.action_space.n != 3:
            raise ValueError("F44_INVALID_ORIGINAL_DISCRETE_ACTIONS")
        initial, _ignored = environment.reset(seed=seed)
        state = f41.public_obs(initial)
        initial_state = state[:]
        transitions = []
        faulted_actions = 0
        flip_at = []
        boundary_steps = []
        for t in range(200):
            requested = policy.decide(state, t)
            physical = f42.effective_action(requested, t, windows)
            next_obs, reward, terminated, truncated, _ignored = environment.step(physical)
            nxt = f41.public_obs(next_obs)
            reward = float(reward)
            if not math.isfinite(reward) or type(terminated) is not bool or type(truncated) is not bool:
                raise ValueError("F44_INVALID_ORIGINAL_PUBLIC_STEP")
            old_flips = policy.flips
            policy.observe(state, requested, nxt)  # Never pass hidden fault or physical action.
            if policy.flips != old_flips:
                flip_at.append(t)
            if requested != physical:
                faulted_actions += 1
            if any(t in (start, stop) for start, stop in windows):
                boundary_steps.append(t)
            transitions.append({
                "requested": requested,
                "physical": physical,  # evaluator-only provenance
                "next": nxt,
                "reward": reward,
                "terminated": terminated,
                "truncated": truncated,
            })
            state = nxt
            if terminated or truncated:
                break
        if not transitions:
            raise ValueError("F44_ORIGINAL_EPISODE_EMPTY")
        return {
            "initial": initial_state,
            "trace": transitions,
            "return": sum(t["reward"] for t in transitions),
            "steps": len(transitions),
            "terminated": transitions[-1]["terminated"],
            "truncated": transitions[-1]["truncated"],
            "faulted_actions": faulted_actions,
            "boundary_steps_reached": boundary_steps,
            "flips": policy.flips,
            "flip_steps": flip_at,
            "forced_probes": policy.probes,
            "informative": policy.informative,
            "decision_ns": policy.decision_ns,
        }
    finally:
        environment.close()


def score(gym, fit, source):
    if (fit["training_sha256"] != TRAIN_SHA256
            or fit["training_transitions"] != 18138
            or fit["training_episodes"] != 96
            or fit["training_action_counts"] != [7107, 3011, 8020]
            or not (0.02 <= fit["tau"] <= 0.75)
            or fit["calibration_n"] < 1000):
        raise ValueError("F44_FROZEN_TRAINING_ONLY_CUSTODY_DRIFT")
    snapshot = canonical(fit["dynamics"])
    cold = json.loads(snapshot)
    if canonical(cold) != snapshot:
        raise ValueError("F44_COLD_DYNAMICS_RESTORE_FAILURE")
    tau = fit["tau"]
    report = {
        "schema": "forge.eureka.f44.original-mountaincar-external-fault-robustness-dev.v1",
        "source": source,
        "original_physics_with_external_faults": True,
        "unmodified_original_gymnasium_task": False,
        "train_sha256": fit["training_sha256"],
        "train_episodes": fit["training_episodes"],
        "train_transitions": fit["training_transitions"],
        "train_action_counts": fit["training_action_counts"],
        "tau": tau,
        "calibration_n": fit["calibration_n"],
        "source_fit_sha256": fit["source_fit_sha256"],
        "model_sha256": digest(fit["dynamics"]),
        "fault_seeds": tuple(FAULT_WORLDS),
        "retention_seeds": RETENTION_WORLDS,
        "development_only": True,
        "scientific_accepted": False,
        "first_use_consumed": False,
        "owner_eligible": False,
        "matched_whole_process_compute_proven": False,
        "arms": {},
    }
    for kind in KINDS:
        worlds = []
        for seed in (*FAULT_WORLDS, *RETENTION_WORLDS):
            cold_run = run_episode(gym, seed, kind, cold, tau)
            warm_run = run_episode(gym, seed, kind, fit["dynamics"], tau)
            if (canonical(cold_run["trace"]) != canonical(warm_run["trace"])
                or cold_run["initial"] != warm_run["initial"]
                or cold_run["flip_steps"] != warm_run["flip_steps"]
                or cold_run["forced_probes"] != warm_run["forced_probes"]):
                raise ValueError("F44_COLD_WARM_PHYSICAL_TRACE_MISMATCH")
            transitions = cold_run["trace"]
            worlds.append({
                "seed": seed,
                "return": cold_run["return"],
                "steps": cold_run["steps"],
                "terminated": cold_run["terminated"],
                "truncated": cold_run["truncated"],
                "faulted_actions": cold_run["faulted_actions"],
                "boundary_steps_reached": cold_run["boundary_steps_reached"],
                "flips": cold_run["flips"],
                "flip_steps": cold_run["flip_steps"],
                "forced_probes": cold_run["forced_probes"],
                "informative": cold_run["informative"],
                "decision_ns": cold_run["decision_ns"],
                "requested_actions_sha256": digest([x["requested"] for x in transitions]),
                "evaluator_physical_actions_sha256": digest([x["physical"] for x in transitions]),
                "observations_sha256": digest([cold_run["initial"], [x["next"] for x in transitions]]),
                "reward_sha256": digest([x["reward"] for x in transitions]),
                "trace_sha256": digest([cold_run["initial"], transitions]),
                "cold_matches": True,
            })
        faults = worlds[:len(FAULT_WORLDS)]
        clean = worlds[len(FAULT_WORLDS):]
        fault_seconds = sum(w["decision_ns"] for w in faults)
        fault_steps = sum(w["steps"] for w in faults)
        if fault_seconds <= 0 or fault_steps <= 0:
            raise ValueError("F44_MISSING_REAL_DECISION_COST")
        report["arms"][kind] = {
            "worlds": worlds,
            "fault_mean_return": sum(w["return"] for w in faults) / len(faults),
            "retention_mean_return": sum(w["return"] for w in clean) / len(clean),
            "fault_decision_ns_per_step": fault_seconds / fault_steps,
            "fault_step_count": fault_steps,
            "fault_total_decision_ns": fault_seconds,
        }
    strongest = max(CONVENTIONAL, key=lambda k: report["arms"][k]["fault_mean_return"])
    candidate = report["arms"]["calibrated-contradiction"]
    control = report["arms"][strongest]
    best_clean = max(report["arms"][k]["retention_mean_return"] for k in CONVENTIONAL)
    report["strongest_conventional"] = strongest
    report["candidate_mean_gain"] = candidate["fault_mean_return"] - control["fault_mean_return"]
    report["candidate_seed_wins_ge10"] = sum(
        w["return"] >= b["return"] + 10
        for w, b in zip(candidate["worlds"][:8], control["worlds"][:8])
    )
    report["candidate_fault_worlds_with_switch"] = sum(w["flips"] >= 1 for w in candidate["worlds"][:8])
    report["best_control_clean_mean"] = best_clean
    report["retention_margin"] = candidate["retention_mean_return"] - best_clean
    report["decision_cost_ratio_to_strongest"] = (
        candidate["fault_decision_ns_per_step"] / control["fault_decision_ns_per_step"]
    )
    report["frozen_conditions_met"] = bool(
        report["candidate_mean_gain"] >= 15
        and report["candidate_seed_wins_ge10"] >= 6
        and report["candidate_fault_worlds_with_switch"] >= 6
        and report["retention_margin"] >= -5
        and all(candidate["fault_mean_return"] >= report["arms"][k]["fault_mean_return"] + 15
                for k in ABLATIONS)
        and all(w["forced_probes"] == 0 for w in candidate["worlds"])
        and all(w["cold_matches"] and w["forced_probes"] <= 16
                for arm in report["arms"].values() for w in arm["worlds"])
        and all(len(arm["worlds"]) == 12 for arm in report["arms"].values())
        and report["decision_cost_ratio_to_strongest"] <= 1.25
    )
    if digest(fit["dynamics"]) != report["model_sha256"]:
        raise ValueError("F44_MUTABLE_SOURCE_MODEL_REFUSED")
    # Interface fixtures cannot issue a source-verified original scientific label.
    report["classification"] = "F44_ORIGINAL_RUNTIME_UNVERIFIED"
    report["report_sha256"] = digest(report)
    return report


def original_gym(root):
    return f41.original_gym(root)


def main(args=None):
    args = sys.argv[1:] if args is None else args
    if len(args) != 2:
        raise ValueError("F44_USAGE source.py /pinned/Gymnasium /output/report.json")
    root = Path(args[0]).resolve(strict=True)
    out = Path(args[1]).resolve()
    if out.is_relative_to(root):
        raise ValueError("F44_OUTPUT_INSIDE_ORIGINAL_SOURCE_REFUSED")
    try:
        gym, git = original_gym(root)
    except (ImportError, FileNotFoundError) as e:
        raise RuntimeError("F44_ORIGINAL_RUNTIME_BLOCKED") from e
    started = time.perf_counter()
    fit = f43.source_fit(gym)
    trained = time.perf_counter()
    result = score(gym, fit, SOURCE)
    evaluated = time.perf_counter()
    original_gym(root)
    if git(root, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"):
        raise ValueError("F44_ORIGINAL_GIT_SOURCE_MUTATED")
    if result["classification"] != "F44_ORIGINAL_RUNTIME_UNVERIFIED":
        raise ValueError("F44_UNATTESTED_SCORE_DISALLOWED")
    result["training_and_fit_seconds"] = trained - started
    result["physical_evaluation_seconds"] = evaluated - trained
    result["classification"] = (
        "F44_DEV_SIGNAL_UNVERIFIED" if result["frozen_conditions_met"] else "F44_DEV_NO_GO"
    )
    result["report_sha256"] = digest({k: v for k, v in result.items() if k != "report_sha256"})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical(result) + b"\n")
    print("F44_ORIGINAL_FAULT_SCHEDULE_DEV=" + result["classification"]
          + " sha256=" + result["report_sha256"])
    print("F44_COMMON_FIT_SHA256=" + result["train_sha256"]
          + " training_n=" + str(result["train_transitions"])
          + " tau=" + str(result["tau"]))
    print("F44_STRONGEST=" + strongest_display(result)
          + " candidate_gain=" + str(result["candidate_mean_gain"])
          + " paired_ge10=" + str(result["candidate_seed_wins_ge10"])
          + " cost_ratio=" + str(result["decision_cost_ratio_to_strongest"]))
    return result


def strongest_display(result):
    return result["strongest_conventional"]


if __name__ == "__main__":
    main()
