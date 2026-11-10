#!/usr/bin/env python3
"""F42 DEV: original MountainCar physics with externally injected hidden actuator faults.

The fault harness, not Gymnasium, remaps commanded actions. No private source
state, first-use, fake-original classification, owner, scheduler or deployment.
"""
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

import f41_original_mountaincar_dev as f41

SOURCE = f41.SOURCE
TRAIN_HASH = "174dee337d801c1046bd0d26b0ff0c50f89adf36cce4489c43100b4ea0dd1f34"
TRAIN_COUNTS = (7107, 3011, 8020)
FAULT_WORLDS = {
    1103: ((40, 96), (132, 170)),
    1117: ((44, 100), (138, 176)),
    1129: ((36, 92), (130, 174)),
    1151: ((48, 104), (136, 180)),
}
RETAIN_WORLDS = (1201, 1213)
FORBIDDEN = (59, 83)
KINDS = (
    "contradiction-probe",
    "bayes-probe",
    "bayes-no-probe",
    "rolling8-probe",
    "fixed-mpc",
    "velocity-rule",
    "wrong-credit-probe",
    "no-adaptation-probe",
)
CONVENTIONAL = (
    "bayes-probe", "bayes-no-probe", "rolling8-probe",
    "fixed-mpc", "velocity-rule",
)
ABLATIONS = ("wrong-credit-probe", "no-adaptation-probe")
PROBING = (
    "contradiction-probe", "bayes-probe", "rolling8-probe",
    "wrong-credit-probe", "no-adaptation-probe",
)
SIGMA = 0.0025


def canonical(obj):
    return f41.canonical(obj)


def digest(obj):
    return f41.digest(obj)


def fault_active(step, windows):
    return any(start <= step < stop for start, stop in windows)


def effective_action(command, step, windows):
    if type(command) is not int or command not in (0, 1, 2):
        raise ValueError("F42_INVALID_COMMANDED_ACTION")
    return 2 - command if fault_active(step, windows) else command


def fitted_training(gym):
    transcript, counts = f41.training(gym)
    got = digest(transcript)
    if got != TRAIN_HASH or len(transcript) != 18138 or tuple(counts) != TRAIN_COUNTS:
        raise ValueError("F42_F41_TRAIN_ONLY_TRANSCRIPT_DRIFT")
    model = f41.fit_dynamics(transcript)
    if np.asarray(model["global"]).shape != (6, 2):
        raise ValueError("F42_COMMON_DYNAMICS_DRIFT")
    model = json.loads(canonical(model))
    return model, got, counts


def reversal_evidence(state, commanded, next_state, model):
    if commanded not in (0, 1, 2):
        raise ValueError("F42_INVALID_FEEDBACK_ACTION")
    prior = f41.public_obs(state)
    observed = f41.public_obs(next_state)
    a_normal = f41.predict([prior], [commanded], model)[0]
    a_reverse = f41.predict([prior], [2 - commanded], model)[0]
    if abs(float(a_normal[1] - a_reverse[1])) <= 0.00025:
        return 0.0
    e_normal = float(observed[1] - a_normal[1]) ** 2
    e_reverse = float(observed[1] - a_reverse[1]) ** 2
    raw = (e_normal - e_reverse) / (2 * SIGMA * SIGMA)
    if not math.isfinite(raw):
        raise ValueError("F42_NONFINITE_CAUSAL_EVIDENCE")
    return float(np.clip(raw, -4, 4))


class Policy:
    """Only public source-fit model, requested action and observed outcomes."""
    def __init__(self, kind, common_model):
        if kind not in KINDS:
            raise ValueError("F42_UNKNOWN_POLICY")
        self.kind = kind
        self.model = common_model
        self.as_reverse = False
        self.posterior = 0.02
        self.recent3 = []
        self.recent8 = []
        self.flips = 0
        self.probes = 0
        self.informative = 0
        self.decision_ns = 0
        self.planner = {"global-linear-mpc": {**common_model, "gate": False}}

    def decide(self, state, step):
        tick = time.perf_counter_ns()
        public = f41.public_obs(state)
        if self.kind == "velocity-rule":
            cmd = f41.velocity_rule(public)
        else:
            intended = f41.mpc_action(public, "global-linear-mpc", self.planner)
            cmd = 2 - intended if self.as_reverse else intended
        if self.kind in PROBING and step % 12 == 0 and self.probes < 16:
            cmd = 0 if (step // 12) % 2 == 0 else 2
            self.probes += 1
        if cmd not in (0, 1, 2):
            raise ValueError("F42_INVALID_SELECTED_ACTION")
        self.decision_ns += time.perf_counter_ns() - tick
        return int(cmd)

    def observe(self, previous, commanded, next_state):
        tick = time.perf_counter_ns()
        evidence = reversal_evidence(previous, commanded, next_state, self.model)
        if evidence != 0:
            self.informative += 1
        if self.kind in ("contradiction-probe", "wrong-credit-probe"):
            if self.kind == "wrong-credit-probe":
                evidence = -evidence
            if evidence:
                self.recent3 = (self.recent3 + [evidence])[-3:]
                # Sign of L supports reversed=positive, normal=negative.
                wants = -1 if self.as_reverse else 1
                if sum(x * wants >= 0.9 for x in self.recent3) >= 2:
                    self.as_reverse = not self.as_reverse
                    self.flips += 1
                    self.recent3.clear()
        elif self.kind in ("bayes-probe", "bayes-no-probe"):
            if evidence:
                prior = 0.03 + 0.94 * self.posterior
                odds = (prior / (1 - prior)) * math.exp(evidence)
                self.posterior = odds / (1 + odds)
                switched = self.posterior >= 0.5
                if switched != self.as_reverse:
                    self.flips += 1
                self.as_reverse = switched
        elif self.kind == "rolling8-probe":
            if evidence:
                self.recent8 = (self.recent8 + [evidence])[-8:]
                switched = sum(self.recent8) > 0
                if switched != self.as_reverse:
                    self.flips += 1
                self.as_reverse = switched
        self.decision_ns += time.perf_counter_ns() - tick


def episode(gym, seed, kind, common_model):
    if seed in FORBIDDEN or seed not in FAULT_WORLDS and seed not in RETAIN_WORLDS:
        raise ValueError("F42_UNAUTHORIZED_DEV_WORLD_OR_FIRST_USE")
    windows = FAULT_WORLDS.get(seed, ())
    env = gym.make("MountainCar-v0", render_mode=None)
    policy = Policy(kind, common_model)
    try:
        if env.action_space.n != 3:
            raise ValueError("F42_ORIGINAL_ACTION_GRAMMAR_DRIFT")
        observation, _discard = env.reset(seed=int(seed))
        state = f41.public_obs(observation)
        initial = state[:]
        trace = []
        faulted_commands = 0
        boundaries_reached = []
        starts = tuple(start for start, _ in windows)
        ends = tuple(stop for _, stop in windows)
        for t in range(200):
            command = policy.decide(state, t)
            physical = effective_action(command, t, windows)
            nxt_raw, reward, terminated, truncated, _discard = env.step(physical)
            nxt = f41.public_obs(nxt_raw)
            reward = float(reward)
            if not math.isfinite(reward) or type(terminated) is not bool or type(truncated) is not bool:
                raise ValueError("F42_INVALID_ORIGINAL_STEP")
            if physical != command:
                faulted_commands += 1
            if t in starts or t in ends:
                boundaries_reached.append(t)
            policy.observe(state, command, nxt)
            trace.append({
                "requested": command, "effective": physical,
                "next": nxt, "reward": reward,
                "terminated": terminated, "truncated": truncated,
            })
            state = nxt
            if terminated or truncated:
                break
        if not trace:
            raise ValueError("F42_NO_REAL_STEPS")
        return {
            "initial": initial,
            "trace": trace,
            "return": sum(z["reward"] for z in trace),
            "steps": len(trace),
            "probes": policy.probes,
            "flips": policy.flips,
            "informative": policy.informative,
            "final_reverse_hypothesis": policy.as_reverse,
            "final_posterior": policy.posterior,
            "decision_ns": policy.decision_ns,
            "faulted_commands": faulted_commands,
            "boundaries_reached": boundaries_reached,
            "terminated": trace[-1]["terminated"],
            "truncated": trace[-1]["truncated"],
        }
    finally:
        env.close()


def assess(gym, common_model, training_hash, source):
    cold_bytes = canonical(common_model)
    cold_model = json.loads(cold_bytes)
    if canonical(cold_model) != cold_bytes:
        raise ValueError("F42_COLD_MODEL_RESTORE_DRIFT")
    report = {
        "schema": "forge.eureka.original-actuator-reversal-dev.f42.v1",
        "source": source, "training_sha256": training_hash,
        "checkpoint_sha256": digest(common_model),
        "faulted_eval_seeds": tuple(FAULT_WORLDS),
        "no_fault_eval_seeds": RETAIN_WORLDS,
        "development_only": True,
        "original_physics_with_external_actuator_fault": True,
        "unmodified_original_gymnasium_task": False,
        "first_use_consumed": False,
        "scientific_accepted": False,
        "owner_eligible": False,
        "matched_whole_process_compute_proven": False,
        "arms": {},
    }
    for kind in KINDS:
        worlds = []
        for seed in (*FAULT_WORLDS, *RETAIN_WORLDS):
            cold = episode(gym, seed, kind, cold_model)
            warm = episode(gym, seed, kind, common_model)
            if (canonical(cold["trace"]) != canonical(warm["trace"])
                    or cold["initial"] != warm["initial"]
                    or cold["probes"] != warm["probes"]
                    or cold["flips"] != warm["flips"]):
                raise ValueError("F42_ORIGINAL_COLD_WARM_PHYSICAL_TRACE_MISMATCH")
            trace = cold["trace"]
            worlds.append({
                "seed": seed, "return": cold["return"], "steps": cold["steps"],
                "actions_sha256": digest([x["requested"] for x in trace]),
                "effective_actions_sha256": digest([x["effective"] for x in trace]),
                "observations_sha256": digest([cold["initial"], [x["next"] for x in trace]]),
                "rewards_sha256": digest([x["reward"] for x in trace]),
                "probes": cold["probes"], "flips": cold["flips"],
                "informative": cold["informative"],
                "faulted_commands": cold["faulted_commands"],
                "boundaries_reached": cold["boundaries_reached"],
                "terminated": cold["terminated"], "truncated": cold["truncated"],
                "decision_ns": cold["decision_ns"],
                "cold_matches": True,
            })
        report["arms"][kind] = {
            "worlds": worlds,
            "fault_mean_return": sum(x["return"] for x in worlds[:4]) / 4,
            "no_fault_mean_return": sum(x["return"] for x in worlds[4:]) / 2,
        }
    best = max(CONVENTIONAL, key=lambda k: report["arms"][k]["fault_mean_return"])
    cand = report["arms"]["contradiction-probe"]
    baseline = report["arms"][best]
    report["strongest_conventional"] = best
    report["candidate_mean_gain"] = cand["fault_mean_return"] - baseline["fault_mean_return"]
    report["candidate_seed_gains_ge10"] = sum(
        c["return"] >= b["return"] + 10
        for c, b in zip(cand["worlds"][:4], baseline["worlds"][:4])
    )
    strongest_retention = max(report["arms"][k]["no_fault_mean_return"] for k in CONVENTIONAL)
    report["strongest_conventional_no_fault_mean"] = strongest_retention
    report["no_fault_retention_margin"] = cand["no_fault_mean_return"] - strongest_retention
    report["first_return_seen_each_fault_world"] = all(
        all(boundary in world["boundaries_reached"] for boundary in (s0, e0))
        for world, ((s0, e0), _other) in zip(cand["worlds"][:4], FAULT_WORLDS.values())
    )
    report["frozen_thresholds_met"] = bool(
        report["candidate_mean_gain"] >= 15
        and report["candidate_seed_gains_ge10"] >= 3
        and all(cand["fault_mean_return"] >= report["arms"][kind]["fault_mean_return"] + 15
                for kind in ABLATIONS)
        and report["no_fault_retention_margin"] >= -5
        and report["first_return_seen_each_fault_world"]
        and all(all(w["cold_matches"] and w["probes"] <= 16 for w in arm["worlds"])
                for arm in report["arms"].values())
    )
    report["classification"] = "F42_ORIGINAL_RUNTIME_UNVERIFIED"
    report["report_sha256"] = digest(report)
    return report


def original_gym(root):
    return f41.original_gym(root)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        raise ValueError("F42_USAGE: source.py /pinned/Gymnasium /report/out.json")
    root = Path(argv[0]).resolve(strict=True)
    output = Path(argv[1]).resolve()
    if output.is_relative_to(root):
        raise ValueError("F42_OUTPUT_INSIDE_PINNED_ORIGINAL")
    try:
        gym, git = original_gym(root)
    except (ImportError, FileNotFoundError) as err:
        raise RuntimeError("F42_ORIGINAL_RUNTIME_BLOCKED") from err
    t0 = time.perf_counter()
    learned, train_hash, coverage = fitted_training(gym)
    t1 = time.perf_counter()
    result = assess(gym, learned, train_hash, SOURCE)
    t2 = time.perf_counter()
    result["train_episodes"] = 96
    result["train_transitions"] = 18138
    result["train_action_counts"] = coverage
    result["training_and_fit_seconds"] = t1 - t0
    result["evaluation_seconds"] = t2 - t1
    original_gym(root)
    if git(root, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"):
        raise ValueError("F42_ORIGINAL_SOURCE_MUTATED_DURING_EXECUTION")
    if result["classification"] != "F42_ORIGINAL_RUNTIME_UNVERIFIED":
        raise ValueError("F42_FAKE_SOURCE_CLASSIFICATION_REFUSED")
    result["classification"] = (
        "F42_DEV_SIGNAL_UNVERIFIED" if result["frozen_thresholds_met"]
        else "F42_DEV_NO_GO"
    )
    result["report_sha256"] = digest({k: v for k, v in result.items() if k != "report_sha256"})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical(result) + b"\n")
    print("F42_ORIGINAL_FAULT_CHANNEL_DEV=" + result["classification"]
          + " digest=" + result["report_sha256"])
    print("F42_REAL_TRAINING=" + str(result["train_transitions"])
          + " checksum=" + train_hash)
    print("F42_STRONGEST=" + result["strongest_conventional"]
          + " candidate_gain=" + str(result["candidate_mean_gain"])
          + " wins_ge10=" + str(result["candidate_seed_gains_ge10"]))
    return result


if __name__ == "__main__":
    main()
