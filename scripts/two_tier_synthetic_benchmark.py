"""Paired synthetic engineering benchmark for two-tier evidence.

This is a deterministic synthetic diagnostic, not a Yggdrasil training run,
authenticated corpus result, transfer study or scientific acceptance.
Every arm receives the same paired public observations. State payload budgets
are reported per actual arm, not borrowed from the two-tier candidate.
"""
from __future__ import annotations
import hashlib
import json
from scripts.two_tier_evidence_memory import TwoTierEvidence

SCHEMA="forge.research.two-tier-synthetic-benchmark.v1"
ARMS=("lifetime-only","recent-only","two-tier","no-memory")
STEPS=48
REVERSAL_AT=24

def _hash(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode("ascii")).hexdigest()

class _Arm:
    def __init__(self,mode):
        self.mode=mode
        self.two=TwoTierEvidence() if mode=="two-tier" else None
        self.life=[[[0,0] for _ in range(2)] for _ in range(16)] if mode=="lifetime-only" else None
        self.recent=bytearray([255]*64) if mode=="recent-only" else None

    @property
    def state_bytes(self):
        return {"lifetime-only":128,"recent-only":64,"two-tier":194,"no-memory":0}[self.mode]

    @property
    def checkpoint_bytes(self):
        return {"lifetime-only":166,"recent-only":102,"two-tier":230,"no-memory":0}[self.mode]

    def _recent_counts(self,context,action):
        slot=(context*2+action)*2
        counts=[0,0]
        for outcome in self.recent[slot:slot+2]:
            if outcome in (0,1):counts[outcome]+=1
        return counts

    @staticmethod
    def _winner(a,b,minimum=2):
        if sum(a)<minimum or sum(b)<minimum:return None
        lhs=a[1]*sum(b);rhs=b[1]*sum(a)
        return None if lhs==rhs else (0 if lhs>rhs else 1)

    def choose(self,context):
        if self.mode=="no-memory":return 0
        if self.mode=="lifetime-only":
            a=self.life[context][0];b=self.life[context][1]
            v=self._winner(a,b)
        elif self.mode=="recent-only":
            v=self._winner(self._recent_counts(context,0),self._recent_counts(context,1))
        else:
            v=self.two.choose(context,minimum_support=2)
        return 0 if v is None else v

    def observe_both_actions(self,context,winner):
        for action in (0,1):
            outcome=int(action==winner)
            if self.mode=="lifetime-only":
                counts=self.life[context][action]
                if counts[outcome]<65535:counts[outcome]+=1
            elif self.mode=="recent-only":
                slot=(context*2+action)*2
                first,second=self.recent[slot:slot+2]
                if first==255:self.recent[slot]=outcome
                elif second==255:self.recent[slot+1]=outcome
                else:self.recent[slot:slot+2]=bytes([second,outcome])
            elif self.mode=="two-tier":
                self.two.observe(context,action,outcome)


def run_sparse_fallback():
    """Seed lifetime knowledge, leave recent tiers empty, then add sparse updates."""
    arms={name:_Arm(name) for name in ARMS}
    for name,arm in arms.items():
        if name=="lifetime-only":
            arm.life[2][0][:]=[4,0]
            arm.life[2][1][:]=[0,4]
        elif name=="two-tier":
            arm.two._lifetime[2][0][:]=[4,0]
            arm.two._lifetime[2][1][:]=[0,4]
    before={name:arm.choose(2) for name,arm in arms.items()}
    recent_counts_before={
        "two-tier":[list(arms["two-tier"].two.recent_counts(2,action)) for action in (0,1)],
        "recent-only":[arms["recent-only"]._recent_counts(2,action) for action in (0,1)]}
    # Only two recent observations per action: sufficient to override the
    # recent estimator, but too small to overturn the stronger lifetime prior.
    for _ in range(2):
        for arm in arms.values():
            arm.observe_both_actions(2,0)
    after={name:arm.choose(2) for name,arm in arms.items()}
    return {"lifetime_prior_winner":1,"recent_winner":0,
            "recent_counts_before":recent_counts_before,
            "decision_before_new_recent_evidence":before,
            "decision_after_two_paired_recent_observations":after,
            "lifetime_only_state_bytes":arms["lifetime-only"].state_bytes,
            "recent_only_state_bytes":arms["recent-only"].state_bytes,
            "two_tier_state_bytes":arms["two-tier"].state_bytes,
            "no_memory_state_bytes":arms["no-memory"].state_bytes}


def run_benchmark():
    schedule=[{"step":step,"winner_by_context":[0 if step<REVERSAL_AT else 1,1]}
              for step in range(STEPS)]
    arms={name:_Arm(name) for name in ARMS}
    history={name:{0:[],1:[]} for name in ARMS}
    for row in schedule:
        for name,arm in arms.items():
            for context,winner in enumerate(row["winner_by_context"]):
                history[name][context].append(int(arm.choose(context)==winner))
                arm.observe_both_actions(context,winner)
    result={"schema":SCHEMA,"classification":"SYNTHETIC_ENGINEERING_DIAGNOSTIC",
      "schedule_sha256":_hash(schedule),"steps":STEPS,"reversal_at":REVERSAL_AT,
      "contexts":2,"paired_observation_policy":"both actions revealed equally to every arm",
      "sparse_fallback_scenario":run_sparse_fallback(),
      "arms":{},"authenticated_source":False,"scientific_first_use":False,
      "scientific_gain_verified":False,"deployment_authorized":False,
      "paid_api_calls":0,"model_calls":0}
    for name,arm in arms.items():
        c0=history[name][0];c1=history[name][1];post=c0[REVERSAL_AT:]
        delay=next((i for i,value in enumerate(post) if value),None)
        result["arms"][name]={
          "context0_pre_reversal_accuracy":sum(c0[:REVERSAL_AT])/REVERSAL_AT,
          "context0_post_reversal_accuracy":sum(post)/len(post),
          "context1_stationary_accuracy":sum(c1)/len(c1),
          "context0_adaptation_delay_steps":delay,
          "active_packed_state_bytes":arm.state_bytes,
          "declared_checkpoint_bytes":arm.checkpoint_bytes}
    return result

if __name__=="__main__":
    print(json.dumps(run_benchmark(),sort_keys=True,indent=2))
