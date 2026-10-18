"""F124-AO prospectively frozen graph sources; evaluator inverses are NOT model inputs.

Rebind the exact immutable F124-AN paired first-admitted birth code with new
source IDs only. This module must NEVER be imported by the learned model.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import json, types
import f124an_frozen_source as parent
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ao-frozen-learned-relations-and-single-state-evidence.json"
FREEZE_BLOB="2c3a60739ad0bc9163f2d30e88390c4f8c20dd45"
PARENT_SOURCE_BLOB="0bdb7579050f90c078a5c05acc7faf77d2f9c5d4"
COHORTS={
 "Yggdrasil":{"TRAIN":range(2700000,2700024),"DEV":range(2700100,2700124)},
 "Wingless":{"TRAIN":range(2710000,2710024),"DEV":range(2710100,2710124)}}
OPERATORS={
 "TRAIN":("affine_AX107","feistel_K101","affine_AX109","feistel_K103"),
 "DEV":("affine_AX131","feistel_K127","affine_AX137","feistel_K137")}
FAMILIES=parent.FAMILIES
VECTORS=parent.VECTORS

def need(ok,tag): q.need(ok,"F124AO_"+tag)

def frozen():
    parent.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(parent.__file__)==PARENT_SOURCE_BLOB,
         "IMMUTABLE_PREIMPLEMENTATION_SOURCE")
    doc=json.loads(FREEZE.read_text(encoding="utf-8"))
    src=doc["source"]
    need(doc["schema"]=="forge.research.f124ao.frozen-learned-unknown-relations-and-one-packed-causal-evidence.v1"
         and doc["status"]=="PREIMPLEMENTATION_FROZEN"
         and doc["lineage"]["parent_head"]=="ca46eba41179a1c6d9cd0bfa74119782c6d11d88"
         and src["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and src["DEV_operators"]==list(OPERATORS["DEV"])
         and all(src[l]=={k:[v.start,v.stop-1] for k,v in COHORTS[l].items()}
                 for l in COHORTS)
         and src["public_output_bit_corruptions_per_graph"]==3
         and all(v is False for v in doc["authority"].values()),
         "IMMUTABLE_SOURCE_CONTRACT")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]),"OPERATOR_DISJOINTNESS")
    for lane in COHORTS:
        need(set(COHORTS[lane]["TRAIN"]).isdisjoint(COHORTS[lane]["DEV"]),
             "COHORT_DISJOINTNESS")
    return doc

RENV=dict(parent.RELATION.__globals__,OPERATORS=OPERATORS)
RELATION=types.FunctionType(parent.RELATION.__code__,RENV,
                            parent.RELATION.__name__,parent.RELATION.__defaults__)
PENV=dict(parent.PLAIN.__globals__,relation=RELATION)
PLAIN=types.FunctionType(parent.PLAIN.__code__,PENV,
                         parent.PLAIN.__name__,parent.PLAIN.__defaults__)

def relation(bits,operator,inverse=False): return RELATION(bits,operator,inverse)
def plain(graph,operator,nonce): return PLAIN(graph,operator,nonce)

def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("TRAIN","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in VECTORS,"SOURCE_BIRTH_RANGE")
    env=dict(parent.build.__globals__)
    env.update(COHORTS=COHORTS,OPERATORS=OPERATORS,
               relation=relation,plain=plain)
    fn=types.FunctionType(parent.build.__code__,env,
                          parent.build.__name__,parent.build.__defaults__)
    fam,operator,nonce,pos,neg,selected=fn(lane,seed,vector,phase)
    need(pos["demos"]==neg["demos"],"PAIRED_SUPPORT_SYMMETRY")
    need(sum(relation(d["input_bits"],operator)!=d["output_bits"]
             for d in pos["demos"])==3,"THREE_PUBLIC_CORRUPTIONS")
    return fam,operator,nonce,pos,neg,selected

def pairs(lane,phase):
    need(lane in COHORTS and phase in ("TRAIN","DEV"),"SOURCE_SPLIT")
    rows=[]
    for v in VECTORS:
        for seed in COHORTS[lane][phase]:
            fam,operator,nonce,pos,neg,chosen=build(lane,seed,v,phase)
            rows.append((chosen,tuple(v),fam,operator,nonce,pos,neg))
    need(len(rows)==48 and Counter(x[2] for x in rows)==
         Counter({fam:12 for fam in FAMILIES}),"NEW_SOURCE_FAMILY_COUNTS")
    return rows
