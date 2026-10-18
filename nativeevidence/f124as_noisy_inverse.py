"""F124-AS source-blind robust residual/syndrome inverse learning.

Parameters inferred strictly from 20 public FIT examples. Last 4 CHECK
observations only calibrate inference and cannot train weights. Neither
source operators, graph labels nor hidden inverse are supplied to the model.
16-cell original Ygg scorer unchanged; entire task model lives in additional
transient memory (disclosed; not a valid 16-cell parity comparison).
"""
from __future__ import annotations
import random,math
import f124am_example_affine_learner as gf
import f124aj_example_operator_learner as public
import f124ag_transition_models as ag
import f124q_fresh_source as q

MODES=("robust_affine_syndrome","robust_pair_interaction_residual")
ERROR_BUDGET=(1,3)
MIN_CHECK=(48,56)
FIT=20
CHECK=4
TRIALS=256
def need(ok,key):q.need(ok,"F124AS_LEARN_"+key)
def bitdist(a,b):return (a^b).bit_count()

def fit(demos,nonce,mode):
    need(type(demos) is list and len(demos)==FIT+CHECK and mode in MODES,
         "PUBLIC_SUPPORT_AND_FIXED_MODE")
    data=demos[:FIT]
    rng=random.Random("F124AS/PUBLIC_FIXED/"+nonce)
    choices={tuple(range(17))}
    while len(choices)<TRIALS:
        choices.add(tuple(sorted(rng.sample(range(FIT),17))))
    ranked=[]
    evaluated=0
    for selection in sorted(choices):
        coeff=gf.solve_17([data[i] for i in selection])
        evaluated+=1
        if coeff is None or gf.inverse_output(0,coeff) is None:continue
        error=sum(bitdist(gf.forward(gf.integer(d["input_bits"]),coeff),
                          gf.integer(d["output_bits"])) for d in data)
        ranked.append((error,coeff))
    ranked.sort(key=lambda t:(t[0],t[1]))
    if not ranked:
        return None,{"matrix_trials":evaluated,"valid_affine_candidates":0,
                      "best_FIT_wrong_bits":None,"transient_coefficients":0,
                      "additional_model_memory_reported":True}
    error,coeff=ranked[0]
    # Optional learned residual correction: public-output nearest neighbors
    # learn bitwise correction to decoded inverse; never uses source identity.
    corrections=[]
    for d in data:
        out=gf.integer(d["output_bits"])
        inverse=gf.inverse_output(out,coeff)
        need(inverse is not None,"VALID_INVERSE")
        corrections.append((out,inverse^gf.integer(d["input_bits"])))
    return (coeff,tuple(corrections),mode),{
        "matrix_trials":evaluated,"valid_affine_candidates":len(ranked),
        "best_FIT_wrong_bits":error,"transient_coefficients":17*16,
        "residual_training_bits":FIT*32,
        "transient_fit_rows":FIT*33,
        "additional_model_memory_reported":True}

def infer(fitted,output):
    coeff,corrections,mode=fitted
    src=gf.integer(output)
    val=gf.inverse_output(src,coeff)
    need(val is not None,"INVERSE_EXISTS")
    bit_ops=16*16
    if mode==MODES[1]:
        nearest=sorted(corrections,key=lambda row:(bitdist(row[0],src),row[0]))[:2]
        # Only correct when two nearby PUBLIC observations agree on a
        # residual feature, avoiding ungrounded novel nonlinear activation.
        if len(nearest)==2 and bitdist(nearest[0][0],src)<=4 and (
            nearest[0][1]==nearest[1][1]):
            val^=nearest[0][1]
        bit_ops+=len(corrections)*16
    return [(val>>i)&1 for i in range(16)],bit_ops

def public_fit(graph,mode):
    raw,demos,nonce=public.public_task(graph)
    fitted,info=fit(demos,nonce,mode)
    return fitted,info,demos

def normalize(graph,fitted,fitinfo,error_budget,min_check):
    need(error_budget in ERROR_BUDGET and min_check in MIN_CHECK,
         "FROZEN_TRAIN_OPTIONS")
    raw,demos,nonce=public.public_task(graph)
    if fitted is None:
        return None,{"abstained":True,"check_correct_bits":0,
                     "fit_wrong_bits":fitinfo["best_FIT_wrong_bits"],
                     "model_bit_ops":0,**fitinfo}
    check_correct=0;ops=0
    for d in demos[FIT:]:
        guess,n=infer(fitted,d["output_bits"]);ops+=n
        check_correct+=sum(int(x==y) for x,y in zip(guess,d["input_bits"]))
    valid=fitinfo["best_FIT_wrong_bits"]<=error_budget and (
        check_correct>=min_check)
    info={"abstained":not valid,"check_correct_bits":check_correct,
          "fit_wrong_bits":fitinfo["best_FIT_wrong_bits"],
          "model_bit_ops":ops,"operator_catalog_known":False,
          "source_oracle_used":False,**fitinfo}
    if not valid:return None,info
    for e in raw["edges"]:
        e["src_bits"],n=infer(fitted,e["src_bits"]);ops+=n
    info["model_bit_ops"]=ops
    ag.frozen.prior.parent.validate_15(raw)
    return raw,info

def ygg(graph,base,delta,fitted,fitinfo,error_budget,min_check):
    raw,meta=normalize(graph,fitted,fitinfo,error_budget,min_check)
    if raw is None:return -1.e9,None,meta
    value,_,_,work=ag.ygg_transition(raw,list(base),list(delta),.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "UNCHANGED_ORIGINAL_SEVEN_PLUS_NINE")
    return value,work,meta

def select(cases,base,delta):
    need(len(cases)==48,"FROZEN_48_TRAIN_PAIRS")
    results=[]
    # Crucially FIT once per task; paired graph labels never influence
    # fitted parameters, only allowed TRAIN-only selection counts.
    fits={mode:[] for mode in MODES}
    for mode in MODES:
        for seed,vec,fam,op,nonce,p,n in cases:
            trained,info,_=public_fit(p,mode)
            fits[mode].append((trained,info))
    for mode in MODES:
        for budget in ERROR_BUDGET:
            for correct in MIN_CHECK:
                paired=fp=fn=abstain=ops=0
                sample=None;max_coeff=0
                for (seed,vec,fam,op,nonce,p,n),(trained,info) in zip(cases,fits[mode]):
                    va,wa,ma=ygg(p,base,delta,trained,info,budget,correct)
                    vb,wb,mb=ygg(n,base,delta,trained,info,budget,correct)
                    paired+=int(va>=0 and vb<0)
                    fp+=int(vb>=0)
                    fn+=int(va<0)
                    abstain+=int(ma["abstained"])+int(mb["abstained"])
                    ops+=ma["model_bit_ops"]+mb["model_bit_ops"]
                    max_coeff=max(max_coeff,info["transient_coefficients"])
                    if wa is not None:
                        need(wa["max_active"]<=7 and wa["max_retained"]<=9,
                             "ORIGINAL_SEVEN_NINE")
                results.append({"mode":mode,"error_budget":budget,
                    "minimum_check_correct":correct,"paired":paired,"FP":fp,"FN":fn,
                    "abstained_graphs":abstain,"model_bit_ops":ops,
                    "max_transient_coefficients_bits":max_coeff})
    need(len(results)==8,"FROZEN_GRID_EIGHT")
    zero=[r for r in results if r["FP"]==0]
    chosen=min(zero or results,key=lambda r:(-r["paired"],r["FN"],
         r["model_bit_ops"],r["mode"],r["error_budget"],r["minimum_check_correct"]))
    return chosen,results
