"""Independently born F124-BM ARX word-relational causal source.

Source grammar differs from independently born GF2 family: three nonlinear
modular odd multiplications, word rotations and XOR phases. FIT only.
No candidate, native scorer, private evaluation or previous source imports.
"""
from __future__ import annotations

import copy
import hashlib
import random

FIT=range(915000,915016)
HOLDOUT=range(915100,915228)
SALT=b"F124BM-REVERSIBLE-THREE-STAGE-ARX-WORD-v1"


def need(ok,tag):
    if not ok:
        raise ValueError("BM_ARX_"+tag)


def bits(x):
    return [(x>>i)&1 for i in range(16)]


def value(v):
    return sum(int(t)<<i for i,t in enumerate(v))


def rot(x,r):
    return ((x<<r)|(x>>(16-r)))&65535


def unrot(x,r):
    return ((x>>r)|(x<<(16-r)))&65535


def forward(x,key):
    for a,b,r,salt in key:
        x=rot((x*a+b)&65535,r)^salt
    return x


def inverse(y,key):
    for a,b,r,salt in reversed(key):
        y=((unrot(y^salt,r)-b)*pow(a,-1,65536))&65535
    return y


def exact(g,key):
    candidates=[(g["start"],None)]
    for role in g["roles"]:
        out=[]
        for node,carry in candidates:
            for e in g["edges"]:
                if e["from"]!=node or e["role"]!=role:
                    continue
                source=inverse(value(e["src_bits"]),key)
                if carry is None or carry==source:
                    out.append((e["to"],value(e["dst_bits"])))
        candidates=out
    return sum(n==g["target"] for n,c in candidates)


def make(seed):
    need(type(seed) is int and seed in FIT,"ONLY_NEW_PUBLIC_FIT_NOT_HELDOUT")
    digest=hashlib.sha256(SALT+b"/"+str(seed).encode()).digest()
    rng=random.Random(int.from_bytes(digest,"big"))
    key=tuple((rng.randrange(32768)*2+1,rng.randrange(65536),
               rng.randint(1,15),rng.randrange(65536)) for _ in range(3))
    points=rng.sample(range(65536),48)
    corrupt=set(rng.sample(range(48),6))
    public=[(x,forward(x,key)^(1 if idx in corrupt else 0))
            for idx,x in enumerate(points)]
    depth=7+(seed-FIT.start)%3
    nonce=hashlib.sha256(SALT+b"/role/"+str(seed).encode()).hexdigest()[:12]
    roles=[f"rel_task_{nonce}:h{idx}" for idx in range(depth)]
    carries=rng.sample(range(65536),depth+1)
    main=[{"from":f"p{j}","to":f"p{j+1}","role":roles[j],
           "src_bits":bits(forward(carries[j],key)),
           "dst_bits":bits(carries[j+1])} for j in range(depth)]
    distractor=[]
    broken_index=depth-2
    for j in range(6):
        x=rng.randrange(65536)
        if j==0:
            while x==carries[broken_index]:
                x=rng.randrange(65536)
        distractor.append({"from":f"side{j}","to":f"sink{j}",
                           "role":roles[(broken_index+j)%depth],
                           "src_bits":bits(forward(x,key)),
                           "dst_bits":bits(rng.randrange(65536))})
    main_edges=main+distractor
    hard=copy.deepcopy(main_edges)
    hard[broken_index]["src_bits"],hard[depth]["src_bits"]=(
        hard[depth]["src_bits"],hard[broken_index]["src_bits"])
    rng.shuffle(main_edges)
    rng.shuffle(hard)
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in public[:24]]
    common={"start":"p0","target":f"p{depth}","roles":roles,"demos":demos}
    pos={**common,"edges":main_edges}
    neg={**common,"edges":hard}
    def tokens(g):
        return sorted(tuple(e[t]) for e in g["edges"]
                      for t in ("src_bits","dst_bits"))
    def topology(g):
        return sorted((e["from"],e["to"],e["role"]) for e in g["edges"])
    need(exact(pos,key)==1 and exact(neg,key)==0,
         "CAUSAL_LABEL_TRUTH")
    need(tokens(pos)==tokens(neg) and topology(pos)==topology(neg)
         and len(main_edges)>=13 and len(corrupt)==6,
         "INVENTORY_PRESERVED")
    return {"FIT":public[:40],"CHECK":public[40:],
            "positive":pos,"hard_negative":neg},{
                "source_operator_private":key,
                "source_corruption_private":tuple(sorted(corrupt)),
                "oracle_positive":1,"oracle_negative":0,
                "FIT_seed":seed,"source_family_private":"TRIPLE_ARX_NONCOMMUTING"}
