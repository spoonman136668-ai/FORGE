"""F124-AZ task-local jointly trained public-evidence affine/Feistel router.

Both original implementations are unchanged. The entire 40-PUBLIC-FIT
task demonstrations fit both components; 8 PUBLIC CHECK examples alone
select a task-wide inverse or abstain. No graph class, oracle key or label.
No graph-specific routing and no hidden cognitive cells or graph cache.
"""
from __future__ import annotations
import f124av_informative_inverse as affine
import f124ay_learned_composition as nonlinear
import f124q_fresh_source as q

MARGINS=(0,8)
TOTAL=48
FIT=40
CHECK=8
MIN_CHECK=96
AFFINE_ERROR_BUDGET=12

def need(cond,key):q.need(cond,"F124AZ_JOINT_PUBLIC_"+key)

def train(demos,nonce,margin):
    need(isinstance(demos,list) and len(demos)==TOTAL
         and type(nonce) is str and nonce and margin in MARGINS,
         "FROZEN_TASK_PUBLIC_FIT_ONLY")
    for d in demos:
        nonlinear.int16(d["input_bits"])
        nonlinear.int16(d["output_bits"])
    aff,info=affine.fit(demos,nonce)
    ca=affine.check(demos,aff)
    feistel=nonlinear.train(demos,"learned_two_round_keyed")
    cf=nonlinear.public_check(feistel,demos)
    va=bool(aff is not None and info["fit_bit_errors"] is not None
            and info["fit_bit_errors"]<=AFFINE_ERROR_BUDGET
            and ca>=MIN_CHECK)
    vf=bool(cf>=MIN_CHECK)
    if va and not vf:
        choice="affine"
    elif vf and not va:
        choice="feistel"
    elif va and vf and abs(ca-cf)>margin:
        choice="affine" if ca>cf else "feistel"
    else:
        choice="abstain"
    need(choice in ("affine","feistel","abstain"),
         "PRECOMMITTED_PUBLIC_ROUTER")
    return {"choice":choice,"affine_coefficients":aff,"affine_info":info,
            "affine_check":ca,"feistel_model":feistel,"feistel_check":cf,
            "margin":margin,"trained_both_from_same_40_FIT":True,
            "public_CHECK_shared_exactly_8":True,
            "extra_task_model_bits_lower":
                info["transient_task_coefficient_bits"]+
                feistel["parameters_bits_lower"],
            "fit_operations_lower":
                info["all_ransac_attempts"]*FIT*17+
                feistel["training_round_evaluations"],
            "model_receives_operator_token":False,
            "model_receives_oracle_inverse":False,
            "model_receives_true_graph_label":False}

def score(graph,base,delta,model,demos):
    need(len(demos)==TOTAL and model["margin"] in MARGINS
         and model["trained_both_from_same_40_FIT"]
         and model["public_CHECK_shared_exactly_8"],
         "ORIGINAL_SHARED_SUPPORT_AND_NO_ORACLE")
    choice=model["choice"]
    if choice=="abstain":
        # Even abstention must confirm graph's unchanged original public demos.
        from f124aj_example_operator_learner import public_task
        _,first,nonce=public_task(graph)
        need(first==demos[:24],"ORIGINAL_GRAPH_PUBLIC_TASK_IDENTITY")
        return -1e9,None,{"abstained":True,"selected":"abstain",
             "affine_check":model["affine_check"],
             "feistel_check":model["feistel_check"],
             "model_receives_operator_token":False}
    if choice=="affine":
        val,work,diag=affine.score(
            graph,base,delta,model["affine_coefficients"],
            model["affine_info"],model["affine_check"],
            AFFINE_ERROR_BUDGET,MIN_CHECK)
    else:
        val,work,diag=nonlinear.score(
            graph,base,delta,model["feistel_model"],
            demos,model["feistel_check"])
    need(not diag.get("source_operator_known",False)
         and not diag.get("operator_token_used",False),
         "MODEL_NEVER_SEES_ORACLE")
    return val,work,{"abstained":diag.get("abstained",False),
       "selected":choice,
       "affine_check":model["affine_check"],
       "feistel_check":model["feistel_check"],
       "model_receives_operator_token":False}
