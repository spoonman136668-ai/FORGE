"""O9 fresh public multi-cue episodic source. No protected scientific role.

Each observation/action in the generated episode is public; hidden cue variables
are not model inputs, and source family/role identities are never learner
features. Only delayed query next-bit is a supervised target.
"""
from __future__ import annotations
import hashlib
import json
import random

NAMESPACE = "o9-20261023-memory-routing-v1"
FAMILIES = ("A_ONE_CUE_RECALL", "B_SELECT_TWO_CUES",
            "C_CUE_ACTION_PARITY", "NULL_IID_QUERY")
ROLES = ("O9_PUBLIC_TRAIN", "O9_PUBLIC_SELECT", "O9_PUBLIC_DEV")
COUNTS = {"O9_PUBLIC_TRAIN":96, "O9_PUBLIC_SELECT":24, "O9_PUBLIC_DEV":32}
STEPS=24
QUERIES=(10,18)


class RefusedRole(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def seed(role, family, index):
    if not (type(role) is str and role in ROLES and
            type(family) is str and family in FAMILIES and
            type(index) is int and 0 <= index < COUNTS[role]):
        raise RefusedRole("O9_PROTECTED_ROLE_OR_INVALID_ID")
    return int.from_bytes(hashlib.sha256(
        f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    ).digest()[:8], "big")


def episode(role, family, index):
    rng = random.Random(seed(role, family, index))
    query_t = QUERIES[rng.randrange(len(QUERIES))]
    first = rng.randrange(2)
    second = rng.randrange(2)
    selector = rng.randrange(2)
    current=first
    parity=0
    rows=[]
    for t in range(STEPS):
        if t == query_t:
            action=2
            if family == "A_ONE_CUE_RECALL":
                nxt = first
            elif family == "B_SELECT_TWO_CUES":
                nxt = first if selector == 0 else second
            elif family == "C_CUE_ACTION_PARITY":
                nxt = first ^ parity
            else:
                nxt = rng.randrange(2)
            if family != "NULL_IID_QUERY" and rng.random() < .05:
                nxt ^= 1
        else:
            action = selector if (family == "B_SELECT_TWO_CUES"
                                  and t == query_t-1) else rng.randrange(2)
            # Put the second *public* cue into o4 via next-bit at t=3.
            nxt = second if (t == 3 and family == "B_SELECT_TWO_CUES") \
                else rng.randrange(2)
        rows.append((current, action, nxt))
        if action == 1 and t < query_t:
            parity ^= 1
        current=nxt
    return tuple(rows)


def public_roles(role, family):
    if type(role) is not str or role not in ROLES or family not in FAMILIES:
        raise RefusedRole("O9_PROTECTED_ROLE")
    return tuple(episode(role, family, i) for i in range(COUNTS[role]))


def digest(batch):
    return hashlib.sha256(canonical(batch)).hexdigest()


def query_info(ep):
    if type(ep) not in (tuple,list) or len(ep) != STEPS:
        raise ValueError("O9_PUBLIC_EPISODE_LENGTH")
    if any(type(row) not in (tuple,list) or len(row)!=3 or
           any(type(x) is not int for x in row) or
           row[0] not in (0,1) or row[1] not in (0,1,2) or
           row[2] not in (0,1) for row in ep):
        raise ValueError("O9_PUBLIC_EPISODE_BINARY")
    if any(ep[t][2] != ep[t+1][0] for t in range(STEPS-1)):
        raise ValueError("O9_PUBLIC_CHAIN")
    qs=[t for t,row in enumerate(ep) if row[1]==2]
    if len(qs)!=1 or qs[0] not in QUERIES:
        raise ValueError("O9_QUERY_LOCATION")
    q=qs[0]
    return {
        "query_t":q,"cue":ep[0][0],"cue4":ep[4][0],
        "selector":ep[q-1][1],
        "parity":sum(row[1]==1 for row in ep[:q])%2,
        "query_observation":ep[q][0],"target":ep[q][2],
    }
