#!/usr/bin/env python3
"""F57 original-Acrobot episode-result structure and threshold checker.

This module is intentionally NON-AUTHORIZING and NEVER RUNS AN ENVIRONMENT.
It accepts untrusted hypothetical episode traces, including synthetic test
fixtures. Numeric threshold satisfaction is not science admission, proof of
genuine original physics, or authorization to launch a fresh experiment.
The independently authenticated FORGE-native FSA must verify all original
STARTED/terminal witnesses, true first-use and actual source before any claim.
"""
import math
import re

import f57_original_acrobot_reward_admission as f57

SCHEMA = "forge.eureka.f57.untrusted-episode-metrics.v1"
UNVERIFIED = "F57_OFFLINE_EPISODE_METRICS_UNVERIFIED"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_REWARD = (-1.0, 0.0)


def _finite(value, field, *, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("F57_NONFINITE_OR_INVALID_" + field)
    out = float(value)
    if nonnegative and out < 0:
        raise ValueError("F57_NEGATIVE_" + field)
    return out


def _observation(obs):
    if (type(obs) not in (list,tuple) or len(obs)!=6 or
        any(type(v) not in (int,float) or not math.isfinite(v) for v in obs)):
        raise ValueError("F57_PUBLIC_OBS6_INVALID")
    c1,s1,c2,s2=map(float,obs[:4])
    if (abs(c1*c1+s1*s1-1.)>1e-4 or
        abs(c2*c2+s2*s2-1.)>1e-4):
        raise ValueError("F57_NONPHYSICAL_TRIG_OBSERVATION")
    return tuple(float(v) for v in obs)


def _episode(raw, seed, mode):
    """Recalculate reward, actions and terminal status from raw trace only."""
    if (type(raw) is not dict or raw.get("seed")!=seed or
        type(raw.get("seed")) is not int or raw.get("mode")!=mode or
        type(raw.get("trace")) not in (list,tuple)):
        raise ValueError("F57_SEED_MODE_OR_TRACE_MISMATCH")
    trace=raw["trace"]
    if not (1<=len(trace)<=f57.MAX_STEPS):
        raise ValueError("F57_EPISODE_STEP_BUDGET_BREACH")
    if not isinstance(raw.get("model_snapshot_sha256"),str) or not _SHA256.fullmatch(raw["model_snapshot_sha256"]):
        raise ValueError("F57_MODEL_SNAPSHOT_DIGEST_INVALID")
    decision_ns=raw.get("decision_ns")
    if type(decision_ns) is not int or decision_ns<0:
        raise ValueError("F57_INVALID_MEASURED_DECISION_NS")
    wall=_finite(raw.get("episode_wall_seconds"),"EPISODE_WALL",nonnegative=True)
    if wall==0:
        raise ValueError("F57_ZERO_EPISODE_WALL")
    previous=None
    reward_total=0.0
    actions=[0,0,0]
    deviations=0
    terminated=False
    truncated=False
    for idx,item in enumerate(trace):
        if type(item) not in (list,tuple) or len(item)!=6:
            raise ValueError("F57_ORIGINAL_ACTION_CONSEQUENCE_TUPLE_INVALID")
        old,action,reward,new,term,trunc=item
        old=_observation(old)
        new=_observation(new)
        if previous is not None and old!=previous:
            raise ValueError("F57_BROKEN_PUBLIC_TRAJECTORY_CONTINUITY")
        if type(action) is not int or action not in (0,1,2):
            raise ValueError("F57_NONPHYSICAL_ACROBOT_ACTION")
        reward=_finite(reward,"REAL_EPISODE_REWARD")
        if reward not in _ALLOWED_REWARD:
            raise ValueError("F57_ORIGINAL_REWARD_DOMAIN_INVALID")
        if type(term) is not bool or type(trunc) is not bool:
            raise ValueError("F57_TERMINATION_FLAGS_INVALID")
        # Original Farama Acrobot-v1: 0 only on terminal success, -1
        # otherwise. TimeLimit sets truncation at step 500 regardless of
        # termination, so both flags can legitimately be true at that step.
        if reward != (0.0 if term else -1.0):
            raise ValueError("F57_ORIGINAL_REWARD_SEMANTICS_INVALID")
        if trunc != (idx+1 == f57.MAX_STEPS):
            raise ValueError("F57_ORIGINAL_500_STEP_TIMELIMIT_INVALID")
        if (term or trunc) and idx!=len(trace)-1:
            raise ValueError("F57_ACTIONS_AFTER_TERMINAL")
        terminated=term
        truncated=trunc
        reward_total+=reward
        actions[action]+=1
        deviations+=int(action!=(2 if old[5]>=0 else 0))
        previous=new
    if not (terminated or truncated):
        raise ValueError("F57_EPISODE_UNTERMINATED")
    if terminated and reward_total>0:
        raise ValueError("F57_ACROBOT_REWARD_INCONSISTENT")
    return {
        "seed":seed,"mode":mode,"steps":len(trace),
        "return":reward_total,"success":terminated,"truncated":truncated,
        "actions":actions,"momentum_deviations":deviations,
        "trace_sha256":f57.digest(trace),
        "model_snapshot_sha256":raw["model_snapshot_sha256"],
        "decision_ns":decision_ns,"episode_wall_seconds":wall,
    }


def _paired_validation(warm, cold, seed, mode):
    a=_episode(warm,seed,mode)
    b=_episode(cold,seed,mode)
    for key in ("seed","mode","steps","return","success","truncated",
                "actions","momentum_deviations","trace_sha256",
                "model_snapshot_sha256"):
        if a[key]!=b[key]:
            raise ValueError("F57_ORIGINAL_EPISODE_COLD_REPLAY_MISMATCH")
    return a


def assess_untrusted_evidence(evidence):
    """Pure arithmetic on UNTRUSTED input; cannot produce scientific PASS.

    Never calls F57.start_scientific_experiment, Gymnasium, worker, queue or FSA.
    Trust in original physical episodes can only come from a separate authentic,
    independent FSA signer + monotonic ledger + original witness validation.
    """
    f57.validate_structure(f57.frozen_proposal())
    if type(evidence) is not dict:
        raise ValueError("F57_EVIDENCE_INPUT_REQUIRED")
    m=f57.frozen_proposal()
    if (evidence.get("manifest_sha256")!=f57.digest(m) or
        evidence.get("source_commit")!=m["independent_upstream_commit"] or
        evidence.get("original_acrobot_blob")!=m["original_acrobot_blob"] or
        evidence.get("fit_sha256")!=f57.OLD_FIT_SHA256 or
        evidence.get("trained_fqi_sha256")!=f57.OLD_FQI_SHA256):
        raise ValueError("F57_UNTRUSTED_EVIDENCE_SOURCE_PINS_MISMATCH")
    arms=evidence.get("arms")
    cost=evidence.get("preparation_seconds_by_arm")
    if (type(arms) is not dict or set(arms)!=set(f57.ARMS) or
        type(cost) is not dict or set(cost)!=set(f57.ARMS)):
        raise ValueError("F57_MISSING_OR_EXTRA_POLICY_OR_COST")
    cost={key:_finite(cost[key], "PREPARATION_COST",nonnegative=True)
          for key in f57.ARMS}
    if cost["momentum-rule"]!=0.0:
        raise ValueError("F57_MOMENTUM_NO_TRAINING_COST")
    summaries={}
    exact_cold=0
    for arm in f57.ARMS:
        data=arms[arm]
        if type(data) is not dict or set(data)!={"transfer","retention","cold_transfer","cold_retention"}:
            raise ValueError("F57_MISSING_OR_EXTRA_EPISODE_COHORT")
        transfer=[]
        retention=[]
        for kind, seeds,mode,result in (
            ("transfer",f57.PROPOSED_TRANSFER,"nips",transfer),
            ("retention",f57.PROPOSED_RETENTION,"book",retention)):
            live=data[kind]
            cold=data["cold_"+kind]
            if type(live) not in (list,tuple) or type(cold) not in (list,tuple) or len(live)!=len(seeds) or len(cold)!=len(seeds):
                raise ValueError("F57_INCOMPLETE_OR_DUPLICATE_ORIGINAL_SEEDS")
            for k,seed in enumerate(seeds):
                result.append(_paired_validation(live[k],cold[k],seed,mode))
                exact_cold+=1
        steps=sum(e["steps"] for e in (*transfer,*retention))
        decisions=sum(e["decision_ns"] for e in (*transfer,*retention))
        wall=sum(e["episode_wall_seconds"] for e in (*transfer,*retention))
        if steps<=0 or wall<=0:
            raise ValueError("F57_MISSING_WHOLE_PROCESS_COST")
        summaries[arm]={
            "transfer_episodes":transfer,
            "retention_episodes":retention,
            "transfer_mean_return":sum(x["return"] for x in transfer)/len(transfer),
            "retention_mean_return":sum(x["return"] for x in retention)/len(retention),
            "transfer_successes":sum(x["success"] for x in transfer),
            "retention_successes":sum(x["success"] for x in retention),
            "transfer_seeds_with_deviation":sum(x["momentum_deviations"]>0 for x in transfer),
            "original_environment_steps":steps,
            "decision_ns_per_action":decisions/steps,
            "episode_wall_seconds":wall,
            "preparation_seconds":cost[arm],
            "whole_process_seconds":cost[arm]+wall,
        }
    if exact_cold!=168:
        raise ValueError("F57_COLD_REPLAY_INCOMPLETE")
    strongest=max(f57.CONVENTIONAL,key=lambda a:summaries[a]["transfer_mean_return"])
    candidate=summaries["quantile-supported"]
    baseline=summaries[strongest]
    neg=summaries["rotated-credit"]
    strongest_retention=max(summaries[k]["retention_mean_return"] for k in f57.CONVENTIONAL)
    paired=sum(a["return"]>b["return"] for a,b in zip(
        candidate["transfer_episodes"],baseline["transfer_episodes"]))
    gain=candidate["transfer_mean_return"]-baseline["transfer_mean_return"]
    neg_gain=candidate["transfer_mean_return"]-neg["transfer_mean_return"]
    retention=candidate["retention_mean_return"]-strongest_retention
    success_gain=candidate["transfer_successes"]-baseline["transfer_successes"]
    checks={
        "mean_transfer_gain":gain>=f57.MIN_MEAN_GAIN,
        "paired_strict_seed_wins":paired>=f57.MIN_PAIRED_WINS,
        "transfer_success_nondegraded":success_gain>=0,
        "rotated_negative_margin":neg_gain>=f57.MIN_NEGATIVE_GAIN,
        "retention_margin":retention>=f57.MIN_RETENTION_MARGIN,
        "transfer_override_coverage":candidate["transfer_seeds_with_deviation"]>=f57.MIN_DEVIATING_TRANSFER_SEEDS,
        "cold_replay":exact_cold==168,
    }
    reported={name:{
        key:value for key,value in summary.items()
        if key not in ("transfer_episodes","retention_episodes")}
        for name,summary in summaries.items()}
    ratio=(candidate["whole_process_seconds"]/baseline["whole_process_seconds"])
    decision_ratio=(candidate["decision_ns_per_action"]/baseline["decision_ns_per_action"]
                    if baseline["decision_ns_per_action"]>0 else None)
    out={
        "schema":SCHEMA,"disposition":UNVERIFIED,
        "manifest_sha256":evidence["manifest_sha256"],
        "nominal_cold_episodes_checked":exact_cold,
        "nominal_scored_episodes_parsed":168,
        "strongest_conventional":strongest,
        "strongest_book_retention_mean":strongest_retention,
        "paired_strict_transfer_wins":paired,
        "transfer_return_gain":gain,
        "transfer_success_gain":success_gain,
        "rotated_credit_transfer_margin":neg_gain,
        "book_retention_margin":retention,
        "candidate_to_baseline_whole_process_cost_ratio":ratio,
        "candidate_to_baseline_decision_ns_per_action_ratio":decision_ratio,
        "frozen_development_checks":checks,
        "untrusted_data_meets_numeric_thresholds":all(checks.values()),
        "arm_metrics":reported,
        "external_original_physics_authenticated":False,
        "fsa_signed_start_witness_verified":False,
        "global_first_use_ledger_verified":False,
        "fsa_monotonic_anchor_readback_verified":False,
        "scientific_accepted":False,
        "eligible_to_run_or_promote":False,
    }
    out["report_sha256"]=f57.digest(out)
    return out
