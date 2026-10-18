"""F124-AX public-only sparse degree-2 inverse candidate, bounded/non-oracle.

Fit 19 columns (16 output bits, affine intercept, two quadratic products)
directly from observed 16-bit public output to public 16-bit input using 256
deterministic RANSAC attempts. Enforce full 16-bit bijection before scoring;
otherwise abstain. The quadratic feature choice is source-blind.
"""
from __future__ import annotations
import random
import math
import f124aj_example_operator_learner as public
import f124ag_transition_models as ag
import f124am_example_affine_learner as gf
import f124q_fresh_source as q

FIT=40
TOTAL=48
TRIALS=256
BUDGET=12
CHECK_MIN=96
FEATURES=19
PAIRS=tuple((i,j) for i in range(16) for j in range(i+1,16))
def need(ok,tag):q.need(ok,"F124AX_QUADRATIC_"+tag)

def feature_word(output, pairs):
    value=gf.integer(output) if not isinstance(output,int) else output
    need(0<=value<65536,"SIXTEEN_OUTPUT_BITS")
    a,b=pairs
    return (value | (1<<16) |
            (((value>>a[0])&(value>>a[1])&1)<<17) |
            (((value>>b[0])&(value>>b[1])&1)<<18))

def solve(samples,pairs):
    need(len(samples)==FEATURES,"FIXED_SYSTEM_RANK")
    rows=[[feature_word(d["output_bits"],pairs),
           gf.integer(d["input_bits"])] for d in samples]
    for bit in range(FEATURES):
        pivot=next((k for k in range(bit,FEATURES) if
                    rows[k][0]&(1<<bit)),None)
        if pivot is None:return None
        rows[bit],rows[pivot]=rows[pivot],rows[bit]
        for k in range(FEATURES):
            if k!=bit and rows[k][0]&(1<<bit):
                rows[k][0]^=rows[bit][0]
                rows[k][1]^=rows[bit][1]
    need(all(rows[k][0]==1<<k for k in range(FEATURES)),
         "GF2_REDUCED_ROW_SYSTEM")
    return tuple(row[1] for row in rows)

def transform(output,coef,pairs):
    mask=feature_word(output,pairs)
    result=0
    while mask:
        low=mask&-mask
        result^=coef[low.bit_length()-1]
        mask^=low
    return result

def bijective(coef,pairs):
    """Exhaustively reject collisions, without inspecting source truth."""
    seen=bytearray(65536)
    for value in range(65536):
        mapped=transform(value,coef,pairs)
        if seen[mapped]:return False
        seen[mapped]=1
    return True

def fit(demos,nonce):
    need(len(demos)==TOTAL and all(len(d["input_bits"])==16
         and len(d["output_bits"])==16 for d in demos),
         "MATCHED_48_PUBLIC_RESPONSES")
    rng=random.Random("F124AX_SPARSE_Q_PUBLIC_ONLY:"+str(nonce))
    sample=demos[:FIT]
    ranked=[]
    for _ in range(TRIALS):
        pairs=tuple(PAIRS[k] for k in rng.sample(range(len(PAIRS)),2))
        row_ids=rng.sample(range(FIT),FEATURES)
        coefficients=solve([sample[k] for k in row_ids],pairs)
        if coefficients is None:continue
        wrong=sum((transform(d["output_bits"],coefficients,pairs)^
                   gf.integer(d["input_bits"])).bit_count()
                  for d in sample)
        ranked.append((wrong,coefficients,pairs))
    ranked.sort(key=lambda t:(t[0],t[1],t[2]))
    for wrong,coefficients,pairs in ranked:
        if wrong>BUDGET:break
        checked=sum(16-(transform(d["output_bits"],coefficients,pairs)^
                        gf.integer(d["input_bits"])).bit_count()
                    for d in demos[FIT:])
        if checked>=CHECK_MIN and bijective(coefficients,pairs):
            return (coefficients,pairs), {
                "fit_bit_errors":wrong,"check_correct_bits":checked,
                "valid_ransac":len(ranked),"fit_solver_trials":TRIALS,
                "public_source_calls_total":48,
                "transient_task_coefficient_bits":(FEATURES*16+2*8),
                "source_operator_known":False,
                "full_domain_bijection_proved":True}
    return None,{
        "fit_bit_errors":ranked[0][0] if ranked else None,
        "check_correct_bits":None,"valid_ransac":len(ranked),
        "fit_solver_trials":TRIALS,"public_source_calls_total":48,
        "transient_task_coefficient_bits":FEATURES*16+2*8,
        "source_operator_known":False,
        "full_domain_bijection_proved":False}

def score(graph,base,delta,fitted):
    norm,_,_=public.public_task(graph)
    if fitted is None:
        return -1e9,None,{"abstained":True,"source_operator_known":False}
    coefficients,pairs=fitted
    for edge in norm["edges"]:
        inv=transform(edge["src_bits"],coefficients,pairs)
        edge["src_bits"]=[(inv>>bit)&1 for bit in range(16)]
    ag.frozen.prior.parent.validate_15(norm)
    val,_,_,work=ag.ygg_transition(norm,list(base),list(delta),.1)
    need(math.isfinite(val) and work["max_active"]<=7
         and work["max_retained"]<=9,"ORIGINAL_SEVEN_NINE")
    return val,work,{"abstained":False,"source_operator_known":False}
