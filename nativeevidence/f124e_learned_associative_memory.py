"""F124-E learned associative key-value addressing (TRAIN-only).

Unlike F124-C/D node averages, each state is an individual latent KEY and
scalar route VALUE/mass. At a join, keep at most three distinct records per
node; outgoing edges query those records by trainable raw-token similarity.
No path identity, oracle equality bit, or preselected source edge is given.
Hard capacity selection is identified as a non-differentiable design limit.
"""
from __future__ import annotations
import hashlib
import json
import math
import random
from pathlib import Path
import f124e_key_value_environment as source
import f124c_node_state_models as ad

WIDTH=8
SLOTS=3
PARAM_A=132
PARAM_B=156
EPOCHS=100
FOUNDATION_BLOB="76653b7877cbdc092f12a96e4140a38b381bbddf"

def contract():
    source.frozen()
    raw=Path(ad.__file__).read_bytes().replace(b"\r\n",b"\n")
    source.require(source.git_blob(raw)==FOUNDATION_BLOB,
                   "EXACT_AUTODIFF_FOUNDATION_IDENTITY")
    return True

def identity(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def initial(arm):
    source.require(arm in ("A","B"),"UNKNOWN_ARM")
    rng=random.Random(124025)
    w=[rng.uniform(-.65,.65) for _ in range(16*WIDTH)]
    w.extend([2.4,-.8,6.,.12])
    if arm=="B":
        w.extend(rng.uniform(-.55,.55) for _ in range(3*WIDTH))
    source.require(len(w)==(PARAM_A if arm=="A" else PARAM_B),"PARAMETER_LENGTH")
    return w

def forward(graph,weights,arm,seed=None):
    """Evaluate bounded associative key/value state on public graph only.

    Returns (prob, logit, gradients when seeded, work). A record carries an
    individually encoded raw VALUE as the next-hop retrieval KEY, plus a
    differentiable confidence. Full paths are never enumerated in the model.
    """
    source.validate(graph)
    source.require(arm in ("A","B") and
                   len(weights)==(PARAM_A if arm=="A" else PARAM_B) and
                   all(type(v) in (int,float) and math.isfinite(v) for v in weights),
                   "MODEL_WEIGHTS_INVALID")
    ad.tape=ad.Tape()
    tape=ad.tape
    w=[tape.node(v) for v in weights]
    edges=sorted(graph["edges"],key=lambda e:(e["from"],e["to"],e["role"],
                                                tuple(e["src_bits"]),tuple(e["dst_bits"])))
    memo={}
    costs={"public_edge_scans":0,"raw_bit_multiply_adds":0,
           "latent_multiply_adds":0,"sigmoid_evaluations":0,
           "peak_key_value_records":0,"messages":0,
           "key_capacity_drops":0,"terminal_record_count":0}
    def raw_embed(bits):
        key=tuple(bits)
        if key not in memo:
            result=[]
            for j in range(WIDTH):
                v=tape.node(0.)
                for k in range(16):
                    v=v+w[j*16+k]*((2*bits[k]-1)/4.)
                    costs["raw_bit_multiply_adds"]+=1
                result.append(ad.tanh(v))
            memo[key]=result
        return memo[key]
    def dot(a,b):
        s=tape.node(0.)
        for x,y in zip(a,b):
            s=s+x*y
            costs["latent_multiply_adds"]+=1
        return s*(1./WIDTH)
    def select(available):
        # An explicit *public* bounded memory: three records at most, selected
        # by learned mass/assignment score, not preselected path/oracle truth.
        ranked=[]
        for mass,key,public_id in available:
            if arm=="A": salience=mass
            else:
                protos=[w[132+i*WIDTH:132+(i+1)*WIDTH] for i in range(SLOTS)]
                raw=[dot(key,p) for p in protos]
                largest=max(x.v for x in raw)
                exps=[math.exp(max(-40.,min(40.,x.v-largest))) for x in raw]
                pref=max(exps)/sum(exps)
                salience=mass*pref
            ranked.append((salience.v,public_id,mass,key))
        ranked.sort(key=lambda x:(-x[0],x[1]))
        if len(ranked)>SLOTS:
            costs["key_capacity_drops"]+=len(ranked)-SLOTS
        return [(r[2],r[3]) for r in ranked[:SLOTS]]
    # One initial empty key/value record at start, then at most three keyed
    # records per node; every record is a *single retained value*, never mean.
    states={graph["start"]:[(tape.node(1.),None)]}
    for step,role in enumerate(graph["roles"]):
        incoming={}
        nmessages=0
        for node in sorted(states):
            local=[e for e in edges if e["from"]==node and e["role"]==role]
            for mass,latent in states[node]:
                costs["public_edge_scans"]+=len(edges)
                for e in local:
                    if latent is None:
                        gate=tape.node(1.)
                    else:
                        compat=w[128]*dot(latent,raw_embed(e["src_bits"]))+w[129]
                        gate=ad.sig(compat)
                        costs["sigmoid_evaluations"]+=1
                    key=raw_embed(e["dst_bits"])
                    after=mass*gate
                    public_id=(e["from"],e["to"],e["role"],
                               tuple(e["src_bits"]),tuple(e["dst_bits"]))
                    incoming.setdefault(e["to"],[]).append((after,key,public_id))
                    nmessages+=1
                    costs["messages"]+=1
                    source.require(nmessages<=128,"MESSAGE_BUDGET")
        states={node:select(incoming[node]) for node in sorted(incoming)}
        costs["peak_key_value_records"]=max(costs["peak_key_value_records"],
                                             sum(len(s) for s in states.values()))
        source.require(costs["peak_key_value_records"]<=128,"MEMORY_BUDGET")
    terminal=states.get(graph["target"],[])
    mass=sum((item[0] for item in terminal),tape.node(0.))
    costs["terminal_record_count"]=len(terminal)
    logit=w[130]*(mass-w[131])
    prob=ad.sig(logit).v
    costs["sigmoid_evaluations"]+=1
    gradient=None
    if seed is not None:
        source.require(type(seed) in (float,int) and math.isfinite(seed),
                       "NONFINITE_OR_INVALID_TRAIN_SEED")
        tape.back(logit,seed)
        gradient=[p.grad for p in w]
        source.require(all(math.isfinite(x) for x in gradient),"NONFINITE_GRADIENT")
    source.require(0<=prob<=1 and math.isfinite(logit.v),"NONFINITE_PREDICTION")
    return prob,logit.v,gradient,costs

def train(lane,vectors,arm):
    contract()
    source.require(lane in source.TRAIN and arm in ("A","B") and
                   type(vectors) is list and len(vectors)==2 and
                   vectors[0]!=vectors[1] and all(type(v) is list and len(v)==3 and
                   all(type(x) is int and 0<=x<=3 for x in v) for v in vectors),
                   "TRAIN_ONLY_CANDIDATES")
    pairs=[source.build(seed,vector,lane,"TRAIN")
           for vector in vectors for seed in source.TRAIN[lane]]
    source.require(len(pairs)==48,"TRAIN_COHORT_DRIFT")
    weights=initial(arm)
    before=list(weights)
    for epoch in range(EPOCHS):
        grads=[0.]*len(weights)
        for j in range(4):
            pos,neg=pairs[(epoch*4+j)%48]
            yes,yeslog,_,_=forward(pos,weights,arm)
            no,nolog,_,_=forward(neg,weights,arm)
            rank=1./(1.+math.exp(max(-40.,min(40.,yeslog-nolog))))
            _,_,gp,_=forward(pos,weights,arm,.5*(yes-1.)-.5*rank)
            _,_,gn,_=forward(neg,weights,arm,.5*no+.5*rank)
            for k in range(len(grads)):
                grads[k]+=gp[k]+gn[k]
        if arm=="B":
            # B frozen 0.03 pairwise prototype overlap penalty. A has none.
            for i in range(SLOTS):
                for j in range(i+1,SLOTS):
                    overlap=sum(weights[132+i*WIDTH+k]*weights[132+j*WIDTH+k]
                                for k in range(WIDTH))/WIDTH
                    for k in range(WIDTH):
                        grads[132+i*WIDTH+k]+=.03*overlap*weights[132+j*WIDTH+k]/WIDTH
                        grads[132+j*WIDTH+k]+=.03*overlap*weights[132+i*WIDTH+k]/WIDTH
        for k,g in enumerate(grads):
            clipped=max(-1.5,min(1.5,g/8.))
            weights[k]=max(-6.,min(6.,weights[k]-.2*clipped))
    displacement=math.sqrt(sum((a-b)**2 for a,b in zip(before,weights)))
    source.require(displacement>1e-5 and all(math.isfinite(x) for x in weights),
                   "NO_LEARNING_OR_NONFINITE_WEIGHT")
    paired=tp=tn=ranked=0
    cost=[]
    for pos,neg in pairs:
        yes,yl,_,work=forward(pos,weights,arm)
        no,nl,_,_=forward(neg,weights,arm)
        paired+=int(yes>=.5 and no<.5)
        tp+=int(yes>=.5);tn+=int(no<.5)
        ranked+=int(yl>nl)
        cost.append(work)
    return {"lane":lane,"arm":arm,"phase":"TRAIN_ONLY",
            "parameter_count":len(weights),"epochs":EPOCHS,"train_pairs":48,
            "trained_weight_sha256":identity(weights),
            "training_displacement_l2":round(displacement,10),
            "train_paired_correct":paired,"train_positive_correct":tp,
            "train_negative_correct":tn,"train_positive_rank_higher":ranked,
            "weights":weights,"mean_key_capacity_drops":round(sum(x["key_capacity_drops"] for x in cost)/48,8),
            "mean_memory_slots":round(sum(x["peak_key_value_records"] for x in cost)/48,8),
            "mean_edge_scans":round(sum(x["public_edge_scans"] for x in cost)/48,8),
            "mean_bit_mac":round(sum(x["raw_bit_multiply_adds"] for x in cost)/48,8),
            "confirm_generated":0,"first_use":False,"science_accepted":False}
