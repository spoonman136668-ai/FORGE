"""F124-DG independent SOURCE-ONLY deterministic causal laws and oracle.

Fresh engineering seeds 201-204. Never used in consumed scientific 924-937
or F124-DF 101-104. Synthetic degree<=4 Boolean laws; source secrets stay
inside this module and only answer explicitly budgeted new probe requests.
"""
from __future__ import annotations
import copy
from itertools import combinations
import random

FAMILIES=("sparse_degree4_GF2_unknown","dense_degree4_GF2_unknown")
SEEDS=(201,202,203,204)
ROLES=("alpha","beta","gamma")
MONOMIALS=tuple(x for deg in range(5) for x in combinations(range(8),deg))

def bits(pair):
    # Public intervention: low 4 target-current bits, high 4 source-current
    return tuple((pair>>i)&1 for i in range(8))

def polynomial_features(pair):
    raw=bits(pair)
    mask=0
    for j,c in enumerate(MONOMIALS):
        if all(raw[i] for i in c):mask|=1<<j
    return mask

def secret(family,seed):
    if family not in FAMILIES or seed not in SEEDS:
        raise ValueError("DG_WRONG_SOURCEFREE_ROSTER")
    rng=random.Random(244101+seed*73+FAMILIES.index(family)*81191)
    # Explicit nonzero highest-order interactions, with varying sparsity.
    count=12 if family==FAMILIES[0] else 55
    degree4=[i for i,m in enumerate(MONOMIALS) if len(m)==4]
    masks=[]
    for bit in range(4):
        positions=set(rng.sample(range(len(MONOMIALS)),count))
        positions.add(rng.choice(degree4))
        masks.append(sum(1<<i for i in positions))
    return masks

def response(family,seed,pair):
    if type(pair) is not int or not 0<=pair<256:
        raise ValueError("DG_SOURCEFREE_ORACLE_QUERY_INVALID")
    x=polynomial_features(pair)
    return sum(((x&w).bit_count()&1)<<i for i,w in enumerate(secret(family,seed)))

def episode(rng,family,seed):
    initial={role:[rng.randrange(16),rng.randrange(16)] for role in ROLES}
    state=copy.deepcopy(initial)
    events=[]
    for _ in range(8):
        target=rng.choice(ROLES)
        source=rng.choice([r for r in ROLES if r!=target])
        e=rng.randrange(16)
        tc=state[target][0];sc=state[source][0]
        observed=response(family,seed,tc|(sc<<4))
        events.append({"target":target,"source":source,
                       "event":e,"observed":observed})
        state[target]=[observed,tc]
    return {"initial":initial,"events":events}

def born(family,seed):
    if family not in FAMILIES or seed not in SEEDS:
        raise ValueError("DG_ONLY_FROZEN_NEW_SOURCEFREE_ID")
    rng=random.Random(12377001+seed*997+FAMILIES.index(family)*31133)
    fit=[episode(rng,family,seed) for _ in range(24)]
    check=[episode(rng,family,seed) for _ in range(8)]
    holdout=[]
    # A matched hard negative must preserve the exact observed-token
    # inventory while swapping different-role, DIFFERENT observations.
    # Before ANY learner/scoring execution, source-only quality-control
    # admits only heldout episodes for which that counterfactual exists.
    # No model prediction, FIT/check success or hidden source selection
    # influences this deterministic validity filter. Explicitly retain
    # the filter and bounded rejected-source count in the qualified
    # protocol rather than fabricating impossible hard negatives.
    for i in range(8):
        for attempt in range(128):
            ep=episode(rng,family,seed)
            e=ep["events"]
            if any(e[a]["target"]!=e[z]["target"] and
                   e[a]["observed"]!=e[z]["observed"]
                   for a in range(8) for z in range(a+1,8)):
                holdout.append(ep)
                break
        else:
            raise ValueError("DG_SOURCE_ONLY_UNCONSTRUCTIBLE_HARD_NEGATIVE")
    return {"FIT":fit,"CHECK":check,"HELDOUT":holdout}

def matched_negative(ep):
    neg=copy.deepcopy(ep)
    e=ep["events"]
    pair=next(((i,j) for i in range(8) for j in range(i+1,8)
          if e[i]["target"]!=e[j]["target"] and
             e[i]["observed"]!=e[j]["observed"]),None)
    if pair is None:raise ValueError("DG_NO_HARD_NEGATIVE_AVAILABLE")
    i,j=pair
    neg["events"][i]["observed"],neg["events"][j]["observed"]=(
        neg["events"][j]["observed"],neg["events"][i]["observed"])
    return neg

def public_meta_pair_frequencies():
    # No private current-source secret, CHECK or heldout. Both trained
    # policies use exactly these frozen eight public meta-task seeds.
    count=[0]*256
    for seed in range(900,908):
        rng=random.Random(seed)
        for _ in range(24*8):
            pair=rng.randrange(16)|(rng.randrange(16)<<4)
            count[pair]+=1
    return count
