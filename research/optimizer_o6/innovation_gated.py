"""O6 prospective local innovation-gated update, independently frozen parameters.

The filtered latent-state belief is supplied by *public* observation history.
The innovation gate uses next public observation ONLY when learning; at
inference the same frozen emission/transition model predicts first. The
two-state filtering equations and gate formula are *hand-designed*, not
discovered by the system. No simulator/hidden latent state is imported.
"""
import math
from o5_frozen_online import OnlineLocalBelief
from public_source import canonical


class InnovationGatedBelief(OnlineLocalBelief):
    def __init__(self, seed, train_transition=True):
        super().__init__(seed, train_transition=train_transition)

    def _forward(self, belief, prior_action, action, next_observation, learn):
        if (type(prior_action) is not int or prior_action not in (0, 1)
                or type(action) is not int or action not in (0, 1)
                or type(next_observation) is not int or next_observation not in (0, 1)):
            raise ValueError("O6_PUBLIC_INPUT_ONLY")
        context = 2*prior_action + action
        f = self.flip[context]
        predicted_latent = [
            belief[0]*(1-f) + belief[1]*f,
            belief[1]*(1-f) + belief[0]*f,
        ]
        forecast = sum(predicted_latent[state]*self.emission[state]
                       for state in (0, 1))
        joint = [[
            belief[prior]*(f if prior != post else 1-f)
            * self._emit(post, next_observation)
            for post in (0, 1)
        ] for prior in (0, 1)]
        total = sum(sum(row) for row in joint)
        if total <= 0 or not math.isfinite(total):
            raise ValueError("O6_DEGENERATE_POSTERIOR")
        posterior = [sum(joint[prior][post] for prior in (0, 1))/total
                     for post in (0, 1)]
        if learn:
            # Exactly frozen, public innovation -> bounded local stepsize:
            # g=clamp(.5+2*|next_public_bit - predictive_probability|,.5,1.5)
            gate = max(0.5, min(1.5, 0.5+2.0*abs(next_observation-forecast)))
            learning_rate = 0.045*gate
            flip_posterior = (joint[0][1]+joint[1][0])/total
            if self.train_transition:
                self.flip[context] += learning_rate*(flip_posterior-self.flip[context])
            for state in (0, 1):
                self.emission[state] += (
                    learning_rate*posterior[state]
                    *(next_observation-self.emission[state]))
            if not all(0.0 < v < 1.0 and math.isfinite(v)
                       for v in self.emission+self.flip):
                raise ValueError("O6_NONFINITE_UPDATE")
            self.updates += 1
        return posterior, forecast

    def checkpoint(self):
        return canonical({
            "schema": "forge.optimizer.o6.innovation-gated.v1",
            "seed": self.seed, "transition_training": self.train_transition,
            "fixed_base_rate": 0.045,
            "innovation_gate": "clamp(0.5+2*abs(observed-public-target - prior-forecast),0.5,1.5)",
            "emission": self.emission, "flip": self.flip,
            "updates": self.updates,
        })
