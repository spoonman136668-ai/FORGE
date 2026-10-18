"""F124-AV independent source-only TRAIN cohort, no DEV construction path.

Exact source identity from qualified AR is verified, and the unchanged
first-admitted AO/AN paired graph constructor is rebound only to new,
precommitted seed/operator identities. Neither learned model imports this.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import json, types, random
import f124au_train_source as prior
import f124ao_frozen_source as birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124av-frozen-informative-queries-and-handoff.json"
FREEZE_BLOB="d27f98324c348ce3a8b113df9caa0f9be74b286f"
PARENT_BLOB="42ea7ec65bdad1f66bf5a923425bfe13733425d3"
COHORTS={
 "Yggdrasil":{"TRAIN":range(4300000,4300024),"DEV":range(4300100,4300124)},
 "Wingless":{"TRAIN":range(4310000,4310024),"DEV":range(4310100,4310124)}}
OPERATORS={
 "TRAIN":("affine_AX367","feistel_K367","affine_AX373","feistel_K373"),
 "DEV":("affine_AX379","feistel_K379","affine_AX383","feistel_K383")}
VECTORS=prior.VECTORS
FAMILIES=prior.FAMILIES

def need(ok,tag):prior.need(ok,"AV_"+tag)

def frozen():
    prior.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(prior.__file__)==PARENT_BLOB,
         "PREIMPLEMENTATION_FROZEN_IDENTITIES")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    src=d["source"]
    need(d["schema"]=="forge.research.f124av.frozen-active-public-inverse-one-state-handoff.v1"
         and d["status"]=="PREIMPLEMENTATION_FROZEN"
         and d["lineage"]["parent_qualified_head"]==
             "c5cdb9ba55772b4b69a2534dd48cfc8b7abe20b2"
         and d["lineage"]["parent_source_blob"]==PARENT_BLOB
         and src["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and src["DEV_operators"]==list(OPERATORS["DEV"])
         and all(src[k]=={phase:[r.start,r.stop-1]
                             for phase,r in COHORTS[k].items()}
                 for k in COHORTS)
         and src["existing_public_demos"]==24
         and src["extra_public_queries"]==24
         and src["extra_corruptions"]==3
         and all(value is False for value in d["authority"].values()),
         "FROZEN_SOURCE_AND_AUTHORITY")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]),
         "NO_OPERATOR_OVERLAP")
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

def active_public_demos(seed,vec,op,condition,original):
    """Evaluator answers source-blind queries; caller gets ONLY public pairs.

    Does not pass source operator string, inverse or truth into any learner.
    Exactly the same 24-query budget and 3 new corrupted output observations
    for designed and matched random conditions.
    """
    need(condition in ("balanced_basis48","random48") and
         len(original)==24 and
         type(seed) is int and
         seed in COHORTS["Yggdrasil"]["TRAIN"] and
         tuple(vec) in VECTORS,
         "NEW_PUBLIC_QUERIES_TRAIN_ONLY")
    if condition=="balanced_basis48":
        patterns=[0]+[1<<j for j in range(16)]+[
            (1<<j)|(1<<((j+5)%16)) for j in range(7)]
    else:
        rng=random.Random("F124AV_MATCHED_RANDOM_48:"+str(seed)+":"+str(tuple(vec)))
        patterns=rng.sample(range(1<<16),24)
    need(len(patterns)==24 and len(set(patterns))==24,
         "ORIGINAL_24_PUBLIC_QUERY_UNIQUENESS")
    extra=[]
    for index,value in enumerate(patterns):
        input_bits=[(value>>j)&1 for j in range(16)]
        output_bits=list(relation(input_bits,op))
        if index in (6,13,20):output_bits[(index+seed)%16]^=1
        extra.append({"input_bits":input_bits,"output_bits":output_bits})
    prior_wrong=sum(relation(d["input_bits"],op)!=d["output_bits"]
                    for d in original)
    extra_wrong=sum(relation(d["input_bits"],op)!=d["output_bits"]
                    for d in extra)
    need(prior_wrong==3 and extra_wrong==3 and
         len(original)+len(extra)==48,
         "HONEST_SIX_NOISY_OBSERVATIONS")
    # The evaluator has oracle access to answer queries; the resulting
    # example pairs are not privileged labels and are common public inputs.
    return list(original)+extra
