"""F124-DB SOURCE-FREE meta-training and structural holdout author.

Separate source-only data author. Learners receive public episodes, not
private templates, meta-task operator IDs, task family or hidden grammar.
All prior authentic original research families (924..937) remain untouched.
"""
from __future__ import annotations
import copy
import random

ROLES=("alpha","beta","gamma")
FAMILIES=("nested-additive-new-graph","nested-xor-new-graph")
SEEDS=(61,62,63,64)
MASK=15

def need(ok,why):
    if not ok:raise ValueError("F124DB_SOURCE_"+why)

def law(op,tc,tl,sc,sl,event):
    A=(tc+sc)&MASK
    B=tl^event
    if op==0:return A
    if op==1:return B
    if op==2:return (A+B)&MASK       # New heldout topology only
    if op==3:return A^B             # Other new heldout topology
    raise ValueError("PRIVATE_UNADMITTED_SOURCE_OPERATOR")

def episode(rng,secret_operator):
    init={r:[rng.randrange(16),rng.randrange(16)] for r in ROLES}
    state=copy.deepcopy(init)
    events=[]
    for _ in range(8):
        t=rng.choice(ROLES)
        src=rng.choice([s for s in ROLES if s!=t])
        e=rng.randrange(16)
        tc,tl=state[t];sc,sl=state[src]
        y=law(secret_operator,tc,tl,sc,sl,e)
        events.append({"target":t,"source":src,"event":e,"observed":y})
        state[t]=[y,tc]
    return {"initial":init,"events":events}

def meta_training():
    # Two independently observed causal operators recurring on 12 training
    # tasks. Learner sees no operation labels, only complete public FIT.
    result=[]
    for i in range(12):
        rng=random.Random(1247700+1049*i)
        private=0 if i%2==0 else 1
        result.append([episode(rng,private) for _ in range(24)])
    return result

def heldout(family,seed):
    need(family in FAMILIES and type(seed) is int and seed in SEEDS,
         "FROZEN_STRUCTURAL_HELDOUT_ROSTER")
    private=2 if family==FAMILIES[0] else 3
    rng=random.Random(1248800+277*seed+FAMILIES.index(family)*39119)
    return {"FIT":[episode(rng,private) for _ in range(24)],
            "CHECK":[episode(rng,private) for _ in range(8)],
            "HELDOUT":[episode(rng,private) for _ in range(8)]}

def hard_negative(ep):
    out=copy.deepcopy(ep)
    ev=out["events"]
    pair=next(((i,j) for i in range(8) for j in range(i+1,8)
        if ev[i]["target"]!=ev[j]["target"] and
        ev[i]["observed"]!=ev[j]["observed"]),None)
    need(pair is not None,"UNAVAILABLE_CROSS_ROLE_NEGATIVE")
    i,j=pair
    ev[i]["observed"],ev[j]["observed"]=ev[j]["observed"],ev[i]["observed"]
    need(sorted(x["observed"] for x in ep["events"])==
         sorted(x["observed"] for x in out["events"]),
         "MATCHED_OBSERVATION_MULTISET")
    return out
