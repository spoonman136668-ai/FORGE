"""F124-BX FIT-only learned structural third-shear gate; engineering only.

Original BQ 32-bit hypothesis, scientific thresholds and code untouched.
One extra flag is repacked from the two immutable odd-gain parity positions,
not allocated as a 33rd persistent state bit.

Only public FIT examples can select the structural flag, using a bounded
first-stage loss scan. Public CHECK remains a veto in ORIGINAL BQ.learn.
Candidate has no access to source names, relationship family, private truth,
model operator labels or graph results for selecting the flag.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ORIGINAL_PATH=HERE/"f124bq_program_learner.py"
FIT_N=40
CHECK_N=8
FLAG0=0
FLAG1=1
MAX_SCAN_EVALS=2*2*64*FIT_N
MAX_FULL_SCAN_EVALS=2*MAX_SCAN_EVALS
STORED_STATE_BITS=32


def need(ok,message):
    if not ok:
        raise ValueError("F124BX_SOURCEBLIND_"+message)


def original():
    spec=importlib.util.spec_from_file_location(
        "f124bx_exact_original_BQ",ORIGINAL_PATH)
    need(spec is not None and spec.loader is not None,
         "FROZEN_PARENT_UNAVAILABLE")
    parent=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    need(parent.STATE_BITS==32 and parent.MAX_PROGRAMS==16
         and parent.MAX_FIT_BIT_ERRORS==6
         and parent.MAX_CHECK_BIT_ERRORS==2
         and parent.ODD_GAINS==tuple(range(1,128,2)),
         "ORIGINAL_LEARNER_CONFIDENCE_DRIFT")
    return parent


def _validate_public(fit,check):
    need(type(fit) in (tuple,list) and len(fit)==FIT_N
         and type(check) in (tuple,list) and len(check)==CHECK_N,
         "FROZEN_40_FIT_AND_8_CHECK")
    for x,y in list(fit)+list(check):
        need(type(x) is int and type(y) is int
             and 0<=x<65536 and 0<=y<65536,
             "PUBLIC_16_BIT_ONLY")


def _ungate_y(y,flag):
    need(flag in (0,1) and type(y) is int and 0<=y<65536,
         "FLAG_AND_OUTPUT_DOMAIN")
    lo=y&255
    hi=y>>8
    return (lo^(hi if flag else 0))|(hi<<8)


def _gate_y(y,flag):
    return _ungate_y(y,flag)


def _public_ungate(rows,flag):
    return [(x,_ungate_y(y,flag)) for x,y in rows]


def _stage1_loss(fit_ungated):
    """Fixed 128 x 40 stage-one FIT scan, CHECK never passed in."""
    best=None
    observations=0
    checks=0
    for mode in (0,1):
        for gain in range(1,128,2):
            histogram={}
            for x,y in fit_ungated:
                lo=x&255
                hi=x>>8
                yl=y&255
                mixed=(yl-lo)&255 if mode==0 else yl^lo
                bias=(mixed-gain*hi)&255
                histogram[bias]=histogram.get(bias,0)+1
                observations+=1
            preferred=min(histogram,key=lambda b:(-histogram[b],b))
            bits=0
            for x,y in fit_ungated:
                lo=x&255
                hi=x>>8
                predicted=((lo+gain*hi+preferred)&255
                           if mode==0 else
                           lo^((gain*hi+preferred)&255))
                bits+=(predicted^(y&255)).bit_count()
                checks+=1
            result=(bits,mode,gain,preferred)
            if best is None or result<best:
                best=result
    need(observations==MAX_SCAN_EVALS and checks==MAX_SCAN_EVALS,
         "FIXED_FIT_ONLY_SEARCH_BOUND")
    return best[0],observations,checks


def encode(program,flag):
    need(type(program) in (tuple,list) and len(program)==6,
         "ORIGINAL_PARAMETER_COUNT")
    a,b,c,d,m1,m2=program
    need(all(type(v) is int for v in program)
         and a in range(1,128,2) and c in range(1,128,2)
         and 0<=b<256 and 0<=d<256
         and m1 in (0,1) and m2 in (0,1)
         and flag in (0,1),
         "PERSISTENT_32_BIT_STATE_DOMAIN")
    value=(a>>1)|(b<<6)|((c>>1)<<14)|(d<<20)|(m1<<28)|(m2<<29)|(flag<<30)
    need(value<2**31,"RESERVED_TOP_BIT_ALWAYS_ZERO")
    return value


def decode(packed):
    need(type(packed) is int and 0<=packed<2**31,
         "RESERVED_TOP_BIT_MUST_REMAIN_ZERO")
    a=2*(packed&63)+1
    b=(packed>>6)&255
    c=2*((packed>>14)&63)+1
    d=(packed>>20)&255
    m1=(packed>>28)&1
    m2=(packed>>29)&1
    flag=(packed>>30)&1
    return (a,b,c,d,m1,m2),flag


def forward(x,packed,parent):
    params,flag=decode(packed)
    return _gate_y(parent.forward(x,params),flag)


def inverse(y,packed,parent):
    params,flag=decode(packed)
    return parent.inverse(_ungate_y(y,flag),params)


def learn(fit,check,parent=None):
    _validate_public(fit,check)
    parent=original() if parent is None else parent
    fit0=_public_ungate(fit,0)
    fit1=_public_ungate(fit,1)
    score0,n0,c0=_stage1_loss(fit0)
    score1,n1,c1=_stage1_loss(fit1)
    flag=0 if score0<=score1 else 1
    chosen=fit0 if flag==0 else fit1
    original_check=_public_ungate(check,flag)
    candidate,old_receipt,plausible=parent.learn(chosen,original_check)
    fit_digest=hashlib.sha256(json.dumps(
        fit,separators=(",",":"),sort_keys=True).encode()).hexdigest()
    admitted=candidate is not None
    packed=encode(candidate,flag) if admitted else None
    all_packed=tuple(encode(p,flag) for p in plausible) if admitted else ()
    receipt={
       "schema":"mass.f124bx.fit-selected-third-shear-engineering.v1",
       "original_BQ_state_bits":parent.STATE_BITS,
       "actual_packed_state_bits":STORED_STATE_BITS,
       "reserved_top_bit_is_zero":True,
       "learned_structural_flag":flag,
       "structural_FIT_only_loss_flag0":score0,
       "structural_FIT_only_loss_flag1":score1,
       "structural_FIT_only_tie_defaults_to_legacy":True,
       "preselection_CHECK_used":False,
       "confidence_CHECK_veto_only":True,
       "original_BQ_FIT_error_bits":old_receipt["FIT_error_bits"],
       "original_BQ_CHECK_error_bits":old_receipt["CHECK_error_bits"],
       "original_BQ_unchanged_algorithm_called_once":True,
       "preselection_residual_observations":n0+n1,
       "preselection_stage_score_evaluations":c0+c1,
       "full_original_BQ_stage_residual_evaluations":
           old_receipt["stage_public_residual_evaluations"],
       "public_original_FIT_sha256":fit_digest,
       "source_family_or_label_used":False,
       "oracle_or_private_key_used":False,
       "original_BQ_model_mutated":False,
       "science_accepted":False,
       "firstuse_development_or_protected":False,
       "confidence":admitted
    }
    need(receipt["preselection_residual_observations"]==MAX_FULL_SCAN_EVALS
         and receipt["preselection_stage_score_evaluations"]==MAX_FULL_SCAN_EVALS,
         "BOUNDED_STRUCTURAL_FIT_SCAN")
    return packed,receipt,all_packed


def causal_consensus(graph,packed,plausible,parent):
    need(packed is not None and packed in plausible
         and type(graph) is dict
         and set(graph)=={"start","target","roles","edges","demos"}
         and 1<=len(plausible)<=16,
         "CAUSAL_INPUT_SHAPE_AND_CONFIDENCE")
    current=graph["start"]
    carry=None
    steps=0
    for role in graph["roles"]:
        edges=[e for e in graph["edges"]
               if e["from"]==current and e["role"]==role]
        if len(edges)!=1:
            return False,{"decision":"ABSTAIN_AMBIGUOUS_ROUTE","hops":steps}
        edge=edges[0]
        src=parent._bits(edge["src_bits"])
        preds={inverse(src,p,parent) for p in plausible}
        if len(preds)!=1:
            return False,{"decision":"ABSTAIN_AMBIGUOUS_PREDECESSOR",
                          "hops":steps}
        x=next(iter(preds))
        steps+=1
        if carry is not None and x!=carry:
            return False,{"decision":"REJECT_WRONG_PREDECESSOR","hops":steps}
        carry=parent._bits(edge["dst_bits"])
        current=edge["to"]
    return current==graph["target"],{
        "decision":"ACCEPT" if current==graph["target"] else "REJECT_WRONG_ENDPOINT",
        "hops":steps}


if __name__=="__main__":
    raise SystemExit("F124BX_NO_SCIENCE_FIRSTUSE_OR_STANDALONE_TRAINING")
