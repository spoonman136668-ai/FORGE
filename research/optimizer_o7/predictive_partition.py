"""O7 supervised predictive partitions over *public* histories.

Branching representation is learned by next-public-bit predictive NLL, not
provided latent labels. A deterministic random-topology control sees the
same training history and fits the same Bernoulli leaf outputs. The learned
topology is a compact SUPERVISED decision tree, not a novel general
cognitive architecture. No privileged generator data or future labels
enter feature construction.
"""
from __future__ import annotations

import hashlib
import math
from public_source import canonical

CAPACITIES = (2, 4, 8)
MIN_CHILD = 64
SPLIT_PENALTY_PER_RECORD = 0.001


def sigmoid(z):
    if z >= 0:
        q = math.exp(-min(z, 60.0))
        return 1/(1+q)
    q = math.exp(max(z, -60.0))
    return q/(1+q)


def nll(y, p):
    p = min(1-1e-12, max(1e-12, p))
    return -math.log(p if y == 1 else (1-p))


def smoothed(rows):
    pos = sum(y for _, y in rows)
    return (pos+1)/(len(rows)+2)


class PredictivePartition:
    def __init__(self, cap, randomized=False):
        if type(cap) is not int or cap not in CAPACITIES:
            raise ValueError("O7_CAPACITY_NOT_FROZEN")
        self.cap = cap
        self.randomized = randomized
        self.nodes = []
        self.updates = 0

    def fit(self, examples):
        if not examples or any(len(x) != 6 or len(row) != 2 for row in examples
                               for x, _ in (row,)):
            raise ValueError("O7_PUBLIC_FEATURES")
        if any(any(type(bit) is not int or bit not in (0, 1) for bit in x)
               or type(y) is not int or y not in (0, 1)
               for x, y in examples):
            raise ValueError("O7_BINARY_ONLY")
        self.updates = len(examples)
        self.nodes = [{"path":(), "rows":list(examples)}]
        while len(self.nodes) < self.cap:
            candidates = []
            for leaf_idx, leaf in enumerate(self.nodes):
                path = leaf["path"]
                used = {feature for feature, _ in path}
                rows = leaf["rows"]
                before_prob = smoothed(rows)
                before_cost = sum(nll(y, before_prob) for _, y in rows)
                for feat in range(6):
                    if feat in used:
                        continue
                    left = [r for r in rows if r[0][feat] == 0]
                    right = [r for r in rows if r[0][feat] == 1]
                    if min(len(left), len(right)) < MIN_CHILD:
                        continue
                    left_prob, right_prob = smoothed(left), smoothed(right)
                    after = (sum(nll(y, left_prob) for _, y in left)
                             + sum(nll(y, right_prob) for _, y in right))
                    gain = before_cost-after-SPLIT_PENALTY_PER_RECORD*len(examples)
                    if self.randomized:
                        tag = canonical({"path":path,"feature":feat,
                                         "round":len(self.nodes)})
                        random_rank = int.from_bytes(
                            hashlib.sha256(b"o7-random-splits-v1:"+tag).digest()[:8],
                            "big")
                        ranking = (random_rank, -leaf_idx, -feat)
                    else:
                        ranking = (gain, -leaf_idx, -feat)
                    candidates.append((ranking, gain, leaf_idx,
                                       feat, left, right))
            if not candidates:
                break
            selected = max(candidates, key=lambda row:row[0])
            _, gain, idx, feat, left, right = selected
            if not self.randomized and gain <= 0:
                break
            parent_path = self.nodes[idx]["path"]
            self.nodes[idx:idx+1] = [
                {"path":parent_path+((feat,0),), "rows":left},
                {"path":parent_path+((feat,1),), "rows":right},
            ]
        self.nodes = [{"path":tuple(n["path"]),
                       "prob":smoothed(n["rows"]),
                       "n":len(n["rows"])}
                      for n in self.nodes]

    def predict_feature(self, x):
        for leaf in self.nodes:
            if all(x[feature] == value for feature,value in leaf["path"]):
                return leaf["prob"]
        raise ValueError("O7_NO_MATCHING_LEAF")

    def predict(self, public_episode):
        result = []
        previous_o = previous_a = older_o = older_a = 0
        for obs, action, _ in public_episode:
            x=(obs,action,previous_o,previous_a,older_o,older_a)
            result.append(self.predict_feature(x))
            older_o, older_a = previous_o, previous_a
            previous_o, previous_a = obs, action
        return result

    def checkpoint(self):
        return canonical({"model":"RANDOM_SPLIT_PARTITION" if self.randomized
                          else "LEARNED_PREDICTIVE_PARTITION",
                          "max_leaves":self.cap,
                          "leaves":[{"path":[list(p) for p in node["path"]],
                                     "prob":node["prob"],"n":node["n"]}
                                    for node in self.nodes],
                          "updates":self.updates})


class FixedPublicCounts:
    def __init__(self, feature_indices, name):
        self.indices = tuple(feature_indices)
        self.name = name
        self.table = {}
        self.updates = 0

    def fit(self, examples):
        for x,y in examples:
            key=tuple(x[i] for i in self.indices)
            counts=self.table.setdefault(key,[0,0])
            counts[y]+=1
            self.updates+=1

    def predict_feature(self,x):
        negative,positive=self.table.get(
            tuple(x[i] for i in self.indices),(0,0))
        return (positive+1)/(negative+positive+2)

    def predict(self, public_episode):
        result=[]
        po=pa=oo=oa=0
        for obs,action,_ in public_episode:
            x=(obs,action,po,pa,oo,oa)
            result.append(self.predict_feature(x))
            oo,oa=po,pa
            po,pa=obs,action
        return result

    def checkpoint(self):
        return canonical({"name":self.name,"indices":self.indices,
                          "counts":[[list(k),v] for k,v in sorted(self.table.items())],
                          "updates":self.updates})


class PublicLogistic:
    def __init__(self):
        self.w=[0.0]*7
        self.updates=0

    def fit(self,examples):
        n=len(examples)
        for _ in range(20):
            grad=[0.0]*7
            for x,y in examples:
                feats=(1.0,)+tuple(float(z) for z in x)
                error=sigmoid(sum(a*b for a,b in zip(self.w,feats)))-y
                for j in range(7):
                    grad[j]+=error*feats[j]
            for j in range(7):
                regularizer=0 if j==0 else 0.001*self.w[j]
                self.w[j]-=0.3*(grad[j]/n+regularizer)
            self.updates+=n

    def predict(self,episode):
        out=[]
        po=pa=oo=oa=0
        for obs,action,_ in episode:
            x=(obs,action,po,pa,oo,oa)
            out.append(sigmoid(self.w[0]+sum(self.w[i+1]*x[i]
                                             for i in range(6))))
            oo,oa=po,pa
            po,pa=obs,action
        return out

    def checkpoint(self):
        return canonical({"model":"FITTED_LOGISTIC","weights":self.w,
                          "updates":self.updates})


def public_score(model,episodes):
    total=0.0
    n=0
    for episode in episodes:
        preds=model.predict(episode)
        if len(preds)!=len(episode):
            raise ValueError("O7_OUTPUT_SHAPE")
        for row,p in zip(episode,preds):
            if not math.isfinite(p) or not 0<=p<=1:
                raise ValueError("O7_NONFINITE_PREDICTION")
            total+=nll(row[2],p)
            n+=1
    return total/n
