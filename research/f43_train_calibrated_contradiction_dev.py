#!/usr/bin/env python3
"""F43: source-frozen training-only calibrated contradictions on real MountainCar physics.

Original Gymnasium dynamics + external evaluator-only command-channel faults.
Development only, no scientific first use or owner/production integration.
"""
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

import f41_original_mountaincar_dev as f41
import f42_original_actuator_reversal_dev as f42

SOURCE = f41.SOURCE
TRAIN_SHA256 = "174dee337d801c1046bd0d26b0ff0c50f89adf36cce4489c43100b4ea0dd1f34"
TRAIN_ACTION_COUNTS = (7107, 3011, 8020)
TRAIN_TRANSITIONS = 18138
FAULT_WORLDS = {
    1409: ((38, 94), (130, 176)),
    1423: ((46, 106), (134, 180)),
    1439: ((42, 102), (138, 184)),
    1451: ((50, 110), (140, 186)),
}
NO_FAULT_WORLDS = (1471, 1483)
KINDS = (
    "calibrated-contradiction",
    "rolling8-probe",
    "rolling8-no-probe",
    "bayes-probe",
    "bayes-no-probe",
    "fixed-mpc",
    "velocity-rule",
    "wrong-credit-no-probe",
    "no-adapt-no-probe",
)
CONVENTIONAL = KINDS[1:7]
ABLATIONS = KINDS[7:]
FIRST_USE_FORBIDDEN = (59, 83)


def canonical(value):
    return f41.canonical(value)


def digest(value):
    return f41.digest(value)


def threshold_from_training_magnitudes(magnitudes):
    vals = np.asarray(magnitudes, dtype=float)
    if len(vals) < 1000 or not np.all(np.isfinite(vals)) or np.any(vals <= 0):
        raise ValueError("F43_INSUFFICIENT_OR_INVALID_TRAIN_ONLY_CALIBRATION")
    tau = max(0.02, min(0.75, 0.4 * float(np.median(vals))))
    if not (0.02 <= tau <= 0.75):
        raise ValueError("F43_CALIBRATED_THRESHOLD_DRIFT")
    return tau


def source_fit(gym):
    start = time.perf_counter()
    transcript, coverage = f41.training(gym)
    training_sha = digest(transcript)
    if (training_sha != TRAIN_SHA256 or len(transcript) != TRAIN_TRANSITIONS
            or tuple(coverage) != TRAIN_ACTION_COUNTS):
        raise ValueError("F43_PREVIOUS_F41_TRAINING_ONLY_TRANSCRIPT_DRIFT")
    dynamics = json.loads(canonical(f41.fit_dynamics(transcript)))
    if np.asarray(dynamics["global"]).shape != (6, 2):
        raise ValueError("F43_COMMON_SOURCE_MODEL_DRIFT")
    mags = []
    for item in transcript:
        if item["a"] == 1:
            continue
        l = f42.reversal_evidence(item["s"], item["a"], item["next"], dynamics)
        if l != 0:
            mags.append(abs(l))
    tau = threshold_from_training_magnitudes(mags)
    result = {
        "dynamics": dynamics,
        "tau": tau,
        "calibration_n": len(mags),
        "calibration_median_abs_l": float(np.median(np.asarray(mags))),
        "training_sha256": training_sha,
        "training_action_counts": coverage,
        "training_transitions": len(transcript),
        "training_episodes": 96,
        "training_and_fit_seconds": time.perf_counter() - start,
    }
    result["source_fit_sha256"] = digest({k: v for k, v in result.items()
                                           if k not in ("source_fit_sha256", "training_and_fit_seconds")})
    return result


class CalibratedPolicy(f42.Policy):
    """No probing; two of last three sufficiently strong contradictions switches mapping."""
    def __init__(self, kind, common_model, tau):
        if kind not in ("calibrated-contradiction", *ABLATIONS):
            raise ValueError("F43_UNKNOWN_CALIBRATED_POLICY")
        super().__init__("fixed-mpc", common_model)
        self.kind = kind
        self.tau = tau
        self.recent3 = []

    def observe(self, state, commanded, next_state):
        tick = time.perf_counter_ns()
        l = f42.reversal_evidence(state, commanded, next_state, self.model)
        if l != 0:
            self.informative += 1
        if self.kind == "no-adapt-no-probe":
            self.decision_ns += time.perf_counter_ns() - tick
            return
        if self.kind == "wrong-credit-no-probe":
            l = -l
        if l:
            self.recent3 = (self.recent3 + [l])[-3:]
            direction = -1 if self.as_reverse else 1
            if sum(v * direction >= self.tau for v in self.recent3) >= 2:
                self.as_reverse = not self.as_reverse
                self.flips += 1
                self.recent3 = []
        self.decision_ns += time.perf_counter_ns() - tick


class RollingNoProbe(f42.Policy):
    def __init__(self, common_model):
        super().__init__("rolling8-probe", common_model)

    def decide(self, state, step):
        tick = time.perf_counter_ns()
        intended = f41.mpc_action(
            f41.public_obs(state),
            "global-linear-mpc",
            self.planner,
        )
        action = 2 - intended if self.as_reverse else intended
        self.decision_ns += time.perf_counter_ns() - tick
        return int(action)


def policy_for(kind, dynamics, tau):
    if kind in ("calibrated-contradiction", *ABLATIONS):
        return CalibratedPolicy(kind, dynamics, tau)
    if kind == "rolling8-no-probe":
        return RollingNoProbe(dynamics)
    if kind in ("rolling8-probe", "bayes-probe", "bayes-no-probe", "fixed-mpc", "velocity-rule"):
        return f42.Policy(kind, dynamics)
    raise ValueError("F43_UNREGISTERED_POLICY")


def episode(gym, seed, kind, dynamics, tau):
    if seed in FIRST_USE_FORBIDDEN or seed not in (*FAULT_WORLDS, *NO_FAULT_WORLDS):
        raise ValueError("F43_UNAUTHORIZED_DEV_OR_PROTECTED_FIRST_USE_SEED")
    policy = policy_for(kind, dynamics, tau)
    windows = FAULT_WORLDS.get(seed, ())
    env = gym.make("MountainCar-v0", render_mode=None)
    try:
        if env.action_space.n != 3:
            raise ValueError("F43_ORIGINAL_ACTION_SPACE_DRIFT")
        state_raw, _ignored = env.reset(seed=seed)
        state = f41.public_obs(state_raw)
        initial = state[:]
        transitions = []
        faulted = 0
        physical_starts = tuple(s for s, _ in windows)
        physical_returns = tuple(e for _, e in windows)
        boundaries = []
        for step in range(200):
            command = policy.decide(state, step)
            physical = f42.effective_action(command, step, windows)
            next_raw, reward, terminated, truncated, _ignored = env.step(physical)
            nxt = f41.public_obs(next_raw)
            reward = float(reward)
            if (not math.isfinite(reward) or type(terminated) is not bool
                    or type(truncated) is not bool):
                raise ValueError("F43_BAD_ORIGINAL_REWARD_OR_TERMINATION")
            policy.observe(state, command, nxt)
            if physical != command:
                faulted += 1
            if step in (*physical_starts, *physical_returns):
                boundaries.append(step)
            transitions.append({
                "requested": command,
                "effective": physical,  # evaluator-only provenance; NEVER to model
                "next": nxt,
                "reward": reward,
                "terminated": terminated,
                "truncated": truncated,
            })
            state = nxt
            if terminated or truncated:
                break
        if not transitions:
            raise ValueError("F43_NO_ORIGINAL_CONSEQUENCES")
        return {
            "initial": initial,
            "transitions": transitions,
            "return": sum(z["reward"] for z in transitions),
            "steps": len(transitions),
            "probes": policy.probes,
            "flips": policy.flips,
            "informative": policy.informative,
            "decision_ns": policy.decision_ns,
            "faulted_commands": faulted,
            "boundaries_reached": boundaries,
            "terminated": transitions[-1]["terminated"],
            "truncated": transitions[-1]["truncated"],
        }
    finally:
        env.close()


def assess(gym, fit, source):
    original_model_bytes = canonical(fit["dynamics"])
    cold_model = json.loads(original_model_bytes)
    if canonical(cold_model) != original_model_bytes:
        raise ValueError("F43_SOURCE_FIT_COLD_RESTORE_FAILURE")
    tau = fit["tau"]
    report = {
        "schema": "forge.eureka.original-fault-calibrated-dev.f43.v1",
        "source": source,
        "training_sha256": fit["training_sha256"],
        "training_episodes": fit["training_episodes"],
        "train_transitions": fit["training_transitions"],
        "train_action_counts": fit["training_action_counts"],
        "calibration_n": fit["calibration_n"],
        "training_only_tau": tau,
        "training_only_calibration_median": fit["calibration_median_abs_l"],
        "source_fit_sha256": fit["source_fit_sha256"],
        "checkpoint_sha256": digest(fit["dynamics"]),
        "faulted_eval_seeds": tuple(FAULT_WORLDS),
        "no_fault_eval_seeds": NO_FAULT_WORLDS,
        "development_only": True,
        "original_physics_with_external_actuator_fault": True,
        "unmodified_original_gymnasium_task": False,
        "first_use_consumed": False,
        "scientific_accepted": False,
        "owner_eligible": False,
        "matched_whole_process_compute_proven": False,
        "arms": {},
    }
    original_checkpoint = digest(fit["dynamics"])
    for kind in KINDS:
        worlds = []
        for seed in (*FAULT_WORLDS, *NO_FAULT_WORLDS):
            cold = episode(gym, seed, kind, cold_model, tau)
            warm = episode(gym, seed, kind, fit["dynamics"], tau)
            if (canonical(cold["transitions"]) != canonical(warm["transitions"])
                    or cold["initial"] != warm["initial"]
                    or cold["flips"] != warm["flips"]
                    or cold["probes"] != warm["probes"]):
                raise ValueError("F43_REAL_COLD_WARM_TRACE_MISMATCH")
            trace = cold["transitions"]
            worlds.append({
                "seed": seed,
                "return": cold["return"],
                "steps": cold["steps"],
                "probes": cold["probes"],
                "flips": cold["flips"],
                "informative": cold["informative"],
                "faulted_commands": cold["faulted_commands"],
                "boundaries_reached": cold["boundaries_reached"],
                "decision_ns": cold["decision_ns"],
                "terminated": cold["terminated"],
                "truncated": cold["truncated"],
                "requested_action_sha256": digest([t["requested"] for t in trace]),
                "evaluator_effective_action_sha256": digest([t["effective"] for t in trace]),
                "observation_sha256": digest([cold["initial"], [t["next"] for t in trace]]),
                "reward_sha256": digest([t["reward"] for t in trace]),
                "cold_matches": True,
            })
        report["arms"][kind] = {
            "worlds": worlds,
            "fault_mean_return": sum(x["return"] for x in worlds[:4]) / 4,
            "no_fault_mean_return": sum(x["return"] for x in worlds[4:]) / 2,
        }
    best = max(CONVENTIONAL, key=lambda k: report["arms"][k]["fault_mean_return"])
    cand = report["arms"]["calibrated-contradiction"]
    base = report["arms"][best]
    report["strongest_conventional"] = best
    report["candidate_mean_gain"] = cand["fault_mean_return"] - base["fault_mean_return"]
    report["candidate_seed_gains_ge10"] = sum(
        x["return"] >= y["return"] + 10
        for x, y in zip(cand["worlds"][:4], base["worlds"][:4])
    )
    report["candidate_fault_worlds_with_switch"] = sum(x["flips"] >= 1 for x in cand["worlds"][:4])
    conventional_retention = max(report["arms"][k]["no_fault_mean_return"] for k in CONVENTIONAL)
    report["strongest_conventional_retention"] = conventional_retention
    report["no_fault_retention_margin"] = cand["no_fault_mean_return"] - conventional_retention
    report["frozen_thresholds_met"] = bool(
        report["candidate_mean_gain"] >= 15
        and report["candidate_seed_gains_ge10"] >= 3
        and report["candidate_fault_worlds_with_switch"] >= 2
        and report["no_fault_retention_margin"] >= -5
        and all(cand["fault_mean_return"] >= report["arms"][ab]["fault_mean_return"] + 15
                for ab in ABLATIONS)
        and all(world["probes"] == 0 for world in cand["worlds"])
        and all(world["cold_matches"] and world["probes"] <= 16
                for arm in report["arms"].values() for world in arm["worlds"])
        and all(len(arm["worlds"]) == 6 for arm in report["arms"].values())
    )
    if digest(fit["dynamics"]) != original_checkpoint:
        raise ValueError("F43_LEARNED_MODEL_MUTATED_AFTER_COLD_EVALUATION")
    # Fake fixtures may validate mechanics but can NEVER classify scientific results.
    report["classification"] = "F43_ORIGINAL_RUNTIME_UNVERIFIED"
    report["report_sha256"] = digest(report)
    return report


def original_gym(root):
    return f41.original_gym(root)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        raise ValueError("F43_USAGE: source.py /original/gymnasium /tmp/report.json")
    root = Path(argv[0]).resolve(strict=True)
    dest = Path(argv[1]).resolve()
    if dest.is_relative_to(root):
        raise ValueError("F43_REPORT_INSIDE_PINNED_ORIGINAL_REFUSED")
    try:
        gym, git = original_gym(root)
    except (ImportError, FileNotFoundError) as error:
        raise RuntimeError("F43_ORIGINAL_RUNTIME_BLOCKED") from error
    start = time.perf_counter()
    fit = source_fit(gym)
    trained = time.perf_counter()
    result = assess(gym, fit, SOURCE)
    assessed = time.perf_counter()
    original_gym(root)
    if git(root, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"):
        raise ValueError("F43_ORIGINAL_PINNED_SOURCE_MUTATED")
    if result["classification"] != "F43_ORIGINAL_RUNTIME_UNVERIFIED":
        raise ValueError("F43_UNVERIFIED_FAKE_CAN_NOT_BE_ACCEPTED")
    result["training_and_fit_seconds"] = trained - start
    result["evaluation_seconds"] = assessed - trained
    result["classification"] = (
        "F43_DEV_SIGNAL_UNVERIFIED" if result["frozen_thresholds_met"] else "F43_DEV_NO_GO"
    )
    result["report_sha256"] = digest({k:v for k,v in result.items() if k != "report_sha256"})
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(canonical(result) + b"\n")
    print("F43_ORIGINAL_FAULT_CHANNEL_DEV=" + result["classification"]
          + " report_sha256=" + result["report_sha256"])
    print("F43_TRAINING_ONLY_TAU=" + str(result["training_only_tau"])
          + " calibration_n=" + str(result["calibration_n"]))
    print("F43_STRONGEST_CONVENTIONAL=" + result["strongest_conventional"]
          + " candidate_gain=" + str(result["candidate_mean_gain"])
          + " wins_ge10=" + str(result["candidate_seed_gains_ge10"]))
    return result


if __name__ == "__main__":
    main()
