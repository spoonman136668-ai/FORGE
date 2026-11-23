"""Q21N-01 isolated, FORGE-native source-free causal generator.

Pure library, no CLI for role generation and no import-side episodes. A future
FSA-admitted worker must fence first use before calling generate() for frozen
FIT_TRAIN/FIT_VALID/DEV. This module never authenticates FSA or issues starts.
Original Q21 roles, seeds, cohorts and protocol are never accessed or changed.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prereg_guard as guard

ROLE_COUNTS = dict(guard.ROLES)
FAMILIES = guard.FAMILIES
PUBLIC_FIELDS = ("family", "observations", "actions")
ROLES = frozenset(ROLE_COUNTS)
SEED_PREFIX = "forge-q21n01-v1:"
OBSERVATIONS = 33
ACTIONS = 32


def require(condition, reason):
    if not condition:
        raise guard.ProtocolRefused("Q21N01_" + reason)


def document():
    doc, old = guard.read_protocol()
    guard.validate(doc, old)
    return doc


def seed_for(role: str, family: str, index: int) -> int:
    """No RNG draw, cohort birth or role consumption here."""
    require(role in ROLES, "UNKNOWN_ROLE")
    require(family in FAMILIES, "UNKNOWN_FAMILY")
    require(type(index) is int and 0 <= index < ROLE_COUNTS[role],
            "EPISODE_INDEX_DRIFT")
    encoded = (SEED_PREFIX + role + ":" + family + ":" + str(index)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big")


def fraction(value: str) -> float:
    require(isinstance(value, str) and value.count("/") == 1,
            "PROBABILITY_FRACTION_FORMAT")
    n, d = value.split("/")
    require(n.isdecimal() and d.isdecimal() and int(d) > 0,
            "PROBABILITY_FRACTION_INVALID")
    p = int(n) / int(d)
    require(0 < p < 1, "PROBABILITY_OUT_OF_RANGE")
    return p


def family_parameters(family: str, doc=None) -> dict:
    require(family in FAMILIES, "UNKNOWN_FAMILY")
    protocol = document() if doc is None else doc
    records = protocol["generator"]["families"]
    return next(record["fixed_generator"] for record in records
                if record["id"] == family)


def flip_probability(family: str, current_action: int,
                     previous_action: int, at_time: int, params: dict) -> float:
    """Pure transition rule; can be tested without sampling a single cohort."""
    require(family in FAMILIES[:2], "NO_CAUSAL_TRANSITION_IN_NULL")
    require(current_action in (0, 1) and previous_action in (0, 1) and
            type(at_time) is int and at_time >= 0,
            "ACTION_HISTORY_INVALID")
    if family == FAMILIES[0]:
        return fraction(params["flip_if_a1"] if current_action
                        else params["flip_if_a0"])
    spontaneous = fraction(params["spontaneous_flip"])
    return (1 - spontaneous) if (at_time > 0 and current_action and
                                previous_action) else spontaneous


def make_public_row(family, observations, actions):
    """Coerce only exact public fields; never return latent or sensor slot."""
    require(family in FAMILIES, "UNKNOWN_PUBLIC_FAMILY")
    require(type(actions) in (list, tuple) and
            type(observations) in (list, tuple) and
            len(actions) + 1 == len(observations),
            "PUBLIC_EPISODE_SHAPE")
    require(all(type(a) is int and a in (0, 1) for a in actions),
            "PUBLIC_ACTION_BIT")
    require(all(type(o) in (tuple, list) and len(o) == 2 and
                all(type(bit) is int and bit in (0, 1) for bit in o)
                for o in observations),
            "PUBLIC_OBSERVATION_BIT")
    return family, tuple(tuple(obs) for obs in observations), tuple(actions)


def public_rows(rows):
    """A learner only sees explicitly validated public triples."""
    require(type(rows) is list, "PUBLIC_ROWS_NOT_LIST")
    output = []
    for row in rows:
        require(type(row) is tuple and len(row) == 3,
                "PRIVILEGED_FIELD_LEAKAGE")
        output.append(make_public_row(*row))
    return output


def generate(role: str, family: str, index: int, *, authenticated_fsa_worker: bool = False):
    """Prospective study operation: MUST be called after external real FSA.

    The boolean is a fail-closed local safeguard, NOT proof of authorization.
    A qualified worker must independently authenticate and journal FSA grant,
    immutable source, one-shot role birth and lease BEFORE entering this API.
    No GitHub branch, CLI, local JSON, ticket flag or test permits science.
    """
    require(authenticated_fsa_worker is True,
            "EXTERNAL_FSA_ADMISSION_NOT_PRESENT")
    doc = document()
    rng = random.Random(seed_for(role, family, index))
    params = family_parameters(family, doc)
    actions = [rng.randrange(2) for _ in range(ACTIONS)]
    if family == FAMILIES[2]:
        observations = [(rng.randrange(2), rng.randrange(2))
                        for _ in range(OBSERVATIONS)]
        secret = {"privileged": True, "null": True, "family": family}
    else:
        slot = rng.randrange(2)
        state = rng.randrange(2)
        noise = fraction(params["noise"])
        observations = []
        for t in range(OBSERVATIONS):
            noisy = state ^ int(rng.random() < noise)
            distractor = rng.randrange(2)
            observations.append((noisy, distractor) if slot == 0
                                else (distractor, noisy))
            if t < ACTIONS:
                prev = actions[t-1] if t else 0
                p_flip = flip_probability(family, actions[t], prev, t, params)
                state ^= int(rng.random() < p_flip)
        secret = {"privileged": True, "family": family,
                  "responsive_slot": slot, "initial_latent_private": True}
    public = make_public_row(family, observations, actions)
    require(len(public[1]) == OBSERVATIONS and
            len(public[2]) == ACTIONS, "EPISODE_LENGTH_DRIFT")
    return public, secret


def preflight():
    status = guard.preflight()
    require(status["authority_admitted"] is False and
            status["cohorts_generated"] == 0, "UNEXPECTED_PREVIOUS_SCIENCE")
    for role, count in ROLE_COUNTS.items():
        for family in FAMILIES:
            seed_for(role, family, 0)
            seed_for(role, family, count-1)
    for family in FAMILIES[:2]:
        params = family_parameters(family)
        flip_probability(family, 0, 0, 0, params)
        flip_probability(family, 1, 1, 2, params)
    return {"status": "Q21N01_NATIVE_GENERATOR_SOURCE_ONLY_PASS",
            "new_seed_namespace": SEED_PREFIX,
            "roles": ROLE_COUNTS,
            "families": list(FAMILIES),
            "episodes_generated": 0,
            "scientific_admission": "NOT_GRANTED",
            "original_or_heldout_first_use": False}


if __name__ == "__main__":
    # Source-only audit, not a sampling or training CLI.
    print(json.dumps(preflight(), sort_keys=True))
