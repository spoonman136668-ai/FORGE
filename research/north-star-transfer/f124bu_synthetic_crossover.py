"""F124-BU ORIGINAL nonregistered source-neutral crossover task ONLY.

No model import, no existing experimental source and no 924/925 source birth.
Chosen BEFORE learner/source scoring in the preregistered protocol. Boolean
function is deliberately in the intersection of two *previously frozen*
hypothesis classes: two XOR byte shears with unit multiplier, zero bias.
No claim of independent novelty or transferable cognition is permitted.
"""
from __future__ import annotations
import copy
import hashlib
import random

SEEDS={"BU-SYN-01":504921,"BU-SYN-02":504922}
ERRORS=6
FIT=40
CHECK=8
SEALED_IDS=((924000,924011),(925000,925011),(924100,924227),(925100,925227))


def need(ok,why):
    if not ok:raise ValueError("F124BU_SYNTHETIC_"+why)


def forward(x):
    need(type(x) is int and 0<=x<65536,"16BIT_ONLY")
    lo=x&255
    hi=x>>8
    yl=lo^hi
    yh=hi^yl
    return yl|(yh<<8)


def inverse(y):
    need(type(y) is int and 0<=y<65536,"INV16")
    yl=y&255
    yh=y>>8
    hi=yh^yl
    lo=yl^hi
    return lo|(hi<<8)


def bits(x):
    return [(x>>i)&1 for i in range(16)]


def number(data):
    return sum(v<<i for i,v in enumerate(data))


def symbolic_path(g):
    carry=None
    node=g["start"]
    for role in g["roles"]:
        matches=[e for e in g["edges"]
                 if e["from"]==node and e["role"]==role]
        if len(matches)!=1:return 0
        edge=matches[0]
        recovered=inverse(number(edge["src_bits"]))
        if carry is not None and carry!=recovered:return 0
        carry=number(edge["dst_bits"])
        node=edge["to"]
    return int(node==g["target"])


def make(case):
    need(type(case) is str and case in SEEDS,"ONLY_TWO_PREDECLARED_NONREGISTERED")
    rng=random.Random(SEEDS[case])
    xvals=rng.sample(range(65536),FIT+CHECK)
    noisy=set(rng.sample(range(FIT),ERRORS))
    support=[(x,forward(x)^(1 if i in noisy else 0))
             for i,x in enumerate(xvals)]
    length=7+int(case[-1])
    nonce=hashlib.sha256(b"F124BU-SOURCEBLIND-PANEL-"+case.encode()).hexdigest()[:12]
    roles=[f"rel_task_{nonce}:hop{j}" for j in range(length)]
    carry=rng.sample(range(65536),length+1)
    path=[{"from":f"n{j}","to":f"n{j+1}","role":roles[j],
           "src_bits":bits(forward(carry[j])),"dst_bits":bits(carry[j+1])}
          for j in range(length)]
    cut=2
    detached=[]
    for j in range(7):
        z=rng.randrange(65536)
        if j==0:
            while z==carry[cut]:z=rng.randrange(65536)
        detached.append({
            "from":f"detached{j}","to":f"exit{j}",
            "role":roles[(cut+j)%length],
            "src_bits":bits(forward(z)),
            "dst_bits":bits(rng.randrange(65536))
        })
    yes_edges=path+detached
    no_edges=copy.deepcopy(yes_edges)
    no_edges[cut]["src_bits"],no_edges[length]["src_bits"]=(
        no_edges[length]["src_bits"],no_edges[cut]["src_bits"])
    rng.shuffle(yes_edges)
    rng.shuffle(no_edges)
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in support[:24]]
    common={"start":"n0","target":f"n{length}",
            "roles":roles,"demos":demos}
    positive={**common,"edges":yes_edges}
    negative={**common,"edges":no_edges}
    topo=lambda g:sorted((e["from"],e["to"],e["role"]) for e in g["edges"])
    inventory=lambda g:sorted(tuple(e[key]) for e in g["edges"]
                              for key in ("src_bits","dst_bits"))
    need(symbolic_path(positive)==1 and symbolic_path(negative)==0,
         "PRIVATE_GRAPH_TRUTH_ONLY_EVALUATOR")
    need(inventory(positive)==inventory(negative)
         and topo(positive)==topo(negative),"HARD_NEGATIVE_SAME_INVENTORY")
    need(len(support)==48 and len(noisy)==6 and all(i<40 for i in noisy),
         "PUBLIC_SUPPORT_STRICT")
    return {"FIT":support[:40],"CHECK":support[40:],
            "positive":positive,"hard_negative":negative},{
        "fixture_type":"NONREGISTERED_SYNTHETIC_INTERSECTION_NOT_SCIENCE",
        "symbolic_positive_paths":1,
        "symbolic_hard_negative_paths":0,
        "source_private_corruption_indices":sorted(noisy),
        "case":case
    }
