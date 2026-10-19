"""F124-BP: compact learned two-stage nonlinear relationship composition.

32-bit source-blind task-local state (4 bytes), no operator catalog, labels,
source family, memorized graph tokens or privileged true inverse.

 x=(lo,hi) -> ylo=lo+a*hi+b mod256 -> yhi=hi+c*ylo+d mod256
 a,c are odd. Two coupled nonlinear reversible stages in one learned state.

Precommitted FIT enumeration <= 2*128*40, <=16 composed models tested on
40 FIT. CHECK only vetoes acceptance; cannot select a more convenient model.
"""
from __future__ import annotations

import hashlib
import json

CAP=4
FIT=40
CHECK=8
MAX_FIT_BIT_ERRORS=6
MAX_CHECK_BIT_ERRORS=2
CONSENSUS_FIT_MARGIN=1
PARAMETER_BITS=32
PAIR_RESIDUAL_CAP=2*128*40
COMPOSITE_CAP=CAP*CAP*FIT


def require(ok,reason):
    if not ok:raise ValueError("F124BP_COMPOSITION_"+reason)


def forward(x,model):
    require(type(x) is int and 0<=x<65536
            and len(model)==4 and all(type(z) is int and 0<=z<=255 for z in model)
            and model[0]&1 and model[2]&1,"FORWARD_DOMAIN")
    a,b,c,d=model
    lo=x&255
    hi=x>>8
    yl=(lo+a*hi+b)&255
    yh=(hi+c*yl+d)&255
    return yl|(yh<<8)


def inverse(y,model):
    require(type(y) is int and 0<=y<65536,"INVERSE_DOMAIN")
    a,b,c,d=model
    require(a&1 and c&1,"REVERSIBLE_STATE")
    yl=y&255
    yh=y>>8
    hi=(yh-c*yl-d)&255
    lo=(yl-a*hi-b)&255
    return lo|(hi<<8)


def _inputs(fit,check):
    require(isinstance(fit,(list,tuple)) and len(fit)==FIT
            and isinstance(check,(list,tuple)) and len(check)==CHECK,
            "EXACT_PUBLIC_BUDGET")
    for xy in list(fit)+list(check):
        require(isinstance(xy,(list,tuple)) and len(xy)==2
                and all(type(v) is int and 0<=v<=65535 for v in xy),
                "PUBLIC_PAIR_DOMAIN")


def _rank_stage(rows,stage):
    """Recover exact hidden byte intercept from public residual histogram."""
    ranked=[]
    checks=0
    for gain in range(1,256,2):
        histogram={}
        for x,y in rows:
            lo,hi=x&255,x>>8
            yl,yh=y&255,y>>8
            if stage=="low":
                observed=(yl-lo-gain*hi)&255
            else:
                observed=(yh-hi-gain*yl)&255
            histogram[observed]=histogram.get(observed,0)+1
            checks+=1
        # Deterministic best residual, and no extra state beyond 256 bins.
        bias=min(histogram,key=lambda b:(-histogram[b],b))
        mismatch=0
        for x,y in rows:
            lo,hi=x&255,x>>8
            yl,yh=y&255,y>>8
            predicted=((lo+gain*hi+bias)&255) if stage=="low" else (
                (hi+gain*yl+bias)&255)
            actual=yl if stage=="low" else yh
            mismatch+=(predicted^actual).bit_count()
        ranked.append((mismatch,gain,bias))
    ranked.sort()
    return ranked[:CAP],checks


def _errors(rows,model):
    return sum((forward(x,model)^y).bit_count() for x,y in rows)


def learn(public_fit,public_check):
    _inputs(public_fit,public_check)
    low,low_work=_rank_stage(public_fit,"low")
    high,high_work=_rank_stage(public_fit,"high")
    models=sorted((_errors(public_fit,(a,b,c,d)),(a,b,c,d))
                  for _,a,b in low for _,c,d in high)
    best_err,selected=models[0]
    check_error=_errors(public_check,selected)
    # CHECK is not used to optimize or break ties, only veto candidates.
    viable=(best_err<=MAX_FIT_BIT_ERRORS and check_error<=MAX_CHECK_BIT_ERRORS)
    plausible=tuple(m for err,m in models
                    if err<=best_err+CONSENSUS_FIT_MARGIN
                    and _errors(public_check,m)<=MAX_CHECK_BIT_ERRORS)
    if viable:
        require(selected in plausible,"CHECK_CAN_ONLY_VETO")
    digest=hashlib.sha256(json.dumps(public_fit,sort_keys=True,
                                    separators=(",",":")).encode()).hexdigest()
    receipt={
       "schema":"mass.f124bp.fourbyte-public-fit.v1",
       "FIT_observations":FIT,"CHECK_observations":CHECK,
       "parameter_bits":PARAMETER_BITS,
       "fit_bit_errors":best_err,"check_bit_errors":check_error,
       "residual_pair_evaluations":low_work+high_work,
       "residual_budget":PAIR_RESIDUAL_CAP,
       "full_model_pair_evaluations":len(models)*FIT,
       "full_model_budget":COMPOSITE_CAP,
       "candidate_state_count":len(models),
       "confidence_models":len(plausible) if viable else 0,
       "fit_SHA256":digest,
       "CHECK_selected_model":False,
       "private_operator_or_graph_truth_used":False,
       "source_family_classifier_used":False,
       "FIT_ONLY_TRAINING":True,
       "confident":viable
    }
    require(low_work+high_work==PAIR_RESIDUAL_CAP
            and len(models)<=CAP**2
            and len(models)*FIT<=COMPOSITE_CAP,"BOUNDED_LEARNING")
    return (selected if viable else None),receipt,(plausible if viable else ())


def _bits(bits):
    require(type(bits) is list and len(bits)==16 and
            all(type(v) is int and v in (0,1) for v in bits),"NATIVE_BITS")
    return sum(v<<j for j,v in enumerate(bits))


def causal_consensus(graph,model,plausible):
    require(model is not None and model in plausible and
            len(plausible)<=CAP*CAP,"CONFIDENCE_MISSING")
    require(type(graph) is dict and
            set(graph)=={"start","target","roles","edges","demos"},
            "ORIGINAL_GRAPH_FORMAT")
    node=graph["start"]
    carry=None
    hops=0
    for role in graph["roles"]:
        edges=[e for e in graph["edges"]
               if e["from"]==node and e["role"]==role]
        if len(edges)!=1:
            return False,{"decision":"ABSTAIN_PATH_BRANCH","hops":hops}
        e=edges[0]
        preds={inverse(_bits(e["src_bits"]),m) for m in plausible}
        if len(preds)!=1:
            return False,{"decision":"ABSTAIN_NONUNIQUE_INVERSE",
                          "hops":hops,"model_count":len(plausible)}
        prev=next(iter(preds))
        hops+=1
        if carry is not None and prev!=carry:
            return False,{"decision":"REJECT_CAUSAL_DISCONTINUITY","hops":hops}
        carry=_bits(e["dst_bits"])
        node=e["to"]
    accepted=(node==graph["target"])
    return accepted,{"decision":("ACCEPT_CONFIDENT_CAUSAL_CHAIN" if accepted
                               else "REJECT_WRONG_TARGET"),"hops":hops,
                     "model_count":len(plausible)}
