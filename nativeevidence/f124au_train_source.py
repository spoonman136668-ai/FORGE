"""F124-AU independent source-only TRAIN cohort, no DEV construction path.

Exact source identity from qualified AR is verified, and the unchanged
first-admitted AO/AN paired graph constructor is rebound only to new,
precommitted seed/operator identities. Neither learned model imports this.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import json, types
import f124at_train_source as prior
import f124ao_frozen_source as birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124au-frozen-public-parity-and-onepacked-policy.json"
FREEZE_BLOB="73476e75eec999cf246f4416a8d371c6e1eec0df"
PARENT_BLOB="e4da961ea74eb286824487c6f20fb3327ae40dc5"
COHORTS={
 "Yggdrasil":{"TRAIN":range(4000000,4000024),"DEV":range(4000100,4000124)},
 "Wingless":{"TRAIN":range(4010000,4010024),"DEV":range(4010100,4010124)}}
OPERATORS={
 "TRAIN":("affine_AX331","feistel_K331","affine_AX337","feistel_K337"),
 "DEV":("affine_AX347","feistel_K347","affine_AX349","feistel_K349")}
VECTORS=prior.VECTORS
FAMILIES=prior.FAMILIES

def need(ok,tag):prior.need(ok,"AU_"+tag)

def frozen():
    prior.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(prior.__file__)==PARENT_BLOB,
         "FROZEN_SOURCE_AND_PARENT_BIRTH")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    source=d["source"]
    need(d["schema"]=="forge.research.f124au.frozen-public-parity-conditional-single-packed.v1"
         and d["status"]=="PREIMPLEMENTATION_FROZEN"
         and d["lineage"]["parent_head"]==
             "b5bb419f9d406bf3d35b868431310cd82e68b7c4"
         and source["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and source["DEV_operators"]==list(OPERATORS["DEV"])
         and all(source[k]=={phase:[r.start,r.stop-1]
                             for phase,r in COHORTS[k].items()}
                 for k in COHORTS)
         and source["public_demos"]==24
         and source["public_corrupted_outputs"]==3
         and all(v is False for v in d["authority"].values()),
         "FROZEN_IDENTITY_AND_LIMITS")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]),
         "NO_DEV_OPERATOR_REUSE")
    return d

RENV=dict(birth.RELATION.__globals__, OPERATORS=OPERATORS)
RELATION=types.FunctionType(birth.RELATION.__code__, RENV,
                            birth.RELATION.__name__, birth.RELATION.__defaults__)
PENV=dict(birth.PLAIN.__globals__,relation=RELATION)
PLAIN=types.FunctionType(birth.PLAIN.__code__,PENV,
                         birth.PLAIN.__name__,birth.PLAIN.__defaults__)

def relation(bits,op,inverse=False):return RELATION(bits,op,inverse)
def plain(g,op,nonce):return PLAIN(g,op,nonce)

def build(lane,seed,v,phase):
    need(lane in COHORTS and phase=="TRAIN" and type(seed) is int
         and seed in COHORTS[lane]["TRAIN"] and tuple(v) in VECTORS,
         "SOURCE_BIRTH_REJECT_DEV")
    env=dict(birth.build.__globals__)
    env.update(COHORTS=COHORTS,OPERATORS=OPERATORS,
               relation=relation,plain=plain)
    f=types.FunctionType(birth.build.__code__,env,
                         birth.build.__name__,birth.build.__defaults__)
    fam,op,nonce,p,n,selected=f(lane,seed,v,phase)
    need(p["demos"]==n["demos"] and len(p["demos"])==24
         and sum(relation(x["input_bits"],op)!=x["output_bits"]
                 for x in p["demos"])==3,
         "EXACT_PUBLIC_CORRUPTION_AND_PAIRED_SUPPORT")
    return fam,op,nonce,p,n,selected

def pairs(lane,phase):
    need(lane in COHORTS and phase=="TRAIN",
         "NO_NEW_DEV_SOURCE_FIRST_USE")
    rows=[]
    for v in VECTORS:
        for seed in COHORTS[lane]["TRAIN"]:
            fam,op,nonce,p,n,selected=build(lane,seed,v,phase)
            rows.append((selected,tuple(v),fam,op,nonce,p,n))
    need(len(rows)==48 and
         Counter(x[2] for x in rows)==Counter({f:12 for f in FAMILIES}),
         "FRESH_TRAIN_FOUR_FAMILIES")
    return rows
