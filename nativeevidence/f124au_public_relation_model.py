"""F124-AU learned operator-agnostic public relationship representations.

Shared representation weights are learned ONLY from source-blind public FIT
input/output pairs. Each new task adapts via its 20 public FIT examples,
calibrates acceptance on its 4 public CHECK examples, then predicts edges.
No encoded operator name, true inverse, evaluator truth, graph label or
source-only reconstruction is a learner input. Original 7+9 scorer unchanged.

Additional model weights and examples are *not* part of original 16 cells.
"""
from __future__ import annotations
import math
import f124aj_example_operator_learner as public
import f124ag_transition_models as ag
import f124q_fresh_source as contract

MODES=("learned_public_kernel_metric","learned_context_attention")
WIDTHS=(8,16)
CHECK_THRESHOLDS=(48,56)
FIT=20
CHECK=4
EPOCHS=2

def need(valid,key):
    contract.need(valid,"F124AU_LEARNED_"+key)

def bipolar(bits):
    need(len(bits)==16 and all(type(v) is int and v in (0,1)
            for v in bits),"PUBLIC_16_BITS_ONLY")
    return [2.0*v-1.0 for v in bits]

def projection(bits, W):
    x=bipolar(bits)
    return [math.tanh(sum(row[j]*x[j] for j in range(16)))
            for row in W]

def decode(h,D):
    return [math.tanh(sum(a*b for a,b in zip(row,h))) for row in D]

def initialize(mode,width):
    need(mode in MODES and width in WIDTHS,"FROZEN_MODE_WIDTH")
    offset=1+MODES.index(mode)
    W=[[(((i+5)*(j+7)*(offset+2))%31-15)/160.0
       for j in range(16)] for i in range(width)]
    D=[[(((k+3)*(i+11)*(offset+1))%37-18)/160.0
       for i in range(width)] for k in range(16)]
    return W,D

def train_shared(tasks, mode, width):
    """Two frozen supervised epochs over 20 PUBLIC FIT rows/task only."""
    need(isinstance(tasks,(list,tuple)) and len(tasks)==48,
         "EXACT_48_SOURCE_NEW_PUBLIC_TASKS")
    W,D=initialize(mode,width)
    for demonstrations in tasks:
        need(type(demonstrations) is list and len(demonstrations)==FIT+CHECK,
             "EXACT_20_FIT_4_CHECK")
        for d in demonstrations:
            bipolar(d["input_bits"]); bipolar(d["output_bits"])
    update_ops=0
    for epoch in range(EPOCHS):
        for support in tasks:
            for index,demo in enumerate(support[:FIT]):
                x=bipolar(demo["output_bits"])
                y=bipolar(demo["input_bits"])
                h=[math.tanh(sum(row[k]*x[k] for k in range(16))) for row in W]
                p=decode(h,D)
                err=[y[k]-p[k] for k in range(16)]
                if mode=="learned_context_attention":
                    # Task-local public FIT margin (without any graph truth).
                    other=bipolar(support[(index+1)%FIT]["input_bits"])
                    err=[e+0.1*(y[k]-other[k]) for k,e in enumerate(err)]
                previous=[row[:] for row in D]
                lr=.006
                for k in range(16):
                    for j in range(width):
                        D[k][j]=max(-2.,min(2.,D[k][j]+lr*err[k]*h[j]))
                for j in range(width):
                    grad=sum(previous[k][j]*err[k] for k in range(16))/16.
                    for k in range(16):
                        W[j][k]=max(-2.,min(2.,W[j][k]+lr*grad*x[k]))
                update_ops+=64*width
    return {"mode":mode,"width":width,"W":tuple(tuple(x) for x in W),
            "D":tuple(tuple(x) for x in D),"shared_train_tasks":48,
            "public_fit_per_task":FIT,"public_check_per_task":CHECK,
            "supervised_update_ops":update_ops,
            "shared_parameters":32*width,
            "shared_float_bytes_lower":32*width*8,
            "source_truth_used":False,"operator_grammar_used":False}

def estimate(model,bits,fit):
    """Inference uses only raw public output bits and public FIT support."""
    need(len(fit)==FIT,"NO_ORACLE_SUPPORT")
    width=model["width"]
    q=projection(bits,model["W"])
    network=decode(q,model["D"])
    scores=[]
    for d in fit:
        support=projection(d["output_bits"],model["W"])
        distance=sum((q[j]-support[j])**2 for j in range(width))/width
        scores.append(-5.0*distance)
    biggest=max(scores)
    weights=[math.exp(max(-100.,s-biggest)) for s in scores]
    z=sum(weights)
    prototype=[sum(weights[i]*bipolar(fit[i]["input_bits"])[k]
                   for i in range(FIT))/z for k in range(16)]
    if model["mode"]=="learned_public_kernel_metric":
        return [.8*prototype[k]+.2*network[k] for k in range(16)]
    # Explicit learned projection with task-local positive/negative public
    # FIT support contrast, unlike the metric mean.
    result=[]
    for k in range(16):
        positive=[scores[i] for i,d in enumerate(fit) if d["input_bits"][k]]
        negative=[scores[i] for i,d in enumerate(fit) if not d["input_bits"][k]]
        contrast=(max(positive)-max(negative)) if positive and negative else 0.
        result.append(.50*prototype[k]+.35*network[k]+.15*contrast)
    return result

def normalize(graph,model,min_check):
    need(min_check in CHECK_THRESHOLDS,"FROZEN_PUBLIC_CHECK_GATE")
    raw,demos,nonce=public.public_task(graph)
    need(len(demos)==FIT+CHECK and model["width"] in WIDTHS
         and model["mode"] in MODES
         and len(model["W"])==model["width"]
         and len(model["D"])==16,"PUBLIC_MODEL_SHAPE")
    fit=demos[:FIT]
    correct=0
    for d in demos[FIT:]:
        prediction=estimate(model,d["output_bits"],fit)
        correct+=sum(int(int(v>=0)==truth)
                     for v,truth in zip(prediction,d["input_bits"]))
    accepted=correct>=min_check
    inferred=CHECK
    if accepted:
        for edge in raw["edges"]:
            prediction=estimate(model,edge["src_bits"],fit)
            edge["src_bits"]=[int(v>=0) for v in prediction]
            inferred+=1
        ag.frozen.prior.parent.validate_15(raw)
    return raw if accepted else None,{
        "public_check_correct_bits":correct,"abstained":not accepted,
        "inference_queries":inferred,
        "estimated_model_mul_add_lower":inferred*(FIT+2)*width*16,
        "shared_float_bytes_lower":model["shared_float_bytes_lower"],
        "task_FIT_bits_lower":FIT*32,
        "feature_activation_float_slots_lower":(FIT+1)*model["width"],
        "extra_memory_outside_original_cognitive_cells":True,
        "original_cognitive_cells":16,
        "source_truth_used":False,"operator_grammar_used":False
    }

def score(graph,base,delta,model,min_check):
    raw,obs=normalize(graph,model,min_check)
    if raw is None:
        return -1e9,None,obs
    val,raw_score,ratio,work=ag.ygg_transition(
        raw,list(base),list(delta),.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "ORIGINAL_COGNITIVE_CAPACITY")
    return val,work,obs
