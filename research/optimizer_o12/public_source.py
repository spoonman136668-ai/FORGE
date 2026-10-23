"""O12 fresh source for numerical engineering diagnostics ONLY.

No O10/O11 SELECT or DEV, no Q21/HELD/FSA use. The only learner
inputs are public (observation, action) histories; query supervision
is available during fit of O12_TRAIN, after the pretarget prediction.
"""
import hashlib
import json
import random

NAMESPACE="o12-20261023-fixeddecimal-trainonly-v1"
FAMILIES=("A_CUE0_COMPOSE","B_CUE4_COMPOSE","C_SELECTOR_COMPOSE","NULL_IID")
ROLES=("O12_TRAIN","O12_TRAIN_DIAGNOSTIC")
COUNTS={"O12_TRAIN":48,"O12_TRAIN_DIAGNOSTIC":8}
STEPS=24
QUERIES=(10,18)


class UnauthorizedSource(ValueError):
    pass


def canonical(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=True,allow_nan=False,
                      separators=(",",":")).encode("ascii")


def seed(role,family,index):
    if not (type(role) is str and role in ROLES and
            type(family) is str and family in FAMILIES and
            type(index) is int and 0 <= index < COUNTS[role]):
        raise UnauthorizedSource("O12_UNAUTHORIZED_OR_PROTECTED_SOURCE_ROLE")
    h=hashlib.sha256(f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")).digest()
    return int.from_bytes(h[:8],"big")


def public_episode(role,family,index):
    rng=random.Random(seed(role,family,index))
    q=QUERIES[rng.randrange(2)]
    cue0=rng.randrange(2)
    cue4=rng.randrange(2)
    selector=rng.randrange(2)
    observed=cue0
    parity=0
    rows=[]
    for t in range(STEPS):
        action=2 if t==q else selector if t==q-1 else rng.randrange(2)
        if t==q:
            if family=="NULL_IID":
                next_observation=rng.randrange(2)
            else:
                cue=(cue0 if family=="A_CUE0_COMPOSE" else
                     cue4 if family=="B_CUE4_COMPOSE" else
                     cue0 if selector==0 else cue4)
                next_observation=cue ^ parity
                if rng.random()<0.05:
                    next_observation^=1
        else:
            next_observation=cue4 if t==3 else rng.randrange(2)
        rows.append((observed,action,next_observation))
        if t<q and action==1:
            parity^=1
        observed=next_observation
    return tuple(rows)


def role_batch(role,family):
    if type(role) is not str or role not in ROLES or family not in FAMILIES:
        raise UnauthorizedSource("O12_UNAUTHORIZED_ROLE")
    return tuple(public_episode(role,family,i) for i in range(COUNTS[role]))


def digest(batch):
    return hashlib.sha256(canonical(batch)).hexdigest()


def query_info(ep):
    if type(ep) not in (tuple,list) or len(ep)!=STEPS:
        raise ValueError("O12_PUBLIC_EPISODE_LENGTH")
    for row in ep:
        if type(row) not in (tuple,list) or len(row)!=3 or \
                any(type(x) is not int for x in row) or \
                row[0] not in (0,1) or row[1] not in (0,1,2) or \
                row[2] not in (0,1):
            raise ValueError("O12_PUBLIC_ONLY_BINARY_OBSERVATION")
    if any(ep[t][2]!=ep[t+1][0] for t in range(STEPS-1)):
        raise ValueError("O12_BROKEN_OBSERVATION_CHAIN")
    qs=[t for t,(_,a,_) in enumerate(ep) if a==2]
    if len(qs)!=1 or qs[0] not in QUERIES:
        raise ValueError("O12_BAD_PUBLIC_QUERY")
    q=qs[0]
    n1=sum(action==1 for _,action,_ in ep[:q])
    return {"query_t":q,"cue":ep[0][0],"cue4":ep[4][0],
            "selector":ep[q-1][1],"n1":n1,"n0":q-n1,
            "parity":n1%2,"query_observation":ep[q][0],
            "target":ep[q][2]}
