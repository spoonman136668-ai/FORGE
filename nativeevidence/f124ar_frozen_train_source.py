"""F124-AR new independently frozen source: exclusively TRAIN.

Evaluator-only operator inverses, original source birth, no modification to
any earlier negative. No candidate module may import this source file.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json,types
import f124aq_train_source as parent
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ar-frozen-failure-isolation.json"
FREEZE_BLOB="952bbe93d732890eeb6ad8c201ea07feb46b3609"
PARENT_BLOB="7899ce9c63f040823fec73657154e5245feb7899"
COHORTS={
 "Yggdrasil":{"TRAIN":range(3000000,3000024),"DEV":range(3000100,3000124)},
 "Wingless":{"TRAIN":range(3010000,3010024),"DEV":range(3010100,3010124)}}
OPERATORS={
 "TRAIN":("affine_AX197","feistel_K197","affine_AX199","feistel_K199"),
 "DEV":("affine_AX211","feistel_K211","affine_AX223","feistel_K223")}
VECTORS=parent.VECTORS
FAMILIES=parent.FAMILIES

def need(ok,label):q.need(ok,"F124AR_"+label)
def frozen():
    parent.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(parent.__file__)==PARENT_BLOB,
         "IMMUTABLE_PREIMPLEMENTATION_SOURCE")
    x=json.loads(FREEZE.read_text(encoding="utf-8"))
    s=x["fresh_source"]
    need(x["schema"]=="forge.research.f124ar.frozen-causal-failure-isolation.v1"
         and x["status"]=="PREIMPLEMENTATION_FROZEN"
         and x["source_parent"]["head"]=="cb2d4ff16e8054e790a0f1dfb4e558b97ebcb3a1"
         and s["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and s["DEV_operators"]==list(OPERATORS["DEV"])
         and all(s[l]=={p:[v.start,v.stop-1] for p,v in COHORTS[l].items()}
                 for l in COHORTS)
         and s["no_DEV"] is True
         and all(v is False for v in x["qualification"]["authority"].values()),
         "FROZEN_SOURCE_NO_AUTHORITY")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]),
         "DISJOINT_OPERATOR_BIRTH")
    return x

RENV=dict(parent.RELATION.__globals__,OPERATORS=OPERATORS)
RELATION=types.FunctionType(parent.RELATION.__code__,RENV,
                            parent.RELATION.__name__,parent.RELATION.__defaults__)
PENV=dict(parent.PLAIN.__globals__,relation=RELATION)
PLAIN=types.FunctionType(parent.PLAIN.__code__,PENV,
                         parent.PLAIN.__name__,parent.PLAIN.__defaults__)
def relation(bits,operator,inverse=False):return RELATION(bits,operator,inverse)
def plain(graph,operator,nonce):return PLAIN(graph,operator,nonce)

def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase=="TRAIN" and
         type(seed) is int and seed in COHORTS[lane]["TRAIN"]
         and tuple(vector) in VECTORS,"DEV_SOURCE_INACCESSIBLE")
    env=dict(parent.build.__globals__)
    env.update(COHORTS=COHORTS,OPERATORS=OPERATORS,
               relation=relation,plain=plain)
    fn=types.FunctionType(parent.build.__code__,env,
                          parent.build.__name__,parent.build.__defaults__)
    fam,operator,nonce,pos,neg,selected=fn(lane,seed,vector,phase)
    need(pos["demos"]==neg["demos"] and len(pos["demos"])==24 and
         sum(relation(d["input_bits"],operator)!=d["output_bits"]
             for d in pos["demos"])==3,"PAIRED_THREE_CORRUPTIONS")
    return fam,operator,nonce,pos,neg,selected

def pairs(lane,phase):
    need(lane in COHORTS and phase=="TRAIN","NO_DEV_CONSTRUCTION")
    rows=[]
    for vector in VECTORS:
        for seed in COHORTS[lane]["TRAIN"]:
            fam,operator,nonce,pos,neg,key=build(lane,seed,vector,"TRAIN")
            rows.append((key,tuple(vector),fam,operator,nonce,pos,neg))
    need(len(rows)==48 and
         Counter(x[2] for x in rows)==
         Counter({fam:12 for fam in FAMILIES}),
         "FROZEN_FOUR_FAMILIES")
    return rows
