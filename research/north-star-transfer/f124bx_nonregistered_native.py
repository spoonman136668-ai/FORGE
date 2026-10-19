"""F124-BX exact TWO disposable nonregistered resource fixtures.

No prior-science import or source label passed to models. Mathematical
engineering motifs (swap and two-shear), not authentic unseen evidence.
"""
from __future__ import annotations
import copy
import hashlib
import random

CASES={"BX-ENG-SWAP":(410971,"swap"),
       "BX-ENG-TWO-SHEAR":(410972,"pair")}


def need(ok,msg):
    if not ok:raise ValueError("BX_FIXTURE_"+msg)


def bits(x):
    return [(x>>i)&1 for i in range(16)]


def asint(v):
    return sum(bit<<i for i,bit in enumerate(v))


def forward(x,preset):
    lo=x&255
    hi=x>>8
    if preset=="swap":
        lo^=hi
        hi^=lo
        lo^=hi
    elif preset=="pair":
        lo^=hi
        hi^=lo
    else:
        raise ValueError("BX_FIXTURE_UNKNOWN")
    return lo|(hi<<8)


def backward(y,preset):
    lo=y&255
    hi=y>>8
    if preset=="swap":
        return (lo<<8)|hi
    if preset=="pair":
        oldhi=hi^lo
        oldlo=lo^oldhi
        return oldlo|(oldhi<<8)
    raise ValueError("BX_FIXTURE_UNKNOWN")


def true_causal_count(g,preset):
    node=g["start"]
    carry=None
    for role in g["roles"]:
        edges=[e for e in g["edges"]
               if e["from"]==node and e["role"]==role]
        if len(edges)!=1:
            return 0
        e=edges[0]
        predecessor=backward(asint(e["src_bits"]),preset)
        if carry is not None and carry!=predecessor:
            return 0
        carry=asint(e["dst_bits"])
        node=e["to"]
    return int(node==g["target"])


def make(case):
    need(type(case) is str and case in CASES,
         "ONLY_TWO_NONREGISTERED_CASES")
    seed,preset=CASES[case]
    rng=random.Random(seed)
    xvals=rng.sample(range(65536),48)
    corrupted={1,5,12,19,24,35}
    public=[(x,forward(x,preset)^(1 if i in corrupted else 0))
            for i,x in enumerate(xvals)]
    length=8 if preset=="swap" else 9
    tag=hashlib.sha256(("F124BX-DISPOSABLE-"+case).encode()).hexdigest()[:12]
    roles=[f"rel_task_{tag}:hop{j}" for j in range(length)]
    carry=rng.sample(range(65536),length+1)
    edges=[{"from":f"node{j}","to":f"node{j+1}","role":roles[j],
            "src_bits":bits(forward(carry[j],preset)),
            "dst_bits":bits(carry[j+1])}
           for j in range(length)]
    cut=3
    side=[]
    for j in range(7):
        orphan=rng.randrange(65536)
        if j==0:
            while orphan==carry[cut]:
                orphan=rng.randrange(65536)
        side.append({"from":f"detached{j}","to":f"dead{j}",
                     "role":roles[(cut+j)%length],
                     "src_bits":bits(forward(orphan,preset)),
                     "dst_bits":bits(rng.randrange(65536))})
    good_edges=edges+side
    bad_edges=copy.deepcopy(good_edges)
    bad_edges[cut]["src_bits"],bad_edges[length]["src_bits"]=(
        bad_edges[length]["src_bits"],bad_edges[cut]["src_bits"])
    rng.shuffle(good_edges)
    rng.shuffle(bad_edges)
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in public[:24]]
    common={"start":"node0","target":f"node{length}",
            "roles":roles,"demos":demos}
    good={**common,"edges":good_edges}
    bad={**common,"edges":bad_edges}
    token=lambda g:sorted(tuple(e[k]) for e in g["edges"]
                          for k in ("src_bits","dst_bits"))
    topology=lambda g:sorted((e["from"],e["to"],e["role"]) for e in g["edges"])
    need(true_causal_count(good,preset)==1
         and true_causal_count(bad,preset)==0
         and token(good)==token(bad)
         and topology(good)==topology(bad),
         "FIXTURE_TRUTH_OR_MATCHED_NEGATIVE")
    return {"FIT":public[:40],"CHECK":public[40:],
            "positive":good,"hard_negative":bad},{
       "fixture_type":"NONREGISTERED_ENGINEERING_NOT_SCIENCE",
       "symbolic_positive_paths":1,
       "symbolic_hard_negative_paths":0,
       "no_original_scientific_case_reused":True
    }
