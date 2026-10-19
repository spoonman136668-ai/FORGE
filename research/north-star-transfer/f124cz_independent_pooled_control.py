"""F124-CZ independent fully trained pooled nonlinear causal control.

No candidate module import. Independent quadratic feature inventory and
row-reduced parity fit over ALL original public FIT episodes, with identical
211 public raw/second-order features and identical canonical ordering.
This ensures success cannot be attributed merely to giving only the
candidate nonlinear interactions. No CHECK or heldout updates.
"""
from __future__ import annotations

ROLES=("alpha","beta","gamma")
SIZE=211

def feature_pairs():
    top=[]
    for left,right in ((range(4),range(8,12)),(range(4,8),range(8,12)),
                       (range(4),range(12,16)),(range(16,20),range(8,12))):
        for i in left:
            for j in right:
                key=(min(i,j),max(i,j))
                if key not in top:top.append(key)
    for i in range(20):
        for j in range(i+1,20):
            if (i,j) not in top:top.append((i,j))
    if len(top)!=190:raise ValueError("F124CZ_CONTROL_FULL_190_MONOMIALS")
    return top

ORDER=feature_pairs()

def check_episode(ep):
    if type(ep) is not dict or set(ep)!={"initial","events"} or set(ep["initial"])!=set(ROLES):
        raise ValueError("F124CZ_CONTROL_EPISODE")
    if type(ep["events"]) is not list or len(ep["events"])!=8 or not all(
        type(e) is dict and set(e)=={"target","source","event","observed"} and
        e["target"] in ROLES and e["source"] in ROLES and e["source"]!=e["target"] and
        type(e["event"]) is int and 0<=e["event"]<16 and
        type(e["observed"]) is int and 0<=e["observed"]<16 for e in ep["events"]):
        raise ValueError("F124CZ_CONTROL_SEQUENCE")
    if not all(type(v) is list and len(v)==2 and
              all(type(x) is int and 0<=x<16 for x in v)
              for v in ep["initial"].values()):
        raise ValueError("F124CZ_CONTROL_INITIAL")

def encode(mem,row):
    own=mem[row["target"]];src=mem[row["source"]]
    ints=(own[0],own[1],src[0],src[1],row["event"])
    x=sum(q<<(j*4) for j,q in enumerate(ints))
    response=x|(1<<20)
    for offset,(i,j) in enumerate(ORDER,21):
        if x&(1<<i) and x&(1<<j):response|=1<<offset
    return response

def eliminate(records,which_bit):
    # Alternative incremental echelon basis, then backward triangular solve.
    # Same ordered features, zero unconstrained variables as candidate.
    reduced=[bits|(((response>>which_bit)&1)<<SIZE)
             for bits,response in records]
    basis={}
    for row in reduced:
        while row&((1<<SIZE)-1):
            lead=((row&((1<<SIZE)-1))&-(row&((1<<SIZE)-1))).bit_length()-1
            if lead in basis:row^=basis[lead]
            else:
                basis[lead]=row;break
        else:
            if row>>SIZE&1:return None,len(basis)
    theta=0
    for lead in sorted(basis,reverse=True):
        row=basis[lead]
        desired=((row>>SIZE)&1)^((row&theta).bit_count()&1)
        if desired:theta|=1<<lead
    return theta,len(basis)

def train(fit):
    if type(fit) is not list or len(fit)!=24:
        raise ValueError("F124CZ_CONTROL_FULL_FIT")
    raw=[]
    for ep in fit:
        check_episode(ep)
        mem={role:list(v) for role,v in ep["initial"].items()}
        for row in ep["events"]:
            x=encode(mem,row)
            raw.append((x,row["observed"]))
            previous=mem[row["target"]][0]
            mem[row["target"]]=[row["observed"],previous]
    weights=[];ranks=[]
    for bit in range(4):
        x,rank=eliminate(raw,bit)
        if x is None:
            return None,{"FIT_consistent":False,"natural_model_fitted":False}
        weights.append(x);ranks.append(rank)
    errs=sum((infer(x,weights)^y).bit_count() for x,y in raw)
    if errs:raise RuntimeError("F124CZ_STRONG_POOLED_PEER_FIT")
    return {"masks":weights},{"FIT_consistent":True,"FIT_rows":192,
           "FIT_bit_errors":0,"natural_model_fitted":True,
           "rank":ranks,"source_unknown":True,
           "all_identical_211_feature_inventory":True,
           "fully_fitted_without_CHECK_or_holdout":True}

def infer(x,weights):
    return sum(((x&w).bit_count()&1)<<i for i,w in enumerate(weights))

def trajectory(model,ep):
    check_episode(ep)
    if model is None:raise ValueError("F124CZ_CONTROL_NOT_FITTED")
    mem={r:list(v) for r,v in ep["initial"].items()}
    outputs=[]
    for e in ep["events"]:
        y=infer(encode(mem,e),model["masks"])
        t=e["target"]
        before=mem[t][0]
        mem[t]=[y,before]
        outputs.append(y)
    return outputs

def score(model,ep):
    p=trajectory(model,ep);y=[e["observed"] for e in ep["events"]]
    return {"correct":p==y,"bit_errors":sum((a^b).bit_count() for a,b in zip(p,y)),
            "native_event_calls":8}
