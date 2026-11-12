#!/usr/bin/env python3
"""F46 source-only *synthetic* causal action-information development experiment.

This is not genuine independent scientific data, trained neural intelligence or
Gymnasium original physics. It never touches FORGE owner, FSA, or first-use.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time

EFFECTS = ((1, 2), (1, 3), (2, 3), (3, 2), (2, 1), (3, 1))
FIT = (2100, 2101, 2102, 2103, 2112, 2113, 2114, 2115)
TRANSFER = (2302, 2303, 2308, 2309, 2314, 2315, 2320, 2321,
            2326, 2327, 2332, 2333, 2338, 2339, 2344, 2345,
            2350, 2351, 2356, 2357, 2362, 2363, 2368, 2369)
RETENTION = (2502, 2503, 2504, 2505, 2514, 2515, 2516, 2517)
ARMS = ("active-information", "bayes-greedy", "bayes-two-step",
        "trained-empirical", "seeded-random", "wrong-credit",
        "no-feedback", "info-only")
CONVENTIONAL = ARMS[1:5]
NEGATIVES = ("wrong-credit", "no-feedback")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def lcg(seed):
    """Deterministic unsigned LCG; public source, no hidden model calls."""
    state = int(seed) & 0xffffffff
    while True:
        state = (1664525 * state + 1013904223) & 0xffffffff
        yield state


def bit_distance(a, b):
    return ((a ^ b) & 1) + (((a ^ b) >> 1) & 1)


class CausalWorld:
    """Evaluator owns hidden mode; policy gets only public state/goal/reward."""
    def __init__(self, source_seed, state, goal):
        if type(source_seed) is not int or not 0 <= source_seed <= 10**8:
            raise ValueError("F46_INVALID_SOURCE_SEED")
        if state not in range(4) or goal not in range(4) or state == goal:
            raise ValueError("F46_INVALID_PUBLIC_TASK")
        self._mode = source_seed % 6
        self.state = state
        self.goal = goal
        self.done = False
        self.steps = 0

    def step(self, action):
        if self.done or type(action) is not int or action not in (0, 1, 2):
            raise ValueError("F46_INVALID_REAL_WORLD_STEP")
        effect = EFFECTS[self._mode][action] if action != 2 else 0
        self.state = self.state ^ effect
        self.steps += 1
        reached = self.state == self.goal
        self.done = reached or self.steps == 5
        return self.state, (9 if reached else -1), self.done


def collect_training():
    worlds = []
    observed_action_counts = [0, 0, 0]
    for seed in FIT:
        records = []
        for episode in range(16):
            stream = lcg((seed << 12) ^ (episode * 891) ^ 0xF46A1)
            state = next(stream) % 4
            for _ in range(5):
                action = (next(stream) >> 16) % 3
                # Open-loop FIT is not scored DEV; every request is physically
                # applied in the same hidden world, even if a goal was reached.
                effect = EFFECTS[seed % 6][action] if action != 2 else 0
                next_state = state ^ effect
                records.append([state, action, next_state])
                observed_action_counts[action] += 1
                state = next_state
        worlds.append(records)
    if len(worlds) != 8 or sum(len(w) for w in worlds) != 640:
        raise ValueError("F46_COMMON_FIT_TRANSCRIPT_SHAPE")
    if not all(observed_action_counts):
        raise ValueError("F46_MISSING_FIT_ACTION")
    return worlds, observed_action_counts


def fit_shared(worlds):
    counts = [1] * 6  # shared Dirichlet pseudocount, never zero support
    effects_counts = [{i: 0 for i in range(4)} for _ in range(3)]
    identified = []
    for world in worlds:
        consistent = [mode for mode in range(6)
                      if all((s ^ next_s) ==
                             (EFFECTS[mode][a] if a != 2 else 0)
                             for s, a, next_s in world)]
        if len(consistent) != 1:
            raise ValueError("F46_FIT_WORLD_NOT_IDENTIFIABLE")
        identified.append(consistent[0])
        counts[consistent[0]] += 1
        for s, a, next_s in world:
            effects_counts[a][s ^ next_s] += 1
    if tuple(sorted(set(identified))) != (0, 1, 2, 3):
        raise ValueError("F46_FIT_MODE_COVERAGE_DRIFT")
    prior = [c / sum(counts) for c in counts]
    empirical = [min(range(4), key=lambda e: (-effects_counts[a][e], e))
                 for a in range(3)]
    return {"prior": prior, "empirical": empirical,
            "fit_mode_counts": counts, "identified_mode_types": 4}


def entropy(probs):
    return -sum(p * math.log(p) for p in probs if p > 0)


def expected_next(probs, action):
    possible = {}
    for mode, prob in enumerate(probs):
        effect = EFFECTS[mode][action] if action != 2 else 0
        possible[effect] = possible.get(effect, 0.0) + prob
    return possible


def update(probs, action, observed_effect, *, corrupt=False):
    if corrupt:
        observed_effect = (observed_effect + 1) % 4
    supported = [p if (EFFECTS[m][action] if action != 2 else 0) == observed_effect else 0
                 for m, p in enumerate(probs)]
    norm = sum(supported)
    if norm <= 0:
        if corrupt:
            return probs[:]  # Negative control cannot fabricate unseen evidence.
        raise ValueError("F46_IMPOSSIBLE_OBSERVED_CAUSAL_EFFECT")
    return [p / norm for p in supported]


def info_gain(probs, action):
    h0 = entropy(probs)
    remaining = 0.0
    for effect, mass in expected_next(probs, action).items():
        if mass:
            post = update(probs, action, effect)
            remaining += mass * entropy(post)
    return h0 - remaining


def immediate_score(state, goal, probs, action):
    return sum(mass *
               (4.0 * (state ^ effect == goal)
                - 0.5 * bit_distance(state ^ effect, goal))
               for effect, mass in expected_next(probs, action).items())


def bayes_two_step_score(state, goal, probs, action):
    total = 0.0
    for effect, mass in expected_next(probs, action).items():
        if not mass:
            continue
        nxt = state ^ effect
        if nxt == goal:
            total += mass * 4.0
            continue
        post = update(probs, action, effect)
        best = max(sum(pr * (1.0 if (nxt ^ e) == goal else 0.0)
                       for e, pr in expected_next(post, a2).items())
                   for a2 in (0, 1, 2))
        total += mass * (4.0 * best - 0.1 * bit_distance(nxt, goal))
    return total


class Policy:
    def __init__(self, kind, fit, episode):
        if kind not in ARMS:
            raise ValueError("F46_UNKNOWN_POLICY")
        self.kind = kind
        self.probs = list(fit["prior"])
        self.empirical = list(fit["empirical"])
        self.generator = lcg(0xF460000 + 131 * episode)
        self.decision_ns = 0
        self.observations = 0
        self.changes = 0

    def action(self, state, goal):
        start = time.perf_counter_ns()
        if self.kind == "seeded-random":
            action = (next(self.generator) >> 16) % 3
        elif self.kind == "trained-empirical":
            action = max((0, 1, 2),
                         key=lambda a: (4 * (state ^ self.empirical[a] == goal)
                                        - 0.5 * bit_distance(state ^ self.empirical[a], goal),
                                        -a))
        elif self.kind == "bayes-two-step":
            action = max((0, 1, 2),
                         key=lambda a: (bayes_two_step_score(state, goal, self.probs, a), -a))
        else:
            if self.kind == "info-only":
                scores = [info_gain(self.probs, a) for a in (0, 1, 2)]
            else:
                bonus = 0.0 if self.kind == "bayes-greedy" else 0.65
                scores = [immediate_score(state, goal, self.probs, a)
                          + bonus * info_gain(self.probs, a) for a in (0, 1, 2)]
            action = max(range(3), key=lambda a: (scores[a], -a))
        self.decision_ns += time.perf_counter_ns() - start
        return int(action)

    def observe(self, previous, action, nxt):
        self.observations += 1
        if self.kind in ("no-feedback", "trained-empirical", "seeded-random"):
            return
        new = update(self.probs, action, previous ^ nxt,
                     corrupt=self.kind == "wrong-credit")
        if new != self.probs:
            self.changes += 1
        self.probs = new

    def snapshot(self):
        return {"kind": self.kind, "probs": self.probs,
                "empirical": self.empirical,
                "observations": self.observations, "changes": self.changes}


def task(seed, episode):
    start = (seed * 7 + episode * 3) % 4
    goal = (start + 1 + ((seed + episode) % 3)) % 4
    if goal == start:
        raise ValueError("F46_TASK_GOAL_EQUALS_START")
    return start, goal


def evaluate_episode(seed, episode, kind, fit):
    if seed not in (*TRANSFER, *RETENTION):
        raise ValueError("F46_EVALUATION_SEED_NOT_FROZEN")
    state, goal = task(seed, episode)
    world = CausalWorld(seed, state, goal)
    model = Policy(kind, fit, episode)
    trace = []
    for _ in range(5):
        action = model.action(world.state, goal)
        old = world.state
        nxt, reward, done = world.step(action)
        model.observe(old, action, nxt)
        trace.append([old, action, nxt, reward, done])
        if done:
            break
    return {"seed": seed, "episode": episode, "success": world.state == goal,
            "return": sum(t[3] for t in trace), "steps": len(trace),
            "trace": trace, "snapshot": model.snapshot(),
            "decision_ns": model.decision_ns}


def evaluate(fit, training_hash):
    if len(fit["prior"]) != 6 or len(fit["empirical"]) != 3:
        raise ValueError("F46_FIT_MODEL_SHAPE_DRIFT")
    if len(set((*FIT, *TRANSFER, *RETENTION))) != 40:
        raise ValueError("F46_FROZEN_SEED_OVERLAP")
    if any(seed % 6 not in (4, 5) for seed in TRANSFER):
        raise ValueError("F46_TRANSFER_MODE_LEAK")
    if any(seed % 6 not in (0, 1, 2, 3) for seed in RETENTION):
        raise ValueError("F46_RETENTION_MODE_LEAK")
    fit_json = canonical(fit)
    cold = json.loads(fit_json)
    if canonical(cold) != fit_json:
        raise ValueError("F46_COLD_FIT_RESTORE_DRIFT")
    report = {"schema": "forge.eureka.f46.causal-information-synthetic-dev.v1",
              "synthetic_only": True, "original_gymnasium_used": False,
              "scientific_accepted": False, "first_use_consumed": False,
              "owner_eligible": False, "general_rsi_proven": False,
              "matched_whole_process_compute_proven": False,
              "training_sha256": training_hash, "training_transitions": 640,
              "fitted_sha256": digest(fit),
              "fit_prior": fit["prior"], "fit_empirical": fit["empirical"],
              "transfer_seeds": TRANSFER, "retention_seeds": RETENTION,
              "arms": {}}
    for kind in ARMS:
        worlds = []
        for seed in (*TRANSFER, *RETENTION):
            episodes = []
            for ep in range(4):
                warm = evaluate_episode(seed, ep, kind, fit)
                cold_episode = evaluate_episode(seed, ep, kind, cold)
                if (canonical(warm["trace"]) != canonical(cold_episode["trace"])
                        or canonical(warm["snapshot"]) != canonical(cold_episode["snapshot"])
                        or warm["return"] != cold_episode["return"]):
                    raise ValueError("F46_INDEPENDENT_COLD_REPLAY_DRIFT")
                episodes.append({
                    "episode": ep, "return": warm["return"],
                    "success": warm["success"], "steps": warm["steps"],
                    "action_trace_sha256": digest([t[1] for t in warm["trace"]]),
                    "state_consequence_sha256": digest(warm["trace"]),
                    "cold_matches": True, "decision_ns": warm["decision_ns"],
                })
            worlds.append({"seed": seed, "episodes": episodes,
                           "successes": sum(x["success"] for x in episodes),
                           "mean_return": sum(x["return"] for x in episodes) / 4.0})
        transfer_worlds = worlds[:24]
        clean_worlds = worlds[24:]
        total_decision_ns = sum(ep["decision_ns"] for w in transfer_worlds for ep in w["episodes"])
        total_actions = sum(ep["steps"] for w in transfer_worlds for ep in w["episodes"])
        report["arms"][kind] = {
            "worlds": worlds,
            "transfer_success_rate": sum(w["successes"] for w in transfer_worlds) / 96,
            "retention_success_rate": sum(w["successes"] for w in clean_worlds) / 32,
            "transfer_mean_return": sum(w["mean_return"] for w in transfer_worlds) / 24,
            "transfer_decision_ns_per_action": total_decision_ns / total_actions,
            "actual_transfer_actions": total_actions,
        }
    best = max(CONVENTIONAL, key=lambda k: report["arms"][k]["transfer_success_rate"])
    ca = report["arms"]["active-information"]
    base = report["arms"][best]
    report["strongest_conventional"] = best
    report["success_rate_gain"] = ca["transfer_success_rate"] - base["transfer_success_rate"]
    report["return_gain"] = ca["transfer_mean_return"] - base["transfer_mean_return"]
    report["paired_world_success_wins"] = sum(
        a["successes"] > b["successes"]
        for a, b in zip(ca["worlds"][:24], base["worlds"][:24]))
    report["best_control_retention"] = max(
        report["arms"][k]["retention_success_rate"] for k in CONVENTIONAL)
    report["retention_margin"] = ca["retention_success_rate"] - report["best_control_retention"]
    report["cost_ratio"] = (ca["transfer_decision_ns_per_action"] /
                            base["transfer_decision_ns_per_action"])
    report["frozen_conditions_met"] = bool(
        report["success_rate_gain"] >= .10 and report["return_gain"] >= .5
        and report["paired_world_success_wins"] >= 16
        and all(ca["transfer_success_rate"] >=
                report["arms"][k]["transfer_success_rate"] + .10 for k in NEGATIVES)
        and report["retention_margin"] >= -.05
        and report["cost_ratio"] <= 2.0
        and all(all(ep["cold_matches"] for w in arm["worlds"] for ep in w["episodes"])
                for arm in report["arms"].values()))
    report["classification"] = ("F46_DEV_SIGNAL_UNVERIFIED" if report["frozen_conditions_met"]
                                else "F46_DEV_NO_GO")
    report["report_sha256"] = digest(report)
    return report


def main(args=None):
    args = sys.argv[1:] if args is None else args
    if len(args) != 1:
        raise ValueError("F46_USAGE: python f46_causal_information_dev.py /tmp/report.json")
    out = Path(args[0]).resolve()
    worlds, action_counts = collect_training()
    report = evaluate(fit_shared(worlds), digest(worlds))
    report["fit_action_counts"] = action_counts
    report["report_sha256"] = digest({k: v for k, v in report.items() if k != "report_sha256"})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical(report) + b"\n")
    print("F46_SYNTHETIC_CAUSAL_DEV="+report["classification"]
          +" report_sha256="+report["report_sha256"])
    print("F46_TRANSITIONS=640 fit_sha256="+report["training_sha256"])
    print("F46_BASELINE="+report["strongest_conventional"]+
          " success_gain="+str(report["success_rate_gain"])+
          " paired_world_wins="+str(report["paired_world_success_wins"])+
          " return_gain="+str(report["return_gain"])+
          " cost_ratio="+str(report["cost_ratio"]))
    return report


if __name__ == "__main__":
    main()
