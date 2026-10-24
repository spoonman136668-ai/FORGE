"""O4 fitted recurrent, latent HMM and count controls: public data only.

No generator import, hidden-label fit, science authority or sealed role support.
Every learner receives exactly the same public observation/action trajectories.
"""
from __future__ import annotations
import hashlib
import math
import random
from public_source import canonical

INIT_SEEDS = (17, 31)
ARMS = ("RNN_TANH_SGD_5E", "RNN_TANH_SGD_16E", "RNN_TANH_ADAM_16E",
        "HMM_2STATE_ACTION_EM", "PUBLIC_LAG_COUNTS", "PUBLIC_CURRENT_COUNTS")
EPS = 1e-10


def sigmoid(x):
    if x >= 0:
        return 1.0 / (1.0+math.exp(-min(x, 60.0)))
    return math.exp(max(x, -60.0))/(1.0+math.exp(max(x, -60.0)))


def loss(y, p):
    if type(y) is not int or y not in (0, 1):
        raise ValueError("O4_NOT_PUBLIC_BINARY_TARGET")
    p = max(EPS, min(1-EPS, p))
    return -math.log(p if y else 1-p)


def score(model, episodes):
    total = 0.0
    n = 0
    for ep in episodes:
        forecasts = model.predict(ep)
        if len(forecasts) != len(ep):
            raise ValueError("O4_INVALID_PREDICTION_LENGTH")
        for row, p in zip(ep, forecasts):
            if not math.isfinite(p) or p < 0 or p > 1:
                raise ValueError("O4_NONFINITE_PREDICTION")
            total += loss(row[2], p)
            n += 1
    return total/n


class PublicHistoryCounts:
    def __init__(self, lagged):
        self.lagged = bool(lagged)
        self.table = {}
        self.updates = 0

    def _keys(self, ep):
        previous_action = 0
        for obs, action, _ in ep:
            key = ((obs, action, previous_action) if self.lagged
                   else (obs, action))
            yield key
            previous_action = action

    def fit(self, episodes):
        for ep in episodes:
            for key, row in zip(self._keys(ep), ep):
                v = self.table.setdefault(key, [0, 0])
                v[row[2]] += 1
                self.updates += 1

    def predict(self, ep):
        predictions = []
        for key in self._keys(ep):
            neg, pos = self.table.get(key, (0, 0))
            predictions.append((pos+1)/(pos+neg+2))
        return predictions

    def checkpoint(self):
        return canonical({"name": "PUBLIC_LAG_COUNTS" if self.lagged
                          else "PUBLIC_CURRENT_COUNTS",
                          "table": [[list(k), v]
                                    for k, v in sorted(self.table.items())],
                          "updates": self.updates})


class PublicRecurrent:
    """Identical two-state tanh architecture; fixed optimizer/epochs by arm."""

    def __init__(self, arm, seed):
        if arm not in ARMS[:3]:
            raise ValueError("O4_BAD_RNN_ARM")
        self.arm = arm
        self.epochs = 5 if arm == ARMS[0] else 16
        self.adam = arm == ARMS[2]
        self.rate = 0.012 if self.adam else 0.035
        self.updates = 0
        rng = random.Random(seed)
        self.w = [[rng.uniform(-0.35, 0.35) for _ in range(6)]
                  for _ in range(2)]
        self.v = [rng.uniform(-0.35, 0.35) for _ in range(4)]
        self.m = [0.0]*16
        self.v2 = [0.0]*16

    def _step(self, observation, action, previous_action, previous_hidden):
        features = [1.0, float(observation), float(action),
                    float(previous_action)] + previous_hidden
        hidden = [math.tanh(sum(a*b for a, b in zip(w, features)))
                  for w in self.w]
        out = [1.0, hidden[0], hidden[1], float(action)]
        p = sigmoid(sum(a*b for a, b in zip(self.v, out)))
        return features, hidden, out, p

    def predict(self, ep):
        h = [0.0, 0.0]
        prev_action = 0
        result = []
        for obs, act, _ in ep:
            _, h, _, p = self._step(obs, act, prev_action, h)
            result.append(p)
            prev_action = act
        return result

    def fit_episode(self, ep):
        h = [0.0, 0.0]
        prev_action = 0
        tape = []
        for obs, act, target in ep:
            features, h, out, p = self._step(obs, act, prev_action, h)
            tape.append((features, h, out, p, target))
            prev_action = act
        gw = [[0.0]*6 for _ in range(2)]
        gv = [0.0]*4
        dh_future = [0.0, 0.0]
        for features, hidden, out, pred, target in reversed(tape):
            delta = (pred-target)/len(tape)
            for j in range(4):
                gv[j] += delta*out[j]
            dz = [(delta*self.v[1+i]+dh_future[i])*
                  (1-hidden[i]*hidden[i]) for i in range(2)]
            for i in range(2):
                for j in range(6):
                    gw[i][j] += dz[i]*features[j]
            dh_future = [sum(dz[i]*self.w[i][4+j] for i in range(2))
                         for j in range(2)]
        gradient = gw[0]+gw[1]+gv
        norm = math.sqrt(sum(g*g for g in gradient))
        if norm > 2.0:
            gradient = [g*2.0/norm for g in gradient]
        self.updates += 1
        weights = self.w[0]+self.w[1]+self.v
        for j, g in enumerate(gradient):
            if self.adam:
                self.m[j] = 0.9*self.m[j] + 0.1*g
                self.v2[j] = 0.999*self.v2[j] + 0.001*g*g
                mhat = self.m[j]/(1-0.9**self.updates)
                vhat = self.v2[j]/(1-0.999**self.updates)
                weights[j] -= self.rate*mhat/(math.sqrt(vhat)+1e-8)
            else:
                weights[j] -= self.rate*g
        self.w = [weights[:6], weights[6:12]]
        self.v = weights[12:]

    def fit(self, episodes):
        for _ in range(self.epochs):
            for ep in episodes:
                self.fit_episode(ep)

    def checkpoint(self):
        return canonical({"name": self.arm, "w": self.w, "v": self.v,
                          "epochs": self.epochs, "updates": self.updates})


class PublicActionHMM:
    """Unsupervised two-state EM with transition conditioned on two public actions.

    Latent labels are never emitted by public_source or seen by the model.
    The two-state symmetric-flip parameterization makes EM identifiable up
    to latent label swap and prevents privileged feature injection.
    """

    def __init__(self, seed):
        rnd = random.Random(seed)
        self.emission = [0.20+rnd.uniform(-0.08, 0.08),
                         0.80+rnd.uniform(-0.08, 0.08)]
        self.flip = [0.12+rnd.uniform(-0.06, 0.06),
                     0.32+rnd.uniform(-0.06, 0.06),
                     0.32+rnd.uniform(-0.06, 0.06),
                     0.65+rnd.uniform(-0.06, 0.06)]
        self.updates = 0

    def _emit(self, state, obs):
        v = self.emission[state]
        return v if obs else 1-v

    @staticmethod
    def _split(ep):
        observations = [ep[0][0]] + [r[2] for r in ep]
        actions = [r[1] for r in ep]
        return observations, actions

    def _forward(self, obs, actions):
        prev_action = 0
        initial = [0.5*self._emit(s, obs[0]) for s in range(2)]
        scale = sum(initial)
        alpha = [[v/scale for v in initial]]
        scales = [scale]
        contexts = []
        for t, action in enumerate(actions):
            context = 2*prev_action + action
            contexts.append(context)
            f = self.flip[context]
            prior0 = alpha[-1][0]*(1-f)+alpha[-1][1]*f
            prior1 = alpha[-1][1]*(1-f)+alpha[-1][0]*f
            unnormalized = [prior0*self._emit(0, obs[t+1]),
                            prior1*self._emit(1, obs[t+1])]
            scale = sum(unnormalized)
            scales.append(scale)
            alpha.append([v/scale for v in unnormalized])
            prev_action = action
        return alpha, scales, contexts

    def predict(self, ep):
        obs, acts = self._split(ep)
        belief0 = 0.5*self._emit(0, obs[0])
        belief1 = 0.5*self._emit(1, obs[0])
        z = belief0+belief1
        belief = [belief0/z, belief1/z]
        prev_action = 0
        preds = []
        for t, action in enumerate(acts):
            f = self.flip[2*prev_action+action]
            prior = [belief[0]*(1-f)+belief[1]*f,
                     belief[1]*(1-f)+belief[0]*f]
            prediction = prior[0]*self.emission[0] + prior[1]*self.emission[1]
            preds.append(prediction)
            post = [prior[s]*self._emit(s, obs[t+1]) for s in range(2)]
            total = post[0]+post[1]
            belief = [v/total for v in post]
            prev_action = action
        return preds

    def fit(self, episodes, iterations=12):
        for _ in range(iterations):
            flip_numer = [0.5]*4
            flip_denom = [1.0]*4
            emit_numer = [0.5, 0.5]
            emit_denom = [1.0, 1.0]
            for episode in episodes:
                obs, actions = self._split(episode)
                alpha, scales, contexts = self._forward(obs, actions)
                T = len(actions)
                beta = [[1.0, 1.0] for _ in range(T+1)]
                for t in range(T-1, -1, -1):
                    f = self.flip[contexts[t]]
                    for s in (0, 1):
                        beta[t][s] = sum(
                            (1-f if s==q else f)*
                            self._emit(q, obs[t+1])*beta[t+1][q]
                            for q in (0, 1))/scales[t+1]
                for t in range(T+1):
                    post = [alpha[t][s]*beta[t][s] for s in (0, 1)]
                    total = sum(post)
                    for s in (0, 1):
                        g = post[s]/total
                        emit_numer[s] += g*obs[t]
                        emit_denom[s] += g
                for t in range(T):
                    f = self.flip[contexts[t]]
                    xi = [[alpha[t][s]*(1-f if s==q else f)*
                           self._emit(q, obs[t+1])*beta[t+1][q]
                           for q in (0, 1)] for s in (0, 1)]
                    total = sum(sum(v) for v in xi)
                    flip_numer[contexts[t]] += (xi[0][1]+xi[1][0])/total
                    flip_denom[contexts[t]] += 1.0
            self.emission = [emit_numer[s]/emit_denom[s] for s in range(2)]
            self.flip = [flip_numer[k]/flip_denom[k] for k in range(4)]
            if not all(0.0 < v < 1.0 and math.isfinite(v)
                       for v in self.emission+self.flip):
                raise ValueError("O4_EM_NONFINITE")
            self.updates += 1

    def checkpoint(self):
        return canonical({"name": "HMM_2STATE_ACTION_EM", "emission": self.emission,
                          "flip": self.flip, "iterations": self.updates})


def fit_select(arm, training, selection):
    if arm not in ARMS:
        raise ValueError("O4_UNKNOWN_ARM")
    if arm in ARMS[-2:]:
        model = PublicHistoryCounts(lagged=(arm == "PUBLIC_LAG_COUNTS"))
        model.fit(training)
        return model, {"selection_nll": score(model, selection),
                       "selected_seed": None,
                       "selection_restarts": {"nonrandom": score(model, selection)}}
    pool = []
    for seed in INIT_SEEDS:
        model = (PublicActionHMM(seed) if arm == "HMM_2STATE_ACTION_EM"
                 else PublicRecurrent(arm, seed))
        model.fit(training)
        pool.append((score(model, selection), seed, model))
    pool.sort(key=lambda x: (x[0], x[1]))
    return pool[0][2], {
        "selection_nll": pool[0][0], "selected_seed": pool[0][1],
        "selection_restarts": {str(seed): val for val, seed, _ in pool},
    }


def sha_checkpoint(model):
    return hashlib.sha256(model.checkpoint()).hexdigest()
