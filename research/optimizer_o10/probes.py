"""O10 trained decoder probes; all probe targets are PUBLIC-history labels.

After fitting and checkpoint-freezing the original O9 recurrent model,
fit small independent logistic readout heads on *O10_PUBLIC_TRAIN only*.
No backpropagation into the original state model during probing.
"""
import math
from public_source import canonical,query_info

PROBE_EPOCHS=100
PROBE_LR=0.5
PROBE_L2=0.001


def sigmoid(x):
    if x >= 0:
        v=math.exp(-min(x,60))
        return 1/(1+v)
    v=math.exp(max(x,-60))
    return v/(1+v)


def nll(y,p):
    p=max(1e-12,min(1-1e-12,p))
    return -math.log(p if y else 1-p)


class PublicProbe:
    def __init__(self,label):
        self.label=label
        self.weights=None
        self.updates=0

    def fit(self,examples):
        if not examples:
            raise ValueError("O10_PROBE_EMPTY_TRAIN")
        n=len(examples)
        dim=len(examples[0][0])
        if not dim or any(len(x)!=dim or type(y) is not int or y not in (0,1)
                          or not all(math.isfinite(v) for v in x)
                          for x,y in examples):
            raise ValueError("O10_PROBE_PUBLIC_SHAPE")
        self.weights=[0.0]*(dim+1)
        for _ in range(PROBE_EPOCHS):
            grad=[0.0]*(dim+1)
            for x,y in examples:
                p=self.predict(x)
                delta=p-y
                grad[0]+=delta
                for j,feature in enumerate(x):
                    grad[j+1]+=delta*feature
            for j in range(dim+1):
                penalty=(PROBE_L2*self.weights[j] if j else 0.0)
                self.weights[j]-=PROBE_LR*(grad[j]/n+penalty)
            self.updates+=n

    def predict(self,x):
        if self.weights is None:
            raise ValueError("O10_PROBE_NOT_TRAINED")
        if len(x)+1!=len(self.weights):
            raise ValueError("O10_PROBE_INFERENCE_SHAPE")
        return sigmoid(self.weights[0]+sum(w*v for w,v in
                                           zip(self.weights[1:],x)))

    def checkpoint(self):
        return canonical({"name":self.label,"weights":self.weights,
                          "updates":self.updates,
                          "method":"frozen-100-epoch-fullbatch-lr0.5-l2-0.001"})


def hidden(ep,trained_model):
    # Provenance: exact O9 model's query-time recurrent state, no future
    # observation is used by _forward's recurrent updates.
    _,tape,_,_=trained_model._forward(ep)
    state=tape[-1][-1]
    if len(state)!=2 or not all(math.isfinite(v) for v in state):
        raise ValueError("O10_UNEXPECTED_HIDDEN_STATE")
    return tuple(state)


def features(ep,trained_model):
    q=query_info(ep)
    h=hidden(ep,trained_model)
    current=(float(q["query_observation"]),float(q["query_t"]==26))
    quadratic=(h[0],h[1],h[0]*h[0],h[0]*h[1],h[1]*h[1])
    engineered=(float(q["cue"]),float(q["parity"]),
                float(q["cue"]^q["parity"]),float(q["query_t"]==26),
                float(q["query_observation"]))
    return {
        "hidden":h,
        "quadratic_hidden":quadratic,
        "current":current,
        "engineered":engineered,
    }


def probe_examples(eps,trained_model,feature_name,label_name):
    out=[]
    if label_name not in ("cue","parity","target"):
        raise ValueError("O10_UNFROZEN_PROBE_TARGET")
    for ep in eps:
        x=features(ep,trained_model)[feature_name]
        q=query_info(ep)
        out.append((x,q[label_name]))
    return tuple(out)


def evaluate_probe(probe,examples):
    return sum(nll(y,probe.predict(x)) for x,y in examples)/len(examples)


class PublicEpisodicCounts:
    def __init__(self):
        self.table={}
        self.updates=0

    def fit(self,episodes):
        for ep in episodes:
            q=query_info(ep)
            key=(q["cue"],q["parity"])
            stored=self.table.setdefault(key,[0,0])
            stored[q["target"]]+=1
            self.updates+=1

    def predict(self,ep):
        q=query_info(ep)
        neg,pos=self.table.get((q["cue"],q["parity"]),(0,0))
        return (pos+1)/(neg+pos+2)

    def checkpoint(self):
        return canonical({"model":"PUBLIC_EXPLICIT_EPISODIC_COUNTS",
                          "counts":[[list(k),v] for k,v in sorted(self.table.items())],
                          "training_queries":self.updates,
                          "hand_engineered_public_history":True})
