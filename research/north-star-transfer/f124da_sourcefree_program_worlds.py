"""F124-DA independently authored source-free CAUSAL PROGRAM author.
Synthetic engineering only; never accesses prior original scientific source.
Hidden syntax trees remain source-only. Learners receive only public episodes.
"""
from __future__ import annotations
import copy
import random

ROLES=("alpha","beta","gamma")
SEEDS=(51,52,53,54)
FAMILIES=("heldout_two_stage_arithmetic_programs","out_of_primitive_class_multiplicative_carry")
NAMES=("target_current","target_lag","source_current","source_lag","event","rotl1_event")
OPERATORS=("xor4","add4","and4","or4")

def calc(op,a,b):
    if op=="xor4":return a^b
    if op=="add4":return (a+b)&15
    if op=="and4":return a&b
    if op=="or4":return a|b
    raise ValueError("DA_UNKNOWN_PRIVATE_OPERATION")

def rot(x):return ((x<<1)|(x>>3))&15

# Four deliberately different two-step topologies never given to learner.
PRIVATE_PROGRAMS=(
  ("xor4","add4",2,1,5),
  ("add4","xor4",0,2,4),
  ("and4","xor4",2,0,5),
  ("or4","add4",3,2,4),
)

def law(family,seed,tc,tl,sc,sl,event):
    if family==FAMILIES[0]:
        inner,outer,a,b,c=PRIVATE_PROGRAMS[SEEDS.index(seed)]
        vals=(tc,tl,sc,sl,event,rot(event))
        return calc(outer,calc(inner,vals[a],vals[b]),vals[c])
    # Multiplication + carry over multiple inputs is deliberately *not*
    # handed to either solver as a primitive. Fixed constants per seed.
    q=SEEDS.index(seed)+1
    return ((sc*(tc|1)+tl+((event^sl)+q))&15)^rot(sc)

def episode(rng,family,seed):
    initial={r:[rng.randrange(16),rng.randrange(16)] for r in ROLES}
    state=copy.deepcopy(initial)
    events=[]
    for _ in range(8):
        target=rng.choice(ROLES)
        source=rng.choice([r for r in ROLES if r!=target])
        e=rng.randrange(16)
        tc,tl=state[target];sc,sl=state[source]
        y=law(family,seed,tc,tl,sc,sl,e)
        events.append({"target":target,"source":source,"event":e,"observed":y})
        state[target]=[y,tc]
    return {"initial":initial,"events":events}

def born(family,seed):
    if family not in FAMILIES or type(seed) is not int or seed not in SEEDS:
        raise ValueError("F124DA_UNREGISTERED_SOURCEFREE_CASE")
    rng=random.Random(1242100+seed*791+FAMILIES.index(family)*20011)
    return {
        "FIT":[episode(rng,family,seed) for _ in range(24)],
        "CHECK":[episode(rng,family,seed) for _ in range(8)],
        "HELDOUT":[episode(rng,family,seed) for _ in range(8)]}

def matched_negative(ep):
    neg=copy.deepcopy(ep)
    pos=ep["events"]
    swap=next(((i,j) for i in range(8) for j in range(i+1,8)
          if pos[i]["target"]!=pos[j]["target"] and
             pos[i]["observed"]!=pos[j]["observed"]),None)
    if swap is None: raise ValueError("F124DA_NO_MATCHED_COUNTERFACTUAL")
    i,j=swap
    neg["events"][i]["observed"],neg["events"][j]["observed"]=(
          neg["events"][j]["observed"],neg["events"][i]["observed"])
    return neg
