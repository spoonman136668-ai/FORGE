"""Exact population information witness for Q21N-01, without role cohorts.

Enumerates a stationary four-observation / five-action public-history window
and marginalizes the uniformly hidden state and per-episode responsive slot.
It computes ideal-law *information availability*, not a trained-model score,
an FSA grant, experimental cohort, oracle heldout or scientific first use.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import product
import json
import math

import generator
import prereg_guard

OBSERVATIONS = tuple(product((0, 1), repeat=2))
PER_BIT = 2
ACTION_WINDOW = 5
OBS_WINDOW = 4
TRANSITIONS_PER_EPISODE = 32
STATIONARY_TRANSITIONS = 28  # t = 4..31, B's previous action is present


def bernoulli_entropy(probability: float) -> float:
    if not 0 < probability < 1:
        return 0.0
    return (-probability * math.log(probability)
            - (1 - probability) * math.log1p(-probability))


def exact_window(family: str) -> dict:
    """Calculate expectation over symbol assignments, not random episodes."""
    generator.require(family in generator.FAMILIES[:2], "TRUE_LAW_FAMILY_REQUIRED")
    params = generator.family_parameters(family)
    noise = generator.fraction(params["noise"])

    def emission(slot, state, observation):
        return 0.5 * (1 - noise if observation[slot] == state else noise)

    current = defaultdict(lambda: [0.0, 0.0, 0.0])
    history_entropy = 0.0
    total_mass = 0.0

    # Five actions include the action before the four-observation window.
    # For B this is necessary: its first transition depends on both actions.
    for actions in product((0, 1), repeat=ACTION_WINDOW):
        previous, a0, a1, a2, a3 = actions
        flips = [
            generator.flip_probability(family, a, before, 1, params)
            for a, before in ((a0, previous), (a1, a0), (a2, a1),
                              (a3, a2))
        ]
        for observations in product(OBSERVATIONS, repeat=OBS_WINDOW):
            # The latent state is stationary uniform; hidden responsive slot
            # is fixed for a whole episode and initially uniform, too.
            state_mass = [
                0.25 * emission(slot, hidden_state, observations[0])
                for slot in (0, 1) for hidden_state in (0, 1)
            ]
            for k, flip in enumerate(flips[:3]):
                next_mass = [0.0] * 4
                for slot in (0, 1):
                    for hidden_state in (0, 1):
                        idx = 2 * slot + hidden_state
                        next_mass[idx] = (
                            state_mass[idx] * (1 - flip)
                            + state_mass[idx ^ 1] * flip
                        ) * emission(slot, hidden_state, observations[k + 1])
                state_mass = next_mass

            # All 32 five-action sequences are equiprobable under the
            # preregistered source-free iid Bernoulli public action policy.
            history_probability = sum(state_mass) / 32
            future_ones = [0.0, 0.0]
            for slot in (0, 1):
                for hidden_state in (0, 1):
                    for successor, transition in (
                        (hidden_state, 1 - flips[3]),
                        (1 - hidden_state, flips[3]),
                    ):
                        for bit in (0, 1):
                            one = ((1 - noise if successor else noise)
                                   if slot == bit else 0.5)
                            future_ones[bit] += (
                                state_mass[2 * slot + hidden_state]
                                * transition * one / 32
                            )
            total_mass += history_probability
            history_entropy += (
                history_probability
                * sum(bernoulli_entropy(p / history_probability)
                      for p in future_ones)
                / PER_BIT
            )

            # At prediction time t, both models know current observation
            # and a_t, a_(t-1). The history model knows the earlier public
            # observations and actions as well. No private slot or state.
            key = (observations[-1], a2, a3)
            joint = current[key]
            for i, value in enumerate((history_probability, *future_ones)):
                joint[i] += value

    generator.require(abs(total_mass - 1.0) < 1e-10, "MASS_NOT_NORMALIZED")
    generator.require(len(current) == 16, "CURRENT_PUBLIC_STATES_DRIFT")
    current_entropy = sum(
        row[0] * sum(bernoulli_entropy(row[i] / row[0])
                     for i in (1, 2)) / PER_BIT
        for row in current.values()
    )
    advantage = current_entropy - history_entropy
    # For each t >= 4, the public four-observation/five-action window has
    # exactly the stationary distribution enumerated above. A full-history
    # Bayes predictor can ignore the earlier history, so it is never worse.
    # The first four timesteps contribute >=0 to the Bayes information gain.
    return {
        "family": family,
        "mass": total_mass,
        "current_public_entropy_nats_per_bit": current_entropy,
        "four_observation_history_entropy_nats_per_bit": history_entropy,
        "stationary_public_history_gain_nats_per_bit": advantage,
        "whole_episode_32_step_information_gain_lower_bound":
            advantage * STATIONARY_TRANSITIONS / TRANSITIONS_PER_EPISODE,
        "hidden_state_or_slot_exposed": False,
        "role_episodes_generated": 0,
    }


def witness() -> dict:
    # Validate the frozen source, including original Q21's byte-identity.
    contract = prereg_guard.preflight()
    results = [exact_window(family) for family in generator.FAMILIES[:2]]
    target = generator.document()["development_decision"][
        "public_oracle_headroom_vs_best_memoryless_min_each_real_family"
    ]
    generator.require(
        all(x["whole_episode_32_step_information_gain_lower_bound"] > target
            for x in results), "IDEAL_PUBLIC_INFORMATION_UNAVAILABLE"
    )
    return {
        "schema": "forge.q21n01.population-information-witness.v1",
        "qualification": "THEORETICAL_INFORMATION_AVAILABLE_NOT_LEARNABILITY",
        "protocol_blob": contract["protocol_git_blob"],
        "base_Q21_protocol_blob": contract["predecessor_git_blob"],
        "bounds": results,
        "iid_null_exact_history_advantage_nats_per_bit": 0.0,
        "threshold_nats_per_bit": target,
        "native_fsa_admission": "NOT_REQUESTED",
        "role_episodes_generated": 0,
        "original_first_use": False,
        "models_trained": 0,
        "claimed_empirical_significance": False,
    }


if __name__ == "__main__":
    print(json.dumps(witness(), sort_keys=True, allow_nan=False))
