"""F124-DG source-neutral active rank-guided degree4 causal learner.

Learns FIT bit-polynomial coefficients using independent GF2 rows. Queries
an explicit synthetic oracle for extra information under caller-enforced
budget; meta-preference ranks independently trainable public source pair
frequencies. No source-law module, CHECK/HELDOUT or private oracle import.
"""
from __future__ import annotations
from itertools import combinations

ROLES=("alpha","beta","gamma")
MONOMIALS=tuple(t for degree in range(5) for t in combinations(range(8),degree))
WIDTH=len(MONOMIALS)
assert WIDTH==163

def feature(pair):
    if type(pair) is not int or pair<0 or pair>255:
        raise ValueError("DG_PUBLIC_CAUSAL_INTERVENTION")
    active=0
    for k,mon in enumerate(MONOMIALS):
        if all(pair&(1<<i) for i in mon):
            active|=1<<k
    return active

def check_ep(ep):
    if type(ep) is not dict or set(ep)!={"initial","events"} or set(ep["initial"])!=set(ROLES):
        raise ValueError("DG_PUBLIC_EPISODE")
    if not all(type(v) is list and len(v)==2 and all(
         type(n) is int and 0<=n<16 for n in v)
         for v in ep["initial"].values()):
        raise ValueError("DG_PUBLIC_STATES")
    if type(ep["events"]) is not list or len(ep["events"])!=8 or not all(
        type(e) is dict and set(e)=={"target","source","event","observed"}
        and e["target"] in ROLES and e["source"] in ROLES and e["target"]!=e["source"]
        and type(e["event"]) is int and 0<=e["event"]<16
        and type(e["observed"]) is int and 0<=e["observed"]<16
        for e in ep["events"]):
        raise ValueError("DG_CAUSAL_SEQUENCE_EIGHT")

def supervised_rows(fit):
    if type(fit) is not list or len(fit)!=24:
        raise ValueError("DG_EXACT_24_ORIGINAL_FIT")
    rows=[]
    for ep in fit:
        check_ep(ep)
        memory={k:list(v) for k,v in ep["initial"].items()}
        for e in ep["events"]:
            x=memory[e["target"]][0]|(memory[e["source"]][0]<<4)
            rows.append((x,e["observed"]))
            prev=memory[e["target"]][0]
            memory[e["target"]]=[e["observed"],prev]
    if len(rows)!=192:raise RuntimeError("DG_COMPLETE_FIT_EVENTS")
    return rows

def basis(records):
    pivot={}
    for pair,response in records:
        x=feature(pair);rhs=response
        while x:
            lead=(x&-x).bit_length()-1
            if lead not in pivot:
                pivot[lead]=(x,rhs);break
            row,val=pivot[lead]
            x^=row;rhs^=val
        else:
            if rhs:raise ValueError("DG_INCONSISTENT_TRAINING_OBSERVATIONS")
    return pivot

def independent(pivot,x):
    row=feature(x)
    while row:
        lead=(row&-row).bit_length()-1
        if lead not in pivot:return True
        row^=pivot[lead][0]
    return False

def solve(pivot):
    weights=[]
    for output in range(4):
        mask=0
        for lead in sorted(pivot,reverse=True):
            row,value=pivot[lead]
            wanted=(value>>output)&1
            already=(row&mask).bit_count()&1
            if wanted!=already:mask|=1<<lead
        weights.append(mask)
    return weights

def reconstruct(weights,x):
    row=feature(x)
    return sum(((w&row).bit_count()&1)<<k for k,w in enumerate(weights))

def learn(fit,budget,oracle,meta_scores):
    if budget not in (0,16,48) or type(meta_scores) is not list or len(meta_scores)!=256:
        raise ValueError("DG_FROZEN_EQUAL_ORACLE_BUDGET")
    rows=supervised_rows(fit)
    initial_basis=basis(rows)
    null_probe=next((x for x in range(256) if independent(initial_basis,x)),None)
    selected=[]
    order=sorted(range(256),key=lambda x:(-meta_scores[x],x))
    all_rows=list(rows)
    current=initial_basis
    for _ in range(budget):
        x=next((x for x in order if x not in selected and
                independent(current,x)),None)
        if x is None:break
        reply=oracle(x)
        if type(reply) is not int or not 0<=reply<16:
            raise ValueError("DG_BAD_EXPLICIT_ORACLE_ANSWER")
        selected.append(x)
        all_rows.append((x,reply))
        current=basis(all_rows)
    weights=solve(current)
    if any(reconstruct(weights,x)!=y for x,y in all_rows):
        raise RuntimeError("DG_FIT_AND_QUERY_EQUATIONS_NOT_SOLVED")
    return {"weights":weights},{
      "FIT_rows":192,"additional_oracle_queries":len(selected),
      "query_budget":budget,"initial_rank":len(initial_basis),
      "final_rank":len(current),"rank_increments":len(current)-len(initial_basis),
      "initial_nullspace_dimension":WIDTH-len(initial_basis),
      "original_FIT_has_independent_counterfactual":null_probe is not None,
      "initial_unidentified_pair":null_probe,
      "FIT_and_query_bit_errors":0,
      "meta_scores_shared_with_strongest_comparator":True,
      "oracle_is_additional_information_not_original_FIT_learning":True}

def trajectory(model,ep):
    check_ep(ep)
    if type(model) is not dict or set(model)!={"weights"}:
        raise ValueError("DG_NOT_FITTED_MODEL")
    state={k:list(v) for k,v in ep["initial"].items()}
    pred=[]
    for e in ep["events"]:
        x=state[e["target"]][0]|(state[e["source"]][0]<<4)
        y=reconstruct(model["weights"],x)
        old=state[e["target"]][0]
        state[e["target"]]=[y,old]
        pred.append(y)
    return pred

def score(model,ep):
    a=trajectory(model,ep);b=[e["observed"] for e in ep["events"]]
    return {"correct":a==b,"bit_errors":sum((x^y).bit_count() for x,y in zip(a,b)),
           "native_events":len(a)}
