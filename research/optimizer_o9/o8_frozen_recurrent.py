"""O8 actual learned recurrent memory, queried after distracting public experience.

GATED_2/GATED_4 learn a recurrent retention gate, candidate content and
query decoder jointly from public delayed-query outcomes using query-only
BPTT and Adam; VANILLA_4 uses the SAME public experience and optimizer.
The filter structure, number of cells and query supervision are designed,
not discovered. No hidden target, generator law or source family enters a
learning feature or model initializer.
"""
from __future__ import annotations
import math
import random

from public_source import canonical, query_info

KINDS = ("GATED_2", "GATED_4", "VANILLA_4")
SEEDS = (17, 31)
EPOCHS = 12
RATE = 0.01
CLIP = 2.0
BETA1 = 0.9
BETA2 = 0.999
EPSILON = 1e-8
INPUTS = 6


def sigmoid(z):
    if z >= 0.0:
        w = math.exp(-min(z, 60.0))
        return 1.0/(1.0+w)
    w = math.exp(max(z, -60.0))
    return w/(1.0+w)


def nll(bit, prob):
    if type(bit) is not int or bit not in (0, 1):
        raise ValueError("O8_QUERY_TARGET_BINARY")
    p = min(1.0-1e-12, max(1e-12, prob))
    return -math.log(p if bit else 1.0-p)


class PublicRecurrentMemory:
    def __init__(self, kind, seed):
        if kind not in KINDS or type(seed) is not int or seed not in SEEDS:
            raise ValueError("O8_UNFROZEN_RECURRENCE")
        self.kind = kind
        self.dim = 2 if kind == "GATED_2" else 4
        self.gated = kind != "VANILLA_4"
        self.feature_count = INPUTS + self.dim
        rng = random.Random(seed)
        self.gate = ([[rng.uniform(-0.27, 0.27)
                       for _ in range(self.feature_count)]
                      for _ in range(self.dim)] if self.gated else [])
        self.content = [[rng.uniform(-0.27, 0.27)
                         for _ in range(self.feature_count)]
                        for _ in range(self.dim)]
        self.out = [rng.uniform(-0.27, 0.27)
                    for _ in range(self.dim+1)]
        self.updates = 0
        self.m = [0.0]*self.parameter_count()
        self.s = [0.0]*self.parameter_count()

    def parameter_count(self):
        return (self.dim*self.feature_count*(2 if self.gated else 1)
                + self.dim+1)

    def _features(self, obs, action, time):
        return (1.0, float(obs), float(action == 0), float(action == 1),
                float(action == 2), float(time == 0))

    def _forward_prefix(self, episode, erased_query=False):
        details = query_info(episode)
        cutoff = details["query_t"]
        h = [0.0]*self.dim
        tape = []
        for t in range(cutoff+1):
            obs, action, _ = episode[t]
            if erased_query and t == cutoff:
                h = [0.0]*self.dim
            previous = list(h)
            features = list(self._features(obs, action, t)) + previous
            gate = ([sigmoid(sum(w*x for w,x in zip(row, features)))
                     for row in self.gate] if self.gated else [0.0]*self.dim)
            cand = [math.tanh(sum(w*x for w,x in zip(row, features)))
                    for row in self.content]
            h = ([gate[i]*previous[i]+(1-gate[i])*cand[i]
                  for i in range(self.dim)] if self.gated else cand)
            tape.append((features, previous, gate, cand, list(h)))
        prediction = sigmoid(self.out[0]+sum(self.out[i+1]*h[i]
                                            for i in range(self.dim)))
        return prediction, tape, details

    def predict(self, episode, erased_query=False):
        return self._forward_prefix(episode, erased_query=erased_query)[0]

    def _params(self):
        return ([v for row in self.gate for v in row] +
                [v for row in self.content for v in row] +
                list(self.out))

    def _set_params(self, new):
        offset = 0
        if self.gated:
            for i in range(self.dim):
                self.gate[i] = new[offset:offset+self.feature_count]
                offset += self.feature_count
        for i in range(self.dim):
            self.content[i] = new[offset:offset+self.feature_count]
            offset += self.feature_count
        self.out = new[offset:]
        if len(self.out) != self.dim+1:
            raise ValueError("O8_PARAMETER_SHAPE")

    def fit_episode(self, episode):
        prob, tape, query = self._forward_prefix(episode)
        delta = prob-query["target"]
        # Gradient of query log-loss through the whole observation history.
        grad_gate = [[0.0]*self.feature_count for _ in range(self.dim)]
        grad_content = [[0.0]*self.feature_count for _ in range(self.dim)]
        grad_out = [delta]+[delta*val for val in tape[-1][4]]
        propagated = [delta*self.out[i+1] for i in range(self.dim)]
        for features, previous, z, c, h in reversed(tape):
            dh_previous = [0.0]*self.dim
            for i in range(self.dim):
                if self.gated:
                    dz = (propagated[i]*(previous[i]-c[i])*
                          z[i]*(1.0-z[i]))
                    dn = propagated[i]*(1.0-z[i])*(1.0-c[i]*c[i])
                    dh_previous[i] += propagated[i]*z[i]
                    for k in range(self.feature_count):
                        grad_gate[i][k] += dz*features[k]
                    for j in range(self.dim):
                        dh_previous[j] += dz*self.gate[i][INPUTS+j]
                else:
                    dn = propagated[i]*(1.0-c[i]*c[i])
                for k in range(self.feature_count):
                    grad_content[i][k] += dn*features[k]
                for j in range(self.dim):
                    dh_previous[j] += dn*self.content[i][INPUTS+j]
            propagated = dh_previous
        gradient = ([v for row in grad_gate for v in row] if self.gated
                    else []) + [v for row in grad_content for v in row] + grad_out
        assert len(gradient) == self.parameter_count()
        if not all(math.isfinite(v) for v in gradient):
            raise ValueError("O8_NONFINITE_GRADIENT")
        norm = math.sqrt(sum(v*v for v in gradient))
        if norm > CLIP:
            gradient = [v*CLIP/norm for v in gradient]
        self.updates += 1
        params = self._params()
        for k, g in enumerate(gradient):
            self.m[k] = BETA1*self.m[k] + (1.0-BETA1)*g
            self.s[k] = BETA2*self.s[k] + (1.0-BETA2)*g*g
            mh = self.m[k]/(1.0-BETA1**self.updates)
            sh = self.s[k]/(1.0-BETA2**self.updates)
            params[k] -= RATE*mh/(math.sqrt(sh)+EPSILON)
        self._set_params(params)

    def fit(self, episodes):
        for _ in range(EPOCHS):
            for ep in episodes:
                self.fit_episode(ep)

    def checkpoint(self):
        return canonical({
            "model": self.kind, "dim": self.dim, "gated": self.gated,
            "feature_count": self.feature_count, "gate_weights": self.gate,
            "content_weights": self.content, "output_weights": self.out,
            "optimizer_first_moment": self.m, "optimizer_second_moment": self.s,
            "updates": self.updates, "parameter_count": self.parameter_count(),
        })
