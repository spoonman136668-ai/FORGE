"""L3 actual trained NAR, tanh RNN and diagonal linear-state-mixing SSM.

All three use full-supervised public semantic IDs + aligned target chunks.
NAR emits independent per-slot predictions; RNN/SSM use teacher-forced
previous target chunk on FIT only and their own generated previous chunk at
DEV inference. RNN/SSM receive backpropagated gradients through their
complete eight-step recurrence, not fixed handcrafted word dependencies.
No prior L1/L2 DEV, hidden generator lexeme/oracle, or paid model is used.
"""
from io import BytesIO
import json
import math

import numpy as np

from public_source import SIZES,canonical

ARMS=("NAR_H13","RNN_H12","SSM_DIAGONAL_H14")
WIDTH={"NAR_H13":13,"RNN_H12":12,"SSM_DIAGONAL_H14":14}
SEEDS=(17,31)
EPOCHS=12
BATCH=32
D=sum(SIZES)
SLOTS=8
BETA1=.9
BETA2=.999
LR=.02
EPS=1e-8
CLIP=2.


def public_inputs(meaning):
    a=np.asarray(meaning,dtype=np.int64)
    if a.ndim==1:
        a=a[None,:]
    if a.shape[1]!=len(SIZES) or np.any(a<0) or \
            any(np.any(a[:,i]>=n) for i,n in enumerate(SIZES)):
        raise ValueError("L3_BAD_PUBLIC_SEMANTIC_IDS")
    out=np.zeros((len(a),D),dtype=np.float64)
    offset=0
    for i,n in enumerate(SIZES):
        out[np.arange(len(a)),offset+a[:,i]]=1.
        offset+=n
    return out


class NeuralChunkModel:
    def __init__(self,arm,seed,vocab):
        if arm not in ARMS or type(seed) is not int or seed not in SEEDS:
            raise ValueError("L3_UNFROZEN_NEURAL_ARM")
        self.arm,self.seed=arm,seed
        self.vocab=tuple(sorted(set(vocab)|{"<bos>"}))
        self.token_id={s:i for i,s in enumerate(self.vocab)}
        self.V=len(self.vocab)
        self.H=WIDTH[arm]
        rng=np.random.default_rng(seed)
        def weights(shape):
            return rng.normal(0.,.09,shape).astype(np.float64)
        self.p={
            "E":weights((D,self.H)),
            "b":np.zeros(self.H,dtype=np.float64),
            "W":weights((self.H,self.V)),
            "out_b":np.zeros(self.V,dtype=np.float64),
            "slot_b":np.zeros((SLOTS,self.V),dtype=np.float64),
        }
        if arm=="NAR_H13":
            self.p["slot_e"]=weights((SLOTS,self.H))
        else:
            self.p["prev_e"]=weights((self.V,self.H))
            if arm=="RNN_H12":
                self.p["recur"]=weights((self.H,self.H))
            else:
                self.p["retention"]=np.zeros(self.H,dtype=np.float64)
        self.m={k:np.zeros_like(v) for k,v in self.p.items()}
        self.v={k:np.zeros_like(v) for k,v in self.p.items()}
        self.updates=0

    def _softmax(self,logits):
        exp=np.exp(logits-np.max(logits,axis=1,keepdims=True))
        return exp/np.sum(exp,axis=1,keepdims=True)

    def _forward(self,meanings,teacher=None):
        x=public_inputs(meanings)
        n=x.shape[0]
        h_prev=np.zeros((n,self.H),dtype=np.float64)
        previous=np.full(n,self.token_id["<bos>"],dtype=np.int64)
        z=x@self.p["E"]+self.p["b"]
        cache=[]
        outputs=[]
        for t in range(SLOTS):
            if self.arm=="NAR_H13":
                innovation=np.tanh(z+self.p["slot_e"][t])
                h=innovation
                lam=None
            else:
                innovation=np.tanh(z+self.p["prev_e"][previous])
                if self.arm=="RNN_H12":
                    innovation=np.tanh(z+self.p["prev_e"][previous]+
                                       h_prev@self.p["recur"])
                    h=innovation
                    lam=None
                else:
                    lam=1/(1+np.exp(-self.p["retention"]))
                    h=lam*h_prev+(1-lam)*innovation
            probs=self._softmax(h@self.p["W"]+
                                self.p["out_b"]+self.p["slot_b"][t])
            outputs.append(probs)
            cache.append((h,h_prev,innovation,previous.copy(),lam))
            previous=(teacher[:,t] if teacher is not None
                      else np.argmax(probs,axis=1))
            h_prev=h
        return outputs,cache,x

    def _batch(self,examples):
        meanings=[r["meaning"] for r in examples]
        targets=np.asarray([[self.token_id[t] for t in r["slots"]]
                            for r in examples],dtype=np.int64)
        return meanings,targets

    def loss_and_gradient(self,examples):
        meanings,y=self._batch(examples)
        probs,cache,x=self._forward(meanings,teacher=y)
        n=len(y)
        grad={k:np.zeros_like(v) for k,v in self.p.items()}
        loss=0.
        dh_next=np.zeros((n,self.H),dtype=np.float64)
        for t in range(SLOTS-1,-1,-1):
            q=probs[t]
            loss-=float(np.log(np.maximum(q[np.arange(n),y[:,t]],1e-14)).sum())
            dq=q.copy()
            dq[np.arange(n),y[:,t]]-=1.
            dq/=(n*SLOTS)
            h,h_prev,innov,prev_ids,lam=cache[t]
            grad["W"]+=h.T@dq
            grad["out_b"]+=np.sum(dq,axis=0)
            grad["slot_b"][t]+=np.sum(dq,axis=0)
            dh=dq@self.p["W"].T+dh_next
            if self.arm=="NAR_H13":
                da=dh*(1-innov*innov)
                grad["slot_e"][t]+=np.sum(da,axis=0)
                dh_next=np.zeros_like(dh)
            elif self.arm=="RNN_H12":
                da=dh*(1-innov*innov)
                grad["recur"]+=h_prev.T@da
                dh_next=da@self.p["recur"].T
            else:
                da=dh*(1-lam)*(1-innov*innov)
                grad["retention"]+=np.sum(
                    dh*(h_prev-innov)*lam*(1-lam),axis=0)
                dh_next=dh*lam
            grad["E"]+=x.T@da
            grad["b"]+=np.sum(da,axis=0)
            if self.arm!="NAR_H13":
                np.add.at(grad["prev_e"],prev_ids,da)
        if any(not np.all(np.isfinite(g)) for g in grad.values()):
            raise ValueError("L3_NONFINITE_TRAIN_GRADIENT")
        return loss/(n*SLOTS),grad

    def step(self,batch):
        loss,grads=self.loss_and_gradient(batch)
        norm=math.sqrt(sum(float(np.sum(g*g)) for g in grads.values()))
        if norm>CLIP:
            grads={k:g*(CLIP/norm) for k,g in grads.items()}
        self.updates+=1
        t=self.updates
        for k,g in grads.items():
            self.m[k]=BETA1*self.m[k]+(1-BETA1)*g
            self.v[k]=BETA2*self.v[k]+(1-BETA2)*g*g
            mhat=self.m[k]/(1-BETA1**t)
            vhat=self.v[k]/(1-BETA2**t)
            self.p[k]-=LR*mhat/(np.sqrt(vhat)+EPS)
        return loss

    def fit(self,train):
        if len(train)!=768:
            raise ValueError("L3_TRAIN_BUDGET_OR_ROLE_DRIFT")
        for _ in range(EPOCHS):
            for begin in range(0,len(train),BATCH):
                self.step(train[begin:begin+BATCH])
        if self.updates!=EPOCHS*24:
            raise ValueError("L3_TRAIN_UPDATE_COVERAGE")
        return self

    def teacher_forced_nll(self,examples):
        meanings,y=self._batch(examples)
        total=0.
        for first in range(0,len(y),BATCH):
            probs,_,_=self._forward(meanings[first:first+BATCH],
                                    teacher=y[first:first+BATCH])
            target=y[first:first+BATCH]
            for t in range(SLOTS):
                total-=float(np.log(np.maximum(
                    probs[t][np.arange(len(target)),target[:,t]],1e-14)).sum())
        return total/(len(y)*SLOTS)

    def generate(self,meaning):
        probabilities,_,_=self._forward([meaning])
        ids=[int(np.argmax(p[0])) for p in probabilities]
        # _forward with no teacher already consumes its own emitted prior tokens.
        words=tuple(self.vocab[i] for i in ids)
        # Dense parameter multiply count is only an analytical operation proxy,
        # NOT a hardware FLOP count or observed parallel wall-time speedup.
        work=SLOTS*(D*self.H+self.H*self.V+
                    (self.H*self.H if self.arm=="RNN_H12"
                     else self.H if self.arm=="SSM_DIAGONAL_H14" else 0))
        return words,work

    def params_count(self):
        return sum(v.size for v in self.p.values())

    def checkpoint(self):
        header=canonical({
            "arm":self.arm,"seed":self.seed,
            "shapes":{k:list(v.shape) for k,v in sorted(self.p.items())},
            "vocab":self.vocab,"updates":self.updates,
            "include_optimizer":True,"dtype":"little_endian_float64"
        })
        parts=[header]
        for k in sorted(self.p):
            for mapping in (self.p,self.m,self.v):
                parts.append(np.asarray(mapping[k],dtype="<f8").tobytes())
        return b"".join(parts)
