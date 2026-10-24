"""O19 source-only exact combinatorial capacity preflight; NO original POPGym import.

Pinned RepeatPrevious source: proroklab/popgym@410d5aa626dae8024f498354d8781a0d1870c399,
blob 5d43f3c97a7af43450dc898096ca7b8a660251b5. Its 51 source steps
read before each writer update; k=8 implies lag=7 and exactly 44 scored actions.
This script counts *guaranteed* retained-timestamp references, independent of
suit or private source values. It is not a bound on total reward: missing suits
can still be guessed or inferred using other information.
"""
from functools import lru_cache
import json

STEPS=51
CAP=4

def optimum(lag=7,steps=STEPS,cap=CAP):
    @lru_cache(None)
    def dp(t,retained):
        if t>=steps:return (0, ())
        target=t-lag
        current_hit=int(target>=0 and target in retained)
        # Once a target has been queried, its stored record serves no later
        # original RepeatPrevious reward, so drop it before the new write.
        useful=tuple(x for x in retained if x>target)
        opts=[(useful,"skip")]
        if t<steps-1:
            if len(useful)<cap:opts.append((tuple(sorted(useful+(t,))),"insert"))
            else:
                for old in useful:
                    nxt=tuple(sorted(x for x in useful if x!=old))+ (t,)
                    opts.append((tuple(sorted(nxt)),f"evict:{old}"))
        best=None
        for nxt,move in opts:
            future,sequence=dp(t+1,nxt)
            candidate=(current_hit+future,(move,)+sequence)
            if best is None or candidate[0]>best[0]:best=candidate
        return best
    successes,policy=dp(0,())
    return {"lag":lag,"steps":steps,"scored":steps-lag,"capacity":cap,
            "max_guaranteed_retrievable":successes,"choices":list(policy),
            "state_count":dp.cache_info().currsize}

def replay(policy,lag=7,steps=STEPS,cap=CAP):
    retained=[];hits=[];peak=0;acts=[]
    for t,move in enumerate(policy):
        target=t-lag
        if target>=0 and target in retained:hits.append(t)
        # expiration after read is legal, no future rewards for that timestamp
        retained=[s for s in retained if s>target]
        if move=="insert":
            if len(retained)>=cap:raise AssertionError("insert at capacity")
            retained.append(t)
        elif move.startswith("evict:"):
            s=int(move.split(':',1)[1]);retained.remove(s);retained.append(t)
        elif move!="skip":raise AssertionError("invalid move")
        assert len(retained)<=cap
        peak=max(peak,len(retained));acts.append(move)
    return {"guaranteed_hit_count":len(hits),"guaranteed_hit_times":hits,
            "peak_slots":peak,"writes":sum(x!="skip" for x in acts)}

def periodic(lag=7,steps=STEPS,cap=CAP):
    # This is a prospective source-blind clock rule; the agent stores only
    # the first four arrivals out of each lag-sized block, never a hidden suit.
    retained=[];hits=[];acts=[]
    for t in range(steps):
        if t-lag in retained:hits.append(t)
        retained=[x for x in retained if x>t-lag]
        if t<steps-1 and t%lag<cap:
            assert len(retained)<cap
            retained.append(t);acts.append("insert")
        else:acts.append("skip")
    return {"guaranteed_hit_count":len(hits),"guaranteed_hit_times":hits,
            "writes":acts.count("insert"),"peak_slots":cap}

def main():
    d=optimum(); r=replay(d["choices"]); p=periodic()
    assert d["max_guaranteed_retrievable"]==r["guaranteed_hit_count"]
    assert p["guaranteed_hit_count"]==d["max_guaranteed_retrievable"]
    assert r["peak_slots"]<=4
    result={"classification":"SOURCE_ONLY_COMBINATORIAL_CAPACITY_NOT_ORIGINAL_SCIENCE",
      "original_upstream_commit":"410d5aa626dae8024f498354d8781a0d1870c399",
      "original_repeat_previous_blob":"5d43f3c97a7af43450dc898096ca7b8a660251b5",
      "source_replay_executed":False,"FIT_or_DEV_cohorts_consumed":0,
      "DP":{k:v for k,v in d.items() if k!="choices"},"DP_replay":r,
      "periodic":p,"caveat":"Bound counts exact timestamp retrievals only; misses may be correct by chance or public-inference. Not an expected reward bound or independent first use."}
    print(json.dumps(result,sort_keys=True,indent=2))

if __name__=="__main__":main()

# Supplemental source-writer-constrained witness, deliberately NOT invoked by
# the main result: source O16/O18 Writer has no arbitrary record deletion.
# A prospective periodic policy can still achieve the 26-slot upper bound by
# evicting the oldest expired slot when inserting a newly selected timestamp.
def periodic_source_writer(lag=7,steps=STEPS,cap=CAP):
    retained=[];hits=[];peak=0
    for t in range(steps):
        if t>=lag and t-lag in retained:hits.append(t)
        if t<steps-1 and t%lag<cap:
            if len(retained)==cap:
                oldest=min(retained)
                # Choose a record already queried, never discard pending target.
                assert oldest<=t-lag,(t,oldest,retained)
                retained.remove(oldest)
            retained.append(t)
        assert len(retained)<=cap
        peak=max(peak,len(retained))
    return {"guaranteed_hit_count":len(hits),"times":hits,"peak_slots":peak}
