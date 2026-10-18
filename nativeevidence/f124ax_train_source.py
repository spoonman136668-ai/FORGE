"""F124-AX source-only independently frozen Ygg TRAIN identities.

Exactly original AO graph constructor and query issuance rebounded to new
operator/source IDs. Models MUST NOT import this module. DEV is inaccessible.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json,types
import f124av_train_source as old
import f124ao_frozen_source as born
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ax-frozen-equal-public-nonlinear-transfer.json"
FREEZE_BLOB="4caedd6b8478da897aed53e6992ff75b6c33e783"
PRIOR_SOURCE_BLOB="07c311e7b0443e21db39a200199a33cc0747046e"
PARENT_HEAD="a0173ff8ab3093dbb24d1b517c416c03502570e1"
COHORTS={"Yggdrasil":{"TRAIN":range(4500000,4500024),
                         "DEV":range(4500100,4500124)}}
OPERATORS={"TRAIN":("affine_AX389","feistel_K389","affine_AX397","feistel_K397"),
           "DEV":("affine_AX401","feistel_K401","affine_AX409","feistel_K409")}
VECTORS=old.VECTORS
FAMILIES=old.FAMILIES
def need(ok,tag):old.need(ok,"AX_"+tag)
def frozen():
    old.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(old.__file__)==PRIOR_SOURCE_BLOB,
         "SOURCE_FROZEN_FIRST")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    src=d["source"]
    need(d["schema"]=="forge.research.f124ax.preimplementation-equal-public-budget-and-nonlinear-transfer.v1"
         and d["status"]=="PREIMPLEMENTATION_SOURCE_AND_CANDIDATES_FROZEN"
         and d["lineage"]["qualified_AW_parent"]==PARENT_HEAD
         and src["lane"]=="Yggdrasil"
         and src["cohorts"]["TRAIN"]==[4500000,4500023]
         and src["cohorts"]["DEV"]==[4500100,4500123]
         and src["operators"]["TRAIN"]==list(OPERATORS["TRAIN"])
         and src["operators"]["DEV"]==list(OPERATORS["DEV"])
         and src["query_conditions"]==["balanced_basis48","random48"]
         and src["total_public_responses_per_task"]==48
         and src["fit_examples"]==40 and src["check_examples"]==8
         and len(d["Yggdrasil"]["models"])==6
         and all(d["safeguards"][k] is False for k in ("new_DEV_generated","new_DEV_consumed","Wingless_DEV_generated","Wingless_DEV_consumed","protected_first_use","independent_scientific_acceptance","optimizer_promotion","production_activation","accepted_ref_mutation","merge","other_repo_mutation","CKB_plane_dependency","external_paid_API")),
         "EXACT_PREIMPLEMENTATION_SOURCE_AND_AUTHORITY")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"])
         and set(COHORTS["Yggdrasil"]["TRAIN"]).isdisjoint(
             COHORTS["Yggdrasil"]["DEV"]),"SEPARATE_HOLDOUT")
    return d

RENV=dict(born.RELATION.__globals__,OPERATORS=OPERATORS)
RELATION=types.FunctionType(born.RELATION.__code__,RENV,
                            born.RELATION.__name__,born.RELATION.__defaults__)
PENV=dict(born.PLAIN.__globals__,relation=RELATION)
PLAIN=types.FunctionType(born.PLAIN.__code__,PENV,
                         born.PLAIN.__name__,born.PLAIN.__defaults__)
def relation(bits,op,inverse=False):return RELATION(bits,op,inverse)
def plain(graph,op,nonce):return PLAIN(graph,op,nonce)

def build(seed,vec,phase="TRAIN"):
    need(phase=="TRAIN" and type(seed) is int and
         seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS,"DEV_BIRTH_NOT_AVAILABLE")
    env=dict(born.build.__globals__,COHORTS=COHORTS,
             OPERATORS=OPERATORS,relation=relation,plain=plain)
    fn=types.FunctionType(born.build.__code__,env,
                          born.build.__name__,born.build.__defaults__)
    fam,op,nonce,p,n,chosen=fn("Yggdrasil",seed,vec,phase)
    need(p["demos"]==n["demos"] and len(p["demos"])==24
         and sum(relation(d["input_bits"],op)!=d["output_bits"]
                 for d in p["demos"])==3,
         "ORIGINAL_24_PUBLIC_NOISY_BIRTH")
    return fam,op,nonce,p,n,chosen

def public48(seed,vec,op,condition,original):
    need(type(seed) is int and seed in COHORTS["Yggdrasil"]["TRAIN"]
         and op in OPERATORS["TRAIN"] and tuple(vec) in VECTORS
         and condition in ("balanced_basis48","random48"),
         "ORIGINAL_QUERY_CONTRACT_TRAIN_ONLY")
    env=dict(old.active_public_demos.__globals__,
             COHORTS=COHORTS,OPERATORS=OPERATORS,
             relation=relation)
    fn=types.FunctionType(old.active_public_demos.__code__,env,
                          old.active_public_demos.__name__,
                          old.active_public_demos.__defaults__)
    demos=fn(seed,vec,op,condition,original)
    need(len(demos)==48
         and sum(relation(row["input_bits"],op)!=row["output_bits"]
                 for row in demos)==6,
         "EQUAL_PUBLIC_QUERY_AND_NOISE_COUNT")
    return demos

def rows(stage):
    frozen()
    need(stage in ("FIT","SCREEN"),"FIT_SCREEN_ONLY")
    seeds=COHORTS["Yggdrasil"]["TRAIN"]
    xs=range(seeds.start,seeds.start+12) if stage=="FIT" else range(
        seeds.start+12,seeds.stop)
    arr=[]
    for vec in VECTORS:
        for seed in xs:
            fam,op,nonce,p,n,chosen=build(seed,vec)
            arr.append((seed,tuple(vec),fam,op,nonce,p,n))
    need(len(arr)==24 and
         Counter(r[2] for r in arr)==Counter({f:6 for f in FAMILIES})
         and len(set((r[0],r[1]) for r in arr))==24,
         "HONEST_FRESH_SUBCOHORT")
    return arr
