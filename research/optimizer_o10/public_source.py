"""O10 paired public causal interventions, with shared distractors and noise.

The learner receives ONLY the public 36-step triples (o_t, action, o_t+1).
Paired episodes share all noise draws. Each twin changes an early public
cue or action, causally affecting the delayed query target where appropriate.
No scientific original/HELD sources or hidden model labels are accessible.
"""
import hashlib
import json
import random

NAMESPACE="o10-public-paired-v1"
FAMILIES=("CUE_RECALL","ACTION_PARITY","NULL_NO_EFFECT")
ROLES=("O10_TRAIN","O10_SELECT","O10_DEV")
COUNTS={"O10_TRAIN":96,"O10_SELECT":24,"O10_DEV":32}
STEPS=36
QUERY_TIMES=(14,26)
ACTION_INTERVENTION=4


class RoleRefused(ValueError):
    pass


def canonical(data):
    return json.dumps(data,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False).encode("ascii")


def seed(role,family,index):
    if (type(role) is not str or role not in ROLES or
            type(family) is not str or family not in FAMILIES or
            type(index) is not int or index<0 or index>=COUNTS[role]):
        raise RoleRefused("O10_PROTECTED_OR_UNREGISTERED_ROLE_REFUSED")
    body=f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(body).digest()[:8],"big")


def episode(role,family,index,intervened=False):
    if type(intervened) is not bool:
        raise ValueError("O10_INTERVENTION_MUST_BE_BOOLEAN")
    rnd=random.Random(seed(role,family,index))
    cue=rnd.randrange(2)
    query_t=QUERY_TIMES[rnd.randrange(2)]
    actions=[2 if t==query_t else rnd.randrange(2) for t in range(STEPS)]
    distracting_bits=[rnd.randrange(2) for _ in range(STEPS)]
    shared_query_noise=int(rnd.random()<0.05)
    null_target=rnd.randrange(2)

    if intervened:
        if family=="ACTION_PARITY":
            actions[ACTION_INTERVENTION]^=1
        else:
            cue^=1

    parity=sum(a==1 for a in actions[:query_t])%2
    if family=="CUE_RECALL":
        delayed_answer=cue^shared_query_noise
    elif family=="ACTION_PARITY":
        delayed_answer=cue^parity^shared_query_noise
    else:
        delayed_answer=null_target

    observed=cue
    rows=[]
    for t in range(STEPS):
        nxt=(delayed_answer if t==query_t else distracting_bits[t])
        rows.append((observed,actions[t],nxt))
        observed=nxt
    return tuple(rows)


def paired(role,family,index):
    return (episode(role,family,index,False),
            episode(role,family,index,True))


def pairs_for_role(role,family):
    if role not in ROLES or family not in FAMILIES:
        raise RoleRefused("O10_PROTECTED_SOURCE_ROLE_REFUSED")
    return tuple(paired(role,family,i) for i in range(COUNTS[role]))


def role_digest(pairs):
    return hashlib.sha256(canonical(pairs)).hexdigest()


def query_info(ep):
    if (type(ep) not in (tuple,list) or len(ep)!=STEPS or any(
            type(row) not in (tuple,list) or len(row)!=3 or
            type(row[0]) is not int or row[0] not in (0,1) or
            type(row[1]) is not int or row[1] not in (0,1,2) or
            type(row[2]) is not int or row[2] not in (0,1)
            for row in ep)):
        raise ValueError("O10_PUBLIC_EPISODE_SCHEMA")
    if any(ep[t][2]!=ep[t+1][0] for t in range(STEPS-1)):
        raise ValueError("O10_PUBLIC_HISTORY_CHAIN_INVALID")
    query=[t for t,row in enumerate(ep) if row[1]==2]
    if len(query)!=1 or query[0] not in QUERY_TIMES:
        raise ValueError("O10_QUERY_SHAPE_INVALID")
    t=query[0]
    parity=sum(row[1]==1 for row in ep[:t])%2
    return {"cue":ep[0][0],"parity":parity,"query_t":t,
            "query_observation":ep[t][0],"target":ep[t][2]}
