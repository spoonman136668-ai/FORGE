"""F124-BY precommitted, NONREGISTERED symbolic engineering panel only.

Reads source identities and seeds from preimplementation frozen protocol.
No module, source, holdout, new external creator, or previous science task is
used to generate these deliberately constructed forms.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import random

FROZEN=Path(__file__).with_name("f124by-frozen-panel.json")


def require(v,why):
    if not v:raise ValueError("F124BY_FROZEN_PANEL_"+why)


def profile(case):
    p=json.loads(FROZEN.read_text())
    require(p["schema"]=="mass.f124by.frozen-structural-composition-transfer.v1",
            "PROTO_ID")
    matches=[r for r in p["cases"] if r["id"]==case]
    require(len(matches)==1,"UNKNOWN_NONREGISTERED_CASE")
    return matches[0],tuple(p["coefficients"][matches[0]["grammar"]])


def bits(x):
    return [(x>>i)&1 for i in range(16)]


def asint(v):
    return sum(n<<i for i,n in enumerate(v))


def apply(v,m,mode):
    return ((v+m)&255) if mode==0 else v^m


def undo(v,m,mode):
    return ((v-m)&255) if mode==0 else v^m


def forward(x,entry,params):
    a,b,c,d,m1,m2=params
    lo=x&255
    hi=x>>8
    lo=apply(lo,(a*hi+b)&255,m1)
    hi=apply(hi,(c*lo+d)&255,m2)
    if entry["third"]:
        lo^=hi
    if entry["grammar"]=="four":
        hi^=lo
    return lo|(hi<<8)


def inverse(y,entry,params):
    a,b,c,d,m1,m2=params
    lo=y&255
    hi=y>>8
    if entry["grammar"]=="four":
        hi^=lo
    if entry["third"]:
        lo^=hi
    oldhi=undo(hi,(c*lo+d)&255,m2)
    oldlo=undo(lo,(a*oldhi+b)&255,m1)
    return oldlo|(oldhi<<8)


def actual_graph_validity(g,entry,params):
    node=g["start"]
    carried=None
    for role in g["roles"]:
        valid=[e for e in g["edges"] if e["from"]==node and e["role"]==role]
        if len(valid)!=1:return False
        e=valid[0]
        recovered=inverse(asint(e["src_bits"]),entry,params)
        if carried is not None and recovered!=carried:return False
        carried=asint(e["dst_bits"])
        node=e["to"]
    return node==g["target"]


def make(case):
    entry,params=profile(case)
    rng=random.Random(entry["seed"])
    xs=rng.sample(range(65536),48)
    noisy={1,5,12,19,24,35}
    support=[(x,forward(x,entry,params)^(1 if i in noisy else 0))
             for i,x in enumerate(xs)]
    hops=entry["hops"]
    tag=hashlib.sha256(("F124BY-ENGINEERING-"+case).encode()).hexdigest()[:12]
    roles=[f"rel_task_{tag}:segment_{j}" for j in range(hops)]
    state=rng.sample(range(65536),hops+1)
    chain=[{"from":f"v{j}","to":f"v{j+1}","role":roles[j],
            "src_bits":bits(forward(state[j],entry,params)),
            "dst_bits":bits(state[j+1])} for j in range(hops)]
    off=[]
    cut=3
    for j in range(9):
        val=rng.randrange(65536)
        if j==0:
            while val==state[cut]:val=rng.randrange(65536)
        off.append({
           "from":f"decoy{j}","to":f"unused{j}",
           "role":roles[(cut+j)%hops],
           "src_bits":bits(forward(val,entry,params)),
           "dst_bits":bits(rng.randrange(65536))})
    positive=chain+off
    negative=copy.deepcopy(positive)
    negative[cut]["src_bits"],negative[hops]["src_bits"]=(
        negative[hops]["src_bits"],negative[cut]["src_bits"])
    rng.shuffle(positive)
    rng.shuffle(negative)
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in support[:24]]
    common={"start":"v0","target":f"v{hops}","roles":roles,"demos":demos}
    pos={**common,"edges":positive}
    hard={**common,"edges":negative}
    inventory=lambda g:sorted(tuple(e[k]) for e in g["edges"]
                               for k in ("src_bits","dst_bits"))
    topology=lambda g:sorted((e["from"],e["to"],e["role"]) for e in g["edges"])
    require(actual_graph_validity(pos,entry,params),"REAL_CAUSAL_POSITIVE")
    require(not actual_graph_validity(hard,entry,params),"TRUE_HARD_NEGATIVE")
    require(inventory(pos)==inventory(hard) and topology(pos)==topology(hard),
            "MATCHED_EDGE_INVENTORY_AND_TOPOLOGY")
    require(len(support)==48 and all(i<40 for i in noisy),"FIT_ONLY_ERROR")
    return {"FIT":support[:40],"CHECK":support[40:],
            "positive":pos,"hard_negative":hard},{"source_neutral":True,
              "private_symbolic_oracle_only_fixture":True,
              "no_registered_science_firstuse":True,
              "fit_error_count":len(noisy)}


if __name__=="__main__":
    raise SystemExit("F124BY_ONLY_NONREGISTERED_ENGINEERING_CALLER")
