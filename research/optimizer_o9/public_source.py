"""O9 completely new public-only long-delay write/read development source.

Public episodes comprise 36 tuples of (observation, action, next_observation).
The initial cue is the only relevant memory input. Intervening bits are
independent distractions. At one query action=2, the next public bit depends
on that cue and optionally all prior public actions. No latent information
is supplied beyond visible public inputs. No scientific/HELD role exists.
"""
from __future__ import annotations
import hashlib
import json
import random

NAMESPACE="o9-public-v1"
FAMILIES=("ECHO_DELAY","PARITY_DELAY","NULL_IID")
ROLES=("O9_PUBLIC_TRAIN","O9_PUBLIC_SELECT","O9_PUBLIC_DEV")
COUNTS={"O9_PUBLIC_TRAIN":96,"O9_PUBLIC_SELECT":24,"O9_PUBLIC_DEV":32}
STEPS=36
QUERY_TIMES=(14,26)


class ProtectedRoleRefused(ValueError):
    pass


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=True,
                      allow_nan=False,separators=(",",":")).encode("ascii")


def seed(role,family,index):
    if not (type(role) is str and role in ROLES
            and type(family) is str and family in FAMILIES
            and type(index) is int and 0 <= index < COUNTS[role]):
        raise ProtectedRoleRefused("O9_PROTECTED_ROLE_OR_UNREGISTERED_SOURCE")
    data=f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(data).digest()[:8],"big")


def episode(role,family,index):
    rnd=random.Random(seed(role,family,index))
    initial_cue=rnd.randrange(2)
    query_t=QUERY_TIMES[rnd.randrange(len(QUERY_TIMES))]
    observation=initial_cue
    action_parity=0
    public=[]
    for t in range(STEPS):
        action=2 if t==query_t else rnd.randrange(2)
        if t==query_t:
            if family=="NULL_IID":
                next_observation=rnd.randrange(2)
            else:
                next_observation=initial_cue
                if family=="PARITY_DELAY":
                    next_observation ^= action_parity
                if rnd.random()<0.05:
                    next_observation ^= 1
        else:
            next_observation=rnd.randrange(2)
        public.append((observation,action,next_observation))
        if action==1:
            action_parity ^= 1
        observation=next_observation
    return tuple(public)


def all_public(role,family):
    if role not in ROLES or family not in FAMILIES:
        raise ProtectedRoleRefused("O9_PROTECTED_SOURCE_ROLE")
    return tuple(episode(role,family,i) for i in range(COUNTS[role]))


def role_digest(batch):
    return hashlib.sha256(canonical(batch)).hexdigest()


def query_info(ep):
    if (type(ep) not in (tuple,list) or len(ep)!=STEPS
        or any(type(row) not in (tuple,list) or len(row)!=3
               or type(row[0]) is not int or row[0] not in (0,1)
               or type(row[1]) is not int or row[1] not in (0,1,2)
               or type(row[2]) is not int or row[2] not in (0,1)
               for row in ep)):
        raise ValueError("O9_INVALID_PUBLIC_EPISODE")
    if any(ep[i][2]!=ep[i+1][0] for i in range(STEPS-1)):
        raise ValueError("O9_DISCONNECTED_PUBLIC_EPISODE")
    positions=[i for i,row in enumerate(ep) if row[1]==2]
    if len(positions)!=1 or positions[0] not in QUERY_TIMES:
        raise ValueError("O9_INVALID_QUERY_ACTION")
    q=positions[0]
    parity=sum(int(row[1]==1) for row in ep[:q])%2
    return {"cue":ep[0][0],"parity":parity,"query_t":q,
            "query_observation":ep[q][0],"target":ep[q][2]}
