"""F124-AT independent source-only TRAIN cohort, no DEV construction path.

Exact source identity from qualified AR is verified, and the unchanged
first-admitted AO/AN paired graph constructor is rebound only to new,
precommitted seed/operator identities. Neither learned model imports this.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import json, types
import f124as_train_source as prior
import f124ao_frozen_source as birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124at-frozen-identifiability-and-packed-collision.json"
FREEZE_BLOB="45dca352cd732358b1dd02b05bf9661c4ed37dc5"
PARENT_BLOB="7b20f61d7f4257f76297f173e3c8805b8ace88ef"
COHORTS={
 "Yggdrasil":{"TRAIN":range(3700000,3700024),"DEV":range(3700100,3700124)},
 "Wingless":{"TRAIN":range(3710000,3710024),"DEV":range(3710100,3710124)}}
OPERATORS={
 "TRAIN":("affine_AX283","feistel_K283","affine_AX293","feistel_K293"),
 "DEV":("affine_AX307","feistel_K307","affine_AX311","feistel_K311")}
VECTORS=prior.VECTORS
FAMILIES=prior.FAMILIES

def need(ok,tag):prior.need(ok,"AT_"+tag)

def frozen():
    prior.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(prior.__file__)==PARENT_BLOB,
         "PREREGISTRATION_AND_QUALIFIED_PARENT_UNCHANGED")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    src=d["source"]
    need(d["schema"]=="forge.research.f124at.frozen-inverse-identifiability-packed-collision.v1"
         and d["status"]=="PREIMPLEMENTATION_FROZEN"
         and d["lineage"]["qualified_parent"]==
             "449fc54cecccb6e30eaa13016f9d1828532714ac"
         and src["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and src["DEV_operators"]==list(OPERATORS["DEV"])
         and all(src[k]=={phase:[r.start,r.stop-1]
                              for phase,r in COHORTS[k].items()}
                 for k in COHORTS)
         and src["corrupted_output_bits"]==3
         and src["public_demos"]==24
         and all(value is False for value in d["authority"].values()),
         "NO_SOURCE_OR_AUTHORITY_DRIFT")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]),
         "OPERATOR_SPLIT_DISJOINT")
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
