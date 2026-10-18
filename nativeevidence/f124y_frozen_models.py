"""F124-Y frozen source-only model adapters for independent resource budget
and FIT-only Yggdrasil readout calibration. No original model changes.
"""
from __future__ import annotations
import json,math,types
from pathlib import Path
import f124x_frozen_models as x
import f124w_hop_trace_indexed as w
import f124v_collision_centered as v
import f124q_fresh_source as source

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124y-frozen-budgeted-readout.json"
FREEZE_BLOB="f16ba9cedf2ed6c52edb3a67117c1dce2721cdd3"
PARENT_BLOB="364f447f4e62a0ef5d3855bd6911934ec0c48371"
COHORTS={
 "Wingless":{"FIT":range(1180000,1180024),"DEV":range(1180100,1180124)},
 "Yggdrasil":{"FIT":range(1190000,1190024),"DEV":range(1190100,1190124)}
}
BIAS=(-2.,-1.5,-1.,-.5,0.,.5,1.,1.5,2.)
SLOPE=(-1.,-.5,0.,.5,1.)
CHECKSUM=(1,3,4,2)


def need(ok,code):
    source.need(ok,"F124Y_"+code)


def frozen():
    x.frozen()
    need(w.blob(FREEZE)==FREEZE_BLOB,"FROZEN_PROTOCOL")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124y.frozen-budgeted-replication-and-fit-readout.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["parent_head"]=="4f7fa505737acae4568df755b4804c384b057980"
         and p["lineage"]["parent_model_blob"]==PARENT_BLOB
         and p["source"]["FIT"]==
             {k:[states["FIT"].start,states["FIT"].stop-1] for k,states in COHORTS.items()}
         and p["source"]["DEV"]==
             {k:[states["DEV"].start,states["DEV"].stop-1] for k,states in COHORTS.items()}
         and p["Yggdrasil"]["bias_grid"]==list(BIAS)
         and p["Yggdrasil"]["slope_grid"]==list(SLOPE)
         and p["Wingless"]["checksum"]==list(CHECKSUM)
         and p["Wingless"]["benchmark"]["repeats_per_case"]==5
         and all(value is False for value in p["authority"].values())
         and w.blob(x.__file__)==PARENT_BLOB,"FROZEN_SOURCE_OR_AUTHORITY")
    return p


def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in x.VECTORS
         and seed not in x.COHORTS[lane]["FIT"]
         and seed not in x.COHORTS[lane]["DEV"]
         and seed not in w.COHORTS[lane]["FIT"]
         and seed not in w.COHORTS[lane]["DEV"]
         and seed not in source.FORBIDDEN[lane],
         "FRESH_PUBLIC_SOURCE")
    global_vars=dict(x.build.__globals__)
    global_vars["COHORTS"]=COHORTS
    f=types.FunctionType(x.build.__code__,global_vars,
                         x.build.__name__,x.build.__defaults__)
    pos,neg=f(lane,seed,vector,phase)
    need(source.paired_admit(pos,neg),"SOURCE_ADMISSION")
    return pos,neg


def pairs(lane,phase):
    need(lane in COHORTS and phase in ("FIT","DEV"),"KNOWN_PHASE")
    return [(seed,tuple(vec),*build(lane,seed,vec,phase))
            for vec in x.VECTORS for seed in COHORTS[lane][phase]]


def checksum_uncached(graph,base,delta):
    """Byte-identical old V forward, alternative frozen checksum injected as
    an *ephemeral function global*, not a source change or rebuilt engine.
    """
    def alternate_nibble(bits):
        need(type(bits) is list and len(bits)==4 and
             all(type(b) is int and b in (0,1) for b in bits),
             "UNCACHED_NIBBLE")
        return sum(vv*bb for vv,bb in zip(CHECKSUM,bits))%5
    namespace=dict(v.wingless_collision_reassignment.__globals__)
    namespace["nibble_code"]=alternate_nibble
    original=types.FunctionType(v.wingless_collision_reassignment.__code__,
                                namespace,v.wingless_collision_reassignment.__name__,
                                v.wingless_collision_reassignment.__defaults__)
    return original(graph,base,delta)


def calibrated_logit(logit,depth,intercept,slope):
    need(depth in (7,8,9) and intercept in BIAS and slope in SLOPE
         and math.isfinite(logit),"READOUT_FROZEN_PARAMETERS")
    return logit+intercept+slope*(depth-8)


def select_fit_bias(fit_pairs,base,delta):
    """One source-disjoint positive/negative FIT grid, no DEV inspection."""
    need(len(fit_pairs)==48,"FIT_PAIRS")
    raw=[]
    for _,_,pos,neg in fit_pairs:
        p,_,_=x.frozen_yggdrasil_score(pos,base,delta,"V_centered")
        n,_,_=x.frozen_yggdrasil_score(neg,base,delta,"V_centered")
        raw.append((p,n,len(pos["roles"])))
    measurements=[]
    for intercept in BIAS:
        for slope in SLOPE:
            n=sum(calibrated_logit(p,d,intercept,slope)>=0 and
                  calibrated_logit(q,d,intercept,slope)<0
                  for p,q,d in raw)
            measurements.append({"bias":intercept,"slope":slope,"paired":n})
    selected=sorted(measurements,key=lambda z:(
        -z["paired"],abs(z["bias"])+abs(z["slope"]),
        z["bias"],z["slope"]))[0]
    return selected,measurements
