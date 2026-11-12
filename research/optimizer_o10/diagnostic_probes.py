"""Frozen recurrent-state diagnostics: TRAIN-fitted readouts, no network adaptation.

Crucially, diagnostic targets are PUBLIC history functionals (cue, reset
parity) and observed next query bit, never source hidden variables. Probes
get no cue/parity as inputs; their ONLY input besides query observation is
a queried FROZEN recurrent state's learned or untrained cell vector.
"""
from __future__ import annotations
import hashlib
import math
from public_source import canonical,query_info
from frozen_o9_memory import TrainedMemory

PROBE_EPOCHS=120
PROBE_RATE=0.2
PROBE_L2=0.002
STARTS=(17,31)
RECURRENT_KIND=("LEARNED_EXTERNAL_WRITE_READ_2","GRU_2")

def sigmoid(z):
    if z>=0:
        k=math.exp(-min(z,60.0))
        return 1/(1+k)
    k=math.exp(max(z,-60.0))
    return k/(1+k)

def nll(target,score):
    p=min(1.0-1e-12,max(1e-12,score))
    return -math.log(p if target==1 else (1-p))

def query_score(model,eps,erased=False):
    return sum(nll(query_info(ep)["target"],
                   model.predict(ep,erased_query=True) if erased
                   else model.predict(ep)) for ep in eps)/len(eps)

def selected_model(kind,train,select):
    if kind not in RECURRENT_KIND:
        raise ValueError("O10_UNKNOWN_FROZEN_ARCHITECTURE")
    trials=[]
    for seed in STARTS:
        model=TrainedMemory(kind,seed)
        model.fit(train)
        trials.append((query_score(model,select),seed,model))
    trials.sort(key=lambda z:(z[0],z[1]))
    return trials[0][2],{"selected_start":trials[0][1],
                         "selected_validation_nll":trials[0][0],
                         "all_select_nll_by_start":{str(seed):loss
                                                     for loss,seed,_ in trials}}

def frozen_state_features(model,ep):
    # The LAST tape record is the hidden state AFTER reading the public
    # query action and current observation but BEFORE the target is revealed.
    prob,tape,read,output=model._forward(ep)
    query=query_info(ep)
    h=tape[-1][-1]
    if len(h)!=2 or not all(math.isfinite(x) for x in h):
        raise ValueError("O10_STATE_DIMENSION_OR_NONFINITE")
    return (1.0,float(query["query_observation"]),*h)

class FrozenStateProbe:
    def __init__(self,task):
        if task not in ("target","cue","parity"):
            raise ValueError("O10_INVALID_DIAGNOSTIC_LABEL")
        self.task=task
        self.w=[0.0]*4
        self.updates=0

    def fit(self,model,train):
        examples=[(frozen_state_features(model,ep),query_info(ep)[self.task])
                  for ep in train]
        for epoch in range(PROBE_EPOCHS):
            gradient=[0.0]*4
            for features,target in examples:
                p=sigmoid(sum(v*w for v,w in zip(features,self.w)))
                error=p-target
                for j in range(4):
                    gradient[j]+=error*features[j]
            for j in range(4):
                penalty=0 if j==0 else PROBE_L2*self.w[j]
                self.w[j]-=PROBE_RATE*(gradient[j]/len(examples)+penalty)
            self.updates+=len(examples)

    def predict(self,model,ep):
        features=frozen_state_features(model,ep)
        return sigmoid(sum(w*x for w,x in zip(self.w,features)))

    def score(self,model,eps):
        return sum(nll(query_info(ep)[self.task],self.predict(model,ep))
                   for ep in eps)/len(eps)

    def checkpoint(self):
        return canonical({"task":self.task,"weights":self.w,
                          "updates":self.updates,
                          "recurrent_weights_frozen":True,
                          "derived_supervision_public_only":True})

class PublicHistoryCounts:
    def __init__(self,which):
        if which not in ("CURRENT","EXPLICIT_RESET_PARITY"):
            raise ValueError("O10_BAD_CONTROL")
        self.which=which
        self.table={}
        self.updates=0

    def key(self,ep):
        q=query_info(ep)
        return ((q["cue"],q["parity"]) if self.which=="EXPLICIT_RESET_PARITY"
                else (q["query_observation"],int(q["query_t"]==26)))

    def fit(self,eps):
        for ep in eps:
            k=self.key(ep)
            entry=self.table.setdefault(k,[0,0])
            entry[query_info(ep)["target"]]+=1
            self.updates+=1

    def predict(self,ep):
        negative,positive=self.table.get(self.key(ep),(0,0))
        return (positive+1)/(negative+positive+2)

    def score(self,eps):
        return sum(nll(query_info(ep)["target"],self.predict(ep))
                   for ep in eps)/len(eps)

    def checkpoint(self):
        return canonical({"which":self.which,"counts":[[list(k),v]
                        for k,v in sorted(self.table.items())],
                        "updates":self.updates,
                        "memory_features_hand_engineered":
                            self.which=="EXPLICIT_RESET_PARITY"})
