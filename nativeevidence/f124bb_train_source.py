"""F124-BB source-only first-birth adapter, TRAIN FIT and SCREEN ONLY.

Original frozen paired graph generator and 48-query issuance rebound to new,
precommitted source IDs. Learned models do NOT import this or see operator.
DEV range exists in registration but is inaccessible in this module.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import json,types
import f124ba_train_source as original
import f124ao_frozen_source as birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124bb-frozen-public-disagreement-veto.json"
FREEZE_BLOB="56e77ac974b4c4673d9d1ba5e012357719165711"
PARENT_SOURCE_BLOB="c605aca61d551889afdbdece173fa5f0fcdb5402"
PARENT_SHA="8796537b6d1ebcd0f8e5a9e2aecf93a06b094d93"
COHORTS={"Yggdrasil":{"TRAIN":range(5000000,5000024),
                       "DEV":range(5000100,5000124)}}
OPERATORS={"TRAIN":("affine_AX503","feistel_K503","affine_AX509","feistel_K509"),
           "DEV":("affine_AX521","feistel_K521","affine_AX523","feistel_K523")}
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
    need(d["schema"]=="forge.research.f124bb.preimplementation-disagreement-evidence-veto.v1"
         and d["status"]=="FROZEN_BEFORE_IMPLEMENTATION_OR_NEW_TRAIN"
         and d["lineage"]["qualified_BA_parent"]==PARENT_SHA
         and s["TRAIN"]==[5000000,5000023] and s["DEV"]==[5000100,5000123]
         and s["operators_TRAIN"]==list(OPERATORS["TRAIN"])
         and s["operators_DEV"]==list(OPERATORS["DEV"])
         and s["equal_public_rows_per_task"]==48
         and s["public_FIT_rows"]==40 and s["public_CHECK_rows"]==8
         and len(d["candidates"]["arms"])==10
         and d["candidates"]["original_active"]==7 and d["candidates"]["original_retained"]==9
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
    env=dict(original.original.original.original.old.active_public_demos.__globals__,
             COHORTS=COHORTS,OPERATORS=OPERATORS,relation=relation)
    fn=types.FunctionType(original.original.original.original.old.active_public_demos.__code__,env,
                          original.original.original.original.old.active_public_demos.__name__,
                          original.original.original.original.old.active_public_demos.__defaults__)
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
