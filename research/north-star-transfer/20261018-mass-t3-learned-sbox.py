"""T3 Mass Research: 8-byte universally representable 4-bit S-box learner.

A public-only trainable finite nonlinear permutation. The 8-byte packed
weights encode all 16! possible bijective nibble substitutions (64 bits);
T1's fixed 32-bit two-shear class could not. Shared three-round composition
and inversion are generic, not specialized to a hidden operator family.
This kernel does NOT train against a registered real/held source.
"""
from __future__ import annotations
import math
def need(ok,key):
    if not ok:raise ValueError("MASS_T3_"+key)
def unpack(packed):
    need(type(packed) is bytes and len(packed)==8,"EIGHT_BYTES_EXACT")
    p=tuple((packed[i//2]>>(4*(i%2)))&15 for i in range(16))
    need(tuple(sorted(p))==tuple(range(16)),"TRUE_PERMUTATION_NOT_REPEATED_LUT")
    return p
def pack(p):
    need(len(p)==16 and sorted(p)==list(range(16)),"TRUE_PERMUTATION")
    return bytes((p[2*i]|(p[2*i+1]<<4) for i in range(8)))
def rot(x,k):return ((x<<k)|(x>>(16-k)))&65535
def apply_sbox(x,p):
    return sum(p[(x>>(4*n))&15]<<(4*n) for n in range(4))
def forward(value,weights):
    need(type(value) is int and 0<=value<65536,"16BIT_INPUT")
    p=unpack(weights)
    v=value
    for _ in range(3):
        v=rot(apply_sbox(v,p),3)
    return v
def inverse(value,weights):
    need(type(value) is int and 0<=value<65536,"16BIT_INPUT")
    p=unpack(weights)
    inv=[0]*16
    for i,v in enumerate(p):inv[v]=i
    v=value
    for _ in range(3):
        v=apply_sbox(rot(v,13),inv)
    return v
def score(pairs,perm):
    packed=pack(perm)
    errors=0;work=0
    for x,y in pairs:
        need(type(x) is int and type(y) is int
             and 0<=x<65536 and 0<=y<65536,"PUBLIC_NO_ORACLE")
        errors+=(forward(x,packed)^y).bit_count()
        work+=1
    return errors,work
def fit_public(FIT,CHECK):
    need(len(FIT)==40 and len(CHECK)==8,
         "EXACT_FROZEN_48_PUBLIC_RESPONSE_SPLIT")
    current=list(range(16))
    best,work=score(FIT,current)
    total=work
    proposals=0
    for _ in range(2):
        for i in range(15):
            for j in range(i+1,16):
                candidate=current[:]
                candidate[i],candidate[j]=candidate[j],candidate[i]
                err,ops=score(FIT,candidate)
                proposals+=1;total+=ops
                if err<best:
                    best=err;current=candidate
    checked,ops=score(CHECK,current);total+=ops
    return pack(current),{"FIT_bit_errors":best,
         "CHECK_bit_errors":checked,
         "FIT_permutation_swaps_evaluated":proposals,
         "sourceblind_forward_evaluations":total,
         "weights_bytes":8,"model_parameter_bits":64,
         "model_family_is_universal_4bit_bijection":True,
         "trained_from_private_truth":False,
         "meta_train_amortization_measured":False,
         "complete_graph_scoring_measured":False,
         "eligible_equal_full_resource":False}
def selftest():
    # Controlled algebraic unit test, not a new prospective source cohort.
    target=pack((3,8,11,2,6,1,14,0,10,15,9,13,4,12,5,7))
    for x in range(0,65536,101):
        need(inverse(forward(x,target),target)==x,
             "GENUINE_THREE_ROUND_INVERTIBLE_COMPOSITION")
    fit=[((i*4009+71)&65535,0) for i in range(40)]
    check=[((i*6221+103)&65535,0) for i in range(8)]
    fit=[(x,forward(x,target)) for x,_ in fit]
    check=[(x,forward(x,target)) for x,_ in check]
    model,info=fit_public(fit,check)
    need(len(model)==8 and info["FIT_permutation_swaps_evaluated"]==240
         and info["sourceblind_forward_evaluations"]==9648,
         "PRECOMMITTED_PUBLIC_FIT_COST")
    need(all(inverse(forward(x,model),model)==x for x in range(0,65536,997)),
         "FITTED_PERMUTATION_INVERTIBLE")
    print("MASS_T3_TRUE_BIJECTION_REPRESENTATION=PASS")
    print("MASS_T3_FIT_PROPOSALS=240")
    print("MASS_T3_TRAINABLE_PARAMETER_BYTES=8")
    print("MASS_T3_OOD_TRANSFER_ESTABLISHED=false")
    print("MASS_T3_FULL_RESOURCE_PARITY=false")
    print("MASS_T3_REGISTERED_COHORTS_USED=0")
if __name__=="__main__":selftest()
