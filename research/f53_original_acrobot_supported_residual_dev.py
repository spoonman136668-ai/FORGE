#!/usr/bin/env python3
"""F53 fresh original Acrobot conservative action-supported residual DEV.

Frozen before implementation: 93b46cf3fc03327f35e080e1ca909e9c6b54253f.
Never execute scored seeds in focused tests or without separately verified
scientific DEV execution authority. Never reuse F51 consumed DEV cohorts.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import f51_original_acrobot_transfer_dev as f51

SCHEMA="forge.eureka.f53.original-acrobot-supported-residual-dev.v1"
PROTOCOL_COMMIT="93b46cf3fc03327f35e080e1ca909e9c6b54253f"
ORIGINAL_F51_FIT_SHA256="63d31930006ec2f465e4becd989c1a0b922e15a0842ef991fe424074d436a31a"
F51_SOURCE_BLOB="d3114ac66589e6b9f623318da721449090cfd54a"
TRANSFER=(41011,41013,41017,41019,41021,41023,41027,41029,
          41031,41033,41037,41039,41041,41047,41051,41057)
RETENTION=(42011,42013,42017,42019,42023,42029,42031,42037)
ARMS=("supported-residual","momentum-rule","frozen-fqi",
      "always-td","margin-only","rotated-credit")
CONVENTIONAL=("momentum-rule","frozen-fqi","always-td")
MARGIN=4.0
SUPPORT_QUANTILE=.90


def validate_cohorts():
    all_seeds=(*TRANSFER,*RETENTION)
    previous=(*f51.FIT,*f51.TRANSFER,*f51.RETENTION,*f51.FORBIDDEN)
    if (len(TRANSFER)!=16 or len(RETENTION)!=8 or
        len(set(all_seeds))!=24 or set(all_seeds)&set(previous) or
        len(set(previous))!=len(previous) or
        tuple(f51.FIT)!=(21011,21017,21019,21023,21029,21031)):
        raise RuntimeError("F53_FRESH_DEV_COHORT_OR_FIRST_USE_COLLISION")


def check_source():
    validate_cohorts()
    source=f51.check_original()
    root=os.environ.get("F51_ORIGINAL_GYMNASIUM_ROOT","")
    if not root:
        raise RuntimeError("F53_ORIGINAL_SOURCE_ROOT_MISSING")
    def git(*args):
        p=subprocess.run(("git","-C",root,*args),capture_output=True,
                         text=True,check=True)
        return p.stdout.strip()
    if (git("rev-parse","HEAD")!=f51.ORIGINAL_COMMIT or
        git("rev-parse","HEAD:gymnasium/envs/classic_control/acrobot.py")!=
        f51.ORIGINAL_FILE_BLOB or source["upstream_commit"]!=f51.ORIGINAL_COMMIT):
        raise RuntimeError("F53_ORIGINAL_UPSTREAM_SOURCE_HASH_DRIFT")
    return source


def frozen_fit():
    source=check_source()
    start=time.perf_counter()
    records,coverage,episodes,collection=f51.collect_fit()
    if (len(records)!=8974 or coverage!=[3604,1824,3546] or
        len(episodes)!=48 or sum(e["steps"] for e in episodes)!=len(records) or
        f51.digest(records)!=ORIGINAL_F51_FIT_SHA256):
        raise RuntimeError("F53_ORIGINAL_COMMON_FIT_CUSTODY_DRIFT")
    fit_start=time.perf_counter()
    theta=f51.fit_fqi(records)
    fitting=time.perf_counter()-fit_start
    if theta.shape!=(3,f51.DIMS) or not np.all(np.isfinite(theta)):
        raise RuntimeError("F53_ORIGINAL_TRAINED_FQI_INVALID")
    cal_start=time.perf_counter()
    X=np.vstack([f51.features(row[0]) for row in records])
    actions=np.asarray([row[1] for row in records],dtype=np.int64)
    inverses=[]
    thresholds=[]
    for a in range(3):
        part=X[actions==a]
        if part.shape[0]!=coverage[a]:
            raise RuntimeError("F53_ORIGINAL_ACTION_COVERAGE_INVALID")
        inv=np.linalg.inv(part.T@part+f51.RIDGE*np.eye(f51.DIMS))
        lever=np.einsum("ij,jk,ik->i",part,inv,part)
        threshold=float(np.quantile(lever,SUPPORT_QUANTILE))
        if (not np.all(np.isfinite(inv)) or not np.all(np.isfinite(lever))
            or threshold<=0 or not math.isfinite(threshold)):
            raise RuntimeError("F53_PUBLIC_FIT_SUPPORT_INVALID")
        inverses.append(inv)
        thresholds.append(threshold)
    calibration=time.perf_counter()-cal_start
    return {
        "source":source,"theta":theta,"inverses":np.stack(inverses),
        "thresholds":np.asarray(thresholds,dtype=np.float64),
        "fitted_sha256":f51.digest(theta.tolist()),
        "support_sha256":f51.digest({"inverses":np.stack(inverses).tolist(),
                                   "thresholds":thresholds}),
        "fit_record_sha256":f51.digest(records),"fit_action_counts":coverage,
        "fit_steps":len(records),"fit_episodes":len(episodes),
        "source_collection_seconds":collection,"fqi_fitting_seconds":fitting,
        "support_calibration_seconds":calibration,
        "total_preparation_seconds":time.perf_counter()-start
    }


class SupportedPolicy:
    """All inference inputs are public obs6 and the same frozen FIT model."""
    def __init__(self,kind,theta,inverses,thresholds):
        if kind not in ARMS:
            raise ValueError("F53_POLICY_NOT_FROZEN")
        self.kind=kind
        self.theta=np.asarray(theta,dtype=np.float64).copy()
        self.inverses=np.asarray(inverses,dtype=np.float64).copy()
        self.thresholds=np.asarray(thresholds,dtype=np.float64).copy()
        if (self.theta.shape!=(3,15) or self.inverses.shape!=(3,15,15)
            or self.thresholds.shape!=(3,) or
            not all(np.all(np.isfinite(a)) for a in (
                self.theta,self.inverses,self.thresholds)) or
            np.any(self.thresholds<=0)):
            raise ValueError("F53_INVALID_COLD_FIT_MODEL_OR_SUPPORT")
        self.base=f51.Policy(kind,self.theta) if kind in f51.ARMS else None
        self.decisions=0
        self.momentum_disagreements=0
        self.physical_observations=0
        self.decision_ns=0

    def action(self,obs):
        tick=time.perf_counter_ns()
        h=f51.energy_rule(obs)
        if self.base is not None:
            a=self.base.action(obs)
        else:
            phi=f51.features(obs)
            rows=self.theta if self.kind!="rotated-credit" else self.theta[[1,2,0]]
            q=rows@phi
            g=int(np.argmax(q))
            allow=g!=h and float(q[g]-q[h])>=MARGIN
            if allow and self.kind!="margin-only":
                lg=float(phi@self.inverses[g]@phi)
                lh=float(phi@self.inverses[h]@phi)
                allow=(lg<=float(self.thresholds[g]) and
                       lh<=float(self.thresholds[h]))
            a=g if allow else h
        if type(a) is not int or a not in (0,1,2):
            raise RuntimeError("F53_INVALID_PUBLIC_ACTION")
        self.decisions+=1
        self.momentum_disagreements+=int(a!=h)
        self.decision_ns+=time.perf_counter_ns()-tick
        return a

    def observe(self,before,action,reward,after,done):
        self.physical_observations+=1
        if self.base is not None:
            self.base.observe(before,action,reward,after,done)

    def snapshot(self):
        return {"kind":self.kind,"theta":
                self.base.theta.tolist() if self.base is not None else
                self.theta.tolist(),"decisions":self.decisions,
                "disagreements":self.momentum_disagreements,
                "physical_observations":self.physical_observations,
                "base":self.base.snapshot() if self.base is not None else None}


def evaluate(seed,mode,kind,theta,inverses,thresholds):
    # Fail before creating a source environment on any historic/unknown seed.
    validate_cohorts()
    if type(seed) is not int or seed not in (*TRANSFER,*RETENTION):
        raise ValueError("F53_UNAUTHORIZED_DEV_SEED")
    if (mode=="nips")!=(seed in TRANSFER) or mode not in ("nips","book"):
        raise ValueError("F53_EVALUATOR_MODE_OR_SEED_MISMATCH")
    policy=SupportedPolicy(kind,theta,inverses,thresholds)
    env=f51.new_real_env(mode)
    trace=[]
    started=time.perf_counter()
    try:
        obs,_=env.reset(seed=seed)
        ended=False
        for _ in range(f51.MAX_STEPS):
            a=policy.action(obs)
            following,reward,terminated,truncated,_=env.step(a)
            policy.observe(obs,a,float(reward),following,bool(terminated or truncated))
            trace.append([list(map(float,obs)),a,float(reward),
                          list(map(float,following)),bool(terminated),bool(truncated)])
            obs=following
            ended=bool(terminated or truncated)
            if ended:
                break
    finally:
        env.close()
    elapsed=time.perf_counter()-started
    if (not trace or len(trace)>500 or
        policy.decisions!=len(trace) or
        policy.physical_observations!=len(trace) or not ended):
        raise RuntimeError("F53_ORIGINAL_ACROBOT_EPISODE_INCOMPLETE")
    return {"seed":seed,"mode":mode,"steps":len(trace),
            "return":sum(float(r[2]) for r in trace),
            "success":bool(trace[-1][4]),"truncated":bool(trace[-1][5]),
            "trace_sha256":f51.digest(trace),
            "policy_snapshot_sha256":f51.digest(policy.snapshot()),
            "momentum_disagreements":policy.momentum_disagreements,
            "decision_ns":policy.decision_ns,"episode_wall_seconds":elapsed,
            "actions":[sum(row[1]==a for row in trace) for a in (0,1,2)]}


def score():
    fit=frozen_fit()    # Original source and public FIT provenance checked.
    cold_theta=np.asarray(json.loads(f51.canonical(fit["theta"].tolist())),dtype=np.float64)
    cold_inv=np.asarray(json.loads(f51.canonical(fit["inverses"].tolist())),dtype=np.float64)
    cold_thresholds=np.asarray(json.loads(f51.canonical(fit["thresholds"].tolist())),dtype=np.float64)
    if (not np.array_equal(fit["theta"],cold_theta) or
        not np.array_equal(fit["inverses"],cold_inv) or
        not np.array_equal(fit["thresholds"],cold_thresholds)):
        raise RuntimeError("F53_COLD_TRAINED_MODEL_OR_SUPPORT_DRIFT")
    report={"schema":SCHEMA,"protocol_commit":PROTOCOL_COMMIT,
            "original_independent_environment":True,
            "synthetic_custom_environment":False,
            "scientific_accepted":False,"owner_eligible":False,
            "general_rsi_proven":False,
            "protected_first_use_consumed":False,
            "matched_whole_process_compute_proven":False,
            "consumes_new_f53_dev_cohort":True,
            "previous_f51_science":"F51_DEV_NO_GO",
            "f52_fit_diagnosis":"F52_FIT_TD_TRIGGER_NOT_OBSERVED",
            "original_source":fit["source"],
            "old_fit_sha256":fit["fit_record_sha256"],
            "fitted_model_sha256":fit["fitted_sha256"],
            "support_sha256":fit["support_sha256"],
            "frozen_support_quantile":SUPPORT_QUANTILE,
            "frozen_margin_q_units":MARGIN,
            "fit_steps":fit["fit_steps"],"fit_episodes":fit["fit_episodes"],
            "fit_action_counts":fit["fit_action_counts"],
            "preparation_seconds":fit["total_preparation_seconds"],
            "fit_collection_seconds":fit["source_collection_seconds"],
            "fqi_fitting_seconds":fit["fqi_fitting_seconds"],
            "support_calibration_seconds":fit["support_calibration_seconds"],
            "transfer_seeds":TRANSFER,"retention_seeds":RETENTION,"arms":{}}
    stable_keys=("return","steps","success","truncated","trace_sha256",
                 "policy_snapshot_sha256","momentum_disagreements","actions")
    total_replays=0
    for kind in ARMS:
        episodes=[]
        for seed in (*TRANSFER,*RETENTION):
            mode="nips" if seed in TRANSFER else "book"
            warm=evaluate(seed,mode,kind,fit["theta"],fit["inverses"],fit["thresholds"])
            cold=evaluate(seed,mode,kind,cold_theta,cold_inv,cold_thresholds)
            if any(warm[k]!=cold[k] for k in stable_keys):
                raise RuntimeError("F53_REAL_ORIGINAL_COLD_TRACE_OR_STATE_DRIFT")
            total_replays+=1
            item=dict(warm)
            item["cold_matches"]=True
            episodes.append(item)
        transfer=episodes[:len(TRANSFER)]
        retention=episodes[len(TRANSFER):]
        steps=sum(ep["steps"] for ep in transfer)
        if steps<1:
            raise RuntimeError("F53_ZERO_REAL_SOURCE_ACTIONS")
        report["arms"][kind]={
            "episodes":episodes,
            "transfer_mean_return":sum(ep["return"] for ep in transfer)/len(TRANSFER),
            "retention_mean_return":sum(ep["return"] for ep in retention)/len(RETENTION),
            "transfer_successes":sum(ep["success"] for ep in transfer),
            "retention_successes":sum(ep["success"] for ep in retention),
            "transfer_episodes_with_deviation":sum(ep["momentum_disagreements"]>0 for ep in transfer),
            "transfer_action_deviations":sum(ep["momentum_disagreements"] for ep in transfer),
            "transfer_real_source_steps":steps,
            "transfer_decision_ns_per_action":
                sum(ep["decision_ns"] for ep in transfer)/steps,
            "transfer_episode_wall_seconds":
                sum(ep["episode_wall_seconds"] for ep in transfer)
        }
    if total_replays!=144 or any(
        len(v["episodes"])!=24 or not all(ep["cold_matches"] for ep in v["episodes"])
        for v in report["arms"].values()):
        raise RuntimeError("F53_ORIGINAL_SOURCE_144_COLD_REPLAYS_INCOMPLETE")
    strongest=max(CONVENTIONAL,key=lambda a:report["arms"][a]["transfer_mean_return"])
    candidate=report["arms"]["supported-residual"]
    baseline=report["arms"][strongest]
    negative=report["arms"]["rotated-credit"]
    best_retention=max(report["arms"][a]["retention_mean_return"] for a in CONVENTIONAL)
    report["strongest_conventional"]=strongest
    report["transfer_mean_gain"]=candidate["transfer_mean_return"]-baseline["transfer_mean_return"]
    report["paired_strict_transfer_wins"]=sum(
        a["return"]>b["return"] for a,b in zip(
            candidate["episodes"][:len(TRANSFER)],baseline["episodes"][:len(TRANSFER)]))
    report["transfer_success_gain"]=candidate["transfer_successes"]-baseline["transfer_successes"]
    report["rotated_credit_margin"]=candidate["transfer_mean_return"]-negative["transfer_mean_return"]
    report["retention_margin"]=candidate["retention_mean_return"]-best_retention
    report["cold_replay_exact_count"]=total_replays
    report["frozen_conditions_met"]=bool(
        report["transfer_mean_gain"]>=15 and
        report["paired_strict_transfer_wins"]>=12 and
        report["transfer_success_gain"]>=0 and
        report["rotated_credit_margin"]>=15 and
        report["retention_margin"]>=-10 and
        candidate["transfer_episodes_with_deviation"]>=4 and
        total_replays==144)
    report["classification"]=("F53_DEV_SIGNAL_UNVERIFIED" if
                              report["frozen_conditions_met"] else "F53_DEV_NO_GO")
    report["report_sha256"]=f51.digest(report)
    return report


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:
        raise ValueError("F53_USAGE: python f53_original_acrobot_supported_residual_dev.py /tmp/report.json")
    report=score()
    path=Path(args[0]).resolve()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(f51.canonical(report)+b"\n")
    print("F53_DEV="+report["classification"]+" sha256="+report["report_sha256"])
    return report


if __name__=="__main__":
    main()
