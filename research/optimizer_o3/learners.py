"""O3: actually fitted compact predictive state versus learned public controls.

Single-state logistic belief and two-state tanh RNN use exact recurrent
sensitivity gradients, only NEXT PUBLIC OBSERVATION loss, no latent labels.
The counts/episodic controls fit exactly the same public histories.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from public_source import canonical

EPS = 1e-12
EPOCHS = 5
LR = 0.035
CLIP = 2.0
INITS = (17, 31)


def sigmoid(v):
    if v >= 0:
        z = math.exp(-min(60.0, v))
        return 1.0 / (1.0 + z)
    z = math.exp(max(-60.0, v))
    return z / (1.0 + z)


def nll(y, p):
    assert type(y) is int and y in (0, 1)
    p = min(1-EPS, max(EPS, p))
    return -math.log(p if y else 1-p)


class FittedRecurrent:
    """Per-episode RTRL: differentiate recurrence through entire public history."""

    def __init__(self, kind, seed):
        if kind not in ("ONE_BELIEF_SIGMOID_RTRL", "TWO_STATE_TANH_RTRL"):
            raise ValueError("O3_BAD_MODEL_KIND")
        self.kind = kind
        self.states = 1 if kind == "ONE_BELIEF_SIGMOID_RTRL" else 2
        rng = random.Random(seed)
        self.w = [[rng.uniform(-0.35, 0.35)
                   for _ in range(3+self.states)]
                  for _ in range(self.states)]
        self.v = [rng.uniform(-0.35, 0.35)
                  for _ in range(self.states+2)]
        self.updates = 0

    def _step(self, observation, action, previous):
        feats = [1.0, float(observation), float(action)] + previous
        pre = [sum(x*y for x, y in zip(weights, feats))
               for weights in self.w]
        hidden = ([sigmoid(x) for x in pre] if self.states == 1
                  else [math.tanh(x) for x in pre])
        out_feats = [1.0] + hidden + [float(action)]
        prediction = sigmoid(sum(x*y for x, y in zip(self.v, out_feats)))
        return hidden, prediction, feats, out_feats

    def predict_episode(self, public_episode):
        last = ([0.5] if self.states == 1 else [0.0] * self.states)
        predictions = []
        for observation, action, _ in public_episode:
            last, prob, _, _ = self._step(observation, action, last)
            predictions.append(prob)
        return predictions

    def train_episode(self, public_episode):
        n = self.states
        params = n*(3+n)
        last = ([0.5] if n == 1 else [0.0]*n)
        sensitivities = [[0.0]*params for _ in range(n)]
        grad_w = [0.0]*params
        grad_v = [0.0]*(n+2)
        for observation, action, target in public_episode:
            hidden, predicted, feats, output = self._step(
                observation, action, last)
            current = [[0.0]*params for _ in range(n)]
            for i in range(n):
                activation_gradient = (hidden[i]*(1-hidden[i]) if n == 1
                                       else 1-hidden[i]*hidden[i])
                for index in range(params):
                    direct = (feats[index % (3+n)]
                              if index // (3+n) == i else 0.0)
                    recurrence = sum(self.w[i][3+j] *
                                     sensitivities[j][index]
                                     for j in range(n))
                    current[i][index] = activation_gradient * (
                        direct + recurrence)
            delta = predicted - target
            for k in range(params):
                grad_w[k] += delta * sum(self.v[1+j]*current[j][k]
                                         for j in range(n))
            for k in range(n+2):
                grad_v[k] += delta * output[k]
            last, sensitivities = hidden, current
        scale = 1.0 / len(public_episode)
        grads = [x*scale for x in grad_w+grad_v]
        norm = math.sqrt(sum(g*g for g in grads))
        if norm > CLIP:
            grads = [g*CLIP/norm for g in grads]
        for k in range(params):
            self.w[k // (3+n)][k % (3+n)] -= LR*grads[k]
        for k in range(n+2):
            self.v[k] -= LR*grads[params+k]
        self.updates += 1

    def train(self, episodes):
        for _ in range(EPOCHS):
            for episode in episodes:
                self.train_episode(episode)

    def checkpoint(self):
        return canonical({"model": self.kind, "w": self.w, "v": self.v,
                          "updates": self.updates})


class PublicCountControl:
    def __init__(self, name):
        if name not in ("CURRENT_ONLY_COUNTS", "FOUR_LAG_BAYES_COUNTS",
                        "EXACT_CONTEXT_EPISODIC"):
            raise ValueError("O3_BAD_COUNT_CONTROL")
        self.name = name
        self.table = {}
        self.updates = 0

    def _features(self, obs, action, prev, prevprev):
        if self.name == "CURRENT_ONLY_COUNTS":
            return (obs, action)
        if self.name == "FOUR_LAG_BAYES_COUNTS":
            return (obs, action) + prev
        return (obs, action) + prev + prevprev

    def _walk(self, episode):
        prev = (-1, -1)
        prevprev = (-1, -1)
        for obs, action, target in episode:
            yield self._features(obs, action, prev, prevprev), target
            prevprev, prev = prev, (obs, action)

    def train(self, episodes):
        for episode in episodes:
            for key, y in self._walk(episode):
                pair = self.table.setdefault(key, [0, 0])
                pair[y] += 1
                self.updates += 1

    def predict_episode(self, episode):
        forecasts = []
        for key, _ in self._walk(episode):
            neg, pos = self.table.get(key, (0, 0))
            forecasts.append((pos+1)/(pos+neg+2))
        return forecasts

    def checkpoint(self):
        return canonical({"model": self.name, "counts": [
            {"key": list(k), "n": counts}
            for k, counts in sorted(self.table.items())],
            "updates": self.updates})


def score(model, episodes):
    losses = []
    for episode in episodes:
        pred = model.predict_episode(episode)
        assert len(pred) == len(episode)
        losses.extend(nll(y, p) for (*_, y), p in zip(episode, pred))
    return sum(losses)/len(losses)


def fit_models(train, selection):
    fitted = {}
    # Both recurrent models train with precisely equal public episodes,
    # update count, gradient-learning rates and seed restarts. Capacity differs
    # and is explicitly reported; they are not equal-parameter models.
    for kind in ("ONE_BELIEF_SIGMOID_RTRL", "TWO_STATE_TANH_RTRL"):
        candidates = []
        for init in INITS:
            model = FittedRecurrent(kind, init)
            model.train(train)
            candidates.append((score(model, selection), init, model))
        candidates.sort(key=lambda x: (x[0], x[1]))
        valid_nll, selected_seed, selected = candidates[0]
        fitted[kind] = (selected, {"public_select_nll": valid_nll,
                                  "selected_initialization": selected_seed,
                                  "parameter_count": selected.states*(
                                      3+selected.states)+selected.states+2,
                                  "all_public_select_nll": {
                                      str(seed): loss
                                      for loss, seed, _ in candidates}})
    for name in ("FOUR_LAG_BAYES_COUNTS", "EXACT_CONTEXT_EPISODIC",
                 "CURRENT_ONLY_COUNTS"):
        model = PublicCountControl(name)
        model.train(train)
        fitted[name] = (model, {"public_select_nll": score(model, selection),
                                "selected_initialization": None,
                                "parameter_count": None})
    return fitted


def model_receipt(model, select):
    data = model.checkpoint()
    return {"checkpoint_sha256": hashlib.sha256(data).hexdigest(),
            "serialized_model_bytes": len(data),
            "training_updates": model.updates,
            **select}
