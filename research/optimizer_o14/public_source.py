"""O14 prospective fresh public source with strict FIT vs TRANSFER custody.

The **only** export is public next-observation histories (o_t, a_t, o_t+1).
No learner sees latent generator state or the family name as a model feature.
All ZERO_SHOT_TRANSFER families fail closed if requested with FIT roles.
This is new author-generated synthetic source, NOT external heldout science.
"""
import hashlib
import json
import random

NAMESPACE="o14-20261023-structural-transfer-v1"
FIT_FAMILIES=("FIT_A_BINARY_ACTION_SWITCH","FIT_B_BINARY_LAG_EFFECT")
TRANSFER_FAMILIES=("XFER_C_THREE_STATE_CYCLE",
                   "XFER_D_COUPLED_BIT_MEMORY","XFER_NULL_IID")
FAMILIES=FIT_FAMILIES+TRANSFER_FAMILIES
ROLES=("O14_FIT_TRAIN","O14_FIT_SELECT","O14_INDOMAIN_DEV",
       "O14_ZERO_SHOT_TRANSFER")
ROLE_COUNTS={
    "O14_FIT_TRAIN":{f:24 for f in FIT_FAMILIES},
    "O14_FIT_SELECT":{f:8 for f in FIT_FAMILIES},
    "O14_INDOMAIN_DEV":{f:24 for f in FIT_FAMILIES},
    "O14_ZERO_SHOT_TRANSFER":{f:24 for f in TRANSFER_FAMILIES},
}
STEPS=32


class SourceCustodyRefused(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=True,allow_nan=False,
                      separators=(",",":")).encode("ascii")


def seed(role,family,index):
    count=ROLE_COUNTS.get(role,{}).get(family)
    if not (type(role) is str and type(family) is str and
            type(index) is int and count is not None
            and 0<=index<count):
        raise SourceCustodyRefused("O14_ROLE_FAMILY_OR_INDEX_REFUSED")
    s=f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(s).digest()[:8],"big")


def episode(role,family,index):
    rng=random.Random(seed(role,family,index))
    if family=="XFER_NULL_IID":
        observed=rng.randrange(2)
        rows=[]
        for _ in range(STEPS):
            action,following=rng.randrange(2),rng.randrange(2)
            rows.append((observed,action,following))
            observed=following
        return tuple(rows)
    previous_action=0
    if family=="XFER_C_THREE_STATE_CYCLE":
        state=rng.randrange(3)
        observed=(int(state==2) if rng.random()<.90
                  else 1-int(state==2))
    elif family=="XFER_D_COUPLED_BIT_MEMORY":
        first,second=rng.randrange(2),rng.randrange(2)
        observed=(first^second if rng.random()<.86
                  else 1-(first^second))
    else:
        state=rng.randrange(2)
        accuracy=.85 if family==FIT_FAMILIES[0] else .82
        observed=state if rng.random()<accuracy else 1-state
    rows=[]
    for _ in range(STEPS):
        action=rng.randrange(2)
        if family==FIT_FAMILIES[0]:
            if rng.random()<(.66 if action else .06):
                state^=1
            bit=state
            accuracy=.85
        elif family==FIT_FAMILIES[1]:
            if rng.random()<(.64 if previous_action==1 and action==0 else .10):
                state^=1
            bit=state
            accuracy=.82
        elif family=="XFER_C_THREE_STATE_CYCLE":
            if rng.random()<.88:
                state=(state+(1 if action==0 else 2))%3
            bit=int(state==2)
            accuracy=.90
        else:
            if rng.random()<.72:
                if action==0:
                    first^=1
                else:
                    second^=1
            bit=first^second
            accuracy=.86
        following=bit if rng.random()<accuracy else 1-bit
        rows.append((observed,action,following))
        observed=following
        previous_action=action
    return tuple(rows)


def episodes(role,family):
    count=ROLE_COUNTS.get(role,{}).get(family)
    if count is None:
        raise SourceCustodyRefused("O14_FIT_ON_TRANSFER_DISALLOWED")
    return tuple(episode(role,family,i) for i in range(count))


def role_digest(rows):
    return hashlib.sha256(canonical(rows)).hexdigest()


def interleaved_fit(role):
    if role not in ("O14_FIT_TRAIN","O14_FIT_SELECT"):
        raise SourceCustodyRefused("O14_ONLY_FIT_SELECT")
    a=episodes(role,FIT_FAMILIES[0])
    b=episodes(role,FIT_FAMILIES[1])
    return tuple(ep for pair in zip(a,b) for ep in pair)
