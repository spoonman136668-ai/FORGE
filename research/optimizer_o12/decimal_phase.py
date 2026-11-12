"""O12 deterministic high-precision mirror of the ORIGINAL O10 phase equations.

Everything is fixed before accessing O12 TRAIN/DIAGNOSTIC:
- Decimal precision 34, ROUND_HALF_EVEN
- deterministic 35-term signed-phase-reduced Taylor sin/cos
- Decimal exp/sqrt/ln and original O10 Adam / clip2
- optional separate preregistered phase-gradient L2 clip at 0.125

This tests reproducible *numeric implementations*, not parity learning
or a scientifically new model. Public cue0/o4 and action counts are
engineered, exactly as in O10; no hidden simulator state is supplied.
"""
from decimal import Decimal as D, Context, ROUND_HALF_EVEN, localcontext
import math
import random
from public_source import canonical, query_info

CTX=Context(prec=34,rounding=ROUND_HALF_EVEN)
PI=D("3.14159265358979323846264338327950288419716939937510")
TERMS=35
EPOCHS=40
SEEDS=(17,31)
PHASE_CLIP=D("0.125")
GLOBAL_CLIP=D("2")
RATE=D("0.03")
B1=D("0.9")
B2=D("0.999")
EPS=D("0.00000001")
VARIANTS=("DECIMAL_PHASE_34","DECIMAL_PHASE_34_CONDITIONED")


def fixed_sin_cos(phase):
    """Deterministic, fixed-length, bounded series; no native libm."""
    with localcontext(CTX):
        two_pi=PI*D(2)
        x=phase%two_pi
        if x>PI:
            x-=two_pi
        if x < -PI:
            x+=two_pi
        sq=x*x
        sin_term=x
        cos_term=D(1)
        sine=x
        cosine=D(1)
        for j in range(1,TERMS):
            sin_term=-(sin_term*sq)/(D(2*j)*D(2*j+1))
            cos_term=-(cos_term*sq)/(D(2*j-1)*D(2*j))
            sine+=sin_term
            cosine+=cos_term
        return +sine,+cosine


def sigmoid(value):
    with localcontext(CTX):
        z=max(D("-60"),min(D("60"),value))
        return +(D(1)/(D(1)+(-z).exp()))


def nll(bit,prob):
    with localcontext(CTX):
        p=max(D("1e-28"),min(D(1)-D("1e-28"),prob))
        return +(-(p if bit else (D(1)-p)).ln())


class DecimalPhase:
    def __init__(self,variant,seed):
        if variant not in VARIANTS or type(seed) is not int or seed not in SEEDS:
            raise ValueError("O12_UNFROZEN_DECIMAL_MODEL")
        self.variant=variant
        self.seed=seed
        rng=random.Random(seed)
        self.w=[D.from_float(rng.uniform(-.5,.5)) for _ in range(8)]
        self.m=[D(0)]*8
        self.v=[D(0)]*8
        self.updates=0

    def _forward(self,ep,erased=False):
        d=query_info(ep)
        p=self.w
        one=D(1)
        x=(one,D(d["selector"]),D(d["cue"]),D(d["cue4"]))
        u=sum((p[2+j]*x[j] for j in range(4)),D(0))
        alpha=sigmoid(u)
        cue=alpha*D(d["cue"])+(one-alpha)*D(d["cue4"])
        signed=2*cue-one
        phase=D(0) if erased else D(d["n0"])*p[0]+D(d["n1"])*p[1]
        sine,cosine=fixed_sin_cos(phase)
        logit=p[6]+p[7]*signed*cosine
        return sigmoid(logit),{
            "x":x,"alpha":alpha,"cue_signed":signed,
            "cue0":D(d["cue"]),"cue4":D(d["cue4"]),
            "phase":phase,"sine":sine,"cosine":cosine,
            "n0":D(d["n0"]),"n1":D(d["n1"]),
        }

    def predict(self,ep,erased=False):
        with localcontext(CTX):
            return self._forward(ep,erased)[0]

    def loss_gradient(self,ep):
        with localcontext(CTX):
            d=query_info(ep)
            pred,z=self._forward(ep)
            delta=pred-D(d["target"])
            grad=[D(0)]*8
            grad[6]=delta
            grad[7]=delta*z["cue_signed"]*z["cosine"]
            upstream=delta*self.w[7]
            dphase=upstream*z["cue_signed"]*(-z["sine"])
            grad[0]=dphase*z["n0"]
            grad[1]=dphase*z["n1"]
            dcue=upstream*z["cosine"]*2
            dalpha=dcue*(z["cue0"]-z["cue4"])
            du=dalpha*z["alpha"]*(D(1)-z["alpha"])
            for j in range(4):
                grad[2+j]=du*z["x"][j]
            if any(not g.is_finite() for g in grad):
                raise ValueError("O12_NONFINITE_GRADIENT")
            return nll(d["target"],pred),grad

    def step(self,ep):
        with localcontext(CTX):
            _,grad=self.loss_gradient(ep)
            if self.variant=="DECIMAL_PHASE_34_CONDITIONED":
                phase_norm=(grad[0]**2+grad[1]**2).sqrt()
                if phase_norm>PHASE_CLIP:
                    grad[0]*=PHASE_CLIP/phase_norm
                    grad[1]*=PHASE_CLIP/phase_norm
            norm=sum((g*g for g in grad),D(0)).sqrt()
            if norm>GLOBAL_CLIP:
                grad=[g*GLOBAL_CLIP/norm for g in grad]
            self.updates+=1
            discount1=D(1)-B1**self.updates
            discount2=D(1)-B2**self.updates
            for j,g in enumerate(grad):
                self.m[j]=B1*self.m[j]+(D(1)-B1)*g
                self.v[j]=B2*self.v[j]+(D(1)-B2)*g*g
                mh=self.m[j]/discount1
                vh=self.v[j]/discount2
                self.w[j]-=RATE*mh/(vh.sqrt()+EPS)

    def fit(self,batch):
        for _ in range(EPOCHS):
            for ep in batch:
                self.step(ep)

    def checkpoint(self):
        return canonical({
            "schema":"forge.optimizer.o12.decimalphase.v1",
            "variant":self.variant,"seed":self.seed,
            "parameters":[str(p) for p in self.w],
            "adam_m":[str(p) for p in self.m],
            "adam_v":[str(p) for p in self.v],
            "updates":self.updates,
            "numeric_context":"decimal34-round-half-even-35term-trig",
            "phase_gradient_clip":(
                str(PHASE_CLIP) if self.variant=="DECIMAL_PHASE_34_CONDITIONED"
                else None),
            "public_state_scalars":5,"stored_public_event_count":0,
        })
