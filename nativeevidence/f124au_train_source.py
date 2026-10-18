"""F124-AU independent frozen TRAIN source, explicitly forbids new DEV use.

Reuses first-admitted source-birth functions with *only* frozen source IDs
rebound. Model code must never import this adapter or evaluator inverse.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json
import types

import f124at_train_source as prior
import f124ao_frozen_source as birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/(
    "reference/research-intake/f124au-frozen-public-relation-and-packed-witness.json")
FREEZE_BLOB="421785b12f13a9675e682d07489ca3cca934332c"
PARENT_BLOB="e4da961ea74eb286824487c6f20fb3327ae40dc5"
PARENT_QUALIFIED="8b910711c143e9ab2940b61969824957d3fee1f9"
COHORTS={
    "Yggdrasil":{"TRAIN":range(4100000,4100024),"DEV":range(4100100,4100124)},
    "Wingless":{"TRAIN":range(4110000,4110024),"DEV":range(4110100,4110124)},
}
OPERATORS={
    "TRAIN":("affine_AX359","feistel_K359","affine_AX367","feistel_K367"),
    "DEV":("affine_AX373","feistel_K373","affine_AX379","feistel_K379"),
}
VECTORS=prior.VECTORS
FAMILIES=prior.FAMILIES

def need(ok,tag):
    prior.need(ok,"AU_"+tag)

def frozen():
    prior.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(prior.__file__)==PARENT_BLOB,
         "FIRST_FREEZE_AND_SOURCE_ANCESTRY")
    data=json.loads(FREEZE.read_text(encoding="utf-8"))
    source=data["source"]
    need(data["schema"]==
         "forge.research.f124au.preimplementation-frozen-agnostic-relations-and-packed-witness.v1"
         and data["status"]=="PREIMPLEMENTATION_FROZEN"
         and data["lineage"]["qualified_AT_parent"]==PARENT_QUALIFIED
         and source["cohorts"]=={lane:{phase:[r.start,r.stop-1]
                           for phase,r in co.items()}
                                for lane,co in COHORTS.items()}
         and source["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and source["DEV_operators"]==list(OPERATORS["DEV"])
         and source["pairs_per_lane_split"]==48
         and source["public_demonstrations"]==24
         and source["corrupted_public_outputs"]==3
         and all(v is False for v in data["qualification"]["authority"].values()),
         "ORIGINAL_REGISTRATION_CONTRACT")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]),
         "INDEPENDENT_OPERATOR_SPLITS")
    for lane in COHORTS:
        need(set(COHORTS[lane]["TRAIN"]).isdisjoint(COHORTS[lane]["DEV"]),
             "INDEPENDENT_COHORT_SPLITS")
    return data

RELENV=dict(birth.RELATION.__globals__,OPERATORS=OPERATORS)
RELATION=types.FunctionType(birth.RELATION.__code__,RELENV,
                            birth.RELATION.__name__,birth.RELATION.__defaults__)
PLAINENV=dict(birth.PLAIN.__globals__,relation=RELATION)
PLAIN=types.FunctionType(birth.PLAIN.__code__,PLAINENV,
                         birth.PLAIN.__name__,birth.PLAIN.__defaults__)
def relation(bits,op,inverse=False):
    return RELATION(bits,op,inverse)
def plain(graph,op,nonce):
    return PLAIN(graph,op,nonce)

def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase=="TRAIN"
         and type(seed) is int and seed in COHORTS[lane]["TRAIN"]
         and tuple(vector) in VECTORS,
         "DEV_SOURCE_CONSTRUCTION_FORBIDDEN")
    env=dict(birth.build.__globals__)
    env.update(COHORTS=COHORTS,OPERATORS=OPERATORS,
               relation=relation,plain=plain)
    fn=types.FunctionType(birth.build.__code__,env,birth.build.__name__,
                          birth.build.__defaults__)
    family,op,nonce,pos,neg,selected=fn(lane,seed,vector,phase)
    demos=pos["demos"]
    need(len(demos)==24 and demos==neg["demos"] and
         sum(relation(d["input_bits"],op)!=d["output_bits"]
             for d in demos)==3,"PUBLIC_NOISE_THREE_SYMMETRIC")
    return family,op,nonce,pos,neg,selected

def pairs(lane,phase):
    need(lane in COHORTS and phase=="TRAIN",
         "NO_DEV_ADAPTER_PATH")
    rows=[]
    for vector in VECTORS:
        for seed in COHORTS[lane]["TRAIN"]:
            family,op,nonce,p,n,selected=build(lane,seed,vector,phase)
            rows.append((selected,tuple(vector),family,op,nonce,p,n))
    need(len(rows)==48 and
         Counter(x[2] for x in rows)==Counter({f:12 for f in FAMILIES}),
         "COMPLETE_48_FOUR_FAMILY_TRAIN")
    return rows
