"""O13 fresh PUBLIC next-bit causal information, no protected roles.

The hidden simulator state exists ONLY inside episode generation. Learners
are given tuple(o_t, public_action_t, o_next), no latent labels or family ID.
"""
import hashlib
import json
import random

NAMESPACE="o13-new-public-credit-v1"
FAMILIES=("A_SWITCH_AND_RETAIN","B_LAGGED_CAUSAL_ACTION",
          "C_SENSOR_REGIME_DRIFT","NULL_IID")
ROLES=("O13_PUBLIC_TRAIN","O13_PUBLIC_SELECT","O13_PUBLIC_DEV")
COUNTS={"O13_PUBLIC_TRAIN":48,"O13_PUBLIC_SELECT":16,
        "O13_PUBLIC_DEV":24}
STEPS=28


class ReservedRole(ValueError):
    pass


def canonical(value):
    return json.dumps(value,sort_keys=True,allow_nan=False,
                      ensure_ascii=True,separators=(",",":")).encode("ascii")


def seed(role,family,index):
    if not (type(role) is str and role in ROLES and
            type(family) is str and family in FAMILIES and
            type(index) is int and 0<=index<COUNTS[role]):
        raise ReservedRole("O13_PROTECTED_OR_UNKNOWN_ROLE")
    s=f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(s).digest()[:8],"big")


def episode(role,family,index):
    rng=random.Random(seed(role,family,index))
    if family=="NULL_IID":
        obs=rng.randrange(2)
        rows=[]
        for _ in range(STEPS):
            action,nxt=rng.randrange(2),rng.randrange(2)
            rows.append((obs,action,nxt))
            obs=nxt
        return tuple(rows)
    hidden=rng.randrange(2)
    accuracy=(.83 if family=="A_SWITCH_AND_RETAIN"
              else .75 if family=="B_LAGGED_CAUSAL_ACTION" else .93)
    obs=hidden if rng.random()<accuracy else hidden^1
    previous_action=0
    rows=[]
    for t in range(STEPS):
        action=rng.randrange(2)
        if family=="A_SWITCH_AND_RETAIN":
            flip=.72 if action else .04
            accuracy=.83
        elif family=="B_LAGGED_CAUSAL_ACTION":
            flip=.76 if previous_action==1 and action==0 else .06
            accuracy=.75
        else:
            flip=.62 if action else .13
            accuracy=.93 if t%2==0 else .61
        if rng.random()<flip:
            hidden^=1
        nxt=hidden if rng.random()<accuracy else hidden^1
        rows.append((obs,action,nxt))
        obs=nxt
        previous_action=action
    return tuple(rows)


def public_episodes(role,family):
    if type(role) is not str or role not in ROLES or family not in FAMILIES:
        raise ReservedRole("O13_NOT_PUBLIC_ROLE")
    return tuple(episode(role,family,i) for i in range(COUNTS[role]))


def digest(batch):
    return hashlib.sha256(canonical(batch)).hexdigest()
