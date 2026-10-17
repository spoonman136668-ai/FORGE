"""F124-D two-slot mass-conserving competitive causal state (TRAIN ONLY).

New mechanism, NOT an F124-C threshold retune. Uses the previously qualified
F124-C reverse-mode autodiff *utility*, not its node-state propagation. Public
raw graph input only; no enumerated paths, equality bit or changed-route oracle.
"""
from __future__ import annotations
import hashlib
import json
import math
import random
from pathlib import Path
import f124d_reconvergent_source as env
import f124c_node_state_models as autodiff

WIDTH=8
P_A=148
P_B=149
EPOCHS=100
MAX_PARAMS=768
AUTODIFF_BLOB="76653b7877cbdc092f12a96e4140a38b381bbddf"

def contract():
    env.frozen()
    blob=env.git_blob(Path(autodiff.__file__).read_bytes().replace(b"\r\n",b"\n"))
    env.require(blob==AUTODIFF_BLOB,"REVERSE_AUTODIFF_FOUNDATION_DRIFT")
    return True

def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def initialize(arm):
    env.require(arm in ("A","B"),"UNKNOWN_COMPETITION_ARM")
    rand=random.Random(124026)
    embed=[rand.uniform(-.65,.65) for _ in range(128)]
    # Raw bit encoder + compatibility scale, compatibility bias,
    # binary head gain, per-hop log-mass offset.
    w=embed+[1.3,-.45,2.1,-.8]
    # Separate prototype directions encourage differentiated persistent slots.
    p0=[rand.uniform(-.65,.65) for _ in range(WIDTH)]
    p1=[-v for v in p0]
    w+=p0+p1
    if arm=="B":w.append(0.0)  # sigmoid residual gate
    env.require(len(w)==(P_A if arm=="A" else P_B),"PARAMETER_SHAPE")
    return w

def _softmax(xs,counters):
    env.require(len(xs)>0,"EMPTY_COMPETITIVE_ALLOCATION")
    detached=max(x.v for x in xs)
    exps=[]
    for x in xs:
        v=math.exp(max(-40.,min(40.,x.v-detached)))
        exps.append(autodiff.tape.node(v,((x,v),)))
        counters["exp_evaluations"]+=1
    total=sum(exps,autodiff.tape.node(0.))
    return [x/total for x in exps]

def _log(x):
    env.require(x.v>0.,"INVALID_LOG_MASS")
    return autodiff.tape.node(math.log(x.v),((x,1./x.v),))

def _public_edge_sort(e):
    return (e["from"],e["to"],e["role"],
            tuple(e["src_bits"]),tuple(e["dst_bits"]))

def forward(graph,weights,arm,backseed=None):
    """Return p, logit, analytic gradient if seeded, and public resource costs."""
    env.validate(graph)
    env.require(arm in ("A","B") and len(weights)==(P_A if arm=="A" else P_B)
                and all(type(v) in (int,float) and math.isfinite(v) for v in weights),
                "NONFINITE_OR_WRONG_MODEL_WEIGHTS")
    autodiff.tape=autodiff.Tape()
    tape=autodiff.tape
    w=[tape.node(x) for x in weights]
    edges=sorted(graph["edges"],key=_public_edge_sort)
    embed_cache={}
    stats={"edge_scans":0,"raw_bit_mult_adds":0,"latent_mult_adds":0,
           "sigmoid_evaluations":0,"exp_evaluations":0,
           "max_live_messages":0,"peak_state_slots":0,
           "max_mass_conservation_excess":0.,"per_hop_total_mass":[],
           "last_slot_masses":[0.,0.],"distinct_slot_masses":[0.,0.]}

    def emb(bits):
        key=tuple(bits)
        if key not in embed_cache:
            vec=[]
            for j in range(WIDTH):
                z=tape.node(0.)
                for k in range(16):
                    z=z+w[j*16+k]*((2*bits[k]-1)/4.)
                    stats["raw_bit_mult_adds"]+=1
                vec.append(autodiff.tanh(z))
            embed_cache[key]=vec
        return embed_cache[key]

    def dot(a,b):
        z=tape.node(0.)
        for x,y in zip(a,b):z=z+x*y;stats["latent_mult_adds"]+=1
        return z*(1./WIDTH)

    # Each node maintains AT MOST two compressed memories, no path identities.
    states={graph["start"]:{0:(tape.node(1.),None)}}
    total_last=1.
    for step,role in enumerate(graph["roles"]):
        messages={}
        n=0
        for node in sorted(states):
            available=[]
            for e in edges:
                stats["edge_scans"]+=1
                if e["from"]==node and e["role"]==role:
                    available.append(e)
            for slot,(mass,latent) in sorted(states[node].items()):
                if not available:continue
                if latent is None:
                    scores=[tape.node(0.) for _ in available]
                    survive=[tape.node(1.) for _ in available]
                else:
                    scores=[w[128]*dot(latent,emb(e["src_bits"]))+w[129]
                            for e in available]
                    survive=[autodiff.sig(z) for z in scores]
                    stats["sigmoid_evaluations"]+=len(scores)
                edge_probs=_softmax(scores,stats)
                for e,pedge,gate in zip(available,edge_probs,survive):
                    src_mass=mass*pedge*gate
                    dest=emb(e["dst_bits"])
                    assignment=_softmax([dot(dest,w[132:140]),
                                         dot(dest,w[140:148])],stats)
                    if arm=="B":
                        residual=autodiff.sig(w[148])
                        stats["sigmoid_evaluations"]+=1
                        assignment=[assignment[k]*(1.-residual)+residual*(1. if slot==k else 0.)
                                    for k in range(2)]
                    for k in range(2):
                        transported=src_mass*assignment[k]
                        messages.setdefault((e["to"],k),[]).append((transported,dest))
                        n+=1
                        env.require(n<=128,"SOURCE_ACTIVATION_BUDGET")
        states={}
        for (target,slot),items in sorted(messages.items()):
            mass=sum((x[0] for x in items),tape.node(0.))
            average=[]
            for j in range(WIDTH):
                value=sum((m*v[j] for m,v in items),tape.node(0.))
                average.append(value/(mass+1e-5))
            states.setdefault(target,{})[slot]=(mass,average)
        current=sum(m.v for slots in states.values() for m,_ in slots.values())
        excess=max(0.,current-total_last)
        stats["max_mass_conservation_excess"]=max(
            stats["max_mass_conservation_excess"],excess)
        env.require(excess<1e-9,"PUBLIC_MESSAGE_MASS_CREATED")
        stats["per_hop_total_mass"].append(round(current,12))
        total_last=current
        stats["peak_state_slots"]=max(stats["peak_state_slots"],
                                       sum(len(s) for s in states.values()))
        stats["max_live_messages"]=max(stats["max_live_messages"],n)
        env.require(stats["peak_state_slots"]<=128,"NODE_STATE_BUDGET")
    target=states.get(graph["target"],{})
    total=sum((m for m,_ in target.values()),tape.node(0.))
    for slot,(mass,_) in target.items():
        stats["last_slot_masses"][slot]=mass.v
    logmass=_log(total+1e-6)*(1./len(graph["roles"]))
    logit=w[130]*(logmass-w[131])
    p=autodiff.sig(logit).v
    stats["sigmoid_evaluations"]+=1
    grads=None
    if backseed is not None:
        env.require(type(backseed) in (int,float) and math.isfinite(backseed),
                    "BACKWARD_SEED_INVALID")
        tape.back(logit,backseed)
        grads=[param.grad for param in w]
        env.require(all(math.isfinite(x) for x in grads),"NONFINITE_GRADIENT")
    stats["parameters"]=len(w)
    stats["live_node_states_at_exit"]=len(states)
    return p,logit.v,grads,stats

def train(lane,vectors,arm):
    contract()
    env.require(lane in env.TRAIN and arm in ("A","B")
                and type(vectors) is list and len(vectors)==2 and vectors[0]!=vectors[1]
                and all(type(v) is list and len(v)==3 and
                        all(type(x) is int and x in (0,1,2,3) for x in v)
                        for v in vectors),"TRAIN_ONLY_VECTOR_COHORT")
    pairs=[env.build(seed,v,lane,"TRAIN")
           for v in vectors for seed in env.TRAIN[lane]]
    env.require(len(pairs)==48,"TRAIN_SOURCE_SIZE")
    weights=initialize(arm);before=list(weights)
    for epoch in range(EPOCHS):
        gradients=[0.]*len(weights)
        for j in range(4):
            pos,neg=pairs[(epoch*4+j)%48]
            yp,lp,_,_=forward(pos,weights,arm)
            yn,ln,_,_=forward(neg,weights,arm)
            # Frozen 0.5 BCE + 0.5 softplus(- (positive logit - negative logit)).
            rank=1./(1.+math.exp(max(-40.,min(40.,lp-ln))))
            positive_seed=.5*(yp-1.)-.5*rank
            negative_seed=.5*yn+.5*rank
            _,_,gp,_=forward(pos,weights,arm,positive_seed)
            _,_,gn,_=forward(neg,weights,arm,negative_seed)
            for k in range(len(weights)):gradients[k]+=gp[k]+gn[k]
        if arm=="B":
            # 0.03 squared, normalized dot-product prototype-overlap penalty.
            dot=sum(weights[132+k]*weights[140+k] for k in range(WIDTH))/WIDTH
            for k in range(WIDTH):
                gradients[132+k]+=4.*.03*dot*weights[140+k]/WIDTH
                gradients[140+k]+=4.*.03*dot*weights[132+k]/WIDTH
        for k,g in enumerate(gradients):
            delta=max(-1.5,min(1.5,g/8.))
            weights[k]=max(-6.,min(6.,weights[k]-.20*delta))
    moved=math.sqrt(sum((x-y)**2 for x,y in zip(before,weights)))
    env.require(moved>1e-5 and len(weights)<=MAX_PARAMS
                and all(math.isfinite(x) for x in weights),"TRAINED_MECHANISM_INVALID")
    paired=tp=tn=ranked=0
    min_ratio=[]
    totals=[]
    for pos,neg in pairs:
        yp,lp,_,ps=forward(pos,weights,arm)
        yn,ln,_,ns=forward(neg,weights,arm)
        tp+=int(yp>=.5);tn+=int(yn<.5)
        paired+=int(yp>=.5 and yn<.5)
        ranked+=int(lp>ln)
        for stat in (ps,ns):
            masses=stat["last_slot_masses"]
            if max(masses)>0:min_ratio.append(min(masses)/max(masses))
            totals.append(stat["max_mass_conservation_excess"])
    return {"lane":lane,"arm":arm,"phase":"TRAIN_ONLY",
            "training_epochs":EPOCHS,"train_pairs":48,
            "parameters":len(weights),"updates_l2":round(moved,10),
            "train_paired_correct":paired,"positive_correct":tp,
            "negative_correct":tn,"train_rank_higher":ranked,
            "mean_minor_slot_ratio":round(sum(min_ratio)/len(min_ratio),10),
            "max_mass_conservation_excess":max(totals),
            "weight_sha256":sha(weights),"weights":weights,
            "source_vector_sha256":sha(vectors),
            "confirm_generated":0,"original_scientific_first_use":False,
            "scientific_acceptances":0,"optimizer_promotions":0}
