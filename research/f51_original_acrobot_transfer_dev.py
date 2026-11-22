#!/usr/bin/env python3
"""F51 independently sourced Acrobot dynamics transfer (DEV, not scientific first-use).

Only genuine Farama Gymnasium v1.2.3 AcrobotEnv dynamics are allowed. No
fallback to fixtures or locally simulated physics. No action-space oracle.
"""
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np
import gymnasium as gym
from gymnasium.envs.classic_control.acrobot import AcrobotEnv

SCHEMA="forge.eureka.f51.original-acrobot-dynamics-transfer-dev.v1"
ORIGINAL_COMMIT="365080941ea3a815ac09e57a7d4ee263a142651d"
ORIGINAL_FILE_BLOB="28c440af281858c30e95fb6023f19923065d64fe"
FIT=(21011,21017,21019,21023,21029,21031)
TRANSFER=(31011,31013,31017,31019,31021,31023,31027,31029,31031,31033,31037,31039)
RETENTION=(32011,32013,32017,32019,32023,32029,32031,32037)
FORBIDDEN=(59,83)
ARMS=("contradiction-gated-td","always-td","frozen-fqi","momentum-rule","wrong-credit-td")
CONTROLS=("always-td","frozen-fqi","momentum-rule")
GAMMA=.98
RIDGE=.05
FQI_PASSES=40
MAX_STEPS=500
DIMS=15


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def check_original():
    """Refuse to score unless real Acrobot is imported from pinned upstream checkout."""
    root=os.environ.get("F51_ORIGINAL_GYMNASIUM_ROOT","")
    if not root or not Path(root).is_dir():
        raise RuntimeError("F51_EXTERNAL_ORIGINAL_ROOT_UNVERIFIED")
    path=Path(inspect.getfile(AcrobotEnv)).resolve()
    expected=(Path(root)/"gymnasium/envs/classic_control/acrobot.py").resolve()
    if path!=expected:
        raise RuntimeError("F51_EXTERNAL_SOURCE_SHADOW_OR_FAKE_IMPORT")
    if gym.__version__!="1.2.3":
        raise RuntimeError("F51_EXTERNAL_VERSION_NOT_PINNED")
    if str(Path(gym.__file__).resolve()).startswith(str(Path(root).resolve())) is False:
        raise RuntimeError("F51_PACKAGE_NOT_ORIGINAL_CHECKOUT")
    with gym.make("Acrobot-v1") as env:
        if env.spec is None or env.spec.id!="Acrobot-v1":
            raise RuntimeError("F51_REAL_ACROBOT_NOT_AVAILABLE")
        if env.action_space.n!=3 or env.observation_space.shape!=(6,):
            raise RuntimeError("F51_SOURCE_INTERFACE_CHANGED")
        if env.unwrapped.book_or_nips!="book":
            raise RuntimeError("F51_ORIGINAL_DYNAMICS_CHANGED")
    if len(set((*FIT,*TRANSFER,*RETENTION)))!=26 or set(FORBIDDEN)&set((*FIT,*TRANSFER,*RETENTION)):
        raise RuntimeError("F51_FROZEN_SEED_CUSTODY_COLLISION")
    if any(seed in (21011,21017,21019,21023,21029,21031) for seed in (*TRANSFER,*RETENTION)):
        raise RuntimeError("F51_HELDOUT_LEAK")
    return {"gymnasium_version":gym.__version__,
            "upstream_commit":ORIGINAL_COMMIT,
            "acrobot_git_blob":ORIGINAL_FILE_BLOB,
            "module_path":str(path)}


def features(obs):
    if len(obs)!=6:
        raise ValueError("F51_PUBLIC_SIX_OBSERVATIONS_REQUIRED")
    a,b,c,d,v1,v2=map(float,obs)
    x=np.array([math.atan2(b,a)/math.pi,math.atan2(d,c)/math.pi,
                float(np.clip(v1/(4*math.pi),-1,1)),
                float(np.clip(v2/(9*math.pi),-1,1))],dtype=np.float64)
    out=[1.0,*x.tolist(),*(x*x).tolist()]
    out.extend(float(x[i]*x[j]) for i in range(4) for j in range(i+1,4))
    arr=np.asarray(out,dtype=np.float64)
    if arr.shape!=(DIMS,) or not np.all(np.isfinite(arr)):
        raise ValueError("F51_NONFINITE_PUBLIC_FEATURES")
    return arr


def energy_rule(obs):
    return 2 if float(obs[5])>=0 else 0


def behavior_action(obs,rng):
    if float(rng.random())<.60:
        return int(rng.integers(0,3))
    if abs(float(obs[5]))<.2 and float(rng.random())<.1:
        return 1
    return energy_rule(obs)


def new_real_env(mode):
    if mode not in ("book","nips"):
        raise ValueError("F51_UNKNOWN_ORIGINAL_DYNAMICS_MODE")
    env=gym.make("Acrobot-v1")
    if not isinstance(env.unwrapped,AcrobotEnv):
        env.close()
        raise RuntimeError("F51_REAL_SOURCE_TYPE_MISMATCH")
    env.unwrapped.book_or_nips=mode  # Evaluator only; NEVER passed to policy.
    return env


def collect_fit():
    """Shared fully authentic physical FIT transcript; only book source seeds."""
    records=[]
    counts=[0,0,0]
    episodes=[]
    start=time.perf_counter()
    for seed in FIT:
        for ep in range(8):
            episode_seed=seed*100+ep
            rng=np.random.default_rng(episode_seed^0xF510FACE)
            env=new_real_env("book")
            try:
                state,_=env.reset(seed=episode_seed)
                trajectory=[]
                for t in range(MAX_STEPS):
                    action=behavior_action(state,rng)
                    next_state,reward,terminated,truncated,_info=env.step(action)
                    entry=[list(map(float,state)),int(action),float(reward),
                           list(map(float,next_state)),bool(terminated),bool(truncated)]
                    records.append(entry)
                    trajectory.append(entry)
                    counts[action]+=1
                    state=next_state
                    if terminated or truncated:
                        break
                episodes.append({"seed":seed,"episode":ep,"steps":len(trajectory),
                                 "terminated":bool(terminated),"trace_sha256":digest(trajectory)})
            finally:
                env.close()
    if len(episodes)!=48 or not records or min(counts)==0:
        raise RuntimeError("F51_REAL_FIT_TRANSCRIPT_OR_ACTION_SUPPORT_MISSING")
    if sum(counts)!=len(records) or len(records)>48*MAX_STEPS:
        raise RuntimeError("F51_FIT_PHYSICAL_ACTION_COUNT_DRIFT")
    return records,counts,episodes,time.perf_counter()-start


def fit_fqi(records,passes=FQI_PASSES):
    """40 offline full-batch linear fitted-Q passes on common public FIT records."""
    if passes!=40 and passes!=2:
        raise ValueError("F51_FQI_PASSES_UNAUTHORIZED")
    if not records:
        raise ValueError("F51_NO_PUBLIC_FIT_DATA")
    states=np.vstack([features(x[0]) for x in records])
    next_states=np.vstack([features(x[3]) for x in records])
    actions=np.fromiter((x[1] for x in records),dtype=np.int64,count=len(records))
    rewards=np.fromiter((x[2] for x in records),dtype=np.float64,count=len(records))
    terminal=np.fromiter((x[4] or x[5] for x in records),dtype=np.float64,count=len(records))
    if not np.all(np.isfinite(states)) or not np.all(np.isfinite(next_states)):
        raise ValueError("F51_NONFINITE_REAL_PHYSICS")
    inds=[np.where(actions==a)[0] for a in range(3)]
    if any(len(i)==0 for i in inds):
        raise RuntimeError("F51_ALL_THREE_TORQUES_NOT_TRAINED")
    # Exact per-action ridge matrices reused on all iterations.
    design=[]
    for ids in inds:
        X=states[ids]
        design.append((ids,X,np.linalg.solve(X.T@X+RIDGE*np.eye(DIMS),X.T)))
    theta=np.zeros((3,DIMS),dtype=np.float64)
    for _ in range(passes):
        next_values=next_states@theta.T
        target=np.clip(rewards+GAMMA*(1-terminal)*np.max(next_values,axis=1),-100,0)
        theta=np.stack([M@target[ids] for ids,X,M in design])
    if not np.all(np.isfinite(theta)):
        raise RuntimeError("F51_FITTED_Q_NUMERICAL_FAILURE")
    return theta


class Policy:
    """Purely public observation/action/real reward, episode-local updates."""
    def __init__(self,kind,frozen_theta):
        if kind not in ARMS:
            raise ValueError("F51_UNKNOWN_POLICY_OR_ORACLE")
        if np.asarray(frozen_theta).shape!=(3,DIMS):
            raise ValueError("F51_UNQUALIFIED_TRAINED_MODEL")
        self.kind=kind
        self.theta=np.asarray(frozen_theta,dtype=np.float64).copy()
        self.streak=0
        self.window=0
        self.trigger_events=0
        self.adapt_steps=0
        self.physical_observations=0
        self.decision_ns=0

    def action(self,obs):
        started=time.perf_counter_ns()
        if self.kind=="momentum-rule":
            a=energy_rule(obs)
        else:
            phi=features(obs)
            a=int(np.argmax(self.theta@phi))
        self.decision_ns+=time.perf_counter_ns()-started
        return a

    def observe(self,old,actual_action,reward,next_observation,done):
        if type(actual_action) is not int or actual_action not in (0,1,2):
            raise ValueError("F51_INVALID_REAL_ACTION_CREDIT")
        self.physical_observations+=1
        if self.kind in ("frozen-fqi","momentum-rule"):
            return
        phi=features(old)
        next_phi=features(next_observation)
        q=float(self.theta[actual_action]@phi)
        target=float(reward)+(0. if done else GAMMA*float(np.max(self.theta@next_phi)))
        td=target-q
        if not math.isfinite(td):
            raise ValueError("F51_NONFINITE_TD_CONTRADICTION")
        if self.kind=="always-td":
            rate=.18
        else:
            self.streak=self.streak+1 if abs(td)>8.0 else 0
            if self.streak>=2:
                self.window=12
                self.trigger_events+=1
                self.streak=0
            rate=.18 if self.window>0 else .01
            if self.window>0:
                self.window-=1
                self.adapt_steps+=1
        credited_action=(actual_action+1)%3 if self.kind=="wrong-credit-td" else actual_action
        update=rate*float(np.clip(td,-30,30))*phi/(1.+float(phi@phi))
        self.theta[credited_action]+=update
        if not np.all(np.isfinite(self.theta)):
            raise ValueError("F51_ADAPTED_PUBLIC_MODEL_NOT_FINITE")

    def snapshot(self):
        return {"kind":self.kind,"theta":self.theta.tolist(),
                "streak":self.streak,"window":self.window,
                "trigger_events":self.trigger_events,"adapt_steps":self.adapt_steps,
                "physical_observations":self.physical_observations}


def evaluate(seed,mode,kind,theta):
    if type(seed) is not int or seed in FORBIDDEN or seed not in (*TRANSFER,*RETENTION):
        raise ValueError("F51_UNAUTHORIZED_DEV_OR_FIRST_USE_SEED")
    if (mode=="nips")!=(seed in TRANSFER):
        raise ValueError("F51_TRANSFER_RETENTION_DYNAMICS_CUSTODY")
    env=new_real_env(mode)
    policy=Policy(kind,theta)
    try:
        state,_=env.reset(seed=seed)
        public_trace=[]
        total=0.
        terminated=truncated=False
        for t in range(MAX_STEPS):
            action=policy.action(state)
            next_obs,reward,terminated,truncated,_=env.step(action)
            policy.observe(state,action,float(reward),next_obs, bool(terminated or truncated))
            public_trace.append([list(map(float,state)),action,float(reward),
                                 list(map(float,next_obs)),bool(terminated),bool(truncated)])
            total+=float(reward)
            state=next_obs
            if terminated or truncated:
                break
    finally:
        env.close()
    if not public_trace or len(public_trace)>MAX_STEPS or policy.physical_observations!=len(public_trace):
        raise RuntimeError("F51_REAL_ORIGINAL_EVALUATION_INCOMPLETE")
    return {"seed":seed,"return":total,"steps":len(public_trace),
            "success":bool(terminated),"truncated":bool(truncated),
            "trace_sha256":digest(public_trace),
            "snapshot_sha256":digest(policy.snapshot()),
            "triggers":policy.trigger_events,"adapt_steps":policy.adapt_steps,
            "decision_ns":policy.decision_ns,
            "actions":[sum(row[1]==a for row in public_trace) for a in (0,1,2)]}


def score(source_info,records,counts,train_episodes,train_seconds,theta,fit_seconds):
    model=np.asarray(theta,dtype=np.float64).tolist()
    cold=np.asarray(json.loads(canonical(model)),dtype=np.float64)
    if not np.array_equal(cold,theta):
        raise RuntimeError("F51_TRAINED_MODEL_COLD_RESTORE_DRIFT")
    start=time.perf_counter()
    report={
        "schema":SCHEMA,"original_independent_environment":True,
        "synthetic_custom_environment":False,"protected_first_use_consumed":False,
        "scientific_accepted":False,"owner_eligible":False,
        "general_rsi_proven":False,"matched_whole_process_compute_proven":False,
        "upstream":source_info,
        "train_seeds":FIT,"transfer_seeds":TRANSFER,"retention_seeds":RETENTION,
        "train_transition_count":len(records),"train_action_counts":counts,
        "train_episode_count":len(train_episodes),
        "training_sha256":digest(records),
        "training_episodes_sha256":digest(train_episodes),
        "fitted_fqi_model_sha256":digest(model),
        "fqi_passes":FQI_PASSES,
        "fit_real_physical_collection_seconds":train_seconds,
        "fit_batch_learning_seconds":fit_seconds,
        "arms":{}
    }
    for kind in ARMS:
        out=[]
        for seed in (*TRANSFER,*RETENTION):
            mode="nips" if seed in TRANSFER else "book"
            warm=evaluate(seed,mode,kind,theta)
            replay=evaluate(seed,mode,kind,cold)
            keys=("return","steps","success","truncated","trace_sha256",
                  "snapshot_sha256","triggers","adapt_steps","actions")
            if any(warm[k]!=replay[k] for k in keys):
                raise RuntimeError("F51_ORIGINAL_ENV_COLD_PUBLIC_TRACE_OR_MEMORY_MISMATCH")
            item={k:warm[k] for k in keys}
            item.update({"seed":seed,"mode":mode,"decision_ns":warm["decision_ns"],"cold_matches":True})
            out.append(item)
        transfer=out[:len(TRANSFER)]
        retention=out[len(TRANSFER):]
        ns=sum(ep["decision_ns"] for ep in transfer)
        steps=sum(ep["steps"] for ep in transfer)
        if steps<=0 or ns<=0:
            raise RuntimeError("F51_UNMEASURED_ORIGINAL_ACTION_COST")
        report["arms"][kind]={
            "episodes":out,
            "transfer_mean_return":sum(e["return"] for e in transfer)/len(transfer),
            "retention_mean_return":sum(e["return"] for e in retention)/len(retention),
            "transfer_successes":sum(e["success"] for e in transfer),
            "retention_successes":sum(e["success"] for e in retention),
            "triggered_transfer_episodes":sum(e["triggers"]>0 for e in transfer),
            "transfer_decision_ns_per_step":ns/steps,
            "total_transfer_actions":steps
        }
    strongest=max(CONTROLS,key=lambda k:report["arms"][k]["transfer_mean_return"])
    base=report["arms"][strongest]
    cand=report["arms"]["contradiction-gated-td"]
    negative=report["arms"]["wrong-credit-td"]
    report["strongest_conventional"]=strongest
    report["transfer_return_gain"]=cand["transfer_mean_return"]-base["transfer_mean_return"]
    report["transfer_success_gain"]=cand["transfer_successes"]-base["transfer_successes"]
    report["transfer_paired_seed_wins"]=sum(
        a["return"]>b["return"]
        for a,b in zip(cand["episodes"][:len(TRANSFER)],base["episodes"][:len(TRANSFER)]))
    report["best_retention"]=max(report["arms"][k]["retention_mean_return"] for k in CONTROLS)
    report["retention_margin"]=cand["retention_mean_return"]-report["best_retention"]
    report["wrong_credit_return_gain"]=cand["transfer_mean_return"]-negative["transfer_mean_return"]
    report["decision_cost_ratio"]=(
        cand["transfer_decision_ns_per_step"]/base["transfer_decision_ns_per_step"])
    report["external_source_scoring_seconds"]=time.perf_counter()-start
    report["whole_process_seconds"]=(train_seconds+fit_seconds+
                                     report["external_source_scoring_seconds"])
    report["frozen_conditions_met"]=bool(
        report["transfer_return_gain"]>=20
        and report["transfer_paired_seed_wins"]>=8
        and report["transfer_success_gain"]>=3
        and report["wrong_credit_return_gain"]>=20
        and report["retention_margin"]>=-15
        and cand["triggered_transfer_episodes"]>=3
        and report["decision_cost_ratio"]<=2
        and all(len(a["episodes"])==20
                and all(e["cold_matches"] and 0<e["steps"]<=MAX_STEPS
                        for e in a["episodes"]) for a in report["arms"].values())
    )
    report["classification"]=(
        "F51_DEV_SIGNAL_UNVERIFIED" if report["frozen_conditions_met"]
        else "F51_DEV_NO_GO")
    report["report_sha256"]=digest(report)
    return report


def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    if len(argv)!=1:
        raise ValueError("F51_USAGE: python f51_original_acrobot_transfer_dev.py /tmp/report.json")
    original=check_original()
    records,counts,episodes,fit_seconds=collect_fit()
    clock=time.perf_counter()
    model=fit_fqi(records)
    train_seconds=time.perf_counter()-clock
    report=score(original,records,counts,episodes,fit_seconds,model,train_seconds)
    out=Path(argv[0]).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(canonical(report)+b"\n")
    print("F51_ORIGINAL_ACROBOT="+report["classification"]+" sha256="+report["report_sha256"])
    print("F51_SOURCE_UPSTREAM_COMMIT="+original["upstream_commit"]+" FILE_BLOB="+original["acrobot_git_blob"])
    print("F51_REAL_FIT_TRANSITIONS="+str(report["train_transition_count"])+" SHA="+report["training_sha256"])
    print("F51_ALL_ARMS="+json.dumps({k:{"transfer":v["transfer_mean_return"],
        "retention":v["retention_mean_return"],"transfer_successes":v["transfer_successes"],
        "triggered_transfer_episodes":v["triggered_transfer_episodes"],
        "ns_per_step":v["transfer_decision_ns_per_step"]} for k,v in report["arms"].items()},sort_keys=True))
    print("F51_STRONGEST="+strongest_name(report)+" TRANSFER_GAIN="+str(report["transfer_return_gain"])
          +" PAIRED_WINS="+str(report["transfer_paired_seed_wins"])
          +" SUCCESS_GAIN="+str(report["transfer_success_gain"])
          +" NEGATIVE_MARGIN="+str(report["wrong_credit_return_gain"])
          +" COST_RATIO="+str(report["decision_cost_ratio"]))
    print("F51_REPORT_SHA256="+report["report_sha256"])
    return report


def strongest_name(report):
    return report["strongest_conventional"]


if __name__=="__main__":
    main()
