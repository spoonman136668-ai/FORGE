"""O10 independent fresh public delayed-query source; NO protected roles.

Every sample is a 36-step public (observation, action, next observation)
sequence. Cue and action parity are learnable from only past publicly
observed data. Query answer is withheld until after current prediction.
"""
import hashlib
import json
import random

NAMESPACE="o10-fresh-public-v1"
ROLES=("O10_PUBLIC_TRAIN","O10_PUBLIC_SELECT","O10_PUBLIC_DEV")
FAMILIES=("ECHO","PARITY","NULL")
COUNTS={"O10_PUBLIC_TRAIN":96,"O10_PUBLIC_SELECT":24,"O10_PUBLIC_DEV":32}
STEPS=36
QUERY_TIMES=(14,26)


class SourceIdentityRejected(ValueError):
    pass


def canonical(data):
    return json.dumps(data,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False).encode("ascii")


def seed(role,family,index):
    if not (type(role) is str and role in ROLES and type(family) is str
            and family in FAMILIES and type(index) is int
            and 0<=index<COUNTS[role]):
        raise SourceIdentityRejected("O10_UNREGISTERED_OR_PROTECTED_SOURCE")
    buf=f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(buf).digest()[:8],"big")


def episode(role,family,index):
    rnd=random.Random(seed(role,family,index))
    cue=rnd.randrange(2)
    query_t=QUERY_TIMES[rnd.randrange(2)]
    observed=cue
    parity=0
    rows=[]
    for t in range(STEPS):
        action=2 if t==query_t else rnd.randrange(2)
        if t==query_t:
            if family=="NULL":
                nxt=rnd.randrange(2)
            else:
                nxt=cue^(parity if family=="PARITY" else 0)
                if rnd.random()<0.05:
                    nxt^=1
        else:
            nxt=rnd.randrange(2)
        rows.append((observed,action,nxt))
        if action==1:
            parity^=1
        observed=nxt
    return tuple(rows)


def public_episodes(role,family):
    if role not in ROLES or family not in FAMILIES:
        raise SourceIdentityRejected("O10_PROTECTED_ROLE")
    return tuple(episode(role,family,i) for i in range(COUNTS[role]))


def source_digest(public):
    return hashlib.sha256(canonical(public)).hexdigest()


def query_info(ep):
    if (type(ep) not in (tuple,list) or len(ep)!=STEPS or
        any(type(row) not in (tuple,list) or len(row)!=3 or
            type(row[0]) is not int or row[0] not in (0,1) or
            type(row[1]) is not int or row[1] not in (0,1,2) or
            type(row[2]) is not int or row[2] not in (0,1)
            for row in ep)):
        raise ValueError("O10_INVALID_PUBLIC_EPISODE")
    if any(ep[i][2]!=ep[i+1][0] for i in range(STEPS-1)):
        raise ValueError("O10_PUBLIC_HISTORY_CHAIN")
    queries=[i for i,r in enumerate(ep) if r[1]==2]
    if len(queries)!=1 or queries[0] not in QUERY_TIMES:
        raise ValueError("O10_WRONG_QUERY")
    q=queries[0]
    parity=sum(r[1]==1 for r in ep[:q])%2
    return {"cue":ep[0][0],"parity":parity,"query_t":q,
            "query_observation":ep[q][0],"target":ep[q][2]}
