"""F124-DC source-only, fully isolated synthetic structural-family author.

Meta training: 12 independently seeded pairwise binary Boolean causal laws.
Heldout: three-input MAJORITY and MUX, never in meta training, and an
out-of-grammar degree-four Boolean interaction (deliberate negative).
Hidden structural laws, input slots and family tags are NOT model inputs.
These are INTERNALLY authored synthetic tasks, not separately authenticated
external scientific sources. No prior original source IDs/holdouts read.
"""
from __future__ import annotations
import copy
import random

ROLES=("alpha","beta","gamma")
FAMILIES=("ternary-majority-unseen","ternary-selector-unseen","quartic-fourway-unseen")
SEEDS=(71,72,73,74)

def need(ok,reason):
    if not ok:raise RuntimeError("F124DC_SOURCE_"+reason)

def words(tcur,tlag,scur,slag,event):
    return (tcur,tlag,scur,slag,event)

def bitlaw(kind,input_positions,values):
    inputs=tuple(values[i] for i in input_positions)
    out=0
    for k in range(4):
        bits=tuple((v>>k)&1 for v in inputs)
        if kind=="nand2":x=1-(bits[0]&bits[1])
        elif kind=="xor2":x=bits[0]^bits[1]
        elif kind=="and2":x=bits[0]&bits[1]
        elif kind=="majority3":x=(bits[0]&bits[1])|(bits[0]&bits[2])|(bits[1]&bits[2])
        elif kind=="selector3":x=bits[1] if bits[0] else bits[2]
        elif kind=="quartic4":x=bits[0]^bits[1]^bits[2]^bits[3]^(bits[0]&bits[1]&bits[2]&bits[3])
        else:raise RuntimeError("SOURCE_UNKNOWN_LAW")
        out|=x<<k
    return out

def episode(rng,kind,wires):
    state={r:[rng.randrange(16),rng.randrange(16)] for r in ROLES}
    initial=copy.deepcopy(state)
    events=[]
    for step in range(8):
        t=rng.choice(ROLES)
        source=rng.choice([r for r in ROLES if r!=t])
        event=rng.randrange(16)
        tc,tl=state[t];sc,sl=state[source]
        y=bitlaw(kind,wires,words(tc,tl,sc,sl,event))
        events.append({"target":t,"source":source,"event":event,"observed":y})
        state[t]=[y,tc]
    return {"initial":initial,"events":events}

def meta_training():
    tasks=[]
    for i in range(12):
        rng=random.Random(1249910+i*1823)
        kind=("nand2","xor2","and2")[i%3]
        wires=((0,2),(1,4),(2,4))[i%3]
        tasks.append([episode(rng,kind,wires) for _ in range(24)])
    return tasks

def heldout(family,seed):
    need(family in FAMILIES and type(seed) is int and seed in SEEDS,
         "ONLY_PREREGISTERED_SOURCEFREE_HOLDOUT")
    rng=random.Random(1249933+seed*577+FAMILIES.index(family)*65413)
    if family==FAMILIES[0]:
        kind="majority3"
        # New input-role wiring each seed; all 3 participate.
        wires=[(0,2,4),(0,3,4),(1,2,4),(1,3,4)][SEEDS.index(seed)]
    elif family==FAMILIES[1]:
        kind="selector3"
        wires=[(4,0,2),(4,1,3),(2,0,4),(3,1,4)][SEEDS.index(seed)]
    else:
        kind="quartic4"
        wires=[(0,1,2,4),(0,1,3,4),(0,2,3,4),(1,2,3,4)][SEEDS.index(seed)]
    fit=[episode(rng,kind,wires) for _ in range(24)]
    check=[episode(rng,kind,wires) for _ in range(8)]
    # Deterministic SOURCE-ONLY eligibility: hard negatives preserve the
    # complete observed-token multiset by swapping outputs of different
    # target roles. Degenerate uniform trajectories cannot admit such a
    # negative. Take the FIRST eligible trajectory of at most 128 draws.
    # No learner is consulted; FIT and CHECK distributions are unchanged.
    heldout=[]
    for _ in range(8):
        for attempt in range(128):
            candidate=episode(rng,kind,wires)
            ev=candidate["events"]
            eligible=any(ev[i]["target"]!=ev[j]["target"] and
                         ev[i]["observed"]!=ev[j]["observed"]
                         for i in range(8) for j in range(i+1,8))
            if eligible:
                heldout.append(candidate)
                break
        else:
            raise RuntimeError("F124DC_SOURCE_NO_ELIGIBLE_MATCHED_NEGATIVE_IN_128")
    return {"FIT":fit,"CHECK":check,"HELDOUT":heldout}

def hard_negative(ep):
    bad=copy.deepcopy(ep)
    e=bad["events"]
    pair=next(((i,j) for i in range(8) for j in range(i+1,8)
               if e[i]["target"]!=e[j]["target"]
               and e[i]["observed"]!=e[j]["observed"]),None)
    need(pair is not None,"NO_MATCHED_CROSSROLE_HARD_NEGATIVE")
    i,j=pair
    e[i]["observed"],e[j]["observed"]=e[j]["observed"],e[i]["observed"]
    need(sorted(z["observed"] for z in bad["events"])==
         sorted(z["observed"] for z in ep["events"]),"HARD_NEGATIVE_OBSERVATION_DRIFT")
    return bad
