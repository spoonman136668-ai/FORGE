"""F124-AF independent frozen source; original F124-AE source model unchanged.

The original source constructor and deterministic public-admission rules run
unchanged except new disjoint seed cohort globals. No source labels or oracle
are passed to a predictor.
"""
from __future__ import annotations
import types,json
from pathlib import Path
import f124ae_frozen_source as parent
import f124w_hop_trace_indexed as source_witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124af-frozen-terminal-contrast-one-state-margin.json"
FREEZE_BLOB="646b203a33929e0f63a31db5b11f0850fec0b954"
PARENT_BLOB="05eb5b8d8a487801a6b25fdab0308549d569c0ce"
COHORTS={"Wingless":{"FIT":range(1880000,1880024),"DEV":range(1880100,1880124)},
         "Yggdrasil":{"FIT":range(1890000,1890024),"DEV":range(1890100,1890124)}}
FAMILIES=parent.FAMILIES
VECTORS=parent.VECTORS
LAMBDAS=(0.,.25,.5,1.,2.,4.)
BETAS=(0.,.25,.5,1.,2.,4.)

def need(ok,label):
    q.need(ok,"F124AF_"+label)

def frozen():
    parent.frozen()
    need(source_witness.blob(FREEZE)==FREEZE_BLOB
         and source_witness.blob(parent.__file__)==PARENT_BLOB,
         "ORIGINAL_PARENT_IDENTITY_AND_FREEZE")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124af.frozen-terminal-contrast-and-single-state-margin.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["qualified_parent"]=="b9438ec1f009af2b421713c468e0acddad63938d"
         and p["lineage"]["parent_raw_SHA256"]=="3b7cce04a678601c503df588ee2f17de6a8116cfcd875347e0395f2632decc40"
         and p["source"]["Wingless"]==
            {phase:[data.start,data.stop-1] for phase,data in COHORTS["Wingless"].items()}
         and p["source"]["Yggdrasil"]==
            {phase:[data.start,data.stop-1] for phase,data in COHORTS["Yggdrasil"].items()}
         and p["source"]["families"]==list(FAMILIES)
         and p["Yggdrasil"]["lambda_grid"]==list(LAMBDAS)
         and p["Wingless"]["beta_grid"]==list(BETAS)
         and p["Wingless"]["memory_budget"]["max_node_states"]==64
         and all(v is False for v in p["authority"].values()),
         "PREDECLARED_HYPOTHESIS_AND_AUTHORITY")
    return p

def build(lane,requested,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(requested) is int and requested in COHORTS[lane][phase]
         and tuple(vector) in VECTORS,
         "ONLY_FROZEN_INDEPENDENT_SEEDS")
    env=dict(parent.build.__globals__)
    env["COHORTS"]=COHORTS
    method=types.FunctionType(parent.build.__code__,env,
                              parent.build.__name__,parent.build.__defaults__)
    family,positive,negative,admitted_seed=method(lane,requested,vector,phase)
    need(family==FAMILIES[(requested-COHORTS[lane][phase].start)%4]
         and parent.routes15(positive,relaxed=family=="one_bit_relaxed_keys")==1
         and parent.routes15(negative,relaxed=family=="one_bit_relaxed_keys")==0,
         "PAIRED_PUBLIC_CAUSAL_REFERENCE")
    return family,positive,negative,admitted_seed

def pairs(lane,phase):
    result=[]
    for vector in VECTORS:
        for requested in COHORTS[lane][phase]:
            family,p,n,admitted=build(lane,requested,vector,phase)
            result.append((admitted,tuple(vector),family,p,n))
    need(len(result)==48 and
         all(sum(x[2]==f for x in result)==12 for f in FAMILIES)
         and (phase!="FIT" or
              all(x[0]<COHORTS[lane]["DEV"].start for x in result)),
         "PUBLIC_SOURCE_COHORT_AND_PHASE_SEPARATION")
    return result
