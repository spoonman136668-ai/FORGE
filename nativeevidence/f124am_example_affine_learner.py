"""F124-AM source-blind learned affine GF(2) representation.

From public examples alone, robustly fit an unknown full 16x16 bit-mixing
matrix and affine offset using deterministic bounded RANSAC and exact GF(2)
elimination. The hypothesis family intentionally cannot represent Feistel.
No operator string, source evaluator, oracle, label or protected data access.
"""
from __future__ import annotations
import random
import f124aj_example_operator_learner as public
import f124ag_transition_models as old
import f124ae_scoring_transfer as wing_old
import f124q_fresh_source as q

COUNTS=(17,20,24)
GAMMAS=(0.,.1,.25,.5,1.)
TRIALS=160
def need(ok,tag):q.need(ok,"F124AM_LEARN_"+tag)
def integer(bits):return sum(bit<<i for i,bit in enumerate(bits))
def popcount(v):return v.bit_count()

def solve_17(sample):
    """Fit 17 input columns incl intercept, simultaneously for 16 outputs."""
    rows=[[(integer(d["input_bits"])|(1<<16)),integer(d["output_bits"])]
          for d in sample]
    need(len(rows)==17,"FIXED_17_DIMENSION")
    for bit in range(17):
        pivot=next((i for i in range(bit,17) if rows[i][0]&(1<<bit)),None)
        if pivot is None:return None
        rows[bit],rows[pivot]=rows[pivot],rows[bit]
        for j in range(17):
            if j!=bit and rows[j][0]&(1<<bit):
                rows[j][0]^=rows[bit][0]
                rows[j][1]^=rows[bit][1]
    need(all(row[0]==1<<i for i,row in enumerate(rows)),
         "GF2_EXACT_GAUSSIAN_PIVOT")
    return tuple(row[1] for row in rows)

def forward(x,coeff):
    result=coeff[16]
    while x:
        low=x&-x
        result^=coeff[low.bit_length()-1]
        x^=low
    return result

def inverse_output(output,coeff):
    # Solve the 16x16 linear map once per input, never consult generator.
    # Augmented unknown input bits recovered by 16 GF2 row equations.
    rows=[]
    for out_bit in range(16):
        input_mask=sum((((coeff[i]>>out_bit)&1)<<i)
                       for i in range(16))
        response=((output^coeff[16])>>out_bit)&1
        rows.append([input_mask,response])
    for bit in range(16):
        pivot=next((i for i in range(bit,16) if rows[i][0]&(1<<bit)),None)
        if pivot is None:return None
        rows[bit],rows[pivot]=rows[pivot],rows[bit]
        for j in range(16):
            if j!=bit and rows[j][0]&(1<<bit):
                rows[j][0]^=rows[bit][0];rows[j][1]^=rows[bit][1]
    return sum(rows[i][1]<<i for i in range(16))

def fit_affine(demos,count,nonce):
    need(count in COUNTS and len(demos)==24,
         "PUBLIC_SOURCE_ONLY_FIT_GRID")
    sample=demos[:count]
    seen={}
    first=tuple(range(17))
    selections=[first]
    rng=random.Random("F124AM/learner/public/"+nonce+"/"+str(count))
    for _ in range(TRIALS-1):
        selections.append(tuple(sorted(rng.sample(range(count),17))))
    for chosen in selections:
        coeff=solve_17([sample[i] for i in chosen])
        if coeff is None or coeff in seen:continue
        errors=sum(popcount(forward(integer(d["input_bits"]),coeff)^
                            integer(d["output_bits"])) for d in sample)
        seen[coeff]=errors
        if errors==0:break
    if not seen:return None,{"demos":count,"unique":False,
        "best_mismatched_output_bits":None,
        "unique_models":0,"full_rank_candidates":0,
        "out_of_class_rejected":True,"source_operator_known":False}
    minimum=min(seen.values())
    best=[coef for coef,e in seen.items() if e==minimum]
    unique=(minimum<=2 and len(best)==1)
    fit=best[0] if unique else None
    # A fit is only valid for source-inversion if its 16-bit linear
    # submatrix is invertible, no hidden oracle fallback.
    if fit is not None and inverse_output(0,fit) is None:
        unique=False;fit=None
    return fit,{"demos":count,"unique":unique,
        "best_mismatched_output_bits":minimum,
        "unique_models":len(best),
        "full_rank_candidates":len(seen),
        "out_of_class_rejected":not unique,
        "source_operator_known":False}

def normalize(graph,count):
    base,demos,nonce=public.public_task(graph)
    coeff,diag=fit_affine(demos,count,nonce)
    if coeff is None:
        return None,{"learner":diag,"bit_ops":0,
                     "extra_retained_cells":0}
    ops=0
    for edge in base["edges"]:
        output=integer(edge["src_bits"])
        raw=inverse_output(output,coeff)
        if raw is None:
            return None,{"learner":dict(diag,unique=False),
                         "bit_ops":ops,"extra_retained_cells":0}
        edge["src_bits"]=[(raw>>i)&1 for i in range(16)]
        ops+=16*16
    old.frozen.prior.parent.validate_15(base)
    return base,{"learner":diag,"bit_ops":ops,
                 "extra_retained_cells":0}

def ygg(graph,weights,delta,count):
    g,meta=normalize(graph,count)
    if g is None:return -1.e9,None,meta
    score,raw,soft,work=old.ygg_transition(g,weights,delta,.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "HISTORICAL_7_ACTIVE_9_RETAINED")
    return score,work,meta

def wing(graph,weights,delta,count,gamma):
    g,meta=normalize(graph,count)
    if g is None:return -1.e9,None,meta
    from f124am_terminal_competition import terminal_competitive
    score,work=terminal_competitive(g,weights,delta,gamma)
    need(work["max_states_per_node"]==1 and
         work["max_packed_bits_per_state"]==12 and
         work["max_active"]<=64,
         "ONE_ORIGINAL_PACKED_STATE")
    return score,work,meta

def fit_support(cases,weights,delta):
    need(len(cases)==48,"FROZEN_TRAIN_ONLY")
    grid=[]
    for count in COUNTS:
        paired=fp=abstentions=0
        for seed,v,fam,op,nonce,p,n in cases:
            a,_,am=ygg(p,weights,delta,count)
            b,_,bm=ygg(n,weights,delta,count)
            paired+=int(a>=0 and b<0);fp+=int(b>=0)
            abstentions+=int(not am["learner"]["unique"])+int(
                not bm["learner"]["unique"])
        grid.append({"count":count,"paired":paired,
                     "FP":fp,"abstentions":abstentions})
    return sorted(grid,key=lambda z:(-z["paired"],z["FP"],z["count"]))[0],grid

def fit_gamma(cases,weights,delta,count):
    need(len(cases)==48 and count in COUNTS,"TRAIN_ONLY_GAMMA")
    grid=[]
    baseline_positive_long=0
    reference=[]
    for seed,v,fam,op,nonce,p,n in cases:
        base,_w,_m=wing(p,weights,delta,count,0.)
        if fam in ("rotate4_dense_13_15","xor16_extended_13_15"):
            baseline_positive_long+=int(base>=0)
        reference.append((seed,v,fam,op,nonce,p,n))
    for gamma in GAMMAS:
        paired=fp=long_positive=0
        for seed,v,fam,op,nonce,p,n in reference:
            a,_,_=wing(p,weights,delta,count,gamma)
            b,_,_=wing(n,weights,delta,count,gamma)
            paired+=int(a>=0 and b<0)
            fp+=int(b>=0)
            if fam in ("rotate4_dense_13_15","xor16_extended_13_15"):
                long_positive+=int(a>=0)
        row={"gamma":gamma,"paired":paired,"FP":fp,
             "long_positive":long_positive,
             "baseline_long_positive":baseline_positive_long,
             "train_preserves_positive":long_positive>=baseline_positive_long}
        grid.append(row)
    eligible=[r for r in grid if r["train_preserves_positive"]]
    need(eligible and any(r["gamma"]==0. for r in eligible),
         "GAMMA_ZERO_BASELINE_INELIGIBLE")
    return sorted(eligible,key=lambda z:(-z["paired"],z["FP"],z["gamma"]))[0],grid
