"""O10 prospectively frozen PUBLIC-ONLY action-composition memory source.

Hidden causal state is used ONLY to emit public action/observation triples.
Learners never receive this state or simulator rule as an input. The
hand-engineered program comparator is separately disclosed as an oracle
diagnostic, not an equally learned architecture.
"""
from __future__ import annotations
import hashlib
import json
import random

NAMESPACE = "o10-public-ops-v1"
FAMILIES = ("A_PARITY_COMPOSITION", "B_OBSERVATION_WRITE_TOGGLE", "NULL_IID")
ROLES = ("O10_PUBLIC_TRAIN", "O10_PUBLIC_SELECT", "O10_PUBLIC_DEV")
COUNTS = {"O10_PUBLIC_TRAIN": 96, "O10_PUBLIC_SELECT": 24,
          "O10_PUBLIC_DEV": 32}
STEPS = 30
QUERY_STEPS = (12, 24)


class RoleNotAdmitted(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=True).encode("ascii")


def seed(role, family, index):
    if not (type(role) is str and role in ROLES and
            type(family) is str and family in FAMILIES and
            type(index) is int and 0 <= index < COUNTS[role]):
        raise RoleNotAdmitted("O10_UNREGISTERED_PUBLIC_ROLE")
    value = f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(value).digest()[:8], "big")


def episode(role, family, index):
    rng = random.Random(seed(role, family, index))
    cue = rng.randrange(2)
    query = QUERY_STEPS[rng.randrange(2)]
    observation = cue
    memory, parity = cue, 0
    rows = []
    for t in range(STEPS):
        action = 2 if t == query else rng.randrange(2)
        if action == 2:
            if family == "NULL_IID":
                nxt = rng.randrange(2)
            else:
                target = (cue ^ parity if family == "A_PARITY_COMPOSITION"
                          else memory)
                nxt = target ^ int(rng.random() < 0.05)
        else:
            if family == "B_OBSERVATION_WRITE_TOGGLE":
                memory = (observation if action == 0 else (memory ^ 1))
            parity ^= (action == 1)
            nxt = rng.randrange(2)
        rows.append((observation, action, nxt))
        observation = nxt
    return tuple(rows)


def role_episodes(role, family):
    if role not in ROLES or family not in FAMILIES:
        raise RoleNotAdmitted("O10_PUBLIC_ONLY")
    return tuple(episode(role, family, i) for i in range(COUNTS[role]))


def role_sha(batch):
    return hashlib.sha256(canonical(batch)).hexdigest()


def query_info(ep):
    if (type(ep) not in (tuple, list) or len(ep) != STEPS
            or any(type(row) not in (tuple, list) or len(row) != 3 or
                   type(row[0]) is not int or row[0] not in (0, 1) or
                   type(row[1]) is not int or row[1] not in (0, 1, 2) or
                   type(row[2]) is not int or row[2] not in (0, 1)
                   for row in ep)):
        raise ValueError("O10_PUBLIC_TRIPLE_CONTRACT")
    if any(ep[t][2] != ep[t+1][0] for t in range(STEPS-1)):
        raise ValueError("O10_BROKEN_PUBLIC_OBSERVATION_CHAIN")
    locations = [t for t, row in enumerate(ep) if row[1] == 2]
    if len(locations) != 1 or locations[0] not in QUERY_STEPS:
        raise ValueError("O10_BAD_QUERY_ACTION")
    q = locations[0]
    return {"cue": ep[0][0], "current": ep[q][0],
            "parity": sum(int(row[1] == 1) for row in ep[:q]) % 2,
            "last_action": ep[q-1][1], "query_t": q,
            "target": ep[q][2]}


def public_program(ep, family):
    """Deliberately engineeered information-sufficiency witness, not learner."""
    if family not in FAMILIES:
        raise ValueError("O10_BAD_WITNESS_FAMILY")
    q = query_info(ep)["query_t"]
    if family == "A_PARITY_COMPOSITION":
        return ep[0][0] ^ sum(int(row[1] == 1) for row in ep[:q]) % 2
    if family == "B_OBSERVATION_WRITE_TOGGLE":
        state = ep[0][0]
        for observation, action, _ in ep[:q]:
            state = observation if action == 0 else state ^ 1
        return state
    return 0
