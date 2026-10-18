"""F124-X source-frozen independent Wingless validation and Yggdrasil readout.

No model training and no data-derived selection. Frozen W algorithms and
original O/T weights remain unchanged. Causal witness never enters inference.
"""
from __future__ import annotations
import json, math, types
from pathlib import Path
import f124w_hop_trace_indexed as w
import f124q_fresh_source as source

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124x-frozen-readout-runtime.json"
FREEZE_BLOB="3eb6e32c29505aa2b88ecb8860291f27241ea3e4"
W_BLOB="21d80fc814b2036095ab9e1a42cbec052e95e278"
COHORTS={
 "Wingless":{"FIT":range(1080000,1080024),"DEV":range(1080100,1080124)},
 "Yggdrasil":{"FIT":range(1090000,1090024),"DEV":range(1090100,1090124)}
}
VECTORS=w.VECTORS
SELECTED=(1,3,4,2)


def need(ok,tag):
    source.need(ok,"F124X_"+tag)


def frozen():
    w.frozen()
    need(w.blob(FREEZE)==FREEZE_BLOB,"SOURCE_PREIMPLEMENTATION_FREEZE")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124x.frozen-new-validation-and-score-readout.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["qualified_parent"]==
             "af17fadc6bb66e30a6f7ebd1a6a629398cc09709"
         and p["lineage"]["parent_model_blob"]==W_BLOB
         and p["source"]["cohorts"]==
             {lane:{phase:[r.start,r.stop-1] for phase,r in states.items()}
              for lane,states in COHORTS.items()}
         and p["Wingless"]["selected_checksum"]==list(SELECTED)
         and p["Wingless"]["benchmark"]["sample_pairs_per_depth"]==4
         and p["Wingless"]["benchmark"]["repeats"]==3
         and p["Yggdrasil"]["readout_arms"]==
            ["T_original_depth_minus_one","V_original_depth","V_counterfactual_depth_minus_one"]
         and p["Yggdrasil"]["hard_cell_budget"]=={"active":7,"retained":9}
         and all(x is False for x in p["control"].values()
                if isinstance(x,bool))
         and w.blob(w.__file__)==W_BLOB,
         "SOURCE_OR_SAFETY_IDENTITY")
    return p


def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in VECTORS
         and seed not in w.COHORTS[lane]["FIT"]
         and seed not in w.COHORTS[lane]["DEV"]
         and seed not in source.COHORTS[lane]["FIT"]
         and seed not in source.COHORTS[lane]["DEV"]
         and seed not in source.FORBIDDEN[lane],
         "NEW_NONRESERVED_SOURCE_ONLY")
    env=dict(w.build.__globals__)
    env["COHORTS"]=COHORTS
    function=types.FunctionType(w.build.__code__,env,w.build.__name__,
                                w.build.__defaults__)
    pos,neg=function(lane,seed,vector,phase)
    need(source.paired_admit(pos,neg),"PUBLIC_CAUSAL_PAIR_ADMISSION")
    return pos,neg


def pairs(lane,phase):
    need(lane in COHORTS and phase in ("FIT","DEV"),"KNOWN_COHORT")
    return [(seed,tuple(vector),*build(lane,seed,vector,phase))
            for vector in VECTORS for seed in COHORTS[lane][phase]]


def frozen_yggdrasil_score(graph,base,delta,mode):
    """Source-blind frozen score. V counterfactual changes *only* readout."""
    need(mode in ("T_rank_only","V_centered","V_depth_minus_one"),"FROZEN_READOUT")
    source.validate_public(graph)
    observed_mode="T_rank_only" if mode=="T_rank_only" else "V_centered"
    original_logit,work,trace=w.ygg_hop_trace(graph,base,delta,observed_mode)
    if mode!="V_depth_minus_one":
        return original_logit,work,trace
    depth=len(graph["roles"])
    final=trace[-1]
    target=[cell[2] for cell in final["active"]+final["retained"]
            if cell[0]==graph["target"]]
    best=max(target,default=-2.*depth)
    new_logit=4.*(best/max(1,depth-1)-base[6])
    need(math.isfinite(new_logit),"FINITE_READOUT")
    return new_logit,work,trace
