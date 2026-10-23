"""L6 genuine TRAIN-fitted character RNN with full BPTT and Adam.

A trained autoregressive recurrent BASELINE, not a cognitive state learner.
No DEV gold or hidden source used at inference. The RNN sees the same
TRAIN word labels as all other comparators, but not their side context
features; count capacity and training CPU differ and MUST be reported.
"""
import math
import numpy as np
from source import canonical

HIDDEN=20
SEEDS=(17,31)
EPOCHS=8
BATCH=32
LR=.025
CLIP=2.
B1=.9
B2=.999
EPS=1e-8
BEAM=4
MAXLEN=18
ALPHABET="abcdefghijklmnopqrstuvwxyz"
END=26
START=27
VOCAB=28


def encode_word(word):
    if not 5<=len(word)<=MAXLEN or any(c not in ALPHABET for c in word):
        raise ValueError("L6_INVALID_PUBLIC_TRAIN_WORD")
    return [ALPHABET.index(c) for c in word]


class TrainedCharRNN:
    def __init__(self,seed):
        if type(seed) is not int or seed not in SEEDS:
            raise ValueError("L6_UNREGISTERED_RNN_SEED")
        self.seed=seed
        rng=np.random.default_rng(seed)
        self.p={
            "E":rng.normal(0,.075,(VOCAB,HIDDEN)),
            "U":rng.normal(0,.075,(HIDDEN,HIDDEN)),
            "V":rng.normal(0,.075,(HIDDEN,VOCAB-1)),
            "b":np.zeros(HIDDEN,dtype=np.float64),
            "c":np.zeros(VOCAB-1,dtype=np.float64),
        }
        self.m={k:np.zeros_like(v) for k,v in self.p.items()}
        self.v={k:np.zeros_like(v) for k,v in self.p.items()}
        self.updates=0

    @staticmethod
    def _batch(words):
        codes=[encode_word(w) for w in words]
        n=len(words)
        steps=max(len(w)+1 for w in codes)
        xx=np.zeros((steps,n),dtype=np.int64)
        yy=np.zeros((steps,n),dtype=np.int64)
        mask=np.zeros((steps,n),dtype=np.float64)
        for j,codes_ in enumerate(codes):
            seq=[START]+codes_
            target=codes_+[END]
            xx[:len(seq),j]=seq
            yy[:len(target),j]=target
            mask[:len(target),j]=1.
        return xx,yy,mask

    @staticmethod
    def _softmax(a):
        e=np.exp(a-np.max(a,axis=1,keepdims=True))
        return e/np.sum(e,axis=1,keepdims=True)

    def forward(self,words):
        xx,yy,mask=self._batch(words)
        n=xx.shape[1]
        hprev=np.zeros((n,HIDDEN),dtype=np.float64)
        cache=[]
        loss=0.
        denom=float(mask.sum())
        for t in range(xx.shape[0]):
            ht=np.tanh(self.p["E"][xx[t]]+hprev@self.p["U"]+self.p["b"])
            prob=self._softmax(ht@self.p["V"]+self.p["c"])
            loss-=float(np.sum(
                np.log(np.maximum(prob[np.arange(n),yy[t]],1e-15))*mask[t]
            ))
            cache.append((hprev,ht,prob,xx[t],yy[t],mask[t]))
            hprev=ht
        return loss/denom,cache,denom

    def loss_grad(self,words):
        loss,cache,denom=self.forward(words)
        g={k:np.zeros_like(v) for k,v in self.p.items()}
        dhnext=np.zeros((len(words),HIDDEN),dtype=np.float64)
        for hprev,h,prob,x,y,mask in reversed(cache):
            dz=prob.copy()
            dz[np.arange(len(words)),y]-=1.
            dz*=mask[:,None]/denom
            g["V"]+=h.T@dz
            g["c"]+=dz.sum(axis=0)
            dh=dz@self.p["V"].T+dhnext
            da=dh*(1-h*h)
            np.add.at(g["E"],x,da)
            g["U"]+=hprev.T@da
            g["b"]+=da.sum(axis=0)
            dhnext=da@self.p["U"].T
        if not np.isfinite(loss) or any(
                not np.all(np.isfinite(v)) for v in g.values()):
            raise ValueError("L6_NONFINITE_RNN_TRAINING")
        return loss,g

    def step(self,words):
        value,grad=self.loss_grad(words)
        norm=math.sqrt(sum(float(np.sum(g*g)) for g in grad.values()))
        if norm>CLIP:
            grad={k:g*(CLIP/norm) for k,g in grad.items()}
        self.updates+=1
        t=self.updates
        for key,g in grad.items():
            self.m[key]=B1*self.m[key]+(1-B1)*g
            self.v[key]=B2*self.v[key]+(1-B2)*g*g
            self.p[key]-=LR*(self.m[key]/(1-B1**t))/(
                np.sqrt(self.v[key]/(1-B2**t))+EPS)
        return value

    def fit(self,train):
        if len(train)!=900 or self.updates:
            raise ValueError("L6_RNN_TRAIN_BUDGET_DRIFT")
        words=[r["gold"] for r in train]
        for _ in range(EPOCHS):
            for j in range(0,len(words),BATCH):
                self.step(words[j:j+BATCH])
        if self.updates!=EPOCHS*math.ceil(len(words)/BATCH):
            raise ValueError("L6_RNN_TRAIN_UPDATE_COVERAGE")
        return self

    def select_nll(self,selection):
        words=[r["gold"] for r in selection]
        weighted=0.
        total=0
        for i in range(0,len(words),BATCH):
            batch=words[i:i+BATCH]
            value,cache,denom=self.forward(batch)
            weighted+=value*denom
            total+=denom
        return weighted/total

    def predict(self,row):
        prefix=row["prefix"]
        if len(prefix)!=3 or any(c not in ALPHABET for c in prefix):
            raise ValueError("L6_INVALID_PUBLIC_TEST_PREFIX")
        state=np.zeros(HIDDEN,dtype=np.float64)
        for c in "^"+prefix:
            index=START if c=="^" else ALPHABET.index(c)
            state=np.tanh(self.p["E"][index]+state@self.p["U"]+self.p["b"])
        beam=[(prefix,state,0.)]
        completed=[]
        operations=0
        for _ in range(3,MAXLEN+1):
            candidate=[]
            for word,h,score in beam:
                logits=h@self.p["V"]+self.p["c"]
                probs=self._softmax(logits[None,:])[0]
                operations+=HIDDEN*HIDDEN+HIDDEN*(VOCAB-1)
                top=np.argsort(-probs)[:max(BEAM+1,5)]
                for k in top:
                    new_score=score+math.log(max(float(probs[k]),1e-15))
                    if k==END:
                        if len(word)>=5:
                            completed.append((new_score/max(1,len(word)-2)-
                                              .04*(len(word)-3),word))
                    elif len(word)<MAXLEN:
                        new_h=np.tanh(self.p["E"][int(k)]+
                                      h@self.p["U"]+self.p["b"])
                        candidate.append((word+ALPHABET[k],new_h,new_score))
                        operations+=HIDDEN*HIDDEN
            beam=sorted(candidate,key=lambda x:(-x[2],x[0]))[:BEAM]
            if not beam:
                break
        if completed:
            best=max(completed,key=lambda x:(x[0],-len(x[1]),x[1]))[1]
        elif beam:
            best=max(beam,key=lambda x:x[2])[0]
        else:
            best=prefix
        return best,int(max(1,operations))

    def params_count(self):
        return int(sum(x.size for x in self.p.values()))

    def checkpoint(self):
        head=canonical({"schema":"forge.optimizer.language.l6.trained_char_rnn.v1",
                        "seed":self.seed,"updates":self.updates,
                        "parameters":self.params_count(),"optimizer":"Adam",
                        "dtype":"little_endian_float64",
                        "hyperparams":[EPOCHS,BATCH,LR,CLIP,BEAM,MAXLEN]})
        return head+b"".join(
            np.asarray(values[name],dtype="<f8").tobytes()
            for name in sorted(self.p) for values in (self.p,self.m,self.v)
        )
