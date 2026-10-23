"""Record-specific source-reward eligibility learning, public development ONLY."""
from __future__ import annotations
import math
from research.optimizer_o16.model import Writer,CAPACITY

class RecordCredit(Writer):
    """Fixed linear 8-feature REINFORCE writer; no future target or oracle."""
    LR=0.01
    def __init__(self,lag,capacity=CAPACITY,seed=0,feature_ablation=False):
        super().__init__(lag,capacity=capacity,seed=seed)
        self.w=[0.0]*8
        self.feature_ablation=feature_ablation
        self.use_counts={}
        self.pending={}
        self.reward_events=0
        self.mean_source_sign=0.0
        self.fit_updates=0
        self.fit_choices=0
        self.peak_fit_eligibility=0

    def reset_episode(self):
        super().reset_episode()
        self.use_counts={}
        self.pending={}

    def read(self,t,current):
        wanted=t-self.lag
        for stamp,value in self.mem.items:
            if stamp==wanted:
                self.use_counts[stamp]=min(65535,self.use_counts.get(stamp,0)+1)
                return value
        return current

    def options(self,t,incoming):
        # SKIP plus one actual legal eviction for EACH resident record.
        scale=max(1,self.lag)
        entries=[(None,(1.,0.,0.,0.,0.,0.,min(1.,t/51.),0.))]
        for i,(stamp,suit) in enumerate(self.mem.items):
            age=t-stamp
            feats=[0.,1.,min(2.,age/scale),
                   min(2.,abs(age-self.lag)/scale),float(suit==incoming),
                   min(1.,self.use_counts.get(stamp,0)/2.),
                   min(1.,t/51.),i/max(1,self.capacity-1)]
            if self.feature_ablation:
                for j in (2,3,4,5):feats[j]=0.
            entries.append((i,tuple(feats)))
        return entries

    def write(self,t,suit,train=False):
        assert type(t) is int and t>=0 and type(suit) is int and 0<=suit<4
        if len(self.mem.items)<self.capacity:
            self.mem.put(t,suit,None)
            self.use_counts[t]=0
            return
        opts=self.options(t,suit)
        scores=[sum(w*v for w,v in zip(self.w,features))
                for _,features in opts]
        hi=max(scores)
        raw=[math.exp(max(-40.,min(40.,s-hi))) for s in scores]
        denom=sum(raw)
        probs=[r/denom for r in raw]
        if train:
            threshold=self.rng.random()
            acc=0.
            chosen=len(opts)-1
            for i,p in enumerate(probs):
                acc+=p
                if threshold<=acc:
                    chosen=i
                    break
            expectation=[sum(probs[i]*opts[i][1][k]
                             for i in range(len(opts))) for k in range(8)]
            self.pending[t]=tuple(opts[chosen][1][k]-expectation[k]
                                  for k in range(8))
            self.fit_choices+=1
            self.peak_fit_eligibility=max(self.peak_fit_eligibility,len(self.pending))
            if len(self.pending)>self.lag+1:
                raise ValueError("O18_ELIGIBILITY_EXCEEDS_FROZEN_HORIZON")
        else:
            chosen=max(range(len(opts)),key=lambda i:(scores[i],-i))
        evicted=opts[chosen][0]
        if evicted is not None:
            old_stamp=self.mem.items[evicted][0]
            self.use_counts.pop(old_stamp,None)
        self.mem.put(t,suit,evicted)
        if evicted is not None:
            self.use_counts[t]=0
        if len(self.use_counts)>self.capacity:
            raise ValueError("O18_RECORD_USAGE_EXCEEDS_FOUR")

    def feedback(self,t,reward):
        # The source has already emitted reward for step(t). Credit only prior
        # eligible action-gradient traces. No queried source-private target.
        if reward!=0:
            sign=1.0 if reward>0 else -1.0
            advantage=sign-self.mean_source_sign
            eligible=[grad for stamp,grad in self.pending.items()
                      if t-self.lag<=stamp<t]
            if eligible:
                mean_gradient=[sum(g[k] for g in eligible)/len(eligible)
                               for k in range(8)]
                self.w=[max(-6.,min(6.,w+self.LR*advantage*g))
                        for w,g in zip(self.w,mean_gradient)]
                self.fit_updates+=1
            self.reward_events+=1
            self.mean_source_sign+=(sign-self.mean_source_sign)/self.reward_events
        # Clean as time advances; never retain unbounded training history.
        self.pending={stamp:grad for stamp,grad in self.pending.items()
                      if stamp>=t-self.lag}

    def state(self):
        return {**super().state(),
          "kind":"LEARNED_PER_RECORD_DELAYED_SOURCE_REWARD_POLICY",
          "eight_trainable_weights":list(self.w),
          "record_features_ablated":self.feature_ablation,
          "fit_reward_events":self.reward_events,
          "fit_updates":self.fit_updates,
          "fit_write_choice_events":self.fit_choices,
          "peak_training_eligibility_records":self.peak_fit_eligibility,
          "train_mean_real_source_reward_sign":self.mean_source_sign,
          "LR":self.LR,
          "credit_horizon_from_public_learned_lag":self.lag}
