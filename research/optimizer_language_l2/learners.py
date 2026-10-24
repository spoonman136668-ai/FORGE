"""L2 fitted conditional categorical chunk realizers, source-oracle BLIND.

Both parallel and sequential controls get the EXACT SAME supervised
semantic IDs and gold aligned chunks during FIT, and no hidden source
relation or gold target at DEV inference. Feature sets selected from FIT
SELECT only, with fixed maximum capacities 3 or 4. None is a trained
recurrent/state-space/transformer model: this is synthetic mechanism triage.
"""
from collections import Counter,defaultdict
from itertools import combinations
import json
import math
from public_source import canonical

ALPHA=.5
PENALTY=.001
THRESHOLDS=(.05,.15,.30)


class PublicChunkLearner:
    def __init__(self,max_features,autoregressive=False):
        if type(max_features) is not int or max_features not in (0,3,4):
            raise ValueError("L2_UNREGISTERED_CAPACITY")
        if max_features==4 and autoregressive:
            raise ValueError("L2_UNREGISTERED_HIGH_CAPACITY_AR")
        self.capacity=max_features
        self.autoregressive=autoregressive
        self.subsets=[]
        self.tables=[]
        self.priors=[]
        self.vocabs=[]
        self.selected_losses=[]
        self.trained=False

    def features(self,meaning,previous):
        if len(meaning)!=6 or len(previous)>48:
            raise ValueError("L2_INVALID_PUBLIC_MEANING_OR_CONTEXT")
        return tuple(meaning)+(previous,)

    def candidate_subsets(self):
        fields=range(7 if self.autoregressive else 6)
        return tuple(s for n in range(self.capacity+1)
                     for s in combinations(fields,n))

    def fit(self,train,selection):
        if self.trained or not train or not selection:
            raise ValueError("L2_DOUBLE_OR_EMPTY_TRAIN")
        candidates=self.candidate_subsets()
        for i in range(8):
            vocab=tuple(sorted({row["slots"][i] for row in train}))
            if not vocab:
                raise ValueError("L2_MISSING_TRAIN_VOCAB")
            best=None
            for subset in candidates:
                counts=defaultdict(Counter)
                prior=Counter()
                for row in train:
                    prev=row["slots"][i-1] if i else ""
                    input_fields=self.features(row["meaning"],prev)
                    key=tuple(input_fields[j] for j in subset)
                    token=row["slots"][i]
                    counts[key][token]+=1
                    prior[token]+=1
                score=0.
                for row in selection:
                    prev=row["slots"][i-1] if i else ""
                    input_fields=self.features(row["meaning"],prev)
                    key=tuple(input_fields[j] for j in subset)
                    hist=counts.get(key,prior)
                    prob=(hist.get(row["slots"][i],0)+ALPHA)/(
                        sum(hist.values())+ALPHA*len(vocab))
                    score-=math.log(prob)
                selection_nll=score/len(selection)+PENALTY*len(subset)
                rank=(selection_nll,len(subset),subset)
                if best is None or rank<best[0]:
                    best=(rank,subset,dict(counts),prior)
            rank,subset,table,prior=best
            self.subsets.append(subset)
            self.tables.append(table)
            self.priors.append(prior)
            self.vocabs.append(vocab)
            self.selected_losses.append(rank[0])
        self.trained=True
        return self

    def distribution(self,i,meaning,previous):
        if not self.trained or i<0 or i>=8:
            raise ValueError("L2_UNFITTED_OR_BAD_SLOT")
        inputs=self.features(meaning,previous)
        key=tuple(inputs[j] for j in self.subsets[i])
        counts=self.tables[i].get(key,self.priors[i])
        normal=sum(counts.values())+ALPHA*len(self.vocabs[i])
        return {v:(counts.get(v,0)+ALPHA)/normal for v in self.vocabs[i]}

    def token(self,i,meaning,previous):
        probs=self.distribution(i,meaning,previous)
        tok=max(self.vocabs[i],key=lambda z:(probs[z],-self.vocabs[i].index(z)))
        return tok,1+len(probs)

    def generate(self,meaning):
        words=[]
        ops=0
        for i in range(8):
            prev=(words[i-1] if self.autoregressive and i>0 else "")
            word,work=self.token(i,meaning,prev)
            words.append(word)
            ops+=work
        return tuple(words),ops

    def checkpoint(self):
        if not self.trained:
            raise ValueError("L2_UNFITTED_CHECKPOINT")
        return canonical({
            "schema":"forge.optimizer.language.l2.fitted-count-heads.v1",
            "feature_capacity":self.capacity,"autoregressive":self.autoregressive,
            "alpha":ALPHA,"selection_nll":self.selected_losses,
            "subsets":[list(s) for s in self.subsets],
            "tables":[{"slot":i,"contexts":[{
                "features":list(key),
                "counts":[[tok,num] for tok,num in sorted(counts.items())]
            } for key,counts in sorted(table.items())],
            "vocab":list(self.vocabs[i]),
            "prior":[[key,num] for key,num in sorted(self.priors[i].items())]}
            for i,table in enumerate(self.tables)]
        })

    def context_entries(self):
        return sum(len(t) for t in self.tables)


class FittedTupleLookup:
    def __init__(self,train,fallback):
        self.table={tuple(row["meaning"]):tuple(row["slots"]) for row in train}
        self.fallback=fallback

    def generate(self,meaning):
        found=self.table.get(tuple(meaning))
        if found is not None:
            return found,1
        words,ops=self.fallback.generate(meaning)
        return words,ops+1

    def checkpoint(self):
        return canonical({
            "schema":"forge.optimizer.language.l2.tuple-lookup-control.v1",
            "records":[[list(s),list(t)] for s,t in sorted(self.table.items())],
            "fallback_checkpoint":json.loads(self.fallback.checkpoint())
        })


class FittedSelectiveRepair:
    def __init__(self,parallel,sequential):
        if not parallel.trained or not sequential.trained:
            raise ValueError("L2_REPAIR_REQUIRES_TWO_TRAINED_MODELS")
        self.parallel=parallel
        self.sequential=sequential
        self.threshold=None

    def propose(self,meaning,threshold):
        base,ops=self.parallel.generate(meaning)
        chunks=list(base)
        repairs=0
        for i in range(8):
            prev=chunks[i-1] if i else ""
            probs=self.sequential.distribution(i,meaning,prev)
            best=max(self.sequential.vocabs[i],
                     key=lambda x:probs[x])
            ops+=1+len(probs)
            if probs.get(chunks[i],0)<threshold and \
                    probs[best]>probs.get(chunks[i],0):
                chunks[i]=best
                repairs+=1
        return tuple(chunks),ops,repairs

    def select(self,selection):
        if self.threshold is not None:
            raise ValueError("L2_REPAIR_THRESHOLD_ALREADY_CHOSEN")
        scores=[]
        for threshold in THRESHOLDS:
            exact=sum(self.propose(row["meaning"],threshold)[0]==
                      tuple(row["slots"]) for row in selection)
            scores.append((-exact,threshold))
        scores.sort()
        self.threshold=scores[0][1]
        return self

    def generate(self,meaning):
        if self.threshold is None:
            raise ValueError("L2_UNSELECTED_VERIFIER")
        return self.propose(meaning,self.threshold)

    def checkpoint(self):
        if self.threshold is None:
            raise ValueError("L2_UNSELECTED_VERIFIER")
        return canonical({
            "schema":"forge.optimizer.language.l2.selective-repair.v1",
            "threshold":self.threshold,
            "proposer":json.loads(self.parallel.checkpoint()),
            "verifier":json.loads(self.sequential.checkpoint()),
            "critical_path_stages":9
        })
