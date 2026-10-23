"""L1 FITTED categorical language realizers; no hidden source-template access.

PARALLEL: each of eight heads conditions ONLY on public meaning features.
AUTOREGRESSIVE: the *same* categorical class/search/smoothing budget per
head, with optional preceding emitted chunk as a seventh input. Both are
trained from identical publicly aligned targets (no target at inference).

Repair freezes both fitted models and uses SELECT-only threshold selection:
propose 8 independent chunks, then verify/replace suspected chunks using
the fully trained left-to-right head. Repair is sequential and its full
cost and both checkpoint sizes MUST be reported.
"""
from collections import Counter, defaultdict
from itertools import combinations
import json
import math

from public_language import FIELDS,SLOTS,canonical

ALPHA=.5
PENALTY=.001
THRESHOLDS=(.05,.15,.30)
FEATURES=tuple(range(6))
CONTEXT_FEATURES=tuple(range(7))


class PublicCategoricalHeads:
    def __init__(self,autoregressive=False,unconditional=False):
        self.autoregressive=autoregressive
        self.unconditional=unconditional
        self.subsets=[]
        self.tables=[]
        self.vocabs=[]
        self.priors=[]
        self.trained=False

    @staticmethod
    def _features(meaning,prev):
        return tuple(meaning)+(prev,)

    def _table(self,examples,i,subset):
        counts=defaultdict(Counter)
        prior=Counter()
        for row in examples:
            data=self._features(row["meaning"],row["slots"][i-1] if i else "")
            key=tuple(data[j] for j in subset)
            output=row["slots"][i]
            counts[key][output]+=1
            prior[output]+=1
        return dict(counts),prior

    @staticmethod
    def _prob(table,prior,vocab,key,target):
        actual=table.get(key,prior)
        return (actual.get(target,0)+ALPHA)/(sum(actual.values())+ALPHA*len(vocab))

    def _eligible_subsets(self):
        if self.unconditional:
            return ((),)
        fields=CONTEXT_FEATURES if self.autoregressive else FEATURES
        return tuple(c for length in range(4)
                     for c in combinations(fields,length))

    def fit(self,train,selection):
        if self.trained or not train or not selection:
            raise ValueError("L1_DOUBLE_OR_EMPTY_FIT")
        candidates=self._eligible_subsets()
        for i in range(8):
            vocab=tuple(sorted({row["slots"][i] for row in train}))
            if not vocab:
                raise ValueError("L1_NO_FITTED_TARGET_VOCAB")
            best=None
            for subset in candidates:
                table,prior=self._table(train,i,subset)
                nll=0.
                for row in selection:
                    prev=row["slots"][i-1] if i else ""
                    features=self._features(row["meaning"],prev)
                    key=tuple(features[j] for j in subset)
                    p=self._prob(table,prior,vocab,key,row["slots"][i])
                    nll-=math.log(p)
                val=nll/len(selection)+PENALTY*len(subset)
                rank=(val,len(subset),subset)
                if best is None or rank<best[0]:
                    best=(rank,subset,table,prior)
            _,subset,table,prior=best
            self.subsets.append(subset)
            self.tables.append(table)
            self.priors.append(prior)
            self.vocabs.append(vocab)
        self.trained=True
        return self

    def distribution(self,i,meaning,previous):
        if not self.trained:
            raise ValueError("L1_FIT_REQUIRED")
        subset=self.subsets[i]
        features=self._features(meaning,previous)
        key=tuple(features[j] for j in subset)
        table=self.tables[i]
        counts=table.get(key,self.priors[i])
        total=sum(counts.values())+ALPHA*len(self.vocabs[i])
        return {
            word:(counts.get(word,0)+ALPHA)/total
            for word in self.vocabs[i]
        }

    def chunk(self,i,meaning,previous):
        probabilities=self.distribution(i,meaning,previous)
        best=max(self.vocabs[i],key=lambda s:(probabilities[s],-self.vocabs[i].index(s)))
        return best,1+len(probabilities)

    def generate(self,meaning):
        words=[]
        operations=0
        for i in range(8):
            prev=words[-1] if self.autoregressive and words else ""
            token,ops=self.chunk(i,meaning,prev)
            words.append(token)
            operations+=ops
        return tuple(words),operations

    def checkpoint(self):
        if not self.trained:
            raise ValueError("L1_UNFITTED_CHECKPOINT")
        return canonical({
            "schema":"forge.optimizer.language.l1.fitted-categorical.v1",
            "autoregressive":self.autoregressive,
            "unconditional":self.unconditional,
            "alpha":ALPHA,
            "subsets":[list(v) for v in self.subsets],
            "tables":[{
                "slot":i,
                "contexts":[{"features":list(context),
                             "targets":[[name,c] for name,c in sorted(counts.items())]}
                            for context,counts in sorted(self.tables[i].items())],
                "prior":[[name,c] for name,c in sorted(self.priors[i].items())],
                "vocab":list(self.vocabs[i]),
            } for i in range(8)],
        })

    def entries(self):
        return sum(len(t) for t in self.tables)


class MemorizedFullMeaning:
    def __init__(self,examples,majority):
        self.table={tuple(x["meaning"]):tuple(x["slots"]) for x in examples}
        self.majority=majority

    def generate(self,meaning):
        key=tuple(meaning)
        if key in self.table:
            return self.table[key],1
        generated,ops=self.majority.generate(meaning)
        return generated,ops+1

    def checkpoint(self):
        return canonical({
            "schema":"forge.optimizer.language.l1.meaning-lookup.v1",
            "pairs":[[list(k),list(v)] for k,v in sorted(self.table.items())],
            "unseen_fallback":"FITTED_UNCONDITIONAL",
            "unconditional_checkpoint":json.loads(self.majority.checkpoint()),
        })


class SelectiveChunkRepair:
    def __init__(self,parallel,ar):
        self.parallel=parallel
        self.ar=ar
        self.threshold=None

    def _propose(self,meaning,threshold):
        proposed,base_ops=self.parallel.generate(meaning)
        tokens=list(proposed)
        repairs=0
        operations=base_ops
        for i in range(8):
            previous=tokens[i-1] if i else ""
            probs=self.ar.distribution(i,meaning,previous)
            best=max(self.ar.vocabs[i],key=lambda s:probs[s])
            operations+=1+len(probs)
            if (probs.get(tokens[i],0.0)<threshold
                    and probs[best]>probs.get(tokens[i],0.0)):
                tokens[i]=best
                repairs+=1
        return tuple(tokens),operations,repairs

    def select(self,selection):
        if self.threshold is not None:
            raise ValueError("L1_REPAIR_THRESHOLD_ALREADY_FROZEN")
        choices=[]
        for threshold in THRESHOLDS:
            hit=sum(self._propose(row["meaning"],threshold)[0]==
                    tuple(row["slots"]) for row in selection)
            choices.append((-hit,threshold))
        choices.sort()
        self.threshold=choices[0][1]
        return self

    def generate(self,meaning):
        if self.threshold is None:
            raise ValueError("L1_SELECT_REPAIR_THRESHOLD_FIRST")
        return self._propose(meaning,self.threshold)

    def checkpoint(self):
        return canonical({
            "schema":"forge.optimizer.language.l1.parallel-selective-repair.v1",
            "threshold":self.threshold,
            "parallel_checkpoint":json.loads(self.parallel.checkpoint()),
            "ar_checkpoint":json.loads(self.ar.checkpoint()),
            "sequential_verification":True,
        })
