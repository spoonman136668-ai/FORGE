"""O10 differentiably trained phase-composition state over PUBLIC action history.

Public per-episode state: cue0, cue4, selector, counts of actions 0 and 1.
No raw 18-event memory is required. Phase parameters are trained from query
supervision, not supplied parity labels. Phase/cosine and public cue event
positions are *engineered inductive biases*; no discovery or independent
unfamiliar transfer is claimed.

The counterfactual ERASE_PHASE forces phase=0 in an already-trained model.
"""
import math
import random
from public_source import canonical,query_info

EPOCHS=40
LR=.03
BETA1=.9
BETA2=.999
EPS=1e-8
CLIP=2.
SEEDS=(17,31)
VARIANTS=("TRAINED_PHASE_MEMORY","FROZEN_PHASE_TRAINED_HEAD","LINEAR_COUNT_MEMORY")
PARAMS=8


def sigmoid(z):
    if z>=0:
        u=math.exp(-min(60.,z))
        return 1./(1.+u)
    u=math.exp(max(-60.,z))
    return u/(1.+u)


def nll(y,p):
    p=max(1e-12,min(1-1e-12,p))
    return -math.log(p if y else 1-p)


class PublicPhaseComposer:
    def __init__(self,variant,seed):
        if variant not in VARIANTS or type(seed) is not int or seed not in SEEDS:
            raise ValueError("O10_NOT_FROZEN_MODEL")
        self.variant=variant
        self.seed=seed
        rng=random.Random(seed)
        self.w=[rng.uniform(-.5,.5) for _ in range(PARAMS)]
        self.m=[0.]*PARAMS
        self.v=[0.]*PARAMS
        self.updates=0

    def _forward(self,episode,erased=False):
        d=query_info(episode)
        if self.variant=="LINEAR_COUNT_MEMORY":
            x=(1.,float(d["cue"]),float(d["cue4"]),float(d["selector"]),
               d["n1"]/18.,d["n0"]/18.,
               float(d["cue"]*d["selector"]),
               float(d["cue4"]*d["selector"]))
            logit=sum(p*z for p,z in zip(self.w,x))
            return sigmoid(logit),{"x":x}
        p=self.w
        x=(1.,float(d["selector"]),float(d["cue"]),float(d["cue4"]))
        u=sum(p[2+j]*x[j] for j in range(4))
        alpha=sigmoid(u)
        cue=alpha*d["cue"]+(1-alpha)*d["cue4"]
        cue_signed=2*cue-1
        phase=(0. if erased else d["n0"]*p[0]+d["n1"]*p[1])
        cosval=math.cos(phase)
        logit=p[6]+p[7]*cue_signed*cosval
        return sigmoid(logit),{
            "alpha":alpha,"cue_signed":cue_signed,"phase":phase,
            "cosval":cosval,"cue0":d["cue"],"cue4":d["cue4"],
            "n0":d["n0"],"n1":d["n1"],"x":x,
        }

    def predict(self,episode,erased=False):
        return self._forward(episode,erased)[0]

    def loss_gradient(self,episode):
        y=query_info(episode)["target"]
        pred,cache=self._forward(episode)
        delta=pred-y
        if self.variant=="LINEAR_COUNT_MEMORY":
            return nll(y,pred),[delta*x for x in cache["x"]]
        g=[0.]*PARAMS
        cue_signed=cache["cue_signed"]
        p=self.w
        g[6]=delta
        g[7]=delta*cue_signed*cache["cosval"]
        upstream=delta*p[7]
        if self.variant=="TRAINED_PHASE_MEMORY":
            dphase=upstream*cue_signed*(-math.sin(cache["phase"]))
            g[0]=dphase*cache["n0"]
            g[1]=dphase*cache["n1"]
        dcue=upstream*cache["cosval"]*2.0
        dalpha=dcue*(cache["cue0"]-cache["cue4"])
        du=dalpha*cache["alpha"]*(1-cache["alpha"])
        for j in range(4):
            g[2+j]=du*cache["x"][j]
        if not all(math.isfinite(v) for v in g):
            raise ValueError("O10_NONFINITE_COMPOSITION_GRADIENT")
        return nll(y,pred),g

    def step(self,episode):
        _,g=self.loss_gradient(episode)
        length=math.sqrt(sum(x*x for x in g))
        if length>CLIP:
            g=[x*CLIP/length for x in g]
        self.updates+=1
        for j,x in enumerate(g):
            if self.variant=="FROZEN_PHASE_TRAINED_HEAD" and j<2:
                continue
            self.m[j]=BETA1*self.m[j]+(1-BETA1)*x
            self.v[j]=BETA2*self.v[j]+(1-BETA2)*x*x
            mh=self.m[j]/(1-BETA1**self.updates)
            vh=self.v[j]/(1-BETA2**self.updates)
            self.w[j]-=LR*mh/(math.sqrt(vh)+EPS)

    def fit(self,episodes):
        for _ in range(EPOCHS):
            for episode in episodes:
                self.step(episode)

    def checkpoint(self):
        return canonical({
            "model":self.variant,"seed":self.seed,
            "trainable_parameter_count":6 if self.variant=="FROZEN_PHASE_TRAINED_HEAD" else 8,
            "parameters":self.w,
            "optimizer_m":self.m,"optimizer_v":self.v,
            "updates":self.updates,
            "public_memory_state":"cue0 cue4 selector n0 n1",
            "state_scalars":5,
            "stored_public_history_event_count":0,
            "public_cue_event_positions_hand_engineered":True,
            "phase_composition_cosine_hand_engineered":self.variant!="LINEAR_COUNT_MEMORY",
        })
