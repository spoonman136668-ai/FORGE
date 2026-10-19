"""F124-BM independently born GF2 bit-relation with counterfactual graphs.

Source-only; imports no learner, scorer, evaluator or previous experiment.
Protected 128-case holdout is never constructible. 16 fresh FIT cases only.
All private relation keys and exact truth stay evaluator-side.
"""
from __future__ import annotations

import copy
import hashlib
import random

FIT=range(914000,914016)
HOLDOUT=range(914100,914228)
SALT=b"F124BM-INDEPENDENT-GF2-SOURCE-BIRTH-v1"


def need(ok,tag):
    if not ok:
        raise ValueError("BM_GF2_"+tag)


def bits(x):
    return [(x>>i)&1 for i in range(16)]


def value(v):
    return sum(t<<i for i,t in enumerate(v))


def forward(x,key):
    permutation,mask=key
    return value([((x>>permutation[i])&1)^((mask>>i)&1)
                  for i in range(16)])


def inverse(y,key):
    permutation,mask=key
    v=0
    for i,p in enumerate(permutation):
        v|=(((y>>i)&1)^((mask>>i)&1))<<p
    return v


def routes(g,key):
    # Private symbolic truth, kept outside model and native scorer.
    candidates=[(g["start"],None)]
    for role in g["roles"]:
        next_candidates=[]
        for node,carry in candidates:
            for edge in g["edges"]:
                if edge["from"]!=node or edge["role"]!=role:
                    continue
                source=inverse(value(edge["src_bits"]),key)
                if carry is None or carry==source:
                    next_candidates.append((edge["to"],value(edge["dst_bits"])))
        candidates=next_candidates
    return sum(int(node==g["target"]) for node,carry in candidates)


def make(seed):
    need(type(seed) is int and seed in FIT,"ONLY_FROZEN_FIT_NOT_PROTECTED")
    digest=hashlib.sha256(SALT+b"/"+str(seed).encode()).digest()
    rng=random.Random(int.from_bytes(digest,"big"))
    p=list(range(16))
    rng.shuffle(p)
    key=(tuple(p),rng.randrange(65536))
    support=rng.sample(range(65536),48)
    bad=set(rng.sample(range(48),6))
    public=[(x,forward(x,key)^(1 if i in bad else 0))
            for i,x in enumerate(support)]
    nonce=hashlib.sha256(SALT+b"/nonce/"+str(seed).encode()).hexdigest()[:12]
    depth=7+((seed-FIT.start)%3)
    roles=[f"rel_task_{nonce}:causal_{j}" for j in range(depth)]
    carries=rng.sample(range(65536),depth+1)
    main=[{"from":f"node_{j}","to":f"node_{j+1}","role":roles[j],
           "src_bits":bits(forward(carries[j],key)),
           "dst_bits":bits(carries[j+1])} for j in range(depth)]
    distractors=[]
    for j in range(5):
        x=rng.randrange(65536)
        if j==0:
            while x==carries[3]:
                x=rng.randrange(65536)
        distractors.append({"from":f"detached_{j}","to":f"dead_{j}",
                           "role":roles[(3+j)%depth],
                           "src_bits":bits(forward(x,key)),
                           "dst_bits":bits(rng.randrange(65536))})
    orig=main+distractors
    counter=copy.deepcopy(orig)
    # Hard counterfactual: identical topology, same public token histogram,
    # only the CAUSAL association between two equal-role edges changes.
    counter[3]["src_bits"],counter[depth]["src_bits"]=(
        counter[depth]["src_bits"],counter[3]["src_bits"])
    rng.shuffle(orig)
    rng.shuffle(counter)
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in public[:24]]
    shared={"start":"node_0","target":f"node_{depth}",
            "roles":roles,"demos":demos}
    positive={**shared,"edges":orig}
    negative={**shared,"edges":counter}
    need(routes(positive,key)==1 and routes(negative,key)==0,
         "EXACT_LABELS_DISJOINT")
    inventory=lambda g: sorted(
        (e["from"],e["to"],e["role"]) for e in g["edges"])
    tokens=lambda g: sorted(
        tuple(e[t]) for e in g["edges"] for t in ("src_bits","dst_bits"))
    need(inventory(positive)==inventory(negative)
         and tokens(positive)==tokens(negative)
         and len(orig)>=12
         and len(bad)==6,
         "HARD_COUNTERFACTUAL_MATCHED_INVENTORY")
    # Return graph/public inputs separately from private source truth.
    return {"FIT":public[:40],"CHECK":public[40:],
            "positive":positive,"hard_negative":negative}, {
        "private_key":key,"oracle_positive_routes":1,
        "oracle_negative_routes":0,"private_corruption_indices":tuple(sorted(bad)),
        "FIT_seed":seed,"private_source_family":"GF2_RANDOM_BIT_PERM"}
