#!/usr/bin/env python3
"""Optimizer O15: actual external POPGym delayed source-reward lag selection.

Learners observe only real public suit histories and source-returned reward AFTER
original env.step. This is PUBLIC development, not source-blinded HELD science.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib, importlib, inspect, json, math, os
from pathlib import Path
import subprocess, sys, time, tracemalloc, types

HERE=Path(__file__).resolve().parent
FIRST="51ef965365396b3b42ab3564f984eae4c9403167"
SOURCE_COMMIT="410d5aa626dae8024f498354d8781a0d1870c399"
SOURCE_BLOBS={
 "popgym/envs/repeat_previous.py":"5d43f3c97a7af43450dc898096ca7b8a660251b5",
 "popgym/core/deck.py":"12bcabfa9a96fd1261809ef0a446c74d3f3bfa86",
 "popgym/core/env.py":"26a20ba3531730b76e135f48e8fc25bb6b620984",
}
DELAYS=(4,8)
REPS=(0,1,2)
FIT_N=48
DEV_N=24
LAGS=tuple(range(1,13))
ARMS=("LOCAL_LAG_PLASTICITY","TRAINED_BAYESIAN_LAG",
      "TRAINED_SOFT_ATTENTION","TRAINED_LOGISTIC_ACTION",
      "SOURCE_KNOWN_LAG_ORACLE","NO_PAST_MAJORITY",
      "LOCAL_LAG_SHIFT_ABLATION")

def need(ok,msg):
    if not ok: raise ValueError(msg)
def stable(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)
def digest(x):
    return hashlib.sha256(stable(x).encode("utf-8")).hexdigest()
def source_only_identity(x):
    # Public source/time-independent identity; keep original measured CPU
    # in the receipt, never mix variable wall/CPU cost into source custody.
    if isinstance(x,dict):
        return {k:source_only_identity(v) for k,v in x.items()
                if k not in ("source_process_and_model_CPU_ns",
                             "model_choice_CPU_ns")}
    if isinstance(x,list):
        return [source_only_identity(z) for z in x]
    return x
def blob(path):
    p=subprocess.run(["git","hash-object","--",str(path)],capture_output=True,
                     text=True,timeout=25)
    need(p.returncode==0,"SOURCE_GIT_BLOB_IDENTITY_UNAVAILABLE")
    return p.stdout.strip()
def original_source(root):
    for p,s in SOURCE_BLOBS.items():
        need(blob(root/p)==s,"EXTERNAL_ORIGINAL_SOURCE_GIT_DRIFT:"+p)
    for name,path in (("popgym","popgym"),("popgym.envs","popgym/envs"),
                      ("popgym.core","popgym/core")):
        m=types.ModuleType(name)
        m.__path__=[str(root/path)]
        m.__package__=name
        sys.modules[name]=m
    for k in list(sys.modules):
        if k.startswith("popgym.") and k not in ("popgym.envs","popgym.core"):
            del sys.modules[k]
    m=importlib.import_module("popgym.envs.repeat_previous")
    cls=m.RepeatPrevious
    need(Path(inspect.getfile(cls)).resolve()==
         (root/"popgym/envs/repeat_previous.py").resolve(),
         "NOT_ACTUAL_ORIGINAL_POPGYM_CLASS")
    return cls
def source_seed(role,di,rep,i):
    return (8100000 if role=="FIT" else 8300000)+400000*di+10000*rep+i
def observed(history,t,lag):
    return history[t-lag] if lag<=t else None
def best_index(values):
    return max(LAGS,key=lambda lag:(values[lag],-lag))
def softmax_logits(w,eligible):
    mx=max(w[lag] for lag in eligible)
    e={lag:math.exp(w[lag]-mx) for lag in eligible}
    tot=sum(e.values())
    return {lag:e[lag]/tot for lag in eligible}

class LocalVotes:
    def __init__(self,shift=0):
        self.v={lag:0 for lag in LAGS};self.updates=0
        self.shift=shift
    def fit(self,events):
        for ep in events:
            for z in ep["source_public_observed_original_actions"]:
                if z["real_original_source_reward_sign"]==0:continue
                a=z["real_original_source_action"]
                t=z["public_time_step"]
                past=z["public_suit_history"]
                success=z["real_original_source_reward_sign"]>0
                for lag in LAGS:
                    old=observed(past,t,lag)
                    if old is None:continue
                    expected_success=a==old
                    self.v[lag]+=1 if expected_success==success else -1
                self.updates+=1
    def learned_lag(self):
        selected=best_index(self.v)
        return ((selected-1+self.shift)%len(LAGS))+1
    def choose(self,history,t):
        lag=self.learned_lag()
        past=observed(history,t,lag)
        return history[t] if past is None else past
    def state(self):
        return {"kind":"LOCAL_HANDDESIGNED_MATCH_VOTES",
                "votes":self.v,"scored_source_outcomes":self.updates,
                "chosen_lag":self.learned_lag(),"shift_readout":self.shift}

class BayesianLag:
    def __init__(self):
        self.loglik={lag:0.0 for lag in LAGS}
        self.updates=0
    def fit(self,episodes):
        for ep in episodes:
            for z in ep["source_public_observed_original_actions"]:
                v=z["real_original_source_reward_sign"]
                if v==0:continue
                for lag in LAGS:
                    past=observed(z["public_suit_history"],z["public_time_step"],lag)
                    if past is None:continue
                    agree=((past==z["real_original_source_action"]) == (v>0))
                    self.loglik[lag]+=math.log(.95 if agree else .05)
                self.updates+=1
    def choose(self,history,t):
        lag=best_index(self.loglik)
        past=observed(history,t,lag)
        return history[t] if past is None else past
    def state(self):
        return {"kind":"CONVENTIONAL_BAYESIAN_PUBLIC_LAG",
                "candidate_loglik":self.loglik,"chosen_lag":best_index(self.loglik),
                "observed_fit_reward_events":self.updates}

class SoftAttention:
    def __init__(self):
        self.w={lag:0.0 for lag in LAGS}
        self.updates=0
    def fit(self,episodes):
        flat=[z for ep in episodes for z in ep["source_public_observed_original_actions"]
              if z["real_original_source_reward_sign"]!=0]
        for _ in range(6):
            for z in flat:
                t=z["public_time_step"]
                available=[lag for lag in LAGS if lag<=t]
                if not available:continue
                a=z["real_original_source_action"]
                past=z["public_suit_history"]
                match={lag:float(observed(past,t,lag)==a) for lag in available}
                attn=softmax_logits(self.w,available)
                pred=sum(attn[j]*match[j] for j in available)
                target=float(z["real_original_source_reward_sign"]>0)
                p=max(1e-5,min(1-1e-5,pred))
                factor=(target-p)/(p*(1-p))
                for j in available:
                    grad=factor*attn[j]*(match[j]-pred)
                    self.w[j]+=.03*max(-3.,min(3.,grad))
                self.updates+=1
    def choose(self,history,t):
        available=[l for l in LAGS if l<=t]
        if not available:return history[t]
        attn=softmax_logits(self.w,available)
        votes=[0.]*4
        for lag,p in attn.items():
            votes[history[t-lag]]+=p
        return max(range(4),key=lambda a:(votes[a],-a))
    def state(self):
        return {"kind":"TRAINED_CONVENTIONAL_TEMPORAL_ATTENTION",
                "lag_weights":self.w,"SGD_updates":self.updates,"passes":6}

class LogisticAction:
    def __init__(self):
        self.w=[0.]*13
        self.updates=0
    def features(self,history,t,action):
        return (1.,)+tuple(float(observed(history,t,lag)==action)
                            for lag in LAGS)
    def fit(self,episodes):
        flat=[z for ep in episodes for z in ep["source_public_observed_original_actions"]
              if z["real_original_source_reward_sign"]!=0]
        for _ in range(6):
            for z in flat:
                x=self.features(z["public_suit_history"],z["public_time_step"],
                                z["real_original_source_action"])
                zz=sum(w*v for w,v in zip(self.w,x))
                p=1./(1.+math.exp(-max(-25.,min(25.,zz))))
                y=float(z["real_original_source_reward_sign"]>0)
                self.w=[w+.03*((y-p)*v-.001*w) for w,v in zip(self.w,x)]
                self.updates+=1
    def choose(self,history,t):
        def value(a):return sum(w*v for w,v in zip(self.w,self.features(history,t,a)))
        return max(range(4),key=lambda a:(value(a),-a))
    def state(self):
        return {"kind":"TRAINED_LOGISTIC_SOURCE_REWARD",
                "weights":self.w,"SGD_updates":self.updates,"passes":6}

class SourceOracle:
    def __init__(self,k):self.k=k
    def fit(self,episodes):pass
    def choose(self,history,t):
        previous=observed(history,t,self.k-1)
        return history[t] if previous is None else previous
    def state(self):return {"known_original_k":self.k,"source_law_privileged":True}

class NoHistory:
    def __init__(self):self.most_common=0;self.counts=[0]*4
    def fit(self,episodes):
        for ep in episodes:
            for suit in ep["source_public_suit_observations"]:
                self.counts[suit]+=1
        self.most_common=max(range(4),key=lambda a:(self.counts[a],-a))
    def choose(self,history,t):return self.most_common
    def state(self):return {"trained_public_FIT_suit_counts":self.counts,
                            "source_NO_HISTORY_suit_prediction":self.most_common}

def model_fit(episodes,k):
    local=LocalVotes()
    choices=[(ARMS[0],local),(ARMS[1],BayesianLag()),
             (ARMS[2],SoftAttention()),(ARMS[3],LogisticAction()),
             (ARMS[4],SourceOracle(k)),(ARMS[5],NoHistory())]
    models={}
    costs={}
    for name,m in choices:
        t=time.process_time_ns()
        m.fit(episodes)
        cpu=time.process_time_ns()-t
        models[name]=m
        costs[name]={"FIT_model_CPU_ns":cpu,
                     "source_training_episodes_seen":len(episodes) if name!=ARMS[4] else 0,
                     "checkpoint_bytes":len(stable(m.state()).encode()),
                     "model_state_SHA256":digest(m.state()),
                     "checkpoint_state":m.state()}
    shifted=LocalVotes(1)
    shifted.v=dict(local.v);shifted.updates=local.updates
    models[ARMS[6]]=shifted
    costs[ARMS[6]]={
       "FIT_model_CPU_ns":0,
       "source_training_episodes_seen":len(episodes),
       "checkpoint_bytes":len(stable(shifted.state()).encode()),
       "model_state_SHA256":digest(shifted.state()),
       "shared_FIT_state_of":ARMS[0]}
    return models,costs

def episode(cls,k,di,rep,i,role,policy=None):
    env=cls(num_decks=1,k=k)
    start=time.process_time_ns()
    first,unused=env.reset(seed=source_seed(role,di,rep,i))
    del unused
    first=int(first)
    need(0<=first<4 and env.action_space.contains(0),
         "EXTERNAL_SOURCE_RESET_PUBLIC_SUIT_INVALID")
    history=[first];data=[]
    result=0;wins=0;loss=0;unscored=0;choice_cpu=0
    trace=[]
    for t in range(51):
        if policy is None:
            a=(t+i)%4
        else:
            start_choice=time.process_time_ns()
            a=policy.choose(history,t)
            choice_cpu+=time.process_time_ns()-start_choice
        need(type(a) is int and 0<=a<4 and env.action_space.contains(a),
             "EXTERNAL_SOURCE_ACTION_NOT_LEGAL")
        nxt,r,terminated,truncated,private_info=env.step(a)
        del private_info
        nxt=int(nxt)
        need(0<=nxt<4 and terminated==(t==50) and truncated is False,
             "EXTERNAL_SOURCE_PUBLIC_NEXT_OR_TERMINAL_DRIFT")
        scaled=float(r)*(52-k)
        need(min(abs(scaled-j) for j in (-1.,0.,1.))<1e-7,
             "REAL_ORIGINAL_SOURCE_REWARD_DRIFT")
        sign=round(scaled)
        need((sign==0)==(t<k-1),
             "REAL_SOURCE_REWARD_ELIGIBILITY_OR_ZERO_DRIFT")
        wins+=int(sign>0);loss+=int(sign<0);unscored+=int(sign==0)
        result+=sign
        data.append({"public_time_step":t,"public_suit_history":tuple(history),
                     "real_original_source_action":a,
                     "real_original_source_reward_sign":sign})
        trace.append((int(history[t]),a,sign,nxt))
        history.append(nxt)
    need(len(history)==52 and wins+loss==52-k and unscored==k-1,
         "REAL_ORIGINAL_SOURCE_PUBLIC_STEP_COUNTS_INVALID")
    return {"source_role":role,"original_seed":source_seed(role,di,rep,i),
            "source_k_hidden_from_fit_policy":k,
            "source_public_suit_observations":history if role=="FIT" else [],
            "source_public_observation_SHA256":digest(history),
            "source_original_legal_step_count":51,
            "source_real_reward_positive_steps":wins,
            "source_real_reward_negative_steps":loss,
            "source_real_reward_unscored_steps":unscored,
            "source_original_signed_reward_per_scored_step":result/(52-k),
            "source_original_real_action_reward_trace_SHA256":digest(trace),
            "source_original_action_reward_trace":trace if role=="DEV" else [],
            "source_public_observed_original_actions":data if role=="FIT" else [],
            "source_process_and_model_CPU_ns":time.process_time_ns()-start,
            "model_choice_CPU_ns":choice_cpu}

def run(root):
    cls=original_source(root)
    role_ids=[source_seed(role,di,rep,i)
              for role,n in (("FIT",FIT_N),("DEV",DEV_N))
              for di in range(2) for rep in REPS for i in range(n)]
    need(len(role_ids)==len(set(role_ids))==2*len(REPS)*(FIT_N+DEV_N),
         "FROZEN_ORIGINAL_FIT_DEV_ROLES_COLLIDE")
    result={"schema":"forge.optimizer.o15.external-reward-delayed-public-memory-v1",
            "frozen_FIRST_prereg":"51ef965365396b3b42ab3564f984eae4c9403167",
            "source_original_git_commit":SOURCE_COMMIT,
            "source_git_blobs":SOURCE_BLOBS,
            "source_families":"ONE_PUBLICLY_INSPECTED_EXTERNAL_POPGYM_FAMILY",
            "source_private_deck_or_target_to_policy":False,
            "FSA_Q21_HELD_first_use_consumed":0,
            "native_Wingless_or_Yggdrasil_integrated":False,
            "historical_O14_structural_transfer_NO_GO_preserved":True,
            "scientific_architecture_promoted":False,
            "scenarios":[],"disposition":"O15_ORIGINAL_SOURCE_PROTOCOL_INVALID"}
    public_fit={"schema":"forge.optimizer.o15.genuine_original_shared_public_fit.v1",
                "scenarios":[]}
    started=time.process_time_ns()
    tracemalloc.start()
    try:
        per=[]
        for di,k in enumerate(DELAYS):
            for rep in REPS:
                fit=[episode(cls,k,di,rep,i,"FIT") for i in range(FIT_N)]
                public_fit["scenarios"].append({"k":k,"replica":rep,
                                               "real_source_SHARED_FIT":fit})
                models,costs=model_fit(fit,k)
                frozen={name:digest(m.state()) for name,m in models.items()}
                rows={}
                for name,m in models.items():
                    dev=[episode(cls,k,di,rep,i,"DEV",m) for i in range(DEV_N)]
                    rows[name]={
                       "original_real_DEV_episodes":DEV_N,
                       "real_source_original_DEV_legal_actions":51*DEV_N,
                       "real_source_original_scored_actions":(52-k)*DEV_N,
                       "source_original_reward_per_scored_action":
                          sum(ep["source_real_reward_positive_steps"]-
                              ep["source_real_reward_negative_steps"]
                              for ep in dev)/(DEV_N*(52-k)),
                       "source_original_correct_scored_rate":
                          sum(ep["source_real_reward_positive_steps"] for ep in dev)/
                          (DEV_N*(52-k)),
                       "actual_source_PUBLIC_observation_hashes":
                          [ep["source_public_observation_SHA256"] for ep in dev],
                       "source_original_DEV_all_episode_receipts":dev,
                       "DEV_model_decision_CPU_ns":sum(ep["model_choice_CPU_ns"] for ep in dev),
                       "DEV_original_env_and_model_CPU_ns":sum(ep["source_process_and_model_CPU_ns"] for ep in dev)}
                need(all(digest(m.state())==frozen[name] for name,m in models.items()),
                     "SOURCE_DEV_MODEL_CHECKPOINT_MUTATED")
                for i in range(DEV_N):
                    observed={rows[name]["actual_source_PUBLIC_observation_hashes"][i]
                              for name in ARMS}
                    need(len(observed)==1,"ORIGINAL_SOURCE_DEV_PAIRED_OBSERVATION_DRIFT")
                gain=lambda name:rows[ARMS[0]]["source_original_reward_per_scored_action"]-rows[name]["source_original_reward_per_scored_action"]
                n=rows[ARMS[0]]["source_original_correct_scored_rate"]
                strong=max(rows[x]["source_original_reward_per_scored_action"]
                           for x in (ARMS[1],ARMS[2],ARMS[3]))
                baseline=rows[ARMS[0]]["source_original_reward_per_scored_action"]
                lag=models[ARMS[0]].learned_lag()
                advance=(lag==k-1 and n>=.95 and
                          gain(ARMS[5])>=.50 and gain(ARMS[6])>=.50 and
                          baseline>=strong-.05)
                per.append(advance)
                result["scenarios"].append({
                   "k_true_source_constructor_auditor_only":k,"replica":rep,
                   "shared_FIT_original_real_reset_episodes":FIT_N,
                   "shared_FIT_public_source_identity_SHA256":digest(source_only_identity(fit)),
                   "original_SOURCE_actual_learned_lag":lag,
                   "FIT_model_costs_and_source_free_states":costs,
                   "DEV_original_source_actual_reward_by_arm":rows,
                   "source_candidate_minus_best_learned_conventional":baseline-strong,
                   "source_candidate_minus_no_past":gain(ARMS[5]),
                   "source_candidate_minus_shift_lag":gain(ARMS[6]),
                   "source_candidate_public_advancement":advance})
                print("O15_SOURCE_K="+str(k)+" REPLICA="+str(rep)+
                      " LOCAL_SELECTED_LAG="+str(lag)+" ORIGINAL_REWARD="+
                      stable({arm:round(rows[arm]["source_original_reward_per_scored_action"],4)
                              for arm in ARMS}),flush=True)
        result["original_source_fit_resets"]=2*len(REPS)*FIT_N
        result["original_source_DEV_resets"]=2*len(REPS)*len(ARMS)*DEV_N
        result["original_source_real_total_resets"]=(
            result["original_source_fit_resets"]+result["original_source_DEV_resets"])
        result["original_source_REAL_legal_step_calls"]=(
            result["original_source_real_total_resets"]*51)
        need(result["original_source_real_total_resets"]==1296 and
             result["original_source_REAL_legal_step_calls"]==66096,
             "REAL_EXTERNAL_SOURCE_ACTION_BUDGET_CHANGED")
        result["shared_FIT_public_source_SHA256"]=digest(source_only_identity(public_fit))
        result["disposition"]=(
          "O15_PUBLIC_HANDDESIGNED_LOCAL_RELEVANCE_LEARNING_SUPPORTED_NO_SUPERIORITY"
          if all(per) else "O15_PUBLIC_LOCAL_LAG_SELECTION_NO_GO")
    except Exception as e:
        result["first_failure"]=type(e).__name__+":"+str(e)[:950]
    finally:
        _,traced=tracemalloc.get_traced_memory()
        tracemalloc.stop()
        result["all_original_source_and_models_process_CPU_ns"]=time.process_time_ns()-started
        result["process_tracemalloc_peak_bytes"]=traced
        if os.name=="posix":
            import resource
            result["process_peak_RSS_bytes"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        else:
            result["process_peak_RSS_bytes"]="NOT_MEASURED_WINDOWS"
    return result,public_fit

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True)
    p.add_argument("--out",required=True)
    o=p.parse_args()
    folder=Path(o.out);folder.mkdir(parents=True,exist_ok=True)
    receipt,fit=run(Path(o.upstream).resolve())
    (folder/"o15-source-native-public-reward-receipt.json").write_text(
        json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (folder/"o15-original-Popgym-shared-FIT-public-history.json").write_text(
        stable(fit)+"\n",encoding="utf-8")
    print("O15_DISPOSITION="+receipt["disposition"],flush=True)
    return 2 if receipt["disposition"]=="O15_ORIGINAL_SOURCE_PROTOCOL_INVALID" else 0
if __name__=="__main__":
    raise SystemExit(main())
