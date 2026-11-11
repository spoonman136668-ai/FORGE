#!/usr/bin/env python3
"""F55 original Farama Acrobot leave-one-FIT-root-out action-only DEV.

Frozen ancestor c30ec17eaad922cce35c901d7c3b62616444d2a0.
Reuses F51's *already consumed* FIT actions; no new evaluated episodes,
scored seeds, heldout physics or scientific first-use.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import f51_original_acrobot_transfer_dev as f51
import f53_original_acrobot_supported_residual_dev as f53
import f54_original_acrobot_fit_quantile_action_audit as f54

SCHEMA = "forge.eureka.f55.original-acrobot-oof-fit-action.v1"
PROTOCOL_COMMIT = "c30ec17eaad922cce35c901d7c3b62616444d2a0"
ORIGINAL_FIT_SHA256 = "63d31930006ec2f465e4becd989c1a0b922e15a0842ef991fe424074d436a31a"
ROOTS = (21011,21017,21019,21023,21029,21031)
ARMS = f54.ARMS
MIN_TOTAL_OVERRIDES = 90
MIN_ACTIVE_ROOTS = 4


def source_and_root_groups():
    """Independently source-verify before reconstructing only consumed FIT."""
    source = f53.check_source()
    records, counts, episodes, collection = f51.collect_fit()
    if (len(records) != 8974 or counts != [3604,1824,3546] or
        len(episodes) != 48 or f51.digest(records) != ORIGINAL_FIT_SHA256 or
        tuple(f51.FIT) != ROOTS or len(set(ROOTS)) != 6):
        raise RuntimeError("F55_ORIGINAL_FIT_SOURCE_CUSTODY_DRIFT")
    grouped = {root: [] for root in ROOTS}
    episode_meta = {root: [] for root in ROOTS}
    cursor = 0
    for idx, ep in enumerate(episodes):
        expected_root = ROOTS[idx//8]
        expected_episode = idx % 8
        root, number, steps = ep["seed"], ep["episode"], ep["steps"]
        if (type(root) is not int or type(number) is not int or
            type(steps) is not int or root != expected_root or
            number != expected_episode or steps < 1 or steps > 500):
            raise RuntimeError("F55_ORIGINAL_FIT_EPISODE_ORDER_DRIFT")
        segment = records[cursor:cursor+steps]
        if (len(segment) != steps or f51.digest(segment) != ep["trace_sha256"] or
            any(type(row[1]) is not int or row[1] not in (0,1,2) for row in segment)):
            raise RuntimeError("F55_ORIGINAL_EPISODE_TRACE_OR_ACTION_DRIFT")
        grouped[root].extend(segment)
        episode_meta[root].append({"episode":number,"steps":steps,
                                    "trace_sha256":ep["trace_sha256"]})
        cursor += steps
    if (cursor != len(records) or sum(len(x) for x in grouped.values()) != 8974 or
        any(len(episode_meta[x]) != 8 or not grouped[x] for x in ROOTS)):
        raise RuntimeError("F55_ROOT_PARTITION_NOT_EXACT")
    return source,grouped,episode_meta,collection


def calibrate_only_five_roots(records):
    """Fit and select every numeric parameter without the excluded root."""
    t0 = time.perf_counter()
    if not records:
        raise RuntimeError("F55_EMPTY_TRAIN_PARTITION")
    theta = f51.fit_fqi(records)
    if theta.shape != (3,15) or not np.all(np.isfinite(theta)):
        raise RuntimeError("F55_FQI_NONFINITE")
    features = np.vstack([f51.features(row[0]) for row in records])
    action = np.asarray([row[1] for row in records],dtype=np.int64)
    counts = [int(np.count_nonzero(action==a)) for a in range(3)]
    if min(counts)<1 or sum(counts)!=len(records):
        raise RuntimeError("F55_UNSUPPORTED_TRAINING_ACTION")
    inverses = []
    support_thresholds = []
    for a in range(3):
        X = features[action==a]
        inv = np.linalg.inv(X.T@X+f51.RIDGE*np.eye(f51.DIMS))
        leverage = np.einsum("ij,jk,ik->i",X,inv,X)
        threshold = float(np.quantile(leverage,.90))
        if (not np.all(np.isfinite(inv)) or
            not np.all(np.isfinite(leverage)) or
            not math.isfinite(threshold) or threshold<=0):
            raise RuntimeError("F55_INVALID_TRAINING_ACTION_SUPPORT")
        inverses.append(inv)
        support_thresholds.append(threshold)
    gaps = []
    for row in records:
        obs = row[0]
        h = f51.energy_rule(obs)
        q = theta@f51.features(obs)
        g = int(np.argmax(q))
        if not np.all(np.isfinite(q)):
            raise RuntimeError("F55_NONFINITE_TRAINING_ACTION_VALUE")
        if g != h:
            gap = float(q[g]-q[h])
            if not math.isfinite(gap) or gap<=0:
                raise RuntimeError("F55_INVALID_TRAINING_Q_GAP")
            gaps.append(gap)
    if not gaps:
        raise RuntimeError("F55_NO_FINITE_TRAINING_GAP")
    margin = float(np.quantile(gaps,.75))
    if not math.isfinite(margin) or margin<=0:
        raise RuntimeError("F55_INVALID_TRAINING_MARGIN")
    inv = np.stack(inverses)
    limits = np.asarray(support_thresholds,dtype=np.float64)
    calibration = {
        "theta":theta,"inverses":inv,"limits":limits,"margin":margin,
        "source_fit_sha256":f51.digest(records),
        "theta_sha256":f51.digest(theta.tolist()),
        "support_sha256":f51.digest({"inverses":inv.tolist(),
                                     "thresholds":limits.tolist()}),
        "train_action_counts":counts,"positive_train_gaps":len(gaps),
        "calibration_seconds":time.perf_counter()-t0
    }
    return calibration


def action_only_pass(excluded,calibration):
    """In-memory action predictions on original observations, no environment."""
    theta = calibration["theta"]
    inv = calibration["inverses"]
    limits = calibration["limits"]
    margin = calibration["margin"]
    policies = {name:f54.Policy(name,theta,inv,limits,margin) for name in ARMS}
    stats = {name:{"deviations":0,"behavior_matches":0,"actions":[0,0,0]}
             for name in ARMS}
    traces = {name:[] for name in ARMS}
    support = {"margin_eligible":0,"both_supported":0,
               "only_g_supported":0,"only_h_supported":0,"neither_supported":0}
    t0 = time.perf_counter()
    for row in excluded:
        obs, actual = row[0],row[1]
        h = f51.energy_rule(obs)
        phi = f51.features(obs)
        q = theta@phi
        g = int(np.argmax(q))
        if not np.all(np.isfinite(q)):
            raise RuntimeError("F55_NONFINITE_HOLDOUT_Q")
        if g != h and float(q[g]-q[h])>=margin:
            support["margin_eligible"]+=1
            lg = float(phi@inv[g]@phi)
            lh = float(phi@inv[h]@phi)
            if not math.isfinite(lg) or not math.isfinite(lh):
                raise RuntimeError("F55_NONFINITE_HOLDOUT_SUPPORT")
            gs = lg<=float(limits[g])
            hs = lh<=float(limits[h])
            key = ("both_supported" if gs and hs else
                   "only_g_supported" if gs else
                   "only_h_supported" if hs else "neither_supported")
            support[key]+=1
        for name,p in policies.items():
            a = p.action(obs)
            if type(a) is not int or a not in (0,1,2):
                raise RuntimeError("F55_NONPHYSICAL_ACTION")
            s = stats[name]
            s["deviations"]+=int(a!=h)
            s["behavior_matches"]+=int(a==actual)
            s["actions"][a]+=1
            traces[name].append(a)
    n=len(excluded)
    if (any(p.n!=n for p in policies.values()) or
        any(sum(s["actions"])!=n for s in stats.values()) or
        stats["momentum-rule"]["deviations"]!=0 or
        stats["quantile-supported"]["deviations"]!=support["both_supported"] or
        stats["quantile-margin-only"]["deviations"]!=support["margin_eligible"] or
        sum(support.values())-support["margin_eligible"]!=support["margin_eligible"]):
        raise RuntimeError("F55_FROZEN_ACTION_OR_SUPPORT_ACCOUNTING_FAILURE")
    return {"arms":stats,"support":support,
            "action_trace_sha256":{a:f51.digest(traces[a]) for a in ARMS},
            "inference_wall_seconds":time.perf_counter()-t0}


def score():
    source,groups,episode_meta,collection = source_and_root_groups()
    folds=[]
    total_overrides=0
    active_roots=0
    for held in ROOTS:
        train_roots=tuple(r for r in ROOTS if r!=held)
        train=[row for root in train_roots for row in groups[root]]
        excluded=groups[held]
        if (held in train_roots or len(train_roots)!=5 or
            len(train)+len(excluded)!=8974):
            raise RuntimeError("F55_FOLD_DISJOINTNESS_FAILURE")
        fit=calibrate_only_five_roots(train)
        first=action_only_pass(excluded,fit)
        second=action_only_pass(excluded,fit)  # Fresh pure policy objects.
        for key in ("arms","support","action_trace_sha256"):
            if f51.digest(first[key])!=f51.digest(second[key]):
                raise RuntimeError("F55_ORIGINAL_FIT_ROOT_COLD_REPLAY_DRIFT")
        n=first["arms"]["quantile-supported"]["deviations"]
        total_overrides+=n
        active_roots+=int(n>0)
        folds.append({
            "excluded_root":held,"train_roots":train_roots,
            "train_steps":len(train),"excluded_steps":len(excluded),
            "excluded_episode_count":len(episode_meta[held]),
            "excluded_episode_metadata":episode_meta[held],
            "excluded_action_counts":[sum(row[1]==a for row in excluded) for a in (0,1,2)],
            "training_action_counts":fit["train_action_counts"],
            "training_source_sha256":fit["source_fit_sha256"],
            "excluded_source_sha256":f51.digest(excluded),
            "trained_model_sha256":fit["theta_sha256"],
            "support_sha256":fit["support_sha256"],
            "positive_train_gaps":fit["positive_train_gaps"],
            "training_q_margin":fit["margin"],
            "calibration_seconds":fit["calibration_seconds"],
            "action_audit":first,
            "cold_action_replay_matches":True
        })
    if (sum(f["excluded_steps"] for f in folds)!=8974 or
        sum(f["excluded_episode_count"] for f in folds)!=48 or
        len(folds)!=6 or total_overrides<0 or active_roots>6):
        raise RuntimeError("F55_COMPLETE_ORIGINAL_FIT_FOLD_COVERAGE_MISSING")
    signal = total_overrides>=MIN_TOTAL_OVERRIDES and active_roots>=MIN_ACTIVE_ROOTS
    report={
        "schema":SCHEMA,"protocol_commit":PROTOCOL_COMMIT,
        "original_source":source,"original_fit_sha256":ORIGINAL_FIT_SHA256,
        "old_fit_observations":8974,"old_fit_episodes":48,
        "original_source_collection_seconds":collection,
        "fold_count":len(folds),"folds":folds,
        "supported_oof_action_overrides":total_overrides,
        "active_excluded_roots":active_roots,
        "required_min_oof_overrides":MIN_TOTAL_OVERRIDES,
        "required_min_active_roots":MIN_ACTIVE_ROOTS,
        "classification":("F55_FIT_OOF_ACTIVATION_UNVERIFIED" if signal
                          else "F55_FIT_OOF_NO_GO"),
        "cold_replay_verified_folds":len(folds),
        "science_accepted":False,"original_first_use_consumed":False,
        "external_transfer_evaluations":0,
        "new_retention_evaluations":0,"physically_scored_excluded_episodes":0,
        "real_value_gain_proven":False,"unfamiliar_physics_transfer_proven":False
    }
    report["report_sha256"]=f51.digest(report)
    return report


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:
        raise ValueError("F55_USAGE: python f55_original_acrobot_oof_fit_action.py report.json")
    report=score()
    path=Path(args[0]).resolve()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(f51.canonical(report)+b"\n")
    print("F55_OOF_CLASSIFICATION="+report["classification"])
    print("F55_OOF_SUMMARY="+json.dumps({
        "supported_oof_action_overrides":report["supported_oof_action_overrides"],
        "active_excluded_roots":report["active_excluded_roots"],
        "excluded_root_overrides":[{
            "root":x["excluded_root"],
            "steps":x["excluded_steps"],
            "threshold":x["training_q_margin"],
            "supported":x["action_audit"]["arms"]["quantile-supported"]["deviations"],
            "margin_only":x["action_audit"]["arms"]["quantile-margin-only"]["deviations"]}
            for x in report["folds"]],
        "report_sha256":report["report_sha256"]},sort_keys=True))
    return report


if __name__=="__main__":
    main()
