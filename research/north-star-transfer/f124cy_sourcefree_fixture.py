"""F124-CY SOURCE-FREE synthetic causal episode author, not a science source.

The generator is independent from learned models and uses no earlier
F124 original source/oracle or original hidden keys. Its parity grammar
is declared in the preregistration; this is a deliberately privileged
operator-class feasibility task, not general unfamiliar science.
"""
import copy
import random

ROLES=("alpha","beta","gamma")
REGIMES=("ungated_shared_linear_GF2","event_bit_gated_GF2")
FIT_N=24
CHECK_N=8
HELDOUT_N=8
STEPS=8

def require(ok,reason):
    if not ok:raise ValueError("F124CY_FIXTURE_"+reason)

def features(target_cur,target_lag,source_cur,source_lag,event):
    assert all(type(v) is int and 0<=v<=15 for v in
               (target_cur,target_lag,source_cur,source_lag,event))
    return target_cur|(target_lag<<4)|(source_cur<<8)|(source_lag<<12)|(event<<16)|(1<<20)

def output(f,masks):
    return sum(((f & mask).bit_count() & 1)<<i for i,mask in enumerate(masks))

def episode(rng,source_masks,gated):
    initial={role:[rng.randrange(16),rng.randrange(16)] for role in ROLES}
    state=copy.deepcopy(initial)
    events=[]
    for step in range(STEPS):
        # Roles are not tied to a fixed transition law or slot.
        target=rng.choice(ROLES)
        source=rng.choice(tuple(r for r in ROLES if r!=target))
        event=rng.randrange(16)
        tc,tl=state[target]
        sc,sl=state[source]
        bits=features(tc,tl,sc,sl,event)
        branch=(event&1) if gated else 0
        observed=output(bits,source_masks[branch])
        events.append({"target":target,"source":source,
                       "event":event,"observed":observed})
        state[target]=[observed,tc]
    return {"initial":initial,"events":events}

def born(regime,seed):
    require(regime in REGIMES and type(seed) is int and 0<=seed<4,
            "ONLY_PREREGISTERED_SYNTHETIC_CASES")
    rng=random.Random(927690 + seed*799 + 99199*REGIMES.index(regime))
    count=2 if regime==REGIMES[1] else 1
    masks=[]
    for _ in range(count):
        # Random learned coefficient matrix, with dependence on target/source
        # and event forced for each bit, not a weak no-causality fixture.
        masks.append([rng.getrandbits(21) |
                      (1<<rng.randrange(0,4))|
                      (1<<rng.randrange(4,8))|
                      (1<<rng.randrange(8,12))|
                      (1<<rng.randrange(16,20)) for _ in range(4)])
    fit=[episode(rng,masks,count==2) for _ in range(FIT_N)]
    check=[episode(rng,masks,count==2) for _ in range(CHECK_N)]
    heldout=[episode(rng,masks,count==2) for _ in range(HELDOUT_N)]
    # The caller receives ONLY the public episodes; hidden masks are not in
    # the model's input or a selection oracle. No rejection or seed picking.
    return {"fit":fit,"check":check,"heldout":heldout}

def matched_hard_negative(positive):
    negative=copy.deepcopy(positive)
    entries=negative["events"]
    pair=next(((i,j) for i in range(len(entries))
               for j in range(i+1,len(entries))
               if entries[i]["target"]!=entries[j]["target"]
               and entries[i]["observed"]!=entries[j]["observed"]),None)
    require(pair is not None,"GENUINE_CROSS_ROLE_DIFFERENT_OUTPUTS")
    i,j=pair
    entries[i]["observed"],entries[j]["observed"]=entries[j]["observed"],entries[i]["observed"]
    require(sorted(x["observed"] for x in positive["events"])==
            sorted(x["observed"] for x in negative["events"]),
            "MATCHED_CAUSAL_OBSERVATION_INVENTORY")
    return negative
