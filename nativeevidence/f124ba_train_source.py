"""F124-BA independent FIT/SCREEN source. NO DEV birth or model labels.

Only evaluator source knows private operator and key. Learned candidate modules
must not import this file; the runner issues public examples and passes only
opaque task nonce and public graph to the model.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import json,types
import f124az_train_source as old
import f124ao_frozen_source as source_birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ba-frozen-public-confidence.json"
FREEZE_BLOB="7ca3648e451fdd45b51b76c8d5113f5f66705b77"
PARENT_SHA="3707fb2c8b28d386cbea530ff61c56ff8bcc147e"
OLD_SOURCE_BLOB="942f1581e1546c68e418dddd3417269d3a158f1c"
COHORTS={"Yggdrasil":{"TRAIN":range(4900000,4900024),
                       "DEV":range(4900100,4900124)}}
OPERATORS={"TRAIN":("affine_AX463","feistel_K463","affine_AX467","feistel_K467"),
           "DEV":("affine_AX479","feistel_K479","affine_AX487","feistel_K487")}
VECTORS=old.VECTORS
FAMILIES=old.FAMILIES
def need(ok,key):old.need(ok,"BA_"+key)

def frozen():
    old.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB
         and witness.blob(old.__file__)==OLD_SOURCE_BLOB,
         "IMMUTABLE_PARENTS_AND_PREIMPLEMENTATION_FREEZE")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    c=d["cohort"]
    need(d["schema"]=="forge.research.f124ba.frozen-public-negative-rejection.v1"
         and d["status"]=="FROZEN_BEFORE_IMPLEMENTATION"
         and d["lineage"]["parent_qualified_head"]==PARENT_SHA
         and c["TRAIN"]==[4900000,4900023] and
         c["FIT"]==[4900000,4900011] and
         c["held_SCREEN"]==[4900012,4900023] and
         c["reserved_DEV"]==[4900100,4900123]
         and c["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and c["reserved_DEV_operators"]==list(OPERATORS["DEV"])
         and c["FIT_pairs"]==24 and c["SCREEN_pairs"]==24
         and d["public_budget"]["total_per_task"]==48
         and len(d["candidates"]["confidence_new"]["threshold_grid"])==6
         and all(v is False for v in d["authority"].values()),
         "FROZEN_SOURCE_BUDGET_OR_AUTHORITY_DRIFT")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"])
         and set(COHORTS["Yggdrasil"]["TRAIN"]).isdisjoint(
             COHORTS["Yggdrasil"]["DEV"]),"DISJOINT_NEW_SOURCES")
    return d

RENV=dict(source_birth.RELATION.__globals__,OPERATORS=OPERATORS)
RELATION=types.FunctionType(source_birth.RELATION.__code__,RENV,
                            source_birth.RELATION.__name__,source_birth.RELATION.__defaults__)
PENV=dict(source_birth.PLAIN.__globals__,relation=RELATION)
PLAIN=types.FunctionType(source_birth.PLAIN.__code__,PENV,
                         source_birth.PLAIN.__name__,source_birth.PLAIN.__defaults__)
def relation(bits,op,inverse=False):return RELATION(bits,op,inverse)
def plain(graph,op,nonce):return PLAIN(graph,op,nonce)

def build_train(seed,vec):
    need(type(seed) is int and seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS,"ONLY_FROZEN_TRAIN_SOURCE")
    env=dict(source_birth.build.__globals__,
             COHORTS=COHORTS,OPERATORS=OPERATORS,
             relation=relation,plain=plain)
    fun=types.FunctionType(source_birth.build.__code__,env,
                           source_birth.build.__name__,source_birth.build.__defaults__)
    fam,op,nonce,pos,neg,_=fun("Yggdrasil",seed,vec,"TRAIN")
    need(pos["demos"]==neg["demos"] and len(pos["demos"])==24
         and sum(relation(d["input_bits"],op)!=d["output_bits"]
                 for d in pos["demos"])==3,"EXACT_ORIGINAL_PUBLIC_CORRUPTION")
    return fam,op,nonce,pos,neg

def public48(seed,vec,op,condition,original):
    need(seed in COHORTS["Yggdrasil"]["TRAIN"] and tuple(vec) in VECTORS
         and op in OPERATORS["TRAIN"] and
         condition in ("balanced_basis48","random48"),"SOURCE_ONLY_PUBLIC_QUERIES")
    env=dict(old.original.original.old.active_public_demos.__globals__,
             COHORTS=COHORTS,OPERATORS=OPERATORS,relation=relation)
    fun=types.FunctionType(old.original.original.old.active_public_demos.__code__,env,
                           old.original.original.old.active_public_demos.__name__,
                           old.original.original.old.active_public_demos.__defaults__)
    public=fun(seed,vec,op,condition,original)
    need(len(public)==48 and
         sum(relation(x["input_bits"],op)!=x["output_bits"]
             for x in public)==6,"MATCHED_48_PUBLIC_SIX_ERRORS")
    return public

def rows(stage):
    frozen()
    need(stage in ("FIT","SCREEN"),"NO_PROTECTED_DEV")
    start=COHORTS["Yggdrasil"]["TRAIN"].start
    seeds=range(start,start+12) if stage=="FIT" else range(start+12,start+24)
    result=[]
    for vec in VECTORS:
        for seed in seeds:
            fam,op,nonce,p,n=build_train(seed,vec)
            result.append((seed,tuple(vec),fam,op,nonce,p,n))
    need(len(result)==24 and
         Counter(x[2] for x in result)==Counter({fam:6 for fam in FAMILIES}),
         "SPLIT_DENOMINATOR_AND_GRAPH_FAMILIES")
    return result
