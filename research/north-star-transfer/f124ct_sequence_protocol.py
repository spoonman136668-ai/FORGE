"""F124-CT source-free public *sequence* protocol, never prior FIT pairs.

All models train on complete causally ordered episodes, never single isolated
transition rows. Targets are available only as supervised TRAINING labels;
inference/recurrent state receives no observed target. CHECK veto only.
"""
from __future__ import annotations
import hashlib
import json
import math
import numpy as np

ROLES=("alpha","beta","gamma")
N_ROLES=3
HIDDEN=8
EVENT_BITS=4
INIT_BITS=8
FIT_EPISODES=24
CHECK_EPISODES=8
STEPS_PER_EPISODE=8
EPOCHS=45
LEARNING_RATE=0.035
GRAD_CLIP_NORM=4.0
CHECK_ERROR_VETO_RATIO=0.32
MIN_FIT_LOSS_REDUCTION=0.04

def need(ok,reason):
    if not ok:raise ValueError("F124CT_"+reason)

def nib(x):
    return type(x) is int and 0<=x<16

def bits(x):
    need(nib(x),"BOUNDED_PUBLIC_NIBBLE")
    return np.array([(x>>j)&1 for j in range(4)],dtype=np.float64)

def init_bits(row):
    return np.concatenate([bits(row[0]),bits(row[1])])

def validate(episodes,count):
    need(type(episodes) in (list,tuple) and len(episodes)==count,"COMPLETE_EPISODE_COUNT")
    result=[]
    for episode in episodes:
        need(type(episode) is dict and set(episode)=={"initial","events"},
             "PUBLIC_INITIAL_AND_EVENTS_ONLY")
        initial=episode["initial"]
        need(type(initial) is dict and set(initial)==set(ROLES) and
             all(type(x) in (list,tuple) and len(x)==2 and all(nib(v) for v in x)
                 for x in initial.values()),"THREE_BOUND_INITIAL_ROLE_STATES")
        events=episode["events"]
        need(type(events) in (list,tuple) and len(events)==STEPS_PER_EPISODE,
             "SEQUENTIAL_EIGHT_EVENTS_NO_ISOLATED_PAIRS")
        for event in events:
            need(type(event) is dict and set(event)==
                 {"target","source","event","observed"}
                 and type(event["target"]) is str and event["target"] in ROLES
                 and type(event["source"]) is str and event["source"] in ROLES
                 and nib(event["event"]) and nib(event["observed"]),
                 "BOUND_CAUSAL_EVENT_SOURCE_ONLY")
        result.append(episode)
    return result

def digest(episodes):
    return hashlib.sha256(json.dumps(episodes,sort_keys=True,
                          separators=(",",":")).encode()).hexdigest()

def sigmoid(x):
    return 1.0/(1.0+np.exp(-np.clip(x,-40.0,40.0)))

def softmax(x):
    y=np.exp(x-np.max(x));return y/np.sum(y)

def loss_bit(prob,target):
    p=np.clip(prob,1e-8,1-1e-8)
    return float(-(target*np.log(p)+(1-target)*np.log(1-p)).sum())

def clip_and_update(parameters,gradients):
    norm=math.sqrt(sum(float(np.sum(v*v)) for v in gradients.values()))
    scale=min(1.0,GRAD_CLIP_NORM/max(1e-12,norm))
    for key in parameters:
        parameters[key]-=LEARNING_RATE*scale*gradients[key]
    need(all(np.isfinite(v).all() for v in parameters.values()),"FINITE_TRAINED_WEIGHTS")
    return norm

def schedule(epoch):
    # Both independently trained arms receive exactly this public sequence
    # permutation for each fixed epoch; no CHECK or private outcome tuning.
    rng=np.random.default_rng(310110+epoch)
    return rng.permutation(FIT_EPISODES)

def assessment(predict,fit,check):
    loss_fit=sum(predict(ep,with_targets=True)[1] for ep in fit)/(len(fit)*STEPS_PER_EPISODE*4)
    mistakes=sum(predict(ep,with_targets=True)[2] for ep in check)
    total=len(check)*STEPS_PER_EPISODE*4
    return float(loss_fit),int(mistakes),int(total)
