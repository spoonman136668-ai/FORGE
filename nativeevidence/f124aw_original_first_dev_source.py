"""F124-AW SINGLE original Yggdrasil DEV birth. Never import in TRAIN tests.

Reuses unchanged authenticated AO source constructor with exactly the frozen
AV DEV seed/operator identities. Only this module can construct the new
Yggdrasil DEV cohort, and it has NO Wingless construction route.
"""
from __future__ import annotations
import json,types
from pathlib import Path
from collections import Counter
import f124av_train_source as av
import f124ao_frozen_source as birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124aw-frozen-original-ygg-first-dev.json"
FREEZE_BLOB="e86cbf31e179bb4a1d4ceeee039c3d017ba27789"
AV_SOURCE_BLOB="07c311e7b0443e21db39a200199a33cc0747046e"
AV_MODEL_BLOB="0364e6a00c2bc3ffcda0e91ab2fe292e6bd8fbd5"  # correction recorded in append-only source-identity erratum
SOURCE_RANGE=av.COHORTS["Yggdrasil"]["DEV"]
def need(ok,why):av.need(ok,"AW_DEV_"+why)
def frozen():
    av.frozen()
    err=Path(__file__).resolve().parents[1]/"reference/research-intake/f124aw-original-model-identity-erratum.json"
    note=json.loads(err.read_text(encoding="utf-8"))
    need(note["schema"]=="forge.research.f124aw.source-identity-erratum-before-first-use.v1"
         and note["actual_qualified_AV_model_blob"]==AV_MODEL_BLOB
         and note["DEV_cases_constructed"]==0,
         "SOURCE_IDENTITY_ERRATUM_STILL_BOUND")
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(av.__file__)==AV_SOURCE_BLOB,
         "ORIGINAL_FREEZE_AND_AV_SOURCE")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124aw.selected-active-inverse-original-prospective-dev.v1"
         and p["status"]=="SELECTED_BEFORE_DEV_IMPLEMENTATION"
         and p["lineage"]["qualified_parent_head"]==
             "0c54bee8cc9a69bd87a7852a236b0e0bc57e01c4"
         and p["locked_source"]["seed_range"]==[SOURCE_RANGE.start,SOURCE_RANGE.stop-1]
         and p["locked_source"]["DEV_operators"]==list(av.OPERATORS["DEV"])
         and p["fixed_model"]["query_condition"]=="balanced_basis48"
         and p["fixed_model"]["fit_bit_budget"]==12
         and p["fixed_model"]["min_CHECK_correct"]==96
         and p["fixed_model"]["robust_ransac_trials"]==256
         and all(v is False for v in p["authority"].values()),
         "NO_CONFIG_OR_AUTHORITY_DRIFT")
    return p

def build(seed,vector):
    need(type(seed) is int and seed in SOURCE_RANGE
         and tuple(vector) in av.VECTORS,"ONLY_YGG_ORIGINAL_DEV")
    env=dict(birth.build.__globals__,
             COHORTS=av.COHORTS,OPERATORS=av.OPERATORS,
             relation=av.relation,plain=av.plain)
    f=types.FunctionType(birth.build.__code__,env,
                         birth.build.__name__,birth.build.__defaults__)
    fam,op,nonce,p,n,ident=f("Yggdrasil",seed,vector,"DEV")
    need(op in av.OPERATORS["DEV"] and
         p["demos"]==n["demos"] and len(p["demos"])==24
         and sum(av.relation(d["input_bits"],op)!=d["output_bits"]
                 for d in p["demos"])==3,
         "ORIGINAL_PAIRED_SOURCE_AND_NOISE")
    return fam,op,nonce,p,n

def original_public_48(seed,vector,op,demos):
    need(type(seed) is int and seed in SOURCE_RANGE and
         tuple(vector) in av.VECTORS and op in av.OPERATORS["DEV"],
         "PRECOMMITTED_PUBLIC_FIRST_DEV")
    env=dict(av.active_public_demos.__globals__)
    env["COHORTS"]={"Yggdrasil":{"TRAIN":SOURCE_RANGE}}
    f=types.FunctionType(av.active_public_demos.__code__,env,
                         av.active_public_demos.__name__,
                         av.active_public_demos.__defaults__)
    out=f(seed,vector,op,"balanced_basis48",demos)
    need(len(out)==48 and
         sum(av.relation(d["input_bits"],op)!=d["output_bits"]
             for d in out)==6,"HONEST_PUBLIC_RESPONSE_AND_ERROR_BUDGET")
    return out

def pairs():
    frozen()
    rows=[]
    for vector in av.VECTORS:
        for seed in SOURCE_RANGE:
            fam,op,nonce,p,n=build(seed,vector)
            rows.append((seed,tuple(vector),fam,op,nonce,p,n))
    need(len(rows)==48 and
         Counter(x[2] for x in rows)==Counter({f:12 for f in av.FAMILIES})
         and all(x[0] not in av.COHORTS["Yggdrasil"]["TRAIN"]
                 for x in rows),"ORIGINAL_FRESH_COMPLETE_48")
    return rows
