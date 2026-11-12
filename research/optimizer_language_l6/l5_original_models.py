"""L5 trained lexical, character n-gram and reusable suffix realizers.

At inference all models receive solely public {prefix,left,right}. Target
word and original source line are NEVER read by predict(). All models fit
the same 750 TRAIN target words plus identical context fields.
"""
from collections import Counter,defaultdict
import hashlib
import math
from source import canonical

ARMS=("WORD_PREFIX_LEXICON","CHAR_BIGRAM_BEAM","CHAR_TRIGRAM_BEAM",
      "CHAR_4GRAM_BEAM","CHAR_TRIGRAM_PLUS_CONTEXT","SUFFIX_CHUNK_REUSE")
WIDTH=12
ALPHA=.5
MAXLEN=18
LENGTH_PENALTY=.04


def inputs(row):
    return row["prefix"],row["left"][-1],row["right"][0]


class ContextCounts:
    def __init__(self):
        self.words=Counter()
        self.left=defaultdict(Counter)
        self.right=defaultdict(Counter)
        self.both=defaultdict(Counter)
    def fit(self,train):
        for r in train:
            w=r["gold"]
            left,right=r["left"][-1],r["right"][0]
            self.words[w]+=1
            self.left[left][w]+=1
            self.right[right][w]+=1
            self.both[(left,right)][w]+=1
    def probability(self,word,left,right):
        # No source-only dictionary entries are furnished at inference.
        data=(self.both.get((left,right)),self.left.get(left),
              self.right.get(right),self.words)
        for d in data:
            if d:
                denom=sum(d.values())+ALPHA*(len(self.words)+1)
                return (d.get(word,0)+ALPHA)/denom
        return 1.0
    def checkpoint(self):
        return {"words":dict(sorted(self.words.items())),
                "left":{k:dict(sorted(v.items())) for k,v in sorted(self.left.items())},
                "right":{k:dict(sorted(v.items())) for k,v in sorted(self.right.items())},
                "both":[[list(k),dict(sorted(v.items()))]
                        for k,v in sorted(self.both.items())]}


class FittedPrefixLexicon:
    def __init__(self):
        self.context=ContextCounts()
        self.trained=False
    def fit(self,train):
        self.context.fit(train)
        self.trained=True
        return self
    def predict(self,row):
        prefix,left,right=inputs(row)
        choices=[w for w in self.context.words if w.startswith(prefix)]
        if not choices:
            return prefix,1
        word=max(sorted(choices),key=lambda w:(
            math.log(1+self.context.words[w])+
            .35*math.log(self.context.probability(w,left,right))))
        return word,len(choices)
    def checkpoint(self):
        return canonical({"model":"L5_FITTED_WORD_PREFIX","context":self.context.checkpoint()})


class FittedCharGram:
    def __init__(self,order):
        if order not in (2,3,4):
            raise ValueError("L5_BAD_NGRAM_ORDER")
        self.order=order
        self.hist={j:defaultdict(Counter) for j in range(1,order+1)}
        self.len_hist=Counter()
        self.train_updates=0
    def fit(self,train):
        for r in train:
            word=r["gold"]
            self.len_hist[len(word)]+=1
            padded="^"*(self.order-1)+word+"$"
            for k in range(self.order-1,len(padded)):
                for level in range(1,self.order+1):
                    history=padded[max(0,k-level+1):k]
                    self.hist[level][history][padded[k]]+=1
                self.train_updates+=1
        return self
    def probs(self,word):
        padded="^"*(self.order-1)+word
        for level in range(self.order,0,-1):
            previous=padded[-(level-1):] if level>1 else ""
            row=self.hist[level].get(previous)
            if row:
                denom=sum(row.values())+ALPHA*27
                return {c:(row.get(c,0)+ALPHA)/denom for c in "abcdefghijklmnopqrstuvwxyz$"}
        return {c:1/27 for c in "abcdefghijklmnopqrstuvwxyz$"}
    def score(self,word,logsum):
        l=len(word)
        prior=(self.len_hist.get(l,0)+ALPHA)/(
            sum(self.len_hist.values())+ALPHA*19)
        return logsum/max(1,l-2)+math.log(prior)-LENGTH_PENALTY*(l-3)
    def candidates(self,prefix):
        if len(prefix)!=3 or not prefix.isalpha() or not prefix.isascii():
            raise ValueError("L5_INVALID_PUBLIC_PREFIX")
        beam=[(prefix,0.)]
        completed=[]
        operations=0
        for depth in range(3,MAXLEN+1):
            next_beam=[]
            for word,logp in beam:
                dist=self.probs(word)
                operations+=len(dist)
                for ch,prob in dist.items():
                    value=logp+math.log(prob)
                    if ch=="$":
                        if len(word)>=5:
                            completed.append((word,self.score(word,value)))
                    elif len(word)<MAXLEN:
                        next_beam.append((word+ch,value))
            next_beam.sort(key=lambda v:(-v[1],v[0]))
            beam=next_beam[:WIDTH]
            if not beam:
                break
        if not completed:
            completed=[(word,self.score(word,score)) for word,score in beam]
        completed.sort(key=lambda v:(-v[1],v[0]))
        return completed[:WIDTH],operations
    def predict(self,row):
        prefix,_,_=inputs(row)
        candidates,ops=self.candidates(prefix)
        return candidates[0][0],ops
    def checkpoint(self):
        return canonical({"model":"L5_FITTED_CHAR_NGRAM","order":self.order,
            "alpha":ALPHA,"beam":WIDTH,"maxlen":MAXLEN,
            "length_penalty":LENGTH_PENALTY,
            "length_counts":dict(sorted(self.len_hist.items())),
            "ngram_counts":{str(level):[
                [context,dict(sorted(counts.items()))]
                for context,counts in sorted(table.items())]
                for level,table in sorted(self.hist.items())}})


class ContextualCharGram:
    def __init__(self):
        self.chars=FittedCharGram(3)
        self.context=ContextCounts()
    def fit(self,train):
        self.chars.fit(train)
        self.context.fit(train)
        return self
    def predict(self,row):
        prefix,left,right=inputs(row)
        options,ops=self.chars.candidates(prefix)
        winner=max(options,key=lambda v:(
            v[1]+.35*math.log(self.context.probability(v[0],left,right)),
            -len(v[0]),v[0]))
        return winner[0],ops+len(options)
    def checkpoint(self):
        return canonical({"model":"L5_CONTEXTUAL_CHAR_TRIGRAM",
            "char":self.chars.checkpoint().decode("ascii"),
            "context":self.context.checkpoint(),
            "context_weight":.35})


class FittedSuffixReuse:
    def __init__(self):
        self.bucket=defaultdict(Counter)
        self.global_suffix=Counter()
    def fit(self,train):
        for r in train:
            word=r["gold"]
            suffix=word[3:]
            if 1<=len(suffix)<=5:
                self.bucket[word[:3]][suffix]+=1
                self.global_suffix[suffix]+=1
        return self
    def predict(self,row):
        prefix,_,_=inputs(row)
        counts=self.bucket.get(prefix) or self.global_suffix
        if not counts:
            return prefix,1
        chosen=max(sorted(counts),key=lambda s:counts[s])
        return prefix+chosen,len(counts)
    def checkpoint(self):
        return canonical({"model":"L5_FITTED_REUSABLE_SUFFIX",
            "bucket":{k:dict(sorted(v.items())) for k,v in sorted(self.bucket.items())},
            "global":dict(sorted(self.global_suffix.items()))})


def build_all(train):
    return {
        "WORD_PREFIX_LEXICON":FittedPrefixLexicon().fit(train),
        "CHAR_BIGRAM_BEAM":FittedCharGram(2).fit(train),
        "CHAR_TRIGRAM_BEAM":FittedCharGram(3).fit(train),
        "CHAR_4GRAM_BEAM":FittedCharGram(4).fit(train),
        "CHAR_TRIGRAM_PLUS_CONTEXT":ContextualCharGram().fit(train),
        "SUFFIX_CHUNK_REUSE":FittedSuffixReuse().fit(train),
    }
