"""F124-AQ new TRAIN source only; DEV is deliberately inaccessible.

Exact AP first-admitted construction code is rebound to fresh immutable
operator/seed identities. The source/evaluator oracle is never model input.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import json,types
import f124ap_frozen_train_source as parent
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124aq-frozen-compositional-parity-and-local-contrast.json"
FREEZE_BLOB="e0a29f6062c45646eb72a31d06be961a7262f1e1"
PARENT_BLOB="d56cacd61d3a37aea3d10e789b993b631ebbcc01"
COHORTS={
 "Yggdrasil":{"TRAIN":range(2900000,2900024),"DEV":range(2900100,2900124)},
 "Wingless":{"TRAIN":range(2910000,2910024),"DEV":range(2910100,2910124)}}
OPERATORS={
 "TRAIN":("affine_AX173","feistel_K173","affine_AX179","feistel_K179"),
 "DEV":("affine_AX181","feistel_K181","affine_AX191","feistel_K191")}
FAMILIES=parent.FAMILIES
VECTORS=parent.VECTORS

def need(ok,name):q.need(ok,"F124AQ_"+name)
def frozen():
    parent.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(parent.__file__)==PARENT_BLOB,
         "IMMUTABLE_NEW_SOURCE_AND_PARENT")
    data=json.loads(FREEZE.read_text(encoding="utf-8"))
    src=data["fresh_source"]
    need(data["schema"]==
         "forge.research.f124aq.frozen-compositional-parity-and-local-causal-contrast.v1"
         and data["status"]=="PREIMPLEMENTATION_FROZEN"
         and data["lineage"]["parent_head"]==
             "18081dadc80a536adc9d0fe1241b5991b4b69bcb"
         and src["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and src["DEV_operators"]==list(OPERATORS["DEV"])
         and all(src[l]=={k:[v.start,v.stop-1]
                          for k,v in COHORTS[l].items()} for l in COHORTS)
         and all(v is False for v in data["qualification"]["authority"].values()),
         "FROZEN_SOURCE_NO_AUTHORITY")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]),
         "NO_OPERATOR_REUSE")
    return data

RENV=dict(parent.RELATION.__globals__,OPERATORS=OPERATORS)
RELATION=types.FunctionType(parent.RELATION.__code__,RENV,
                            parent.RELATION.__name__,parent.RELATION.__defaults__)
PENV=dict(parent.PLAIN.__globals__,relation=RELATION)
PLAIN=types.FunctionType(parent.PLAIN.__code__,PENV,
                         parent.PLAIN.__name__,parent.PLAIN.__defaults__)
def relation(bits,op,inverse=False):return RELATION(bits,op,inverse)
def plain(graph,op,nonce):return PLAIN(graph,op,nonce)

def build(lane,seed,vec,phase):
    need(phase=="TRAIN" and lane in COHORTS and
         type(seed) is int and seed in COHORTS[lane]["TRAIN"] and
         tuple(vec) in VECTORS,"DEV_FORBIDDEN_TRAIN_ONLY")
    env=dict(parent.build.__globals__)
    env.update(COHORTS=COHORTS,OPERATORS=OPERATORS,
               relation=relation,plain=plain)
    fn=types.FunctionType(parent.build.__code__,env,
                          parent.build.__name__,parent.build.__defaults__)
    family,op,nonce,p,n,selected=fn(lane,seed,vec,phase)
    need(p["demos"]==n["demos"] and
         sum(relation(d["input_bits"],op)!=d["output_bits"]
             for d in p["demos"])==3,"SYMMETRIC_THREE_NOISY_DEMOS")
    return family,op,nonce,p,n,selected

def pairs(lane,phase):
    need(lane in COHORTS and phase=="TRAIN","DEV_SOURCE_CONSTRUCTION_FORBIDDEN")
    rows=[]
    for vec in VECTORS:
        for seed in COHORTS[lane]["TRAIN"]:
            fam,op,nonce,p,n,selected=build(lane,seed,vec,phase)
            rows.append((selected,tuple(vec),fam,op,nonce,p,n))
    need(len(rows)==48 and
         Counter(x[2] for x in rows)==Counter({f:12 for f in FAMILIES}),
         "NEW_TRAIN_FAMILY_DENOMINATOR")
    return rows
