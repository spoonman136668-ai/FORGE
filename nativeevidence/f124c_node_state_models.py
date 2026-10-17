"""F124-C genuinely trainable compact node-state causal composition (TRAIN only).

Pure-Python reverse-mode differentiation; 128 learned raw-bit-to-eight embedding
parameters, bilinear token attention and per-node normalized state. A: one slot;
B: two competitive learned slots. Neither enumerates routes or sees the oracle.
The generator's reserved CONFIRM cohorts are not callable through this module.
"""
from __future__ import annotations
import hashlib
import json
import math
import random
import f124c_reconvergent_graph as env

D=8
P_A=132                       # 128 embedding, gate gain, gate bias, output gain, cutoff
P_B=P_A+9                    # two-slot routing prototype (8) and bias
EPOCHS=100
PARAMETER_LIMIT=768

class Tape:
    def __init__(self):
        self.nodes=[]
    def node(self,value,parents=()):
        n=Var(float(value),tuple(parents))
        self.nodes.append(n)
        return n
    def back(self,root,seed):
        root.grad=float(seed)
        for n in reversed(self.nodes):
            if n.grad:
                for p,d in n.parents:
                    p.grad+=n.grad*d

class Var:
    __slots__=("v","parents","grad")
    def __init__(self,value,parents):
        self.v=value;self.parents=parents;self.grad=0.
    def __add__(self,other):
        other=other if isinstance(other,Var) else tape.node(other)
        return tape.node(self.v+other.v,((self,1.),(other,1.)))
    __radd__=__add__
    def __mul__(self,other):
        other=other if isinstance(other,Var) else tape.node(other)
        return tape.node(self.v*other.v,((self,other.v),(other,self.v)))
    __rmul__=__mul__
    def __truediv__(self,other):
        other=other if isinstance(other,Var) else tape.node(other)
        env.require(abs(other.v)>1e-12,"UNSTABLE_NORMALIZER")
        return tape.node(self.v/other.v,((self,1./other.v),(other,-self.v/(other.v*other.v))))
    def __neg__(self):
        return self*(-1.)
    def __sub__(self,other):
        return self+(-other if isinstance(other,Var) else -other)
    def __rsub__(self,other):
        return other+(-self)

# Per-inference local tape. No model-global learning state.
tape=None
def sig(x):
    v=1./(1.+math.exp(-max(-40.,min(40.,x.v))))
    return tape.node(v,((x,v*(1.-v)),))
def tanh(x):
    v=math.tanh(x.v)
    return tape.node(v,((x,1.-v*v),))
def value_hash(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def initial(arm):
    env.require(arm in ("A","B"),"INVALID_MODEL_ARM")
    rng=random.Random(124024)
    params=[rng.uniform(-.72,.72) for _ in range(128)]
    params.extend([1.3,-.6,3.0,.6])
    if arm=="B":
        params.extend([rng.uniform(-.4,.4) for _ in range(D)]+[0.])
    return params

def forward(observation,parameters,arm,gradient_label=None):
    """Returns probability, analytic objective gradient (if requested), diagnostics.
    Dynamic programming keyed ONLY by public node IDs and query role sequence.
    Max 1/2 normalized latent states per node per step; no path traces.
    """
    global tape
    env.validate(observation)
    env.require(arm in ("A","B") and len(parameters)==(P_A if arm=="A" else P_B)
                and all(type(p) in (float,int) and math.isfinite(p) for p in parameters),
                "MODEL_PARAMETER_CONTRACT")
    tape=Tape()
    w=[tape.node(x) for x in parameters]
    cache={}
    stats={"public_edge_scans":0,"gate_sigmoids":0,"prototype_sigmoids":0,
           "embedding_dot_products":0,"peak_state_slots":0,
           "max_incoming_messages":0,"slot_mass":[0.,0.],
           "bit_multiply_adds_proxy":0}
    def embed(bs):
        key=tuple(bs)
        if key not in cache:
            v=[]
            for j in range(D):
                z=tape.node(0.)
                for k in range(16):
                    z=z+w[j*16+k]*((2*bs[k]-1)/4.)
                v.append(tanh(z))
            cache[key]=v
        return cache[key]
    # Entries are (mass, 8-value latent) associated with each node, never path ID.
    states={observation["start"]:[(tape.node(1.),None)]}
    for step,role in enumerate(observation["roles"]):
        incoming={}
        nmessages=0
        for node,slots in states.items():
            for e in observation["edges"]:
                stats["public_edge_scans"]+=1
                if e["from"]!=node or e["role"]!=role: continue
                for mass,latent in slots:
                    carrier=embed(e["dst_bits"])
                    if latent is None:
                        link=tape.node(1.)
                    else:
                        src=embed(e["src_bits"])
                        compatibility=tape.node(0.)
                        for i in range(D): compatibility=compatibility+latent[i]*src[i]
                        link=sig(w[128]*(compatibility*(1./D))+w[129])
                        stats["gate_sigmoids"]+=1
                        stats["embedding_dot_products"]+=1
                        stats["bit_multiply_adds_proxy"]+=D
                    matched_mass=mass*link
                    if arm=="A":
                        dest=[(0,tape.node(1.))]
                    else:
                        g=tape.node(0.)
                        for k in range(D):g=g+carrier[k]*w[P_A+k]
                        preference=sig(g*(1./D)+w[P_B-1])
                        stats["prototype_sigmoids"]+=1
                        dest=[(0,preference),(1,tape.node(1.)-preference)]
                    for target_slot,routing in dest:
                        transported=matched_mass*routing
                        key=(e["to"],target_slot)
                        if key not in incoming: incoming[key]=[]
                        incoming[key].append((transported,carrier))
                        nmessages+=1
                        env.require(nmessages<=128,"ACTIVATION_BUDGET_EXCEEDED")
        states={}
        for (node,slot),messages in sorted(incoming.items()):
            total=tape.node(0.)
            summed=[tape.node(0.) for _ in range(D)]
            for mass,latent in messages:
                total=total+mass
                for j in range(D):summed[j]=summed[j]+mass*latent[j]
            mean=[s/(total+tape.node(1e-5)) for s in summed]
            if node not in states: states[node]=[]
            states[node].append((total,mean))
            if step==len(observation["roles"])-1:
                stats["slot_mass"][slot]+=total.v
        stats["peak_state_slots"]=max(stats["peak_state_slots"],
                                      sum(len(v) for v in states.values()))
        stats["max_incoming_messages"]=max(stats["max_incoming_messages"],nmessages)
        env.require(stats["peak_state_slots"]<=128,"NODE_STATE_BUDGET_EXCEEDED")
    mass=tape.node(0.)
    for m,_ in states.get(observation["target"],[]):mass=mass+m
    logit=w[130]*(mass-w[131])
    prob=1./(1.+math.exp(-max(-40.,min(40.,logit.v))))
    env.require(math.isfinite(prob) and stats["peak_state_slots"]<=128,
                "NONFINITE_FORWARD")
    grads=None
    if gradient_label is not None:
        env.require(gradient_label in (0,1) and type(gradient_label) is int,
                    "INVALID_TRAIN_LABEL")
        tape.back(logit,prob-gradient_label)
        grads=[v.grad for v in w]
        env.require(len(grads)==len(parameters) and all(math.isfinite(v) for v in grads),
                    "NONFINITE_GRADIENT")
    stats["terminal_mass"]=round(mass.v,8)
    stats["score"]=round(prob,8)
    return prob,grads,stats

def train(lane,vectors,arm):
    env.frozen()
    env.require(lane in env.TRAIN and arm in ("A","B") and
                type(vectors) is list and len(vectors)==2 and vectors[0]!=vectors[1] and
                all(type(v) is list and len(v)==3 and
                    all(type(n) is int and 0<=n<=3 for n in v) for v in vectors),
                "TRAIN_ONLY_VECTOR_QUALIFICATION")
    rows=[]
    for v in vectors:
        for seed in env.TRAIN[lane]:
            pos,neg=env.build(seed,v,lane,"TRAIN")
            rows.append((pos,neg))
    env.require(len(rows)==48,"COHORT_DRIFT")
    weights=initial(arm)
    before=weights[:]
    for epoch in range(EPOCHS):
        grads=[0.]*len(weights)
        # Fixed rotating TRAIN minibatch; no confirmation or adaptive early stop.
        for j in range(4):
            pos,neg=rows[(epoch*4+j)%48]
            for obs,label in ((pos,1),(neg,0)):
                _,d,_=forward(obs,weights,arm,label)
                for k,g in enumerate(d):grads[k]+=g
        rate=.20
        for k,g in enumerate(grads):
            v=max(-1.5,min(1.5,g/8.))
            weights[k]=max(-6.,min(6.,weights[k]-rate*v))
    movement=math.sqrt(sum((a-b)**2 for a,b in zip(before,weights)))
    env.require(len(weights)<=PARAMETER_LIMIT and movement>1e-5 and
                all(math.isfinite(x) for x in weights),
                "PARAMETER_UPDATE_OR_BUDGET_FAILURE")
    paircorrect=tp=tn=0
    masses=[]
    for pos,neg in rows:
        pp,_,sp=forward(pos,weights,arm)
        pn,_,sn=forward(neg,weights,arm)
        goodp=pp>=.5;goodn=pn<.5
        paircorrect+=int(goodp and goodn)
        tp+=int(goodp);tn+=int(goodn)
        masses.append((sp["slot_mass"],sn["slot_mass"]))
    return {"lane":lane,"arm":arm,"phase":"TRAIN_ONLY",
            "train_pairs":48,"train_selection_eligible":True,
            "parameters":len(weights),"epochs":EPOCHS,
            "trained_weight_sha256":value_hash(weights),
            "train_pairs_correct":paircorrect,"positive_correct":tp,
            "negative_correct":tn,
            "movement":round(movement,9),
            "weights":weights,"terminal_slot_mass":masses,
            "training_source_sha256":value_hash(vectors),
            "confirmation_examples_generated":0,
            "scientific_acceptances":0,"optimizer_promotions":0}

def train_lanes(vectors_by_lane):
    env.require(type(vectors_by_lane) is dict and set(vectors_by_lane)==set(env.TRAIN),
                "MISSING_INDEPENDENT_LANES")
    out=[]
    for lane in ("Wingless","Yggdrasil"):
        arms={a:train(lane,vectors_by_lane[lane],a) for a in ("A","B")}
        selected=max(("A","B"),key=lambda a:(arms[a]["train_pairs_correct"],a=="A"))
        out.append({"lane":lane,"selection":"TRAIN_ONLY","selected_arm":selected,
                    "selected_weight_sha256":arms[selected]["trained_weight_sha256"],
                    "arms":arms,"confirmation_examples_generated":0})
    return {"schema":"forge.research.f124c.train-learned-node-state.v1",
            "freeze_git_blob":env.FREEZE_BLOB,
            "lanes":out,"phase":"TRAIN_ONLY","confirmation_examples_generated":0,
            "scientific_first_use":False,"scientific_acceptances":0,
            "optimizer_promotions":0}
