"""F124-AC separate frozen source birth, only new cohort rebinding."""
from __future__ import annotations
import json,types
from pathlib import Path
import f124ab_frozen_source as original
import f124w_hop_trace_indexed as guard
import f124q_fresh_source as source

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ac-frozen-depth-collision-diagnostics.json"
FREEZE_BLOB="be5f9a3121beca097ca81f4451e73c1927aae595"
ORIGINAL_SOURCE_BLOB="f5451197b72259fbcebc56b1a625dbd816f0edc3"
ORIGINAL_MODEL_BLOB="557c040d63646acf678c216f9658201693f557e0"
COHORTS={"Wingless":{"FIT":range(1580000,1580024),"DEV":range(1580100,1580124)},
         "Yggdrasil":{"FIT":range(1590000,1590024),"DEV":range(1590100,1590124)}}
FAMILIES=original.FAMILIES
VECTORS=original.VECTORS

def need(ok,why):
    source.need(ok,"F124AC_"+why)

def frozen():
    original.frozen()
    need(guard.blob(FREEZE)==FREEZE_BLOB
         and guard.blob(original.__file__)==ORIGINAL_SOURCE_BLOB,"FROZEN_PARENT_SOURCE")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124ac.frozen-hop-failure-and-packed-collision.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["qualified_parent"]=="0a17074b9c801d7ddc76f995d9d14bb53c4234c1"
         and p["source"]["Wingless"]==
              {k:[v.start,v.stop-1] for k,v in COHORTS["Wingless"].items()}
         and p["source"]["Yggdrasil"]==
              {k:[v.start,v.stop-1] for k,v in COHORTS["Yggdrasil"].items()}
         and p["source"]["families"]==list(FAMILIES)
         and p["Yggdrasil"]["held_constant"]==
              {"active":7,"retained":9,"gamma":.25,"penalty":.25}
         and p["Wingless"]["max_states_per_node"]==1
         and all(value is False for value in p["authority"].values()),
         "FROZEN_EXPERIMENT_IDENTITY")
    return p

def build(lane,seed,vec,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vec) in VECTORS
         and seed not in original.COHORTS[lane]["FIT"]
         and seed not in original.COHORTS[lane]["DEV"],"NEW_COHORT_ONLY")
    env=dict(original.build.__globals__)
    env["COHORTS"]=COHORTS
    method=types.FunctionType(original.build.__code__,env,
                              original.build.__name__,original.build.__defaults__)
    family,p,n=method(lane,seed,vec,phase)
    need(family==FAMILIES[(seed-COHORTS[lane][phase].start)%4]
         and original.parent.routes(p,relaxed=family=="one_bit_relaxed_keys")==1
         and original.parent.routes(n,relaxed=family=="one_bit_relaxed_keys")==0,
         "REFERENCE_OUTSIDE_MODEL")
    return family,p,n

def pairs(lane,phase):
    cases=[(seed,tuple(vec),*build(lane,seed,vec,phase))
           for vec in VECTORS for seed in COHORTS[lane][phase]]
    need(len(cases)==48 and
         all(sum(c[2]==f for c in cases)==12 for f in FAMILIES),
         "EXACT_NEW_PUBLIC_COHORT")
    return cases
