"""F124-CY independently fitted, fully trained role-conditional GF2 control.

The comparator receives SAME 20 public causal bit features, the same 24
FIT and eight CHECK sequences and the same declared event gate. It trains
independent programs for each of six ordered target/source entity edges.
No candidate imports or deliberately weakened optimization. Underconstrained
features use a deterministic zero-free-variable exact solver.
"""
from __future__ import annotations

ROLES=("alpha","beta","gamma")
REGIMES=("ungated_shared_linear_GF2","event_bit_gated_GF2")
WIDTH=21

def validate(ep):
    if type(ep) is not dict or set(ep)!={"initial","events"} or set(ep["initial"])!=set(ROLES):
        raise ValueError("F124CY_CONTROL_EPISODE")
    if len(ep["events"])!=8 or not all(set(x)=={"target","source","event","observed"} and
          x["target"] in ROLES and x["source"] in ROLES and x["source"]!=x["target"] and
          all(type(x[q]) is int and 0<=x[q]<16 for q in ("event","observed"))
          for x in ep["events"]):raise ValueError("F124CY_CONTROL_EVENTS")
    if not all(type(v) is list and len(v)==2 and
               all(type(x) is int and 0<=x<16 for x in v)
               for v in ep["initial"].values()):raise ValueError("F124CY_CONTROL_INIT")

def form(state,x):
    own=state[x["target"]];other=state[x["source"]]
    return own[0]|(own[1]<<4)|(other[0]<<8)|(other[1]<<12)|(x["event"]<<16)|(1<<20)

def solve(A,bit):
    mat=[x+(((y>>bit)&1)<<WIDTH) for x,y in A]
    pivot=[]
    n=0
    for position in range(WIDTH):
        row=next((k for k in range(n,len(mat)) if (mat[k]>>position)&1),None)
        if row is None:continue
        mat[n],mat[row]=mat[row],mat[n]
        for j in range(len(mat)):
            if j!=n and (mat[j]>>position)&1:mat[j]^=mat[n]
        pivot.append(position);n+=1
        if n==len(mat):break
    if any(((x&((1<<WIDTH)-1))==0) and ((x>>WIDTH)&1) for x in mat):
        return None,n
    solution=0
    for index in range(len(pivot)-1,-1,-1):
        col=pivot[index]
        rhs=(mat[index]>>WIDTH)&1
        parity=(mat[index]&solution).bit_count()&1
        if rhs^parity:solution|=(1<<col)
    return solution,n

def train(fit,regime):
    if type(fit) is not list or len(fit)!=24 or regime not in REGIMES:
        raise ValueError("F124CY_CONTROL_FIT_PROTOCOL")
    groups={}
    for ep in fit:
        validate(ep)
        state={name:list(value) for name,value in ep["initial"].items()}
        for x in ep["events"]:
            key=(x["target"],x["source"],x["event"]&1 if regime==REGIMES[1] else 0)
            groups.setdefault(key,[]).append((form(state,x),x["observed"]))
            current=state[x["target"]][0]
            state[x["target"]]=[x["observed"],current]
    learned={};inconsistent=[]
    for target in ROLES:
        for source in ROLES:
            if target==source:continue
            for gate in range(2 if regime==REGIMES[1] else 1):
                k=(target,source,gate);samples=groups.get(k,[])
                masks=[];rank=0
                for bit in range(4):
                    fitted,bit_rank=solve(samples,bit);rank=max(rank,bit_rank)
                    if fitted is None:inconsistent.append(k);break
                    masks.append(fitted)
                if len(masks)==4:learned[k]={"masks":masks,"FIT_sample_count":len(samples),"rank":rank}
    if inconsistent:
        return None,{"natural_admission":False,"inconsistent_groups":inconsistent}
    return {"regime":regime,"edges":learned},{
       "natural_admission":True,
       "complete_FIT_rows":192,
       "trained_directed_edge_groups":len(learned),
       "full_public_bit_feature_vocabulary":21,
       "fully_fitted_without_CHECK_tuning":True,
       "zero_unconstrained_free_parameters":True,
       "edge_fit_ranks":{"/".join(map(str,k)):v["rank"] for k,v in learned.items()}}

def predict(model,ep):
    validate(ep)
    if model is None:raise ValueError("F124CY_CONTROL_NOT_ADMITTED")
    state={name:list(value) for name,value in ep["initial"].items()}
    outputs=[]
    for event in ep["events"]:
        key=(event["target"],event["source"],
             (event["event"]&1) if model["regime"]==REGIMES[1] else 0)
        weights=model["edges"][key]["masks"]
        f=form(state,event)
        y=sum(((f&m).bit_count()&1)<<i for i,m in enumerate(weights))
        before=state[event["target"]][0]
        state[event["target"]]=[y,before]
        outputs.append(y)
    return outputs

def score(model,ep):
    predicted=predict(model,ep)
    actual=[row["observed"] for row in ep["events"]]
    return {"correct":predicted==actual,
            "bit_errors":sum((a^b).bit_count() for a,b in zip(predicted,actual)),
            "native_event_calls":len(predicted)}

if __name__=="__main__":
    raise SystemExit("F124CY_STRONG_ROLE_PAIR_CONTROL_ONLY")
