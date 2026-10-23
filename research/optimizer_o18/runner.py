#!/usr/bin/env python3
"""O18 original POPGym source-level reward-credit experiment (PUBLIC development)."""
from __future__ import annotations
import argparse,json,sys,time,tracemalloc
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
# Unchanged O16 runner imports a historic local 'model' module.
sys.path.insert(0,str(ROOT/"research"/"optimizer_o16"))
from research.optimizer_o15.runner import (
    original_source,episode,LocalVotes,source_seed,digest,stable,need,
    SOURCE_COMMIT,SOURCE_BLOBS)
from research.optimizer_o16.runner import source_episode
from research.optimizer_o16.model import FIFO,Stride,LearnedEviction
from research.optimizer_o17.model import PhaseGate
from research.optimizer_o18.model import RecordCredit

DELAYS=(4,8)
REPS=(0,1,2)
FIT_N=48
DEV_N=24
ARMS=("RECORD_CREDIT","O17_PHASE_GATE","O16_LEGACY_EVICTION",
      "TRAINED_STRIDE","FIFO","RECORD_FEATURE_ABLATION")
FIT_ARMS=("RECORD_CREDIT","O17_PHASE_GATE","O16_LEGACY_EVICTION",
          "TRAINED_STRIDE_SPLIT")
STRIDES=(1,2,4)
FIRST="3f0e4a58404ab5d8ed260017b1a3f11737afea0d"
PARENT="1f8ebc965b84bd858a32bc12abae12e4f889f842"

def role_seed(role,di,rep,i):
    if role=="LAG_FIT":
        return source_seed("FIT",di,rep,i)
    if role=="POLICY_FIT":
        return 13100000+400000*di+10000*rep+i
    if role=="DEV":
        return 14300000+400000*di+10000*rep+i
    raise ValueError("O18_UNREGISTERED_ROLE")

def copy_frozen_record_state(x):
    y=RecordCredit(x.lag,seed=15001,feature_ablation=True)
    y.w=list(x.w)
    y.fit_updates=x.fit_updates
    y.fit_choices=x.fit_choices
    y.reward_events=x.reward_events
    y.mean_source_sign=x.mean_source_sign
    y.peak_fit_eligibility=x.peak_fit_eligibility
    return y

def full_run(cls):
    receipt={
      "schema":"forge.optimizer.o18.original-record-credit-source-v1",
      "O18_FIRST_source_only_commit":FIRST,
      "immutable_parent_O17_sha":PARENT,
      "original_external_source_commit":SOURCE_COMMIT,
      "original_external_source_blobs":SOURCE_BLOBS,
      "original_source_family":"ONE_PUBLICLY_INSPECTED_POPGYM_FAMILY",
      "shared_lag_support_uses_full_FIT_history":True,
      "DEV_memory_capacity":4,
      "independent_scientific_first_use":False,
      "science_promotion":False,
      "scenarios":[],
      "disposition":"O18_INVALID"}
    started=time.process_time_ns()
    tracemalloc.start()
    try:
        role_ids=[role_seed(role,di,rep,i)
                  for role,n in (("LAG_FIT",FIT_N),
                                 ("POLICY_FIT",FIT_N),
                                 ("DEV",DEV_N))
                  for di in range(2) for rep in REPS for i in range(n)]
        need(len(role_ids)==len(set(role_ids)),
             "O18_FROZEN_ORIGINAL_FIT_DEV_ROLES_COLLIDE")
        old_dev={base+400000*di+10000*rep+i
                 for base in (9900000,12300000)
                 for di in range(2) for rep in REPS for i in range(DEV_N)}
        new_dev={role_seed("DEV",di,rep,i)
                 for di in range(2) for rep in REPS for i in range(DEV_N)}
        need(not old_dev & new_dev,"O18_REUSED_PREVIOUS_PUBLIC_DEV")
        total_resets=0
        advancements=[]
        for di,k in enumerate(DELAYS):
            for rep in REPS:
                fit=[episode(cls,k,di,rep,i,"FIT") for i in range(FIT_N)]
                total_resets+=FIT_N
                lagfit=LocalVotes();lagfit.fit(fit)
                lag=lagfit.learned_lag()
                need(1<=lag<=12,"O18_FIT_LAG_INVALID")
                models={
                  "RECORD_CREDIT":RecordCredit(lag,seed=300+100*di+rep),
                  "O17_PHASE_GATE":PhaseGate(lag,seed=500+100*di+rep),
                  "O16_LEGACY_EVICTION":LearnedEviction(lag,seed=700+100*di+rep)}
                fit_trace={}
                fit_cost={}
                for name in ("RECORD_CREDIT","O17_PHASE_GATE","O16_LEGACY_EVICTION"):
                    model=models[name]
                    t0=time.process_time_ns()
                    rows=[]
                    for i in range(FIT_N):
                        rows.append(source_episode(
                            cls,k,role_seed("POLICY_FIT",di,rep,i),
                            model,train=True))
                    total_resets+=FIT_N
                    fit_trace[name]=rows
                    fit_cost[name]=time.process_time_ns()-t0
                # Independent conventional with exact same total FIT budget,
                # 16 real original action/reward episodes for each stride.
                t0=time.process_time_ns()
                stride_trace=[]
                real_stride_rewards={}
                for j,stride in enumerate(STRIDES):
                    model=Stride(lag,stride,seed=901+rep+j)
                    rows=[source_episode(cls,k,
                            role_seed("POLICY_FIT",di,rep,i),model)
                          for i in range(j*16,(j+1)*16)]
                    stride_trace.extend(rows)
                    real_stride_rewards[stride]=sum(
                        z["sum_source_reward_sign"] for z in rows)/(16*(52-k))
                    total_resets+=16
                fit_trace["TRAINED_STRIDE_SPLIT"]=stride_trace
                fit_cost["TRAINED_STRIDE_SPLIT"]=time.process_time_ns()-t0
                chosen_stride=max(STRIDES,
                                  key=lambda s:(real_stride_rewards[s],-s))
                models["TRAINED_STRIDE"]=Stride(lag,chosen_stride)
                models["FIFO"]=FIFO(lag)
                models["RECORD_FEATURE_ABLATION"]=copy_frozen_record_state(
                    models["RECORD_CREDIT"])
                need(set(models)==set(ARMS),"O18_ARM_MATRIX_CHANGED")
                frozen={name:stable(model.state())
                        for name,model in models.items()}
                original_dev={}
                score={}
                positive_rate={}
                for name in ARMS:
                    model=models[name]
                    rows=[source_episode(cls,k,
                            role_seed("DEV",di,rep,i),model)
                          for i in range(DEV_N)]
                    total_resets+=DEV_N
                    need(stable(model.state())==frozen[name],
                         "O18_DEV_TRAINING_OR_CHECKPOINT_MUTATION:"+name)
                    original_dev[name]=rows
                    score[name]=sum(z["sum_source_reward_sign"]
                                    for z in rows)/(DEV_N*(52-k))
                    positive_rate[name]=sum(z["correct"] for z in rows)/(DEV_N*(52-k))
                for i in range(DEV_N):
                    need(len({original_dev[arm][i][
                                  "public_original_observation_SHA256"]
                              for arm in ARMS})==1,
                         "O18_PAIRED_GENUINE_ORIGINAL_SOURCE_DRIFT")
                benchmark=max(score[x] for x in (
                    "O17_PHASE_GATE","O16_LEGACY_EVICTION",
                    "TRAINED_STRIDE","FIFO"))
                candidate=score["RECORD_CREDIT"]
                ablation=score["RECORD_FEATURE_ABLATION"]
                yes=(lag==k-1 and
                     (candidate>=benchmark-.05 if k==4 else
                      candidate>=benchmark+.05 and candidate>=ablation+.05))
                advancements.append(yes)
                receipt["scenarios"].append({
                  "k_original_source_constructor_auditor_only":k,
                  "replica":rep,
                  "shared_FULL_history_LAG_FIT_original_episodes":FIT_N,
                  "shared_FULL_history_LAG_FIT_source_SHA256":digest(
                      [z["source_public_observation_SHA256"] for z in fit]),
                  "learned_lag_from_real_original_source_reward":lag,
                  "original_FIT_episodes_per_learned_arm":FIT_N,
                  "original_DEV_episodes_per_arm":DEV_N,
                  "original_policy_FIT_all_action_reward_receipts":fit_trace,
                  "original_policy_FIT_total_process_CPU_ns":fit_cost,
                  "trained_stride_FIT_original_source_reward":real_stride_rewards,
                  "trained_stride_selected":chosen_stride,
                  "frozen_model_checkpoint_JSON":frozen,
                  "frozen_model_checkpoint_bytes":{a:len(frozen[a].encode())
                                                   for a in ARMS},
                  "original_source_DEV_mean_signed_reward":score,
                  "original_source_DEV_correct_rate":positive_rate,
                  "original_source_DEV_all_action_reward_receipts":original_dev,
                  "O18_candidate_per_scenario_advance":yes})
                print("O18_ORIGINAL_SOURCE k="+str(k)+
                      " rep="+str(rep)+" lag="+str(lag)+
                      " reward="+stable(score),flush=True)
        receipt["total_original_source_resets"]=total_resets
        receipt["total_genuine_original_source_legal_steps"]=total_resets*51
        need(total_resets==2304 and total_resets*51==117504,
             "O18_REAL_SOURCE_ROLE_OR_ACTION_BUDGET_DRIFT")
        receipt["disposition"]=(
            "O18_PUBLIC_RECORD_CREDIT_CANDIDATE_NOT_FIRST_USE"
            if all(advancements) else "O18_PUBLIC_RECORD_CREDIT_NO_GO")
    except Exception as exc:
        receipt["first_failure"]=type(exc).__name__+":"+str(exc)[:750]
    finally:
        _,peak=tracemalloc.get_traced_memory()
        tracemalloc.stop()
        receipt["process_peak_tracemalloc_bytes"]=peak
        receipt["total_actual_process_CPU_ns"]=time.process_time_ns()-started
        if sys.platform!="win32":
            import resource
            receipt["process_peak_RSS_bytes"]=resource.getrusage(
                resource.RUSAGE_SELF).ru_maxrss*1024
        else:
            receipt["process_peak_RSS_bytes"]="NOT_MEASURED_WINDOWS"
        receipt["energy"]="NOT_MEASURED"
    return receipt

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--upstream",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    cls=original_source(Path(args.upstream).resolve())
    r=full_run(cls)
    dst=Path(args.out)
    dst.mkdir(parents=True,exist_ok=True)
    (dst/"o18-original-source-actual-reward-receipt.json").write_text(
        json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("O18_DISPOSITION="+r["disposition"],flush=True)
    return 2 if r["disposition"]=="O18_INVALID" else 0

if __name__=="__main__":
    raise SystemExit(main())
