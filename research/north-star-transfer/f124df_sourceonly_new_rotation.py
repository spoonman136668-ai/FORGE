"""F124-DF independently authored fresh source-only rotation identification cases.

The source-only model is NEVER imported by either frozen F124-DE learner.
Truth wiring can be disclosed only for AFTER-FIT forensic classification.
No original 91..94 sourcefree holdout or authenticated scientific original.
"""
from __future__ import annotations
import copy
import random
ROLES=("alpha","beta","gamma")
FAMILIES=("rotated-modular-add-unfamiliar","rotated-modular-add-role-switch",
          "plain-modular-add-control","three-register-arithmetic-out-of-class")
SEEDS=(101,102,103,104)
def need(ok,why):
    if not ok:raise ValueError("F124DF_SOURCE_"+why)
def wiring(family,seed):
    need(family in FAMILIES and type(seed) is int and seed in SEEDS,
         "EXACT_NEW_SOURCEFREE_ROSTER")
    idx=SEEDS.index(seed)
    table=(
      ((0,2),(1,4),(0,3),(2,4)),
      ((0,4),(1,2),(0,3),(2,4)),
      ((0,2),(1,4),(2,3),(0,4)),
      ((0,2,4),(1,2,3),(0,1,4),(2,3,4))
    )
    return tuple(table[FAMILIES.index(family)][idx])
def private_operator(family,raw,slots):
    if family==FAMILIES[-1]:
        a,b,c=(raw[i] for i in slots)
        return (a+b+c)&15
    a,b=(raw[i] for i in slots)
    summed=(a+b)&15
    if family==FAMILIES[0]:
        return ((summed<<1)|(summed>>3))&15
    if family==FAMILIES[1]:
        return ((summed<<2)|(summed>>2))&15
    return summed
def episode(rng,family,slots):
    state={k:[rng.randrange(16),rng.randrange(16)] for k in ROLES}
    initial=copy.deepcopy(state);events=[]
    for i in range(8):
        t=rng.choice(ROLES)
        s=rng.choice([name for name in ROLES if name!=t])
        ev=rng.randrange(16)
        own=state[t];foreign=state[s]
        result=private_operator(family,(own[0],own[1],foreign[0],foreign[1],ev),slots)
        events.append({"target":t,"source":s,"event":ev,"observed":result})
        state[t]=[result,own[0]]
    return {"initial":initial,"events":events}
def birth(family,seed):
    slots=wiring(family,seed)
    rng=random.Random(2391147+seed*499+FAMILIES.index(family)*31991)
    FIT=[episode(rng,family,slots) for _ in range(24)]
    CHECK=[episode(rng,family,slots) for _ in range(8)]
    HELDOUT=[]
    for i in range(8):
        for attempt in range(128):
            x=episode(rng,family,slots)
            e=x["events"]
            if any(e[j]["target"]!=e[k]["target"] and
                   e[j]["observed"]!=e[k]["observed"]
                   for j in range(8) for k in range(j+1,8)):
                HELDOUT.append(x)
                break
        else:
            raise RuntimeError("F124DF_SOURCE_NO_ELIGIBLE_HARD_NEGATIVE")
    return {"FIT":FIT,"CHECK":CHECK,"HELDOUT":HELDOUT}
def hard_negative(ep):
    new=copy.deepcopy(ep)
    old=new["events"]
    pair=next(((i,j) for i in range(8) for j in range(i+1,8)
             if old[i]["target"]!=old[j]["target"] and
             old[i]["observed"]!=old[j]["observed"]),None)
    need(pair is not None,"OUTPUT_SWAP_NOT_ELIGIBLE")
    i,j=pair
    old[i]["observed"],old[j]["observed"]=old[j]["observed"],old[i]["observed"]
    need(sorted(e["observed"] for e in old)==
         sorted(e["observed"] for e in ep["events"]),"NEGATIVE_OUTPUT_INVENTORY_CHANGED")
    return new
