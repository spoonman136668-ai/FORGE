#!/usr/bin/env python3
"""F58 real-original FIT-only action/consequence rule identification.

Recollects only already-consumed six book-FIT roots; zero new scored seeds,
zero unfamiliar-world resets, zero FSA execution or promotion.
Prospective protocol ancestor ec22d962f145f2f55262368b3a5f7381f4806c50.
"""
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np
import f51_original_acrobot_transfer_dev as f51
import f53_original_acrobot_supported_residual_dev as f53

SCHEMA = "forge.eureka.f58.fit-torque-rule-dev.v1"
PROTOCOL_COMMIT = "ec22d962f145f2f55262368b3a5f7381f4806c50"
PROTOCOL_BLOB = "a8396cab6180e0aaefbbc799d1f7b8b770d3a372"
FIT_SHA256 = "63d31930006ec2f465e4becd989c1a0b922e15a0842ef991fe424074d436a31a"
ROOTS = (21011,21017,21019,21023,21029,21031)
FIT_ACTIONS = (3604,1824,3546)
RIDGE = .05
SHUFFLE_OFFSET = 581000
ARMS = ("factorized-torque","action-specific-ridge","action-blind-ridge","shuffled-torque")
SIGNAL = "F58_FIT_ACTION_RULE_SIGNAL_UNVERIFIED"
NO_GO = "F58_FIT_ACTION_RULE_NO_GO"
RUNTIME_BLOCKED = "F58_RUNTIME_BLOCKED"
V1 = 4*math.pi
V2 = 9*math.pi


def design(phi, actions, arm):
    """Only public obs features plus the observed torque, never next-state data."""
    phi = np.asarray(phi,dtype=np.float64)
    a = np.asarray(actions)
    if (phi.ndim != 2 or phi.shape[1] != 15 or a.ndim != 1 or
        a.shape[0] != phi.shape[0] or phi.shape[0] < 1 or
        not np.all(np.isfinite(phi)) or
        not np.issubdtype(a.dtype, np.integer) or
        not np.all((a>=0)&(a<=2))):
        raise ValueError("F58_PUBLIC_FEATURE_OR_ACTION_INVALID")
    if arm == "action-blind-ridge":
        out = phi.copy()
    elif arm in ("factorized-torque","shuffled-torque"):
        t = a.astype(np.float64)-1.
        out = np.concatenate((phi,phi*t[:,None]),axis=1)
    elif arm == "action-specific-ridge":
        out = np.zeros((len(a),45),dtype=np.float64)
        for k in range(3):
            indices=np.where(a==k)[0]
            out[indices,k*15:(k+1)*15]=phi[indices]
    else:
        raise ValueError("F58_UNDECLARED_ESTIMATOR")
    return out


def targets(rows):
    """Genuine two-velocity public action consequences, not reward proxies."""
    if not rows:
        raise ValueError("F58_NO_HISTORICAL_RECORDS")
    phi=np.vstack([f51.features(r[0]) for r in rows])
    actions=np.fromiter((r[1] for r in rows),dtype=np.int64,count=len(rows))
    y=np.asarray([[(float(r[3][4])-float(r[0][4]))/V1,
                   (float(r[3][5])-float(r[0][5]))/V2]
                  for r in rows],dtype=np.float64)
    if (y.shape!=(len(rows),2) or not np.all(np.isfinite(y)) or
        np.any(np.abs(y)>2.00001)):
        raise ValueError("F58_ORIGINAL_PHYSICAL_TARGET_INVALID")
    return phi,actions,y


def ridge_fit(x, y):
    """One standard closed-form multioutput ridge solve, no tuning."""
    x=np.asarray(x,dtype=np.float64)
    y=np.asarray(y,dtype=np.float64)
    if (x.ndim!=2 or y.shape!=(len(x),2) or x.shape[1] not in (15,30,45) or
        len(x)<x.shape[1] or not np.all(np.isfinite(x)) or
        not np.all(np.isfinite(y))):
        raise ValueError("F58_INVALID_RIDGE_TRAINING_INPUT")
    gram=x.T@x+RIDGE*np.eye(x.shape[1],dtype=np.float64)
    weights=np.linalg.solve(gram,x.T@y)
    if weights.shape!=(x.shape[1],2) or not np.all(np.isfinite(weights)):
        raise RuntimeError("F58_NONFINITE_FITTED_DYNAMICS")
    return weights


def historical_root_groups():
    """Freshly *recollect historical FIT only* with original source custody."""
    source=f53.check_source()
    records,counts,episodes,collection_seconds=f51.collect_fit()
    if (tuple(f51.FIT)!=ROOTS or len(records)!=8974 or
        tuple(counts)!=FIT_ACTIONS or len(episodes)!=48 or
        f51.digest(records)!=FIT_SHA256):
        raise RuntimeError("F58_PREVIOUSLY_CONSUMED_FIT_CUSTODY_MISMATCH")
    offset=0
    groups={r:[] for r in ROOTS}
    per_root_episodes={r:0 for r in ROOTS}
    for ep in episodes:
        root=ep["seed"]
        steps=ep["steps"]
        chunk=records[offset:offset+steps]
        if (root not in groups or steps<1 or steps>500 or
            len(chunk)!=steps or ep["episode"]!=per_root_episodes[root] or
            f51.digest(chunk)!=ep["trace_sha256"]):
            raise RuntimeError("F58_HISTORICAL_EPISODE_SHA_OR_ORDER_DRIFT")
        groups[root].extend(chunk)
        per_root_episodes[root]+=1
        offset+=steps
    if (offset!=8974 or any(per_root_episodes[r]!=8 or not groups[r] for r in ROOTS)
        or sum(len(g) for g in groups.values())!=8974):
        raise RuntimeError("F58_HISTORICAL_ROOT_PARTITION_DRIFT")
    return source,groups,collection_seconds


def compare_arm(train, test, arm, held):
    """Pure logged-physics ridge fit and evaluation; no env calls."""
    train_phi,train_a,train_y=train
    test_phi,test_a,test_y=test
    labels=(np.random.default_rng(SHUFFLE_OFFSET+held).permutation(train_a)
            if arm=="shuffled-torque" else train_a)
    t0=time.perf_counter()
    x=design(train_phi,labels,arm)
    theta=ridge_fit(x,train_y)
    fit_seconds=time.perf_counter()-t0
    t1=time.perf_counter()
    estimates=design(test_phi,test_a,arm)@theta
    prediction_seconds=time.perf_counter()-t1
    err=estimates-test_y
    mse=float(np.mean(err*err))
    if not math.isfinite(mse) or mse<=0:
        raise RuntimeError("F58_MISSING_POSITIVE_HISTORICAL_PREDICTION_ERROR")
    effect_norm=(float(np.linalg.norm(theta[15:,:]))
                 if arm in ("factorized-torque","shuffled-torque") else None)
    if effect_norm is not None and not math.isfinite(effect_norm):
        raise RuntimeError("F58_NONFINITE_TORQUE_RULE")
    return {
        "mse":mse,"params":int(theta.size),"input_features":int(x.shape[1]),
        "model_sha256":f51.digest(theta.tolist()),
        "prediction_sha256":f51.digest(estimates.tolist()),
        "effect_norm":effect_norm,
        "fit_seconds":fit_seconds,"inference_seconds":prediction_seconds,
    }


def audit_fold(groups,held):
    train_rows=[r for root in ROOTS if root!=held for r in groups[root]]
    test_rows=groups[held]
    if (len(train_rows)+len(test_rows)!=8974 or
        len(train_rows)<45 or len(test_rows)<1):
        raise RuntimeError("F58_ROOT_HOLDOUT_LEAK_OR_MISSING")
    tr=targets(train_rows)
    te=targets(test_rows)
    if min(np.bincount(tr[1],minlength=3))==0 or min(np.bincount(te[1],minlength=3))==0:
        raise RuntimeError("F58_ACTION_RANDOMIZATION_SUPPORT_MISSING")
    first={name:compare_arm(tr,te,name,held) for name in ARMS}
    cold={name:compare_arm(tr,te,name,held) for name in ARMS}
    for name in ARMS:
        # Timings are nondeterministic measurements; models and predictions must match.
        for key in ("mse","params","input_features","model_sha256",
                    "prediction_sha256","effect_norm"):
            if first[name][key]!=cold[name][key]:
                raise RuntimeError("F58_COLD_MODEL_OR_PREDICTION_NONDETERMINISM")
    return {
        "excluded_root":held,
        "training_roots":[x for x in ROOTS if x!=held],
        "training_rows":len(train_rows),"heldout_rows":len(test_rows),
        "heldout_action_counts":np.bincount(te[1],minlength=3).tolist(),
        "training_sha256":f51.digest(train_rows),
        "heldout_sha256":f51.digest(test_rows),
        "arms":first,"cold_model_prediction_exact":True,
    }


def decide(root_means,folds):
    if set(root_means)!=set(ARMS) or len(folds)!=6:
        raise RuntimeError("F58_RESULT_COMPLETENESS_INVALID")
    candidate=root_means["factorized-torque"]
    flat=root_means["action-specific-ridge"]
    blind=root_means["action-blind-ridge"]
    shuffled=root_means["shuffled-torque"]
    wins=sum(f["arms"]["factorized-torque"]["mse"] <
             f["arms"]["action-specific-ridge"]["mse"] for f in folds)
    all_pass=(candidate<=.98*flat and candidate<=.95*blind and
              wins>=5 and shuffled>=1.05*candidate and
              all(f["arms"]["factorized-torque"]["effect_norm"]>1e-8
                  for f in folds))
    return (SIGNAL if all_pass else NO_GO), {
        "candidate_to_action_specific_mse_ratio":candidate/flat,
        "candidate_to_action_blind_mse_ratio":candidate/blind,
        "shuffled_to_candidate_mse_ratio":shuffled/candidate,
        "candidate_beats_action_specific_roots":wins,
        "nonzero_action_effect_root_count":sum(
            f["arms"]["factorized-torque"]["effect_norm"]>1e-8 for f in folds),
        "thresholds":{"candidate_vs_strong_conventional_max_ratio":.98,
                      "candidate_vs_blind_max_ratio":.95,
                      "minimum_conventional_root_wins":5,
                      "shuffled_negative_min_ratio":1.05,
                      "minimum_effect_norm":1e-8}
    }


def score():
    source,groups,collection_seconds=historical_root_groups()
    fold_results=[audit_fold(groups,root) for root in ROOTS]
    means={arm:float(np.mean([f["arms"][arm]["mse"] for f in fold_results]))
           for arm in ARMS}
    if (len(fold_results)!=6 or any(not math.isfinite(v) or v<=0
                                    for v in means.values())):
        raise RuntimeError("F58_INVALID_FIT_ROOT_MSE")
    disposition,checks=decide(means,fold_results)
    out={
        "schema":SCHEMA,"protocol_commit":PROTOCOL_COMMIT,
        "protocol_blob":PROTOCOL_BLOB,"disposition":disposition,
        "source":source,
        "original_fit_sha256":FIT_SHA256,"historical_fit_episodes":48,
        "historical_fit_transitions":8974,"historical_action_counts":FIT_ACTIONS,
        "historical_roots":ROOTS,"original_collection_seconds":collection_seconds,
        "folds":fold_results,"cold_replay_exact_roots":6,
        "root_equal_normalized_velocity_increment_mse":means,
        "frozen_falsifier":checks,
        "new_scored_episodes":0,"fresh_original_firstuse":False,
        "f57_frozen_trial_unchanged":True,
        "unfamiliar_physics_transfer_proven":False,
        "episodic_policy_return_proven":False,
        "causal_counterfactual_at_same_state_proven":False,
        "scientific_accepted":False,
        "model_promoted":False
    }
    out["report_sha256"]=f51.digest(out)
    return out


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if len(args)!=1:
        raise ValueError("F58_USAGE: python f58_original_acrobot_fit_torque_rule.py REPORT.json")
    report=score()
    path=Path(args[0]).resolve()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(f51.canonical(report)+b"\n")
    m=report["root_equal_normalized_velocity_increment_mse"]
    print("F58_HISTORICAL_FIT_RESULT="+report["disposition"])
    print("F58_HISTORICAL_FIT_SUMMARY="+json.dumps({
        "mse":m,"comparators":report["frozen_falsifier"],
        "report_sha256":report["report_sha256"],
        "historical_records":8974,"fresh_scored_episodes":0},
        sort_keys=True))
    return report


if __name__=="__main__":
    main()
