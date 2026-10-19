"""F124-BP separately born source B: nonlinear three-step byte feedback.

A different three-stage reversible nonlinear composition; explicitly beyond
the four-byte two-shear candidate. No predictor or other source import.
Only 12 new FIT task identities are callable. Reserve 128 protected.
"""
from __future__ import annotations

import copy
import hashlib
import random

SALT=b"F124BP-INDEPENDENT-THREE-ROUND-COUPLED-FEEDBACK-B-20261019"
FIT=range(923000,923012)
SEALED=range(923100,923228)


def need(ok,label):
    if not ok:raise ValueError("F124BP_SOURCE_B_"+label)


def bits(x):
    return [(x>>i)&1 for i in range(16)]


def asint(v):
    return sum(bit<<i for i,bit in enumerate(v))


def rotate(v,shift):
    return ((v<<shift)|(v>>(8-shift)))&255


def forward(x,steps):
    lo=x&255
    hi=x>>8
    for a,b,c,d in steps:
        lo=(lo+a*hi+b)&255
        hi^=(((c*lo+d)&255)^rotate(lo,3))
    return lo|(hi<<8)


def inverse(y,steps):
    lo=y&255
    hi=y>>8
    for a,b,c,d in reversed(steps):
        hi^=(((c*lo+d)&255)^rotate(lo,3))
        lo=(lo-a*hi-b)&255
    return lo|(hi<<8)


def source_truth(graph,key):
    states=[(graph["start"],None)]
    for role in graph["roles"]:
        next_states=[]
        for node,carry in states:
            for edge in graph["edges"]:
                if edge["from"]!=node or edge["role"]!=role:continue
                decoded=inverse(asint(edge["src_bits"]),key)
                if carry is None or decoded==carry:
                    next_states.append((edge["to"],asint(edge["dst_bits"])))
        states=next_states
    return sum(node==graph["target"] for node,carry in states)


def make(case):
    need(type(case) is int and case in FIT,
         "NO_PROTECTED_OR_PREVIOUS_EXPERIMENT_CASE")
    rng=random.Random(int.from_bytes(hashlib.sha256(
        SALT+b"/new/"+str(case).encode()).digest(),"big"))
    key=tuple((rng.randrange(128)*2+1,rng.randrange(256),
               rng.randrange(128)*2+1,rng.randrange(256)) for _ in range(3))
    xvals=rng.sample(range(65536),48)
    flipped=set(rng.sample(range(48),6))
    public=[(x,forward(x,key)^(1 if index in flipped else 0))
            for index,x in enumerate(xvals)]
    depth=7+(case-FIT.start)%4
    nonce=hashlib.sha256(SALT+b"/native/"+str(case).encode()).hexdigest()[:12]
    roles=[f"rel_task_{nonce}:hop{j}" for j in range(depth)]
    carries=rng.sample(range(65536),depth+1)
    path=[{"from":f"n{j}","to":f"n{j+1}","role":roles[j],
           "src_bits":bits(forward(carries[j],key)),
           "dst_bits":bits(carries[j+1])} for j in range(depth)]
    cut=2+(case-FIT.start)%(depth-3)
    detached=[]
    for j in range(7):
        unwanted=rng.randrange(65536)
        if j==0:
            while unwanted==carries[cut]:unwanted=rng.randrange(65536)
        detached.append({"from":f"side{j}","to":f"end{j}",
                         "role":roles[(cut+j)%depth],
                         "src_bits":bits(forward(unwanted,key)),
                         "dst_bits":bits(rng.randrange(65536))})
    yes_edges=path+detached
    no_edges=copy.deepcopy(yes_edges)
    no_edges[cut]["src_bits"],no_edges[depth]["src_bits"]=(
        no_edges[depth]["src_bits"],no_edges[cut]["src_bits"])
    rng.shuffle(yes_edges)
    rng.shuffle(no_edges)
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in public[:24]]
    body={"start":"n0","target":f"n{depth}",
          "roles":roles,"demos":demos}
    yes={**body,"edges":yes_edges}
    no={**body,"edges":no_edges}
    structural=lambda g:sorted((e["from"],e["to"],e["role"]) for e in g["edges"])
    token=lambda g:sorted(tuple(e[k]) for e in g["edges"]
                          for k in ("src_bits","dst_bits"))
    need(source_truth(yes,key)==1 and source_truth(no,key)==0,
         "SYMBOLIC_PRIVATE_CHAIN_TRUTH")
    need(structural(yes)==structural(no) and token(yes)==token(no)
         and len(yes_edges)>=14 and len(flipped)==6,
         "MATCHED_PRIVATE_HARD_NEGATIVE")
    return {"FIT":public[:40],"CHECK":public[40:],
            "positive":yes,"hard_negative":no},{
        "private_three_stage_coupling_key":key,
        "private_bit_error_positions":tuple(sorted(flipped)),
        "private_positive_routes":1,"private_hard_routes":0,
        "private_case":case}
