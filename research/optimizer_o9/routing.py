"""O9 differentiable, TRAINED episodic write/read routing over public events.

Raw binary observation and public event index are stored as candidate memory.
Both soft write probability and selector-conditioned soft retrieval score are
TRAINABLE parameters. The supervised query gradient propagates through both.
FROZEN_RANDOM_ROUTE fits the identical output head but freezes both routers;
LEARNED_READ_FIXED_WRITE trains reads but fixes all write masks to one.

This is a supervised write/read routing experiment over an externally stored
public trace, NOT self-organized native causal representation or heldout
scientific first use. Features expose public t=0,t=4 position markers.
"""
from __future__ import annotations
import math
import random
from public_source import canonical,query_info

N_FEATURES=7
PARAMS=3*N_FEATURES+3
EPOCHS=40
LR=.03
BETA1=.9
BETA2=.999
EPS=1e-8
CLIP=2.0
VARIANTS=("LEARNED_WRITE_READ","LEARNED_READ_FIXED_WRITE","FROZEN_RANDOM_ROUTE")
SEEDS=(17,31)


def sigmoid(x):
    if x>=0:
        z=math.exp(-min(60.0,x))
        return 1.0/(1.0+z)
    z=math.exp(max(-60.0,x))
    return z/(1.0+z)


def nll(target,p):
    p=min(1-1e-12,max(1e-12,p))
    return -math.log(p if target else 1-p)


class LearnedEpisodicRouting:
    def __init__(self, variant, seed):
        if variant not in VARIANTS or type(seed) is not int or seed not in SEEDS:
            raise ValueError("O9_UNFROZEN_CANDIDATE")
        self.variant=variant
        self.seed=seed
        rng=random.Random(seed)
        # 7 write, 7 base-read, 7 selector-read, 3 output.
        self.params=[rng.uniform(-.25,.25) for _ in range(PARAMS)]
        self.params[-2]=rng.uniform(.2,.6)
        self.m=[0.0]*PARAMS
        self.s=[0.0]*PARAMS
        self.updates=0

    def features(self, ep, q):
        selector=ep[q-1][1]
        rows=[]
        for t in range(q+1):
            obs,act,_=ep[t]
            feat=(1.0,float(obs),float(act==0),float(act==1),
                  float(t==0),float(t==4),t/24.0)
            rows.append((obs,feat))
        return selector,rows

    def _forward(self, ep, erased=False):
        q=query_info(ep)["query_t"]
        selector,rows=self.features(ep,q)
        if erased:
            rows=rows[-1:]
        params=self.params
        logits=[]
        masks=[]
        for obs,x in rows:
            write=(1.0 if self.variant=="LEARNED_READ_FIXED_WRITE"
                   else sigmoid(sum(params[j]*x[j] for j in range(7))))
            read=(sum(params[7+j]*x[j] for j in range(7))+
                  selector*sum(params[14+j]*x[j] for j in range(7)))
            logits.append(read+math.log(max(1e-15,write)))
            masks.append(write)
        hi=max(logits)
        unnorm=[math.exp(z-hi) for z in logits]
        normal=sum(unnorm)
        attention=[z/normal for z in unnorm]
        retrieval=sum(att*float(row[0]) for att,row in zip(attention,rows))
        prob=sigmoid(params[21]+params[22]*(retrieval-.5)+params[23]*selector)
        return prob,retrieval,selector,rows,masks,attention

    def predict(self, ep, erased=False):
        return self._forward(ep,erased)[0]

    def loss_gradient(self, ep):
        target=query_info(ep)["target"]
        prob,ret,selector,rows,masks,attention=self._forward(ep)
        delta=prob-target
        grad=[0.0]*PARAMS
        grad[21]=delta
        grad[22]=delta*(ret-.5)
        grad[23]=delta*selector
        for (obs,x),mask,alpha in zip(rows,masks,attention):
            # derivative of softmax retrieval w.r.t event score and write logit
            chain=delta*self.params[22]*alpha*(obs-ret)
            if self.variant=="LEARNED_WRITE_READ":
                for j in range(7):
                    grad[j]+=chain*(1.0-mask)*x[j]
            if self.variant!="FROZEN_RANDOM_ROUTE":
                for j in range(7):
                    grad[7+j]+=chain*x[j]
                    grad[14+j]+=chain*selector*x[j]
        if self.variant=="FROZEN_RANDOM_ROUTE":
            for j in range(21):
                grad[j]=0.0
        if self.variant=="LEARNED_READ_FIXED_WRITE":
            for j in range(7):
                grad[j]=0.0
        if not all(math.isfinite(g) for g in grad):
            raise ValueError("O9_NONFINITE_ROUTER_GRADIENT")
        return nll(target,prob),grad

    def step(self, ep):
        _,grad=self.loss_gradient(ep)
        norm=math.sqrt(sum(g*g for g in grad))
        if norm>CLIP:
            grad=[g*CLIP/norm for g in grad]
        self.updates+=1
        for j,g in enumerate(grad):
            if self.variant=="FROZEN_RANDOM_ROUTE" and j<21:
                continue
            if self.variant=="LEARNED_READ_FIXED_WRITE" and j<7:
                continue
            self.m[j]=BETA1*self.m[j]+(1-BETA1)*g
            self.s[j]=BETA2*self.s[j]+(1-BETA2)*g*g
            mhat=self.m[j]/(1-BETA1**self.updates)
            shat=self.s[j]/(1-BETA2**self.updates)
            self.params[j]-=LR*mhat/(math.sqrt(shat)+EPS)

    def fit(self, episodes):
        for _ in range(EPOCHS):
            for ep in episodes:
                self.step(ep)

    def checkpoint(self):
        return canonical({
            "schema":"forge.optimizer.o9.episodic-routing.v1",
            "variant":self.variant,"seed":self.seed,
            "parameters":self.params,
            "optimizer_m":self.m,"optimizer_v":self.s,
            "updates":self.updates,
            "parameter_count_total":PARAMS,
            "trainable_parameter_count":(
                3 if self.variant=="FROZEN_RANDOM_ROUTE" else
                17 if self.variant=="LEARNED_READ_FIXED_WRITE" else 24),
            "public_event_store":"all_public_o_t_action_t_t_position_through_query",
        })
