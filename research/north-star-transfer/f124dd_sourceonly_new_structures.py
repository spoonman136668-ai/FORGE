"""F124-DD SOURCE-ONLY synthetic operator task birth, separate from learners.

Fresh seeds and worlds; no F124-DC heldout tasks or original scientific
sources are used. Hidden arity/primitive/wiring stays in this file. Model
inputs are the returned public FIT/CHECK/HELDOUT trajectories alone.
Internally authored engineering tasks != independent scientific first-use.
"""
from __future__ import annotations
import copy
import random
ROLES=("alpha","beta","gamma")
FAMILIES=("fresh-ternary-compiler-sanity","four-input-parity-conjunction","four-input-selector-with-interaction","nibble-addition-carry-out-of-bitwise")
SEEDS=(81,82,83,84)
def need(ok,msg):
    if not ok:raise ValueError("F124DD_AUTHOR_"+msg)

def step(inputs,kind,wires):
    if kind=="nand2":
        a,b=(inputs[i] for i in wires)
        return (~(a&b))&15
    if kind=="xor2":
        a,b=(inputs[i] for i in wires)
        return a^b
    if kind=="and2":
        a,b=(inputs[i] for i in wires)
        return a&b
    if kind=="ternary":
        a,b,c=(inputs[i] for i in wires)
        # New source-specific nested bitwise law, not reusing DC tasks.
        return (a ^ b ^ (a&b&c))&15
    if kind=="quartic-parity":
        a,b,c,d=(inputs[i] for i in wires)
        return (a^b^c^d^(a&b&c&d))&15
    if kind=="quartic-selector":
        a,b,c,d=(inputs[i] for i in wires)
        return ((a&b)|((~a)&c))^((a&d)&15)
    if kind=="carry":
        tc,tl,sc,sl,event=inputs
        return (((tc+sc+event)&15)^((tl+sl)&15))&15
    raise ValueError("FORBIDDEN_SOURCE_KIND")

def episode(rng,kind,wires):
    mem={k:[rng.randrange(16),rng.randrange(16)] for k in ROLES}
    initial=copy.deepcopy(mem);events=[]
    for t in range(8):
        dest=rng.choice(ROLES)
        source=rng.choice([k for k in ROLES if k!=dest])
        event=rng.randrange(16)
        own=mem[dest];foreign=mem[source]
        value=step((own[0],own[1],foreign[0],foreign[1],event),kind,wires)
        events.append({"target":dest,"source":source,"event":event,"observed":value})
        mem[dest]=[value,own[0]]
    return {"initial":initial,"events":events}

def meta_training():
    tasks=[]
    for i in range(12):
        rng=random.Random(17721000+1739*i)
        kind=("nand2","xor2","and2")[i%3]
        wires=((0,2),(1,4),(2,4))[i%3]
        tasks.append([episode(rng,kind,wires) for _ in range(24)])
    return tasks

def heldout(family,seed):
    need(family in FAMILIES and type(seed) is int and seed in SEEDS,
         "PREREGISTERED_SOURCEFREE_CASE_ONLY")
    famidx=FAMILIES.index(family)
    rng=random.Random(17722000+seed*941+famidx*101119)
    if famidx==0:kind="ternary";wires=((0,2,4),(0,3,4),(1,2,4),(1,3,4))[SEEDS.index(seed)]
    elif famidx==1:kind="quartic-parity";wires=((0,1,2,4),(0,2,3,4),(0,1,3,4),(1,2,3,4))[SEEDS.index(seed)]
    elif famidx==2:kind="quartic-selector";wires=((0,1,2,3),(1,2,3,4),(0,1,3,4),(0,2,3,4))[SEEDS.index(seed)]
    else:kind="carry";wires=()
    fit=[episode(rng,kind,wires) for _ in range(24)]
    check=[episode(rng,kind,wires) for _ in range(8)]
    hold=[]
    # Frozen first eligible per original source-only outcome inventory;
    # no candidate/model used in source selection.
    for _ in range(8):
        for attempt in range(128):
            e=episode(rng,kind,wires)
            items=e["events"]
            if any(items[i]["target"]!=items[j]["target"] and
                   items[i]["observed"]!=items[j]["observed"]
                   for i in range(8) for j in range(i+1,8)):
                hold.append(e);break
        else:raise ValueError("NO_HARD_NEGATIVE_ELIGIBLE_EPISODE")
    return {"FIT":fit,"CHECK":check,"HELDOUT":hold}

def hard_negative(positive):
    other=copy.deepcopy(positive)
    events=other["events"]
    pair=next(((i,j) for i in range(8) for j in range(i+1,8) if
             events[i]["target"]!=events[j]["target"] and
             events[i]["observed"]!=events[j]["observed"]),None)
    need(pair is not None,"MISSING_MATCHED_ROLE_DISTINCT_OUTPUTS")
    i,j=pair
    events[i]["observed"],events[j]["observed"]=events[j]["observed"],events[i]["observed"]
    need(sorted(e["observed"] for e in other["events"])==
         sorted(e["observed"] for e in positive["events"]),"OUTPUT_INVENTORY_DRIFT")
    return other
