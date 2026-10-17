"""F124-F query-conditioned three-record learned causal retrieval, TRAIN only.

Distinct from F124-E: preserve public raw 16-bit carried keys individually;
before bounded eviction, rank keys against the *next public role's* outgoing
source slots rather than prioritizing historical mass alone. Model uses a
trainable raw pair compatibility and hop-normalized signed log-evidence head.
No route oracle, engineered binary equality bit or path label enters forward.
"""
from __future__ import annotations
import hashlib
import json
import math
import random
from pathlib import Path

import f124f_public_graph_source as graph
import f124c_node_state_models as autodiff

SLOTS=3
PA=19
PB=20
EPOCHS=100
AUTO_BLOB="76653b7877cbdc092f12a96e4140a38b381bbddf"

def require(test,code):
    graph.require(test,"MODEL_"+code)

def contract():
    graph.frozen()
    raw=Path(autodiff.__file__).read_bytes().replace(b"\r\n",b"\n")
    require(graph.git_blob(raw)==AUTO_BLOB,"AUTODIFF_FOUNDATION_IDENTITY")
    return True

def sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def initial(arm):
    require(arm in ("A","B"),"INVALID_ARM")
    rng=random.Random(12402602)
    # Each bit has an independently learned match importance; bitwise products
    # are computed by the architecture, never given as an oracle input.
    values=[rng.uniform(.30,.65) for _ in range(16)]
    values.extend([-1.0,7.0,-0.4])
    if arm=="B":
        values.append(.7)  # trainable soft novelty/record gate
    require(len(values)==(PA if arm=="A" else PB),"MODEL_SHAPE")
    return values

def _sigmoid(x):
    return autodiff.sig(x)

def _log(x):
    require(x.v>0,"LOG_DOMAIN")
    return autodiff.tape.node(math.log(x.v),((x,1./x.v),))

def _ekey(e):
    return (e["from"],e["to"],e["role"],tuple(e["src_bits"]),tuple(e["dst_bits"]))

def forward(obs,values,arm,train_seed=None,query_priority=True):
    """Return probability, pre-sigmoid logit, gradients, and work witnesses.

    TRAIN diagnostic ablation query_priority=False is NEVER selectable as a
    scientific arm; it is exposed only to independently evaluate the mechanism.
    """
    graph.validate(obs)
    require(arm in ("A","B") and type(values) is list and
            len(values)==(PA if arm=="A" else PB) and
            all(type(v) in (int,float) and math.isfinite(v) for v in values) and
            type(query_priority) is bool,
            "WEIGHT_OR_PUBLIC_INPUT_CONTRACT")
    autodiff.tape=autodiff.Tape()
    tape=autodiff.tape
    w=[tape.node(x) for x in values]
    edges=sorted(obs["edges"],key=_ekey)
    lookups={}
    for role in obs["roles"]:
        for edge in edges:
            if edge["role"]==role:
                lookups.setdefault((edge["from"],role),[]).append(edge["src_bits"])
    work={"public_edge_scans":0,"raw_bit_multiply_adds":0,
          "sigmoids":0,"peak_key_records":0,"max_messages_per_hop":0,
          "evicted_records":0,"query_eligible_evictions":0,
          "terminal_records":0,"depth":len(obs["roles"])}
    def agreement(key,query):
        z=w[16]
        for i,(a,b) in enumerate(zip(key,query)):
            z=z+w[i]*((2*a-1)*(2*b-1))/16.
            work["raw_bit_multiply_adds"]+=1
        return z

    states={obs["start"]:[(tape.node(1.),None)]}
    for index,role in enumerate(obs["roles"]):
        incoming={}
        count=0
        for node in sorted(states):
            eligible=[e for e in edges if e["from"]==node and e["role"]==role]
            for mass,key in states[node]:
                work["public_edge_scans"]+=len(edges)
                for edge in eligible:
                    if key is None: gate=tape.node(1.)
                    else:
                        gate=_sigmoid(agreement(key,edge["src_bits"]))
                        work["sigmoids"]+=1
                    nextmass=mass*gate
                    raw=tuple(edge["dst_bits"])
                    incoming.setdefault(edge["to"],[]).append(
                       (nextmass,raw,_ekey(edge)))
                    count+=1
                    require(count<=128,"MAX_MESSAGE_ACTIVATIONS")
        states={}
        nextrole=obs["roles"][index+1] if index+1<len(obs["roles"]) else None
        for node in sorted(incoming):
            candidates=[]
            for mass,key,public_edge in incoming[node]:
                nextqueries=lookups.get((node,nextrole),[]) if nextrole else []
                # The public next role provides a *query*, not a chosen route.
                if query_priority and nextqueries:
                    score=max(agreement(key,q).v for q in nextqueries)
                else:score=0.
                candidate_priority=(score,mass.v,public_edge,key)
                candidates.append((candidate_priority,mass,key))
            # Selection is bounded, deterministic and explicitly nondifferentiable.
            # Same sort and capacity for both arms, including public multiedges.
            candidates.sort(key=lambda x:(-x[0][0],-x[0][1],x[0][2],x[0][3]))
            records=[]
            for priority,mass,key in candidates:
                if arm=="B":
                    if records:
                        novelty=min(sum(a!=b for a,b in zip(key,other_key))/16.
                                    for _,other_key in records)
                    else:novelty=1.
                    # Differentiable penalty for duplicate/aliased keys.
                    gate=_sigmoid(w[19]*(novelty-.25))
                    work["sigmoids"]+=1
                    mass=mass*gate
                records.append((mass,key))
                if len(records)==SLOTS:break
            work["evicted_records"]+=max(0,len(candidates)-SLOTS)
            work["query_eligible_evictions"]+=sum(
                int(bool(lookups.get((node,nextrole),[]))) for _ in
                candidates[SLOTS:]) if nextrole else 0
            states[node]=records
        work["max_messages_per_hop"]=max(work["max_messages_per_hop"],count)
        work["peak_key_records"]=max(work["peak_key_records"],
                                    sum(len(x) for x in states.values()))
        require(work["peak_key_records"]<=128,"MAX_MEMORY_RECORDS")
    terminal=states.get(obs["target"],[])
    work["terminal_records"]=len(terminal)
    total=sum((mass for mass,_ in terminal),tape.node(0.))
    # Signed depth-normalized log-likelihood of reaching public target.
    # This avoids using an unnormalized accumulated state as a classifier.
    signed=_log(total+tape.node(1e-6))*(1./len(obs["roles"]))
    logit=w[17]*(signed-w[18])
    prob=_sigmoid(logit).v
    work["sigmoids"]+=1
    require(math.isfinite(prob) and 0.<=prob<=1.,"NONFINITE_INFERENCE")
    grads=None
    if train_seed is not None:
        require(type(train_seed) in (float,int) and math.isfinite(train_seed),
                "INVALID_BCE_SEED")
        tape.back(logit,train_seed)
        grads=[p.grad for p in w]
        require(all(math.isfinite(g) for g in grads),"NONFINITE_GRADIENT")
    return prob,logit.v,grads,work

def train(lane,vectors,arm):
    contract()
    require(lane in graph.TRAIN and arm in ("A","B")
            and type(vectors) is list and len(vectors)==2 and vectors[0]!=vectors[1]
            and all(type(v) is list and len(v)==3 and
                    all(type(x) is int and 0<=x<=3 for x in v) for v in vectors),
            "TRAIN_ONLY_VECTOR_AUTHORITY")
    pairs=[graph.build(seed,v,lane,"TRAIN") for v in vectors
           for seed in graph.TRAIN[lane]]
    require(len(pairs)==48,"TRAIN_SIZE")
    weights=initial(arm);original=list(weights)
    for epoch in range(EPOCHS):
        gradients=[0.]*len(weights)
        for j in range(4):
            pos,neg=pairs[(epoch*4+j)%48]
            pp,lp,_,_=forward(pos,weights,arm)
            pn,ln,_,_=forward(neg,weights,arm)
            rank=1./(1.+math.exp(max(-40.,min(40.,lp-ln))))
            _,_,pg,_=forward(pos,weights,arm,.5*(pp-1.)-.5*rank)
            _,_,ng,_=forward(neg,weights,arm,.5*pn+.5*rank)
            for k in range(len(weights)):gradients[k]+=pg[k]+ng[k]
        for k,g in enumerate(gradients):
            weights[k]=max(-6.,min(6.,weights[k]-.20*max(-1.5,min(1.5,g/8.))))
    change=math.sqrt(sum((a-b)**2 for a,b in zip(weights,original)))
    require(change>1e-6 and all(math.isfinite(x) for x in weights),
            "UNTRAINED_OR_NONFINITE_MODEL")
    tp=tn=paired=ranked=0
    total_costs={"public_edge_scans":0,"raw_bit_multiply_adds":0,
                 "sigmoids":0,"evicted_records":0}
    depth={"4":{"pairs":0,"correct":0},"5":{"pairs":0,"correct":0}}
    for pos,neg in pairs:
        yes,yl,_,cost=forward(pos,weights,arm)
        no,nl,_,_=forward(neg,weights,arm)
        good=yes>=.5 and no<.5
        paired+=int(good);tp+=int(yes>=.5);tn+=int(no<.5)
        ranked+=int(yl>nl)
        d=str(len(pos["roles"]))
        depth[d]["pairs"]+=1;depth[d]["correct"]+=int(good)
        for k in total_costs:total_costs[k]+=cost[k]
    return {"lane":lane,"arm":arm,"phase":"TRAIN_ONLY",
            "training_epochs":EPOCHS,"paired_examples":48,
            "parameters":len(weights),"weight_sha256":sha(weights),
            "update_l2":round(change,10),
            "train_paired_correct":paired,"train_positive_correct":tp,
            "train_negative_correct":tn,"ranked_positive_higher":ranked,
            "depth_strata":depth,"training_vectors_sha256":sha(vectors),
            "weights":weights,"resource_counts":total_costs,
            "confirmation_examples":0,"scientific_first_use":False,
            "optimizer_promotions":0}
