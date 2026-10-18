"""F124-AX source-blind public-only nonlinear inverse learners.

A learned sparse quadratic Boolean inverse and a weighted-Hamming public
support baseline share exactly 40 PUBLIC FIT and 8 PUBLIC CHECK responses.
No source operator, graph truth, evaluator inverse, or cohort class enters
fit, confidence selection, graph normalization, or inference.
"""
from __future__ import annotations
import math
import f124aj_example_operator_learner as public
import f124ag_transition_models as ag
import f124q_fresh_source as q

MODES=("quadratic_sparse","weighted_hamming")
FIT=40
CHECK=8
TOTAL=48
MIN_CHECK=96
QUADRATIC_WIDTH=137 # constant + 16 output bits + 120 pairwise ANDs
MAX_FEATURES_PER_TARGET=3
PASSES=2

def need(ok,name):q.need(ok,"F124AX_NONLINEAR_"+name)
def bits(row):
    need(type(row) is list and len(row)==16 and
         all(type(x) is int and x in (0,1) for x in row),
         "PUBLIC_16BIT_RESPONSE")
    return sum(v<<i for i,v in enumerate(row))

def features(output):
    v=bits(output)
    f=[1]+[(v>>i)&1 for i in range(16)]
    for i in range(16):
        for j in range(i+1,16):
            f.append(int(bool(v&(1<<i)) and bool(v&(1<<j))))
    need(len(f)==QUADRATIC_WIDTH,"ONLY_DEGREE_TWO_PUBLIC_POLYNOMIAL")
    return f

def train(demos,mode):
    need(mode in MODES and type(demos) is list and len(demos)==TOTAL,
         "EXACT_EQUAL_PUBLIC_BUDGET")
    for d in demos:
        bits(d["input_bits"]);bits(d["output_bits"])
    fit=demos[:FIT]
    check=demos[FIT:]
    if mode=="weighted_hamming":
        return {"mode":mode,"public_FIT":tuple(
                (tuple(d["output_bits"]),tuple(d["input_bits"]))
                 for d in fit),"workspace_lower_bits":FIT*32,
                "extra_model_bits_lower":FIT*32,
                "fit_operations_lower":0,"operator_catalog_used":False,
                "model_family_known":False}
    xs=[features(d["output_bits"]) for d in fit]
    model=[]
    ops=0
    for bit in range(16):
        residual=[d["input_bits"][bit] for d in fit]
        indices=[]
        for _ in range(MAX_FEATURES_PER_TARGET):
            errors=sum(residual)
            best=(errors,QUADRATIC_WIDTH,None)
            for j in range(QUADRATIC_WIDTH):
                if j in indices:continue
                remaining=sum(residual[k]^xs[k][j] for k in range(FIT))
                ops+=FIT
                item=(remaining,j,j)
                if item<best:best=item
            if best[2] is None or best[0]>=errors:break
            indices.append(best[2])
            residual=[residual[k]^xs[k][best[2]] for k in range(FIT)]
        model.append(tuple(indices))
    need(len(model)==16 and all(len(x)<=3 for x in model),
         "BOUNDED_SPARSITY")
    return {"mode":mode,"model":tuple(model),
            "extra_model_bits_lower":16*3*8,
            "workspace_lower_bits":FIT*QUADRATIC_WIDTH,
            "fit_operations_lower":ops,
            "operator_catalog_used":False,"model_family_known":False}

def predict(model,output):
    need(model["mode"] in MODES,"ORIGINAL_FIXED_MODEL_FAMILY")
    source_bits=bits(output)
    if model["mode"]=="quadratic_sparse":
        feat=features(output)
        return [sum(feat[j] for j in indices)%2
                for indices in model["model"]]
    ordered=sorted(
        (sum(a!=b for a,b in zip(output,public_output)),index,public_input)
        for index,(public_output,public_input) in
        enumerate(model["public_FIT"]))
    chosen=ordered[:3]
    # Support patterns and sorted public-support identity are the only inputs.
    return [int(sum(int(row[2][k]) for row in chosen)>=2)
            for k in range(16)]

def public_check(model,demos):
    need(len(demos)==TOTAL,"EXACT_CHECK_SAMPLES")
    return sum(sum(int(a==b) for a,b in zip(
        predict(model,d["output_bits"]),d["input_bits"]))
        for d in demos[FIT:])

def score(graph,base,delta,model,demos,check_correct):
    need(len(demos)==TOTAL and check_correct in range(0,129)
         and model["mode"] in MODES,
         "NO_ORACLE_GRAPH_RECONSTRUCTION")
    raw,public_original,nonce=public.public_task(graph)
    need(len(public_original)==24 and public_original==demos[:24],
         "PUBLIC_GRAPH_MATCHED_QUERY_BUDGET")
    admitted=check_correct>=MIN_CHECK
    if not admitted:
        return -1e9,None,{"abstained":True,
                          "source_class_known":False,
                          "check_correct_bits":check_correct,
                          "extra_model_bits_lower":model["extra_model_bits_lower"]}
    op_count=0
    for e in raw["edges"]:
        e["src_bits"]=predict(model,e["src_bits"])
        op_count+=QUADRATIC_WIDTH*16 if model["mode"]=="quadratic_sparse" else FIT*16
    ag.frozen.prior.parent.validate_15(raw)
    value,_,_,work=ag.ygg_transition(raw,list(base),list(delta),.1)
    need(math.isfinite(value) and work["max_active"]<=7
         and work["max_retained"]<=9,"ORIGINAL_SEVEN_PLUS_NINE")
    return value,work,{"abstained":False,
                       "source_class_known":False,
                       "check_correct_bits":check_correct,
                       "inference_operations_lower":op_count,
                       "extra_model_bits_lower":model["extra_model_bits_lower"]}
