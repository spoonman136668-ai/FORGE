"""F124-AS independent source-only TRAIN cohort, no DEV construction path.

Exact source identity from qualified AR is verified, and the unchanged
first-admitted AO/AN paired graph constructor is rebound only to new,
precommitted seed/operator identities. Neither learned model imports this.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import json, types
import f124ar_train_source as prior
import f124ao_frozen_source as birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124as-frozen-noisy-relations-and-packed-forks.json"
FREEZE_BLOB="8920dcdc81e5cfb4355d0943eff1be359926ab04"
PARENT_BLOB="8fe8af6f16dbe730f791994252a2bf136be6f337"
COHORTS={
 "Yggdrasil":{"TRAIN":range(3400000,3400024),"DEV":range(3400100,3400124)},
 "Wingless":{"TRAIN":range(3410000,3410024),"DEV":range(3410100,3410124)}}
OPERATORS={
 "TRAIN":("affine_AX239","feistel_K239","affine_AX241","feistel_K241"),
 "DEV":("affine_AX251","feistel_K251","affine_AX257","feistel_K257")}
VECTORS=prior.VECTORS
FAMILIES=prior.FAMILIES

def need(ok,tag):prior.need(ok,"AS_"+tag)

def frozen():
    prior.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(prior.__file__)==PARENT_BLOB,
         "PREREGISTRATION_AND_QUALIFIED_PARENT_UNCHANGED")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    s=d["sources"]
    need(d["schema"]=="forge.research.f124as.preimplementation-frozen-noisy-relation-and-packed-forks.v1"
         and d["status"]=="PREIMPLEMENTATION_FROZEN"
         and d["parent"]["head"]=="bc5c1dad37637247f105c98d98c1dd0ed2ae1f92"
         and s["operators"]=={k:list(v) for k,v in OPERATORS.items()}
         and s["cohorts"]=={k:{t:[r.start,r.stop-1] for t,r in v.items()}
                            for k,v in COHORTS.items()}
         and s["corruptions"]==3
         and s["public_demos"]==24
         and all(x is False for x in d["authority"].values()),
         "NO_IDENTITY_OR_AUTHORITY_DRIFT")
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
