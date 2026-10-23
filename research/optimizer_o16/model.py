"""O16 bounded four-record learned writer, FIFO, reservoir, trained stride."""
import math,random

CAPACITY=4

class Memory:
    def __init__(self,capacity=CAPACITY):
        self.capacity=capacity;self.items=[];self.writes=0;self.skips=0;self.peak=0
    def read(self,t,lag,current):
        return next((v for stamp,v in self.items if stamp==t-lag),current)
    def put(self,t,suit,evict):
        if len(self.items)<self.capacity:
            self.items.append((t,suit));self.writes+=1
        elif evict is None:self.skips+=1
        else:self.items[evict]=(t,suit);self.writes+=1
        self.peak=max(self.peak,len(self.items))
        assert self.peak<=self.capacity

class Writer:
    def __init__(self,lag,capacity=CAPACITY,seed=0):
        self.lag=lag;self.capacity=capacity;self.rng=random.Random(seed)
        self.mem=Memory(capacity);self.fit_updates=0
    def reset_episode(self):self.mem=Memory(self.capacity)
    def read(self,t,suit):return self.mem.read(t,self.lag,suit)
    def write(self,t,suit,train=False):raise NotImplementedError
    def feedback(self,t,reward):pass
    def state(self):return {"type":type(self).__name__,"lag":self.lag,"capacity":self.capacity}

class FIFO(Writer):
    def write(self,t,suit,train=False):
        pos=None if len(self.mem.items)<self.capacity else min(
            range(self.capacity),key=lambda i:self.mem.items[i][0])
        self.mem.put(t,suit,pos)

class Reservoir(Writer):
    def write(self,t,suit,train=False):
        if len(self.mem.items)<self.capacity:self.mem.put(t,suit,None);return
        j=self.rng.randrange(t+1)
        self.mem.put(t,suit,j if j<self.capacity else None)

class Stride(Writer):
    def __init__(self,lag,stride,**kw):super().__init__(lag,**kw);self.stride=stride
    def write(self,t,suit,train=False):
        if t%self.stride:self.mem.put(t,suit,None);return
        pos=None if len(self.mem.items)<self.capacity else min(
            range(self.capacity),key=lambda i:self.mem.items[i][0])
        self.mem.put(t,suit,pos)
    def state(self):return {**super().state(),"stride":self.stride}

class LearnedEviction(Writer):
    """Causal delayed original-reward policy. No future source data at write."""
    LR=.012
    def __init__(self,lag,**kw):
        super().__init__(lag,**kw);self.w=[0.]*6;self.pending={}
    def reset_episode(self):
        super().reset_episode();self.pending={}
    def features(self,t):
        parity=1. if t%2 else -1.
        result=[(None,(1.,0.,0.,0.,parity,0.))]
        for i,(stamp,suit) in enumerate(self.mem.items):
            age=(t-stamp)/max(1,self.lag)
            result.append((i,(0.,1.,min(2.,age),min(2.,abs(age-1.)),0.,parity)))
        return result
    def write(self,t,suit,train=False):
        if len(self.mem.items)<self.capacity:
            self.mem.put(t,suit,None);return
        opts=self.features(t)
        scores=[sum(a*b for a,b in zip(self.w,f)) for _,f in opts]
        m=max(scores);e=[math.exp(max(-40.,min(40.,s-m))) for s in scores]
        z=sum(e);p=[q/z for q in e]
        if train:
            r=self.rng.random();acc=0.;j=len(p)-1
            for i,v in enumerate(p):
                acc+=v
                if r<=acc:j=i;break
            avg=[sum(p[i]*opts[i][1][k] for i in range(len(p))) for k in range(6)]
            self.pending[t]=tuple(opts[j][1][k]-avg[k] for k in range(6))
        else:j=max(range(len(scores)),key=lambda i:(scores[i],-i))
        self.mem.put(t,suit,opts[j][0])
    def feedback(self,t,reward):
        g=self.pending.pop(t-self.lag,None)
        if g is not None and reward!=0:
            adv=1. if reward>0 else -1.
            self.w=[max(-6.,min(6.,v+self.LR*adv*h)) for v,h in zip(self.w,g)]
            self.fit_updates+=1
    def state(self):
        return {**super().state(),"weights":self.w,"fit_updates":self.fit_updates,
                "learning_rule":"delayed_original_reward_softmax_credit","rate":self.LR}
