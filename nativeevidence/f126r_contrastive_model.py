"""F126-R frozen 20-parameter contrastive raw-token binding learner.

Inference consumes one complete public graph. It never sees a partner case,
label, symbolic route, source seed, phase, or confirmation. Training uses only
paired synthetic TRAIN, with a fixed pairwise ranking + 0.5 BCE objective.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from collections import defaultdict

import f126r_freeze_admission as freeze
import f126r_train_environment as env

DIM=20
EPOCHS=100
RATE=.22
CAP=256
EXPANSIONS=512
INIT=[0.12]*16+[0.05,1.0,3.0,0.5]
def need(ok,code): env.need(bool(ok),"MODEL_"+code)
def sha(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def sigmoid(x):return 1/(1+math.exp(-max(-40.,min(40.,x))))
def canonical_key(e):
    return (e["from"],e["to"],e["role"],sha(e))
def null_graph(g):
    """Single canonical PUBLIC-only source-token rotation per observed graph."""
    env.validate(g)
    n=copy.deepcopy(g)
    order=sorted(range(len(n["edges"])),key=lambda i:canonical_key(n["edges"][i]))
    need(len(order)>2,"NO_ROTATABLE_PUBLIC_EDGES")
    tokens=[list(n["edges"][i]["src_bits"]) for i in order]
    # Public graph SHA gives a deterministic offset, independent of edge order.
    offset=1+(int(sha({"query":[g["start"],g["target"],g["roles"]],
                         "edges":sorted(sha(e) for e in g["edges"])}),16)
              % (len(order)-1))
    for k,idx in enumerate(order):
        n["edges"][idx]["src_bits"]=list(tokens[(k+offset)%len(order)])
    env.validate(n)
    return n

def route_features(g,work):
    """Enumerate visible role-compatible paths, never token-filter routes."""
    env.validate(g)
    adjacency=defaultdict(list)
    for e in g["edges"]:
        adjacency[(e["from"],e["role"])].append(e)
        work["public_edge_scans"]+=1
        work["index_inserts"]+=1
        work["hashed_bytes"]+=len(json.dumps(e,sort_keys=True,separators=(",",":")).encode())
    for edges in adjacency.values():
        edges.sort(key=canonical_key)
        work["sort_comparison_upper"]+=len(edges)*max(1,(len(edges)-1).bit_length())
    states=[(g["start"],None,[0.]*16,())]
    paths=[]
    for step,role in enumerate(g["roles"]):
        nxt=[]
        for node,previous,features,route in states:
            for e in adjacency.get((node,role),()):
                f=list(features)
                if previous is not None:
                    f=[v+(2*a-1)*(2*b-1)
                       for v,a,b in zip(f,previous,e["src_bits"])]
                    work["raw_bit_interactions"]+=16
                    work["feature_adds"]+=16
                nxt.append((e["to"],e["dst_bits"],f,route+(sha(e),)))
                work["candidate_expansions"]+=1
                need(work["candidate_expansions"]<=EXPANSIONS,
                     "CANDIDATE_EXPANSION_OVERFLOW")
        states=nxt
        work["state_peak"]=max(work["state_peak"],len(states))
        need(len(states)<=CAP,"PUBLIC_STATE_OVERFLOW")
    for node,last,features,route in states:
        if node==g["target"]:
            paths.append((features,route))
    need(1<=len(paths)<=16,"PUBLIC_PATH_BUDGET")
    paths.sort(key=lambda x:x[1])
    return [f for f,_ in paths]

def logmean_and_deriv(g,w,work):
    features=route_features(g,work)
    depth=len(g["roles"])-1
    need(depth>=2,"MISSING_BINDING_DEPTH")
    # Per-binding mean avoids a raw depth-only route-mass accumulation.
    scale=w[17]/(16*depth)
    scores=[scale*sum(a*b for a,b in zip(w[:16],f))+w[16]
            for f in features]
    work["learned_multiply_adds"]+=16*len(features)
    high=max(scores)
    exp=[math.exp(x-high) for x in scores]
    total=sum(exp)
    probs=[x/total for x in exp]
    value=high+math.log(total/len(scores))
    expected=[sum(p*f[k] for p,f in zip(probs,features)) for k in range(16)]
    wdot=sum(a*b for a,b in zip(w[:16],expected))
    grad=[w[17]*v/(16*depth) for v in expected]+[1.,wdot/(16*depth)]
    work["derivative_multiply_adds"]+=16*len(features)
    return value,grad,len(features)

def forward(g,w,trace=False,ablation=None):
    env.validate(g)
    need(type(w) in (tuple,list) and len(w)==DIM and
         all(type(x) in (float,int) and math.isfinite(x) and abs(x)<=8
             for x in w),"PARAMETER_COUNT_OR_FINITE")
    frozen,_=freeze.frozen()
    need(frozen["hypothesis"]["trainable_parameters"]==DIM
         and frozen["hypothesis"]["optimizer_epochs"]==EPOCHS
         and frozen["hypothesis"]["learning_rate"]==RATE,
         "FROZEN_PROTOCOL_DRIFT")
    need(ablation in (None,"NO_NULL","NO_NORMALIZATION"),
         "UNKNOWN_ABLATION")
    work={k:0 for k in (
        "public_edge_scans","index_inserts","hashed_bytes",
        "sort_comparison_upper","raw_bit_interactions","feature_adds",
        "candidate_expansions","learned_multiply_adds",
        "derivative_multiply_adds")}
    work["state_peak"]=0
    signal,gs,paths=logmean_and_deriv(g,w,work)
    if ablation=="NO_NULL":
        baseline=0.
        gb=[0.]*18
    else:
        reference=null_graph(g)
        baseline,gb,_=logmean_and_deriv(reference,w,work)
    z=signal-baseline
    derivative=[a-b for a,b in zip(gs,gb)]
    if ablation=="NO_NORMALIZATION":
        # Exploratory analysis only. The originally trained weights stay fixed.
        z*=len(g["roles"])-1
        derivative=[v*(len(g["roles"])-1) for v in derivative]
    logit=w[18]*z-w[19]
    dlogit=[w[18]*v for v in derivative]+[z,-1.]
    need(len(dlogit)==20 and all(math.isfinite(x) for x in dlogit+[logit]),
         "NONFINITE_INFERENCE")
    prob=sigmoid(logit)
    if trace:
        return prob,dlogit,{"logit":logit,"binding_evidence":z,
                            "public_complete_paths":paths,
                            "work":work,
                            "protected_confirmation_read":False}
    return prob,dlogit

def fit(rows):
    c,_=freeze.frozen()
    need(c["hypothesis"]["training_loss"].startswith(
        "Full-batch balanced matched-pair logistic ranking loss plus 0.5*BCE")
         and c["hypothesis"]["gradient_clip"]==1
         and c["hypothesis"]["optimizer_epochs"]==EPOCHS,
         "LOSS_OR_SCHEDULE_DRIFT")
    need(type(rows) is list and len(rows)==128
         and sum(y for _,y in rows)==64
         and all(rows[i][1]==1 and rows[i+1][1]==0
                 for i in range(0,128,2)),"FROZEN_PAIRED_TRAIN")
    weights=list(INIT)
    for _ in range(EPOCHS):
        grad=[0.]*DIM
        for i in range(0,len(rows),2):
            pp,gp=forward(rows[i][0],weights)
            pn,gn=forward(rows[i+1][0],weights)
            # Pairwise logistic gradient: d/d logit+ = sigmoid(delta)-1.
            delta=(math.log(pp/(1-pp))-math.log(pn/(1-pn)))
            derivative=sigmoid(delta)-1
            dp=derivative + .5*(pp-1)
            dn=-derivative + .5*pn
            for k in range(DIM):
                grad[k]+=dp*gp[k]+dn*gn[k]
        for k in range(DIM):
            delta=max(-1.,min(1.,grad[k]/64))
            weights[k]=max(-8.,min(8.,weights[k]-RATE*delta))
        need(all(math.isfinite(v) for v in weights),"NONFINITE_UPDATE")
    motion=sum((a-b)**2 for a,b in zip(INIT,weights))**.5
    need(motion>1e-5,"INERT_TRAIN")
    return weights,motion

def paired_score(rows,predict):
    need(len(rows)==128 and sum(y for _,y in rows)==64,"SCORE_COHORT")
    paired=pos=neg=rank=0
    depth={}
    for k in range(0,len(rows),2):
        p,y=rows[k];n,yn=rows[k+1]
        need(y==1 and yn==0,"LABEL_ORDER")
        a,b=predict(p),predict(n)
        yes=a>=.5;no=b<.5
        paired+=int(yes and no)
        pos+=int(yes);neg+=int(no);rank+=int(a>b)
        key=str(len(p["roles"]))
        if key not in depth:depth[key]={"pairs":0,"paired_correct":0,"rank_correct":0}
        depth[key]["pairs"]+=1
        depth[key]["paired_correct"]+=int(yes and no)
        depth[key]["rank_correct"]+=int(a>b)
    return {"pairs":64,"paired_correct":paired,
            "positive_correct":pos,"negative_correct":neg,
            "rank_correct":rank,
            "balanced_accuracy":round((pos+neg)/128,8),
            "depth":depth}
