"""F124-U frozen fresh-source readout calibration and causal cell-value intervention.

No new FIT training, no prior DEV reuse, no extra Yggdrasil slots,
no oracle inside prediction. Wingless selects one logit calibration on fresh
FIT only; Yggdrasil applies frozen T coefficients to public cell values
instead of using those same coefficients solely in discrete ranking.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import types

import f124t_absolute_binding as t
import f124q_independent_binding as q
import f124q_fresh_source as source
import f124o_native_learners as model

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124u-frozen-readout-cell-score.json"
FREEZE_BLOB="204b4dc051607aa9a30307875bcafb1d188426a2"
T_SOURCE_BLOB="e230ba3b2552e6a29afa012648cba42d8fefce4e"
MODEL_BLOB="ebad38ff22ef6b151fd5ff7f25da41a20d9fcf65"
COHORTS={
 "Wingless":{"FIT":range(780000,780024),"DEV":range(780100,780124)},
 "Yggdrasil":{"FIT":range(790000,790024),"DEV":range(790100,790124)}
}
VECTORS=t.VECTORS
GRID=(-.75,-.5,-.25,0.,.25,.5,.75)


def need(ok,label):
    source.need(ok,"F124U_"+label)


def git_blob(path):
    b=Path(path).read_bytes().replace(b"\r\n",b"\n")
    return source.git_blob(b)


def frozen():
    t.frozen()
    need(git_blob(FREEZE)==FREEZE_BLOB,"PREREGISTRATION_CHANGED")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124u.frozen-fresh-readout-calibration-and-causal-cell-score.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["parent_f124t_head"]=="01560f7f4f1aab5737cfd045dffd7faaccfb0608"
         and p["lineage"]["t_source_blob"]==T_SOURCE_BLOB
         and p["lineage"]["original_ygg_model_blob"]==MODEL_BLOB
         and p["source"]["cohorts"]==
            {lane:{phase:[s.start,s.stop-1] for phase,s in sub.items()}
             for lane,sub in COHORTS.items()}
         and p["hypotheses"]["Wingless"]["bias_grid"]==list(GRID)
         and p["hypotheses"]["Yggdrasil"]["coefficient"]==.15
         and p["reporting"]["no_extra_training"]
         and all(v is False for v in p["authority"].values())
         and git_blob(t.__file__)==T_SOURCE_BLOB
         and git_blob(q.__file__)==MODEL_BLOB,
         "FROZEN_METHOD_OR_SOURCE_IDENTITY")
    return p


def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and seed in COHORTS[lane][phase]
         and seed not in t.COHORTS[lane]["FIT"]
         and seed not in t.COHORTS[lane]["DEV"]
         and seed not in source.COHORTS[lane]["FIT"]
         and seed not in source.COHORTS[lane]["DEV"]
         and tuple(vector) in VECTORS,"ONLY_FRESH_PUBLIC_PAIRS")
    env=dict(t.build.__globals__)
    env["COHORTS"]=COHORTS
    fn=types.FunctionType(t.build.__code__,env,t.build.__name__,t.build.__defaults__)
    positive,negative=fn(lane,seed,vector,phase)
    need(source.paired_admit(positive,negative),"AUTHENTIC_PUBLIC_SOURCE_PAIR")
    return positive,negative


def pairs(lane,phase):
    need(lane in COHORTS and phase in ("FIT","DEV"),"NO_OTHER_COHORT")
    return [(seed,tuple(vec),*build(lane,seed,vec,phase))
            for vec in VECTORS for seed in COHORTS[lane][phase]]


def yggdrasil_value_intervention(g,base,delta):
    """Exact original T hard 7/9 state limits with one preregistered score path.

    Source-blind: no label, route oracle or paired negative at inference.
    Original qmodel.yggdrasil_lookahead is immutable and used as a control.
    """
    source.validate_public(g)
    need(len(base)==7 and len(delta)==2 and
         all(math.isfinite(float(z)) for z in (*base,*delta)),"WEIGHT_SHAPE")
    edges=model.sorted_edges(g)
    active=[(g["start"],None,0.)]
    retained=[]
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
          "max_retained":0,"evictions":0,"prospective_key_comparisons":0,
          "active_cell_limit":7,"retained_cell_limit":9}
    def comp(left,right):
        if left is None:return 1.
        work["raw_bit_ops"]+=16
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            left[j*4:j*4+4],right[j*4:j*4+4]))/4.
            for j in range(4))/4.
    for i,role in enumerate(g["roles"]):
        nextrole=g["roles"][i+1] if i+1<len(g["roles"]) else None
        candidates=[]
        for node,carried,score in active+retained:
            work["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:continue
                similarity=comp(carried,edge["src_bits"])
                value=score+base[4]*(similarity-.35)
                competition=base[5]*(similarity-.5)
                if nextrole is None:
                    look=0.
                else:
                    possible=[e for e in edges
                              if e["from"]==edge["to"] and e["role"]==nextrole]
                    work["public_edge_scans"]+=len(edges)
                    look=max((comp(tuple(edge["dst_bits"]),p["src_bits"])
                             for p in possible),default=0.)
                    work["prospective_key_comparisons"]+=len(possible)
                value+=.15*(delta[0]+delta[1])*(look-.5)
                cell=(edge["to"],tuple(edge["dst_bits"]),value)
                candidates.append((value+competition+delta[0]*(look-.5),
                                   value-competition+delta[1]*(look-.5),cell))
        candidates.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active=[row[2] for row in candidates[:7]]
        selected={id(row) for row in candidates[:7]}
        extras=[row for row in candidates if id(row) not in selected]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[row[2] for row in extras[:9]]
        work["evictions"]+=max(0,len(candidates)-16)
        work["max_active"]=max(work["max_active"],len(active))
        work["max_retained"]=max(work["max_retained"],len(retained))
        need(len(active)<=7 and len(retained)<=9 and
             len(active)+len(retained)<=16,"EXACT_7_PLUS_9")
    terminal=[v for node,_,v in active+retained if node==g["target"]]
    best=max(terminal,default=-2.*len(g["roles"]))
    logit=4.*(best/max(1,len(g["roles"])-1)-base[6])
    need(math.isfinite(logit),"FINITE_VALUE")
    return logit,work


def choose_fit_bias(fit_pairs,base,delta):
    """One predeclared grid, paired accuracy only. No DEV during selection."""
    need(len(fit_pairs)==48,"FIT_DENOMINATOR")
    rows=[]
    cache=[]
    for _,_,pos,neg in fit_pairs:
        a,_=q.forward("Wingless",pos,list(base),list(delta))
        b,_=q.forward("Wingless",neg,list(base),list(delta))
        cache.append((a,b))
    for bias in GRID:
        correct=sum(a+bias>=0 and b+bias<0 for a,b in cache)
        rows.append({"bias":bias,"paired":correct})
    selected=sorted(rows,key=lambda x:(-x["paired"],abs(x["bias"]),x["bias"]))[0]
    return selected,rows
