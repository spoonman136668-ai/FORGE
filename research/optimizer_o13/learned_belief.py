"""O13 genuinely fitted action-conditioned binary public predictive belief.

The learned *parameters* form a compact predictive state estimate. The 2-state
filter structure and action-conditioning are predefined, not architecturally
discovered. Query targets are used only after prediction in TRAIN fitting.

FULL: exact central finite differences of the entire episode recurrent-loss,
including gradients flowing through prior predictive belief across time.
STOP: identical forward episodes, but freeze each pre-observation prior for
gradient only. This is explicit one-step temporal-credit ablation. FROZEN:
full gradient but transition logits cannot learn. All arms same observations,
same parameter initialization, same 24 epochs and minibatch schedule.
"""
from __future__ import annotations
import hashlib
import math
import random
from public_source import canonical

ARMS=("FULL_CREDIT_BELIEF","STOP_CREDIT_BELIEF","FROZEN_TRANSITION_BELIEF")
SEEDS=(17,31)
EPOCHS=24
BATCH=8
LR=.02
B1=.9
B2=.999
ADAM_EPS=1e-8
FD_EPS=.0001
CLIP=2.
START=(-1.2,1.2,-2.,-1.,0.)


def sigmoid(v):
    if v>=0:
        z=math.exp(-min(60.,v))
        return 1/(1+z)
    z=math.exp(max(-60.,v))
    return z/(1+z)


def loss(y,p):
    p=max(1e-12,min(1.-1e-12,p))
    return -math.log(p if y else 1-p)


class LearnedPublicBelief:
    def __init__(self,arm,seed):
        if arm not in ARMS or type(seed) is not int or seed not in SEEDS:
            raise ValueError("O13_UNREGISTERED_ARCHITECTURE")
        self.arm=arm
        self.seed=seed
        rng=random.Random(seed)
        self.w=[base+rng.uniform(-.20,.20) for base in START]
        self.m=[0.]*5
        self.v=[0.]*5
        self.updates=0

    def _episode(self,ep,params,reset=False,held_priors=None,return_priors=False):
        if len(ep)==0:
            raise ValueError("O13_EMPTY_PUBLIC_EPISODE")
        e0,e1,f0,f1,begin=map(sigmoid,params)
        prior=begin
        saved=[]
        predictions=[]
        for t,(observed,action,target) in enumerate(ep):
            if (type(observed) is not int or observed not in (0,1)
                    or type(action) is not int or action not in (0,1)
                    or type(target) is not int or target not in (0,1)):
                raise ValueError("O13_REJECT_NONPUBLIC_BINARY_TRAJECTORY")
            if t>0 and ep[t-1][2]!=observed:
                raise ValueError("O13_PUBLIC_CHAIN_BROKEN")
            if reset:
                prior=.5
            if held_priors is not None:
                prior=held_priors[t]
            saved.append(prior)
            lk0=e0 if observed else 1-e0
            lk1=e1 if observed else 1-e1
            num=prior*lk1
            denom=num+(1-prior)*lk0
            if denom<=0:
                raise ValueError("O13_DEGENERATE_BELIEF")
            posterior=num/denom
            flip=f1 if action else f0
            predicted_hidden=posterior*(1-flip)+(1-posterior)*flip
            prediction=e0+(e1-e0)*predicted_hidden
            predictions.append(prediction)
            prior=predicted_hidden
        if return_priors:
            return tuple(saved)
        return predictions

    def predict(self,ep,erased=False):
        return self._episode(ep,self.w,reset=erased)

    def mean_episode_loss(self,ep,params,held_priors=None):
        preds=self._episode(ep,params,held_priors=held_priors)
        return sum(loss(row[2],p) for row,p in zip(ep,preds))/len(ep)

    def minibatch_gradient(self,episodes):
        if not episodes:
            raise ValueError("O13_EMPTY_MINIBATCH")
        held=None
        if self.arm=="STOP_CREDIT_BELIEF":
            held=[self._episode(ep,self.w,return_priors=True) for ep in episodes]
        grad=[]
        for j in range(5):
            if self.arm=="FROZEN_TRANSITION_BELIEF" and j in (2,3):
                grad.append(0.)
                continue
            base=self.w[j]
            try:
                self.w[j]=base+FD_EPS
                plus=sum(self.mean_episode_loss(
                    ep,self.w,None if held is None else held[i])
                         for i,ep in enumerate(episodes))/len(episodes)
                self.w[j]=base-FD_EPS
                minus=sum(self.mean_episode_loss(
                    ep,self.w,None if held is None else held[i])
                         for i,ep in enumerate(episodes))/len(episodes)
            finally:
                self.w[j]=base
            grad.append((plus-minus)/(2*FD_EPS))
        if any(not math.isfinite(g) for g in grad):
            raise ValueError("O13_NONFINITE_GRADIENT")
        return grad

    def fit(self,train):
        if len(train)!=48:
            # focused tests may exercise small subsets, but production runner
            # always verifies exact frozen 48-episode TRAIN role.
            if not (len(train)>0 and len(train)%BATCH==0):
                raise ValueError("O13_TRAIN_EPISODE_BUDGET")
        for _ in range(EPOCHS):
            for first in range(0,len(train),BATCH):
                minibatch=train[first:first+BATCH]
                grad=self.minibatch_gradient(minibatch)
                norm=math.sqrt(sum(g*g for g in grad))
                if norm>CLIP:
                    grad=[g*CLIP/norm for g in grad]
                self.updates+=1
                for j,g in enumerate(grad):
                    if self.arm=="FROZEN_TRANSITION_BELIEF" and j in (2,3):
                        continue
                    self.m[j]=B1*self.m[j]+(1-B1)*g
                    self.v[j]=B2*self.v[j]+(1-B2)*g*g
                    mh=self.m[j]/(1-B1**self.updates)
                    vh=self.v[j]/(1-B2**self.updates)
                    self.w[j]-=LR*mh/(math.sqrt(vh)+ADAM_EPS)

    def checkpoint(self):
        return canonical({
            "schema":"forge.optimizer.o13.learned-binary-predictive-belief.v1",
            "arm":self.arm,"seed":self.seed,
            "w":self.w,"adam_m":self.m,"adam_v":self.v,
            "updates":self.updates,"state_scalars":1,
            "trained_logit_count":3 if self.arm=="FROZEN_TRANSITION_BELIEF" else 5,
            "hand_designed_filter_structure":True,
        })
