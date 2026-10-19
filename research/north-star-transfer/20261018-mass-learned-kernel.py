"""Mass Research T1: source-blind compact trainable invertible composition.

Two 8-bit nonlinear triangular shears; no special-case operator names,
no source oracle, private case labels, hidden family or source generator.
This is an engineering kernel, not OOD success or equal-cost acceptance.
"""
from __future__ import annotations

def need(ok,key):
    if not ok:raise ValueError("MASS_TRANSFER_"+key)
def r8(x,n):
    return ((x<<n)|(x>>(8-n)))&255
def shear(x,p,q):
    return (r8(x,1)&p)^((r8(x,3)&r8(x,5))&q)
def forward(value,masks):
    need(type(value) is int and 0<=value<65536 and
         type(masks) is bytes and len(masks)==4,
         "PUBLIC_16BIT_AND_4_BYTE_MODEL")
    a=value&255;b=(value>>8)&255
    p,q,r,s=masks
    b^=shear(a,p,q)
    a^=shear(b,r,s)
    return a|(b<<8)
def inverse(value,masks):
    need(type(value) is int and 0<=value<65536 and
         type(masks) is bytes and len(masks)==4,
         "PUBLIC_16BIT_AND_4_BYTE_MODEL")
    a=value&255;b=(value>>8)&255
    p,q,r,s=masks
    a^=shear(b,r,s)
    b^=shear(a,p,q)
    return a|(b<<8)
def errors(public,masks):
    need(type(public) in (tuple,list) and 1<=len(public)<=48,
         "PUBLIC_ONLY_SAMPLE_BOUND")
    score=0
    for x,y in public:
        need(type(x) is int and type(y) is int and
             0<=x<65536 and 0<=y<65536,"NO_TRUE_SOURCE_LABELS")
        score+=(forward(x,masks)^y).bit_count()
    return score
def fit_public(public_fit,public_check,init=bytes(4)):
    """Fixed two-pass coordinate search, no diagnostic/holdout retuning."""
    need(len(public_fit)==40 and len(public_check)==8 and len(init)==4,
         "EXACT_40_FIT_8_CHECK")
    model=bytearray(init)
    work=0
    current=errors(public_fit,bytes(model))
    work+=40
    for _ in range(2):
        for pos in range(4):
            for bit in range(8):
                alt=bytearray(model)
                alt[pos]^=1<<bit
                scored=errors(public_fit,bytes(alt))
                work+=40
                if scored<current:
                    model=alt;current=scored
    masks=bytes(model)
    checked=errors(public_check,masks)
    work+=8
    return masks,{"public_FIT_bit_errors":current,
                  "public_CHECK_bit_errors":checked,
                  "public_forward_evaluations":work,
                  "parameter_bits":32,
                  "complete_task_memory_qualified":False,
                  "full_train_amortized_compute_qualified":False,
                  "sourceblind_nonlinear_coupling":True,
                  "independent_OOD_result":False}
def learned_prior(training_tasks):
    """Train a shared compact mask initializer across public TRAIN tasks only."""
    need(type(training_tasks) in (list,tuple) and
         1<=len(training_tasks)<=192,"INDEPENDENT_TRAIN_TASK_BOUND")
    bit_votes=[0]*32
    compute=0
    for fit,check in training_tasks:
        masks,receipt=fit_public(fit,check)
        compute+=receipt["public_forward_evaluations"]
        for i in range(32):
            bit_votes[i]+=(masks[i//8]>>(i%8))&1
    out=bytearray(4)
    for i,v in enumerate(bit_votes):
        if v*2>len(training_tasks):
            out[i//8]|=1<<(i%8)
    return bytes(out),{"public_training_task_count":len(training_tasks),
                      "training_forward_evaluations":compute,
                      "training_temporary_memory_not_qualified":True}
def selftest():
    ref=bytes((0x35,0x9c,0x6a,0xc3))
    # Synthetic compositional bijection proof; NOT unseen-family evaluation.
    for x in range(0,65536,257):
        need(inverse(forward(x,ref),ref)==x,"COMPOSED_INVERTIBLE")
    fit=[((i*4009+71)&65535,0) for i in range(40)]
    check=[((i*6221+103)&65535,0) for i in range(8)]
    fit=[(x,forward(x,ref)) for x,_ in fit]
    check=[(x,forward(x,ref)) for x,_ in check]
    w,r=fit_public(fit,check)
    need(len(w)==4 and r["public_forward_evaluations"]==2608
         and r["parameter_bits"]==32 and r["independent_OOD_result"] is False,
         "LEARNABLE_PUBLIC_FIT_BOUND")
    print("MASS_T1_LEARNED_INVERTIBLE_COMPOSITION_SELFTEST=PASS")
    print("MASS_T1_MODEL_PARAMETER_BITS=32")
    print("MASS_T1_TOTAL_RUNTIME_RESOURCE_ACCEPTANCE=false")
    print("MASS_T1_NEW_TRAIN_OR_HOLDOUT_CONSUMED=false")
if __name__=="__main__":selftest()
