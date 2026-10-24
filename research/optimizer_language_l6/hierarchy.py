"""L6 TRAIN-discovered hierarchical stem + suffix mechanism and ablation.

No hand-coded English morphemes. Learn suffix library from frequencies,
derive supported stems, then recombine known stems and learned suffix
pieces to create full word forms. The matched inventory ablation forbids
unseen recombinations. Gold never supplied to predict().
"""
from collections import Counter,defaultdict
import math
from source import canonical
from l5_original_models import FittedPrefixLexicon,ContextCounts

MAX_SUFFIXES=32
MAX_STEMS_PER_PREFIX=40
MAX_AFFIXES_PER_STEM=16
ALPHA=.5


class HierarchicalStemAffix:
    def __init__(self,allow_recombination=True):
        self.recombine=bool(allow_recombination)
        self.words=Counter()
        self.suffix_frequency=Counter()
        self.suffixes=[]
        self.stems=Counter()
        self.pairs=Counter()
        self.context=ContextCounts()
        self.prefix_stems=defaultdict(set)
        self.learned=False

    def fit(self,train):
        if self.learned:
            raise ValueError("L6_HIERARCHY_CANNOT_FIT_TWICE")
        self.words.update(row["gold"] for row in train)
        self.context.fit(train)
        candidates=Counter()
        for word,freq in self.words.items():
            for length in range(1,min(5,len(word)-3)+1):
                candidates[word[-length:]]+=freq
        self.suffixes=[
            suffix for suffix,count in sorted(
                candidates.items(),key=lambda row:(-row[1],-len(row[0]),row[0]))
            if count>=3][:MAX_SUFFIXES]
        if not self.suffixes:
            raise ValueError("L6_NO_LEARNED_SUFFIX_LIBRARY")
        stem_support=Counter()
        for word,freq in self.words.items():
            for suffix in self.suffixes:
                if word.endswith(suffix) and len(word)>len(suffix)+2:
                    stem_support[word[:-len(suffix)]]+=freq
        self.suffix_frequency.update(
            {suffix:candidates[suffix] for suffix in self.suffixes}
        )
        for word,freq in self.words.items():
            parsings=[]
            for suffix in self.suffixes:
                if word.endswith(suffix) and len(word)>len(suffix)+2:
                    stem=word[:-len(suffix)]
                    score=(math.log1p(stem_support[stem])+
                           math.log1p(candidates[suffix])+
                           .04*len(suffix))
                    parsings.append((score,len(suffix),stem,suffix))
            if parsings:
                _,_,stem,suffix=max(parsings)
            else:
                stem,suffix=word,""
            self.stems[stem]+=freq
            self.pairs[(stem,suffix)]+=freq
            self.prefix_stems[stem[:3]].add(stem)
            if suffix=="":
                self.suffix_frequency[suffix]+=freq
        self.learned=True
        return self

    def _rank(self,word,stem,suffix,left,right):
        return (
            math.log(self.stems[stem]+ALPHA)+
            math.log(self.suffix_frequency[suffix]+ALPHA)+
            .7*math.log(self.pairs.get((stem,suffix),0)+ALPHA)+
            .2*math.log(self.context.probability(word,left,right))-
            .03*max(0,len(word)-12)
        )

    def predict(self,row):
        if not self.learned:
            raise ValueError("L6_UNFITTED_HIERARCHY")
        prefix,left,right=(row["prefix"],row["left"][-1],row["right"][0])
        stems=sorted(self.prefix_stems.get(prefix,()),key=lambda s:(
            -self.stems[s],s))[:MAX_STEMS_PER_PREFIX]
        if not stems:
            # OOV prefix: do not manufacture source semantics from test gold.
            return prefix,1
        suffixes=sorted(self.suffix_frequency,key=lambda s:(
            -self.suffix_frequency[s],s))[:MAX_AFFIXES_PER_STEM]
        candidates=[]
        operations=0
        for stem in stems:
            for suffix in suffixes:
                word=stem+suffix
                if not word.startswith(prefix) or not (5<=len(word)<=18):
                    continue
                if not self.recombine and word not in self.words:
                    continue
                operations+=1
                candidates.append((self._rank(word,stem,suffix,left,right),
                                   -len(word),word))
        if not candidates:
            return prefix,max(1,operations)
        return max(candidates)[2],max(1,operations)

    def checkpoint(self):
        if not self.learned:
            raise ValueError("L6_UNTRAINED_HIERARCHY_CHECKPOINT")
        return canonical({
            "schema":"forge.optimizer.language.l6.stem-affix-v1",
            "recombine":self.recombine,
            "suffix_library_limit":MAX_SUFFIXES,
            "max_stems":MAX_STEMS_PER_PREFIX,
            "max_suffixes":MAX_AFFIXES_PER_STEM,
            "train_vocab":dict(sorted(self.words.items())),
            "suffix_frequency":dict(sorted(self.suffix_frequency.items())),
            "stems":dict(sorted(self.stems.items())),
            "pairs":[[list(k),n] for k,n in sorted(self.pairs.items())],
            "context":self.context.checkpoint()
        })
