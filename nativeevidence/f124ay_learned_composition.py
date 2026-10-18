"""F124-AY two source-blind learned, nonlinear inverse representations.

One architecture is a preregistered 8-bit parametric two-round Feistel
composition: an explicit structure-matched inductive bias (NOT universal
nonlinear learning). The other learns two nonparametric round lookup tables.
Only 40 PUBLIC input/output training observations are seen. Neither model
imports the evaluator/source or sees operator names, keys, graph labels or
oracle inverses. All model memory is additional to original 7+9 cells.
"""
from __future__ import annotations
from collections import Counter,defaultdict
import math
import f124aj_example_operator_learner as public
import f124ag_transition_models as ag
import f124q_fresh_source as q

MODES=("learned_two_round_keyed","learned_public_round_table")
TOTAL=48
FIT=40
CHECK=8
CHECK_MINIMUM=96
MASK=255

def need(ok,tag):q.need(ok,"F124AY_ROUND_COMPOSITION_"+tag)

def int16(bits):
    need(type(bits) is list and len(bits)==16 and
         all(type(b) is int and b in (0,1) for b in bits),"VALID_PUBLIC_16BITS")
    return sum(b<<i for i,b in enumerate(bits))

def bits16(value):
    return [(value>>i)&1 for i in range(16)]

def mix_round(value,initial,round_idx):
    """Fixed public architecture; unknown 8-bit parameter learned from FIT."""
    k=(initial+29*round_idx)&MASK
    return ((value*k)^((value<<3)&MASK)^(value>>2)^((value*value)&MASK)^k)&MASK

def forward_bits(input_bits,key):
    val=int16(input_bits)
    left=(val>>8)&MASK
    right=val&MASK
    for r in (0,1):
        left,right=right,left^mix_round(right,key,r)
    return bits16((left<<8)|right)

def decode_bits(output_bits,key):
    value=int16(output_bits)
    left=(value>>8)&MASK
    right=value&MASK
    for r in (1,0):
        left,right=right^mix_round(left,key,r),left
    return bits16((left<<8)|right)

def table_votes(public_fit):
    tables=[defaultdict(Counter),defaultdict(Counter)]
    for d in public_fit:
        x=int16(d["input_bits"])
        y=int16(d["output_bits"])
        xl,xr=(x>>8)&MASK,x&MASK
        yl,yr=(y>>8)&MASK,y&MASK
        tables[0][xr][xl^yl]+=1
        tables[1][yl][xr^yr]+=1
    return [{k:min(c, key=lambda v:(-c[v],v)) for k,c in t.items()}
            for t in tables]

def table_lookup(table,value):
    if value in table:return table[value]
    # A public-neighbor structural fallback, not memorized source truth.
    closest=min(table,key=lambda v:((v^value).bit_count(),v))
    return table[closest]

def train(demos,mode):
    need(mode in MODES and type(demos) is list and len(demos)==TOTAL,
         "EXACT_FROZEN_48_PUBLIC_RESPONSES")
    for d in demos:
        int16(d["input_bits"]);int16(d["output_bits"])
    fit=demos[:FIT]
    if mode=="learned_two_round_keyed":
        estimates=[]
        for key in range(256):
            mismatch=sum((int16(forward_bits(d["input_bits"],key))^
                          int16(d["output_bits"])).bit_count() for d in fit)
            estimates.append((mismatch,key))
        wrong,key=min(estimates)
        return {"mode":mode,"learned_key":key,
                "public_FIT_bit_errors":wrong,
                "training_round_evaluations":FIT*256*2,
                "parameters_bits_lower":8,
                "public_fit_support_bits_lower":FIT*32,
                "structural_source_family_bias":True,
                "operator_token_used":False,"source_key_used":False}
    t0,t1=table_votes(fit)
    need(len(t0)>0 and len(t1)>0,"NONEMPTY_TWO_LEARNED_ROUND_TABLES")
    return {"mode":mode,"table0":t0,"table1":t1,
            "public_FIT_bit_errors":None,
            "training_round_evaluations":FIT*2,
            "parameters_bits_lower":(len(t0)+len(t1))*16,
            "public_fit_support_bits_lower":FIT*32,
            "structural_source_family_bias":True,
            "operator_token_used":False,"source_key_used":False}

def predict(model,output):
    need(model["mode"] in MODES,"ONLY_REGISTERED_NONLINEAR_MODEL")
    if model["mode"]=="learned_two_round_keyed":
        return decode_bits(output,model["learned_key"])
    value=int16(output)
    yl,yr=(value>>8)&MASK,value&MASK
    xr=yr^table_lookup(model["table1"],yl)
    xl=yl^table_lookup(model["table0"],xr)
    return bits16((xl<<8)|xr)

def public_check(model,demos):
    need(type(demos) is list and len(demos)==TOTAL,
         "EXACT_8_HELD_PUBLIC_CHECK")
    val=sum(sum(int(a==b) for a,b in zip(
        predict(model,d["output_bits"]),d["input_bits"]))
        for d in demos[FIT:])
    need(0<=val<=128,"CHECK_RANGE")
    return val

def score(graph,base,delta,model,demos,checked):
    need(type(demos) is list and len(demos)==TOTAL
         and checked in range(0,129),"PUBLIC_QUERY_COST_AND_CALIBRATION")
    raw,original,nonce=public.public_task(graph)
    need(len(original)==24 and original==demos[:24],
         "GRAPH_SHARES_UNCHANGED_PUBLIC_DEMONSTRATIONS")
    if checked<CHECK_MINIMUM:
        return -1e9,None,{"abstained":True,
                          "check_correct":checked,
                          "model_extra_bits":model["parameters_bits_lower"],
                          "operator_token_used":False}
    ops=0
    for e in raw["edges"]:
        e["src_bits"]=predict(model,e["src_bits"])
        ops+=16 if model["mode"]=="learned_two_round_keyed" else 2*256
    ag.frozen.prior.parent.validate_15(raw)
    value,_,_,work=ag.ygg_transition(raw,list(base),list(delta),.1)
    need(math.isfinite(value) and work["max_active"]<=7 and
         work["max_retained"]<=9,"UNCHANGED_7_9_COGNITION_LIMIT")
    return value,work,{"abstained":False,
                       "check_correct":checked,
                       "model_extra_bits":model["parameters_bits_lower"],
                       "inference_operations_lower":ops,
                       "operator_token_used":False}
