"""F124-BQ precommitted 32-bit source-blind learned algebraic program.

Two reversible byte shears, but *each operation type is learned from FIT*:
 ADD mod 256 or XOR, never inferred from source or graph family tags.

State: gain1 (7 odd bits), bias1 (8 bits), gain2 (7 odd bits), bias2
(8 bits), mode1 and mode2 (1 bit each) = exactly 32 bits.

CHECK is a pure veto and confidence filter, NEVER a model selector.
"""
from __future__ import annotations

import hashlib
import json

FIT_N=40
CHECK_N=8
ODD_GAINS=tuple(range(1,128,2))
MAX_STAGE_CANDIDATES=4
MAX_PROGRAMS=16
MAX_FIT_BIT_ERRORS=6
MAX_CHECK_BIT_ERRORS=2
MAX_NEAR_FIT=1
STATE_BITS=32
FIT_RESIDUAL_EVAL_CAP=2*2*64*FIT_N
FIT_FULLPROGRAM_CAP=MAX_PROGRAMS*FIT_N


def require(ok,label):
    if not ok:raise ValueError("F124BQ_PROGRAM_"+label)


def _apply(target,mix,mode):
    return ((target+mix)&255) if mode==0 else (target^mix)


def _undo(target,mix,mode):
    return ((target-mix)&255) if mode==0 else (target^mix)


def forward(x,program):
    require(type(x) is int and 0<=x<65536 and
            type(program) in (tuple,list) and len(program)==6
            and all(type(i) is int for i in program),"FORWARD_DOMAIN")
    a,b,c,d,mode1,mode2=program
    require(a in ODD_GAINS and c in ODD_GAINS
            and 0<=b<=255 and 0<=d<=255
            and mode1 in (0,1) and mode2 in (0,1),
            "32_BIT_STATE_DOMAIN")
    lo=x&255
    hi=x>>8
    yl=_apply(lo,(a*hi+b)&255,mode1)
    yh=_apply(hi,(c*yl+d)&255,mode2)
    return yl|(yh<<8)


def inverse(y,program):
    require(type(y) is int and 0<=y<65536,"INVERSE_DOMAIN")
    a,b,c,d,mode1,mode2=program
    yl=y&255
    yh=y>>8
    hi=_undo(yh,(c*yl+d)&255,mode2)
    lo=_undo(yl,(a*hi+b)&255,mode1)
    return lo|(hi<<8)


def _samples(fit,check):
    require(type(fit) in (tuple,list) and len(fit)==FIT_N
            and type(check) in (tuple,list) and len(check)==CHECK_N,
            "PUBLIC_40_AND_8")
    for sample in list(fit)+list(check):
        require(type(sample) in (tuple,list) and len(sample)==2
                and all(type(u) is int and 0<=u<=65535 for u in sample),
                "16_BIT_PUBLIC_PAIR")


def _stage_candidates(fit,stage):
    proposals=[]
    evals=0
    for mode in (0,1):
        for gain in ODD_GAINS:
            observed={}
            for x,y in fit:
                lo,hi=x&255,x>>8
                yl,yh=y&255,y>>8
                target=lo if stage==1 else hi
                result=yl if stage==1 else yh
                driver=hi if stage==1 else yl
                mixing=((result-target)&255) if mode==0 else (result^target)
                bias=(mixing-gain*driver)&255
                observed[bias]=observed.get(bias,0)+1
                evals+=1
            # The deterministic strongest residual is learned from FIT only.
            best_bias=min(observed,key=lambda b:(-observed[b],b))
            wrong_bits=0
            for x,y in fit:
                lo,hi=x&255,x>>8
                yl,yh=y&255,y>>8
                if stage==1:
                    predicted=_apply(lo,(gain*hi+best_bias)&255,mode)
                    wrong_bits+=(predicted^yl).bit_count()
                else:
                    predicted=_apply(hi,(gain*yl+best_bias)&255,mode)
                    wrong_bits+=(predicted^yh).bit_count()
            proposals.append((wrong_bits,gain,best_bias,mode))
    proposals.sort()
    require(evals==2*64*FIT_N,"SOURCEBLIND_FIXED_ENUMERATION")
    return proposals[:MAX_STAGE_CANDIDATES],evals


def _errors(fit,program):
    return sum((forward(x,program)^y).bit_count() for x,y in fit)


def learn(fit,check):
    _samples(fit,check)
    low,n1=_stage_candidates(fit,1)
    high,n2=_stage_candidates(fit,2)
    programs=sorted((
        _errors(fit,(a,b,c,d,m1,m2)),(a,b,c,d,m1,m2)
    ) for _,a,b,m1 in low for _,c,d,m2 in high)
    require(len(programs)<=MAX_PROGRAMS and n1+n2==FIT_RESIDUAL_EVAL_CAP,
            "BOUND_PROGRAM_SEARCH")
    error,best=programs[0]
    check_error=_errors(check,best)
    admitted=(error<=MAX_FIT_BIT_ERRORS
              and check_error<=MAX_CHECK_BIT_ERRORS)
    compatible=tuple(p for fiterror,p in programs
                     if fiterror<=error+MAX_NEAR_FIT
                     and _errors(check,p)<=MAX_CHECK_BIT_ERRORS)
    require(not admitted or best in compatible,
            "CHECK_CANNOT_OVERRIDE_FIT_WINNER")
    receipt={
      "schema":"mass.f124bq.learned-32bit-two-operation-program.v1",
      "state_bits":STATE_BITS,
      "sourceblind_operator_mode_bits":2,
      "learned_from_FIT_only":True,
      "CHECK_can_only_veto":True,
      "public_fit":FIT_N,"public_check":CHECK_N,
      "FIT_error_bits":error,"CHECK_error_bits":check_error,
      "operator1_mode_from_public_fit":best[4],
      "operator2_mode_from_public_fit":best[5],
      "stage_public_residual_evaluations":n1+n2,
      "whole_program_FIT_evaluations":len(programs)*FIT_N,
      "retained_fullprograms":len(programs),
      "confidence_programs":len(compatible) if admitted else 0,
      "FIT_sha256":hashlib.sha256(json.dumps(
          fit,separators=(",",":"),sort_keys=True).encode()).hexdigest(),
      "operator_family_name_used":False,
      "private_source_truth_used":False,
      "graph_oracle_used":False,
      "confidence":admitted
    }
    return (best if admitted else None),receipt,(compatible if admitted else ())


def _bits(bits):
    require(type(bits) is list and len(bits)==16
            and all(type(t) is int and t in (0,1) for t in bits),
            "NATIVE_GRAPH_BITS")
    return sum(t<<i for i,t in enumerate(bits))


def causal_consensus(graph,program,plausible):
    require(program is not None and program in plausible and
            1<=len(plausible)<=MAX_PROGRAMS,"UNCERTAIN_PROGRAM")
    require(type(graph) is dict and set(graph)=={
        "start","target","roles","edges","demos"},"NATIVE_GRAPH_STRUCTURE")
    current=graph["start"]
    carry=None
    steps=0
    for role in graph["roles"]:
        applicable=[e for e in graph["edges"]
                    if e["from"]==current and e["role"]==role]
        if len(applicable)!=1:
            return False,{"decision":"ABSTAIN_ROUTE_AMBIGUOUS","hops":steps}
        edge=applicable[0]
        previous={inverse(_bits(edge["src_bits"]),p) for p in plausible}
        if len(previous)!=1:
            return False,{"decision":"ABSTAIN_NONUNIQUE_PROGRAM_INVERSE",
                          "hops":steps,"candidate_programs":len(plausible)}
        value=next(iter(previous))
        steps+=1
        if carry is not None and carry!=value:
            return False,{"decision":"REJECT_WRONG_CAUSAL_PREDECESSOR",
                          "hops":steps}
        carry=_bits(edge["dst_bits"])
        current=edge["to"]
    passed=(current==graph["target"])
    return passed,{"decision":("ACCEPT_CAUSALLY_CONTIGUOUS" if passed
                             else "REJECT_WRONG_ENDPOINT"),
                   "hops":steps,"candidate_programs":len(plausible)}
