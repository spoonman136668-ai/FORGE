#!/usr/bin/env python3
"""F56 frozen FIT-only original Acrobot logged-randomization one-step audit.

Protocol-first ancestor 53a2bc7a196a618a6c31eea11e25700326b2ee2c.
Never evaluates fresh physical policy episodes, original DEV cohorts, or science.
Only the six already-consumed, genuine F51 book-FIT root trajectories are read.
"""
import itertools
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import f51_original_acrobot_transfer_dev as f51
import f54_original_acrobot_fit_quantile_action_audit as f54
import f55_original_acrobot_oof_fit_action as f55

SCHEMA = "forge.eureka.f56.original-acrobot-fit-ips-one-step.v1"
PROTOCOL_COMMIT = "53a2bc7a196a618a6c31eea11e25700326b2ee2c"
ROOTS = f55.ROOTS
ARMS = f54.ARMS
CONTROL = ("momentum-rule","frozen-fqi")
NEGATIVE = "rotated-credit"
MIN_GAIN = 0.001
MIN_POSITIVE_ROOTS = 5
MIN_ESS = 100.0
BOOTSTRAP_COUNT = 6**6


def behavior_probs(obs):
    """Exact known F51 .60 uniform + .40 momentum(.10 action1 if low speed)."""
    if len(obs) != 6 or not all(math.isfinite(float(x)) for x in obs):
        raise ValueError("F56_INVALID_PUBLIC_OBSERVATION")
    h = f51.energy_rule(obs)
    if h not in (0,2):
        raise RuntimeError("F56_INVALID_HEURISTIC_ACTION")
    p = np.asarray([.20,.20,.20],dtype=np.float64)
    if abs(float(obs[5])) < .2:
        p[h] += .36
        p[1] += .04
    else:
        p[h] += .40
    if (not np.all(np.isfinite(p)) or np.min(p)<.20-1e-12 or
        np.max(p)>.60+1e-12 or not np.isclose(np.sum(p),1.,atol=1e-12)):
        raise RuntimeError("F56_BEHAVIOR_SOURCE_PROPENSITY_INVALID")
    return p


def tip_height(obs):
    """Acrobot physical tip height from *public* cos/sin observations."""
    if len(obs)!=6 or not all(math.isfinite(float(x)) for x in obs):
        raise ValueError("F56_PUBLIC_HEIGHT_OBSERVATION_REQUIRED")
    c1,s1,c2,s2 = map(float,obs[:4])
    if (abs(c1*c1+s1*s1-1.)>1e-4 or
        abs(c2*c2+s2*s2-1.)>1e-4):
        raise ValueError("F56_NONPHYSICAL_ORIGINAL_ACROBOT_OBSERVATION")
    h = -c1-(c1*c2-s1*s2)
    if not math.isfinite(h) or h<-2.00001 or h>2.00001:
        raise ValueError("F56_NONFINITE_OR_NONPHYSICAL_HEIGHT")
    return h


def recorded_one_step(row):
    if len(row)!=6 or type(row[1]) is not int or row[1] not in (0,1,2):
        raise ValueError("F56_ORIGINAL_RECORD_INVALID")
    old, actual, rew, new, term, trunc = row
    if (type(term) is not bool or type(trunc) is not bool or
        not math.isfinite(float(rew))):
        raise ValueError("F56_ORIGINAL_RECORD_TERMINATION_DRIFT")
    delta=tip_height(new)-tip_height(old)
    if not math.isfinite(delta) or abs(delta)>4.00002:
        raise RuntimeError("F56_INVALID_PHYSICAL_HEIGHT_CHANGE")
    probs=behavior_probs(old)
    propensity=float(probs[actual])
    if propensity<.20-1e-12:
        raise RuntimeError("F56_BEHAVIOR_POSITIVITY_BROKEN")
    return delta,probs


def evaluate_logged_fold(records,calibration):
    """No original env or new action/consequence; pure IPS on logged root."""
    policies={name:f54.Policy(name,calibration["theta"],calibration["inverses"],
                              calibration["limits"],calibration["margin"])
              for name in ARMS}
    stats={name:{"matched_count":0,"weight_sum":0.,"weight_sq_sum":0.,
                 "weighted_delta_sum":0.,"deviations_vs_momentum":0,
                 "actions":[0,0,0]} for name in ARMS}
    trace={name:[] for name in ARMS}
    signed={k:[] for k in ("momentum-rule","frozen-fqi","rotated-credit")}
    t0=time.perf_counter()
    for row in records:
        delta,probs=recorded_one_step(row)
        original=int(row[1])
        h=f51.energy_rule(row[0])
        z={}
        for name,policy in policies.items():
            proposed=policy.action(row[0])
            weight=(1.0/float(probs[proposed])) if proposed==original else 0.
            contribution=weight*delta
            s=stats[name]
            s["matched_count"]+=int(weight>0)
            s["weight_sum"]+=weight
            s["weight_sq_sum"]+=weight*weight
            s["weighted_delta_sum"]+=contribution
            s["deviations_vs_momentum"]+=int(proposed!=h)
            s["actions"][proposed]+=1
            trace[name].append(proposed)
            z[name]=contribution
        for name in signed:
            signed[name].append(z["quantile-supported"]-z[name])
    n=len(records)
    for name,policy in policies.items():
        s=stats[name]
        if policy.n!=n or sum(s["actions"])!=n:
            raise RuntimeError("F56_POLICY_COUNT_OR_FOLD_DRIFT")
        if s["weight_sq_sum"]<=0 or s["weight_sum"]<=0:
            raise RuntimeError("F56_ZERO_MATCHED_LOGGED_ACTIONS")
        s["ht_ips_mean"]=s["weighted_delta_sum"]/n
        s["snips_mean_diagnostic"]=s["weighted_delta_sum"]/s["weight_sum"]
        s["ess"]=(s["weight_sum"]**2)/s["weight_sq_sum"]
        if not all(math.isfinite(s[k]) for k in
                   ("ht_ips_mean","snips_mean_diagnostic","ess")):
            raise RuntimeError("F56_NONFINITE_OFFLINE_ESTIMATE")
    contrasts={name:float(np.mean(signed[name])) for name in signed}
    if not all(math.isfinite(v) for v in contrasts.values()):
        raise RuntimeError("F56_INVALID_PAIRED_ONE_STEP_CONTRAST")
    # Include only deterministic numerical fields in cold replay comparison.
    return {"arms":stats,
            "paired_contrasts":contrasts,
            "action_trace_sha256":{k:f51.digest(trace[k]) for k in ARMS},
            "recorded_steps":n,
            "inference_wall_seconds":time.perf_counter()-t0}


def exhaustive_root_interval(diffs):
    if len(diffs)!=6 or not all(math.isfinite(float(x)) for x in diffs):
        raise RuntimeError("F56_INVALID_ROOT_BOOTSTRAP_INPUT")
    data=np.asarray(diffs,dtype=np.float64)
    indices=np.fromiter((i for draws in itertools.product(range(6),repeat=6)
                         for i in draws),dtype=np.int8,count=BOOTSTRAP_COUNT*6)
    indices=indices.reshape((BOOTSTRAP_COUNT,6))
    values=np.mean(data[indices],axis=1)
    lower,upper=np.quantile(values,[.025,.975])
    if not all(math.isfinite(float(x)) for x in (lower,upper)):
        raise RuntimeError("F56_INVALID_ROOT_BOOTSTRAP_QUANTILE")
    return {"lower_025":float(lower),"upper_975":float(upper),
            "resamples":BOOTSTRAP_COUNT}


def score():
    source,groups,episode_meta,collection_seconds=f55.source_and_root_groups()
    if tuple(groups)!=ROOTS or sum(map(len,groups.values()))!=8974:
        raise RuntimeError("F56_ORIGINAL_ROOT_CUSTODY_DRIFT")
    folds=[]
    totals={name:{"weights":0.,"weight_squares":0.,"matches":0}
            for name in ARMS}
    for held in ROOTS:
        train_roots=tuple(x for x in ROOTS if x!=held)
        train=[row for root in train_roots for row in groups[root]]
        excluded=groups[held]
        if len(train_roots)!=5 or len(train)+len(excluded)!=8974:
            raise RuntimeError("F56_FOLD_DATA_LEAKAGE")
        calibration=f55.calibrate_only_five_roots(train)
        first=evaluate_logged_fold(excluded,calibration)
        cold=evaluate_logged_fold(excluded,calibration)
        for key in ("arms","paired_contrasts","action_trace_sha256","recorded_steps"):
            if f51.digest(first[key])!=f51.digest(cold[key]):
                raise RuntimeError("F56_COLD_ROOT_ACTION_OR_IPS_REPLAY_MISMATCH")
        for name,s in first["arms"].items():
            totals[name]["weights"]+=s["weight_sum"]
            totals[name]["weight_squares"]+=s["weight_sq_sum"]
            totals[name]["matches"]+=s["matched_count"]
        folds.append({
            "excluded_root":held,"excluded_steps":len(excluded),
            "excluded_episodes":len(episode_meta[held]),"train_roots":train_roots,
            "train_steps":len(train),
            "train_original_sha256":calibration["source_fit_sha256"],
            "excluded_original_sha256":f51.digest(excluded),
            "trained_fqi_sha256":calibration["theta_sha256"],
            "support_sha256":calibration["support_sha256"],
            "calibrated_q_margin":calibration["margin"],
            "calibration_seconds":calibration["calibration_seconds"],
            "audit":first, "cold_replay_exact":True
        })
    arm_means={name:float(np.mean([f["audit"]["arms"][name]["ht_ips_mean"]
                                   for f in folds])) for name in ARMS}
    conventional=max(CONTROL,key=lambda c:(arm_means[c],1 if c=="momentum-rule" else 0))
    diffs={name:[f["audit"]["paired_contrasts"][name] for f in folds]
           for name in ("momentum-rule","frozen-fqi","rotated-credit")}
    intervals={k:exhaustive_root_interval(v) for k,v in diffs.items()}
    root_positive=sum(x>0 for x in diffs["momentum-rule"])
    if (len(folds)!=6 or sum(f["excluded_steps"] for f in folds)!=8974 or
        sum(f["excluded_episodes"] for f in folds)!=48):
        raise RuntimeError("F56_ORIGINAL_FIT_FOLD_COVERAGE_MISSING")
    root_contrast_means={k:float(np.mean(v)) for k,v in diffs.items()}
    for name in ARMS:
        w=totals[name]
        if w["weight_squares"]<=0 or w["weights"]<=0:
            raise RuntimeError("F56_TOTAL_ESS_INVALID")
        w["ess"]=(w["weights"]**2)/w["weight_squares"]
        if not math.isfinite(w["ess"]):
            raise RuntimeError("F56_NONFINITE_TOTAL_ESS")
    signal=bool(
        all(totals[k]["ess"]>=MIN_ESS for k in ("quantile-supported",*CONTROL)) and
        root_contrast_means["momentum-rule"]>=MIN_GAIN and
        root_contrast_means[conventional]>=MIN_GAIN and
        root_positive>=MIN_POSITIVE_ROOTS and
        intervals["momentum-rule"]["lower_025"]>0 and
        root_contrast_means[NEGATIVE]>0
    )
    report={
        "schema":SCHEMA,"protocol_commit":PROTOCOL_COMMIT,
        "original_source":source,"original_fit_sha256":f55.ORIGINAL_FIT_SHA256,
        "original_fit_steps":8974,"original_fit_episodes":48,
        "roots":ROOTS,"original_collection_seconds":collection_seconds,
        "folds":folds,"root_count":len(folds),
        "arm_ht_ips_root_equal_means":arm_means,
        "strongest_conventional_arm":conventional,
        "root_equal_candidate_contrasts":root_contrast_means,
        "root_cluster_exhaustive_intervals":intervals,
        "momentum_positive_root_count":root_positive,
        "aggregate_diagnostic_ess":totals,
        "frozen_thresholds":{"min_height_difference":MIN_GAIN,
                             "min_positive_roots":MIN_POSITIVE_ROOTS,
                             "min_diagnostic_ess":MIN_ESS,
                             "bootstrap_draws":BOOTSTRAP_COUNT},
        "classification":("F56_FIT_ONE_STEP_PROXY_SIGNAL_UNVERIFIED" if signal
                          else "F56_FIT_ONE_STEP_NO_GO"),
        "cold_exact_roots":len(folds),"new_original_environment_resets":0,
        "fresh_scored_episodes":0,"scientific_first_use":False,
        "scientific_accepted":False,"episodic_policy_return_proven":False,
        "unfamiliar_physics_transfer_proven":False,"autonomous_rsi_proven":False
    }
    report["report_sha256"]=f51.digest(report)
    return report


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:
        raise ValueError("F56_USAGE: python f56_original_acrobot_fit_ips_proxy.py REPORT.json")
    report=score()
    outfile=Path(args[0]).resolve()
    outfile.parent.mkdir(parents=True,exist_ok=True)
    outfile.write_bytes(f51.canonical(report)+b"\n")
    print("F56_FIT_ONE_STEP_CLASSIFICATION="+report["classification"])
    print("F56_FIT_ONE_STEP_SUMMARY="+json.dumps({
        "candidate_ips_height":report["arm_ht_ips_root_equal_means"]["quantile-supported"],
        "momentum_ips_height":report["arm_ht_ips_root_equal_means"]["momentum-rule"],
        "fqi_ips_height":report["arm_ht_ips_root_equal_means"]["frozen-fqi"],
        "strongest_conventional_arm":report["strongest_conventional_arm"],
        "candidate_vs_momentum_height":report["root_equal_candidate_contrasts"]["momentum-rule"],
        "candidate_vs_fqi_height":report["root_equal_candidate_contrasts"]["frozen-fqi"],
        "candidate_vs_rotated_height":report["root_equal_candidate_contrasts"]["rotated-credit"],
        "root_positive_count":report["momentum_positive_root_count"],
        "momentum_root_bootstrap":report["root_cluster_exhaustive_intervals"]["momentum-rule"],
        "candidate_ess":report["aggregate_diagnostic_ess"]["quantile-supported"]["ess"],
        "report_sha256":report["report_sha256"]},sort_keys=True))
    return report


if __name__=="__main__":
    main()
