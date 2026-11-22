#!/usr/bin/env python3
"""F52: training-only diagnosis of value surprise versus a causal regime change.

Uses *only* immutable F51 original external Acrobot FIT trajectories and the
unchanged trained F51 model/policy. All previous F51 DEV holdouts are fenced.
"""
import math
from pathlib import Path
import sys
import time

import numpy as np
import f51_original_acrobot_transfer_dev as f51

SCHEMA="forge.eureka.f52.acrobot-fit-td-contradiction-specificity.v1"
F51_SOURCE_BLOB="d3114ac66589e6b9f623318da721449090cfd54a"
F52_PROTOCOL_BLOB="73564b62728d0df0d87955d83a8836aa08e53d15"
F51_ORIGINAL_FIT_SHA256="63d31930006ec2f465e4becd989c1a0b922e15a0842ef991fe424074d436a31a"
EXPECTED_FIT_COUNTS=(3604,1824,3546)
EXPECTED_FIT_TRANSITIONS=8974
FIT_THRESHOLD=8.0


def frozen_q_error(row,theta):
    """Same exact online F51 TD formula, on frozen fitted-Q parameters only."""
    obs,action,reward,next_obs,terminated,truncated=row
    if type(action) is not int or action not in (0,1,2):
        raise ValueError("F52_INVALID_PUBLIC_PHYSICAL_ACTION")
    x=f51.features(obs)
    y=f51.features(next_obs)
    value=float(theta[action]@x)
    backup=0. if terminated or truncated else f51.GAMMA*float(np.max(theta@y))
    error=float(reward)+backup-value
    if not math.isfinite(error):
        raise ValueError("F52_NONFINITE_PUBLIC_TD_ERROR")
    return error


def audit_training_only():
    source=f51.check_original()
    if (tuple(f51.FIT)!=(21011,21017,21019,21023,21029,21031)
        or len(f51.TRANSFER)!=12 or len(f51.RETENTION)!=8
        or set(f51.FIT)&set((*f51.TRANSFER,*f51.RETENTION,*f51.FORBIDDEN))
        or set(f51.TRANSFER)&set(f51.RETENTION)
        or set(f51.FORBIDDEN)&set((*f51.FIT,*f51.TRANSFER,*f51.RETENTION))):
        raise RuntimeError("F52_TRAINING_ONLY_COHORT_OR_FIRST_USE_DRIFT")
    if (source["upstream_commit"]!=f51.ORIGINAL_COMMIT or
        source["acrobot_git_blob"]!=f51.ORIGINAL_FILE_BLOB):
        raise RuntimeError("F52_THIRD_PARTY_SOURCE_CUSTODY_DRIFT")

    records,coverage,episodes,real_fit_seconds=f51.collect_fit()
    if (len(records)!=EXPECTED_FIT_TRANSITIONS or
        tuple(coverage)!=EXPECTED_FIT_COUNTS or
        len(episodes)!=48 or
        sum(ep["steps"] for ep in episodes)!=len(records)):
        raise RuntimeError("F52_ORIGINAL_ACROBOT_TRAINING_COUNTS_DRIFT")
    record_sha=f51.digest(records)
    if record_sha!=F51_ORIGINAL_FIT_SHA256:
        raise RuntimeError("F52_ORIGINAL_F51_PUBLIC_FIT_TRANSCRIPT_HASH_DRIFT")

    fitting_started=time.perf_counter()
    theta=f51.fit_fqi(records)
    fitting_seconds=time.perf_counter()-fitting_started
    model=np.asarray(theta,dtype=np.float64)
    if model.shape!=(3,15) or not np.all(np.isfinite(model)):
        raise RuntimeError("F52_FROZEN_FQI_TRAINED_CHECKPOINT_INVALID")
    model_sha=f51.digest(model.tolist())

    analysis_started=time.perf_counter()
    errors=[]
    high_by_action=[0,0,0]
    count_by_action=[0,0,0]
    momentum_agree=0
    total_terminal_high=0
    total_nonterminal_high=0
    for record in records:
        err=frozen_q_error(record,model)
        old,act,reward,next_obs,terminated,truncated=record
        errors.append(abs(err))
        count_by_action[act]+=1
        flagged=abs(err)>FIT_THRESHOLD
        high_by_action[act]+=int(flagged)
        total_terminal_high+=int(flagged and (terminated or truncated))
        total_nonterminal_high+=int(flagged and not (terminated or truncated))
        momentum_agree+=int(
            int(np.argmax(model@f51.features(old)))==f51.energy_rule(old))
    if count_by_action!=coverage:
        raise RuntimeError("F52_FROZEN_ORIGINAL_FIT_ACTION_CREDIT_DRIFT")

    episode_summaries=[]
    ptr=0
    total_candidate_triggers=0
    total_candidate_adapt_steps=0
    total_candidate_high_streak_episodes=0
    total_public_observations={"contradiction-gated-td":0,"always-td":0,
                               "wrong-credit-td":0}
    for ep_info in episodes:
        n=ep_info["steps"]
        rows=records[ptr:ptr+n]
        ptr+=n
        if len(rows)!=n or f51.digest(rows)!=ep_info["trace_sha256"]:
            raise RuntimeError("F52_ORIGINAL_FIT_EPISODE_CUSTODY_DRIFT")
        policies={kind:f51.Policy(kind,model) for kind in total_public_observations}
        for before,action,reward,after,term,trunc in rows:
            for kind,p in policies.items():
                p.observe(before,action,float(reward),after,bool(term or trunc))
        for kind,p in policies.items():
            if p.physical_observations!=n or not np.all(np.isfinite(p.theta)):
                raise RuntimeError("F52_OFFPOLICY_PUBLIC_FIT_REPLAY_INVALID")
            total_public_observations[kind]+=p.physical_observations
        cand=policies["contradiction-gated-td"]
        total_candidate_triggers+=cand.trigger_events
        total_candidate_adapt_steps+=cand.adapt_steps
        total_candidate_high_streak_episodes+=int(cand.trigger_events>0)
        episode_summaries.append({
            "root_seed":ep_info["seed"],"episode":ep_info["episode"],
            "source_steps":n,
            "original_behavior_return":sum(float(r[2]) for r in rows),
            "real_source_episode_trace_sha256":ep_info["trace_sha256"],
            "f51_candidate_offpolicy_trigger_events":cand.trigger_events,
            "f51_candidate_offpolicy_adapt_steps":cand.adapt_steps,
            "candidate_policy_snapshot_sha256":f51.digest(cand.snapshot()),
            "always_td_snapshot_sha256":f51.digest(policies["always-td"].snapshot()),
            "wrong_credit_snapshot_sha256":f51.digest(policies["wrong-credit-td"].snapshot())
        })
    if ptr!=len(records) or len(episode_summaries)!=48 or any(
        n!=len(records) for n in total_public_observations.values()
    ):
        raise RuntimeError("F52_STATIONARY_TRAINING_EPISODE_REPLAY_INCOMPLETE")
    if total_nonterminal_high+total_terminal_high!=sum(high_by_action):
        raise RuntimeError("F52_FROZEN_VALUE_ERROR_PARTITION_INCONSISTENT")
    if total_candidate_triggers!=sum(ep["f51_candidate_offpolicy_trigger_events"]
                                     for ep in episode_summaries):
        raise RuntimeError("F52_FROZEN_POLICY_TRIGGER_CUSTODY_DRIFT")

    arr=np.asarray(errors,dtype=np.float64)
    if arr.size!=len(records) or not np.all(np.isfinite(arr)):
        raise RuntimeError("F52_TD_ERROR_REPORT_NONFINITE")
    report={
        "schema":SCHEMA,"fit_only":True,"original_external_environment":True,
        "heldout_scoring_performed":False,"first_use_consumed":False,
        "scientific_accepted":False,"owner_eligible":False,
        "general_rsi_proven":False,
        "original_f51_science_unchanged":"F51_DEV_NO_GO",
        "frozen_f51_source_blob":F51_SOURCE_BLOB,
        "preregistered_f52_protocol_blob":F52_PROTOCOL_BLOB,
        "upstream":source,
        "original_f51_public_fit_sha256":record_sha,
        "original_f51_trained_fqi_model_sha256":model_sha,
        "fit_seed_roots":tuple(f51.FIT),
        "real_source_fit_episodes":len(episodes),
        "real_source_fit_steps":len(records),
        "real_source_fit_action_counts":coverage,
        "f51_fixed_td_threshold":FIT_THRESHOLD,
        "f51_discount":f51.GAMMA,
        "f51_fqi_passes":f51.FQI_PASSES,
        "mean_absolute_frozen_base_td_error":float(arr.mean()),
        "median_absolute_frozen_base_td_error":float(np.quantile(arr,.5)),
        "p90_absolute_frozen_base_td_error":float(np.quantile(arr,.90)),
        "p99_absolute_frozen_base_td_error":float(np.quantile(arr,.99)),
        "max_absolute_frozen_base_td_error":float(arr.max()),
        "frozen_base_high_td_events":int(sum(high_by_action)),
        "frozen_base_high_td_nonterminal":total_nonterminal_high,
        "frozen_base_high_td_terminal":total_terminal_high,
        "frozen_base_high_td_rate":int(sum(high_by_action))/len(records),
        "frozen_base_high_td_by_actual_action":high_by_action,
        "greedy_fqi_agrees_with_momentum_count":momentum_agree,
        "greedy_fqi_agrees_with_momentum_rate":momentum_agree/len(records),
        "offpolicy_original_f51_candidate_trigger_events":total_candidate_triggers,
        "offpolicy_original_f51_candidate_adapt_steps":total_candidate_adapt_steps,
        "fixed_book_episodes_with_candidate_trigger":total_candidate_high_streak_episodes,
        "offpolicy_public_observation_counts":total_public_observations,
        "episode_diagnostics":episode_summaries,
        "original_source_fit_collection_seconds":real_fit_seconds,
        "frozen_fqi_fit_seconds":fitting_seconds,
        "fit_audit_seconds":time.perf_counter()-analysis_started,
        "diagnosis":(
            "F52_FIT_TD_TRIGGER_WITHOUT_REGIME_CHANGE_OBSERVED"
            if total_candidate_triggers>0
            else "F52_FIT_TD_TRIGGER_NOT_OBSERVED")
    }
    report["report_sha256"]=f51.digest(report)
    return report


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:
        raise ValueError("F52_USAGE: python f52_original_acrobot_fit_value_error_audit.py /tmp/report.json")
    report=audit_training_only()
    dest=Path(args[0]).resolve()
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(f51.canonical(report)+b"\n")
    print("F52_ORIGINAL_ACROBOT_FIT_DIAGNOSIS="+report["diagnosis"])
    print("F52_ORIGINAL_SOURCE_TRAINING_SHA256="+report["original_f51_public_fit_sha256"])
    print("F52_TRAINED_FQI_SHA256="+report["original_f51_trained_fqi_model_sha256"])
    print("F52_TD_ERROR_HIGH_TOTAL="+str(report["frozen_base_high_td_events"])
          +" NONTERMINAL="+str(report["frozen_base_high_td_nonterminal"])
          +" TERMINAL="+str(report["frozen_base_high_td_terminal"]))
    print("F52_FIXED_BOOK_CANDIDATE_TRIGGERS="+str(report["offpolicy_original_f51_candidate_trigger_events"])
          +" EPISODES="+str(report["fixed_book_episodes_with_candidate_trigger"])
          +" ADAPT_STEPS="+str(report["offpolicy_original_f51_candidate_adapt_steps"]))
    print("F52_FROZEN_FQI_MOMENTUM_AGREEMENT="+str(report["greedy_fqi_agrees_with_momentum_rate"]))
    print("F52_REPORT_SHA256="+report["report_sha256"])
    return report


if __name__=="__main__":
    main()
