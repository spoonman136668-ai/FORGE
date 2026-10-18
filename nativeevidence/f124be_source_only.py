"""F124-BE source-only fresh TRAIN FIT and conditional held SCREEN.

Reuse original BC source-born one-bit negative construction through BD
adapter while rebinding only fresh IDs, source relation and source oracle
transform; candidate code never imports this module or oracle.
"""
from __future__ import annotations
import json,types
from pathlib import Path
from collections import Counter
import f124bd_source_only as parent
import f124ao_frozen_source as birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124be-frozen-public-nearmiss-contrast.json"
FREEZE_BLOB="77faaa6439e5e8b211e9a2fbd90fc5f8c115dfdb"
FREEZE_COMMIT="ec518a52865627a2d7d73690fba6a4914286ca33"
PARENT="b82522dff58c3bf0403a1de9e07e4378e2cf7d01"
PARENT_SOURCE_BLOB="59e3afe54034033d93fad3aa2cfa6205ee6a001a"
COHORTS={"Yggdrasil":{"TRAIN":range(5300000,5300024),
                       "DEV":range(5300100,5300124)}}
OPERATORS={"TRAIN":("affine_AX641","feistel_K641","affine_AX647","feistel_K647"),
           "DEV":("affine_AX659","feistel_K659","affine_AX661","feistel_K661")}
VECTORS=parent.VECTORS
FAMILIES=parent.FAMILIES
def need(ok,name):parent.need(ok,"BE_"+name)

def frozen():
    parent.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(parent.__file__)==PARENT_SOURCE_BLOB,
         "SOURCE_BIRTH_OR_PARENT_DRIFT")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    s=d["source"]
    need(d["schema"]=="forge.research.f124be.frozen-independent-public-nearmiss-contrast.v1",
         "IMMUTABLE_FREEZE_SCHEMA")
    need(d["state"]=="PREIMPLEMENTATION_FROZEN"
         and d["lineage"]["parent_archived_head"]==PARENT
         and s["FIT"]==[5300000,5300011]
         and s["held_SCREEN"]==[5300012,5300023]
         and s["reserved_DEV"]==[5300100,5300123]
         and s["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and s["DEV_operators"]==list(OPERATORS["DEV"])
         and d["challengers"]["min_hard_coverage"]==18
         and d["public"]["same_48_responses_per_task"] is True
         and len(d["arms"]["candidates"])==6
         and all(v is False for v in d["authority"].values()),
         "FROZEN_SOURCE_OR_AUTHORITY_DRIFT")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"])
         and set(COHORTS["Yggdrasil"]["TRAIN"]).isdisjoint(COHORTS["Yggdrasil"]["DEV"]),
         "PROTECTED_COHORT_DISJOINT")
    return d

ENV=dict(birth.RELATION.__globals__,OPERATORS=OPERATORS)
REL=types.FunctionType(birth.RELATION.__code__,ENV,birth.RELATION.__name__,birth.RELATION.__defaults__)
PENV=dict(birth.PLAIN.__globals__,relation=REL)
PLAIN=types.FunctionType(birth.PLAIN.__code__,PENV,birth.PLAIN.__name__,birth.PLAIN.__defaults__)
def relation(bits,op,inverse=False):return REL(bits,op,inverse)
def plain(graph,op,nonce):return PLAIN(graph,op,nonce)

def near_miss(p,n,op,nonce,fam):
    env=dict(parent.near_miss.__globals__,plain=plain)
    fn=types.FunctionType(parent.near_miss.__code__,env,
                          parent.near_miss.__name__,parent.near_miss.__defaults__)
    return fn(p,n,op,nonce,fam)

def build(seed,vec):
    need(type(seed) is int and seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS,"TRAIN_ONLY")
    env=dict(parent.build.__globals__,COHORTS=COHORTS,OPERATORS=OPERATORS,
             relation=relation,plain=plain,near_miss=near_miss)
    fn=types.FunctionType(parent.build.__code__,env,parent.build.__name__,parent.build.__defaults__)
    fam,op,nonce,p,n,h,meta=fn(seed,vec)
    need(meta["source_oracle_probes"]<=1024 and
         not meta["selection_used_model_predictions"],"SOURCE_MODEL_BLIND_PROOF")
    return fam,op,nonce,p,n,h,meta

def public48(seed,vec,op,query,demos):
    need(type(seed) is int and seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS and op in OPERATORS["TRAIN"]
         and query in ("balanced_basis48","random48"),
         "TRAIN_ONLY_PUBLIC")
    env=dict(parent.public48.__globals__,COHORTS=COHORTS,
             OPERATORS=OPERATORS,relation=relation)
    fn=types.FunctionType(parent.public48.__code__,env,
                          parent.public48.__name__,parent.public48.__defaults__)
    return fn(seed,vec,op,query,demos)

def rows(stage):
    frozen()
    need(stage in ("FIT","SCREEN"),"NO_PROTECTED_DEV")
    seeds=range(5300000,5300012) if stage=="FIT" else range(5300012,5300024)
    out=[]
    for vec in VECTORS:
        for seed in seeds:
            fam,op,nonce,p,n,h,m=build(seed,vec)
            out.append((seed,tuple(vec),fam,op,nonce,p,n,h,m))
    need(len(out)==24 and
         Counter(x[2] for x in out)==Counter({f:6 for f in FAMILIES}),
         "INDEPENDENT_24_PAIRED_BIRTH")
    return out
