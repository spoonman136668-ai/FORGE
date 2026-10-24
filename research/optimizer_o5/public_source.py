"""O5 fresh role-isolated PUBLIC development observations.

This generator's latent variable is never exposed to the learner. Public
tuple: (current-observation, action, next-observation). O5 never instantiates
any protected, original, O4, Q20, Q21 or Q21N01 cohort.
"""
from __future__ import annotations
import hashlib
import json
import random

NAMESPACE = "o5-public-v1"
FAMILIES = ("A_FRESH_PERSISTENT", "B_FRESH_DELAYED", "NULL_FRESH_IID")
ROLES = ("O5_PUBLIC_TRAIN", "O5_PUBLIC_SELECT", "O5_PUBLIC_DEV")
ROLE_COUNTS = {"O5_PUBLIC_TRAIN": 64, "O5_PUBLIC_SELECT": 16,
               "O5_PUBLIC_DEV": 24}
STEPS = 24


class ForbiddenRole(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def seed(role, family, index):
    if (type(role) is not str or role not in ROLES or
            type(family) is not str or family not in FAMILIES or
            type(index) is not int or not 0 <= index < ROLE_COUNTS[role]):
        raise ForbiddenRole("O5_PUBLIC_ROLE_FAMILY_INDEX_REFUSED")
    body = f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(body).digest()[:8], "big")


def episode(role, family, index):
    rnd = random.Random(seed(role, family, index))
    if family == "NULL_FRESH_IID":
        observation = rnd.randrange(2)
        public = []
        for _ in range(STEPS):
            action, next_observation = rnd.randrange(2), rnd.randrange(2)
            public.append((observation, action, next_observation))
            observation = next_observation
        return tuple(public)
    latent = rnd.randrange(2)
    observation = latent if rnd.random() < 0.82 else (latent ^ 1)
    previous_action = 0
    public = []
    for _ in range(STEPS):
        action = rnd.randrange(2)
        if family == "A_FRESH_PERSISTENT":
            probability = 0.62 if action else 0.05
        else:
            probability = 0.73 if previous_action == 1 and action == 1 else 0.11
        if rnd.random() < probability:
            latent ^= 1
        next_observation = latent if rnd.random() < 0.82 else (latent ^ 1)
        public.append((observation, action, next_observation))
        observation, previous_action = next_observation, action
    return tuple(public)


def role_episodes(role, family):
    if role not in ROLES or family not in FAMILIES:
        raise ForbiddenRole("O5_UNREGISTERED_ROLE_OR_FAMILY")
    return tuple(episode(role, family, n) for n in range(ROLE_COUNTS[role]))


def digest(public_rows):
    return hashlib.sha256(canonical(public_rows)).hexdigest()
