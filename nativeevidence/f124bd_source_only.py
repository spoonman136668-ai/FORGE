"""F124-BD only source/evaluator path: independently frozen new TRAIN births.

Reuse exactly BC first oracle-confirmed one-bit-hard-negative source function,
changing ONLY frozen seed/operator identities. The public certificate module
never imports this file or source oracle. DEV cannot be born.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json,types
import f124bc_hard_negative_source as prior
import f124ao_frozen_source as birth
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124bd-frozen-public-path-certificate.json"
FREEZE_BLOB="66d5ee8502130c4c45e562b160adc5d61210fd14"
FIRST_FREEZE_COMMIT="3c8b0da32c93efd1654aff120ff72a3b4bb67753"
PARENT="b9a12e2a73d41eb66b38737239808f09ed3f66d0"
PARENT_SOURCE_BLOB="ec669582b884a16865dbb22a2372d6b7a2ba3e5d"
COHORTS={"Yggdrasil":{"TRAIN":range(5200000,5200024),
                       "DEV":range(5200100,5200124)}}
OPERATORS={"TRAIN":("affine_AX601","feistel_K601","affine_AX607","feistel_K607"),
           "DEV":("affine_AX613","feistel_K613","affine_AX617","feistel_K617")}
VECTORS=prior.VECTORS
FAMILIES=prior.FAMILIES

def need(ok,tag):prior.need(ok,"BD_"+tag)
def frozen():
    prior.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(prior.__file__)==PARENT_SOURCE_BLOB,
         "IMMUTABLE_PARENT_AND_FREEZE")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    s=d["source"]
    need(d["schema"]=="forge.research.f124bd.public-causal-path-certificate.v1"
         and d["status"]=="PREIMPLEMENTATION_FROZEN"
         and d["lineage"]["parent_archival_head"]==PARENT
         and s["FIT"]==[5200000,5200011]
         and s["held_SCREEN"]==[5200012,5200023]
         and s["reserved_DEV"]==[5200100,5200123]
         and s["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and s["DEV_operators"]==list(OPERATORS["DEV"])
         and len(d["new_arms"])==6
         and d["public"]["total_responses_per_case"]==48
         and d["hard_negative"]["min_confirmed_hard_per_24"]==18
         and all(value is False for value in d["authority"].values()),
         "FROZEN_RULES_OR_SEPARATION_DRIFT")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"])
         and set(COHORTS["Yggdrasil"]["TRAIN"]).isdisjoint(COHORTS["Yggdrasil"]["DEV"]),
         "TRAIN_AND_PROTECTED_DEV_DISJOINT")
    return d

R_ENV=dict(birth.RELATION.__globals__,OPERATORS=OPERATORS)
RELATION=types.FunctionType(birth.RELATION.__code__,R_ENV,
                            birth.RELATION.__name__,birth.RELATION.__defaults__)
P_ENV=dict(birth.PLAIN.__globals__,relation=RELATION)
PLAIN=types.FunctionType(birth.PLAIN.__code__,P_ENV,birth.PLAIN.__name__,birth.PLAIN.__defaults__)
def relation(bits,op,inverse=False):return RELATION(bits,op,inverse)
def plain(graph,op,nonce):return PLAIN(graph,op,nonce)

def near_miss(pos,neg,op,nonce,fam):
    env=dict(prior.model_blind_one_bit_near_miss.__globals__,plain=plain)
    func=types.FunctionType(prior.model_blind_one_bit_near_miss.__code__,env,
                            prior.model_blind_one_bit_near_miss.__name__,
                            prior.model_blind_one_bit_near_miss.__defaults__)
    return func(pos,neg,op,nonce,fam)

def build(seed,vec):
    need(type(seed) is int and seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS,"TRAIN_ONLY_NO_DEV_BIRTH")
    env=dict(prior.build.__globals__,COHORTS=COHORTS,OPERATORS=OPERATORS,
             relation=relation,plain=plain,model_blind_one_bit_near_miss=near_miss)
    f=types.FunctionType(prior.build.__code__,env,prior.build.__name__,prior.build.__defaults__)
    fam,op,nonce,p,n,hard,meta=f(seed,vec)
    need(meta["source_oracle_probes"]<=1024 and
         meta["selection_used_model_predictions"] is False,
         "MODEL_BLIND_SOURCE_CHALLENGE")
    return fam,op,nonce,p,n,hard,meta

def public48(seed,vec,op,query,demos):
    need(seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS and op in OPERATORS["TRAIN"],
         "NO_PROTECTED_PUBLIC_ACCESS")
    env=dict(prior.public48.__globals__,COHORTS=COHORTS,
             OPERATORS=OPERATORS,relation=relation)
    f=types.FunctionType(prior.public48.__code__,env,prior.public48.__name__,prior.public48.__defaults__)
    return f(seed,vec,op,query,demos)

def rows(stage):
    frozen()
    need(stage in ("FIT","SCREEN"),"NO_DEV_REQUEST")
    seeds=range(5200000,5200012) if stage=="FIT" else range(5200012,5200024)
    out=[]
    for vec in VECTORS:
        for seed in seeds:
            fam,op,nonce,p,n,hard,meta=build(seed,vec)
            out.append((seed,tuple(vec),fam,op,nonce,p,n,hard,meta))
    need(len(out)==24 and
         Counter(v[2] for v in out)==Counter({f:6 for f in FAMILIES}),
         "EXACT_NEW_24_PAIRED_AND_HARD_SOURCE")
    return out
