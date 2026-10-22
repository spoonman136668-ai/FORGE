"""ITD-01 R2: THREE ACTUALLY TRAINED developer-only baseline classes.

IMPORTANT: synthetic public DEV/mock task qualification ONLY. Training
labels are completed PUBLIC terminal rewards, never hidden causal roles.
An evaluator must pass public observation dictionaries, not world objects.
No original MiniGrid/Pycolab, H1/H2, protected first use or authority.
The agents have different learning objectives but identical public TRAIN tasks.
"""
from __future__ import annotations

import itertools
import json
import math
import random

from public_dev import action, canonical

PAIRS = tuple(itertools.combinations(range(4), 2))
TRAIN_SCHEMAS = "itd01.baselines.public-dev.v1"


def sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-min(x, 70.0)))
    z = math.exp(max(x, -70.0))
    return z / (1.0 + z)


def obtain_public_probes(reset_observation: dict, step) -> tuple[list[tuple[int, float]], list[str]]:
    """Agent gets only a PUBLIC reset dictionary and PUBLIC step callback."""
    names = sorted(e["id"] for e in reset_observation["entities"])
    if len(names) != 4 or len(set(names)) != 4:
        raise ValueError("ITD01_DEV_ENTITIES_INVALID")
    out = []
    for idx, name in enumerate(names):
        for _ in range(4):
            result = step(action("inspect", name))
            signal = result["observation"]["observations"]
            if result["done"] or len(signal) != 1 or signal[0].get("entity") != name:
                raise ValueError("ITD01_PUBLIC_INSPECTION_INVALID")
            val = signal[0].get("signal")
            if val not in ("responsive", "idle"):
                raise ValueError("ITD01_PUBLIC_PROBE_SIGNAL_INVALID")
            out.append((idx, 1.0 if val == "responsive" else 0.0))
    return out, names


def execute_public_candidate(reset_obs: dict, step, names: list[str],
                             pair_index: int) -> int:
    """Terminal reward is the *only* public chosen-action training target."""
    if not (0 <= pair_index < len(PAIRS)):
        raise ValueError("ITD01_BAD_PUBLIC_PAIR")
    on_value = reset_obs["entities"][0]["legal_values"][0]
    if on_value not in ("activate", "fill"):
        raise ValueError("ITD01_BAD_DEV_PUBLIC_ACTION")
    for idx in PAIRS[pair_index]:
        result = step(action("intervene", names[idx], on_value))
        if result["done"]:
            raise ValueError("ITD01_EARLY_TERMINATION")
    for _ in range(3):
        result = step(action("wait"))
        if result["done"]:
            raise ValueError("ITD01_EARLY_WAIT_TERMINATION")
    result = step(action("commit"))
    if not result["done"] or result["reward"] not in (0, 1):
        raise ValueError("ITD01_PUBLIC_TERMINAL_REWARD_INVALID")
    return int(result["reward"])


def features(probes: list[tuple[int, float]]) -> tuple[float, ...]:
    counts = [0.0] * 4
    for idx, val in probes:
        counts[idx] += val
    return tuple(v / 4 for v in counts)


class RecurrentRewardAgent:
    """8-state Elman recurrent model; actual truncated-free BPTT over public probes.

    Trains via Bernoulli terminal reward for randomly selected candidate pair;
    no private target IDs, no oracle data, no world-model privilege.
    """
    def __init__(self, seed: int = 17, width: int = 8):
        self.width = width
        rng = random.Random(seed)
        self.wx = [[rng.uniform(-.2, .2) for _ in range(5)] for _ in range(width)]
        self.wh = [[rng.uniform(-.12, .12) for _ in range(width)] for _ in range(width)]
        self.b = [0.0] * width
        self.wo = [[rng.uniform(-.20, .20) for _ in range(width)] for _ in PAIRS]
        self.bo = [0.0] * len(PAIRS)
        self.updates = 0

    def _state(self, probes: list[tuple[int, float]]):
        states = [[0.0] * self.width]
        vectors = []
        for idx, val in probes:
            inp = [float(i == idx) for i in range(4)] + [2.0 * val - 1.0]
            previous = states[-1]
            h = [math.tanh(self.b[j] + sum(w * x for w, x in zip(self.wx[j], inp))
                           + sum(w * x for w, x in zip(self.wh[j], previous)))
                 for j in range(self.width)]
            vectors.append(inp)
            states.append(h)
        return states, vectors

    def predict_all(self, probes: list[tuple[int, float]]) -> list[float]:
        h = self._state(probes)[0][-1]
        return [sigmoid(self.bo[k] + sum(w * x for w, x in zip(row, h)))
                for k, row in enumerate(self.wo)]

    def train(self, episodes: list[dict], epochs: int = 3, rate: float = .055) -> None:
        for _ in range(epochs):
            for episode in episodes:
                probes, pair, target = episode["probes"], episode["pair"], episode["reward"]
                states, vectors = self._state(probes)
                h = states[-1]
                p = sigmoid(self.bo[pair] + sum(w * x for w, x in zip(self.wo[pair], h)))
                # BCE: d(logit loss)/dlogit = p - terminal_reward
                delta = p - target
                upstream = [delta * w for w in self.wo[pair]]
                old_wh = [row[:] for row in self.wh]
                for j in range(self.width):
                    self.wo[pair][j] -= rate * delta * h[j]
                self.bo[pair] -= rate * delta
                for t in range(len(vectors) - 1, -1, -1):
                    cur, prev, inp = states[t + 1], states[t], vectors[t]
                    local = [max(-1.0, min(1.0, upstream[j] * (1.0 - cur[j] ** 2)))
                             for j in range(self.width)]
                    upstream = [sum(local[j] * old_wh[j][i] for j in range(self.width))
                                for i in range(self.width)]
                    for j in range(self.width):
                        self.b[j] -= rate * local[j]
                        for d in range(5):
                            self.wx[j][d] -= rate * local[j] * inp[d]
                        for d in range(self.width):
                            self.wh[j][d] -= rate * local[j] * prev[d]
                self.updates += 1

    def choose(self, probes: list[tuple[int, float]]) -> int:
        return max(range(len(PAIRS)), key=lambda k: (self.predict_all(probes)[k], -k))

    def serialize(self) -> dict:
        return {"class": "trained_recurrent_reward", "wx": self.wx, "wh": self.wh,
                "b": self.b, "wo": self.wo, "bo": self.bo, "updates": self.updates}


class PredictiveWorldModelAgent:
    """Public self-supervised next-observation model plus a bounded public planner.

    The next noisy public diagnostic from an entity is the only teaching signal.
    Logistic forward parameters learn to predict another inspection from the
    preceding PUBLIC diagnostic history; planner then selects a pair.
    """
    def __init__(self):
        self.weights = [0.04, 0.0, 0.0]
        self.updates = 0

    @staticmethod
    def _x(positive: float, total: int) -> list[float]:
        return [1.0, positive - (total - positive), math.log1p(total)]

    def _p(self, pos: float, total: int) -> float:
        return sigmoid(sum(w * x for w, x in zip(self.weights, self._x(pos, total))))

    def train(self, episodes: list[dict], epochs: int = 5, rate: float = .025) -> None:
        for _ in range(epochs):
            for episode in episodes:
                pos = [0.0] * 4
                seen = [0] * 4
                for idx, val in episode["probes"]:
                    if seen[idx]:
                        xs = self._x(pos[idx], seen[idx])
                        error = self._p(pos[idx], seen[idx]) - val
                        for j in range(3):
                            self.weights[j] -= rate * error * xs[j]
                        self.updates += 1
                    pos[idx] += val
                    seen[idx] += 1

    def predict_all(self, probes: list[tuple[int, float]]) -> list[float]:
        pos = [0.0] * 4
        seen = [0] * 4
        for idx, val in probes:
            pos[idx] += val
            seen[idx] += 1
        probs = [self._p(pos[i], seen[i]) for i in range(4)]
        return [math.prod(probs[i] if i in pair else (1.0 - probs[i])
                          for i in range(4)) for pair in PAIRS]

    def choose(self, probes: list[tuple[int, float]]) -> int:
        scores = self.predict_all(probes)
        return max(range(len(PAIRS)), key=lambda k: (scores[k], -k))

    def serialize(self) -> dict:
        return {"class": "trained_public_world_model", "weights": self.weights,
                "updates": self.updates}


class ExplicitEpisodicAgent:
    """Trained public terminal-reward memory; no hidden task labels.

    Case retrieval matches public diagnostic histories and the previously
    actioned pair, then reuses the observed public terminal feedback.
    """
    def __init__(self, max_cases: int = 2000):
        self.max_cases = max_cases
        self.cases: list[dict] = []
        self.updates = 0

    def train(self, episodes: list[dict]) -> None:
        for ep in episodes:
            self.cases.append({"features": list(features(ep["probes"])),
                               "pair": ep["pair"], "reward": ep["reward"]})
            self.updates += 1
        self.cases = self.cases[-self.max_cases:]

    def predict_all(self, probes: list[tuple[int, float]]) -> list[float]:
        obs = features(probes)
        result = []
        for pair in range(len(PAIRS)):
            cases = (c for c in self.cases if c["pair"] == pair)
            ranking = sorted(((sum(abs(x - y) for x, y in zip(obs, c["features"])), c["reward"])
                              for c in cases), key=lambda z: z[0])
            selected = ranking[:24]
            top = [math.exp(-3 * d) for d, _ in selected]
            # Laplace public-feedback smoothing only, no oracle.
            result.append((1.0 + sum(w * reward for w, (_, reward) in zip(top, selected)))
                          / (2.0 + sum(top)))
        return result

    def choose(self, probes: list[tuple[int, float]]) -> int:
        scores = self.predict_all(probes)
        return max(range(len(PAIRS)), key=lambda k: (scores[k], -k))

    def serialize(self) -> dict:
        return {"class": "trained_explicit_public_memory",
                "cases": self.cases, "updates": self.updates}


def model_state_bytes(agent) -> int:
    return len(canonical(agent.serialize()))


def model_identity(agent) -> str:
    import hashlib
    return hashlib.sha256(canonical(agent.serialize())).hexdigest()
