"""O10 trained conventional public-history models and privileged diagnostic witness.

Engineered program knows a source family law and is NOT a fair learned
architecture. Its success only establishes that the public trajectory
contains enough signal. Generic counts/logistic see the same TRAIN roles.
"""
from __future__ import annotations
from public_source import canonical,query_info,public_program
from learned_operator import sigmoid


class FittedPublicCounts:
    def __init__(self,mode,family=None):
        if mode not in ("PUBLIC_HISTORY","CURRENT","ENGINEERED_WITNESS"):
            raise ValueError("O10_BAD_COUNT_MODE")
        if mode=="ENGINEERED_WITNESS" and not family:
            raise ValueError("O10_WITNESS_FAMILY_REQUIRED")
        self.mode=mode
        self.family=family
        self.table={}
        self.updates=0

    def key(self,ep):
        info=query_info(ep)
        if self.mode=="PUBLIC_HISTORY":
            return (info["cue"],info["parity"],info["current"],
                    info["last_action"])
        if self.mode=="CURRENT":
            return (info["current"],int(info["query_t"]==24))
        return (public_program(ep,self.family),)

    def fit(self,episodes):
        for ep in episodes:
            k=self.key(ep)
            counts=self.table.setdefault(k,[0,0])
            counts[query_info(ep)["target"]]+=1
            self.updates+=1

    def predict(self,ep):
        negatives,positives=self.table.get(self.key(ep),(0,0))
        return (positives+1)/(negatives+positives+2)

    def checkpoint(self):
        return canonical({"mode":self.mode,"family":self.family,
                          "table":[[list(k),counts]
                                   for k,counts in sorted(self.table.items())],
                          "updates":self.updates,
                          "oracle_mechanism_privilege":self.mode=="ENGINEERED_WITNESS"})


class PublicHistoryLogistic:
    def __init__(self):
        self.weights=[0.0]*7
        self.updates=0

    def features(self,ep):
        info=query_info(ep)
        cue,parity=info["cue"],info["parity"]
        return (1.0,float(cue),float(parity),float(info["current"]),
                float(info["last_action"]),float(cue*parity),
                float(info["query_t"]==24))

    def fit(self,episodes):
        count=len(episodes)
        if count==0:
            raise ValueError("O10_NO_TRAIN")
        for _ in range(50):
            gradient=[0.0]*7
            for ep in episodes:
                x=self.features(ep)
                y=query_info(ep)["target"]
                error=sigmoid(sum(w*f for w,f in zip(self.weights,x)))-y
                for j in range(7):
                    gradient[j]+=error*x[j]
            for j in range(7):
                self.weights[j]-=0.3*(
                    gradient[j]/count + (0 if j==0 else 0.001*self.weights[j]))
            self.updates+=count

    def predict(self,ep):
        return sigmoid(sum(w*x for w,x in zip(self.weights,self.features(ep))))

    def checkpoint(self):
        return canonical({"model":"PUBLIC_HISTORY_LOGISTIC",
                          "public_history_hand_features":True,
                          "weights":self.weights,"updates":self.updates})
