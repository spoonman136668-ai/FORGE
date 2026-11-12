#!/usr/bin/env python3
"""ITD-02 W1L: closed-loop source-owned numerical worlds, DEV only.

Source-free simulated action consequences. No Gymnasium/original first-use,
cloud provider, controller, scheduler, live owner or cross-project execution.
Frozen design: docs/EUREKA-ITD02-W1L-CLOSED-LOOP-DEV.md at 7057eef8e47f984ab20bd65a01214c0b906bdd51.
"""
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time
from collections import deque

from itd02_online_consequence_memory import OnlineConsequenceMemory
from itd02_two_bank_reversal_dev import TwoBankMemory

SCHEMA = "forge.eureka.itd02.w1l.closed-loop-source-dev.v1"
PROTOCOL_COMMIT = "7057eef8e47f984ab20bd65a01214c0b906bdd51"
FAMILIES = ("switch", "third", "lagged")
SEEDS = (73011, 73017, 73021, 73029)
ARMS = ("two-bank", "switch-bayes", "rolling8", "rolling16",
        "lagged-credit", "no-feedback", "random")
CONVENTIONAL = ("switch-bayes", "rolling8", "rolling16", "lagged-credit")
FIT_STEPS = 64
SCORED_STEPS = 128
RIDGE = .1
HAZARD = .02
SIGMA = .25
EXPLORATION = .5
AB_EFFECTS = ((1., -1.), (-1., 1.))
C_EFFECTS = (-.25, .5)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def sha(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def clip(v):
    return max(-1., min(1., v))


class NumericWorld:
    """A small independent numerical consequence source, not a real environment."""
    def __init__(self, family, seed, *, fit):
        if family not in FAMILIES or type(seed) is not int or seed < 1 or type(fit) is not bool:
            raise ValueError("W1L_SOURCE_WORLD_INVALID")
        self.family = family
        self.seed = seed
        self.fit = fit
        self.horizon = FIT_STEPS if fit else SCORED_STEPS
        tag = FAMILIES.index(family)
        self.rng = random.Random(seed * 127 + tag * 104729 + (101 if fit else 313))
        self.position = self.rng.uniform(-.1, .1)
        self.velocity = self.rng.uniform(-.1, .1)
        self.previous_action = 0
        self.t = 0

    def public(self):
        return [self.position, self.velocity]

    def _effects(self):
        if self.fit:
            index = 0 if self.t < 32 else 1
        else:
            phase = self.t // 32
            if self.family == "third":
                index = (0, 1, 2, 0)[phase]
            else:
                index = (0, 1, 0, 1)[phase]
        return (AB_EFFECTS[0], AB_EFFECTS[1], C_EFFECTS)[index]

    def step(self, action):
        if type(action) is not int or action not in (0, 1) or self.t >= self.horizon:
            raise ValueError("W1L_WORLD_ACTION_OR_BUDGET_INVALID")
        before = self.public()
        effects = self._effects()
        credited = self.previous_action if self.family == "lagged" else action
        noise = self.rng.uniform(-.05, .05)
        reward = effects[credited] + .1 * self.position + noise
        vnew = clip(.65 * self.velocity + .35 * (1. if action == 0 else -1.))
        pnew = clip(.8 * self.position + .2 * vnew)
        self.velocity, self.position = vnew, pnew
        self.previous_action = action
        self.t += 1
        if not math.isfinite(reward) or not -2. <= reward <= 2.:
            raise ValueError("W1L_NONFINITE_SOURCE_CONSEQUENCE")
        return before, float(reward), self.public(), self.t == self.horizon


class TwoBankPolicy:
    def __init__(self):
        self.model = TwoBankMemory(public_dim=2, actions=2, max_events=256)

    def choose(self, obs):
        result = self.model.propose(obs, EXPLORATION)
        if result["can_dispatch_original"] or result["scientific_accepted"]:
            raise ValueError("W1L_FORBIDDEN_SCIENTIFIC_AUTHORITY")
        return result["action"]

    def observe(self, obs, action, consequence):
        self.model.observe(self.model.completed, obs, action, consequence)

    def cold(self):
        payload, digest = self.model.checkpoint()
        self.model = TwoBankMemory.restore(
            payload, digest, minimum_completed=self.model.completed)

    def state(self):
        return self.model.checkpoint()[1]


class RecentRidge:
    """Conventional fully fitted action-specific ridge on actual recent rows."""
    def __init__(self, window, lagged=False):
        self.window = window
        self.lagged = lagged
        self.rows = [deque(maxlen=window) for _ in (0, 1)]
        self.previous = None

    def _fitted(self):
        m = OnlineConsequenceMemory(public_dim=2, actions=2, max_events=256)
        for action in (0, 1):
            for obs, outcome in self.rows[action]:
                m.observe(m.completed, obs, action, outcome)
        return m

    def choose(self, obs):
        m = self._fitted()
        scores = [m.predict(obs, a) + EXPLORATION * m.uncertainty(obs, a)
                  for a in (0, 1)]
        return max((0, 1), key=lambda a: (scores[a], -a))

    def observe(self, obs, action, consequence):
        if self.lagged:
            if self.previous is not None:
                prior_obs, prior_action = self.previous
                self.rows[prior_action].append((prior_obs, consequence))
            self.previous = (list(obs), action)
        else:
            self.rows[action].append((list(obs), consequence))

    def episode_reset(self):
        if self.lagged:
            self.previous = None

    def state(self):
        return sha({"rows": [list(x) for x in self.rows],
                    "lagged": self.lagged, "previous": self.previous})


class SwitchingBayes:
    """Independent conventional two-state hazard/likelihood filter.

    No hidden mode or reward oracle. Both fitted models use actual observed
    source action consequences; trainable capacity equals two action models.
    """
    def __init__(self):
        self.banks = [OnlineConsequenceMemory(2, 2, max_events=256)
                      for _ in (0, 1)]
        self.posterior = [1., 0.]

    def choose(self, obs):
        scores = []
        for a in (0, 1):
            score = 0.
            for i, bank in enumerate(self.banks):
                score += self.posterior[i] * (
                    bank.predict(obs, a) +
                    EXPLORATION * bank.uncertainty(obs, a))
            scores.append(score)
        return max((0, 1), key=lambda a: (scores[a], -a))

    def observe(self, obs, action, consequence):
        left, right = self.banks
        if right.completed == 0:
            if (left.counts[action] >= 3 and
                abs(consequence - left.predict(obs, action)) >= .9):
                right.observe(right.completed, obs, action, consequence)
                self.posterior = [HAZARD, 1. - HAZARD]
            else:
                left.observe(left.completed, obs, action, consequence)
            return
        prior = [self.posterior[0] * (1 - HAZARD) + self.posterior[1] * HAZARD,
                 self.posterior[1] * (1 - HAZARD) + self.posterior[0] * HAZARD]
        scores = []
        for i, bank in enumerate(self.banks):
            err = consequence - bank.predict(obs, action)
            # Untrained action rows have broad likelihood, never an oracle.
            if bank.counts[action] == 0:
                likelihood = .25
            else:
                likelihood = math.exp(-.5 * (err / SIGMA) ** 2)
            scores.append(prior[i] * likelihood)
        total = sum(scores)
        self.posterior = ([x / total for x in scores]
                          if total > 1e-200 else prior)
        chosen = max((0, 1), key=lambda i: (self.posterior[i], -i))
        self.banks[chosen].observe(
            self.banks[chosen].completed, obs, action, consequence)

    def state(self):
        return sha({"posterior": self.posterior,
                    "banks": [m.checkpoint()[1] for m in self.banks]})


class ActionZero:
    def choose(self, _obs):
        return 0
    def observe(self, _obs, _action, _consequence):
        return None
    def state(self):
        return sha({"model": "no-feedback"})


class RandomAction:
    def __init__(self, seed):
        self.rng = random.Random(seed)
    def choose(self, _obs):
        return self.rng.randrange(2)
    def observe(self, _obs, _action, _consequence):
        return None
    def state(self):
        return sha({"model": "random", "state": self.rng.getstate()})


def new_policy(name, seed):
    if name == "two-bank":
        return TwoBankPolicy()
    if name == "switch-bayes":
        return SwitchingBayes()
    if name in ("rolling8", "rolling16"):
        return RecentRidge(8 if name == "rolling8" else 16)
    if name == "lagged-credit":
        return RecentRidge(16, lagged=True)
    if name == "no-feedback":
        return ActionZero()
    if name == "random":
        return RandomAction(seed * 1997 + 29)
    raise ValueError("W1L_UNDECLARED_CONTROL")


def collect_fit(family, seed):
    world = NumericWorld(family, seed, fit=True)
    rows = []
    for t in range(FIT_STEPS):
        action = t % 2
        old, reward, new, terminal = world.step(action)
        rows.append((old, action, reward, new, terminal))
    if len(rows) != FIT_STEPS or not rows[-1][-1]:
        raise ValueError("W1L_FIT_SOURCE_INCOMPLETE")
    return rows


def rollout(family, seed, name, fit_rows, *, cold):
    agent = new_policy(name, seed)
    start_cpu = time.process_time()
    start_wall = time.perf_counter()
    for observation, action, outcome, _new, _terminal in fit_rows:
        agent.observe(observation, action, outcome)
    if hasattr(agent, "episode_reset"):
        agent.episode_reset()
    world = NumericWorld(family, seed, fit=False)
    trace = []
    positive = 0
    reward_total = 0.
    action_counts = [0, 0]
    snapshot_count = 0
    for t in range(SCORED_STEPS):
        obs = world.public()
        action = agent.choose(obs)
        old, outcome, new, terminal = world.step(action)
        agent.observe(old, action, outcome)
        positive += int(outcome > 0.)
        reward_total += outcome
        action_counts[action] += 1
        trace.append((old, action, outcome, new, terminal))
        if name == "two-bank" and cold and t == 63:
            agent.cold()
            snapshot_count += 1
    if len(trace) != SCORED_STEPS or not trace[-1][-1]:
        raise ValueError("W1L_CLOSED_LOOP_TERMINAL_MISSING")
    recovery = []
    for origin in (32, 64, 96):
        local = next((i for i in range(32)
                      if trace[origin+i][2] > 0.), 32)
        recovery.append(local)
    return {"return": reward_total, "positive_steps": positive,
            "trace_sha256": sha(trace), "state_sha256": agent.state(),
            "action_counts": action_counts,
            "source_owned_actions": SCORED_STEPS,
            "recovery_steps": recovery, "cold_restores": snapshot_count,
            "fit_rows_consumed": FIT_STEPS,
            "wall_seconds": time.perf_counter() - start_wall,
            "cpu_seconds": time.process_time() - start_cpu}


def score():
    """One frozen evaluation. Call only after focused source preflight PASS."""
    episodes = []
    total_warm = 0
    total_cold = 0
    for family in FAMILIES:
        for seed in SEEDS:
            fit_rows = collect_fit(family, seed)
            fit_digest = sha(fit_rows)
            scores = {}
            for arm in ARMS:
                warm = rollout(family, seed, arm, fit_rows, cold=False)
                cold = rollout(family, seed, arm, fit_rows, cold=True)
                total_warm += warm["source_owned_actions"]
                total_cold += cold["source_owned_actions"]
                for key in ("return", "positive_steps", "trace_sha256",
                            "state_sha256", "action_counts", "recovery_steps",
                            "fit_rows_consumed"):
                    if warm[key] != cold[key]:
                        raise ValueError("W1L_COLD_EPISODE_OR_MODEL_DIVERGENCE")
                if arm == "two-bank" and cold["cold_restores"] != 1:
                    raise ValueError("W1L_MISSING_REAL_COLD_CONTINUATION")
                scores[arm] = warm
            episodes.append({"family": family, "seed": seed,
                             "fit_sha256": fit_digest, "arms": scores})
    if total_warm != 10752 or total_cold != 10752 or len(episodes) != 12:
        raise ValueError("W1L_MISSING_PHYSICAL_SOURCE_STEPS")
    sums = {name: sum(ep["arms"][name]["return"] for ep in episodes)
            for name in ARMS}
    strongest = max(CONVENTIONAL, key=lambda name: (sums[name], -CONVENTIONAL.index(name)))
    gain = sums["two-bank"] - sums[strongest]
    wins = sum(ep["arms"]["two-bank"]["return"] >
               ep["arms"][strongest]["return"] for ep in episodes)
    family_means = {
        family: {name: (sum(ep["arms"][name]["return"] for ep in episodes
                          if ep["family"] == family) / len(SEEDS))
                 for name in ARMS}
        for family in FAMILIES
    }
    nondegraded = all(family_means[f]["two-bank"] >=
                      family_means[f][strongest] for f in FAMILIES)
    threshold = max(1., .05 * abs(sums[strongest]))
    passed = gain >= threshold and wins >= 9 and nondegraded
    result = {
        "schema": SCHEMA, "protocol_commit": PROTOCOL_COMMIT,
        "status": ("ITD02_W1L_DEV_SIGNAL_UNVERIFIED" if passed
                   else "ITD02_W1L_DEV_NO_GO"),
        "source": "deterministic-source-owned-synthetic-closed-loop",
        "families": FAMILIES, "seeds": SEEDS, "arms": ARMS,
        "strongest_conventional": strongest,
        "strongest_conventional_total_return": sums[strongest],
        "total_returns": sums, "paired_world_wins": wins,
        "candidate_total_return_gain": gain,
        "candidate_minimum_gain": threshold,
        "per_family_mean_returns": family_means,
        "per_family_nondegraded": nondegraded,
        "warm_scored_world_steps": total_warm,
        "cold_replay_world_steps": total_cold,
        "original_first_use_authorized": False,
        "scientific_accepted": False,
        "original_physical_world_run": False,
        "F57_new_seed_use": 0,
        "episodes": episodes,
    }
    result["report_sha256"] = sha(result)
    return result


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise ValueError("W1L_EXPECTS_EXACT_REPORT_PATH")
    report = score()
    path = Path(args[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(report) + b"\n")
    print("W1L_RESULT=" + report["status"])
    print("W1L_SUMMARY=" + json.dumps({
        "strongest_conventional": report["strongest_conventional"],
        "returns": report["total_returns"],
        "paired_wins": report["paired_world_wins"],
        "gain": report["candidate_total_return_gain"],
        "threshold": report["candidate_minimum_gain"],
        "family_means": report["per_family_mean_returns"],
        "warm_steps": report["warm_scored_world_steps"],
        "cold_steps": report["cold_replay_world_steps"],
        "report_sha256": report["report_sha256"]}, sort_keys=True))
    return report


if __name__ == "__main__":
    main()
