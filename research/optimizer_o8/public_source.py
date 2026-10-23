"""O8 fresh, prospectively frozen PUBLIC query episodes only.

The public observation o0 carries one task cue. All intervening public bits
are iid distractions. Only one public query action=2 occurs at t=10 or 18.
A next-bit is returned after each action, but only query responses are scored
and used for supervision. Hidden task variables never enter learner inputs.
"""
from __future__ import annotations

import hashlib
import json
import random

NAMESPACE = "o8-public-20261023-v1"
FAMILIES = ("A_DELAYED_ECHO", "B_DELAYED_ACTION_PARITY",
            "NULL_DELAYED_QUERY_IID")
ROLES = ("O8_PUBLIC_TRAIN", "O8_PUBLIC_SELECT", "O8_PUBLIC_DEV")
COUNTS = {"O8_PUBLIC_TRAIN": 96, "O8_PUBLIC_SELECT": 24,
          "O8_PUBLIC_DEV": 32}
STEPS = 24
QUERY_TIMES = (10, 18)


class ProtectedRoleRefused(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=True).encode("ascii")


def seed(role, family, i):
    if not (type(role) is str and role in ROLES and
            type(family) is str and family in FAMILIES and
            type(i) is int and 0 <= i < COUNTS[role]):
        raise ProtectedRoleRefused("O8_UNREGISTERED_SOURCE_ID")
    data = f"{NAMESPACE}:{role}:{family}:{i}".encode("ascii")
    return int.from_bytes(hashlib.sha256(data).digest()[:8], "big")


def public_episode(role, family, i):
    rng = random.Random(seed(role, family, i))
    initial_cue = rng.randrange(2)
    query_t = QUERY_TIMES[rng.randrange(len(QUERY_TIMES))]
    observation = initial_cue
    parity = 0
    rows = []
    for t in range(STEPS):
        action = 2 if t == query_t else rng.randrange(2)
        if t == query_t:
            if family == "A_DELAYED_ECHO":
                nxt = initial_cue
                if rng.random() < 0.05:
                    nxt ^= 1
            elif family == "B_DELAYED_ACTION_PARITY":
                nxt = initial_cue ^ parity
                if rng.random() < 0.05:
                    nxt ^= 1
            else:
                nxt = rng.randrange(2)
        else:
            nxt = rng.randrange(2)
        rows.append((observation, action, nxt))
        if action == 1:
            parity ^= 1
        observation = nxt
    return tuple(rows)


def all_public(role, family):
    if type(role) is not str or role not in ROLES or family not in FAMILIES:
        raise ProtectedRoleRefused("O8_PROTECTED_ROLE_REFUSED")
    return tuple(public_episode(role, family, i)
                 for i in range(COUNTS[role]))


def role_digest(data):
    return hashlib.sha256(canonical(data)).hexdigest()


def query_info(episode):
    """Cue and action parity are derived exclusively from *public* history."""
    if (type(episode) not in (tuple, list) or len(episode) != STEPS
            or any(type(row) not in (tuple, list) or len(row) != 3
                   or any(type(bit) is not int or bit not in (0, 1, 2)
                          for bit in row)
                   or row[0] == 2 or row[2] == 2
                   for row in episode)):
        raise ValueError("O8_PUBLIC_EPISODE_SCHEMA")
    if any(episode[i][2] != episode[i+1][0] for i in range(STEPS-1)):
        raise ValueError("O8_PUBLIC_CHAIN_MISMATCH")
    query_positions = [i for i,row in enumerate(episode) if row[1] == 2]
    if len(query_positions) != 1 or query_positions[0] not in QUERY_TIMES:
        raise ValueError("O8_UNEXPECTED_QUERY_POSITIONS")
    q = query_positions[0]
    parity = 0
    for _,action,_ in episode[:q]:
        if action == 1:
            parity ^= 1
    return {"cue":episode[0][0], "parity":parity,
            "query_t":q,"query_observation":episode[q][0],
            "target":episode[q][2]}
