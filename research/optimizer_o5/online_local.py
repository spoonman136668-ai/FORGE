"""O5 single-pass local predictive-state learner, public observations ONLY.

Two inferred latent-state beliefs, a locally learned action-conditioned state
flip estimate, and locally learned public sensor emission probabilities. Does
not inspect the source's hidden state or train on public DEV. State formation
is learned; the two-state filter structure is prescribed and disclosed.
"""
from __future__ import annotations

import math
import random
from public_source import canonical

SEEDS = (17, 31)
STEP_RATE = 0.045
STATES = 2


class OnlineLocalBelief:
    def __init__(self, seed, train_transition=True):
        if type(seed) is not int or seed not in SEEDS:
            raise ValueError("O5_UNFROZEN_INITIALIZATION")
        if type(train_transition) is not bool:
            raise ValueError("O5_UNFROZEN_ABLATION")
        rnd = random.Random(seed)
        self.seed = seed
        self.train_transition = train_transition
        self.emission = [
            0.20 + rnd.uniform(-0.08, 0.08),
            0.80 + rnd.uniform(-0.08, 0.08),
        ]
        self.flip = [
            0.12 + rnd.uniform(-0.06, 0.06),
            0.32 + rnd.uniform(-0.06, 0.06),
            0.32 + rnd.uniform(-0.06, 0.06),
            0.65 + rnd.uniform(-0.06, 0.06),
        ]
        self.updates = 0

    def _emit(self, state, observed):
        probability = self.emission[state]
        return probability if observed else 1.0-probability

    def _initial_belief(self, observed):
        p = [0.5*self._emit(state, observed) for state in range(STATES)]
        normalization = sum(p)
        return [value/normalization for value in p]

    def _forward(self, belief, prior_action, action, next_observation, learn):
        if (type(prior_action) is not int or prior_action not in (0, 1)
                or type(action) is not int or action not in (0, 1)
                or type(next_observation) is not int or next_observation not in (0, 1)):
            raise ValueError("O5_NONPUBLIC_OR_INVALID_INPUT")
        context = 2*prior_action+action
        flip = self.flip[context]
        predicted_state = [
            belief[0]*(1.0-flip)+belief[1]*flip,
            belief[1]*(1.0-flip)+belief[0]*flip,
        ]
        next_bit_p = (
            predicted_state[0]*self.emission[0]
            + predicted_state[1]*self.emission[1]
        )
        next_joint = [[
            belief[previous] * (flip if previous != after else 1.0-flip)
            * self._emit(after, next_observation)
            for after in range(STATES)
        ] for previous in range(STATES)]
        mass = sum(sum(row) for row in next_joint)
        if mass <= 0 or not math.isfinite(mass):
            raise ValueError("O5_FILTER_MASS_INVALID")
        posterior = [sum(next_joint[previous][state]
                         for previous in range(STATES))/mass
                     for state in range(STATES)]
        if learn:
            inferred_flip = (next_joint[0][1]+next_joint[1][0])/mass
            if self.train_transition:
                self.flip[context] += STEP_RATE*(inferred_flip-self.flip[context])
            for state in range(STATES):
                self.emission[state] += (
                    STEP_RATE*posterior[state]*
                    (next_observation-self.emission[state])
                )
            if not all(0 < x < 1 and math.isfinite(x)
                       for x in self.emission+self.flip):
                raise ValueError("O5_MODEL_UPDATE_NONFINITE")
            self.updates += 1
        return posterior, next_bit_p

    def _walk(self, episode, learn):
        if type(episode) not in (tuple, list) or len(episode) != 24:
            raise ValueError("O5_EXACT_PUBLIC_EPISODE_REQUIRED")
        if not all(type(row) in (tuple, list) and len(row) == 3
                   and all(type(bit) is int and bit in (0, 1) for bit in row)
                   for row in episode):
            raise ValueError("O5_PUBLIC_ROW_SCHEMA")
        if any(episode[t][2] != episode[t+1][0]
               for t in range(len(episode)-1)):
            raise ValueError("O5_PUBLIC_EPISODE_DISCONNECTED")
        belief = self._initial_belief(episode[0][0])
        prior_action = 0
        predictions = []
        for _, action, next_observation in episode:
            belief, prediction = self._forward(
                belief, prior_action, action, next_observation, learn)
            predictions.append(prediction)
            prior_action = action
        return predictions

    def fit(self, episodes):
        if type(episodes) not in (tuple, list) or not episodes:
            raise ValueError("O5_FIT_REQUIRES_PUBLIC_EPISODES")
        for row in episodes:
            self._walk(row, True)

    def predict(self, episode):
        return self._walk(episode, False)

    def checkpoint(self):
        return canonical({
            "schema": "forge.optimizer.o5.local-predictive-state.v1",
            "seed": self.seed,
            "transition_training": self.train_transition,
            "emission": self.emission,
            "flip": self.flip,
            "updates": self.updates,
        })
