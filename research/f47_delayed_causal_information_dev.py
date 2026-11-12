#!/usr/bin/env python3
"""F47: delayed physical action consequences + paid noisy diagnosis (synthetic DEV).

All evaluation is deterministic and source-owned, never an original outside
environment or scientific first use. The causal-world object is evaluator-only;
the policies receive only public state, goal, pending command and public signals.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time

EFFECTS = ((1, 2), (1, 4), (2, 4), (2, 1), (4, 2), (4, 1))
FIT_SEEDS = (3102, 3103, 3104, 3105, 3114, 3115, 3116, 3117)
TRANSFER_SEEDS = (
    3304, 3305, 3310, 3311, 3316, 3317, 3322, 3323,
    3328, 3329, 3334, 3335, 3340, 3341, 3346, 3347,
    3352, 3353, 3358, 3359, 3364, 3365, 3370, 3371,
)
RETENTION_SEEDS = (3504, 3505, 3506, 3507, 3510, 3511, 3512, 3513,
                   3516, 3517, 3518, 3519)
FORBIDDEN = (59, 83)
ARMS = ("active-probe", "bayes-two-step", "bayes-one-step", "trained-empirical",
        "seeded-random", "wrong-credit", "no-feedback", "info-only")
CONVENTIONAL = ARMS[1:5]
NEGATIVES = ("wrong-credit", "no-feedback")
DURATION = 6
SENSOR_BONUS = 0.8
HAZARD = 0.08


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(x):
    return hashlib.sha256(canonical(x)).hexdigest()


def lcg_step(x):
    return (1664525 * (x & 0xffffffff) + 1013904223) & 0xffffffff


def distance(a, b):
    return (a ^ b).bit_count()


def task(seed, episode):
    if type(seed) is not int or type(episode) is not int or not 0 <= episode < 12:
        raise ValueError("F47_UNAUTHORIZED_WORLD_TASK")
    state = (seed * 3 + episode * 5 + 1) % 8
    goal = state ^ (1 + ((seed + episode * 7) % 7))
    if goal == state:
        raise ValueError("F47_GOAL_NOT_DISTINCT")
    return state, goal


def exogenous(seed, episode, step):
    """Evaluator-only, fixed noise independent of physical command or policy."""
    x = ((seed * 2654435761) ^ ((episode + 7) * 2246822519)
         ^ ((step + 11) * 3266489917) ^ 0xF4700000) & 0xffffffff
    x = lcg_step(x)
    noise = (1, 2, 4)[lcg_step(x) % 3] if x % 5 == 0 else 0
    x = lcg_step(lcg_step(x))
    flip_witness = (x % 5 == 0)
    return noise, flip_witness


class CausalWorld:
    def __init__(self, seed, episode, *, switching):
        if type(seed) is not int or seed not in (*FIT_SEEDS, *TRANSFER_SEEDS, *RETENTION_SEEDS):
            raise ValueError("F47_UNAUTHORIZED_WORLD_OR_PROTECTED_FIRST_USE")
        state, goal = task(seed, episode)
        self._seed = seed
        self._episode = episode
        self._initial_mode = seed % 6
        self._switching = bool(switching)
        self.state = state
        self.goal = goal
        self.pending = 2
        self.steps = 0
        self.done = False

    def step(self, requested):
        if self.done or type(requested) is not int or requested not in (0, 1, 2):
            raise ValueError("F47_INVALID_OR_EXTRA_REAL_ACTION")
        t = self.steps
        mode = ((self._initial_mode + 3) % 6
                if self._switching and t in (3, 4) else self._initial_mode)
        queued = self.pending
        predicted_effect = EFFECTS[mode][queued] if queued != 2 else 0
        noise, witness_flip = exogenous(self._seed, self._episode, t)
        self.state ^= predicted_effect ^ noise
        witness = ((int(mode >= 3) ^ int(witness_flip))
                   if queued == 2 else -1)
        self.pending = requested
        self.steps += 1
        self.done = self.steps == DURATION
        reward = -1
        if self.done:
            reward += 10 if self.state == self.goal else -2 * distance(self.state, self.goal)
        return self.state, witness, reward, self.done


def observed_likelihood(mode, pending, delta, witness):
    expected = EFFECTS[mode][pending] if pending != 2 else 0
    residual = delta ^ expected
    p = 0.8 if residual == 0 else (0.2 / 3 if residual in (1, 2, 4) else 0.0)
    if pending == 2:
        if witness not in (0, 1):
            raise ValueError("F47_SENSOR_MISSING_WHEN_PHYSICALLY_APPLIED")
        p *= 0.8 if witness == int(mode >= 3) else 0.2
    elif witness != -1:
        raise ValueError("F47_PHANTOM_PUBLIC_SENSOR")
    return p


def normalize(values):
    total = sum(values)
    if total <= 0 or not math.isfinite(total):
        raise ValueError("F47_INVALID_POSTERIOR_NO_LIKELIHOOD")
    return [v / total for v in values]


def fit_data():
    worlds = []
    coverage = [0, 0, 0]
    for seed in FIT_SEEDS:
        episodes = []
        for ep in range(12):
            world = CausalWorld(seed, ep, switching=False)
            records = []
            for action in (0, 2, 1, 0, 1, 2):
                old, pending = world.state, world.pending
                nxt, signal, reward, done = world.step(action)
                records.append([old, pending, action, nxt, signal, reward, done])
                coverage[action] += 1
            episodes.append(records)
        worlds.append(episodes)
    if len(worlds) != 8 or sum(len(ep) for w in worlds for ep in w) != 576:
        raise ValueError("F47_TRAINING_ONLY_TRANSCRIPT_COUNT")
    if coverage != [192, 192, 192]:
        raise ValueError("F47_TRAINING_ACTION_COVERAGE_DRIFT")
    return worlds, coverage


def fit_shared(worlds):
    if len(worlds) != 8 or any(len(w) != 12 for w in worlds):
        raise ValueError("F47_INVALID_FIT_COHORT")
    counts = [1.0] * 6
    evidence_counts = [{e: 0 for e in range(8)} for _ in range(3)]
    mode_winners = []
    n = 0
    for world in worlds:
        probs = [1 / 6] * 6
        for ep in world:
            for old, pending, requested, nxt, witness, reward, done in ep:
                if pending not in (0, 1, 2) or requested not in (0, 1, 2):
                    raise ValueError("F47_INVALID_LOGGED_ACTION")
                like = [observed_likelihood(m, pending, old ^ nxt, witness)
                        for m in range(6)]
                probs = normalize([p * l for p, l in zip(probs, like)])
                evidence_counts[pending][old ^ nxt] += 1
                n += 1
        counts = [x + p for x, p in zip(counts, probs)]
        mode_winners.append(max(range(6), key=lambda m: probs[m]))
    if n != 576:
        raise ValueError("F47_FIT_TRANSITIONS_INVALID")
    prior = normalize(counts)
    empirical = [min(range(8), key=lambda e: (-evidence_counts[a][e], e))
                 for a in range(3)]
    if any(not p > 0 for p in prior):
        raise ValueError("F47_FIT_UNSEEN_MODE_SUPPORT_LOST")
    return {"prior": prior, "empirical": empirical,
            "mode_winners": mode_winners, "fit_transition_count": n,
            "training_worlds": len(worlds)}


def update_belief(prior, fit_prior, pending, old, nxt, witness, *, corrupt=False):
    mixed = [(1 - HAZARD) * p + HAZARD * fit_prior[i]
             for i, p in enumerate(prior)]
    delta = old ^ nxt
    if corrupt:
        delta = (delta + 1) % 8
    weighted = [p * observed_likelihood(m, pending, delta, witness)
                for m, p in enumerate(mixed)]
    if sum(weighted) <= 0:
        if not corrupt:
            raise ValueError("F47_IMPOSSIBLE_SOURCE_EFFECT")
        return mixed, True
    return normalize(weighted), False


def witness_info(probs):
    """Exact information in an 80%-reliable binary witness; never a free source call."""
    mass_high = sum(probs[3:])
    q = 0.2 + 0.6 * mass_high

    def h2(x):
        return -x * math.log(x) - (1 - x) * math.log(1 - x) if 0 < x < 1 else 0
    return max(0.0, h2(q) - h2(0.2))


def two_step_score(state, goal, pending, action, prior):
    score = 0.0
    for mode, p in enumerate(prior):
        first = EFFECTS[mode][pending] if pending != 2 else 0
        second = EFFECTS[mode][action] if action != 2 else 0
        prospective = state ^ first ^ second
        score += p * (2.0 * int(prospective == goal) - distance(prospective, goal))
    return score


def one_step_score(state, goal, pending, action, prior):
    return sum(p * (
        -distance(state ^ (EFFECTS[m][pending] if pending != 2 else 0), goal)
        -0.5 * distance(state ^ (EFFECTS[m][pending] if pending != 2 else 0)
                        ^ (EFFECTS[m][action] if action != 2 else 0), goal))
               for m, p in enumerate(prior))


class Policy:
    def __init__(self, kind, fit, episode):
        if kind not in ARMS:
            raise ValueError("F47_UNKNOWN_CONTROL")
        self.kind = kind
        self.probs = list(fit["prior"])
        self.fit_prior = list(fit["prior"])
        self.empirical = list(fit["empirical"])
        self.random_state = (0x47F10102 + episode * 15679) & 0xffffffff
        self.decisions = 0
        self.sensors = 0
        self.updates = 0
        self.abstains = 0
        self.decision_ns = 0

    def decide(self, state, goal, pending, physical_t):
        started = time.perf_counter_ns()
        if not (0 <= state < 8 and 0 <= goal < 8 and pending in (0, 1, 2)
                and 0 <= physical_t < DURATION):
            raise ValueError("F47_INVALID_PUBLIC_POLICY_INPUT")
        if self.kind == "seeded-random":
            self.random_state = lcg_step(self.random_state)
            selected = (self.random_state >> 16) % 3
        elif self.kind == "trained-empirical":
            first = self.empirical[pending]
            selected = max(range(3),
                           key=lambda a: (-distance(state ^ first ^ self.empirical[a], goal), -a))
        elif self.kind == "bayes-one-step":
            selected = max(range(3),
                           key=lambda a: (one_step_score(state,goal,pending,a,self.probs), -a))
        elif self.kind == "info-only":
            selected = 2 if physical_t <= 3 and witness_info(self.probs) > 0 else 0
        else:
            bonus = (0 if self.kind == "bayes-two-step" else
                     SENSOR_BONUS * witness_info(self.probs))
            selected = max(range(3),
                           key=lambda a: (two_step_score(state,goal,pending,a,self.probs)
                                          + (bonus if a == 2 and physical_t <= 3 else 0), -a))
        self.decisions += 1
        if selected == 2:
            self.sensors += 1
        self.decision_ns += time.perf_counter_ns() - started
        return int(selected)

    def observe(self, old, pending_applied, new, witness):
        if self.kind in ("trained-empirical", "seeded-random", "no-feedback"):
            return
        new_probs, abstained = update_belief(
            self.probs, self.fit_prior, pending_applied, old, new, witness,
            corrupt=self.kind == "wrong-credit")
        if abstained:
            self.abstains += 1
        self.probs = new_probs
        self.updates += 1

    def snapshot(self):
        return {"kind": self.kind, "probs": self.probs,
                "decisions": self.decisions, "sensors": self.sensors,
                "updates": self.updates, "abstains": self.abstains}


def evaluate_episode(seed, ep, kind, fit):
    if type(seed) is not int or seed not in (*TRANSFER_SEEDS, *RETENTION_SEEDS):
        raise ValueError("F47_UNAUTHORIZED_DEV_OR_FIRST_USE_SEED")
    world = CausalWorld(seed, ep, switching=seed in TRANSFER_SEEDS)
    learner = Policy(kind, fit, ep)
    goal = world.goal
    trace = []
    for physical_t in range(DURATION):
        old, pending = world.state, world.pending
        command = learner.decide(old, goal, pending, physical_t)
        nxt, witness, reward, terminal = world.step(command)
        learner.observe(old, pending, nxt, witness)
        trace.append([old, pending, command, nxt, witness, reward, terminal])
    if not world.done or len(trace) != DURATION:
        raise ValueError("F47_REAL_ACTION_BUDGET_INCOMPLETE")
    success = world.state == goal
    return {"seed": seed, "episode": ep, "start": trace[0][0], "goal": goal,
            "success": success, "return": sum(t[5] for t in trace),
            "terminal_distance": distance(world.state, goal),
            "actual_actions": len(trace), "sensor_actions": learner.sensors,
            "trace": trace, "snapshot": learner.snapshot(),
            "decision_ns": learner.decision_ns}


def assess(fit, training_sha, coverage):
    if fit["fit_transition_count"] != 576 or fit["training_worlds"] != 8:
        raise ValueError("F47_FIT_CUSTODY_INVALID")
    if coverage != [192, 192, 192] or len(fit["prior"]) != 6:
        raise ValueError("F47_SHARED_TRAINING_COVERAGE_INVALID")
    if len(set((*FIT_SEEDS, *TRANSFER_SEEDS, *RETENTION_SEEDS))) != 44:
        raise ValueError("F47_FIT_DEV_SEED_COLLISION")
    if any(s % 6 not in (4, 5) for s in TRANSFER_SEEDS):
        raise ValueError("F47_UNSEEN_TRANSFER_MODE_LEAKAGE")
    if any(s % 6 not in (0, 1, 2, 3) for s in (*FIT_SEEDS, *RETENTION_SEEDS)):
        raise ValueError("F47_RETENTION_MODE_LEAKAGE")
    frozen = canonical(fit)
    cold = json.loads(frozen)
    if canonical(cold) != frozen:
        raise ValueError("F47_FIT_CHECKPOINT_RESTORE_DRIFT")
    report = {
        "schema": "forge.eureka.f47.delayed-causal-information-synthetic-dev.v1",
        "synthetic_only": True, "original_external_environment": False,
        "first_use_consumed": False, "scientific_accepted": False,
        "owner_eligible": False, "general_rsi_proven": False,
        "matched_whole_process_compute_proven": False,
        "training_sha256": training_sha, "fitted_sha256": digest(fit),
        "training_transitions": 576, "train_action_counts": coverage,
        "fit_prior": fit["prior"], "empirical_effects": fit["empirical"],
        "train_worlds": FIT_SEEDS, "transfer_worlds": TRANSFER_SEEDS,
        "retention_worlds": RETENTION_SEEDS, "arms": {},
    }
    for kind in ARMS:
        worlds = []
        for seed in (*TRANSFER_SEEDS, *RETENTION_SEEDS):
            episodes = []
            for ep in range(4):
                warm = evaluate_episode(seed, ep, kind, fit)
                cold_test = evaluate_episode(seed, ep, kind, cold)
                if (canonical(warm["trace"]) != canonical(cold_test["trace"])
                    or canonical(warm["snapshot"]) != canonical(cold_test["snapshot"])
                    or warm["success"] != cold_test["success"]
                    or warm["return"] != cold_test["return"]):
                    raise ValueError("F47_COLD_WARM_REAL_ACTION_TRACE_MISMATCH")
                episodes.append({
                    "episode": ep, "return": warm["return"],
                    "success": warm["success"], "actual_actions":warm["actual_actions"],
                    "sensor_actions":warm["sensor_actions"],
                    "terminal_distance":warm["terminal_distance"],
                    "trace_sha256":digest(warm["trace"]),
                    "policy_sha256":digest(warm["snapshot"]),
                    "decision_ns":warm["decision_ns"],
                    "cold_matches":True,
                })
            worlds.append({
                "seed": seed, "episodes": episodes,
                "successes": sum(e["success"] for e in episodes),
                "mean_return":sum(e["return"] for e in episodes)/4,
                "sensor_actions":sum(e["sensor_actions"] for e in episodes),
            })
        transfer=worlds[:24];retention=worlds[24:]
        decision_ns=sum(e["decision_ns"] for w in transfer for e in w["episodes"])
        actions=sum(e["actual_actions"] for w in transfer for e in w["episodes"])
        report["arms"][kind]={
            "worlds":worlds,
            "transfer_success":sum(w["successes"] for w in transfer)/96,
            "retention_success":sum(w["successes"] for w in retention)/48,
            "transfer_mean_return":sum(w["mean_return"] for w in transfer)/24,
            "transfer_sensor_worlds":sum(w["sensor_actions"]>0 for w in transfer),
            "transfer_sensor_actions":sum(w["sensor_actions"] for w in transfer),
            "decision_ns_per_action":decision_ns/actions,
            "total_transfer_actions":actions,
        }
    chosen=max(CONVENTIONAL,key=lambda k:report["arms"][k]["transfer_success"])
    ca=report["arms"]["active-probe"]; base=report["arms"][chosen]
    report["strongest_conventional"]=chosen
    report["candidate_success_gain"]=ca["transfer_success"]-base["transfer_success"]
    report["candidate_return_gain"]=ca["transfer_mean_return"]-base["transfer_mean_return"]
    report["paired_world_success_wins"]=sum(
        a["successes"]>b["successes"]
        for a,b in zip(ca["worlds"][:24],base["worlds"][:24]))
    report["best_retention"]=max(report["arms"][k]["retention_success"] for k in CONVENTIONAL)
    report["retention_margin"]=ca["retention_success"]-report["best_retention"]
    report["decision_cost_ratio"]=ca["decision_ns_per_action"]/base["decision_ns_per_action"]
    report["frozen_conditions_met"]=bool(
        report["candidate_success_gain"]>=0.10
        and report["candidate_return_gain"]>=0.75
        and report["paired_world_success_wins"]>=16
        and all(ca["transfer_success"]>=report["arms"][k]["transfer_success"]+0.10
                for k in NEGATIVES)
        and report["retention_margin"]>=-0.05
        and ca["transfer_sensor_worlds"]>=8
        and report["decision_cost_ratio"]<=2
        and all(all(ep["cold_matches"] and ep["actual_actions"]==DURATION
                    for w in arm["worlds"] for ep in w["episodes"])
                for arm in report["arms"].values()))
    report["classification"]=(
        "F47_DEV_SIGNAL_UNVERIFIED" if report["frozen_conditions_met"]
        else "F47_DEV_NO_GO")
    report["report_sha256"]=digest(report)
    return report


def main(args=None):
    args=sys.argv[1:] if args is None else args
    if len(args)!=1:
        raise ValueError("F47_USAGE: python source.py /tmp/synthetic-dev-report.json")
    out=Path(args[0]).resolve()
    fit_worlds, coverage=fit_data()
    model=fit_shared(fit_worlds)
    report=assess(model,digest(fit_worlds),coverage)
    report["report_sha256"]=digest({k:v for k,v in report.items() if k!="report_sha256"})
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(canonical(report)+b"\n")
    print("F47_SYNTHETIC_DELAYED_DEV="+report["classification"]
          +" sha256="+report["report_sha256"])
    print("F47_FIT_REAL_SYNTHETIC_TRANSITIONS="+str(report["training_transitions"])
          +" sha256="+report["training_sha256"])
    print("F47_STRONGEST="+report["strongest_conventional"]
          +" success_gain="+str(report["candidate_success_gain"])
          +" wins="+str(report["paired_world_success_wins"])
          +" return_gain="+str(report["candidate_return_gain"])
          +" paid_sensor_worlds="+str(report["arms"]["active-probe"]["transfer_sensor_worlds"])
          +" decision_ratio="+str(report["decision_cost_ratio"]))
    return report


if __name__=="__main__":
    main()
