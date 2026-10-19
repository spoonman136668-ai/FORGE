"""F124-CC disposable 2-case engineering source, defined in frozen precode.

This arithmetic construction is authored on the same research account and
IS NOT independently originated scientific transfer. It consumes none of
F124-BV reserved source families, prior CB/CA/BY cases, or heldout identities.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import random

FROZEN=Path(__file__).with_name("f124cc-frozen-trained-two-link.json")


def need(ok,msg):
    if not ok:raise ValueError("F124CC_FIXTURE_"+msg)


def bitvec(x):
    return [(x>>i)&1 for i in range(16)]


def integer(v):
    return sum(bit<<i for i,bit in enumerate(v))


def prior(case):
    d=json.loads(FROZEN.read_text())
    opts=d["new_predeclared_nonregistered_sources"]
    found=[entry for entry in opts if entry["id"]==case]
    need(len(found)==1,"EXACT_PREBIRTH_SOURCE_AND_SEED")
    return found[0]


def apply(x,p):
    src=[(x>>(4*i))&15 for i in range(4)]
    perm=p["perm"];g=p["gains"];bias=p["bias"];links=p["links"]
    out=[(g[j]*src[perm[j]]+bias[j])&15 for j in range(4)]
    if links[0]:out[0]^=out[1]
    if links[1]:out[2]^=out[3]
    return sum(z<<(4*j) for j,z in enumerate(out))


def invert(y,p):
    val=[(y>>(4*i))&15 for i in range(4)]
    links=p["links"];perm=p["perm"];g=p["gains"];bias=p["bias"]
    if links[0]:val[0]^=val[1]
    if links[1]:val[2]^=val[3]
    src=[0]*4
    for j in range(4):
        src[perm[j]]=(pow(g[j],-1,16)*(val[j]-bias[j]))&15
    return sum(z<<(4*i) for i,z in enumerate(src))


def truly_causal(graph,params):
    node=graph["start"]
    carry=None
    for role in graph["roles"]:
        edges=[e for e in graph["edges"] if e["from"]==node and e["role"]==role]
        if len(edges)!=1:return False
        edge=edges[0]
        source=invert(integer(edge["src_bits"]),params)
        if carry is not None and carry!=source:return False
        carry=integer(edge["dst_bits"])
        node=edge["to"]
    return node==graph["target"]


def make(case):
    p=prior(case)
    rng=random.Random(p["seed"])
    samples=rng.sample(range(65536),48)
    noise={1,5,12,19,24,35}
    public=[(x,apply(x,p)^(1 if j in noise else 0))
            for j,x in enumerate(samples)]
    tag=hashlib.sha256(("F124CC-NEW-PRECODE-ONLY-"+case).encode()).hexdigest()[:12]
    length=p["hops"]
    roles=[f"rel_task_{tag}:binding_{j}" for j in range(length)]
    state=rng.sample(range(65536),length+1)
    real=[{
        "from":f"src{j}","to":f"src{j+1}","role":roles[j],
        "src_bits":bitvec(apply(state[j],p)),
        "dst_bits":bitvec(state[j+1])
    } for j in range(length)]
    off=[]
    for j in range(9):
        x=rng.randrange(65536)
        if j==0:
            while x==state[3]:x=rng.randrange(65536)
        off.append({
            "from":f"unused{j}","to":f"dead{j}",
            "role":roles[(3+j)%length],
            "src_bits":bitvec(apply(x,p)),
            "dst_bits":bitvec(rng.randrange(65536))
        })
    good=real+off
    bad=copy.deepcopy(good)
    bad[3]["src_bits"],bad[length]["src_bits"]=(
        bad[length]["src_bits"],bad[3]["src_bits"])
    rng.shuffle(good);rng.shuffle(bad)
    demos=[{"input_bits":bitvec(x),"output_bits":bitvec(y)}
           for x,y in public[:24]]
    base={"start":"src0","target":f"src{length}","roles":roles,"demos":demos}
    good_g={**base,"edges":good}
    bad_g={**base,"edges":bad}
    topo=lambda z:sorted((e["from"],e["to"],e["role"]) for e in z["edges"])
    invent=lambda z:sorted(tuple(e[k]) for e in z["edges"]
                           for k in ("src_bits","dst_bits"))
    need(truly_causal(good_g,p) and not truly_causal(bad_g,p),
         "REQUIRED_POSITIVE_AND_HARD_NEGATIVE")
    need(topo(good_g)==topo(bad_g)
         and invent(good_g)==invent(bad_g),
         "TOKEN_AND_TOPOLOGY_MATCHED_HARD_NEGATIVE")
    need(len(public)==48 and len(set(x for x,y in public))==48,
         "PUBLIC_INPUTS_FROZEN_NO_DUPLICATE")
    return {"FIT":public[:40],"CHECK":public[40:],
            "positive":good_g,"hard_negative":bad_g},{
      "role":"SOURCE_PRIVATE_SYMBOLIC_ORACLE_ONLY",
      "reserved_scientific_source_used":False,
      "protected_cohort_used":False,
      "new_independent_source_author":False,
      "symbolic_positive":True,
      "symbolic_hard_negative":True
    }


if __name__=="__main__":
    raise SystemExit("ONLY_PREDECLARED_SYNTHETIC_ENGINEERING_FIXTURES")
