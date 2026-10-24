"""L4 fitted real-text 2-word span mechanisms, with fixed backoff.

Every arm observes exactly the same 1,200 TRAIN left/right contexts and
gold missing two words. No learner accesses raw source text or chronology,
line labels, held DEV answers, grammar oracle or trained external weights.
"""
from collections import Counter, defaultdict
import hashlib
import json
import math
from source import canonical

ALPHA=.5
REPAIR_MARGINS=(0.,.5,1.)


def _sortkey(word):
    return word


class CategoricalCounts:
    def __init__(self,kind):
        if kind not in ("parallel","sequential","joint","prior"):
            raise ValueError("L4_UNFROZEN_MODEL_KIND")
        self.kind=kind
        self.tables=[defaultdict(Counter) for _ in range(2 if kind not in ("joint",) else 1)]
        self.global_counts=[Counter() for _ in self.tables]
        self.trained=False

    @staticmethod
    def keys(example,previous="",joint=False):
        left=example["left"][-1]
        right=example["right"][0]
        if joint:
            return ((left,right),(left,),(right,),())
        if previous:
            return ((left,right,previous),(left,previous),(right,previous),
                    (previous,),(left,right),(left,),(right,),())
        return ((left,right),(left,),(right,),())

    def fit(self,train):
        if self.trained or not train:
            raise ValueError("L4_DOUBLE_FIT_OR_NO_TRAIN")
        for row in train:
            for j in range(len(self.tables)):
                value=(
                    " ".join(row["gold"]) if self.kind=="joint"
                    else row["gold"][j]
                )
                prior_previous=(
                    row["gold"][0] if self.kind=="sequential" and j==1 else ""
                )
                self.global_counts[j][value]+=1
                if self.kind=="prior":
                    continue
                for key in self.keys(row,prior_previous,
                                     joint=self.kind=="joint"):
                    self.tables[j][key][value]+=1
        self.trained=True
        return self

    def histogram(self,index,example,previous=""):
        if not self.trained:
            raise ValueError("L4_NOT_FITTED")
        if self.kind=="prior":
            return self.global_counts[index]
        for key in self.keys(example,previous,joint=self.kind=="joint"):
            existing=self.tables[index].get(key)
            if existing:
                return existing
        return self.global_counts[index]

    def best_and_probability(self,index,example,previous=""):
        counts=self.histogram(index,example,previous)
        top=max(sorted(counts),key=lambda x:counts[x])
        num=counts[top]
        total=sum(counts.values())
        prob=(num+ALPHA)/(total+ALPHA*len(self.global_counts[index]))
        return top,prob,1+len(counts)

    def probability(self,index,example,word,previous=""):
        counts=self.histogram(index,example,previous)
        denom=sum(counts.values())+ALPHA*len(self.global_counts[index])
        return (counts.get(word,0)+ALPHA)/denom

    def generate(self,example):
        if self.kind=="joint":
            span,_,ops=self.best_and_probability(0,example)
            tokens=span.split(" ")
            if len(tokens)!=2:
                raise ValueError("L4_BROKEN_FROZEN_JOINT_SPAN")
            return tuple(tokens),ops
        tokens=[]
        ops=0
        for j in range(2):
            prev=tokens[0] if j==1 and self.kind=="sequential" else ""
            word,_,cost=self.best_and_probability(j,example,prev)
            tokens.append(word)
            ops+=cost
        return tuple(tokens),ops

    def checkpoint(self):
        if not self.trained:
            raise ValueError("L4_UNTRAINED_MODEL_CHECKPOINT")
        return canonical({
            "schema":"forge.optimizer.language.l4.smoothed-counts.v1",
            "kind":self.kind,"alpha":ALPHA,
            "tables":[{
                "context":[list(key),dict(sorted(counts.items()))]
                for key,counts in sorted(table.items())
            } for table in self.tables],
            "priors":[dict(sorted(row.items())) for row in self.global_counts],
        })


class SelectiveRepair:
    def __init__(self,parallel,sequential):
        if not parallel.trained or not sequential.trained or \
                parallel.kind!="parallel" or sequential.kind!="sequential":
            raise ValueError("L4_REPAIR_REQUIRES_FULL_PRETRAINED_ARMS")
        self.parallel,self.sequential=parallel,sequential
        self.margin=None

    def propose(self,example,margin):
        pair,work=self.parallel.generate(example)
        first,second=pair
        alt,_,cost=self.sequential.best_and_probability(
            1,example,first)
        work+=cost+2
        original_prob=self.sequential.probability(1,example,second,first)
        better_prob=self.sequential.probability(1,example,alt,first)
        if (alt!=second and
                math.log(better_prob)-math.log(original_prob)>margin):
            return (first,alt),work,1
        return pair,work,0

    def select(self,selection):
        if self.margin is not None:
            raise ValueError("L4_REPAIR_MARGIN_ALREADY_FIXED")
        scores=[]
        for margin in REPAIR_MARGINS:
            exact=sum(self.propose(row,margin)[0]==tuple(row["gold"])
                      for row in selection)
            scores.append((-exact,margin))
        scores.sort()
        self.margin=scores[0][1]
        return self

    def generate(self,example):
        if self.margin is None:
            raise ValueError("L4_REPAIR_THRESHOLD_UNFROZEN")
        return self.propose(example,self.margin)

    def checkpoint(self):
        if self.margin is None:
            raise ValueError("L4_UNSELECTED_REPAIR")
        return canonical({
            "schema":"forge.optimizer.language.l4.selective-repair.v1",
            "margin":self.margin,
            "parallel":json.loads(self.parallel.checkpoint()),
            "sequential":json.loads(self.sequential.checkpoint()),
        })
