"""F124-AY source-only FIT. Original source mechanism, independently frozen IDs.

The true operator/inverse is evaluator-only. There is NO SCREEN or DEV
constructor in this module. Callers evaluating learned models receive only
public pairs, task nonce and graph; no source labels.
"""
from __future__ import annotations
import json,random,types
from pathlib import Path
from collections import Counter
import f124ao_frozen_source as prior
import f124av_train_source as queries
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ay-frozen-diagnostic-contract.json"
FREEZE_BLOB="e7dedbf082c9852259ff4cc30502f5a8a3e322a3"
PARENT="089745a0ea0c388842c0ed1be5f9221daf580549"
PARENT_SOURCE_BLOB="6c6bd9b685b8ad6b1b3685f95959947c4940f2ff"
TRAIN=range(4600000,4600024)
FIT=range(4600000,4600012)
SCREEN=range(4600012,4600024)
RESERVED_DEV=range(4600100,4600124)
OPERATORS={"TRAIN":("affine_AX431","feistel_K431","affine_AX439","feistel_K439"),
           "DEV":("affine_AX449","feistel_K449","affine_AX457","feistel_K457")}
COHORTS={"Yggdrasil":{"TRAIN":TRAIN,"DEV":RESERVED_DEV}}
VECTORS=queries.VECTORS
FAMILIES=queries.FAMILIES

def need(ok,why):queries.need(ok,"AY_"+why)

def frozen():
    queries.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(prior.__file__)==PARENT_SOURCE_BLOB,
         "EXACT_FROZEN_SOURCE_IDENTITY")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    s=d["cohort"]
    need(d["schema"]=="forge.research.f124ay.causal-sparse-inverse-diagnostics.freeze.v1"
         and d["status"]=="PREIMPLEMENTATION_FROZEN"
         and d["lineage"]["qualified_parent"]==PARENT
         and s["TRAIN"]==[TRAIN.start,TRAIN.stop-1]
         and s["FIT"]==[FIT.start,FIT.stop-1]
         and s["reserved_SCREEN"]==[SCREEN.start,SCREEN.stop-1]
         and s["reserved_DEV"]==[RESERVED_DEV.start,RESERVED_DEV.stop-1]
         and s["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and s["reserved_DEV_operators"]==list(OPERATORS["DEV"])
         and s["FIT_cases"]==24
         and s["SCREEN_cases_constructed"]==0
         and s["DEV_cases_constructed"]==0
         and s["public_48"]["fit_RANSAC_trials"]==256
         and s["public_96_diagnostic_only"]["fit_trials"]==256
         and all(d["governance"][key] is True for key in
                 ("no_promotion","no_merge","no_accepted_ref_mutation",
                  "no_Wingless_use","no_second_controller")),
         "PREIMPLEMENTATION_CONTRACT")
    need(set(TRAIN).isdisjoint(RESERVED_DEV)
         and set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]),
         "NO_DEV_OVERLAP")
    return d

ENV=dict(prior.RELATION.__globals__,OPERATORS=OPERATORS)
RELATION=types.FunctionType(prior.RELATION.__code__,ENV,
                            prior.RELATION.__name__,prior.RELATION.__defaults__)
PENV=dict(prior.PLAIN.__globals__,relation=RELATION)
PLAIN=types.FunctionType(prior.PLAIN.__code__,PENV,
                         prior.PLAIN.__name__,prior.PLAIN.__defaults__)
def relation(bits,operator,inverse=False):return RELATION(bits,operator,inverse)
def plain(graph,operator,nonce):return PLAIN(graph,operator,nonce)

def build_fit(seed,vector):
    need(type(seed) is int and seed in FIT and tuple(vector) in VECTORS,
         "ONLY_FIT_BIRTH")
    env=dict(prior.build.__globals__)
    env.update(COHORTS=COHORTS,OPERATORS=OPERATORS,
               relation=relation,plain=plain)
    func=types.FunctionType(prior.build.__code__,env,
                            prior.build.__name__,prior.build.__defaults__)
    fam,op,nonce,p,n,_=func("Yggdrasil",seed,vector,"TRAIN")
    need(p["demos"]==n["demos"]
         and len(p["demos"])==24
         and sum(relation(x["input_bits"],op)!=x["output_bits"]
                 for x in p["demos"])==3,"HONEST_PAIRED_ORIGINAL_3_NOISE")
    return (seed,tuple(vector),fam,op,nonce,p,n)

def fit_rows():
    frozen()
    rows=[build_fit(seed,vector) for vector in VECTORS for seed in FIT]
    need(len(rows)==24 and Counter(r[2] for r in rows)==
         Counter({f:6 for f in FAMILIES}),"EXACT_NEW_FIT")
    return rows

def public48(seed,vector,operator,original):
    need(seed in FIT and tuple(vector) in VECTORS
         and operator in OPERATORS["TRAIN"],"PUBLIC_NEW_FIT_ONLY")
    env=dict(queries.active_public_demos.__globals__)
    env.update(COHORTS=COHORTS,relation=relation)
    fun=types.FunctionType(queries.active_public_demos.__code__,env,
                           queries.active_public_demos.__name__,
                           queries.active_public_demos.__defaults__)
    out=fun(seed,vector,operator,"balanced_basis48",original)
    need(len(out)==48
         and sum(relation(x["input_bits"],operator)!=x["output_bits"] for x in out)==6,
         "48_RESPONSES_SIX_CORRUPTIONS")
    return out

def public96_diagnostic(seed,vector,operator,original48):
    need(seed in FIT and tuple(vector) in VECTORS
         and operator in OPERATORS["TRAIN"]
         and len(original48)==48,"ONLY_EXTRA_DIAGNOSTIC_RESPONSES")
    d=frozen()["cohort"]["public_96_diagnostic_only"]
    used={tuple(x["input_bits"]) for x in original48}
    rng=random.Random(d["sourceblind_random_query_seed_prefix"]+str(seed)+":"+str(tuple(vector)))
    candidates=[n for n in range(65536) if tuple((n>>j)&1 for j in range(16)) not in used]
    bits_values=rng.sample(candidates,48)
    extra=[]
    for i,n in enumerate(bits_values):
        inp=[(n>>j)&1 for j in range(16)]
        output=list(relation(inp,operator))
        if i in d["extra_corruption_positions"]:
            output[(i+seed)%16]^=1
        extra.append({"input_bits":inp,"output_bits":output})
    full=list(original48)+extra
    need(len(full)==96 and
         sum(relation(x["input_bits"],operator)!=x["output_bits"] for x in full)==12,
         "96_DIAG_PUBLIC_TWELVE_CORRUPTIONS")
    return full
