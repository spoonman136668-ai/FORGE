"""O6 new public DEV source families, source-disjoint from O2-O5 by namespace.

The private generator's hidden binary value is never learner input. Only
(current public observation, public action, NEXT public observation) is
returned. The target is used for training after predicting it.
"""
import hashlib
import json
import random

NAMESPACE = "o6-public-v1"
FAMILIES = ("A_XOR_ACTION_HISTORY", "B_FALLING_EDGE", "NULL_IID")
ROLES = ("O6_PUBLIC_TRAIN", "O6_PUBLIC_SELECT", "O6_PUBLIC_DEV")
ROLE_COUNTS = {"O6_PUBLIC_TRAIN": 64, "O6_PUBLIC_SELECT": 16,
               "O6_PUBLIC_DEV": 24}
STEPS = 24


class ReservedSourceRole(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      allow_nan=False, separators=(",", ":")).encode("ascii")


def seed(role, family, index):
    if (type(role) is not str or role not in ROLES or
        type(family) is not str or family not in FAMILIES or
        type(index) is not int or not 0 <= index < ROLE_COUNTS[role]):
        raise ReservedSourceRole("O6_UNAUTHORIZED_SOURCE_ROLE")
    text = f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(text).digest()[:8], "big")


def public_episode(role, family, index):
    rng = random.Random(seed(role, family, index))
    if family == "NULL_IID":
        observed = rng.randrange(2)
        rows = []
        for _ in range(STEPS):
            action, nxt = rng.randrange(2), rng.randrange(2)
            rows.append((observed, action, nxt))
            observed = nxt
        return tuple(rows)
    hidden = rng.randrange(2)
    sensor_accuracy = 0.85 if family == "A_XOR_ACTION_HISTORY" else 0.75
    observed = hidden if rng.random() < sensor_accuracy else hidden ^ 1
    previous_action = 0
    rows = []
    for _ in range(STEPS):
        action = rng.randrange(2)
        if family == "A_XOR_ACTION_HISTORY":
            flip = 0.70 if previous_action != action else 0.06
        else:
            flip = 0.80 if (previous_action == 1 and action == 0) else 0.08
        if rng.random() < flip:
            hidden ^= 1
        nxt = hidden if rng.random() < sensor_accuracy else hidden ^ 1
        rows.append((observed, action, nxt))
        observed, previous_action = nxt, action
    return tuple(rows)


def role_episodes(role, family):
    if role not in ROLES or family not in FAMILIES:
        raise ReservedSourceRole("O6_RESERVED_SOURCE_ROLE")
    return tuple(public_episode(role, family, index)
                 for index in range(ROLE_COUNTS[role]))


def source_digest(episodes):
    return hashlib.sha256(canonical(episodes)).hexdigest()
