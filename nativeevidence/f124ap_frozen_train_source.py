"""F124-AP immutable new TRAIN source, no DEV construction in this gate.

The original AO first-admitted paired source/restore functions are rebound
only to independently preregistered cohorts and operator names. This is
source/evaluator code and MUST NOT be imported by model inference modules.
"""
from __future__ import annotations
import json,types
from pathlib import Path
from collections import Counter
import f124ao_frozen_source as parent
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ap-frozen-kernel-relations-and-hop-evidence.json"
FREEZE_BLOB="4ceb1d410001cfb56d0be5e4b6eb8b17cf4cade9"
PARENT_SOURCE_BLOB="6c6bd9b685b8ad6b1b3685f95959947c4940f2ff"
COHORTS={
 "Yggdrasil":{"TRAIN":range(2800000,2800024),"DEV":range(2800100,2800124)},
 "Wingless":{"TRAIN":range(2810000,2810024),"DEV":range(2810100,2810124)}}
OPERATORS={
 "TRAIN":("affine_AX149","feistel_K151","affine_AX157","feistel_K157"),
 "DEV":("affine_AX163","feistel_K163","affine_AX167","feistel_K167")}
FAMILIES=parent.FAMILIES
VECTORS=parent.VECTORS

def need(ok,label):q.need(ok,"F124AP_"+label)

def frozen():
    parent.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and witness.blob(parent.__file__)==PARENT_SOURCE_BLOB,
         "PREIMPLEMENTATION_FROZEN_BLOB")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    src=p["sources"]
    need(p["schema"]=="forge.research.f124ap.frozen-dual-kernel-inverse-and-single-packed-hop-causality.v1"
         and p["status"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["qualified_parent_head"]=="a0d15c8cf307a9c7972728899b525f79717049c7"
         and src["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and src["DEV_operators"]==list(OPERATORS["DEV"])
         and all(src[k]=={s:[v.start,v.stop-1]
                          for s,v in COHORTS[k].items()} for k in COHORTS)
         and src["corrupted_output_bits"]==3
         and all(v is False for v in p["qualification"]["authority"].values()),
         "NO_SOURCE_AUTHORITY_DRIFT")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]),
         "INDEPENDENT_NEW_OPERATORS")
    return p

RENV=dict(parent.RELATION.__globals__,OPERATORS=OPERATORS)
RELATION=types.FunctionType(parent.RELATION.__code__,RENV,
                            parent.RELATION.__name__,parent.RELATION.__defaults__)
PENV=dict(parent.PLAIN.__globals__,relation=RELATION)
PLAIN=types.FunctionType(parent.PLAIN.__code__,PENV,
                         parent.PLAIN.__name__,parent.PLAIN.__defaults__)
def relation(bits,operator,inverse=False): return RELATION(bits,operator,inverse)
def plain(graph,operator,nonce): return PLAIN(graph,operator,nonce)

def build(lane,seed,vector,phase):
    need(phase=="TRAIN" and lane in COHORTS and
         type(seed) is int and seed in COHORTS[lane]["TRAIN"]
         and tuple(vector) in VECTORS,
         "NO_DEV_SOURCE_BEFORE_INDEPENDENT_FIRST_USE")
    env=dict(parent.build.__globals__)
    env.update(COHORTS=COHORTS,OPERATORS=OPERATORS,
               relation=relation,plain=plain)
    fn=types.FunctionType(parent.build.__code__,env,
                          parent.build.__name__,parent.build.__defaults__)
    fam,operator,nonce,p,n,selected=fn(lane,seed,vector,phase)
    need(p["demos"]==n["demos"] and len(p["demos"])==24
         and sum(relation(x["input_bits"],operator)!=x["output_bits"]
                 for x in p["demos"])==3,"NOISE_PAIRED_SYMMETRY")
    return fam,operator,nonce,p,n,selected

def pairs(lane,phase):
    need(phase=="TRAIN" and lane in COHORTS,
         "TRAIN_ONLY_NO_DEV_CONSTRUCTION")
    rows=[]
    for vec in VECTORS:
        for seed in COHORTS[lane]["TRAIN"]:
            fam,operator,nonce,p,n,chosen=build(lane,seed,vec,phase)
            rows.append((chosen,tuple(vec),fam,operator,nonce,p,n))
    need(len(rows)==48 and Counter(x[2] for x in rows)==
         Counter({fam:12 for fam in FAMILIES}),
         "INDEPENDENT_TRAIN_FOUR_FAMILIES")
    return rows
