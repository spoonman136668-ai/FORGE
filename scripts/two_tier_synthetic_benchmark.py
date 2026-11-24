"""Paired synthetic engineering benchmark with explicit abstention.

Synthetic only: not a Yggdrasil training run, authenticated corpus, transfer study
or scientific acceptance. Every strategy receives the same paired observations.
Abstaining is counted as zero coverage, never credited as a correct default.
"""
from __future__ import annotations
import hashlib
import json
from scripts.two_tier_evidence_memory import TwoTierEvidence

SCHEMA="forge.research.two-tier-synthetic-benchmark.v2"
ARMS=("lifetime-only","recent-only","two-tier","no-memory")
WARMUP_PAIRS=6
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
        if self.mode=="no-memory":return None
        if self.mode=="lifetime-only":
            a=self.life[context][0];b=self.life[context][1]
            return self._winner(a,b)
        if self.mode=="recent-only":
            return self._winner(self._recent_counts(context,0),self._recent_counts(context,1))
        return self.two.choose(context,minimum_support=2)

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

def _paired_round(arms,contexts):
    for arm in arms.values():
        for context,winner in contexts.items():
            arm.observe_both_actions(context,winner)

def run_sparse_fallback():
    """Shared prior, one ambiguous reversal pair, then enough evidence to adapt."""
    arms={name:_Arm(name) for name in ARMS}
    for _ in range(WARMUP_PAIRS):
        _paired_round(arms,{2:1})
    _paired_round(arms,{2:0})
    before={name:arm.choose(2) for name,arm in arms.items()}
    counts={
        "two-tier":[list(arms["two-tier"].two.recent_counts(2,a)) for a in (0,1)],
        "recent-only":[arms["recent-only"]._recent_counts(2,a) for a in (0,1)]}
    _paired_round(arms,{2:0})
    after={name:arm.choose(2) for name,arm in arms.items()}
    return {"historical_winner":1,"reversal_winner":0,"warmup_pairs":WARMUP_PAIRS,
      "ambiguous_reversal_pairs":1,"recent_counts_after_one_reversal_pair":counts,
      "decision_after_one_reversal_pair":before,"decision_after_two_reversal_pairs":after,
      "abstention_after_one_pair":{name:value is None for name,value in before.items()},
      "abstention_after_two_pairs":{name:value is None for name,value in after.items()},
      "state_bytes":{name:arm.state_bytes for name,arm in arms.items()}}

def run_benchmark():
    schedule=[{"step":step,"winner_by_context":[0 if step<REVERSAL_AT else 1,1]}
              for step in range(STEPS)]
    arms={name:_Arm(name) for name in ARMS}
    # Identical six-pair training-side warmup, excluded from measured accuracy.
    for _ in range(WARMUP_PAIRS):
        _paired_round(arms,{0:0,1:1})
    history={name:{0:[],1:[]} for name in ARMS}
    for row in schedule:
        for name,arm in arms.items():
            for context,winner in enumerate(row["winner_by_context"]):
                decision=arm.choose(context)
                history[name][context].append({
                    "correct":int(decision is not None and decision==winner),
                    "covered":int(decision is not None)})
                arm.observe_both_actions(context,winner)
    result={"schema":SCHEMA,"classification":"SYNTHETIC_ENGINEERING_DIAGNOSTIC",
      "schedule_sha256":_hash(schedule),"warmup_pairs":WARMUP_PAIRS,
      "steps":STEPS,"reversal_at":REVERSAL_AT,"contexts":2,
      "paired_observation_policy":"both actions revealed equally to every arm",
      "abstention_policy":"abstentions count as zero coverage and zero correct decisions",
      "sparse_fallback_scenario":run_sparse_fallback(),"arms":{},
      "authenticated_source":False,"scientific_first_use":False,
      "scientific_gain_verified":False,"deployment_authorized":False,
      "paid_api_calls":0,"model_calls":0}
    for name,arm in arms.items():
        rows0=history[name][0];rows1=history[name][1];post=rows0[REVERSAL_AT:]
        def metrics(rows):
            covered=sum(x["covered"] for x in rows)
            correct=sum(x["correct"] for x in rows)
            return {"decision_accuracy_all_steps":correct/len(rows),
                    "decision_coverage":covered/len(rows),
                    "accuracy_when_decided":None if not covered else correct/covered,
                    "correct_decisions":correct,"abstentions":len(rows)-covered}
        first=next((i+1 for i,x in enumerate(post) if x["correct"]),None)
        result["arms"][name]={
          "context0_pre_reversal":metrics(rows0[:REVERSAL_AT]),
          "context0_post_reversal":metrics(post),
          "context1_stationary":metrics(rows1),
          "context0_adaptation_delay_steps":first,
          "active_packed_state_bytes":arm.state_bytes,
          "declared_checkpoint_bytes":arm.checkpoint_bytes}
    return result

if __name__=="__main__":
    print(json.dumps(run_benchmark(),sort_keys=True,indent=2))
