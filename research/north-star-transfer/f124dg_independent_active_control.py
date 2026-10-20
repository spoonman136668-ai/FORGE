"""F124-DG independently written exact max-rank active comparator.

Same complete 163 Boolean degree<=4 monomials, identical public FIT,
same meta-learned 256 query scores, same fully budgeted counterfactual
oracle. No import of candidate, source or original scientific material.
The lex-rank arm is a secondary equal-budget strong exact-information
control. No privileged source coefficients or CHECK/heldout tuning.
"""
from __future__ import annotations
import itertools

ROLES=("alpha","beta","gamma")
COMBS=[c for degree in range(5) for c in itertools.combinations(range(8),degree)]
W=len(COMBS)
assert W==163

def input_row(pair):
    if type(pair) is not int or pair not in range(256):
        raise ValueError("DG_PEER_INVALID_INTERVENTION")
    answer=0
    for j,comb in enumerate(COMBS):
        if all(pair>>k&1 for k in comb):answer|=1<<j
    return answer

def data(fit):
    if type(fit) is not list or len(fit)!=24:raise ValueError("DG_PEER_FIT_24")
    values=[]
    for ep in fit:
        if set(ep)!={"initial","events"} or set(ep["initial"])!=set(ROLES) or len(ep["events"])!=8:
            raise ValueError("DG_PEER_PUBLIC_EPISODE")
        st={k:list(v) for k,v in ep["initial"].items()}
        for e in ep["events"]:
            if set(e)!={"target","source","event","observed"} or e["target"] not in ROLES or e["source"] not in ROLES:
                raise ValueError("DG_PEER_CAUSAL_EVENT")
            x=st[e["target"]][0]|(st[e["source"]][0]<<4)
            values.append((input_row(x),e["observed"]))
            prior=st[e["target"]][0]
            st[e["target"]]=[e["observed"],prior]
    if len(values)!=192:raise RuntimeError("DG_PEER_MISSING_FIT_TRANSITIONS")
    return values

def echelon(samples):
    ledger={}
    for mask,answer in samples:
        while mask:
            lead=(mask&-mask).bit_length()-1
            if lead not in ledger:
                ledger[lead]=(mask,answer);break
            other,outcome=ledger[lead]
            mask^=other;answer^=outcome
        else:
            if answer:raise RuntimeError("DG_PEER_INCONSISTENT_OBSERVED_DATA")
    return ledger

def rank_gain(rows,probe):
    row=input_row(probe)
    while row:
        lead=(row&-row).bit_length()-1
        if lead not in rows:return 1
        row^=rows[lead][0]
    return 0

def complete(rows):
    masks=[]
    for output in range(4):
        v=0
        for k in sorted(rows,reverse=True):
            linear,bits=rows[k]
            if ((bits>>output)&1)!=((linear&v).bit_count()&1):
                v|=1<<k
        masks.append(v)
    return masks

def output(maskset,pair):
    x=input_row(pair)
    return sum(((maskset[k]&x).bit_count()&1)<<k for k in range(4))

def fit(fit,budget,oracle,meta_scores,lex_only=False):
    if budget not in (0,16,48) or len(meta_scores)!=256:
        raise ValueError("DG_PEER_FROZEN_QUERY_BUDGET")
    samples=data(fit)
    ledger=echelon(samples)
    before=len(ledger)
    chosen=[]
    order=(list(range(256)) if lex_only else
           sorted(range(256),key=lambda v:(-meta_scores[v],v)))
    for _ in range(budget):
        target=next((x for x in order if x not in chosen
                     and rank_gain(ledger,x)),None)
        if target is None:break
        answer=oracle(target)
        if type(answer) is not int or answer not in range(16):
            raise ValueError("DG_PEER_NEW_ORACLE_RESPONSE_INVALID")
        chosen.append(target)
        samples.append((input_row(target),answer))
        ledger=echelon(samples)
    coefficients=complete(ledger)
    if any(((sum(((x&coefficients[k]).bit_count()&1)<<k for k in range(4)))!=y)
           for x,y in samples):
        raise RuntimeError("DG_PEER_ZERO_RESIDUAL_BROKEN")
    return {"theta":coefficients},{
        "FIT_rows":192,"initial_rank":before,"final_rank":len(ledger),
        "budget":budget,"extra_queries":len(chosen),
        "rank_increment":len(ledger)-before,
        "shared_exact_meta_prior":not lex_only,
        "full_exact_rank_greedy":True,
        "no_source_law_access":True,"all_FIT_and_probe_constraints_fit":True}

def trajectory(model,ep):
    if model is None:raise ValueError("DG_PEER_NOT_FITTED")
    if set(ep)!={"initial","events"}:raise ValueError("DG_PEER_EVAL_EPISODE")
    state={k:list(v) for k,v in ep["initial"].items()}
    guesses=[]
    for event in ep["events"]:
        pair=state[event["target"]][0]|(state[event["source"]][0]<<4)
        answer=output(model["theta"],pair)
        old=state[event["target"]][0]
        state[event["target"]]=[answer,old]
        guesses.append(answer)
    return guesses

def score(model,ep):
    a=trajectory(model,ep);b=[e["observed"] for e in ep["events"]]
    return {"correct":a==b,"bit_errors":sum((x^y).bit_count() for x,y in zip(a,b)),
            "native_events":len(a)}
