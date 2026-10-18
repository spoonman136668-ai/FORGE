"""F124-AD disjoint preregistered source adapter, parent bytecode unchanged."""
from __future__ import annotations
import json,types
from pathlib import Path
import f124ac_frozen_source as previous
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as source

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ad-frozen-long-chain-and-fingerprint.json"
FREEZE_BLOB="69a0a65c561e2c901ea2ad13310657cc16e6f997"
PARENT_SOURCE_BLOB="e735ec894e650491fc53e3f1fb2e6002f2e148e2"
COHORTS={"Wingless":{"FIT":range(1680000,1680024),"DEV":range(1680100,1680124)},
         "Yggdrasil":{"FIT":range(1690000,1690024),"DEV":range(1690100,1690124)}}
VECTORS=previous.VECTORS
FAMILIES=previous.FAMILIES
ANCHORS=(8,9,10,11,16)
ALPHAS=(0.,.1,.25,.5)

def need(ok,label):
    source.need(ok,"F124AD_"+label)

def frozen():
    previous.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB
         and witness.blob(previous.__file__)==PARENT_SOURCE_BLOB,
         "ORIGINAL_PREREGISTRATION_AND_PARENT_SOURCE")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124ad.frozen-depth-readout-and-four-bit-key-witness.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["exact_qualified_parent"]==
             "9942043805a525406c52838cd8cea18fb2949817"
         and p["source"]["Wingless"]==
             {k:[r.start,r.stop-1] for k,r in COHORTS["Wingless"].items()}
         and p["source"]["Yggdrasil"]==
             {k:[r.start,r.stop-1] for k,r in COHORTS["Yggdrasil"].items()}
         and p["source"]["families"]==list(FAMILIES)
         and p["Yggdrasil"]["anchor_grid"]==list(ANCHORS)
         and p["Wingless"]["alpha_grid"]==list(ALPHAS)
         and all(value is False for value in p["authority"].values()),
         "SOURCE_MODEL_OR_AUTHORITY_DRIFT")
    return p

def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in VECTORS
         and seed not in previous.COHORTS[lane]["FIT"]
         and seed not in previous.COHORTS[lane]["DEV"],
         "NEW_SOURCE_IDENTITY")
    env=dict(previous.build.__globals__)
    env["COHORTS"]=COHORTS
    method=types.FunctionType(previous.build.__code__,env,
                              previous.build.__name__,previous.build.__defaults__)
    family,p,n=method(lane,seed,vector,phase)
    need(family==FAMILIES[(seed-COHORTS[lane][phase].start)%4]
         and previous.original.parent.routes(
             p,relaxed=family=="one_bit_relaxed_keys")==1
         and previous.original.parent.routes(
             n,relaxed=family=="one_bit_relaxed_keys")==0,
         "INDEPENDENT_PUBLIC_REFERENCE_ADMISSION")
    return family,p,n

def pairs(lane,phase):
    out=[(seed,tuple(vec),*build(lane,seed,vec,phase))
         for vec in VECTORS for seed in COHORTS[lane][phase]]
    need(len(out)==48 and
         all(sum(x[2]==fam for x in out)==12 for fam in FAMILIES),
         "FROZEN_FAMILY_CENSUS")
    return out
