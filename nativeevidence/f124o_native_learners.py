"""F124-O two genuinely different learned structural-binding mechanisms.

Wingless: bounded compressed-latent relational message passing, three states/node.
Yggdrasil: competitively gated 7 active + 9 retained cognitive cells.
Both observe only public graph fields. They do not receive labels, correct paths,
source metadata, oracle outputs, or paired counterparts at inference.
Training is separate and FIT-only. No paid API, model service or protected source.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
import math
import random

import f124n_novel_structure_source as source

SCHEMA = "forge.research.f124o.two-native-learned-structural-programs.v1"
WINGLESS_INIT = [0.8, 0.7, 0.9, 0.6, 1.0, 0.15, -0.5]
YGGDRASIL_INIT = [0.4, 0.9, 0.65, 0.75, 0.8, 0.2, -0.5]
EPOCHS = 12
BATCH = 8
PERTURB = 0.08
RATE = 0.04


def need(ok, code):
    source.need(ok, "LEARNED_" + code)


def sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,
                                     separators=(",",":")).encode()).hexdigest()


def sigmoid(x):
    return 1. / (1. + math.exp(-max(-40.,min(40.,x))))


def sorted_edges(g):
    return sorted(g["edges"],
                  key=lambda e:(e["from"],e["to"],e["role"],
                                tuple(e["src_bits"]),tuple(e["dst_bits"])))


def wingless_forward(g, w):
    """4-channel learned compression of raw token bits and node-local 3-slot state."""
    source.validate_public(g)
    need(type(w) is list and len(w) == 7 and
         all(type(x) in (int,float) and math.isfinite(x) for x in w),
         "WINGLESS_PARAMETER_SHAPE")
    edges = sorted_edges(g)
    counters = {"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
                "evictions":0,"state_limit":3}
    def encode(bits):
        counters["raw_bit_ops"] += 16
        return tuple(w[j] * (sum(2 * b - 1 for b in bits[j*4:j*4+4]) / 4.)
                     for j in range(4))
    def affinity(a,b):
        counters["raw_bit_ops"] += 4
        return 1. - sum(abs(x-y) for x,y in zip(a,b))/8.
    # Each state stores (evidence, compressed value), never source or oracle labels.
    states = {g["start"]:[(0.,None)]}
    for step,role in enumerate(g["roles"]):
        nextrole = g["roles"][step+1] if step+1 < len(g["roles"]) else None
        new = defaultdict(list)
        for node in sorted(states):
            allowed = [e for e in edges if e["from"] == node and e["role"] == role]
            for score,carried in states[node]:
                counters["public_edge_scans"] += len(edges)
                for e in allowed:
                    src = encode(e["src_bits"])
                    dst = encode(e["dst_bits"])
                    compat = 1. if carried is None else affinity(carried,src)
                    value = score + w[4] * (compat-.6)
                    if nextrole is None:
                        look = 0.
                    else:
                        # Public prospective query (no ground-truth path).
                        queries = [q for q in edges
                                   if q["from"] == e["to"] and q["role"] == nextrole]
                        look = max((affinity(dst,encode(q["src_bits"])) for q in queries),
                                   default=0.)
                    priority = value + w[5] * (look-.6)
                    new[e["to"]].append((priority,value,dst))
        states = {}
        for node, candidates in new.items():
            candidates.sort(key=lambda x:(-x[0],-x[1],x[2]))
            counters["evictions"] += max(0,len(candidates)-3)
            states[node] = [(v,k) for _,v,k in candidates[:3]]
        counters["max_active"] = max(counters["max_active"],
                                    sum(len(v) for v in states.values()))
        need(counters["max_active"] <= 192,
             "WINGLESS_PUBLIC_NODE_STATE_BOUND")
    scores = [s for s,_ in states.get(g["target"],[])]
    best = max(scores,default=-2.*len(g["roles"]))
    logit = 4. * (best/max(1,len(g["roles"])-1) - w[6])
    need(math.isfinite(logit),"WINGLESS_NONFINITE")
    return logit,counters


def yggdrasil_forward(g,w):
    """Exactly 7 active + 9 retained slots, competitive retain/recall each hop.

    Unlike Wingless there is no per-node state: it is a global 16-cell budget.
    Retained cells at stage t are reactivated as candidates at stage t+1.
    Cells carry public node plus the raw 16-bit value, never a causal oracle.
    """
    source.validate_public(g)
    need(type(w) is list and len(w)==7 and
         all(type(x) in (float,int) and math.isfinite(x) for x in w),
         "YGGDRASIL_PARAMETER_SHAPE")
    edges = sorted_edges(g)
    active = [(g["start"],None,0.)]
    retained = []
    counters = {"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
                "max_retained":0,"evictions":0,
                "active_cell_limit":7,"retained_cell_limit":9}
    def compatibility(carried, src):
        if carried is None:
            return 1.
        counters["raw_bit_ops"] += 16
        return sum(w[j] * sum(int(a==b) for a,b in zip(
                     carried[j*4:j*4+4],src[j*4:j*4+4]))/4.
                   for j in range(4))/4.
    for role in g["roles"]:
        candidate = []
        for node,carried,score in active+retained:
            counters["public_edge_scans"] += len(edges)
            for e in edges:
                if e["from"] != node or e["role"] != role:
                    continue
                similarity = compatibility(carried,e["src_bits"])
                value = score + w[4] * (similarity-.35)
                competition = w[5]*(similarity-.5)
                cell = (e["to"],tuple(e["dst_bits"]),value)
                candidate.append((value+competition,value-competition,cell))
        candidate.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active = [x[2] for x in candidate[:7]]
        selected = {id(x) for x in candidate[:7]}
        extras = [x for x in candidate if id(x) not in selected]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained = [x[2] for x in extras[:9]]
        counters["evictions"] += max(0,len(candidate)-16)
        counters["max_active"] = max(counters["max_active"],len(active))
        counters["max_retained"] = max(counters["max_retained"],len(retained))
        need(len(active) <= 7 and len(retained) <= 9 and
             len(active)+len(retained)<=16,"YGGDRASIL_CELL_OVERFLOW")
    terminal = [score for node,_,score in active+retained
                if node == g["target"]]
    best = max(terminal,default=-2.*len(g["roles"]))
    logit = 4. * (best/max(1,len(g["roles"])-1) - w[6])
    need(math.isfinite(logit),"YGGDRASIL_NONFINITE")
    return logit,counters


def forward(lane,g,w):
    if lane=="Wingless":
        return wingless_forward(g,w)
    if lane=="Yggdrasil":
        return yggdrasil_forward(g,w)
    raise source.Quarantined("F124O_UNKNOWN_LANE")


def fit_pairs(lane):
    # FIT-only constructor; this is never called with DEV or protected seeds.
    source.frozen()
    result=[]
    for vector in source.VECTORS:
        for seed in source.COHORTS[lane]["FIT"]:
            pos,neg=source.build(lane,seed,vector,"FIT")
            result.append((pos,neg))
    need(len(result)==48,"FIT_DENOMINATOR")
    return result


def pair_loss(lane,pairs,w):
    """Bounded logistic loss and paired ranking, labels visible only here."""
    total=0.
    for pos,neg in pairs:
        a,_=forward(lane,pos,w)
        b,_=forward(lane,neg,w)
        # Stable softplus; never access the exact symbolic reference to train.
        total+=math.log1p(math.exp(-abs(a)))+max(-a,0.)
        total+=math.log1p(math.exp(-abs(-b)))+max(b,0.)
        total+=.15 * (math.log1p(math.exp(-abs(b-a)))+max(b-a,0.))
    return total/len(pairs)


def train(lane):
    need(lane in ("Wingless","Yggdrasil"),"UNKNOWN_LANE_TRAIN")
    pairs=fit_pairs(lane)
    w=list(WINGLESS_INIT if lane=="Wingless" else YGGDRASIL_INIT)
    prior=list(w)
    rng=random.Random(int.from_bytes(
        hashlib.sha256(("F124O/FIT/SPSA/v1/"+lane).encode()).digest()[:12],"big"))
    initial_loss=pair_loss(lane,pairs,w)
    steps=0
    for epoch in range(EPOCHS):
        order=list(range(48))
        rng.shuffle(order)
        for k in range(0,48,BATCH):
            batch=[pairs[i] for i in order[k:k+BATCH]]
            signs=[1 if rng.getrandbits(1) else -1 for _ in w]
            positive=[max(-3.,min(3.,x+PERTURB*s)) for x,s in zip(w,signs)]
            negative=[max(-3.,min(3.,x-PERTURB*s)) for x,s in zip(w,signs)]
            gradient=(pair_loss(lane,batch,positive)
                      -pair_loss(lane,batch,negative))/(2*PERTURB)
            rate=RATE/(1+.01*steps)
            w=[max(-3.,min(3.,x-rate*gradient*s))
               for x,s in zip(w,signs)]
            steps+=1
    final_loss=pair_loss(lane,pairs,w)
    change=sum((x-y)**2 for x,y in zip(w,prior))**.5
    need(steps==72 and change>1e-9 and
         all(math.isfinite(x) for x in w), "GENUINE_TRAIN_UPDATE")
    return {"lane":lane,"train_phase":"FIT_ONLY",
            "method":"DETERMINISTIC_TWO_SIDED_SPSA_BINARY_PAIR_LOSS",
            "trained_weights":w,"trained_weight_sha256":sha(w),
            "training_steps":steps,"epochs":EPOCHS,"pairs":48,
            "initial_loss":round(initial_loss,8),
            "final_loss":round(final_loss,8),
            "weight_update_l2":round(change,9),
            "prior_weight_sha256":sha(prior),
            "dev_seen_during_training":False,
            "protected_cases_seen":0}
