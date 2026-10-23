"""O17 four-logit genuine-feedback phase write gate, frozen test candidate."""
import math
from research.optimizer_o16.model import Writer,CAPACITY

class PhaseGate(Writer):
    LR=0.008
    BASELINE=-0.5
    def __init__(self,lag,capacity=CAPACITY,seed=0,phase_shift=0):
        super().__init__(lag,capacity=capacity,seed=seed)
        self.logits=[0.0]*4
        self.pending={}
        self.phase_shift=phase_shift
        self.fit_updates=0
        self.fit_reward_events=0
        self.fit_write_events=0

    def reset_episode(self):
        super().reset_episode()
        self.pending={}

    def write(self,t,suit,train=False):
        assert 0<=suit<4 and isinstance(t,int) and t>=0
        if len(self.mem.items)<self.capacity:
            self.mem.put(t,suit,None)
            return
        phase=(t+self.phase_shift)%4
        prob=1./(1.+math.exp(-max(-6.,min(6.,self.logits[phase]))))
        decision=(self.rng.random()<prob) if train else (prob>=0.5)
        if train:
            # Score-function derivative d(log p(a|state))/d(logit).
            # Causal timestamp is retained; no outcome observed at write time.
            self.pending[t]=(phase,(1.0 if decision else 0.0)-prob)
            self.fit_write_events+=1
        eviction=(min(range(self.capacity),key=lambda i:self.mem.items[i][0])
                  if decision else None)
        self.mem.put(t,suit,eviction)

    def feedback(self,t,reward):
        # Called only AFTER the real source step. Reward for read at t can
        # credit prior choices in [t-lag,t), never present/future writes.
        if reward!=0 and self.pending:
            self.fit_reward_events+=1
            advantage=(1.0 if reward>0 else -1.0)-self.BASELINE
            changes=[0.0]*4
            eligible=0
            for stamp,(phase,grad) in self.pending.items():
                if t-self.lag<=stamp<t:
                    changes[phase]+=advantage*grad/max(1,self.lag)
                    eligible+=1
            if eligible:
                self.logits=[max(-6.,min(6.,v+self.LR*delta))
                             for v,delta in zip(self.logits,changes)]
                self.fit_updates+=1
        # Retain only pending choices that could affect a future source read.
        self.pending={s:v for s,v in self.pending.items() if s>=t-self.lag}

    def state(self):
        return {**super().state(),
                "kind":"FOUR_PHASE_HANDDESIGNED_BASIS_LEARNED_WRITE_SKIP",
                "phase_logits":list(self.logits),
                "phase_shift":self.phase_shift,
                "fit_updates":self.fit_updates,
                "fit_source_reward_events":self.fit_reward_events,
                "fit_write_choices":self.fit_write_events,
                "LR":self.LR,
                "score_sign_baseline":self.BASELINE,
                "readout":"deterministic_prob_ge_half_oldest_eviction"}
