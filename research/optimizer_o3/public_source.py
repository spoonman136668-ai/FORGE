"""O3 public-only causal source: never creates protected/HELD role episodes.

Hidden generator law is used only to emit public action/observation histories.
Learners receive the public tuple (o_t, a_t) before predicting o_(t+1).
"""
from __future__ import annotations

import hashlib
import json
import random

FAMILIES = ("A_PERSISTENT_ACTION_SWITCH", "B_DELAYED_ACTION_SWITCH",
            "NULL_INDEPENDENT")
ROLES = ("PUBLIC_TRAIN", "PUBLIC_SELECT", "PUBLIC_DEV")
ROLE_COUNTS = {"PUBLIC_TRAIN": 48, "PUBLIC_SELECT": 16, "PUBLIC_DEV": 20}
STEPS = 24


class RoleRefused(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def seed_for(role, family, index):
    if (type(role) is not str or role not in ROLES or
            type(family) is not str or family not in FAMILIES or
            type(index) is not int or not 0 <= index < ROLE_COUNTS[role]):
        raise RoleRefused("O3_SOURCE_ROLE_OR_INDEX_REFUSED")
    v = "o3-public-dev-v1:" + role + ":" + family + ":" + str(index)
    return int.from_bytes(hashlib.sha256(v.encode("ascii")).digest()[:8], "big")


def public_episode(role, family, index):
    """Emits 24 public (current_observation, current_action, next_observation)."""
    rnd = random.Random(seed_for(role, family, index))
    if family == "NULL_INDEPENDENT":
        observation = rnd.randrange(2)
        rows = []
        for _ in range(STEPS):
            action, nxt = rnd.randrange(2), rnd.randrange(2)
            rows.append((observation, action, nxt))
            observation = nxt
        return tuple(rows)
    hidden = rnd.randrange(2)
    observation = hidden if rnd.random() < 0.86 else (hidden ^ 1)
    prev_action = 0
    rows = []
    for _ in range(STEPS):
        action = rnd.randrange(2)
        if family == "A_PERSISTENT_ACTION_SWITCH":
            flip_probability = 0.7 if action else 0.1
        else:
            flip_probability = 0.85 if action and prev_action else 0.07
        if rnd.random() < flip_probability:
            hidden ^= 1
        nxt = hidden if rnd.random() < 0.86 else (hidden ^ 1)
        rows.append((observation, action, nxt))
        observation, prev_action = nxt, action
    return tuple(rows)


def role_episodes(role, family):
    if role not in ROLES or family not in FAMILIES:
        raise RoleRefused("O3_SOURCE_ROLE_REFUSED")
    return tuple(public_episode(role, family, i)
                 for i in range(ROLE_COUNTS[role]))


def role_digest(role, family, episodes=None):
    rows = role_episodes(role, family) if episodes is None else episodes
    return hashlib.sha256(canonical(rows)).hexdigest()
