"""F124-CA 2 disposable source-neutral mathematical binding tasks.

These are NOT externally originated relationship families and NEVER occupy
original 924xxx / 925xxx identities. They must not be used to tune models
after first observation. Private symbolic truth verifies engineering
construction only, never passed to learner/scorer.
"""
from __future__ import annotations

import copy
import hashlib
import random

CASES={
 "CA-ENG-01":(630101,(3,0,1,2),(3,5,11,1),(6,4,12,9),0,8),
 "CA-ENG-02":(630102,(1,2,3,0),(1,7,5,1),(3,10,7,1),1,9)
}


def need(ok,reason):
    if not ok:raise ValueError("F124CA_NONREGISTERED_"+reason)


def bitvec(x):
    return [(x>>j)&1 for j in range(16)]


def integer(b):
    return sum(v<<i for i,v in enumerate(b))


def forward(x,perm,gains,bias,gate):
    need(0<=x<65536,"16BIT_BOUNDARY")
    nib=tuple((x>>(4*i))&15 for i in range(4))
    out=[(gains[j]*nib[perm[j]]+bias[j])&15 for j in range(4)]
    if gate:out[0]^=out[1]
    return sum(z<<(4*j) for j,z in enumerate(out))


def inverse(y,perm,gains,bias,gate):
    outs=[(y>>(4*i))&15 for i in range(4)]
    if gate:outs[0]^=outs[1]
    original=[0]*4
    for j in range(4):
        original[perm[j]]=(pow(gains[j],-1,16)*(outs[j]-bias[j]))&15
    return sum(z<<(4*j) for j,z in enumerate(original))


def symbolic(graph,perm,gains,bias,gate):
    current=graph["start"]
    carried=None
    for role in graph["roles"]:
        matches=[e for e in graph["edges"]
                 if e["from"]==current and e["role"]==role]
        if len(matches)!=1:return False
        edge=matches[0]
        inv=inverse(integer(edge["src_bits"]),perm,gains,bias,gate)
        if carried is not None and carried!=inv:return False
        carried=integer(edge["dst_bits"])
        current=edge["to"]
    return current==graph["target"]


def make(case):
    need(type(case) is str and case in CASES,"ONLY_TWO_PREDECLARED_TASKS")
    seed,perm,gains,bias,gate,hops=CASES[case]
    rng=random.Random(seed)
    xs=rng.sample(range(65536),48)
    noisy={1,5,12,19,24,35}
    pairs=[(x,forward(x,perm,gains,bias,gate)^(1 if i in noisy else 0))
           for i,x in enumerate(xs)]
    tag=hashlib.sha256(("F124CA-SOURCE-ONLY-"+case).encode()).hexdigest()[:12]
    roles=[f"rel_task_{tag}:step_{j}" for j in range(hops)]
    state=rng.sample(range(65536),hops+1)
    chain=[
        {"from":f"v{j}","to":f"v{j+1}","role":roles[j],
         "src_bits":bitvec(forward(state[j],perm,gains,bias,gate)),
         "dst_bits":bitvec(state[j+1])}
        for j in range(hops)]
    extra=[]
    for j in range(9):
        x=rng.randrange(65536)
        if j==0:
            while x==state[3]:x=rng.randrange(65536)
        extra.append({
          "from":f"off{j}","to":f"dead{j}",
          "role":roles[(3+j)%hops],
          "src_bits":bitvec(forward(x,perm,gains,bias,gate)),
          "dst_bits":bitvec(rng.randrange(65536))})
    good=chain+extra
    hard=copy.deepcopy(good)
    hard[3]["src_bits"],hard[hops]["src_bits"]=(
        hard[hops]["src_bits"],hard[3]["src_bits"])
    rng.shuffle(good)
    rng.shuffle(hard)
    demos=[{"input_bits":bitvec(x),"output_bits":bitvec(y)}
           for x,y in pairs[:24]]
    template={"start":"v0","target":f"v{hops}",
              "roles":roles,"demos":demos}
    positive={**template,"edges":good}
    negative={**template,"edges":hard}
    topology=lambda g:sorted((e["from"],e["to"],e["role"]) for e in g["edges"])
    inventory=lambda g:sorted(tuple(e[k]) for e in g["edges"]
                               for k in ("src_bits","dst_bits"))
    need(symbolic(positive,perm,gains,bias,gate),"SYMBOLIC_POSITIVE")
    need(not symbolic(negative,perm,gains,bias,gate),"SYMBOLIC_HARD_NEGATIVE")
    need(topology(positive)==topology(negative)
         and inventory(positive)==inventory(negative),
         "MATCHED_TOKEN_INVENTORY_AND_GRAPH_TOPOLOGY")
    return {"FIT":pairs[:40],"CHECK":pairs[40:],
            "positive":positive,"hard_negative":negative},{
      "case":case,"source_neutral_engineering_only":True,
      "private_oracle_never_model_input":True,
      "original_scientific_source_firstuse":False,
      "protected_cohorts_opened":False
    }


if __name__=="__main__":
    raise SystemExit("F124CA_NOT_AN_INDEPENDENT_SCIENTIFIC_ORIGIN")
