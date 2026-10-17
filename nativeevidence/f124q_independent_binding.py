"""F124-Q independently learned causal-binding deltas on fresh FIT data.

Wingless: uniform-anchored, bounded zero-sum learned latent channel residual.
Yggdrasil: two learned public future-key continuity priorities over the original
7 active + 9 retained cell capacity. No source label or oracle at inference.
"""
from __future__ import annotations
import hashlib
import json
import math
import random
import f124o_native_learners as previous
import f124q_fresh_source as source

EPOCHS=12
BATCH=8
LR=.04
PERTURB=.08
WING_INIT=[0.,0.,0.,0.]
YGG_INIT=[0.,0.]


def need(ok,code):
    source.need(ok,"LEARNER_"+code)


def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def wingless_anchored_weights(base, delta):
    need(len(base)==7 and len(delta)==4 and all(math.isfinite(x) for x in delta),
         "WINGLESS_DELTA_SHAPE")
    avg=sum(delta)/4.
    # Frozen uniform prior; learn only bounded small deviations, no capacity growth.
    return [1.+.2*math.tanh(x-avg) for x in delta]+list(base[4:])


def yggdrasil_lookahead(g, base, delta):
    source.validate_public(g)
    need(len(base)==7 and len(delta)==2 and all(math.isfinite(x) for x in delta),
         "YGGDRASIL_DELTA_SHAPE")
    edges=previous.sorted_edges(g)
    active=[(g["start"],None,0.)]
    retained=[]
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
          "max_retained":0,"evictions":0,"prospective_key_comparisons":0,
          "active_cell_limit":7,"retained_cell_limit":9}
    def comp(carried,src):
        if carried is None:
            return 1.
        work["raw_bit_ops"]+=16
        return sum(base[j]*sum(int(a==b) for a,b in zip(
                carried[j*4:j*4+4],src[j*4:j*4+4]))/4. for j in range(4))/4.
    for step,role in enumerate(g["roles"]):
        nextrole=g["roles"][step+1] if step+1<len(g["roles"]) else None
        candidate=[]
        for node,carried,score in active+retained:
            work["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:
                    continue
                similarity=comp(carried,edge["src_bits"])
                value=score+base[4]*(similarity-.35)
                competition=base[5]*(similarity-.5)
                if nextrole is None:
                    look=0.
                else:
                    possible=[e for e in edges if e["from"]==edge["to"] and
                              e["role"]==nextrole]
                    work["public_edge_scans"]+=len(edges)
                    look=max((comp(tuple(edge["dst_bits"]),q["src_bits"])
                              for q in possible),default=0.)
                    work["prospective_key_comparisons"]+=len(possible)
                # Public *learned* approximate compatibility, never exact oracle.
                cell=(edge["to"],tuple(edge["dst_bits"]),value)
                candidate.append((value+competition+delta[0]*(look-.5),
                                  value-competition+delta[1]*(look-.5),
                                  cell))
        candidate.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active=[row[2] for row in candidate[:7]]
        selected={id(row) for row in candidate[:7]}
        extras=[row for row in candidate if id(row) not in selected]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[row[2] for row in extras[:9]]
        work["evictions"]+=max(0,len(candidate)-16)
        work["max_active"]=max(work["max_active"],len(active))
        work["max_retained"]=max(work["max_retained"],len(retained))
        need(len(active)<=7 and len(retained)<=9 and
             len(active)+len(retained)<=16,"YGGDRASIL_FIXED_CELL_BUDGET")
    terminal=[v for node,_,v in active+retained if node==g["target"]]
    best=max(terminal,default=-2.*len(g["roles"]))
    logit=4.*(best/max(1,len(g["roles"])-1)-base[6])
    need(math.isfinite(logit),"YGGDRASIL_FINITE")
    return logit,work


def forward(lane,g,base,delta):
    if lane=="Wingless":
        return previous.wingless_forward(g,wingless_anchored_weights(base,delta))
    if lane=="Yggdrasil":
        return yggdrasil_lookahead(g,base,delta)
    raise source.Quarantined("F124Q_UNKNOWN_LANE")


def fit_pairs(lane):
    source.frozen()
    pairs=[]
    for vector in source.VECTORS:
        for seed in source.COHORTS[lane]["FIT"]:
            pairs.append(source.build(lane,seed,vector,"FIT"))
    need(len(pairs)==48,"FULL_FIT_DENOMINATOR")
    return pairs


def softplus(x):
    return max(x,0.)+math.log1p(math.exp(-abs(x)))


def loss(lane,pairs,base,delta):
    total=0.
    for pos,neg in pairs:
        a,_=forward(lane,pos,base,delta)
        b,_=forward(lane,neg,base,delta)
        total+=softplus(-a)+softplus(b)+.15*softplus(b-a)
    return total/len(pairs)


def train(lane,base):
    need(lane in ("Wingless","Yggdrasil") and len(base)==7,"KNOWN_LANE_BASE")
    pairs=fit_pairs(lane)
    d=list(WING_INIT if lane=="Wingless" else YGG_INIT)
    start=list(d)
    rng=random.Random(int.from_bytes(hashlib.sha256(
        ("F124Q/FIT/SPSA/v1/"+lane).encode()).digest()[:12],"big"))
    initial=loss(lane,pairs,base,d)
    steps=0
    for epoch in range(EPOCHS):
        order=list(range(48));rng.shuffle(order)
        for k in range(0,48,BATCH):
            subset=[pairs[i] for i in order[k:k+BATCH]]
            sign=[1 if rng.getrandbits(1) else -1 for _ in d]
            hi=[max(-3.,min(3.,v+PERTURB*s)) for v,s in zip(d,sign)]
            lo=[max(-3.,min(3.,v-PERTURB*s)) for v,s in zip(d,sign)]
            derivative=(loss(lane,subset,base,hi)-
                        loss(lane,subset,base,lo))/(2*PERTURB)
            lr=LR/(1.+.01*steps)
            d=[max(-3.,min(3.,v-lr*derivative*s))
               for v,s in zip(d,sign)]
            steps+=1
    change=sum((a-b)**2 for a,b in zip(d,start))**.5
    need(steps==72 and change>1e-9 and
         all(math.isfinite(x) for x in d),"GENUINE_FIT_ONLY_LEARNER_UPDATE")
    return {"lane":lane,"delta":d,"delta_sha256":digest(d),
            "base_weights_sha256":previous.sha(list(base)),
            "fit_only":True,"fit_pairs":48,"epochs":EPOCHS,
            "training_steps":steps,"weight_update_l2":round(change,9),
            "initial_fit_loss":round(initial,8),
            "final_fit_loss":round(loss(lane,pairs,base,d),8),
            "dev_access_during_training":0,
            "protected_access_during_training":0}
