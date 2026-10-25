"""F124CO bounded source-PUBLIC-only structure induction.

Searches carrier and parity-gate wiring, both modular residual coefficients
and bias from 40 FIT examples. No original source module, parameter, scorer or
private world enters this learner. Grammar is SOURCE-INFORMED and conventional.
"""
from __future__ import annotations
import hashlib
import json
from itertools import combinations

ODDS_AND_ZERO=(0,1,3,5,7,9,11,13,15)
SCHEMA="forge.itd02.f124co.fitted_structural_composition_dev.v1"
CANDIDATE_LAYOUTS=1944
CANDIDATE_FULL_WORDS=31104

def require(ok,label):
    if not ok: raise ValueError("F124CO_"+label)

def public4(value):
    require(type(value) is int and 0<=value<65536,"PUBLIC_16BIT_VALUE")
    return tuple((value>>(4*i))&15 for i in range(4))

def public_fit(items):
    require(type(items) in (tuple,list) and len(items)==40,"FIT_40")
    require(all(type(row) in (tuple,list) and len(row)==2 and
                type(row[0]) is int and 0<=row[0]<65536 and
                type(row[1]) is int and 0<=row[1]<65536 for row in items),
            "PUBLIC_PAIR_SHAPE")
    require(len(set(row[0] for row in items))==40,"PUBLIC_INPUT_REUSE")
    return tuple((public4(x),y&15) for x,y in items)

def wiring():
    for left,right in combinations(range(4),2):
        rem=tuple(k for k in range(4) if k!=left and k!=right)
        for gate in rem:
            for direction in (0,1):
                for w0 in ODDS_AND_ZERO:
                    for w1 in ODDS_AND_ZERO:
                        yield left,right,gate,direction,w0,w1,rem

def result_from_public(model,observation):
    left,right,gate,direction,w0,w1,bias=model
    v=public4(observation)
    rem=tuple(i for i in range(4) if i not in (left,right))
    carrier=v[left] if (v[gate]&1)==direction else v[right]
    return (carrier+w0*v[rem[0]]+w1*v[rem[1]]+bias)&15

def train(fit):
    samples=public_fit(fit)
    best=None
    row_work=0
    layouts=0
    for left,right,gate,direction,w0,w1,rem in wiring():
        hist=[0]*16
        layouts+=1
        for vals,target in samples:
            carrier=(vals[left] if (vals[gate]&1)==direction
                     else vals[right])
            residual=(target-carrier-w0*vals[rem[0]]-w1*vals[rem[1]])&15
            hist[residual]+=1
            row_work+=1
        bias=min(range(16),key=lambda k:(-hist[k],k))
        candidate=(40-hist[bias],left,right,gate,direction,w0,w1,bias)
        if best is None or candidate<best:best=candidate
    require(layouts==CANDIDATE_LAYOUTS and row_work==layouts*40,
            "EXHAUSTIVE_STRUCTURE_BUDGET")
    return tuple(best[1:]),{
        "FIT_nibble_mismatches":best[0],
        "FIT_40_public_pairs":True,
        "source_informed_hypothesis_class":True,
        "layout_candidates":layouts,"residual_row_evaluations":row_work}

def conventional_enumeration(fit):
    """Independent brute-force fully trained SAME-CLASS strong conventional.

    Unlike the candidate's histogram fitting, directly scores all 16 biases,
    all 1,944 symbolic layouts on the FIT pairs; never sees heldout outcomes.
    """
    samples=public_fit(fit)
    best=None
    nwords=0
    evaluations=0
    for left,right,gate,direction,w0,w1,rem in wiring():
        for bias in range(16):
            nwords+=1
            errors=0
            for vals,target in samples:
                carrier=vals[left] if (vals[gate]&1)==direction else vals[right]
                estimate=(carrier+w0*vals[rem[0]]+w1*vals[rem[1]]+bias)&15
                errors+=(estimate!=target)
                evaluations+=1
            option=(errors,left,right,gate,direction,w0,w1,bias)
            if best is None or option<best:best=option
    require(nwords==CANDIDATE_FULL_WORDS and
            evaluations==CANDIDATE_FULL_WORDS*40,
            "CONVENTIONAL_FULL_MODEL_SEARCH")
    return tuple(best[1:]),{"FIT_nibble_mismatches":best[0],
                             "full_candidate_words":nwords,
                             "FIT_row_evaluations":evaluations}

def valid_structure(model):
    if type(model) is not tuple or len(model)!=7:return False
    left,right,gate,direction,w0,w1,bias=model
    return (all(type(x) is int for x in model) and
            0<=left<right<4 and gate in range(4) and
            gate not in (left,right) and direction in (0,1) and
            w0 in ODDS_AND_ZERO and w1 in ODDS_AND_ZERO and
            0<=bias<16)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      allow_nan=False,ensure_ascii=True).encode("ascii")

def checkpoint(model):
    require(valid_structure(model),"STRUCTURE_DOMAIN")
    body={"schema":SCHEMA,"wiring_and_coefficients":list(model),
          "source_created":False,"protected_firstuse":False,
          "science_accepted":False}
    return canonical({"body":body,
                      "sha256":hashlib.sha256(canonical(body)).hexdigest()})

def restore(data):
    require(type(data) is bytes and 0<len(data)<2048,"CHECKPOINT_BOUND")
    def reject_duplicates(pairs):
        out={}
        for k,v in pairs:
            require(k not in out,"DUPLICATE_CHECKPOINT_FIELD")
            out[k]=v
        return out
    try:
        doc=json.loads(data.decode("ascii"),object_pairs_hook=reject_duplicates)
    except (UnicodeError,ValueError,TypeError) as error:
        raise ValueError("F124CO_CHECKPOINT_JSON") from error
    require(type(doc) is dict and set(doc)=={"body","sha256"}
            and data==canonical(doc),"CHECKPOINT_CANONICAL")
    body=doc["body"]
    require(type(body) is dict and set(body)=={"schema","wiring_and_coefficients",
         "source_created","protected_firstuse","science_accepted"} and
         body["schema"]==SCHEMA and body["source_created"] is False and
         body["protected_firstuse"] is False and body["science_accepted"] is False,
            "CHECKPOINT_NO_SOURCE_AUTHORITY")
    require(type(doc["sha256"]) is str and
            doc["sha256"]==hashlib.sha256(canonical(body)).hexdigest(),
            "CHECKPOINT_INTEGRITY")
    params=body["wiring_and_coefficients"]
    require(type(params) is list and
            all(type(v) is int for v in params),"CHECKPOINT_MODEL_SHAPE")
    params=tuple(params)
    checkpoint(params)
    return params
