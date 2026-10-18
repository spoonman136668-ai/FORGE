"""F124-BB source-only independent FIT / conditional SCREEN.

Freeze is committed before this adapter. Model code cannot access operators,
oracle inverses or source-task labels. No DEV builder path exists.
"""
from __future__ import annotations
import json,types
from collections import Counter
from pathlib import Path
import f124ba_train_source as parent
import f124ao_frozen_source as birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124bb-frozen-public-transition-consensus.json"
FREEZE_BLOB="7328674f265efe93fa7c76b48ddeefee31ebe990"
FIRST_COMMIT="28f712b226864f1c7092d5c9a3c611241a9a025a"
PARENT="e96f54154d5b00d7d832eb3017a050d2d59d461c"
PARENT_SOURCE_BLOB="eb7ef9ffeaabcabb2c73a283b1b20ebd574d0e40"
COHORTS={"Yggdrasil":{"TRAIN":range(5000000,5000024),
                       "DEV":range(5000100,5000124)}}
OPERATORS={"TRAIN":("affine_AX503","feistel_K503","affine_AX509","feistel_K509"),
           "DEV":("affine_AX521","feistel_K521","affine_AX523","feistel_K523")}
VECTORS=parent.VECTORS
FAMILIES=parent.FAMILIES

def need(ok,key):parent.need(ok,"BB_"+key)

def frozen():
    parent.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(parent.__file__)==PARENT_SOURCE_BLOB,"BIRTH_PARENT_DRIFT")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    s=d["sources"]
    need(d["schema"]=="forge.research.f124bb.frozen-public-transition-consensus.v1"
         and d["status"]=="BEFORE_IMPLEMENTATION_AND_NEW_FIRST_USE"
         and d["lineage"]["parent_archived_head"]==PARENT
         and s["FIT_seeds"]==[5000000,5000011]
         and s["SCREEN_seeds"]==[5000012,5000023]
         and s["DEV_reserved"]==[5000100,5000123]
         and s["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and s["DEV_operators"]==list(OPERATORS["DEV"])
         and d["information"]["all_arms_exactly_48_public_responses"] is True
         and len(d["models"]["new_candidates"])==4
         and all(v is False for v in d["governance"].values()),
         "IMMUTABLE_EXPERIMENT_RULES_OR_SAFETY_DRIFT")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"])
         and set(COHORTS["Yggdrasil"]["TRAIN"]).isdisjoint(
             COHORTS["Yggdrasil"]["DEV"]),"NEW_UNCONSUMED_SOURCE")
    return d

REN=dict(birth.RELATION.__globals__,OPERATORS=OPERATORS)
REL=types.FunctionType(birth.RELATION.__code__,REN,birth.RELATION.__name__,birth.RELATION.__defaults__)
PEN=dict(birth.PLAIN.__globals__,relation=REL)
PLAIN=types.FunctionType(birth.PLAIN.__code__,PEN,birth.PLAIN.__name__,birth.PLAIN.__defaults__)
def relation(bits,op,inverse=False):return REL(bits,op,inverse)
def plain(graph,op,nonce):return PLAIN(graph,op,nonce)

def build(seed,vec):
    need(type(seed) is int and seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS,"TRAIN_ONLY_BIRTH")
    env=dict(birth.build.__globals__,COHORTS=COHORTS,OPERATORS=OPERATORS,
             relation=relation,plain=plain)
    fun=types.FunctionType(birth.build.__code__,env,
                           birth.build.__name__,birth.build.__defaults__)
    fam,op,nonce,p,n,_=fun("Yggdrasil",seed,vec,"TRAIN")
    need(p["demos"]==n["demos"] and len(p["demos"])==24
         and sum(relation(d["input_bits"],op)!=d["output_bits"]
                 for d in p["demos"])==3,"ORIGINAL_24_THREE_ERRORS")
    return fam,op,nonce,p,n

def public48(seed,vec,op,condition,demos):
    need(seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS
         and op in OPERATORS["TRAIN"]
         and condition in ("balanced_basis48","random48"),
         "TRAIN_ONLY_PUBLIC_SOURCE")
    env=dict(parent.old.original.original.old.active_public_demos.__globals__,
             COHORTS=COHORTS,OPERATORS=OPERATORS,relation=relation)
    fun=types.FunctionType(parent.old.original.original.old.active_public_demos.__code__,
                           env,parent.old.original.original.old.active_public_demos.__name__,
                           parent.old.original.original.old.active_public_demos.__defaults__)
    out=fun(seed,vec,op,condition,demos)
    need(len(out)==48 and
         sum(relation(x["input_bits"],op)!=x["output_bits"] for x in out)==6,
         "EXACT_48_PUBLIC_AND_SIX_ERRORS")
    return out

def rows(stage):
    frozen()
    need(stage in ("FIT","SCREEN"),"NO_DEV_BIRTH")
    seeds=(range(5000000,5000012) if stage=="FIT" else range(5000012,5000024))
    out=[]
    for vec in VECTORS:
        for seed in seeds:
            fam,op,nonce,p,n=build(seed,vec)
            out.append((seed,tuple(vec),fam,op,nonce,p,n))
    need(len(out)==24 and
         Counter(x[2] for x in out)==Counter({fam:6 for fam in FAMILIES}),
         "DISJOINT_FAMILY_PAIRED_COUNTS")
    return out
