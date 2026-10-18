"""F124-R independent fixed-budget causal-key calibration experiments.

- Wingless: uniform-anchored compressed message passing plus two learned
  continuous raw-key calibration coefficients, at most 3 states/public node.
- Yggdrasil: retain original 7 active and 9 retained cells and original
  learned discrete selector; train two scalar continuous causal-evidence
  readout weights, so gradients do not require ranking flips.
No original model mutation, label, oracle, future query or protected source.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
import math
import random

import f124o_native_learners as original
import f124r_fresh_source as source

EPOCHS=12
BATCH=8
LR=.04
PERTURB=.08
WING_INIT=[0.,0.]
YGG_INIT=[0.,0.]


def need(ok,msg):
    source.need(ok,"LEARNER_"+msg)


def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,
        separators=(",",":")).encode()).hexdigest()


def wingless_calibrated(g,base,delta):
    source.validate_public(g)
    need(len(base)==7 and len(delta)==2 and
         all(math.isfinite(v) for v in list(base)+list(delta)),
         "WING_PARAMETERS")
    # original F124O head and capacity remain immutable; channels uniform.
    w=[1.,1.,1.,1.]+list(base[4:])
    mix=original.sigmoid(delta[0])
    temp=1.+.2*math.tanh(delta[1])
    edges=original.sorted_edges(g)
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
          "evictions":0,"state_limit":3,"causal_key_comparisons":0,
          "max_retained":0}
    def enc(bits):
        work["raw_bit_ops"]+=16
        return tuple(sum(2*b-1 for b in bits[j*4:j*4+4])/4.
                     for j in range(4))
    def affinity(carried,carried_raw,src,src_raw):
        work["raw_bit_ops"]+=4+16
        work["causal_key_comparisons"]+=1
        latent=1.-sum(abs(a-b) for a,b in zip(carried,src))/8.
        raw=sum(int(a==b) for a,b in zip(carried_raw,src_raw))/16.
        return temp*((1.-mix)*latent+mix*raw)
    # original top-3-per-node selection, with raw key only as an ordinary
    # public data field carried alongside compressed state (same slot count).
    states={g["start"]:[(0.,None,None)]}
    for step,role in enumerate(g["roles"]):
        nextrole=g["roles"][step+1] if step+1<len(g["roles"]) else None
        new=defaultdict(list)
        for node in sorted(states):
            allowed=[e for e in edges if e["from"]==node and e["role"]==role]
            for score,carried,carried_raw in states[node]:
                work["public_edge_scans"]+=len(edges)
                for edge in allowed:
                    src=enc(edge["src_bits"])
                    dst=enc(edge["dst_bits"])
                    compat=1. if carried is None else affinity(
                        carried,carried_raw,src,tuple(edge["src_bits"]))
                    value=score+w[4]*(compat-.6)
                    if nextrole is None:
                        look=0.
                    else:
                        queries=[q for q in edges if q["from"]==edge["to"] and
                                 q["role"]==nextrole]
                        look=max((affinity(dst,tuple(edge["dst_bits"]),
                                          enc(q["src_bits"]),tuple(q["src_bits"]))
                                  for q in queries),default=0.)
                    priority=value+w[5]*(look-.6)
                    new[edge["to"]].append((
                        priority,value,dst,tuple(edge["dst_bits"])))
        states={}
        for node,candidates in new.items():
            candidates.sort(key=lambda x:(-x[0],-x[1],x[2],x[3]))
            work["evictions"]+=max(0,len(candidates)-3)
            states[node]=[(v,k,raw) for _,v,k,raw in candidates[:3]]
        work["max_active"]=max(work["max_active"],
                               sum(len(v) for v in states.values()))
        need(work["max_active"]<=192,"WING_PUBLIC_NODE_STATE_BUDGET")
    terminal=[score for score,_,_ in states.get(g["target"],[])]
    best=max(terminal,default=-2.*len(g["roles"]))
    logit=4.*(best/max(1,len(g["roles"])-1)-w[6])
    need(math.isfinite(logit),"WING_NONFINITE")
    return logit,work


def yggdrasil_continuous(g,base,delta):
    source.validate_public(g)
    need(len(base)==7 and len(delta)==2 and
         all(math.isfinite(v) for v in list(base)+list(delta)),
         "YGG_PARAMETERS")
    edges=original.sorted_edges(g)
    active=[(g["start"],None,0.)]
    retained=[]
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
          "max_retained":0,"evictions":0,"active_cell_limit":7,
          "retained_cell_limit":9,"causal_key_comparisons":0}
    evidence_sum=0.
    evidence_count=0
    target_sum=0.
    target_count=0
    def compat(carried,src):
        if carried is None:
            return 1.
        work["raw_bit_ops"]+=16
        work["causal_key_comparisons"]+=1
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            carried[j*4:j*4+4],src[j*4:j*4+4]))/4.
            for j in range(4))/4.
    for step,role in enumerate(g["roles"]):
        candidate=[]
        for node,carried,score in active+retained:
            work["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:
                    continue
                similarity=compat(carried,edge["src_bits"])
                value=score+base[4]*(similarity-.35)
                competition=base[5]*(similarity-.5)
                # Continuous, bounded evidence of approximate raw-key
                # agreement over *all visited role-constrained candidates*.
                # Learning modifies only downstream readout, never rankings.
                soft=original.sigmoid(6.*(similarity-.5))
                evidence_sum+=soft
                evidence_count+=1
                if step==len(g["roles"])-1 and edge["to"]==g["target"]:
                    target_sum+=soft
                    target_count+=1
                cell=(edge["to"],tuple(edge["dst_bits"]),value)
                candidate.append((value+competition,value-competition,cell))
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
             len(active)+len(retained)<=16,
             "YGG_EXACT_SEVEN_NINE_CELLS")
    terminal=[score for node,_,score in active+retained
              if node==g["target"]]
    best=max(terminal,default=-2.*len(g["roles"]))
    original_logit=4.*(best/max(1,len(g["roles"])-1)-base[6])
    # Two scalar aggregates, no extra retained cognitive memory cells.
    mean=(evidence_sum/max(1,evidence_count))-.5
    final_target=(target_sum/max(1,target_count))-.5 if target_count else -.5
    logit=original_logit+2.*delta[0]*mean+2.*delta[1]*final_target
    need(math.isfinite(logit),"YGG_NONFINITE")
    return logit,work


def forward(lane,g,base,delta):
    if lane=="Wingless":
        return wingless_calibrated(g,base,delta)
    if lane=="Yggdrasil":
        return yggdrasil_continuous(g,base,delta)
    raise source.Quarantined("F124R_UNKNOWN_LANE")


def fit_pairs(lane):
    source.frozen()
    result=[]
    for vector in source.VECTORS:
        for seed in source.COHORTS[lane]["FIT"]:
            result.append(source.build(lane,seed,vector,"FIT"))
    need(len(result)==48,"FIT_DENOMINATOR")
    return result


def softplus(x):
    return max(0.,x)+math.log1p(math.exp(-abs(x)))


def pair_loss(lane,pairs,base,delta):
    total=0.
    for pos,neg in pairs:
        a,_=forward(lane,pos,base,delta)
        b,_=forward(lane,neg,base,delta)
        total+=softplus(-a)+softplus(b)+.15*softplus(b-a)
    return total/len(pairs)


def train(lane,base):
    need(lane in ("Wingless","Yggdrasil") and len(base)==7,"LANE_ID")
    pairs=fit_pairs(lane)
    w=list(WING_INIT if lane=="Wingless" else YGG_INIT)
    prior=list(w)
    rng=random.Random(int.from_bytes(hashlib.sha256(
        ("F124R/FIT/SPSA/v1/"+lane).encode()).digest()[:12],"big"))
    initial=pair_loss(lane,pairs,base,w)
    step=0
    for _ in range(EPOCHS):
        indices=list(range(48));rng.shuffle(indices)
        for k in range(0,48,BATCH):
            batch=[pairs[i] for i in indices[k:k+BATCH]]
            signs=[1 if rng.getrandbits(1) else -1 for _ in w]
            hi=[max(-3.,min(3.,v+PERTURB*s)) for v,s in zip(w,signs)]
            lo=[max(-3.,min(3.,v-PERTURB*s)) for v,s in zip(w,signs)]
            g=(pair_loss(lane,batch,base,hi)-
               pair_loss(lane,batch,base,lo))/(2*PERTURB)
            lr=LR/(1.+.01*step)
            w=[max(-3.,min(3.,v-lr*g*s)) for v,s in zip(w,signs)]
            step+=1
    magnitude=sum((x-y)**2 for x,y in zip(w,prior))**.5
    need(step==72 and magnitude>1e-9 and
         all(math.isfinite(v) for v in w),
         "GENUINE_FIT_LEARNING_OR_NONFINITE")
    return {"lane":lane,"delta":w,"delta_sha256":digest(w),
            "base_weights_sha256":original.sha(list(base)),
            "fit_only":True,"fit_pairs":48,"epochs":EPOCHS,
            "training_steps":step,"initial_fit_loss":round(initial,8),
            "final_fit_loss":round(pair_loss(lane,pairs,base,w),8),
            "weight_update_l2":round(magnitude,9),
            "dev_access_during_training":0,"protected_access_during_training":0}
