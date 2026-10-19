"""F124-BO: fit nonlinear reversible modular relation with selective confidence.

Task-local learning from 40 public FIT, 8 CHECK only; no source import.
One precommitted representation for all operator families:
 y = ((a*x + b) modulo 65536) XOR c, a odd.
Max 64 beam entries and 8192 extensions; six-byte fitted model.
Never treats a guessed path as true solely because native scorer likes it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

BEAM=64
BITS=16
EXTENSION_BUDGET=16*64*8
CHECK_LIMIT=2
FIT_TIE_MARGIN=1
CHECK_CONSENSUS_MARGIN=1


def need(ok,reason):
    if not ok:
        raise ValueError("F124BO_NONLINEAR_"+reason)


def _validate(fit,check):
    need(isinstance(fit,(tuple,list)) and len(fit)==40
         and isinstance(check,(tuple,list)) and len(check)==8,
         "EXACT_PUBLIC_FIT_CHECK")
    for pair in list(fit)+list(check):
        need(isinstance(pair,(list,tuple)) and len(pair)==2
             and all(type(v) is int and 0<=v<65536 for v in pair),
             "PUBLIC_16_BIT_PAIRS")


def forward(x,parameters):
    a,b,c=parameters
    need(type(x) is int and 0<=x<65536
         and all(type(p) is int and 0<=p<65536 for p in parameters)
         and a&1,"ODD_REVERSIBLE_RELATION")
    return ((a*x+b)&65535)^c


def inverse(y,parameters):
    a,b,c=parameters
    need(type(y) is int and 0<=y<65536,"INVERSE_INPUT")
    return ((((y^c)-b)*pow(a,-1,65536))&65535)


def _errors(samples,params,mask=65535):
    a,b,c=params
    return sum(((((a*x+b)&mask)^(c&mask)^(y&mask)).bit_count())
               for x,y in samples)


def learn(fit,check):
    _validate(fit,check)
    # Only public FIT affects all beam parameter choices and tie-breaking.
    candidates=[(0,0,0,0)]
    extensions=0
    trace=[]
    for layer in range(BITS):
        mask=(1<<(layer+1))-1
        bit=1<<layer
        options=[]
        for cost,a,b,c in candidates:
            for abit in ((1,) if layer==0 else (0,1)):
                for bbit in (0,1):
                    for cbit in (0,1):
                        next_param=(a|abit*bit,b|bbit*bit,c|cbit*bit)
                        # Existing prefix errors cannot be erased.
                        mismatch=_errors(fit,next_param,mask)
                        extensions+=1
                        options.append((mismatch,*next_param))
        options.sort()
        candidates=options[:BEAM]
        need(len(candidates)>0 and extensions<=EXTENSION_BUDGET,
             "BOUNDED_BEAM_SEARCH")
        trace.append({"layer":layer,"retained":len(candidates),
                      "best_fit_bit_errors":candidates[0][0]})
    best_fit=candidates[0][0]
    near=[item for item in candidates if item[0]<=best_fit+FIT_TIE_MARGIN]
    measured=[(_errors(check,item[1:]),item)
              for item in near]
    eligible=[(e,it) for e,it in measured if e<=CHECK_LIMIT]
    fit_digest=hashlib.sha256(json.dumps(fit,sort_keys=True,
                            separators=(",",":")).encode()).hexdigest()
    # Never train model selection on CHECK: best beam is fixed by FIT;
    # checking confidence may only reduce, not improve, admissibility.
    main=candidates[0][1:]
    main_check=_errors(check,main)
    passed=(best_fit<=6 and main_check<=CHECK_LIMIT)
    if not passed:
        return None,{"fit_sha256":fit_digest,"fit_errors":best_fit,
                     "CHECK_errors":main_check,"parameter_bits":48,
                     "search_extensions":extensions,"beam_size":BEAM,
                     "confident":False,"oracle_used":False,
                     "role_family_tag_used":False,
                     "trace":trace},()
    plausible=tuple(it[1:] for e,it in eligible
                    if e<=main_check+CHECK_CONSENSUS_MARGIN)
    need(main in plausible,"CHECK_CANNOT_RESELECT_MODEL")
    return main,{"fit_sha256":fit_digest,"fit_errors":best_fit,
                 "CHECK_errors":main_check,"parameter_bits":48,
                 "search_extensions":extensions,"beam_size":BEAM,
                 "confident":True,
                 "candidate_count_for_graph_consensus":len(plausible),
                 "oracle_used":False,"role_family_tag_used":False,
                 "trace":trace},plausible


def _u16(bits):
    need(isinstance(bits,list) and len(bits)==16
         and all(type(bit) is int and bit in (0,1) for bit in bits),
         "GRAPH_NATIVE_BITS")
    return sum(bit<<i for i,bit in enumerate(bits))


def selective_causal_path(graph,parameters,plausible):
    need(parameters is not None and parameters in plausible
         and len(plausible)<=BEAM,
         "UNCERTAIN_MODEL_ABSTAIN")
    need(isinstance(graph,dict) and
         set(graph)=={"start","target","roles","edges","demos"},
         "EXACT_NATIVE_GRAPH_FORMAT")
    role_seq=graph["roles"]
    current=graph["start"]
    carry=None
    hops=0
    for role in role_seq:
        edges=[e for e in graph["edges"]
               if e["from"]==current and e["role"]==role]
        if len(edges)!=1:
            return False,{"decision":"ABSTAIN_GRAPH_AMBIGUOUS",
                          "hops":hops}
        edge=edges[0]
        y=_u16(edge["src_bits"])
        predictions={inverse(y,params) for params in plausible}
        if len(predictions)!=1:
            return False,{"decision":"ABSTAIN_NONLINEAR_CONFIDENCE",
                          "hops":hops,"plausible":len(plausible)}
        predecessor=next(iter(predictions))
        hops+=1
        if carry is not None and predecessor!=carry:
            return False,{"decision":"REJECT_CAUSAL_EDGE",
                          "hops":hops}
        carry=_u16(edge["dst_bits"])
        current=edge["to"]
    return current==graph["target"],{
        "decision":"ACCEPT_CONFIDENT_CAUSAL_CHAIN"
                   if current==graph["target"] else "REJECT_END_NODE",
        "hops":hops,"plausible":len(plausible)}
