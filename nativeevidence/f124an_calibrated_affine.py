"""F124-AN robust source-blind confidence calibration for public affine tasks.

Learn an affine GF2 mapping from public input-output support ONLY. A bounded
RANSAC explores 768 prospectively frozen 17-of-N subsets and selects lowest
total output Hamming residual with uniqueness and calibrated support margin.
Never inspect operator family, source oracle, hidden graph class or DEV fit.
Feistel relationships lie OUTSIDE this deliberately limited hypothesis class.
"""
from __future__ import annotations
import random
import f124am_example_affine_learner as parent
import f124aj_example_operator_learner as public
import f124ag_transition_models as ag
import f124q_fresh_source as q

COUNT=24
TRIALS=768
GRID=((2,1),(3,1),(3,2),(3,4))
def need(value,key):q.need(value,"F124AN_MODEL_"+key)

def fit(demos,nonce,threshold,margin):
    need(type(demos) is list and len(demos)==24 and
         (threshold,margin) in GRID,
         "FROZEN_PUBLIC_SUPPORT_OR_CALIBRATION")
    seen={}
    rng=random.Random("F124AN/ransac/public/"+nonce)
    tried=0;successful=0
    for i in range(TRIALS):
        selection=tuple(sorted(rng.sample(range(COUNT),17)))
        coeff=parent.solve_17([demos[j] for j in selection])
        tried+=1
        if coeff is None or coeff in seen:continue
        if parent.inverse_output(0,coeff) is None:continue
        successful+=1
        err=sum(parent.popcount(parent.forward(parent.integer(d["input_bits"]),coeff)^
                                parent.integer(d["output_bits"])) for d in demos)
        seen[coeff]=err
    ranked=sorted(((e,k) for k,e in seen.items()))
    best=ranked[0][0] if ranked else None
    matches=[coef for err,coef in ranked if err==best] if ranked else []
    runner_up=next((err for err,coef in ranked if err>best),None)
    gap=(runner_up-best) if runner_up is not None else None
    confident=(best is not None and best<=threshold and len(matches)==1
               and (gap is None or gap>=margin))
    return (matches[0] if confident else None),{
        "public_demos":COUNT,"trials":tried,
        "distinct_fullrank_candidates":successful,
        "best_mismatched_output_bits":best,
        "tied_best_models":len(matches),
        "runner_up_gap":gap,
        "calibrated_residual_limit":threshold,
        "calibrated_margin":margin,
        "accepted_unique_affine":confident,
        "abstained":not confident,
        "operator_name_known":False,
        "hypothesis_class":"invertible_affine_GF2_only"}

def normalize(graph,threshold,margin):
    raw,demos,nonce=public.public_task(graph)
    coeff,diagnostic=fit(demos,nonce,threshold,margin)
    if coeff is None:
        return None,{"learner":diagnostic,"normalization_bit_ops":0,
                     "extra_retained_cells":0}
    n=0
    for edge in raw["edges"]:
        decoded=parent.inverse_output(parent.integer(edge["src_bits"]),coeff)
        if decoded is None:
            return None,{"learner":dict(diagnostic,accepted_unique_affine=False,
                                       abstained=True),
                         "normalization_bit_ops":n,"extra_retained_cells":0}
        edge["src_bits"]=[(decoded>>k)&1 for k in range(16)]
        n+=16*16
    ag.frozen.prior.parent.validate_15(raw)
    return raw,{"learner":diagnostic,
                "normalization_bit_ops":n,"extra_retained_cells":0}

def ygg(graph,base,delta,threshold,margin):
    normalized,diag=normalize(graph,threshold,margin)
    if normalized is None:return -1.e9,None,diag
    score,raw,prob,work=ag.ygg_transition(normalized,base,delta,.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "NO_ORIGINAL_7_9_INCREASE")
    return score,work,diag

def select(cases,base,delta):
    """Choose uncertainty cutoffs on NEW TRAIN labels, never on DEV."""
    need(len(cases)==48,"ONLY_FROZEN_NEW_TRAIN_CASES")
    results=[]
    for threshold,margin in GRID:
        correct=fp=wrong=abstain=0
        for seed,vec,fam,operator,nonce,p,n in cases:
            ap,_,dp=ygg(p,base,delta,threshold,margin)
            an,_,dn=ygg(n,base,delta,threshold,margin)
            correct+=int(ap>=0 and an<0)
            fp+=int(an>=0)
            abstain+=int(dp["learner"]["abstained"])+int(dn["learner"]["abstained"])
            # The scorer's model is never told operator/source truth.
            # Source-only evaluator code separately records wrong maps.
        results.append({"threshold":threshold,"margin":margin,
                        "paired":correct,"FP":fp,"abstained_graphs":abstain})
    chosen=sorted(results,key=lambda r:(-r["paired"],r["FP"],
                                        r["threshold"],-r["margin"]))[0]
    return chosen,results
