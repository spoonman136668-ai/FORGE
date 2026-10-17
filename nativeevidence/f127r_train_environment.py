"""F127-R new adversarial public TRAIN graph family, never protected CONFIRM.

Graph-local salted 16-bit tokens, 6-10 competing public paths, near-miss
junctions and label-balanced topology/token marginals. Oracle used ONLY for
source admissibility, not an inference feature.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import random

import f127r_freeze_admission as freeze

LANES={"Wingless":{"FIT":range(180100,180116),"TRAIN_CHECK":range(180116,180132)},
       "Yggdrasil":{"FIT":range(190100,190116),"TRAIN_CHECK":range(190116,190132)}}
FIELDS={"start","target","roles","edges"}
EDGE_FIELDS={"from","to","role","src_bits","dst_bits"}
BITS=16

class Invalid(ValueError):pass
def need(ok,why):
    if not ok:raise Invalid("F127R_GRAPH_"+why)

def digest(o):
    return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def validate(g):
    need(type(g) is dict and set(g)==FIELDS
         and type(g["start"]) is str and type(g["target"]) is str
         and g["start"]!=g["target"]
         and type(g["roles"]) is list and 3<=len(g["roles"])<=5
         and all(type(s) is str and s for s in g["roles"])
         and type(g["edges"]) is list and 2<=len(g["edges"])<=128,
         "PUBLIC_OBSERVATION")
    for e in g["edges"]:
        need(type(e) is dict and set(e)==EDGE_FIELDS
             and all(type(e[k]) is str and e[k] for k in ("from","to","role"))
             and all(type(e[k]) is list and len(e[k])==BITS and
                     all(type(z) is int and z in (0,1) for z in e[k])
                     for k in ("src_bits","dst_bits")),
             "RAW_PUBLIC_EDGE")

def graph_paths(g,require_tokens=False):
    validate(g)
    states=[(g["start"],None)]
    for role in g["roles"]:
        nxt=[]
        for node,last in states:
            for e in g["edges"]:
                if e["from"]!=node or e["role"]!=role:continue
                if require_tokens and last is not None and last!=e["src_bits"]:
                    continue
                nxt.append((e["to"],e["dst_bits"]))
                need(len(nxt)<=256,"PUBLIC_PATH_BUDGET")
        states=nxt
    return sum(node==g["target"] for node,_ in states)

def marginals(g):
    validate(g)
    return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
            Counter(tuple(v) for e in g["edges"]
                    for v in (e["src_bits"],e["dst_bits"])))

def pair_admit(p,n,path_count):
    validate(p);validate(n)
    need(p["roles"]==n["roles"] and
         p["start"]==n["start"] and p["target"]==n["target"] and
         marginals(p)==marginals(n),
         "PAIRED_MARGINAL_LEAKAGE")
    need(graph_paths(p)==path_count and graph_paths(n)==path_count,
         "PUBLIC_ROUTE_INVENTORY")
    need(graph_paths(p,True)==1 and graph_paths(n,True)==0,
         "SYMBOLIC_REFERENCE_LABELS")

def build(seed,vector,lane,stage):
    need(lane in LANES and stage in ('FIT','TRAIN_CHECK') and type(seed) is int and seed in LANES[lane][stage] and
         type(vector) is list and len(vector)==3 and
         all(type(x) is int and 0<=x<=3 for x in vector),
         "NOT_RESERVED_TRAIN_SOURCE")
    cfg,_=freeze.frozen()
    need(cfg["source_cohorts"][lane][stage]==
         [LANES[lane][stage].start,LANES[lane][stage].stop-1] and
         cfg["current_gate"]["protected_CONFIRM_used"] is False and
         cfg["source_cohorts"]["structure"][stage+"_depths"]==[3,5] and
         cfg["source_cohorts"]["structure"][stage+"_public_paths"]==[6,12],
         "FROZEN_FAMILY_CHANGED")
    context="F127R/PUBLIC/TRAIN/20261017/new-namespace/"+lane+"/"+stage+"/"+str(seed)+"/"+str(vector)
    rng=random.Random(int(hashlib.sha256(context.encode()).hexdigest()[:16],16))
    hops=3+(seed%3)
    paths=6+((seed+vector[0])%7)
    def node(tag):return hashlib.sha256((context+"/n/"+tag).encode()).hexdigest()[:24]
    start,target=node("start"),node("target")
    roles=[node("query-role-"+str(k)) for k in range(hops)]
    nodes=[[start]+[node("p"+str(p)+"_h"+str(h))
          for h in range(1,hops)]+[target] for p in range(paths)]
    # Shared-prefix and shared-suffix public edge, not an oracle feature.
    nodes[1][1]=nodes[0][1]
    nodes[2][-2]=nodes[0][-2]
    def token():return rng.randrange(0,1<<BITS)
    def near(b):
        flips=rng.sample(range(BITS),1+(rng.randrange(2)))
        n=b
        for bit in flips:n^=(1<<bit)
        return n
    def bits(x):return [(x>>k)&1 for k in range(BITS)]
    main=[token() for _ in range(hops+1)]
    # Unique values for the true chain avoid accidental zero-length aliases.
    while len(set(main))!=len(main):main=[token() for _ in range(hops+1)]
    edges=[]
    for i in range(hops):
        edges.append([nodes[0][i],nodes[0][i+1],roles[i],
                      main[i],main[i+1]])
    for p in range(1,paths):
        previous=None
        for i in range(hops):
            if p==1 and i==0:
                previous=main[1]
                continue
            if p==2 and i==hops-1:
                continue
            src=token() if previous is None else near(previous)
            dst=near(main[hops-1]) if p==2 and i==hops-2 else token()
            edges.append([nodes[p][i],nodes[p][i+1],roles[i],src,dst])
            previous=dst
    # Alias-heavy wrong-role distractors preserve token collisions outside
    # the requested query path and provide an inert counterfactual swap slot.
    decoy_idx=len(edges)
    distractor=node("wrong-role-distractor")
    for i in range(4):
        edges.append([start if i==0 else distractor,
                      distractor if i<3 else target,
                      node("off-role-"+str(i)),
                      main[i%len(main)], token()])
    neg=[list(e) for e in edges]
    target_join=max(1,hops//2)
    left=neg[target_join]
    right=neg[decoy_idx]
    need(left[3]!=right[3],"INERT_TRUE_ROUTE_SWAP")
    left[3],right[3]=right[3],left[3]
    rng.shuffle(edges);rng.shuffle(neg)
    def observation(rows):
        g={"start":start,"target":target,"roles":list(roles),
           "edges":[{"from":a,"to":b,"role":r,
                     "src_bits":bits(x),"dst_bits":bits(y)}
                    for a,b,r,x,y in rows]}
        validate(g)
        return g
    pos,negative=observation(edges),observation(neg)
    pair_admit(pos,negative,paths)
    return pos,negative

def cohort_rows(lane,vectors,stage):
    need(lane in LANES and stage in ('FIT','TRAIN_CHECK') and type(vectors) is list and len(vectors)==2
         and vectors[0]!=vectors[1],"SOURCE_VECTOR_IDENTITY")
    rows=[]
    for vector in vectors:
        for seed in LANES[lane][stage]:
            p,n=build(seed,vector,lane,stage)
            rows.extend(((p,1),(n,0)))
    need(len(rows)==64 and sum(y for _,y in rows)==32,
         "SOURCE_COHORT_INCOMPLETE")
    return rows
