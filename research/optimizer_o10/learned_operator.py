"""O10 learned action/observation-conditioned causal state transition operator.

A two-state predictive belief is initialized from the public first cue.
Each visible (action, observation) chooses a LEARNED stochastic 2x2
operator. Only the delayed public query target trains the parameters,
via exact analytic backpropagation through 12 or 24 transitions.
Neither source transition law nor hand-engineered parity is imported.
"""
from __future__ import annotations
import math
import random
from public_source import canonical,query_info

SEEDS=(17,31)
EPOCHS=24
RATE=0.015
B1,B2,EPS=0.9,0.999,1e-8
CLIP=2.0


def sigmoid(z):
    if z >= 0:
        r=math.exp(-min(z,60.0))
        return 1/(1+r)
    r=math.exp(max(z,-60.0))
    return r/(1+r)


def nll(y,p):
    p=max(1e-12,min(1-1e-12,p))
    return -math.log(p if y else 1-p)


class PublicLearnedOperator:
    def __init__(self,seed,action_tied=False):
        if type(seed) is not int or seed not in SEEDS or type(action_tied) is not bool:
            raise ValueError("O10_UNFROZEN_OPERATOR_IDENTITY")
        self.seed=seed
        self.action_tied=action_tied
        rng=random.Random(seed)
        self.theta=[rng.uniform(-1.8,1.8)
                    for _ in range(4 if action_tied else 8)]
        self.init=[rng.uniform(-0.6,0.6) for _ in range(2)]
        self.decoder=[rng.uniform(-0.6,0.6) for _ in range(2)]
        self.updates=0
        self.m=[0.0]*self.parameters()
        self.v=[0.0]*self.parameters()

    def parameters(self):
        return len(self.theta)+4

    def _params(self):
        return self.init+self.theta+self.decoder

    def _set(self,values):
        self.init=values[:2]
        self.theta=values[2:-2]
        self.decoder=values[-2:]
        if len(self._params())!=self.parameters():
            raise ValueError("O10_BAD_PARAMS")

    def _forward(self,ep,erased=False):
        info=query_info(ep)
        cue=info["cue"]
        h=sigmoid(self.init[0]+self.init[1]*cue)
        tape=[]
        for obs,act,_ in ep[:info["query_t"]]:
            slot=(obs if self.action_tied else 2*act+obs)
            k=2*slot
            p0=sigmoid(self.theta[k])
            p1=sigmoid(self.theta[k+1])
            nxt=(1-h)*p0+h*p1
            tape.append((h,p0,p1,k))
            h=nxt
        if erased:
            h=0.5
        prediction=sigmoid(self.decoder[0]+self.decoder[1]*h)
        return prediction,h,tape,info

    def predict(self,ep,erased_query=False):
        return self._forward(ep,erased=erased_query)[0]

    def gradient_episode(self,ep):
        prob,terminal,tape,info=self._forward(ep)
        y=info["target"]
        dout=prob-y
        decoder_gradient=[dout,dout*terminal]
        downstream=dout*self.decoder[1]
        dtheta=[0.0]*len(self.theta)
        for before,p0,p1,index in reversed(tape):
            dtheta[index]+=downstream*(1-before)*p0*(1-p0)
            dtheta[index+1]+=downstream*before*p1*(1-p1)
            downstream*=p1-p0
        cue=info["cue"]
        first=sigmoid(self.init[0]+self.init[1]*cue)
        din=downstream*first*(1-first)
        gradient=[din,din*cue]+dtheta+decoder_gradient
        if not all(math.isfinite(v) for v in gradient):
            raise ValueError("O10_BAD_ANALYTIC_GRADIENT")
        return nll(y,prob),gradient

    def fit_episode(self,ep):
        _,grad=self.gradient_episode(ep)
        norm=math.sqrt(sum(x*x for x in grad))
        if norm>CLIP:
            grad=[x*CLIP/norm for x in grad]
        self.updates+=1
        values=self._params()
        for k,x in enumerate(grad):
            self.m[k]=B1*self.m[k]+(1-B1)*x
            self.v[k]=B2*self.v[k]+(1-B2)*x*x
            m=self.m[k]/(1-B1**self.updates)
            v=self.v[k]/(1-B2**self.updates)
            values[k]-=RATE*m/(math.sqrt(v)+EPS)
        self._set(values)

    def fit(self,eps):
        for _ in range(EPOCHS):
            for ep in eps:
                self.fit_episode(ep)

    def checkpoint(self):
        return canonical({"model":"ACTION_TIED_OPERATOR" if self.action_tied
                          else "LEARNED_MARKOV_OPERATOR",
                          "initial":self.init,"transition_logits":self.theta,
                          "query_decoder":self.decoder,
                          "parameter_count":self.parameters(),
                          "adam_first":self.m,"adam_second":self.v,
                          "updates":self.updates,"seed":self.seed})
