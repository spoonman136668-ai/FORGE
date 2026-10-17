"""F124-R sparse two-state per-hop learned router; TRAIN only.

Hard deterministic K=2 beam uses raw query-conditioned 16-bit token features.
Pruning is part of the differentiable selected-path forward (piecewise derivative).
No oracle equality bit, truth coordinate, held-out case or original F123 weight
appears as an input. Research negatives are preserved, never hidden.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
import math

import f124r_train_environment as env
import f124r_freeze_admission as freeze

PARAMETERS = 20
K = 2
EPOCHS = 100
RATE = .22
MAX_CANDIDATES = 128

def require(ok, code):
    env.require(ok, "MODEL_" + code)

def sigmoid(x):
    return 1 / (1 + math.exp(-max(-40., min(40., x))))

def token_features(last, start, phase):
    # Raw interaction features (not an engineered equality flag).
    return [1.] + [(2*a-1)*(2*b-1) for a,b in zip(last,start)] + [phase]

def edge_id(edge):
    return hashlib.sha256(json.dumps(edge, sort_keys=True,
                            separators=(",", ":")).encode()).hexdigest()

def init():
    return [-1.2] + [.17]*16 + [.05,3.,.5]

def forward(obs, weights, trace=False):
    env.validate(obs)
    require(type(weights) in (list, tuple) and len(weights) == PARAMETERS
            and all(type(w) in (float, int) and math.isfinite(w) and abs(w) <= 8
                    for w in weights), "INVALID_WEIGHT_VECTOR")
    cfg,_ = freeze.frozen()
    require(cfg["proposed_mechanism"]["beam_width"] == K and
            cfg["proposed_mechanism"]["max_trainable_parameters"] == PARAMETERS
            and cfg["proposed_mechanism"]["optimizer_epochs"] == EPOCHS,
            "FROZEN_LEARNER_BOUNDS")
    indexed = defaultdict(list)
    work = {"public_edge_visits":0,"index_operations":0,
            "hashed_edge_descriptors":0,"attention_bit_interactions":0,
            "attention_multiply_adds":0,"beam_candidates":0,
            "sort_comparison_upper":0,"allocated_states":0,
            "pruned_states":0,"retained_max":0}
    for e in obs["edges"]:
        desc = edge_id(e)
        indexed[(e["from"],e["role"])].append((desc,e))
        work["public_edge_visits"] += 1
        work["index_operations"] += 1
        work["hashed_edge_descriptors"] += 1
    # Sort the public adjacency deterministically, independent of edge order.
    for edges in indexed.values():
        edges.sort(key=lambda e: e[0])
        n=len(edges)
        work["sort_comparison_upper"] += n * max(1,(n-1).bit_length())
    # States (node, last edge raw token, mass, gradient d mass / d raw,
    #         immutable public edge-descriptor trace).
    states=[(obs["start"],None,1.,[0.]*18,())]
    peak=1
    for step,role in enumerate(obs["roles"]):
        proposals=[]
        for node,prev,mass,grad,trail in states:
            for desc,e in indexed.get((node,role),()):
                if prev is None:
                    attn, derivative=1.,[0.]*18
                else:
                    features=token_features(prev,e["src_bits"],
                                            float(step)/len(obs["roles"]))
                    attn=sigmoid(sum(w*x for w,x in zip(weights[:18],features)))
                    derivative=[attn*(1-attn)*x for x in features]
                    work["attention_bit_interactions"]+=16
                    work["attention_multiply_adds"]+=18
                dm=[g*attn+mass*d for g,d in zip(grad,derivative)]
                proposals.append((e["to"],e["dst_bits"],mass*attn,
                                  dm,trail+(desc,)))
                work["allocated_states"]+=1
                work["beam_candidates"]+=1
                require(work["beam_candidates"]<=MAX_CANDIDATES,
                        "INFERENCE_CANDIDATE_BUDGET")
        n=len(proposals)
        work["sort_comparison_upper"]+=n*max(1,(n-1).bit_length())
        proposals.sort(key=lambda v:(-v[2],v[4]))
        work["pruned_states"]+=max(0,n-K)
        states=proposals[:K]
        peak=max(peak,len(states))
        if not states:
            break
    valid=[s for s in states if s[0]==obs["target"]]
    amount=sum(x[2] for x in valid)
    deriv=[sum(s[3][i] for s in valid) for i in range(18)]
    gain,cutoff=weights[-2:]
    p=sigmoid(gain*(amount-cutoff))
    grad=[gain*x for x in deriv]+[amount-cutoff,-gain]
    work["retained_max"]=peak
    need=work["retained_max"] <= K and work["public_edge_visits"]==len(obs["edges"])
    require(need,"BEAM_OR_INPUT_INFORMATION_VIOLATION")
    if trace:
        return p,grad,{"work":work, "surviving_routes":
            [{"route_sha256":hashlib.sha256("|".join(s[4]).encode()).hexdigest(),
              "mass":s[2],"hops":len(s[4])}
             for s in states], "target_mass":amount,
             "no_route_counted_as_failure":not bool(valid)}
    return p,grad

def fit(rows):
    cfg,_=freeze.frozen()
    require(cfg["proposed_mechanism"]["optimizer"] ==
            "fixed deterministic full-batch clipped gradient updates with one seed and exact frozen schedule"
            and cfg["proposed_mechanism"]["learning_rate"]==RATE,
            "OPTIMIZER_PRECOMMITMENT")
    require(type(rows) is list and len(rows)==128 and
            sum(label for _,label in rows)==64,"FROZEN_TRAIN_ONLY_ROWS")
    weights=init()
    old=list(weights)
    for _ in range(EPOCHS):
        grad=[0.]*PARAMETERS
        for obs,label in rows:
            p,dp=forward(obs,weights)
            for k,x in enumerate(dp):
                grad[k]+=(p-label)*x
        for k,g in enumerate(grad):
            weights[k]=max(-8.,min(8.,weights[k]-
                           RATE*max(-1.,min(1.,g/len(rows)))))
        require(all(math.isfinite(w) for w in weights),"NONFINITE_TRAIN")
    moved=math.sqrt(sum((a-b)**2 for a,b in zip(weights,old)))
    require(moved>0.0001,"ZERO_LEARNING_MOVEMENT")
    return weights,moved

def score(rows,weights):
    require(len(rows)%2==0 and len(rows)>0,"INVALID_SCORE_COHORT")
    yes=no=paired=0
    for k in range(0,len(rows),2):
        pos,a=rows[k];neg,b=rows[k+1]
        require(a==1 and b==0,"UNPAIRED_LABELS")
        p=forward(pos,weights)[0]>=.5
        n=forward(neg,weights)[0]<.5
        yes+=int(p);no+=int(n);paired+=int(p and n)
    return {"pairs":len(rows)//2,"paired_correct":paired,
            "positive_correct":yes,"negative_correct":no,
            "balanced_accuracy":round((yes+no)/len(rows),8)}

def sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,
                          separators=(",",":")).encode()).hexdigest()
