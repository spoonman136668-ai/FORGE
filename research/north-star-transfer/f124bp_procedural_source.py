"""F124-BP independently born source A: procedural composed byte shears.

Two independent sweeps, 15 private elementary reversible operations, not
importing the 4-byte predictor. Their cumulative action is a compact
two-stage nonlinear composition; task-specific private keys never sent
to learner or original control. New FIT cases only; holdout inaccessible.
"""
from __future__ import annotations

import copy
import hashlib
import random

SALT=b"F124BP-INDEPENDENT-PROCEDURAL-COMPOSITION-A-20261019"
FIT=range(922000,922012)
SEALED=range(922100,922228)


def need(ok,label):
    if not ok:raise ValueError("F124BP_SOURCE_A_"+label)


def bitlist(x):
    return [(x>>i)&1 for i in range(16)]


def integer(v):
    return sum(bit<<i for i,bit in enumerate(v))


def forward(x,key):
    lows,highs=key
    lo=x&255
    hi=x>>8
    for a,b in lows:
        lo=(lo+a*hi+b)&255
    for c,d in highs:
        hi=(hi+c*lo+d)&255
    return lo|(hi<<8)


def inverse(y,key):
    lows,highs=key
    lo=y&255
    hi=y>>8
    for c,d in reversed(highs):
        hi=(hi-c*lo-d)&255
    for a,b in reversed(lows):
        lo=(lo-a*hi-b)&255
    return lo|(hi<<8)


def graph_truth(graph,key):
    states=[(graph["start"],None)]
    for role in graph["roles"]:
        next_states=[]
        for node,last in states:
            for e in graph["edges"]:
                if e["from"]!=node or e["role"]!=role:continue
                source=inverse(integer(e["src_bits"]),key)
                if last is None or source==last:
                    next_states.append((e["to"],integer(e["dst_bits"])))
        states=next_states
    return sum(node==graph["target"] for node,last in states)


def make(case):
    need(type(case) is int and case in FIT,
         "REGISTERED_PUBLIC_FIT_ONLY_NO_PROTECTED_OR_OLD_CASE")
    rng=random.Random(int.from_bytes(hashlib.sha256(
        SALT+b"/"+str(case).encode()).digest(),"big"))
    lows=[(rng.randrange(256),rng.randrange(256)) for _ in range(7)]
    highs=[(rng.randrange(256),rng.randrange(256)) for _ in range(6)]
    # Add one independent elementary step to each segment; enforce only
    # the two aggregate gains odd so the frozen learner's hypothesis applies.
    lows.append(((1-sum(a for a,b in lows))&255,rng.randrange(256)))
    highs.append(((1-sum(c for c,d in highs))&255,rng.randrange(256)))
    # Gain total exactly 1 (odd), cumulative intercept still task-private.
    # It is a *15-step source grammar*, not a model-family label.
    key=(tuple(lows),tuple(highs))
    xs=rng.sample(range(65536),48)
    errors=set(rng.sample(range(48),6))
    public=[(x,forward(x,key)^(1 if j in errors else 0))
            for j,x in enumerate(xs)]
    depth=7+(case-FIT.start)%4
    nonce=hashlib.sha256(SALT+b"/role/"+str(case).encode()
                         ).hexdigest()[:12]
    roles=[f"rel_task_{nonce}:link{j}" for j in range(depth)]
    carries=rng.sample(range(65536),depth+1)
    path=[{"from":f"p{j}","to":f"p{j+1}","role":roles[j],
           "src_bits":bitlist(forward(carries[j],key)),
           "dst_bits":bitlist(carries[j+1])} for j in range(depth)]
    cut=2+(case-FIT.start)%(depth-3)
    detached=[]
    for j in range(7):
        decoy=rng.randrange(65536)
        if j==0:
            while decoy==carries[cut]:decoy=rng.randrange(65536)
        detached.append({"from":f"far{j}","to":f"sink{j}",
                         "role":roles[(cut+j)%depth],
                         "src_bits":bitlist(forward(decoy,key)),
                         "dst_bits":bitlist(rng.randrange(65536))})
    valid=path+detached
    false=copy.deepcopy(valid)
    false[cut]["src_bits"],false[depth]["src_bits"]=(
        false[depth]["src_bits"],false[cut]["src_bits"])
    rng.shuffle(valid)
    rng.shuffle(false)
    demos=[{"input_bits":bitlist(x),"output_bits":bitlist(y)}
           for x,y in public[:24]]
    shared={"start":"p0","target":f"p{depth}",
            "roles":roles,"demos":demos}
    yes={**shared,"edges":valid}
    no={**shared,"edges":false}
    tokens=lambda g:sorted(tuple(e[k]) for e in g["edges"]
                           for k in ("src_bits","dst_bits"))
    topology=lambda g:sorted((e["from"],e["to"],e["role"])
                            for e in g["edges"])
    need(graph_truth(yes,key)==1 and graph_truth(no,key)==0,
         "INDEPENDENT_EXACT_CAUSAL_TRUTH")
    need(tokens(yes)==tokens(no) and topology(yes)==topology(no)
         and len(valid)>=14 and len(errors)==6,
         "MATCHED_HARD_NEGATIVE")
    return {"FIT":public[:40],"CHECK":public[40:],
            "positive":yes,"hard_negative":no},{
        "private_15_stage_relation":key,
        "private_public_bit_errors":tuple(sorted(errors)),
        "private_positive_routes":1,"private_hard_routes":0,
        "private_case":case}
