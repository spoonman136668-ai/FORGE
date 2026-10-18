"""F124-AG source-disjoint original AF generator; immutable source admission."""
from __future__ import annotations
import json,types
from pathlib import Path
import f124af_frozen_source as prior
import f124w_hop_trace_indexed as guard
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ag-frozen-transition-consistency.json"
FREEZE_BLOB="f533b36c0e978bfc60c6ff97b83585fd546207c3"
PARENT_BLOB="3ea7f3e14bc47212f7659e2b34b20619a68b2792"
COHORTS={"Wingless":{"FIT":range(1980000,1980024),"DEV":range(1980100,1980124)},
         "Yggdrasil":{"FIT":range(1990000,1990024),"DEV":range(1990100,1990124)}}
FAMILIES=prior.FAMILIES
VECTORS=prior.VECTORS
ETAS=(0.,.025,.05,.1,.2,.4)

def need(ok,tag):q.need(ok,"F124AG_"+tag)

def frozen():
    prior.frozen()
    need(guard.blob(FREEZE)==FREEZE_BLOB
         and guard.blob(prior.__file__)==PARENT_BLOB,
         "FROZEN_PROTOCOL_OR_ORIGINAL_SOURCE")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124ag.frozen-causal-transition-discrimination.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["parent_head"]=="94108177a92e0dddb57475e1d408075f7ee63255"
         and p["source"]["Wingless"]==
              {k:[v.start,v.stop-1] for k,v in COHORTS["Wingless"].items()}
         and p["source"]["Yggdrasil"]==
              {k:[v.start,v.stop-1] for k,v in COHORTS["Yggdrasil"].items()}
         and p["source"]["families"]==list(FAMILIES)
         and p["Yggdrasil"]["eta_grid"]==list(ETAS)
         and p["Wingless"]["eta_grid"]==list(ETAS)
         and all(v is False for v in p["authority"].values()),
         "PREDECLARED_COHORT_AND_HARD_LIMIT")
    return p

def build(lane,requested,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(requested) is int and requested in COHORTS[lane][phase]
         and tuple(vector) in VECTORS,
         "SOURCE_COHORT_IDENTITY")
    env=dict(prior.build.__globals__)
    env["COHORTS"]=COHORTS
    method=types.FunctionType(prior.build.__code__,env,
                              prior.build.__name__,prior.build.__defaults__)
    family,pos,neg,admitted=method(lane,requested,vector,phase)
    need(family==FAMILIES[(requested-COHORTS[lane][phase].start)%4]
         and prior.parent.routes15(pos,relaxed=family=="one_bit_relaxed_keys")==1
         and prior.parent.routes15(neg,relaxed=family=="one_bit_relaxed_keys")==0,
         "POSTBIRTH_PUBLIC_LABEL_ADMISSION_ONLY")
    return family,pos,neg,admitted

def pairs(lane,phase):
    result=[]
    for vec in VECTORS:
        for seed in COHORTS[lane][phase]:
            fam,p,n,chosen=build(lane,seed,vec,phase)
            result.append((chosen,tuple(vec),fam,p,n))
    need(len(result)==48 and
         all(sum(x[2]==fam for x in result)==12 for fam in FAMILIES)
         and (phase!="FIT" or
              all(x[0]<COHORTS[lane]["DEV"].start for x in result)),
         "PROSPECTIVE_SOURCE_DISJOINT")
    return result
