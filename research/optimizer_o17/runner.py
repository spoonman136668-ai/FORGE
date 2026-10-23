#!/usr/bin/env python3
"""O17 original-source prospectively frozen phase-retention mechanism experiment."""
from __future__ import annotations
import argparse,json,sys,time,tracemalloc
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
# O16 source_episode's existing intentionally local `from model import` import
# is bound to the exact inherited O16 model. No existing file is mutated.
sys.path.insert(0,str(ROOT/"research"/"optimizer_o16"))
from research.optimizer_o15.runner import (original_source,episode,LocalVotes,
    source_seed,digest,stable,need,SOURCE_COMMIT,SOURCE_BLOBS)
from research.optimizer_o16.runner import source_episode
from research.optimizer_o16.model import FIFO,Stride,LearnedEviction
from research.optimizer_o17.model import PhaseGate

DELAYS=(4,8)
REPS=(0,1,2)
FIT_N=48
DEV_N=24
ARMS=("O17_PHASE_GATE","O16_LEGACY_EVICTION","FIFO","TRAINED_STRIDE",
      "O17_PHASE_ROTATE_ABLATION")
STRIDES=(1,2,4)
FIRST="fbbc8b2206d476d72fff4fcd3c33396cc1982599"
O16_PARENT="7f3ce9fca6151c9db7dc163535431069960ef299"

def source_seed_o17(role,di,rep,i):
    if role=="LAG_FIT":return source_seed("FIT",di,rep,i)
    return (11100000 if role=="POLICY_FIT" else 12300000)+400000*di+10000*rep+i

def run(cls):
    out={"schema":"forge.optimizer.o17.original-public-phase-retention-v1",
         "source_original_git_commit":SOURCE_COMMIT,
         "source_original_git_blobs":SOURCE_BLOBS,
         "frozen_FIRST_protocol_commit":FIRST,
         "exact_O16_parent_commit":O16_PARENT,
         "source_family":"ONE_PUBLIC_INSPECTED_POPGYM_FAMILY",
         "original_science_first_use":False,
         "scientific_candidate_promoted":False,
         "memory_records_max":4,
         "scenarios":[],
         "disposition":"O17_INVALID"}
    tracemalloc.start();start=time.process_time_ns()
    try:
        roles=[source_seed_o17(role,di,rep,i)
               for role,n in (("LAG_FIT",48),("POLICY_FIT",48),("DEV",24))
               for di in range(2) for rep in REPS for i in range(n)]
        need(len(roles)==len(set(roles)),
             "O17_FIT_DEV_SOURCE_SEED_COLLISION")
        need(not set(source_seed_o17("DEV",di,rep,i)
                     for di in range(2) for rep in REPS for i in range(DEV_N))
                 &set(9900000+400000*di+10000*rep+i
                      for di in range(2) for rep in REPS for i in range(DEV_N)),
             "O17_REUSED_O16_DEV_SEEDS")
        resets=0;approved=[]
        for di,k in enumerate(DELAYS):
            for rep in REPS:
                lagfit=[episode(cls,k,di,rep,i,"FIT") for i in range(FIT_N)]
                resets+=FIT_N
                lag=LocalVotes();lag.fit(lagfit)
                selected_lag=lag.learned_lag()
                need(1<=selected_lag<=12,"O17_INVALID_FITTED_LAG")
                phase=PhaseGate(selected_lag,seed=701+100*di+rep)
                legacy=LearnedEviction(selected_lag,seed=801+100*di+rep)
                fit_start=time.process_time_ns()
                phase_fit_rows=[]
                for i in range(FIT_N):
                    phase_fit_rows.append(source_episode(cls,k,
                        source_seed_o17("POLICY_FIT",di,rep,i),
                        phase,train=True))
                    resets+=1
                phase_fit_cpu=time.process_time_ns()-fit_start
                fit_start=time.process_time_ns()
                legacy_fit_rows=[]
                for i in range(FIT_N):
                    legacy_fit_rows.append(source_episode(cls,k,
                        source_seed_o17("POLICY_FIT",di,rep,i),
                        legacy,train=True))
                    resets+=1
                legacy_fit_cpu=time.process_time_ns()-fit_start
                fit_start=time.process_time_ns()
                actual_fit_rewards={}
                stride_fit_rows=[]
                for j,stride in enumerate(STRIDES):
                    policy=Stride(selected_lag,stride,seed=901+rep+j)
                    rows=[source_episode(cls,k,
                          source_seed_o17("POLICY_FIT",di,rep,i),policy)
                          for i in range(j*16,(j+1)*16)]
                    resets+=16
                    stride_fit_rows.extend(rows)
                    actual_fit_rewards[stride]=sum(
                        z["sum_source_reward_sign"] for z in rows)/(16*(52-k))
                selected_stride=max(STRIDES,
                                    key=lambda s:(actual_fit_rewards[s],-s))
                stride_fit_cpu=time.process_time_ns()-fit_start
                rotated=PhaseGate(selected_lag,seed=701+100*di+rep,
                                  phase_shift=1)
                rotated.logits=list(phase.logits)
                rotated.fit_updates=phase.fit_updates
                rotated.fit_reward_events=phase.fit_reward_events
                rotated.fit_write_events=phase.fit_write_events
                models={
                  "O17_PHASE_GATE":phase,
                  "O16_LEGACY_EVICTION":legacy,
                  "FIFO":FIFO(selected_lag),
                  "TRAINED_STRIDE":Stride(selected_lag,selected_stride),
                  "O17_PHASE_ROTATE_ABLATION":rotated}
                frozen={name:stable(model.state()) for name,model in models.items()}
                rows_by_arm={}
                for name,model in models.items():
                    rows=[source_episode(cls,k,
                          source_seed_o17("DEV",di,rep,i),model,train=False)
                          for i in range(DEV_N)]
                    resets+=DEV_N
                    rows_by_arm[name]=rows
                    need(stable(model.state())==frozen[name],
                         "O17_DEV_POLICY_CHECKPOINT_MUTATION:"+name)
                for i in range(DEV_N):
                    need(len({rows_by_arm[a][i]["public_original_observation_SHA256"]
                              for a in ARMS})==1,
                         "O17_ORIGINAL_SOURCE_DEV_OBSERVATION_DRIFT")
                scores={name:sum(z["sum_source_reward_sign"] for z in rows)
                        /(DEV_N*(52-k))
                        for name,rows in rows_by_arm.items()}
                strong=max(scores[a] for a in
                           ("O16_LEGACY_EVICTION","FIFO","TRAINED_STRIDE"))
                candidate=scores["O17_PHASE_GATE"]
                ablation=scores["O17_PHASE_ROTATE_ABLATION"]
                condition=(selected_lag==k-1 and
                           (candidate>=strong-.05 if k==4
                            else candidate>=strong+.05 and candidate>=ablation+.05))
                approved.append(condition)
                out["scenarios"].append({
                    "source_k_auditor_only":k,
                    "source_replica":rep,
                    "learned_lag_from_real_public_reward":selected_lag,
                    "original_source_LAG_FIT_SHA256":digest(
                       [z["source_public_observation_SHA256"] for z in lagfit]),
                    "original_source_POLICY_FIT_episodes_per_trained_arm":FIT_N,
                    "original_source_DEV_episodes_per_arm":DEV_N,
                    "phase_fit_original_source_CPU_ns":phase_fit_cpu,
                    "legacy_fit_original_source_CPU_ns":legacy_fit_cpu,
                    "stride_fit_original_source_CPU_ns":stride_fit_cpu,
                    "trained_stride_source_FIT_reward":actual_fit_rewards,
                    "genuine_original_POLICY_FIT_action_reward_receipts":{
                        "phase_gate":phase_fit_rows,
                        "legacy":legacy_fit_rows,
                        "stride_split_16_16_16":stride_fit_rows},
                    "trained_stride_selected":selected_stride,
                    "frozen_original_source_FIT_policy_states":frozen,
                    "source_real_reward_per_scored_action":scores,
                    "genuine_original_DEV_action_reward_receipts":rows_by_arm,
                    "O17_PUBLIC_ADVANCEMENT_PER_SCENARIO":condition})
                print("O17_ORIGINAL_SOURCE k="+str(k)+" rep="+str(rep)+
                      " learned_lag="+str(selected_lag)+" reward="+stable(scores),
                      flush=True)
        out["original_real_source_resets"]=resets
        out["original_legal_source_steps"]=resets*51
        need(resets==1872 and resets*51==95472,
             "O17_ORIGINAL_SOURCE_BUDGET_CHANGED")
        out["disposition"]=(
            "O17_PUBLIC_PHASE_RETAIN_CANDIDATE_NOT_FIRST_USE"
            if all(approved) else "O17_PUBLIC_PHASE_RETAIN_NO_GO")
    except Exception as exc:
        out["first_failure"]=type(exc).__name__+":"+str(exc)[:700]
    finally:
        _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        out["process_peak_tracemalloc_bytes"]=peak
        out["source_and_models_CPU_ns"]=time.process_time_ns()-start
        if sys.platform!="win32":
            import resource
            out["process_peak_RSS_bytes"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        else:out["process_peak_RSS_bytes"]="NOT_MEASURED_WINDOWS"
        out["energy"]="NOT_MEASURED"
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    cls=original_source(Path(a.upstream).resolve())
    receipt=run(cls)
    path=Path(a.out);path.mkdir(parents=True,exist_ok=True)
    (path/"o17-genuine-original-public-receipt.json").write_text(
        json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("O17_DISPOSITION="+receipt["disposition"],flush=True)
    return 2 if receipt["disposition"]=="O17_INVALID" else 0
if __name__=="__main__":raise SystemExit(main())
