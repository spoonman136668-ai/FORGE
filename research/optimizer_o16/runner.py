#!/usr/bin/env python3
"""O16 genuine original POPGym public development; NOT scientific first use."""
from __future__ import annotations
import argparse,json,sys,time,tracemalloc
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from research.optimizer_o15.runner import (
    original_source,episode,LocalVotes,source_seed,stable,digest,
    SOURCE_COMMIT,SOURCE_BLOBS,need)
from model import FIFO,Reservoir,Stride,LearnedEviction

DELAYS=(4,8)
REPS=(0,1,2)
FIT_LAG=48
FIT_EVICT=48
DEV=24
BUDGET=4
ARMS=("LEARNED_EVICTION","FIFO","RESERVOIR","TRAINED_STRIDE")
STRIDES=(1,2,4)

def seed(role,di,rep,i):
    if role=="LAG_FIT":return source_seed("FIT",di,rep,i)
    return {"POLICY_FIT":9100000,"DEV":9900000}[role]+400000*di+10000*rep+i

def source_episode(cls,k,s,model,train=False):
    env=cls(num_decks=1,k=k)
    first,_=env.reset(seed=s)
    suit=int(first)
    need(0<=suit<4,"INVALID_PUBLIC_SUIT")
    model.reset_episode()
    scored=0;correct=0;reward_total=0.;trace=[]
    start=time.process_time_ns()
    for t in range(51):
        a=int(model.read(t,suit))
        need(0<=a<4 and env.action_space.contains(a),
             "NOT_LEGAL_ORIGINAL_SOURCE_ACTION")
        nxt,r,done,trunc,info=env.step(a)
        del info
        r=float(r)
        need(r in (0.,1./(52-k),-1./(52-k)),
             "ORIGINAL_REWARD_UNEXPECTED")
        # This original reward arrives BEFORE current write, and can credit
        # only a prior write from t-learned_lag, NEVER a future query.
        model.feedback(t,r if train else 0)
        model.write(t,suit,train=train)
        trace.append((t,suit,a,r,int(nxt)))
        if r:
            scored+=1;correct+=int(r>0);reward_total+=r*(52-k)
        suit=int(nxt)
        need(0<=suit<4,"INVALID_PUBLIC_NEXT_SUIT")
        need(done==(t==50) and not trunc,"ORIGINAL_TERMINATION_DRIFT")
    need(scored==52-k,"ORIGINAL_REWARD_SCORING_COUNT_DRIFT")
    need(model.mem.peak<=BUDGET,"MEMORY_CAPACITY_OVERFLOW")
    return {"source_seed":s,"real_source_legal_steps":51,
        "scored":scored,"correct":correct,"sum_source_reward_sign":reward_total,
        "public_original_observation_SHA256":digest([(t,c,n) for t,c,a,r,n in trace]),
        "actual_source_actions_reward_SHA256":digest(trace),
        "bounded_memory_peak_items":model.mem.peak,
        "bounded_writes":model.mem.writes,"bounded_skips":model.mem.skips,
        "process_CPU_ns":time.process_time_ns()-start}

def arm(lag,name,seedval=0,stride=1):
    args={"capacity":BUDGET,"seed":seedval}
    return {
        "LEARNED_EVICTION":lambda:LearnedEviction(lag,**args),
        "FIFO":lambda:FIFO(lag,**args),
        "RESERVOIR":lambda:Reservoir(lag,**args),
        "TRAINED_STRIDE":lambda:Stride(lag,stride,**args),
    }[name]()

def execute(cls):
    out={"schema":"forge.optimizer.o16.original-public-write-evict-v1",
         "upstream_original_commit":SOURCE_COMMIT,
         "upstream_original_blobs":SOURCE_BLOBS,
         "o15_base_head":"b07e8d5293f12466263986e1f8b9a8b679334e48",
         "source_families":"ONE_PUBLICLY_INSPECTED_EXTERNAL_POPGYM_FAMILY",
         "FSA_Q21_HELD_first_use_consumed":0,
         "scientific_candidate_promoted":False,
         "memory_budget_records":BUDGET,"scenarios":[],"disposition":"O16_INVALID"}
    started=time.process_time_ns();tracemalloc.start()
    try:
        total_resets=0;qualified=[]
        role_ids=[seed(r,di,rep,i)
                  for r,n in (("LAG_FIT",FIT_LAG),("POLICY_FIT",FIT_EVICT),("DEV",DEV))
                  for di in range(2) for rep in REPS for i in range(n)]
        need(len(role_ids)==len(set(role_ids)),"ORIGINAL_SEED_ROLES_COLLIDE")
        for di,k in enumerate(DELAYS):
            for rep in REPS:
                # Equal full-public-FIT learned lag prior for every arm.
                fit=[episode(cls,k,di,rep,i,"FIT") for i in range(FIT_LAG)]
                total_resets+=FIT_LAG
                lag_model=LocalVotes();lag_model.fit(fit)
                lag=lag_model.learned_lag()
                need(1<=lag<=12,"INVALID_LEARNED_LAG")
                models={x:arm(lag,x,seedval=1000+di*100+rep*10+j)
                        for j,x in enumerate(ARMS) if x!="TRAINED_STRIDE"}
                learn=models["LEARNED_EVICTION"]
                t0=time.process_time_ns()
                for i in range(FIT_EVICT):
                    source_episode(cls,k,seed("POLICY_FIT",di,rep,i),learn,train=True)
                total_resets+=FIT_EVICT
                fit_cpu=time.process_time_ns()-t0
                trained_state=stable(learn.state())
                # Strong conventional selection; actual source episodes, never
                # fabricated counterfactual labels; same 48 FIT seed budget.
                trials={}
                t0=time.process_time_ns()
                for j,stride in enumerate(STRIDES):
                    policy=arm(lag,"TRAINED_STRIDE",seedval=2000+j,stride=stride)
                    tests=[source_episode(cls,k,seed("POLICY_FIT",di,rep,i),policy)
                           for i in range(j*16,(j+1)*16)]
                    trials[stride]=sum(z["sum_source_reward_sign"] for z in tests)/(16*(52-k))
                    total_resets+=16
                selected=max(STRIDES,key=lambda s:(trials[s],-s))
                stride_fit_cpu=time.process_time_ns()-t0
                models["TRAINED_STRIDE"]=arm(lag,"TRAINED_STRIDE",stride=selected)
                frozen={x:stable(models[x].state()) for x in ARMS}
                scores={};traces={}
                for name in ARMS:
                    rows=[source_episode(cls,k,seed("DEV",di,rep,i),models[name])
                          for i in range(DEV)]
                    total_resets+=DEV
                    scores[name]=sum(z["sum_source_reward_sign"] for z in rows)/(DEV*(52-k))
                    traces[name]=rows
                    need(stable(models[name].state())==frozen[name],
                         "DEV_MODEL_CHANGED:"+name)
                for i in range(DEV):
                    need(len({traces[n][i]["public_original_observation_SHA256"]
                              for n in ARMS})==1,
                         "PAIRED_ORIGINAL_SOURCE_OBSERVATION_DRIFT")
                strong=max(scores[name] for name in ARMS if name!="LEARNED_EVICTION")
                positive=(lag==k-1 and (scores["LEARNED_EVICTION"]>=strong-.05
                           if k==4 else scores["LEARNED_EVICTION"]>=strong+.05))
                qualified.append(positive)
                out["scenarios"].append({
                   "k_auditor_only":k,"replica":rep,
                   "lag_from_shared_real_FIT":lag,
                   "public_shared_lag_FIT_SHA256":digest(
                       [z["source_public_observation_SHA256"] for z in fit]),
                   "learned_policy_original_FIT_count":FIT_EVICT,
                   "conventional_stride_original_FIT_count":FIT_EVICT,
                   "learned_policy_original_FIT_CPU_ns":fit_cpu,
                   "conventional_stride_original_FIT_CPU_ns":stride_fit_cpu,
                   "trained_stride_FIT_original_rewards":trials,
                   "trained_stride_selected":selected,
                   "learned_policy_frozen_checkpoint":trained_state,
                   "DEV_reward_per_original_scored_action":scores,
                   "DEV_original_source_episode_evidence":traces,
                   "source_public_advancement":positive})
                print("O16_ORIGINAL_SOURCE k=%d rep=%d lag=%d reward=%s" %
                      (k,rep,lag,stable(scores)),flush=True)
        out["actual_original_source_resets"]=total_resets
        out["actual_original_source_steps"]=total_resets*51
        need(total_resets==6*(48+48+48+DEV*len(ARMS)),
             "ORIGINAL_ROLE_BUDGET_DRIFT")
        out["disposition"]=(
            "O16_PUBLIC_LEARNED_EVICTION_ADVANCEMENT_CANDIDATE_NOT_FIRST_USE"
            if all(qualified) else "O16_PUBLIC_LEARNED_EVICTION_NO_GO")
    except Exception as e:
        out["first_failure"]=type(e).__name__+":"+str(e)[:600]
    finally:
        _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        out["process_tracemalloc_peak_bytes"]=peak
        out["process_CPU_ns"]=time.process_time_ns()-started
        if sys.platform!="win32":
            import resource
            out["process_peak_RSS_bytes"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        else:out["process_peak_RSS_bytes"]="NOT_MEASURED_WINDOWS"
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True);p.add_argument("--out",required=True)
    a=p.parse_args()
    cls=original_source(Path(a.upstream).resolve())
    result=execute(cls)
    dest=Path(a.out);dest.mkdir(parents=True,exist_ok=True)
    (dest/"o16-original-public-receipt.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("O16_DISPOSITION="+result["disposition"],flush=True)
    return 2 if result["disposition"]=="O16_INVALID" else 0
if __name__=="__main__":raise SystemExit(main())
