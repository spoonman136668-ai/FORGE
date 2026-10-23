"""O4 fresh public-only development source; never instantiates protected roles.

These synthetic generators use private latent variables ONLY to emit public
tuples; models receive (current public observation, current public action,
next public observation), and predict before seeing the last field.
"""
from __future__ import annotations
import hashlib
import json
import random

FAMILIES = ("A_ACTION_SWITCH", "B_DELAYED_ACTION_SWITCH", "NULL_IID")
ROLES = ("O4_TRAIN", "O4_SELECT", "O4_DEV")
COUNTS = {"O4_TRAIN": 48, "O4_SELECT": 16, "O4_DEV": 24}
STEPS = 24
NAMESPACE = "o4-public-20261023-v1"


class PublicRoleRefused(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def public_seed(role, family, index):
    if (type(role) is not str or role not in ROLES or
            type(family) is not str or family not in FAMILIES or
            type(index) is not int or not 0 <= index < COUNTS[role]):
        raise PublicRoleRefused("O4_ROLE_FAMILY_INDEX_REFUSED")
    value = f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(value).digest()[:8], "big")


def episode(role, family, index):
    rng = random.Random(public_seed(role, family, index))
    if family == "NULL_IID":
        observation = rng.randrange(2)
        result = []
        for _ in range(STEPS):
            action, next_observation = rng.randrange(2), rng.randrange(2)
            result.append((observation, action, next_observation))
            observation = next_observation
        return tuple(result)
    latent = rng.randrange(2)
    observation = latent if rng.random() < 0.86 else 1-latent
    previous_action = 0
    result = []
    for _ in range(STEPS):
        action = rng.randrange(2)
        if family == "A_ACTION_SWITCH":
            flip_probability = 0.7 if action else 0.1
        else:
            flip_probability = 0.85 if previous_action == action == 1 else 0.07
        if rng.random() < flip_probability:
            latent = 1-latent
        next_observation = latent if rng.random() < 0.86 else 1-latent
        result.append((observation, action, next_observation))
        previous_action, observation = action, next_observation
    return tuple(result)


def dataset(role, family):
    if role not in ROLES or family not in FAMILIES:
        raise PublicRoleRefused("O4_RESERVED_ROLE_OR_FAMILY")
    return tuple(episode(role, family, i) for i in range(COUNTS[role]))


def digest(rows):
    return hashlib.sha256(canonical(rows)).hexdigest()
