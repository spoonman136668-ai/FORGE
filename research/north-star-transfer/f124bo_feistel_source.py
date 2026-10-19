"""F124-BO independently born new source B: 4-round reversible Feistel.

This genuine nonlinear 16-bit transformation is not a single modular-affine
plus XOR relationship. 12 new development cases only, independent original
source birth and salt, 128 reserved sealed. No predictor/source imports.
"""
from __future__ import annotations
import copy
import hashlib
import random

SALT=b"F124BO-FEISTEL-FOUR-ROUND-ORIGINAL-SOURCE-B-20261018"
FIT=range(921000,921012)
RESERVED=range(921100,921228)


def need(ok,name):
    if not ok:raise ValueError("F124BO_FEISTEL_"+name)


def rot8(x,n):
    return ((x<<n)|(x>>(8-n)))&255


def bits(x):
    return [(x>>j)&1 for j in range(16)]


def asint(x):
    return sum(v<<j for j,v in enumerate(x))


def f(x,key):
    mult,offset,mask=key
    return (((x*mult+offset)&255)^rot8(x,3)^mask)&255


def forward(x,keys):
    a=x&255
    b=x>>8
    for key in keys:
        a,b=b,a^f(b,key)
    return a|(b<<8)


def inverse(y,keys):
    a=y&255
    b=y>>8
    for key in reversed(keys):
        a,b=b^f(a,key),a
    return a|(b<<8)


def causal_truth(graph,keys):
    states=[(graph["start"],None)]
    for role in graph["roles"]:
        nxt=[]
        for node,carry in states:
            for edge in graph["edges"]:
                if edge["from"]!=node or edge["role"]!=role:continue
                predecessor=inverse(asint(edge["src_bits"]),keys)
                if carry is None or carry==predecessor:
                    nxt.append((edge["to"],asint(edge["dst_bits"])))
        states=nxt
    return sum(node==graph["target"] for node,carry in states)


def make(case):
    need(type(case) is int and case in FIT,
         "HELDOUT_PREVIOUS_OR_UNREGISTERED_SOURCE_DENIED")
    r=random.Random(int.from_bytes(hashlib.sha256(
        SALT+b"/"+str(case).encode()).digest(),"big"))
    keys=tuple((r.randrange(128)*2+1,r.randrange(256),r.randrange(256))
               for _ in range(4))
    xs=r.sample(range(65536),48)
    noise=set(r.sample(range(48),6))
    public=[(x,forward(x,keys)^(1 if j in noise else 0))
            for j,x in enumerate(xs)]
    length=7+(case-FIT.start)%4
    nonce=hashlib.sha256(SALT+b"/tasknonce/"+str(case).encode()
                         ).hexdigest()[:12]
    roles=[f"rel_task_{nonce}:new{j}" for j in range(length)]
    carries=r.sample(range(65536),length+1)
    path=[{"from":f"n{j}","to":f"n{j+1}","role":roles[j],
           "src_bits":bits(forward(carries[j],keys)),
           "dst_bits":bits(carries[j+1])}
          for j in range(length)]
    cut=2+(case-FIT.start)%(length-3)
    detached=[]
    for j in range(7):
        decoy=r.randrange(65536)
        if j==0:
            while decoy==carries[cut]:decoy=r.randrange(65536)
        detached.append({"from":f"far{j}","to":f"end{j}",
                         "role":roles[(cut+j)%length],
                         "src_bits":bits(forward(decoy,keys)),
                         "dst_bits":bits(r.randrange(65536))})
    valid=path+detached
    invalid=copy.deepcopy(valid)
    invalid[cut]["src_bits"],invalid[length]["src_bits"]=(
        invalid[length]["src_bits"],invalid[cut]["src_bits"])
    r.shuffle(valid)
    r.shuffle(invalid)
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in public[:24]]
    shared={"start":"n0","target":f"n{length}",
            "roles":roles,"demos":demos}
    positive={**shared,"edges":valid}
    negative={**shared,"edges":invalid}
    footprint=lambda graph:sorted((e["from"],e["to"],e["role"])
                                  for e in graph["edges"])
    tokens=lambda graph:sorted(tuple(e[name]) for e in graph["edges"]
                               for name in ("src_bits","dst_bits"))
    need(causal_truth(positive,keys)==1
         and causal_truth(negative,keys)==0,
         "EXACT_SOURCE_PRIVATE_CAUSAL_TRUTH")
    need(footprint(positive)==footprint(negative)
         and tokens(positive)==tokens(negative)
         and len(valid)>=14 and len(noise)==6,
         "IDENTICAL_TOPOLOGY_TOKEN_NEGATIVE")
    return {"FIT":public[:40],"CHECK":public[40:],
            "positive":positive,"hard_negative":negative},{
        "private_operator_round_keys":keys,
        "private_error_positions":sorted(noise),
        "private_truth_pos":1,
        "private_truth_neg":0,
        "private_operator_family":"FEISTEL_FOUR_ROUND",
        "private_case":case}
