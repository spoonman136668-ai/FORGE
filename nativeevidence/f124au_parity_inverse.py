"""F124-AU learned source-blind sparse Boolean inverse from noisy public support.

Each input bit is predicted from a learned XOR of <=degree output bits and
an optional complement. No named operator, family, generator, true inverse
or graph label is a model input. Public FIT first 20, public CHECK last 4.
The task-specific learned parameters are explicitly EXTRA to the unchanged
7 active and 9 retained Yggdrasil cognitive cells.
"""
from __future__ import annotations
from itertools import combinations
import f124aj_example_operator_learner as public
import f124ag_transition_models as ag
import f124q_fresh_source as q

DEGREES=(2,3)
CHECK_LIMITS=(48,56)
FIT=20
def need(ok,name):q.need(ok,"F124AU_PARITY_"+name)
def bitsmask(samples,key,j):
    return sum((d[key][j]<<i) for i,d in enumerate(samples))
def learn(demos,degree):
    need(degree in DEGREES and len(demos)==24,
         "FROZEN_PUBLIC_FIT_AND_PARITY_DEGREE")
    fit=demos[:FIT];complete=(1<<FIT)-1
    outm=[bitsmask(fit,"output_bits",j) for j in range(16)]
    inm=[bitsmask(fit,"input_bits",j) for j in range(16)]
    terms=[]
    # Restrict learning to a frozen low-degree Boolean parity dictionary.
    for size in range(1,degree+1):
        for coords in combinations(range(16),size):
            value=0
            for j in coords:value^=outm[j]
            terms.append((coords,value))
    coeff=[];cost=0;maxerror=0
    for inp in inm:
        best=None
        for coords,pred in terms:
            wrong=(pred^inp).bit_count()
            complement=wrong>FIT-wrong
            error=min(wrong,FIT-wrong)
            candidate=(error,len(coords),coords,int(complement))
            if best is None or candidate<best:best=candidate
            cost+=1
        err,size,coords,flip=best
        maxerror=max(maxerror,err)
        coeff.append((coords,flip))
    need(len(coeff)==16 and all(len(x[0])<=degree for x in coeff),
         "SOURCE_BLIND_BITWISE_PARAMETERS")
    return tuple(coeff),{"fit_rows":FIT,"candidate_terms":len(terms),
            "feature_bit_comparisons":cost*FIT,
            "max_fit_errors_per_bit":maxerror,
            "model_coefficients_bits_lower":16*(degree*4+1),
            "fit_support_storage_bits_lower":20*32,
            "extra_model_memory_outside_7_plus_9":True,
            "source_operator_known":False}
def predict(fit,outputs):
    need(len(outputs)==16 and len(fit)==16,"PUBLIC_OUTPUT_BITS")
    ans=[]
    for coords,flip in fit:
        val=flip
        for j in coords:val^=outputs[j]
        ans.append(val)
    return ans
def calibrated(demos,fit):
    ncorrect=sum(sum(a==b for a,b in zip(predict(fit,d["output_bits"]),
                                                  d["input_bits"]))
                 for d in demos[FIT:])
    need(0<=ncorrect<=64,"CHECK_BOUND")
    return ncorrect
def decode(graph,fit,required):
    need(required in CHECK_LIMITS,"FROZEN_CHECK_CRITERION")
    normalized,demos,nonce=public.public_task(graph)
    check=calibrated(demos,fit)
    if check<required:
        return None,{"abstained":True,"public_check_correct_bits":check,
                     "inference_bit_ops":0,"operator_known":False}
    ops=0
    for edge in normalized["edges"]:
        edge["src_bits"]=predict(fit,edge["src_bits"])
        ops+=sum(len(coords) for coords,flag in fit)
    ag.frozen.prior.parent.validate_15(normalized)
    return normalized,{"abstained":False,"public_check_correct_bits":check,
                        "inference_bit_ops":ops,"operator_known":False}
def score(graph,base,delta,fit,required):
    raw,diag=decode(graph,fit,required)
    if raw is None:return -1.e9,None,diag
    val,_,_,work=ag.ygg_transition(raw,list(base),list(delta),.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "ORIGINAL_COGNITIVE_CELL_CONSERVATION")
    return val,work,diag
