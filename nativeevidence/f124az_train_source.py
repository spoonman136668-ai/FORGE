"""F124-AZ source-only first-birth adapter, TRAIN FIT and SCREEN ONLY.

Original frozen paired graph generator and 48-query issuance rebound to new,
precommitted source IDs. Learned models do NOT import this or see operator.
DEV range exists in registration but is inaccessible in this module.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import json,types
import f124ay_train_source as original
import f124ao_frozen_source as birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124az-frozen-public-gated-affine-feistel.json"
FREEZE_BLOB="9aaaef5c9b724be4afd0d7fa4783285139290540"
PARENT_SOURCE_BLOB="7ef2e017fb652f5f19c3ef54ae584c750a591f56"
PARENT_SHA="a1916139fbc2ce99e180c727ba94b716406aaefe"
COHORTS={"Yggdrasil":{"TRAIN":range(4700000,4700024),
                       "DEV":range(4700100,4700124)}}
OPERATORS={"TRAIN":("affine_AX443","feistel_K443","affine_AX449","feistel_K449"),
           "DEV":("affine_AX457","feistel_K457","affine_AX461","feistel_K461")}
VECTORS=original.VECTORS
FAMILIES=original.FAMILIES

def need(ok,tag):original.need(ok,"AY_"+tag)
def frozen():
    original.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(original.__file__)==PARENT_SOURCE_BLOB,
         "IMMUTABLE_ORIGINAL_FROZEN_SOURCE")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    s=d["source"]
    need(d["schema"]=="forge.research.f124az.preimplementation-frozen-joint-public-gated-inverse.v1"
         and d["status"]=="PREIMPLEMENTATION_FROZEN"
         and d["lineage"]["parent_AY_qualified_head"]==PARENT_SHA
         and s["TRAIN"]==[4700000,4700023] and s["DEV"]==[4700100,4700123]
         and s["operators_TRAIN"]==list(OPERATORS["TRAIN"])
         and s["operators_DEV"]==list(OPERATORS["DEV"])
         and s["public_responses_per_task"]==48
         and s["FIT_public_pairs"]==40 and s["CHECK_public_pairs"]==8
         and len(d["models"]["arms"])==8
         and d["models"]["original_active"]==7 and d["models"]["original_retained"]==9
         and all(v is False for v in d["authority"].values()),
         "FROZEN_FIT_SCREEN_AND_NO_DEV_AUTHORITY")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"])
         and set(COHORTS["Yggdrasil"]["TRAIN"]).isdisjoint(
             COHORTS["Yggdrasil"]["DEV"]),
         "HONEST_INDEPENDENT_COHORT")
    return d

RENV=dict(birth.RELATION.__globals__,OPERATORS=OPERATORS)
RELATION=types.FunctionType(birth.RELATION.__code__,RENV,
                            birth.RELATION.__name__,birth.RELATION.__defaults__)
PENV=dict(birth.PLAIN.__globals__,relation=RELATION)
PLAIN=types.FunctionType(birth.PLAIN.__code__,PENV,
                         birth.PLAIN.__name__,birth.PLAIN.__defaults__)

def relation(bits,op,inverse=False):return RELATION(bits,op,inverse)
def plain(g,op,nonce):return PLAIN(g,op,nonce)

def build(seed,vec,phase="TRAIN"):
    need(phase=="TRAIN" and type(seed) is int and
         seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS,"NO_DEV_BIRTH")
    env=dict(birth.build.__globals__,COHORTS=COHORTS,
             OPERATORS=OPERATORS,relation=relation,plain=plain)
    fn=types.FunctionType(birth.build.__code__,env,
                          birth.build.__name__,birth.build.__defaults__)
    fam,op,nonce,p,n,chosen=fn("Yggdrasil",seed,vec,phase)
    need(p["demos"]==n["demos"] and len(p["demos"])==24
         and sum(relation(d["input_bits"],op)!=d["output_bits"]
                 for d in p["demos"])==3,
         "ORIGINAL_NOISY_24_PAIR")
    return fam,op,nonce,p,n,chosen

def public48(seed,vec,op,condition,original_demos):
    need(type(seed) is int and seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS and op in OPERATORS["TRAIN"]
         and condition in ("balanced_basis48","random48"),
         "EQUAL_PUBLIC_QUERY_SOURCE_ONLY")
    env=dict(original.original.old.active_public_demos.__globals__,
             COHORTS=COHORTS,OPERATORS=OPERATORS,relation=relation)
    fn=types.FunctionType(original.original.old.active_public_demos.__code__,env,
                          original.original.old.active_public_demos.__name__,
                          original.original.old.active_public_demos.__defaults__)
    result=fn(seed,vec,op,condition,original_demos)
    need(len(result)==48 and
         sum(relation(x["input_bits"],op)!=x["output_bits"]
             for x in result)==6,
         "EXACT_EQUAL_PUBLIC_48_AND_NOISE")
    return result

def rows(stage):
    frozen()
    need(stage in ("FIT","SCREEN"),"TRAIN_SUBCOHORT_ONLY")
    start=COHORTS["Yggdrasil"]["TRAIN"].start
    seeds=range(start,start+12) if stage=="FIT" else range(start+12,start+24)
    result=[]
    for vec in VECTORS:
        for seed in seeds:
            fam,op,nonce,p,n,_=build(seed,vec,"TRAIN")
            result.append((seed,tuple(vec),fam,op,nonce,p,n))
    need(len(result)==24
         and Counter(x[2] for x in result)==Counter({f:6 for f in FAMILIES}),
         "UNSEEN_TRAIN_FOUR_FAMILY_DENOMINATOR")
    return result
