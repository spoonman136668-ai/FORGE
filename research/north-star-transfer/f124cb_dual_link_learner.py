"""F124-CB factorized source-blind learned dual causal-variable-binding map.

Preregistered BEFORE source/code firstuse, same 32 stored state bits as BZ,
four 4-bit variables, optional independent links out0 ^= out1 and
out2 ^= out3. Only 40 public FIT pairs train. CHECK is VETO ONLY.
Entire model objective and search schedule sourceblind; not a graph oracle.
"""
from __future__ import annotations
from itertools import permutations
import hashlib
import json

FITS=40
CHECKS=8
ODDS=(1,3,5,7,9,11,13,15)
PERMS=tuple(permutations(range(4)))
PERM_IDS={v:i for i,v in enumerate(PERMS)}
FIT_ERROR_MAX=6
CHECK_ERROR_MAX=2
PARAM_BITS=32
RESIDUAL_COUNT=6560
FIT_SCORING_COUNT=6560
STRUCTURAL_COMBINATIONS=96


def need(ok,msg):
    if not ok:raise ValueError("F124CB_SOURCEBLIND_"+msg)


def unpack(word):
    need(type(word) is int and 0<=word<2**32,"32_BIT_STATE")
    idx=word&31
    need(idx<24,"PERMUTATION_NOT_SCIENCE_VALID")
    gains=tuple(ODDS[(word>>(5+3*i))&7] for i in range(3))+(1,)
    bias=tuple((word>>(14+4*i))&15 for i in range(4))
    links=((word>>30)&1,(word>>31)&1)
    return PERMS[idx],gains,bias,links


def pack(perm,gains,bias,links):
    perm=tuple(perm)
    gains=tuple(gains)
    bias=tuple(bias)
    links=tuple(links)
    need(perm in PERM_IDS and len(gains)==4 and len(bias)==4
         and len(links)==2 and gains[3]==1
         and all(type(g) is int and g in ODDS for g in gains[:3])
         and all(type(v) is int and 0<=v<16 for v in bias)
         and all(type(g) is int and g in (0,1) for g in links),
         "32_BIT_FROZEN_BINDING_SCHEMA")
    out=PERM_IDS[perm]
    for j in range(3):out|=ODDS.index(gains[j])<<(5+3*j)
    for j in range(4):out|=bias[j]<<(14+4*j)
    out|=links[0]<<30
    out|=links[1]<<31
    need(0<=out<2**32,"NO_PERSISTENT_EXTRA_STATE")
    return out


def nibs(word):
    need(type(word) is int and 0<=word<65536,"ONLY_UINT16")
    return tuple((word>>(4*i))&15 for i in range(4))


def word(v):
    need(len(v)==4 and all(type(x) is int and 0<=x<16 for x in v),
         "FOUR_CORRECT_NIBBLES")
    return sum(x<<(4*i) for i,x in enumerate(v))


def forward(x,state):
    perm,gains,bias,links=unpack(state)
    src=nibs(x)
    out=[(gains[j]*src[perm[j]]+bias[j])&15 for j in range(4)]
    if links[0]:out[0]^=out[1]
    if links[1]:out[2]^=out[3]
    return word(out)


def inverse(y,state):
    perm,gains,bias,links=unpack(state)
    val=list(nibs(y))
    if links[0]:val[0]^=val[1]
    if links[1]:val[2]^=val[3]
    src=[0]*4
    for j in range(4):
        src[perm[j]]=(pow(gains[j],-1,16)*(val[j]-bias[j]))&15
    return word(src)


def _validate(fit,check):
    need(isinstance(fit,(list,tuple)) and len(fit)==FITS
         and isinstance(check,(list,tuple)) and len(check)==CHECKS,
         "EXACT_FIT_CHECK_SIZE")
    pairs=list(fit)+list(check)
    need(all(isinstance(pair,(list,tuple)) and len(pair)==2
             and all(type(v) is int and 0<=v<65536 for v in pair)
             for pair in pairs)
         and len({p[0] for p in pairs})==48,
         "PUBLIC_NO_DUPLICATE_UINT16_PAIR")
    return [(nibs(x),nibs(y)) for x,y in fit]


def _trained_locals(rows):
    local={}
    residual_scans=0
    bit_score_scans=0
    for slot in range(4):
        gate_values=(0,1) if slot in (0,2) else (0,)
        gains=ODDS if slot<3 else (1,)
        for input_slot in range(4):
            for gate in gate_values:
                target=[(x[input_slot],
                         y[slot]^(y[slot+1] if gate else 0))
                        for x,y in rows]
                best=None
                best_ties=0
                for gain in gains:
                    hist=[0]*16
                    for src,dst in target:
                        hist[(dst-gain*src)&15]+=1
                        residual_scans+=1
                    bias=min(range(16),key=lambda v:(-hist[v],v))
                    errors=0
                    for src,dst in target:
                        errors+=((((gain*src+bias)&15)^dst).bit_count())
                        bit_score_scans+=1
                    key=(errors,gain,bias)
                    if best is None or errors<best[0]:
                        best=key
                        best_ties=0
                    elif errors==best[0] and (gain,bias)!=(best[1],best[2]):
                        best_ties+=1
                local[slot,input_slot,gate]={
                    "errors":best[0],"gain":best[1],"bias":best[2],
                    "ambiguous":best_ties>0}
    need(residual_scans==RESIDUAL_COUNT
         and bit_score_scans==FIT_SCORING_COUNT,
         "FROZEN_6560_RESIDUAL_AND_6560_FIT_SCORING")
    return local,residual_scans,bit_score_scans


def learn(fit,check):
    rows=_validate(fit,check)
    local,residuals,scores=_trained_locals(rows)
    best=None
    tied_best=0
    for perm in PERMS:
        for g0 in (0,1):
            for g2 in (0,1):
                links=(g0,g2)
                slots=[
                    local[j,perm[j],links[0] if j==0 else
                          links[1] if j==2 else 0]
                    for j in range(4)]
                total=sum(p["errors"] for p in slots)
                params=pack(perm,
                            tuple(p["gain"] for p in slots),
                            tuple(p["bias"] for p in slots),links)
                uncertain=any(p["ambiguous"] for p in slots)
                if best is None or total<best["fit_errors"]:
                    best={"fit_errors":total,"params":params,
                          "local_ambiguous":uncertain}
                    tied_best=0
                elif total==best["fit_errors"]:
                    tied_best+=1
    need(best is not None,"MISSING_PUBLIC_LEARNER")
    check_errors=sum((forward(x,best["params"])^y).bit_count()
                     for x,y in check)
    confident=(best["fit_errors"]<=FIT_ERROR_MAX
               and check_errors<=CHECK_ERROR_MAX
               and tied_best==0
               and not best["local_ambiguous"])
    return (best["params"] if confident else None),{
        "schema":"mass.f124cb.two-learned-causal-link-FIT-only.v1",
        "public_FIT_sha256":hashlib.sha256(json.dumps(
            fit,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "FIT_bit_errors":best["fit_errors"],
        "CHECK_bit_errors":check_errors,
        "trained_FIT_only":True,"CHECK_veto_only":True,
        "source_or_graph_role_label_used":False,
        "original_scientific_case_used":False,
        "frozen_32bit_persistent_state":True,
        "trained_FIT_residuals":residuals,
        "trained_FIT_bit_scores":scores,
        "layout_assignments":STRUCTURAL_COMBINATIONS,
        "equal_best_ambiguity":tied_best,
        "local_parameter_ambiguity":best["local_ambiguous"],
        "learned_flags":unpack(best["params"])[3],
        "full_science_resource_pass":False,
        "science_accepted":False,
        "confidence":confident
    }


if __name__=="__main__":
    raise SystemExit("NO_PROSPECTIVE_SOURCE_FIRSTUSE_IN_MODEL")
