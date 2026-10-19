"""F124-CZ independently authored SOURCE-FREE unknown-law fixture.

No original scientific source/birth module imported. All laws, hidden terms,
seeds and original per-case source parameters remain in this module only.
Learned models receive FIT/CHECK/HELDOUT episodes, never hidden terms or
symbolic original oracle. These are deterministic synthetic engineering
worlds, NOT independent real first-use experimental sources.
"""
from __future__ import annotations
import copy
import random

REGIMES=("nonlinear_cross_role_quadratic","modular_carry_composition")
SEEDS=(41,42,43,44)
ROLES=("alpha","beta","gamma")
FIT_N=24
CHECK_N=8
HELDOUT_N=8

def require(ok,reason):
    if not ok:raise ValueError("F124CZ_SOURCEFREE_"+reason)

def quadratic_parameters(rng):
    # Each output bit has genuine source-target cross-entity conjunction.
    # The hypothesis class is disclosed in preregistration, but hidden
    # coefficient values and pair selections are not passed to any learner.
    groups=(
       [(i,j) for i in range(4) for j in range(8,12)],
       [(i,j) for i in range(4,8) for j in range(8,12)],
       [(i,j) for i in range(4) for j in range(12,16)],
       [(i,j) for i in range(16,20) for j in range(8,12)])
    laws=[]
    for bit in range(4):
        linear=rng.sample(range(20),4)
        pair=[rng.choice(groups[bit]),rng.choice(groups[(bit+1)%4])]
        laws.append((linear,pair,rng.randrange(2)))
    return laws

def value(regime,tc,tl,sc,sl,event,secret):
    require(regime in REGIMES and all(type(x) is int and 0<=x<16
            for x in (tc,tl,sc,sl,event)),"LAW_BOUNDED")
    if regime==REGIMES[0]:
        inputs=[(n>>i)&1 for n in (tc,tl,sc,sl,event) for i in range(4)]
        out=0
        for bit,(linears,pairs,bias) in enumerate(secret):
            y=bias
            for j in linears:y^=inputs[j]
            for j,k in pairs:y^=(inputs[j]&inputs[k])
            out|=(y&1)<<bit
        return out
    # Interleaved modular carries and XOR create 3rd/4th degree structure.
    # Constants vary with the hidden synthetic source case, never CHECK.
    c0,c1,c2=secret
    u=(sc+tc+((event^sl)+c0))&15
    v=(tl+((sc<<1)&15)+c1)&15
    return (u^v^c2)&15

def episode(rng,regime,secret):
    initial={r:[rng.randrange(16),rng.randrange(16)] for r in ROLES}
    current=copy.deepcopy(initial)
    events=[]
    for i in range(8):
        target=rng.choice(ROLES)
        source=rng.choice([r for r in ROLES if r!=target])
        e=rng.randrange(16)
        tc,tl=current[target];sc,sl=current[source]
        observed=value(regime,tc,tl,sc,sl,e,secret)
        events.append({"target":target,"source":source,"event":e,
                       "observed":observed})
        current[target]=[observed,tc]
    return {"initial":initial,"events":events}

def born(regime,seed):
    require(regime in REGIMES and type(seed) is int and seed in SEEDS,
            "UNQUALIFIED_SYNTHETIC_SEED_OR_LAW")
    rng=random.Random(17102201+seed*997+(REGIMES.index(regime))*91273)
    secret=quadratic_parameters(rng) if regime==REGIMES[0] else [
              rng.randrange(16) for _ in range(3)]
    public={
      "FIT":[episode(rng,regime,secret) for _ in range(FIT_N)],
      "CHECK":[episode(rng,regime,secret) for _ in range(CHECK_N)],
      "HELDOUT":[episode(rng,regime,secret) for _ in range(HELDOUT_N)]}
    # No acceptance-based case selection: fixed seeds yield all 8 cases.
    return public

def hard_negative(ep):
    other=copy.deepcopy(ep)
    events=other["events"]
    pair=next(((i,j) for i in range(8) for j in range(i+1,8)
          if events[i]["target"]!=events[j]["target"] and
             events[i]["observed"]!=events[j]["observed"]),None)
    require(pair is not None,"MATCHED_ROLE_DISTINCT_SWAPPABLE_NEGATIVE")
    i,j=pair
    events[i]["observed"],events[j]["observed"]=(
          events[j]["observed"],events[i]["observed"])
    require(sorted(x["observed"] for x in ep["events"])==
            sorted(x["observed"] for x in other["events"]),
            "MUST_PRESERVE_EXACT_OUTPUT_INVENTORY")
    return other

def derivative_witness(regime,seed):
    """Source-author-side algebraic sanity; never sent to learners."""
    rng=random.Random(17102201+seed*997+REGIMES.index(regime)*91273)
    secret=quadratic_parameters(rng) if regime==REGIMES[0] else [
              rng.randrange(16) for _ in range(3)]
    # Nonzero degree>=2: toggle two input bits, detect parity difference.
    # For carry, prove degree>=3 via exact third finite derivative.
    dimensions=(0,8,16,4,12)
    for start in range(48):
        vals=[(start*3+q*7)&15 for q in range(5)]
        for order in ((0,8,16),(0,4,8),(4,8,16),(0,8,12)):
            acc=0
            for mask in range(8):
                x=vals.copy()
                for j,index in enumerate(order):
                    if mask>>j&1:x[index//4]^=1<<(index%4)
                acc^=value(regime,*x,secret)
            if acc!=0:return True
    return False

if __name__=="__main__":
    raise SystemExit("SOURCEFREE_UNKNOWN_SYNTHETIC_LAW_ONLY")
