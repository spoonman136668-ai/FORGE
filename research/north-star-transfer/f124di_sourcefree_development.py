"""F124-DI DEVELOPMENT ONLY synthetic causal episodes, not scientific first-use.

Unseen source family labels and hidden wiring are NEVER model inputs.
These development seeds are consumed when CI executes; do not reuse
as a future untouched prospective validation cohort.
"""
from __future__ import annotations
import copy
import random

ROLES=("alpha","beta","gamma")
FAMILIES=("two_register_add_carry","two_register_rotate_and_add",
          "non_arithmetic_bitwise_boolean","three_register_outside_model")
SEEDS=(701,702,703,704)

def source_step(kind,raw,wires):
    a,b=(raw[i] for i in wires[:2])
    if kind==FAMILIES[0]:return (a+b)&15
    if kind==FAMILIES[1]:
        v=(a+b)&15
        return ((v<<1)|(v>>3))&15
    if kind==FAMILIES[2]:return ((a^b)^(a&b))&15
    if kind==FAMILIES[3]:return (a+b+raw[wires[2]])&15
    raise ValueError("SOURCE_OPERATOR_ID")

def episode(rng,kind,wires):
    state={r:[rng.randrange(16),rng.randrange(16)] for r in ROLES}
    first=copy.deepcopy(state)
    events=[]
    for _ in range(8):
        t=rng.choice(ROLES)
        src=rng.choice([r for r in ROLES if r!=t])
        ev=rng.randrange(16)
        own=state[t];other=state[src]
        y=source_step(kind,(own[0],own[1],other[0],other[1],ev),wires)
        events.append({"target":t,"source":src,"event":ev,"observed":y})
        state[t]=[y,own[0]]
    return {"initial":first,"events":events}

def development(kind,seed):
    if kind not in FAMILIES or type(seed) is not int or seed not in SEEDS:
        raise ValueError("F124DI_DEVELOPMENT_FIXED_ROSTER_ONLY")
    i=SEEDS.index(seed)
    w=( ((0,2),(1,4),(2,3),(0,4)),
        ((0,3),(1,2),(2,4),(0,2)),
        ((0,4),(1,3),(2,4),(0,2)),
        ((0,2,4),(1,2,3),(0,1,4),(2,3,4)))[FAMILIES.index(kind)][i]
    rng=random.Random(6602140+seed*1009+FAMILIES.index(kind)*20063)
    fit=[episode(rng,kind,w) for _ in range(24)]
    check=[episode(rng,kind,w) for _ in range(8)]
    held=[]
    for _ in range(8):
        for attempt in range(128):
            x=episode(rng,kind,w)
            e=x["events"]
            if any(e[j]["target"]!=e[k]["target"] and
                   e[j]["observed"]!=e[k]["observed"]
                   for j in range(8) for k in range(j+1,8)):
                held.append(x);break
        else:raise RuntimeError("SOURCEONLY_MATCHED_NEGATIVE_INELIGIBLE")
    return {"FIT":fit,"CHECK":check,"HELDOUT":held}

def matched_negative(ep):
    other=copy.deepcopy(ep);e=other["events"]
    pair=next(((i,j) for i in range(8) for j in range(i+1,8)
               if e[i]["target"]!=e[j]["target"]
               and e[i]["observed"]!=e[j]["observed"]),None)
    if pair is None:raise ValueError("SOURCE_ONLY_NONELIGIBLE_HARD_NEGATIVE")
    i,j=pair
    e[i]["observed"],e[j]["observed"]=e[j]["observed"],e[i]["observed"]
    return other
