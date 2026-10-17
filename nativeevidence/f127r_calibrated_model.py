"""F127-R fixed-parameter-count raw-binding readout, FIT only."""
import math,json,hashlib
from collections import defaultdict
import f127r_train_environment as env
import f127r_freeze_admission as freeze
import f126r_contrastive_model as prior

INIT=[.12]*16+[.05,1.,3.,.5,0.,0.]
def require(ok,msg): env.need(bool(ok),"MODEL_"+msg)
def sigmoid(x):return 1/(1+math.exp(-max(-40.,min(40.,x))))
def evidence(g,w):
    env.validate(g)
    # Reuse only the frozen PUBLIC route enumerator; never prior trained weights.
    work={k:0 for k in ("public_edge_scans","index_inserts","hashed_bytes",
        "sort_comparison_upper","raw_bit_interactions","feature_adds",
        "candidate_expansions","learned_multiply_adds","derivative_multiply_adds")}
    work["state_peak"]=0
    paths=prior.route_features(g,work)
    require(1<=len(paths)<=16 and work["state_peak"]<=256
            and work["candidate_expansions"]<=512,"BUDGET")
    depth=len(g["roles"])-1
    s=[w[17]*sum(a*b for a,b in zip(w[:16],f))/(16*depth)+w[16]
       for f in paths]
    high=max(s)
    ev=[math.exp(x-high) for x in s]
    probabilities=[x/sum(ev) for x in ev]
    mean=[sum(p*path[k] for p,path in zip(probabilities,paths))
          for k in range(16)]
    d=[w[17]*a/(16*depth) for a in mean]+[
       1.,sum(a*b for a,b in zip(w[:16],mean))/(16*depth)]
    return high+math.log(sum(ev)/len(ev)),d,len(paths),work

def forward(g,w,trace=False,ablation=None):
    env.validate(g)
    require(len(w)==22 and all(type(x) in (float,int) and
            math.isfinite(x) and abs(x)<=8 for x in w),"BAD_WEIGHTS")
    frozen,_=freeze.frozen()
    require(frozen["hypothesis"]["parameters"]==22 and
            frozen["hypothesis"]["training"]["epochs"]==100,"FROZEN_ID")
    require(ablation in (None,"NO_RESIDUAL","GRAPH_NULL_SUBTRACTION"),"ABLATION")
    v,d,paths,work=evidence(g,w)
    if ablation=="GRAPH_NULL_SUBTRACTION":
        null,nd,_,extra=evidence(prior.null_graph(g),w)
        v-=null;d=[a-b for a,b in zip(d,nd)]
        for k in work: work[k]+=extra[k]
    dep=(len(g["roles"])-4)/2.
    number=(paths-9)/6.
    if ablation=="NO_RESIDUAL": dep=number=0.
    z=w[18]*v-w[19]+w[20]*dep+w[21]*number
    grad=[w[18]*x for x in d]+[v,-1.,dep,number]
    p=sigmoid(z)
    if trace:return p,grad,{"logit":z,"paths":paths,"work":work,
                              "protected_confirmation_read":False}
    return p,grad

def fit(rows):
    protocol,_=freeze.frozen()
    require(protocol["hypothesis"]["training"]["epochs"]==100 and
            protocol["hypothesis"]["training"]["learning_rate"]==.22,
            "FROZEN_SCHEDULE")
    require(len(rows)==64 and sum(y for g,y in rows)==32 and
            all(rows[k][1]==1 and rows[k+1][1]==0
                for k in range(0,64,2)),"FIT_ONLY")
    w=INIT[:]
    for epoch in range(100):
        grad=[0.]*22
        for k in range(0,64,2):
            p,dp,a=forward(rows[k][0],w,True)
            n,dn,b=forward(rows[k+1][0],w,True)
            rank=sigmoid(a["logit"]-b["logit"])-1
            for j in range(22):
                grad[j]+=(rank+.5*(p-1))*dp[j]+(-rank+.5*n)*dn[j]
        for j in range(22):
            g=grad[j]/32+(.02*w[j] if j in (20,21) else 0.)
            w[j]=max(-8.,min(8.,w[j]-.22*max(-1.,min(1.,g))))
    return w,sum((a-b)**2 for a,b in zip(w,INIT))**.5

def score(rows,predict):
    require(len(rows)==64 and sum(y for g,y in rows)==32,"CHECK_COHORT")
    out={"pairs":32,"paired_correct":0,"positive_correct":0,
         "negative_correct":0,"rank_correct":0,"depth":{}}
    for k in range(0,64,2):
        require(rows[k][1]==1 and rows[k+1][1]==0,"PAIRED_ORDER")
        a=predict(rows[k][0]);b=predict(rows[k+1][0])
        pc=int(a>=.5);nc=int(b<.5);rank=int(a>b)
        out["paired_correct"]+=pc*nc
        out["positive_correct"]+=pc
        out["negative_correct"]+=nc
        out["rank_correct"]+=rank
        depth=str(len(rows[k][0]["roles"]))
        obj=out["depth"].setdefault(depth,{"pairs":0,"paired_correct":0,
                                "rank_correct":0})
        obj["pairs"]+=1;obj["paired_correct"]+=pc*nc
        obj["rank_correct"]+=rank
    return out
