"""FORGE T1 transfer-utility learning kernel, non-authorizing.

All inputs to this pure kernel are caller-provided mock TRAIN observations.
It does not convert them into authenticated optimizerbridge.LaneEvidence.
Real source signatures, propensity audit, eligibility and randomization
are delegated to the EXISTING independent Go admission machinery.
"""
from __future__ import annotations
import math

FEATURES=4
WEIGHTS_BYTES=4
def need(ok,name):
    if not ok:raise ValueError("OPT_TRANSFER_"+name)
def clipped(x):
    return min(127,max(-128,int(round(x))))
def features(item):
    # novel source transfer, independent reproduction, observed false
    # positives/harm, fully accounted compute. No gate-count feature.
    keys=("unseen_transfer","independent_replication","false_positive_harm","resource_cost")
    need(type(item) is dict and set(item)==set(keys),"EXACT_PUBLIC_FEATURE_CONTRACT")
    values=tuple(item[k] for k in keys)
    need(all(type(v) in (float,int) and math.isfinite(v) and
             0<=v<=1 for v in values),"BOUNDED_TRANSFER_ONLY_FEATURES")
    return values
def learn_train_only(rows):
    """Pure bounded supervised kernel; TRAIN rows are NOT trust-verified here."""
    need(type(rows) in (list,tuple) and 1<=len(rows)<=2048,
         "TRAIN_SAMPLES_ONLY")
    weights=[0.0]*FEATURES
    updates=0
    for _ in range(2):
        for feat,label in rows:
            x=features(feat)
            need(label in (0,1),"TRAIN_ONLY_BINARY_TRANSFER_OUTCOME")
            pred=1/(1+math.exp(-sum(w*v for w,v in zip(weights,x))))
            for i in range(FEATURES):
                # Fixed regularization and step; no held outcome tuning.
                weights[i]+=0.0625*((label-pred)*x[i]-0.01*weights[i])
                updates+=1
    packed=bytes(clipped(w*32)&255 for w in weights)
    need(len(packed)==WEIGHTS_BYTES,"SIGNED_QUANTIZED_WEIGHT_SIZE")
    return packed,{"fit_parameter_updates":updates,
                   "source_signature_verified":False,
                   "policy_admitted":False,
                   "independent_causal_selection_verified":False,
                   "scientific_improvement_established":False}

def advisory_score(packed,record):
    need(type(packed) is bytes and len(packed)==WEIGHTS_BYTES,
         "EXACT_FROZEN_MODEL")
    w=[v if v<128 else v-256 for v in packed]
    return sum(v*x for v,x in zip(w,features(record)))/32

def authorize_optimizer(*_):
    # Must call existing optimizerbridge acceptance and selection audit in
    # an independently qualified native workflow. Never synthesize authority.
    raise ValueError("OPT_TRANSFER_SIGNED_EVIDENCE_AND_SELECTION_AUDIT_REQUIRED")

def selftest():
    x={"unseen_transfer":1.0,"independent_replication":1.0,
       "false_positive_harm":0.0,"resource_cost":0.5}
    bad={"unseen_transfer":0.0,"independent_replication":0.0,
       "false_positive_harm":1.0,"resource_cost":0.9}
    p,m=learn_train_only(((x,1),(bad,0)))
    need(len(p)==4 and m["fit_parameter_updates"]==16,
         "TRAIN_ONLY_LEARNABLE_4_BYTE_SHADOW")
    need(advisory_score(p,x)>advisory_score(p,bad),
         "SHADOW_LEARNED_PUBLIC_UTILITY")
    try:authorize_optimizer()
    except ValueError:pass
    else:raise AssertionError("Optimizer authority must fail closed")
    print("OPT_T1_LEARNED_TRANSFER_UTILITY_SELFTEST=PASS")
    print("OPT_T1_SIGNED_REAL_EVIDENCE_ADMISSION=false")
    print("OPT_T1_RANDOMIZED_PROSPECTIVE_EXPERIMENT=false")
    print("OPT_T1_NO_DISPATCH_OR_PRODUCTION=true")
if __name__=="__main__":selftest()
