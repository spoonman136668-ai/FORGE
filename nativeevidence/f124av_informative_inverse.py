"""F124-AV source-blind robust affine inverse on expanded, query-priced support.

Only returned PUBLIC pairs are inputs. 48 queried support examples cost 48
public forward-response accesses including 24 original demos (6 bit-corrupt
outputs total); 40 FIT, 8 CHECK. Frozen 256 robust GF2 trials. Neither
operator name nor task-truth enters any fit, scoring, or abstention decision.
"""
from __future__ import annotations
import random,math
import f124am_example_affine_learner as gf
import f124aj_example_operator_learner as public
import f124ag_transition_models as ag
import f124q_fresh_source as q

FIT=40;TOTAL=48;TRIALS=256
BUDGETS=(6,12);CHECK_LIMITS=(96,112)
def need(ok,name):q.need(ok,"F124AV_PUBLIC_RANSAC_"+name)

def fit(demos,nonce):
    need(len(demos)==TOTAL and all(len(d["input_bits"])==
         len(d["output_bits"])==16 for d in demos),
         "EXACT_PUBLIC_SUPPORT_BUDGET")
    sample=demos[:FIT]
    rng=random.Random("F124AV/RANSAC_ONLY_PUBLIC_NONCE:"+nonce)
    choices={tuple(range(17))}
    while len(choices)<TRIALS:
        choices.add(tuple(sorted(rng.sample(range(FIT),17))))
    ranked=[]
    for indices in sorted(choices):
        coeff=gf.solve_17([sample[i] for i in indices])
        if coeff is None or gf.inverse_output(0,coeff) is None:
            continue
        wrong=sum((gf.forward(gf.integer(x["input_bits"]),coeff)^
                    gf.integer(x["output_bits"])).bit_count()
                  for x in sample)
        ranked.append((wrong,coeff))
    if not ranked:
        return None,{"fit_bit_errors":None,"valid_ransac":0,
                     "all_ransac_attempts":TRIALS,
                     "transient_task_coefficient_bits":0,
                     "public_source_calls_total":48,
                     "total_public_bit_reads_lower":48*32,
                     "source_operator_known":False}
    best=min(ranked,key=lambda t:(t[0],t[1]))
    return best[1],{"fit_bit_errors":best[0],
        "valid_ransac":len(ranked),"all_ransac_attempts":TRIALS,
        "transient_task_coefficient_bits":17*16,
        "fit_workspace_bits_lower":FIT*33,
        "public_source_calls_total":48,
        "total_public_bit_reads_lower":48*32,
        "source_operator_known":False}

def check(demos,coeff):
    if coeff is None:return 0
    total=0
    for row in demos[FIT:]:
        x=gf.inverse_output(gf.integer(row["output_bits"]),coeff)
        if x is None:return 0
        total+=16-(x^gf.integer(row["input_bits"])).bit_count()
    need(0<=total<=128,"PUBLIC_CHECK_RANGE")
    return total

def score(graph,base,delta,coeff,info,check_correct,budget,minimum):
    need(budget in BUDGETS and minimum in CHECK_LIMITS,
         "FROZEN_SOURCE_BLIND_GRID")
    normalized,demos,nonce=public.public_task(graph)
    admitted=(coeff is not None and
              info["fit_bit_errors"]<=budget and check_correct>=minimum)
    diag={"abstained":not admitted,"public_CHECK_correct":check_correct,
          "public_FIT_bit_errors":info["fit_bit_errors"],
          "extra_task_model_bits":info["transient_task_coefficient_bits"],
          "query_calls":48,"source_operator_known":False}
    if not admitted:return -1e9,None,diag
    for e in normalized["edges"]:
        value=gf.inverse_output(gf.integer(e["src_bits"]),coeff)
        need(value is not None,"VALID_INVERSE_PER_EDGE")
        e["src_bits"]=[(value>>k)&1 for k in range(16)]
    ag.frozen.prior.parent.validate_15(normalized)
    val,_,_,work=ag.ygg_transition(normalized,list(base),list(delta),.1)
    need(math.isfinite(val) and work["max_active"]<=7 and
         work["max_retained"]<=9,"ORIGINAL_SEVEN_NINE")
    return val,work,diag
