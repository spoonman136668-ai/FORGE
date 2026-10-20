"""F124-DE SOURCE-ONLY new causal laws; no prior source or learner import.

Two-nibble modular addition, rotation-after-addition, fresh cross-role
bitwise primitive, and a three-nibble negative outside the preregistered
eight-input-bit / degree<=4 function space. Every source type and wiring
is hidden from learner modules; all source-free engineering only.
"""
from __future__ import annotations
import copy
import random
ROLES=("alpha","beta","gamma")
FAMILIES=("novel-carry-nibble-add","novel-rotate-after-add","fresh-bitwise-crossrole-check","three-nibble-unseen-negative")
SEEDS=(91,92,93,94)
def need(ok,what):
    if not ok:raise ValueError("F124DE_SOURCE_"+what)
def private_step(family,wire,values):
    a=values[wire[0]];b=values[wire[1]]
    if family==FAMILIES[0]:return (a+b)&15
    if family==FAMILIES[1]:
        s=(a+b)&15
        return ((s<<1)|(s>>3))&15
    if family==FAMILIES[2]:
        return (a^b^(a&b))&15
    if family==FAMILIES[3]:
        c=values[wire[2]]
        return (a+b+c)&15
    raise ValueError("FORBIDDEN_OPERATOR_ID")
def born_episode(rng,family,wire):
    state={k:[rng.randrange(16),rng.randrange(16)] for k in ROLES}
    initial=copy.deepcopy(state)
    events=[]
    for i in range(8):
        target=rng.choice(ROLES)
        foreign=rng.choice([k for k in ROLES if k!=target])
        ev=rng.randrange(16)
        own=state[target];src=state[foreign]
        value=private_step(family,wire,(own[0],own[1],src[0],src[1],ev))
        events.append({"target":target,"source":foreign,"event":ev,"observed":value})
        state[target]=[value,own[0]]
    return {"initial":initial,"events":events}
def born(family,seed):
    need(family in FAMILIES and type(seed) is int and seed in SEEDS,
         "FROZEN_NEW_SYNTHETIC_SOURCE_ROSTER")
    rng=random.Random(2199123+seed*599+FAMILIES.index(family)*110123)
    idx=SEEDS.index(seed)
    if family==FAMILIES[0]:wire=((0,2),(1,4),(0,3),(2,4))[idx]
    elif family==FAMILIES[1]:wire=((0,4),(1,2),(0,3),(2,4))[idx]
    elif family==FAMILIES[2]:wire=((0,2),(1,3),(0,4),(2,4))[idx]
    else:wire=((0,2,4),(0,1,3),(1,2,4),(0,3,4))[idx]
    fit=[born_episode(rng,family,wire) for _ in range(24)]
    check=[born_episode(rng,family,wire) for _ in range(8)]
    heldout=[]
    for _ in range(8):
        for attempt in range(128):
            ep=born_episode(rng,family,wire)
            e=ep["events"]
            if any(e[i]["target"]!=e[j]["target"] and e[i]["observed"]!=e[j]["observed"]
                   for i in range(8) for j in range(i+1,8)):
                heldout.append(ep);break
        else:raise RuntimeError("NO_ELIGIBLE_SOURCE_ONLY_MATCHED_NEGATIVE")
    return {"FIT":fit,"CHECK":check,"HELDOUT":heldout}
def negative(ep):
    other=copy.deepcopy(ep)
    e=other["events"]
    ij=next(((i,j) for i in range(8) for j in range(i+1,8)
            if e[i]["target"]!=e[j]["target"] and e[i]["observed"]!=e[j]["observed"]),None)
    need(ij is not None,"CROSS_ROLE_NEGATIVE_NOT_ELIGIBLE")
    i,j=ij
    e[i]["observed"],e[j]["observed"]=e[j]["observed"],e[i]["observed"]
    need(sorted(row["observed"] for row in e)==
         sorted(row["observed"] for row in ep["events"]),"INVENTORY_MISMATCH")
    return other

def meta_training():
    # Extra independent PUBLIC supervision for historical DD control only:
    # not a source/model label and not any reused DD source cohort.
    tasks=[]
    for i in range(12):
        rng=random.Random(21990000+1297*i)
        gate=("meta_nand","meta_xor","meta_and")[i%3]
        wires=((0,2),(1,4),(2,4))[i%3]
        state_tasks=[]
        for _ in range(24):
            state={k:[rng.randrange(16),rng.randrange(16)] for k in ROLES}
            initial=copy.deepcopy(state);ev=[]
            for j in range(8):
                target=rng.choice(ROLES)
                source=rng.choice([k for k in ROLES if k!=target])
                event=rng.randrange(16)
                own=state[target];src=state[source]
                inputs=(own[0],own[1],src[0],src[1],event)
                a,bb=(inputs[k] for k in wires)
                value=(~(a&bb))&15 if gate=="meta_nand" else (
                      a^bb if gate=="meta_xor" else a&bb)
                ev.append({"target":target,"source":source,"event":event,"observed":value})
                state[target]=[value,own[0]]
            state_tasks.append({"initial":initial,"events":ev})
        tasks.append(state_tasks)
    return tasks
