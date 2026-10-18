"""F124-S: Wingless packed-key replacement, Yggdrasil learned cell credit.

Wingless serialized per-state payload is literally struct <dH (10 bytes), not
the prior floating score + four float64 compressed channels (40 logical bytes).
Information granularity differs: byte bound alone is not representational
capacity equivalence, and operation costs are measured separately.
Yggdrasil's state is unchanged (node, raw16, evidence), with learned continuous
credit added before existing seven-active/nine-retained selection.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
import math
import random
import struct

import f124o_native_learners as original
import f124s_fresh_source as source

STATE=struct.Struct("<dH")
SCORE=struct.Struct("<d")
EPOCHS=12
BATCH=8
LR=.04
PERTURB=.08
WING_INIT=[0.,0.]
YGG_INIT=[0.,0.]


def need(x,msg):
    source.need(x,"LEARNER_"+msg)


def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,
           separators=(",",":")).encode()).hexdigest()


def bits_to_uint16(bits):
    need(type(bits) is list and len(bits)==16 and
         all(type(x) is int and x in (0,1) for x in bits),
         "PACKED_BITS_NOT_RAW16")
    return sum(v<<i for i,v in enumerate(bits))


def wingless_packed(g,base,delta):
    source.validate_public(g)
    need(len(base)==7 and len(delta)==2 and
         all(math.isfinite(x) for x in list(base)+list(delta)),
         "WING_DELTA")
    edges=original.sorted_edges(g)
    w=[1.,1.,1.,1.]+list(base[4:])
    mix=original.sigmoid(delta[0])
    temp=1.+.2*math.tanh(delta[1])
    cost={"public_edge_scans":0,"raw_bit_ops":0,"causal_key_comparisons":0,
          "max_active":1,"max_retained":0,"evictions":0,"state_limit":3,
          "serialized_state_payload_bytes":STATE.size,
          "reference_serialized_state_payload_bytes":40,
          "max_serialized_payload_bytes":STATE.size}
    # Logical carried key IS the original 16-bit token, and REPLACES rather than
    # accompanies the expanded four-element latent vector. Persistent states
    # are exact 10-byte binary records, checked when read/write.
    def pack(bits):
        cost["raw_bit_ops"]+=16
        return bits_to_uint16(bits)
    def channel_vector(key):
        cost["raw_bit_ops"]+=16
        return tuple((2*((key>>(4*j))&15).bit_count()-4)/4. for j in range(4))
    def affinity(a,b):
        cost["raw_bit_ops"]+=20
        cost["causal_key_comparisons"]+=1
        av,bv=channel_vector(a),channel_vector(b)
        latent=1.-sum(abs(x-y) for x,y in zip(av,bv))/8.
        raw=(16-(a^b).bit_count())/16.
        return temp*((1.-mix)*latent+mix*raw)
    state={g["start"]:[STATE.pack(0.,0)]}
    for hop,role in enumerate(g["roles"]):
        nextrole=g["roles"][hop+1] if hop+1<len(g["roles"]) else None
        proposals=defaultdict(list)
        for node in sorted(state):
            allowed=[e for e in edges if e["from"]==node and e["role"]==role]
            for record in state[node]:
                need(type(record) is bytes and len(record)==STATE.size,
                     "WING_SERIALIZATION_BOUNDARY")
                score,carried=STATE.unpack(record)
                cost["public_edge_scans"]+=len(edges)
                for e in allowed:
                    src=pack(e["src_bits"])
                    dst=pack(e["dst_bits"])
                    compatibility=1. if hop==0 else affinity(carried,src)
                    value=score+w[4]*(compatibility-.6)
                    if nextrole is None:
                        look=0.
                    else:
                        q=[t for t in edges if t["from"]==e["to"] and
                           t["role"]==nextrole]
                        look=max((affinity(dst,pack(t["src_bits"]))
                                  for t in q),default=0.)
                        cost["public_edge_scans"]+=len(edges)
                    priority=value+w[5]*(look-.6)
                    record_next=STATE.pack(value,dst)
                    proposals[e["to"]].append((priority,record_next))
        state={}
        for node,options in proposals.items():
            options.sort(key=lambda x:(-x[0],x[1]))
            cost["evictions"]+=max(0,len(options)-3)
            state[node]=[rec for _,rec in options[:3]]
        cost["max_active"]=max(cost["max_active"],
                               sum(len(v) for v in state.values()))
        cost["max_serialized_payload_bytes"]=max(
            cost["max_serialized_payload_bytes"],
            cost["max_active"]*STATE.size)
        need(cost["max_active"]<=192 and
             all(len(v)<=3 for v in state.values()),"WING_NODE_CAPACITY")
    scores=[STATE.unpack(rec)[0] for rec in state.get(g["target"],[])]
    best=max(scores,default=-2.*len(g["roles"]))
    logit=4.*(best/max(1,len(g["roles"])-1)-w[6])
    need(math.isfinite(logit),"WING_FINITE")
    return logit,cost


def yggdrasil_cell_credit(g,base,delta):
    source.validate_public(g)
    need(len(base)==7 and len(delta)==2 and
         all(math.isfinite(x) for x in list(base)+list(delta)),
         "YGG_DELTA")
    edges=original.sorted_edges(g)
    active=[(g["start"],None,0.)]
    retained=[]
    cost={"public_edge_scans":0,"raw_bit_ops":0,
          "causal_key_comparisons":0,"max_active":1,"max_retained":0,
          "evictions":0,"active_cell_limit":7,"retained_cell_limit":9}
    def compatibility(carried,src):
        if carried is None:
            return 1.
        cost["raw_bit_ops"]+=16
        cost["causal_key_comparisons"]+=1
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            carried[j*4:j*4+4],src[j*4:j*4+4]))/4.
            for j in range(4))/4.
    for role in g["roles"]:
        proposals=[]
        for node,carried,score in active+retained:
            cost["public_edge_scans"]+=len(edges)
            for e in edges:
                if e["from"]!=node or e["role"]!=role:
                    continue
                sim=compatibility(carried,e["src_bits"])
                confidence=original.sigmoid(6.*(sim-.5))-.5
                # Both continuous parameters participate in the cell's
                # pre-selection evidence/value; not a final-only surrogate.
                value=score+base[4]*(sim-.35)+delta[0]*confidence
                competition=base[5]*(sim-.5)+delta[1]*confidence
                cell=(e["to"],tuple(e["dst_bits"]),value)
                proposals.append((value+competition,value-competition,cell))
        proposals.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active=[row[2] for row in proposals[:7]]
        selected={id(row) for row in proposals[:7]}
        extras=[row for row in proposals if id(row) not in selected]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[row[2] for row in extras[:9]]
        cost["evictions"]+=max(0,len(proposals)-16)
        cost["max_active"]=max(cost["max_active"],len(active))
        cost["max_retained"]=max(cost["max_retained"],len(retained))
        need(len(active)<=7 and len(retained)<=9 and
             len(active)+len(retained)<=16,"YGG_7_PLUS_9_FIXED_CAP")
    terminal=[v for node,_,v in active+retained if node==g["target"]]
    best=max(terminal,default=-2.*len(g["roles"]))
    logit=4.*(best/max(1,len(g["roles"])-1)-base[6])
    need(math.isfinite(logit),"YGG_FINITE")
    return logit,cost


def forward(lane,g,base,delta):
    if lane=="Wingless":
        return wingless_packed(g,base,delta)
    if lane=="Yggdrasil":
        return yggdrasil_cell_credit(g,base,delta)
    raise source.Quarantined("F124S_UNKNOWN_LANE")


def fit_pairs(lane):
    source.frozen()
    cases=[]
    for v in source.VECTORS:
        for seed in source.COHORTS[lane]["FIT"]:
            cases.append(source.build(lane,seed,v,"FIT"))
    need(len(cases)==48,"FIT_48_PAIR_DENOMINATOR")
    return cases


def softplus(x):
    return max(0.,x)+math.log1p(math.exp(-abs(x)))


def loss(lane,pairs,base,d):
    total=0.
    for p,n in pairs:
        a,_=forward(lane,p,base,d)
        b,_=forward(lane,n,base,d)
        total+=softplus(-a)+softplus(b)+.15*softplus(b-a)
    return total/len(pairs)


def train(lane,base):
    need(lane in ("Wingless","Yggdrasil") and len(base)==7,
         "LANE_OR_ORIGINAL_WEIGHT_ERROR")
    pairs=fit_pairs(lane)
    delta=list(WING_INIT if lane=="Wingless" else YGG_INIT)
    init=list(delta)
    rng=random.Random(int.from_bytes(hashlib.sha256(
        ("F124S/FIT/SPSA/v1/"+lane).encode()).digest()[:12],"big"))
    initial_loss=loss(lane,pairs,base,delta)
    steps=0
    for _ in range(EPOCHS):
        ids=list(range(48));rng.shuffle(ids)
        for k in range(0,48,BATCH):
            batch=[pairs[i] for i in ids[k:k+BATCH]]
            signs=[1 if rng.getrandbits(1) else -1 for _ in delta]
            hi=[max(-3.,min(3.,w+PERTURB*s))
                for w,s in zip(delta,signs)]
            lo=[max(-3.,min(3.,w-PERTURB*s))
                for w,s in zip(delta,signs)]
            slope=(loss(lane,batch,base,hi)-loss(lane,batch,base,lo))/(2*PERTURB)
            lr=LR/(1.+.01*steps)
            delta=[max(-3.,min(3.,w-lr*slope*s))
                   for w,s in zip(delta,signs)]
            steps+=1
    magnitude=sum((x-y)**2 for x,y in zip(delta,init))**.5
    need(steps==72 and magnitude>1e-9 and
         all(math.isfinite(v) for v in delta),
         "GENUINE_FIT_UPDATE_GATE")
    return {"lane":lane,"fit_only":True,"delta":delta,
            "delta_sha256":digest(delta),
            "original_base_weight_sha256":original.sha(list(base)),
            "epochs":EPOCHS,"training_steps":steps,"fit_pairs":48,
            "initial_fit_loss":round(initial_loss,8),
            "final_fit_loss":round(loss(lane,pairs,base,delta),8),
            "weight_update_l2":round(magnitude,9),
            "DEV_access_during_train":0,"protected_access_during_train":0}
