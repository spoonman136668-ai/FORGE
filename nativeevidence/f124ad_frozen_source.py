"""F124-AD disjoint preregistered source adapter, parent bytecode unchanged."""
from __future__ import annotations
import json,types
from pathlib import Path
import f124ac_frozen_source as previous
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as source

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ad-frozen-long-chain-and-fingerprint.json"
FREEZE_BLOB="69a0a65c561e2c901ea2ad13310657cc16e6f997"
ADMISSION=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ad-source-admission-amendment-v2.json"
ADMISSION_BLOB="f7a32422bca8adf1b64e19e0737f163bef4771d0"
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
         and witness.blob(ADMISSION)==ADMISSION_BLOB
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
    amendment=json.loads(ADMISSION.read_text(encoding="utf-8"))
    need(amendment["schema"]==
         "forge.research.f124ad.public-source-admission-amendment.v2"
         and amendment["state"]=="FROZEN_BEFORE_ANY_SUCCESSFUL_FIT_OR_DEV"
         and amendment["max_attempts"]==20
         and amendment["step"]==24
         and amendment["sample_positions"]==24
         and amendment["original_freeze"]==FREEZE_BLOB
         and all(v is True for v in amendment["invariants"].values()
                 if isinstance(v,bool) and v is True)
         and amendment["invariants"]["protected_first_use"] is False,
         "PRE_FIT_ADMISSION_RULE")
    return p

def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in VECTORS
         and seed not in previous.COHORTS[lane]["FIT"]
         and seed not in previous.COHORTS[lane]["DEV"],
         "NEW_SOURCE_IDENTITY")
    # Deterministic source-birth rejection sampling: no model or label scoring.
    # Numerical disjointness: FIT candidates are strictly below DEV's base.
    selected_base=COHORTS[lane][phase].start
    dev_base=COHORTS[lane]["DEV"].start
    position=seed-selected_base
    extended={ln:{stage:range(keys.start,keys.start+24*20+24)
                  for stage,keys in stages.items()}
              for ln,stages in COHORTS.items()}
    env=dict(previous.build.__globals__)
    env["COHORTS"]=extended
    method=types.FunctionType(previous.build.__code__,env,
                              previous.build.__name__,previous.build.__defaults__)
    for attempt in range(20):
        chosen=selected_base+position+24*attempt
        if phase=="FIT" and chosen>=dev_base:
            break  # never expose a FIT sample inside DEV's reserved support
        try:
            family,p,n=method(lane,chosen,vector,phase)
        except source.Quarantined:
            continue  # original admission guard rejects; never weaken it
        need(family==FAMILIES[(seed-selected_base)%4]
             and previous.original.parent.routes(
                 p,relaxed=family=="one_bit_relaxed_keys")==1
             and previous.original.parent.routes(
                 n,relaxed=family=="one_bit_relaxed_keys")==0,
             "INDEPENDENT_PUBLIC_REFERENCE_ADMISSION")
        return family,p,n,chosen
    raise source.Quarantined("F124AD_PRE_FIT_ADMISSION_EXHAUSTED_"+lane+"_"+phase+"_"+str(position))

def pairs(lane,phase):
    out=[]
    for vec in VECTORS:
        for requested_seed in COHORTS[lane][phase]:
            family,p,n,selected_seed=build(lane,requested_seed,vec,phase)
            out.append((selected_seed,tuple(vec),family,p,n))
    need(len(out)==48 and
         all(sum(x[2]==fam for x in out)==12 for fam in FAMILIES)
         and (phase!="FIT" or all(x[0]<COHORTS[lane]["DEV"].start for x in out)),
         "FROZEN_FAMILY_AND_PHASE_SEED_CENSUS")
    return out
