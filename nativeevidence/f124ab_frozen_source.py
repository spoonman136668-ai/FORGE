"""F124-AB: immutable parental generator with new independent FIT/DEV sources."""
from __future__ import annotations
import json,types
from pathlib import Path
import f124aa_frozen_source as parent
import f124w_hop_trace_indexed as guard
import f124q_fresh_source as source

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ab-frozen-soft-key-and-packed-pareto.json"
FREEZE_BLOB="61724ad438c1609a6738bef7b7a3e239132d8944"
PARENT_SOURCE_BLOB="11e01c477b46c06e8a71240cf6b7ddf8aa8f4e78"
PARENT_MODEL_BLOB="6d4bb7cbbed1759a92437bd3cd37d373aab86354"
COHORTS={"Wingless":{"FIT":range(1480000,1480024),"DEV":range(1480100,1480124)},
         "Yggdrasil":{"FIT":range(1490000,1490024),"DEV":range(1490100,1490124)}}
FAMILIES=parent.FAMILIES
VECTORS=parent.VECTORS

def need(ok,why):
    source.need(ok,"F124AB_"+why)

def frozen():
    parent.frozen()
    need(guard.blob(FREEZE)==FREEZE_BLOB
         and guard.blob(parent.__file__)==PARENT_SOURCE_BLOB,
         "FROZEN_OR_ORIGINAL_SOURCE_BLOB")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124ab.frozen-hamming-tolerance-and-packed-pareto.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["qualified_parent"]==
           "53bf4555ef3a88dbc126af4ff060aadecc976d9b"
         and p["source"]["cohorts"]==
           {lane:{phase:[r.start,r.stop-1] for phase,r in parts.items()}
             for lane,parts in COHORTS.items()}
         and p["source"]["four_families"]==list(FAMILIES)
         and p["Yggdrasil"]["gamma_grid"]==[0,.25,.5,1,2]
         and p["Yggdrasil"]["penalty_grid"]==[0,.25,.5,1,2]
         and p["Wingless"]["capacities"]==[1,2,3]
         and all(v is False for v in p["authority"].values()),
         "FROZEN_PROPOSAL_IDENTITY")
    return p

def build(lane,seed,vec,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vec) in VECTORS
         and seed not in parent.COHORTS[lane]["FIT"]
         and seed not in parent.COHORTS[lane]["DEV"],
         "NEW_SOURCE_ONLY")
    env=dict(parent.build.__globals__)
    env["COHORTS"]=COHORTS
    method=types.FunctionType(parent.build.__code__,env,
                               parent.build.__name__,parent.build.__defaults__)
    family,pos,neg=method(lane,seed,vec,phase)
    need(family==FAMILIES[(seed-COHORTS[lane][phase].start)%4]
         and parent.routes(pos,relaxed=family=="one_bit_relaxed_keys")==1
         and parent.routes(neg,relaxed=family=="one_bit_relaxed_keys")==0,
         "AUTHENTIC_ALTERNATIVE_REFERENCE_ADMISSION")
    return family,pos,neg

def pairs(lane,phase):
    result=[]
    for v in VECTORS:
        for seed in COHORTS[lane][phase]:
            family,pos,neg=build(lane,seed,v,phase)
            result.append((seed,tuple(v),family,pos,neg))
    need(len(result)==48 and
         all(sum(c[2]==family for c in result)==12 for family in FAMILIES),
         "PUBLIC_PAIR_CENSUS")
    return result
