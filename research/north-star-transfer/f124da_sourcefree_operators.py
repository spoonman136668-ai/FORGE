"""F124-DA new SOURCE-FREE hidden operator/wiring task originator.

No consumed experimental generator or hidden-law import. Deterministic
synthetic FIT/CHECK/HELDOUT only. Models receive raw public trajectories;
the binary truth tables and wiring are never exported to model processes.
"""
from __future__ import annotations
import copy
import random

ROLES=("alpha","beta","gamma")
REGIMES=("unseen_boolean_operator_lexicon","fourbit_carry_outside_lexicon")
SEEDS=(51,52,53,54)

def need(ok,why):
    if not ok:raise ValueError("F124DA_SOURCE_"+why)

def nonlinear(table):
    # One two-bit Boolean output; its mixed GF(2) derivative is nonzero.
    return ((table>>0)^(table>>1)^(table>>2)^(table>>3))&1

def hidden(rng,regime):
    if regime==REGIMES[0]:
        ops=[]
        for output_bit in range(4):
            a=rng.randrange(0,8)  # current/lag target
            b=rng.randrange(8,16) # current/lag source
            z=rng.randrange(16,20) # event
            table=rng.choice(tuple(x for x in range(16) if nonlinear(x)))
            ops.append((a,b,z,table))
        return ops
    return tuple(rng.randrange(16) for _ in range(3))

def step_law(raw,regime,params):
    if regime==REGIMES[0]:
        y=0
        for out,(a,b,z,table) in enumerate(params):
            truth=(table>>(((raw>>a)&1)|(((raw>>b)&1)<<1)))&1
            y|=(truth^((raw>>z)&1))<<out
        return y
    tc=(raw>>0)&15;tl=(raw>>4)&15
    sc=(raw>>8)&15;sl=(raw>>12)&15;e=(raw>>16)&15
    c0,c1,c2=params
    # Composed multi-bit carry, not a single binary LUT XOR one raw bit.
    value=((tc+sc+((sl^e)+c0))&15)^((tl+((sc<<1)&15)+c1)&15)^c2
    return value&15

def episode(rng,regime,params):
    initial={role:[rng.randrange(16),rng.randrange(16)] for role in ROLES}
    state=copy.deepcopy(initial)
    events=[]
    for i in range(8):
        target=rng.choice(ROLES)
        source=rng.choice([r for r in ROLES if r!=target])
        event=rng.randrange(16)
        tc,tl=state[target];sc,sl=state[source]
        raw=tc|(tl<<4)|(sc<<8)|(sl<<12)|(event<<16)
        observed=step_law(raw,regime,params)
        events.append({"target":target,"source":source,"event":event,
                      "observed":observed})
        state[target]=[observed,tc]
    return {"initial":initial,"events":events}

def born(regime,seed):
    need(regime in REGIMES and type(seed) is int and seed in SEEDS,
         "EXACT_NEW_SOURCEFREE_ROSTER")
    rng=random.Random(12451000+seed*991+REGIMES.index(regime)*97777)
    private=hidden(rng,regime)
    # Private operator IDs/wiring do not cross into learner call output.
    return {"FIT":[episode(rng,regime,private) for _ in range(24)],
            "CHECK":[episode(rng,regime,private) for _ in range(8)],
            "HELDOUT":[episode(rng,regime,private) for _ in range(8)]}

def hard_negative(ep):
    neg=copy.deepcopy(ep)
    events=neg["events"]
    pair=next(((i,j) for i in range(8) for j in range(i+1,8)
               if events[i]["target"]!=events[j]["target"] and
               events[i]["observed"]!=events[j]["observed"]),None)
    need(pair is not None,"NO_CROSS_ROLE_ALTERABLE_NEGATIVE")
    i,j=pair
    events[i]["observed"],events[j]["observed"]=events[j]["observed"],events[i]["observed"]
    need(sorted(e["observed"] for e in ep["events"])==
         sorted(e["observed"] for e in neg["events"]),
         "NEGATIVE_INVENTORY_NOT_MATCHED")
    return neg
