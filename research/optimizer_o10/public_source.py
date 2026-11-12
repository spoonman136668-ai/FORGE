"""O10 fresh synthetic public composition and iid-null sources.

All learning inputs are public (o_t, a_t); only query labels after prediction
may supervise TRAIN. Query role and source family NEVER enter learner features.
"""
import hashlib
import json
import random

NAMESPACE="o10-20261023-public-compose-v1"
FAMILIES=("A_CUE0_ACTION_COMPOSE","B_CUE4_ACTION_COMPOSE",
          "C_SELECTED_CUE_ACTION_COMPOSE","NULL_IID_QUERY")
ROLES=("O10_TRAIN","O10_SELECT","O10_DEV")
ROLE_COUNTS={"O10_TRAIN":96,"O10_SELECT":24,"O10_DEV":32}
STEPS=24
QUERY_TIMES=(10,18)


class UnauthorizedPublicSource(ValueError):
    pass


def canonical(value):
    return json.dumps(value,sort_keys=True,allow_nan=False,
                      ensure_ascii=True,separators=(",",":")).encode("ascii")


def seed(role,family,index):
    if not (type(role) is str and role in ROLES and type(family) is str
            and family in FAMILIES and type(index) is int
            and 0 <= index < ROLE_COUNTS[role]):
        raise UnauthorizedPublicSource("O10_PROTECTED_ROLE_OR_INVALID_SOURCE")
    s=f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(s).digest()[:8],"big")


def episode(role,family,index):
    rng=random.Random(seed(role,family,index))
    q=QUERY_TIMES[rng.randrange(2)]
    cue0=rng.randrange(2)
    cue4=rng.randrange(2)
    selector=rng.randrange(2)
    current=cue0
    parity=0
    rows=[]
    for t in range(STEPS):
        action=2 if t==q else (selector if t==q-1 else rng.randrange(2))
        if t==q:
            if family=="NULL_IID_QUERY":
                nxt=rng.randrange(2)
            else:
                value=(cue0 if family=="A_CUE0_ACTION_COMPOSE" else
                       cue4 if family=="B_CUE4_ACTION_COMPOSE" else
                       cue0 if selector==0 else cue4)
                nxt=value ^ parity
                if rng.random()<.05:
                    nxt^=1
        else:
            nxt=cue4 if t==3 else rng.randrange(2)
        rows.append((current,action,nxt))
        if t<q and action==1:
            parity^=1
        current=nxt
    return tuple(rows)


def public_episodes(role,family):
    if role not in ROLES or family not in FAMILIES:
        raise UnauthorizedPublicSource("O10_ROLE_NOT_PUBLIC")
    return tuple(episode(role,family,i) for i in range(ROLE_COUNTS[role]))


def digest(batch):
    return hashlib.sha256(canonical(batch)).hexdigest()


def query_info(ep):
    if type(ep) not in (tuple,list) or len(ep)!=STEPS:
        raise ValueError("O10_INVALID_EPISODE_LENGTH")
    for row in ep:
        if type(row) not in (tuple,list) or len(row)!=3 or any(
                type(x) is not int for x in row) or row[0] not in (0,1) or \
                row[1] not in (0,1,2) or row[2] not in (0,1):
            raise ValueError("O10_PUBLIC_ONLY_BINARY_INPUT")
    if any(ep[t][2]!=ep[t+1][0] for t in range(STEPS-1)):
        raise ValueError("O10_BROKEN_PUBLIC_CHAIN")
    q_positions=[t for t,x in enumerate(ep) if x[1]==2]
    if len(q_positions)!=1 or q_positions[0] not in QUERY_TIMES:
        raise ValueError("O10_BAD_QUERY_TIME")
    q=q_positions[0]
    n1=sum(row[1]==1 for row in ep[:q])
    return {
        "query_t":q,"cue":ep[0][0],"cue4":ep[4][0],
        "selector":ep[q-1][1],"parity":n1%2,
        "n1":n1,"n0":q-n1,
        "query_observation":ep[q][0],"target":ep[q][2],
    }
