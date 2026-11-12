"""O10 fresh public role births: noisy delayed cue, resettable parity, iid null.

At t0 o0 is a public cue bit. At nonquery times the next observation is
independent fair distraction, and public action is 0,1 or 3 (reset).
At query action=2, the next public bit depends only on initial public cue,
resettable parity of publicly seen action=1, and independent 0.05 label noise.
No source label or privileged hidden state reaches any fitted learner.
"""
import hashlib
import json
import random

NAMESPACE="o10-public-reset-parity-v1"
ROLES=("O10_PUBLIC_TRAIN","O10_PUBLIC_SELECT","O10_PUBLIC_DEV")
FAMILIES=("ECHO_WITH_RESETS","RESETTABLE_PARITY","NULL_IID")
COUNTS={"O10_PUBLIC_TRAIN":64,"O10_PUBLIC_SELECT":16,"O10_PUBLIC_DEV":24}
STEPS=32
QUERY_TIMES=(14,26)

class PublicSourceRefused(ValueError):
    pass

def canonical(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=True,
                      allow_nan=False,separators=(",",":")).encode("ascii")

def seed(role,family,index):
    if not(type(role) is str and role in ROLES and
           type(family) is str and family in FAMILIES and
           type(index) is int and 0<=index<COUNTS[role]):
        raise PublicSourceRefused("O10_PROTECTED_OR_MALFORMED_SOURCE_ID")
    b=f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(b).digest()[:8],"big")

def episode(role,family,index):
    rng=random.Random(seed(role,family,index))
    cue=rng.randrange(2)
    query_t=QUERY_TIMES[rng.randrange(len(QUERY_TIMES))]
    obs=cue
    parity=0
    rows=[]
    for t in range(STEPS):
        action=2 if t==query_t else (0,1,3)[rng.randrange(3)]
        if action==2:
            nxt=(rng.randrange(2) if family=="NULL_IID" else
                 (cue if family=="ECHO_WITH_RESETS" else cue^parity))
            if family!="NULL_IID" and rng.random()<0.05:
                nxt ^= 1
        else:
            nxt=rng.randrange(2)
        rows.append((obs,action,nxt))
        if action==3:
            parity=0
        elif action==1:
            parity ^= 1
        obs=nxt
    return tuple(rows)

def all_public(role,family):
    if role not in ROLES or family not in FAMILIES:
        raise PublicSourceRefused("O10_RESERVED_SOURCE_ROLE")
    return tuple(episode(role,family,i) for i in range(COUNTS[role]))

def digest(batch):
    return hashlib.sha256(canonical(batch)).hexdigest()

def query_info(ep):
    if (type(ep) not in (tuple,list) or len(ep)!=STEPS or
        any(type(row) not in (tuple,list) or len(row)!=3 or
            type(row[0]) is not int or row[0] not in (0,1) or
            type(row[1]) is not int or row[1] not in (0,1,2,3) or
            type(row[2]) is not int or row[2] not in (0,1)
            for row in ep)):
        raise ValueError("O10_PUBLIC_INPUT_SHAPE")
    if any(ep[i][2]!=ep[i+1][0] for i in range(STEPS-1)):
        raise ValueError("O10_BROKEN_PUBLIC_CHAIN")
    queries=[i for i,row in enumerate(ep) if row[1]==2]
    if len(queries)!=1 or queries[0] not in QUERY_TIMES:
        raise ValueError("O10_QUERY_POSITION_DRIFT")
    t=queries[0]
    parity=0
    for _,a,_ in ep[:t]:
        if a==3:
            parity=0
        elif a==1:
            parity ^= 1
    return {"cue":ep[0][0],"parity":parity,
            "query_t":t,"query_observation":ep[t][0],"target":ep[t][2]}
