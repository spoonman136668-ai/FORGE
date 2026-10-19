"""F124-BZ candidate: FIT-only learned four-variable binding, not science.

Precode frozen at f124bz-frozen-binding-hypothesis.json. NOT the original
BQ/BX model; it is a structurally distinct reversible 4-nibble variable
binder with up to 31 learned/persistent state bits, 1 zero reserved bit.
Only 40 public FIT observations choose a program. Eight CHECK observations
may only VETO. No training on graph truth, labels, old source or holdouts.
"""
from __future__ import annotations
from itertools import permutations
from pathlib import Path
import hashlib
import json

NIBBLES=4
BITS=32
FIT=40
CHECK=8
ODD=(1,3,5,7,9,11,13,15)
PERMS=tuple(permutations(range(4)))
PERM_INV={p:i for i,p in enumerate(PERMS)}
TRAIN_RESIDUALS=24*2*(8+8+8+1)*40
FIT_BIT_ERROR_MAX=6
CHECK_BIT_ERROR_MAX=2


def need(ok,reason):
    if not ok:raise ValueError("F124BZ_VARIABLE_BINDING_"+reason)


def unpack(word):
    need(type(word) is int and 0<=word<2**31 and (word>>31)==0,
         "RESERVED_32BIT_DOMAIN")
    pi=word&31
    need(pi<24,"ORIGINAL_PERMUTATION_RANGE")
    gi=[(word>>(5+3*j))&7 for j in range(3)]
    gains=tuple(ODD[x] for x in gi)+(1,)
    biases=tuple((word>>(14+4*j))&15 for j in range(4))
    gate=(word>>30)&1
    return PERMS[pi],gains,biases,gate


def pack(perm,gains,biases,gate):
    need(tuple(perm) in PERM_INV and len(gains)==4
         and len(biases)==4 and all(type(v) is int for v in gains+biases)
         and all(g in ODD for g in gains[:3]) and gains[3]==1
         and all(0<=b<16 for b in biases) and gate in (0,1),
         "PERSISTENT_LAYOUT")
    p=PERM_INV[tuple(perm)]
    for j in range(3):
        p|=ODD.index(gains[j])<<(5+3*j)
    for j in range(4):
        p|=biases[j]<<(14+4*j)
    p|=gate<<30
    need(p<2**31,"PACKED_BITS_STAY_31")
    return p


def nibbles(x):
    need(type(x) is int and 0<=x<65536,"16BIT_WORD")
    return tuple((x>>(4*j))&15 for j in range(4))


def word_of(values):
    need(len(values)==4 and all(type(v) is int and 0<=v<16 for v in values),
         "FOUR_NIBBLE_BITS")
    return sum(v<<(4*j) for j,v in enumerate(values))


def _ungate(y,gate):
    vals=list(nibbles(y))
    if gate:vals[0]^=vals[1]
    return tuple(vals)


def forward(x,word):
    perm,gains,biases,gate=unpack(word)
    inp=nibbles(x)
    out=[(gains[j]*inp[perm[j]]+biases[j])&15 for j in range(4)]
    if gate:out[0]^=out[1]
    return word_of(out)


def inverse(y,word):
    perm,gains,biases,gate=unpack(word)
    out=list(_ungate(y,gate))
    inp=[0]*4
    for j in range(4):
        inverse_gain=pow(gains[j],-1,16)
        inp[perm[j]]=(inverse_gain*(out[j]-biases[j]))&15
    return word_of(inp)


def _validate(fit,check):
    need(type(fit) in (tuple,list) and len(fit)==FIT
         and type(check) in (tuple,list) and len(check)==CHECK,
         "STRICT_40_FIT_8_CHECK")
    all_pairs=list(fit)+list(check)
    need(all(type(row) in (list,tuple) and len(row)==2
             and all(type(x) is int and 0<=x<65536 for x in row)
             for row in all_pairs),
         "ONLY_PUBLIC_UINT16")
    need(len({x for x,_ in all_pairs})==48,
         "REPEATED_FIT_CHECK_INPUT")
    return [(nibbles(x),nibbles(y)) for x,y in fit]


def _learn_slot(rows,perm,gate,slot):
    """40 FIT samples; candidate gain/bias chosen by residual histogram."""
    pool=ODD if slot<3 else (1,)
    best=None
    tied=False
    count=0
    for gain in pool:
        hist=[0]*16
        transformed=[]
        for x,y in rows:
            target=y[slot]^(y[1] if gate and slot==0 else 0)
            residual=(target-gain*x[perm[slot]])&15
            hist[residual]+=1
            transformed.append((x[perm[slot]],target))
            count+=1
        bias=min(range(16),key=lambda b:(-hist[b],b))
        errors=sum((((gain*v+bias)&15)^target).bit_count()
                   for v,target in transformed)
        candidate=(errors,gain,bias)
        if best is None or errors<best[0]:
            best=candidate
            tied=False
        elif errors==best[0] and (gain,bias)!=(best[1],best[2]):
            tied=True
    return best,tied,count


def learn(fit,check):
    rows=_validate(fit,check)
    best=None
    ties=0
    residuals=0
    contenders=0
    for gate in (0,1):
        for pi,perm in enumerate(PERMS):
            gains=[]
            biases=[]
            error=0
            ambiguous=False
            for slot in range(4):
                candidate,tied,count=_learn_slot(rows,perm,gate,slot)
                residuals+=count
                error+=candidate[0]
                gains.append(candidate[1])
                biases.append(candidate[2])
                ambiguous|=tied
            word=pack(perm,tuple(gains),tuple(biases),gate)
            key=(error,gate,pi,word)
            contenders+=1
            if best is None or error<best["error"]:
                best={"error":error,"word":word,"ambiguous":ambiguous,
                      "gate":gate,"perm":pi}
                ties=0
            elif error==best["error"]:
                ties+=1
    need(residuals==TRAIN_RESIDUALS and contenders==48,
         "FROZEN_TRAINING_WORK_BOUND")
    need(best is not None,"NO_FIT_CANDIDATE")
    check_errors=sum((forward(x,best["word"])^y).bit_count()
                     for x,y in check)
    confidence=(best["error"]<=FIT_BIT_ERROR_MAX
                and check_errors<=CHECK_BIT_ERROR_MAX
                and ties==0 and not best["ambiguous"])
    digest=hashlib.sha256(json.dumps(
        fit,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    receipt={
        "schema":"mass.f124bz.sourceblind-learned-variable-binding.v1",
        "public_FIT_SHA256":digest,
        "trained_on_public_FIT_only":True,
        "CHECK_only_veto":True,
        "fit_error_bits":best["error"],
        "check_error_bits":check_errors,
        "fit_only_permutation_index":best["perm"],
        "fit_only_relation_flag":best["gate"],
        "fit_equal_loss_competing_layouts":ties,
        "fit_ambiguous_parameters":best["ambiguous"],
        "training_residual_evaluations":residuals,
        "training_permutation_gate_candidates":contenders,
        "stored_state_bits_max":BITS,
        "reserved_bit_zero":True,
        "source_label_or_private_truth_used":False,
        "science_accepted":False,
        "protected_firstuse":False,
        "confidence":confidence
    }
    return (best["word"] if confidence else None),receipt


if __name__=="__main__":
    raise SystemExit("F124BZ_NO_REGISTERED_OR_PROTECTED_FIRSTUSE")
