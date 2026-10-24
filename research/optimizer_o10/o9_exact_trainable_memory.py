"""O9 fully trainable differentiable write/read external memory and GRU.

All parameters (memory write, content, read and output; or GRU update, reset,
candidate and output) learn by exact query-only BPTT across public events.
No cue/parity feature extractor, hidden state labels or source-law imports.
The event-is-first and query flags are public, same as baseline O8 model.
"""
from __future__ import annotations

import math
import random
from public_source import canonical,query_info

KINDS=("LEARNED_EXTERNAL_WRITE_READ_1","LEARNED_EXTERNAL_WRITE_READ_2",
       "GRU_2","GRU_4")
STARTS=(17,31)
FEATURES=6
EPOCHS=12
RATE=0.01
B1,B2,EPS=0.9,0.999,1e-8
CLIP=2.0


def sigmoid(z):
    if z>=0:
        q=math.exp(-min(z,60.0))
        return 1.0/(1.0+q)
    q=math.exp(max(z,-60.0))
    return q/(1.0+q)


class TrainedMemory:
    def __init__(self,kind,seed):
        if kind not in KINDS or type(seed) is not int or seed not in STARTS:
            raise ValueError("O9_UNFROZEN_MODEL")
        self.kind=kind
        self.gru=kind.startswith("GRU_")
        self.dim=(4 if kind=="GRU_4" else
                  2 if kind in ("GRU_2","LEARNED_EXTERNAL_WRITE_READ_2") else 1)
        rng=random.Random(seed)
        width=FEATURES+self.dim
        def matrix():
            return [[rng.uniform(-0.25,0.25) for _ in range(width)]
                    for _ in range(self.dim)]
        self.write=matrix()             # GRU: update gate
        self.reset=matrix() if self.gru else []
        self.content=matrix()           # GRU: reset-conditioned candidate
        self.read=[] if self.gru else matrix()
        self.out=[rng.uniform(-0.25,0.25)
                  for _ in range(1+FEATURES+self.dim)]
        self.updates=0
        self.m=[0.0]*self.parameter_count()
        self.v=[0.0]*self.parameter_count()

    def parameter_count(self):
        count=(self.dim*(FEATURES+self.dim)
               *(3 if self.gru else 3))
        return count+1+FEATURES+self.dim

    def _x(self,observation,action,t):
        return [1.0,float(observation),float(action==0),
                float(action==1),float(action==2),float(t==0)]

    def _forward(self,ep,erase=False):
        q=query_info(ep)["query_t"]
        h=[0.0]*self.dim
        tape=[]
        for t in range(q+1):
            observation,action,_=ep[t]
            if erase and t==q:
                h=[0.0]*self.dim
            previous=list(h)
            x=self._x(observation,action,t)
            features=x+previous
            write=[sigmoid(sum(w*f for w,f in zip(row,features)))
                   for row in self.write]
            if self.gru:
                reset=[sigmoid(sum(w*f for w,f in zip(row,features)))
                       for row in self.reset]
                candidate_features=x+[reset[j]*previous[j]
                                      for j in range(self.dim)]
            else:
                reset=[]
                candidate_features=features
            candidate=[math.tanh(sum(w*f for w,f in zip(row,candidate_features)))
                       for row in self.content]
            if self.gru:
                h=[write[j]*previous[j]+(1-write[j])*candidate[j]
                   for j in range(self.dim)]
            else:
                h=[(1-write[j])*previous[j]+write[j]*candidate[j]
                   for j in range(self.dim)]
            tape.append((x,features,previous,write,reset,
                         candidate_features,candidate,list(h)))
        if self.gru:
            read=[]
            output_features=[1.0]+tape[-1][0]+h
        else:
            rf=tape[-1][0]+h
            read=[sigmoid(sum(w*f for w,f in zip(row,rf)))
                  for row in self.read]
            output_features=[1.0]+tape[-1][0]+[
                read[i]*h[i] for i in range(self.dim)]
        probability=sigmoid(sum(w*f for w,f in zip(self.out,output_features)))
        return probability,tape,read,output_features

    def predict(self,ep,erased_query=False):
        return self._forward(ep,erase=erased_query)[0]

    def _params(self):
        return ([n for row in self.write for n in row]
                +[n for row in self.reset for n in row]
                +[n for row in self.content for n in row]
                +[n for row in self.read for n in row]
                +self.out[:])

    def _set_params(self,values):
        offset=0
        width=FEATURES+self.dim
        for name in ("write","reset","content","read"):
            matrix=getattr(self,name)
            for row in range(len(matrix)):
                matrix[row]=values[offset:offset+width]
                offset+=width
        self.out=values[offset:]
        if len(self.out)!=1+FEATURES+self.dim:
            raise ValueError("O9_BAD_PARAMETER_LAYOUT")

    def fit_episode(self,ep):
        prediction,tape,read,output=self._forward(ep)
        y=query_info(ep)["target"]
        delta=prediction-y
        dwrite=[[0.0]*(FEATURES+self.dim) for _ in range(self.dim)]
        dreset=([[0.0]*(FEATURES+self.dim) for _ in range(self.dim)]
                if self.gru else [])
        dcontent=[[0.0]*(FEATURES+self.dim) for _ in range(self.dim)]
        dread=([[0.0]*(FEATURES+self.dim) for _ in range(self.dim)]
               if not self.gru else [])
        dout=[delta*v for v in output]
        h=tape[-1][-1]
        if self.gru:
            dh=[delta*self.out[1+FEATURES+j] for j in range(self.dim)]
        else:
            rf=tape[-1][0]+h
            read_derivatives=[
                delta*self.out[1+FEATURES+j]*h[j]*read[j]*(1-read[j])
                for j in range(self.dim)]
            for j in range(self.dim):
                for k in range(FEATURES+self.dim):
                    dread[j][k]+=read_derivatives[j]*rf[k]
            dh=[
                delta*self.out[1+FEATURES+j]*read[j] +
                sum(read_derivatives[i]*self.read[i][FEATURES+j]
                    for i in range(self.dim))
                for j in range(self.dim)
            ]
        for x,features,prev,write,reset,candidate_features,candidate,after in reversed(tape):
            dprev=[0.0]*self.dim
            dz=[0.0]*self.dim
            dn=[0.0]*self.dim
            for j in range(self.dim):
                if self.gru:
                    dz[j]=dh[j]*(prev[j]-candidate[j])*write[j]*(1-write[j])
                    dn[j]=dh[j]*(1-write[j])*(1-candidate[j]*candidate[j])
                    dprev[j]+=dh[j]*write[j]
                else:
                    dz[j]=dh[j]*(candidate[j]-prev[j])*write[j]*(1-write[j])
                    dn[j]=dh[j]*write[j]*(1-candidate[j]*candidate[j])
                    dprev[j]+=dh[j]*(1-write[j])
                for k in range(FEATURES+self.dim):
                    dwrite[j][k]+=dz[j]*features[k]
                    dcontent[j][k]+=dn[j]*candidate_features[k]
            for j in range(self.dim):
                dprev[j]+=sum(dz[i]*self.write[i][FEATURES+j]
                              for i in range(self.dim))
                d_candidate_input=sum(dn[i]*self.content[i][FEATURES+j]
                                      for i in range(self.dim))
                if self.gru:
                    dprev[j]+=d_candidate_input*reset[j]
                    dr=d_candidate_input*prev[j]*reset[j]*(1-reset[j])
                    for k in range(FEATURES+self.dim):
                        dreset[j][k]+=dr*features[k]
                    # reset recurrent contribution includes ALL reset gates:
                    # accumulated after all per-cell reset grads exist.
                else:
                    dprev[j]+=d_candidate_input
            if self.gru:
                for j in range(self.dim):
                    dprev[j]+=sum(
                        self.reset[i][FEATURES+j] * (
                            sum(dn[k]*self.content[k][FEATURES+i]
                                for k in range(self.dim))
                            *prev[i]*reset[i]*(1-reset[i]))
                        for i in range(self.dim))
            dh=dprev
        gradient=([v for row in dwrite for v in row]
                  +[v for row in dreset for v in row]
                  +[v for row in dcontent for v in row]
                  +[v for row in dread for v in row]
                  +dout)
        if len(gradient)!=self.parameter_count() or not all(
                math.isfinite(g) for g in gradient):
            raise ValueError("O9_INVALID_BACKPROP")
        norm=math.sqrt(sum(g*g for g in gradient))
        if norm>CLIP:
            gradient=[g*CLIP/norm for g in gradient]
        params=self._params()
        self.updates+=1
        for i,g in enumerate(gradient):
            self.m[i]=B1*self.m[i]+(1-B1)*g
            self.v[i]=B2*self.v[i]+(1-B2)*g*g
            mh=self.m[i]/(1-B1**self.updates)
            vh=self.v[i]/(1-B2**self.updates)
            params[i]-=RATE*mh/(math.sqrt(vh)+EPS)
        self._set_params(params)

    def fit(self,episodes):
        for _ in range(EPOCHS):
            for ep in episodes:
                self.fit_episode(ep)

    def checkpoint(self):
        return canonical({
            "schema":"forge.optimizer.o9.trainable-memory.v1",
            "kind":self.kind,
            "dim":self.dim,"parameter_count":self.parameter_count(),
            "write_weights":self.write,"reset_weights":self.reset,
            "content_weights":self.content,"read_weights":self.read,
            "output_weights":self.out,
            "adam_first_moment":self.m,"adam_second_moment":self.v,
            "updates":self.updates,
        })
