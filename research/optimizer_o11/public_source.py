"""O11 NEW, TRAINING-ONLY source (never reads O10 TRAIN/SELECT/DEV).

Copying the *shape* of the public causal source does not copy its episode
identity; every episode is born from a fresh O11 namespace. Hidden simulator
information and source family identifiers never enter any model features.
"""
import hashlib
import json
import random

NAMESPACE="o11-determinism-training-probe-v1"
FAMILIES=("A_CUE0_COMPOSE","B_CUE4_COMPOSE","C_SELECTOR_COMPOSE","NULL_IID")
ROLES=("O11_DIAG_TRAIN",)
COUNT=96
STEPS=24
QUERY_TIMES=(10,18)


class UnauthorizedSource(ValueError):
    pass


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,
                      separators=(",",":")).encode("ascii")


def seed(role,family,index):
    if not (type(role) is str and role in ROLES
            and type(family) is str and family in FAMILIES
            and type(index) is int and 0<=index<COUNT):
        raise UnauthorizedSource("O11_NOT_PUBLIC_TRAIN")
    h=hashlib.sha256(f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")).digest()
    return int.from_bytes(h[:8],"big")


def public_episode(role,family,index):
    rng=random.Random(seed(role,family,index))
    query=QUERY_TIMES[rng.randrange(2)]
    first=rng.randrange(2)
    fourth=rng.randrange(2)
    selector=rng.randrange(2)
    obs=first
    parity=0
    result=[]
    for t in range(STEPS):
        action=(2 if t==query else
                selector if t==query-1 else rng.randrange(2))
        if t==query:
            if family=="NULL_IID":
                next_observation=rng.randrange(2)
            else:
                cue=(first if family=="A_CUE0_COMPOSE" else
                     fourth if family=="B_CUE4_COMPOSE" else
                     first if selector==0 else fourth)
                next_observation=cue^parity
                if rng.random()<.05:
                    next_observation^=1
        else:
            next_observation=fourth if t==3 else rng.randrange(2)
        result.append((obs,action,next_observation))
        if t<query and action==1:
            parity^=1
        obs=next_observation
    return tuple(result)


def public_train(family):
    if family not in FAMILIES:
        raise UnauthorizedSource("O11_UNKNOWN_TRAIN_FAMILY")
    return tuple(public_episode(ROLES[0],family,i) for i in range(COUNT))


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def query_info(ep):
    if type(ep) not in (tuple,list) or len(ep)!=STEPS:
        raise ValueError("O11_PUBLIC_EPISODE_LENGTH")
    if any(type(row) not in (tuple,list) or len(row)!=3 or
           any(type(x) is not int for x in row) or
           row[0] not in (0,1) or row[1] not in (0,1,2) or
           row[2] not in (0,1) for row in ep):
        raise ValueError("O11_PUBLIC_BINARY_SCHEMA")
    if any(ep[t][2]!=ep[t+1][0] for t in range(STEPS-1)):
        raise ValueError("O11_SOURCE_OBSERVATION_CHAIN")
    indices=[i for i,(_,a,_) in enumerate(ep) if a==2]
    if len(indices)!=1 or indices[0] not in QUERY_TIMES:
        raise ValueError("O11_PUBLIC_QUERY_POSITION")
    q=indices[0]
    n1=sum(a==1 for _,a,_ in ep[:q])
    return {"query_t":q,"cue":ep[0][0],"cue4":ep[4][0],
            "selector":ep[q-1][1],"n1":n1,"n0":q-n1,
            "parity":n1%2,"query_observation":ep[q][0],
            "target":ep[q][2]}
