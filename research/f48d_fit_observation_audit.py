#!/usr/bin/env python3
"""F48D: FIT-only observational likelihood and false-reset audit.

No heldout transfer or retention source environment is instantiated. The F48
model and protocol are imported unchanged; actual source noise/latent FIT mode
are used ONLY to evaluate measurement calibration, NEVER as policy inputs.
"""
import math
from pathlib import Path
import sys

import f48_regime_reset_credit_dev as f48

SCHEMA = "forge.eureka.f48d.fit-only-observation-calibration.v1"
SOURCE_BLOB = "2e2c9665fb6557a682cf788d678f6818e51fd995"
PROTOCOL_BLOB = "84a4db4dfd8bc84f68f3a7c43cec005ecce0af90"
CUTOFF = 0.12
EXPECTED_COVERAGE = (288, 288, 192)
FIT = tuple(f48.FIT)


def audit_transition(seed, episode, t, record, policy):
    """Read-only audit of one recorded physical step; no new environment call."""
    if type(seed) is not int or seed not in FIT:
        raise ValueError("F48D_NON_FIT_SEED_REFUSED")
    if type(episode) is not int or not 0 <= episode < 12:
        raise ValueError("F48D_NON_FIT_EPISODE_REFUSED")
    if type(t) is not int or not 0 <= t < f48.DURATION:
        raise ValueError("F48D_NON_FIT_STEP_REFUSED")
    if len(record) != 7:
        raise ValueError("F48D_INVALID_SOURCE_TRANSCRIPT")
    before, pending, requested, after, witness, reward, done = record
    if pending not in f48.ACTIONS or requested not in f48.ACTIONS:
        raise ValueError("F48D_NON_PUBLIC_ACTION")
    source_mode = seed % 6  # EVALUATOR-ONLY ground truth; never passed to policy.
    physical_effect = f48.EFFECTS[source_mode][pending] if pending != 2 else 0
    true_noise, flip = f48.exogenous(seed, episode, t)
    observed_noise = before ^ after ^ physical_effect
    if observed_noise != true_noise:
        raise ValueError("F48D_SOURCE_DELAY_OR_NOISE_MISMATCH")
    expected_witness = (int(source_mode >= 3) ^ int(flip)) if pending == 2 else -1
    if witness != expected_witness:
        raise ValueError("F48D_SOURCE_WITNESS_MISMATCH")

    effect = before ^ after
    correctly_credited = f48.likelihood(
        source_mode, pending, effect, witness, sensor_applied=pending == 2)
    wrongly_credited = f48.likelihood(
        source_mode, requested, effect, witness, sensor_applied=pending == 2)
    if not 0 <= correctly_credited <= 1 or not 0 <= wrongly_credited <= 1:
        raise ValueError("F48D_INVALID_LIKELIHOOD_RANGE")
    if correctly_credited <= 0:
        raise ValueError("F48D_TRUE_PHYSICAL_CAUSE_IMPOSSIBLE_UNDER_SOURCE_MODEL")

    # This is the unchanged actual F48 model's predictive probability before
    # seeing the public observation. No source-mode or noise information enters it.
    q = sum(
        policy.working[m] * f48.likelihood(
            m, pending, effect, witness, sensor_applied=pending == 2)
        for m in range(6)
    )
    expected_reset = (pending != 2 and q < CUTOFF)
    before_resets = policy.resets
    before_updates = policy.stable_updates
    policy.observe(before, pending, requested, after, witness)
    reset_count = policy.resets - before_resets
    stable_updates = policy.stable_updates - before_updates
    if reset_count not in (0, 1) or bool(reset_count) != bool(expected_reset):
        raise ValueError("F48D_ACTUAL_POLICY_RESET_NOT_EQUAL_TO_FROZEN_CUTOFF")
    if stable_updates not in (0, 1):
        raise ValueError("F48D_POLICY_STABLE_UPDATE_DRIFT")
    return {
        "noise": bool(true_noise), "queued_sensor": pending == 2,
        "witness_flip": bool(flip) if pending == 2 else False,
        "correct_credit_nll": -math.log(max(correctly_credited, 1e-12)),
        "wrong_credit_nll": -math.log(max(wrongly_credited, 1e-12)),
        "correct_more_likely": correctly_credited > wrongly_credited,
        "wrong_more_likely": correctly_credited < wrongly_credited,
        "equal_likelihood": correctly_credited == wrongly_credited,
        "q": q, "surprise": expected_reset,
        "reset": reset_count, "stable_update": stable_updates,
        "reset_with_noise": bool(reset_count and true_noise),
        "reset_without_noise": bool(reset_count and not true_noise),
    }


def audit_fit():
    if (FIT != (4104, 4105, 4106, 4107, 4110, 4111, 4112, 4113)
        or len(set(FIT)) != 8
        or set(FIT).intersection((*f48.TRANSFER, *f48.RETENTION, *f48.FORBIDDEN))):
        raise ValueError("F48D_FROZEN_FIT_ONLY_SEEDS_DRIFT")
    worlds, coverage = f48.fit_data()
    if (tuple(coverage) != EXPECTED_COVERAGE
        or len(worlds) != 8
        or any(len(world) != 12 for world in worlds)):
        raise ValueError("F48D_FIT_TRANSCRIPT_DRIFT")
    fit = f48.fit_shared(worlds)
    if (fit["training_transitions"] != 768 or fit["training_worlds"] != 8
        or len(fit["prior"]) != 6
        or any(p <= 0 for p in fit["prior"])):
        raise ValueError("F48D_FITTED_SOURCE_MODEL_DRIFT")
    if f48.canonical(fit) != f48.canonical(f48.fit_shared(worlds)):
        raise ValueError("F48D_FIT_CHECKPOINT_NOT_REPRODUCIBLE")
    metrics = {
        "source_steps": 0, "physical_noise_events": 0, "sensor_steps": 0,
        "witness_flip_events": 0, "reset_count_in_fixed_worlds": 0,
        "reset_with_noise": 0, "reset_without_noise": 0,
        "stable_updates": 0, "correct_credit_higher": 0,
        "wrong_credit_higher": 0, "same_credit_likelihood": 0,
        "sum_correct_nll": 0.0, "sum_wrong_nll": 0.0,
        "predictive_brier_sum": 0.0, "surprise_flag_count": 0,
    }
    details = []
    for seed, episodes in zip(FIT, worlds):
        if seed not in FIT:
            raise ValueError("F48D_UNAUTHORIZED_WORLD_LOOP")
        for ep, records in enumerate(episodes):
            policy = f48.Policy("stable-working-reset", fit)
            episode_reset = 0
            episode_noise = 0
            episode_false_noise = 0
            episode_false_quiet = 0
            for t, record in enumerate(records):
                d = audit_transition(seed, ep, t, record, policy)
                metrics["source_steps"] += 1
                metrics["physical_noise_events"] += int(d["noise"])
                metrics["sensor_steps"] += int(d["queued_sensor"])
                metrics["witness_flip_events"] += int(d["witness_flip"])
                metrics["reset_count_in_fixed_worlds"] += d["reset"]
                metrics["reset_with_noise"] += int(d["reset_with_noise"])
                metrics["reset_without_noise"] += int(d["reset_without_noise"])
                metrics["stable_updates"] += d["stable_update"]
                metrics["correct_credit_higher"] += int(d["correct_more_likely"])
                metrics["wrong_credit_higher"] += int(d["wrong_more_likely"])
                metrics["same_credit_likelihood"] += int(d["equal_likelihood"])
                metrics["sum_correct_nll"] += d["correct_credit_nll"]
                metrics["sum_wrong_nll"] += d["wrong_credit_nll"]
                metrics["predictive_brier_sum"] += (int(d["noise"]) - 0.2)**2
                metrics["surprise_flag_count"] += int(d["surprise"])
                episode_reset += d["reset"]
                episode_noise += int(d["noise"])
                episode_false_noise += int(d["reset_with_noise"])
                episode_false_quiet += int(d["reset_without_noise"])
            if policy.observations != f48.DURATION:
                raise ValueError("F48D_UNCHANGED_POLICY_REPLAY_NOT_COMPLETE")
            details.append({
                "seed": seed, "episode": ep,
                "noise_events": episode_noise, "false_resets": episode_reset,
                "resets_on_noise": episode_false_noise,
                "resets_without_noise": episode_false_quiet,
                "stable_updates": policy.stable_updates,
                "policy_snapshot_sha256": f48.digest(policy.snapshot()),
            })
    n = metrics["source_steps"]
    if (n != 768 or len(details) != 96 or
        metrics["correct_credit_higher"]+metrics["wrong_credit_higher"]
        +metrics["same_credit_likelihood"] != n or
        metrics["reset_count_in_fixed_worlds"] != metrics["surprise_flag_count"] or
        metrics["reset_count_in_fixed_worlds"] !=
        metrics["reset_with_noise"]+metrics["reset_without_noise"] or
        metrics["sensor_steps"] <= 0):
        raise ValueError("F48D_INCOMPLETE_CUSTODY_OR_CUTOFF_PARITY")
    report = {
        "schema": SCHEMA,
        "purpose": "training-only noise calibration, delayed-credit and false-reset audit",
        "synthetic_only": True, "fit_only": True,
        "heldout_scoring_performed": False,
        "science_f48_classification_preserved": "F48_DEV_NO_GO",
        "scientific_accepted": False, "first_use_consumed": False,
        "owner_eligible": False, "general_rsi_proven": False,
        "frozen_source_blob": SOURCE_BLOB,
        "frozen_protocol_blob": PROTOCOL_BLOB,
        "source_fit_seeds": FIT,
        "source_fit_transcript_sha256": f48.digest(worlds),
        "source_fitted_model_sha256": f48.digest(fit),
        "fit_action_coverage": coverage,
        "source_record_count": n,
        "stationary_policy_replays": len(details),
        "source_noise_rate": metrics["physical_noise_events"]/n,
        "source_witness_flip_rate": (metrics["witness_flip_events"]
                                    /metrics["sensor_steps"]),
        "noise_event_brier": metrics["predictive_brier_sum"]/n,
        "mean_nll_correct_delayed_credit": metrics["sum_correct_nll"]/n,
        "mean_nll_wrong_current_action_credit": metrics["sum_wrong_nll"]/n,
        "single_hypothesis_corruption_likelihood": 0.2/3,
        "frozen_surprise_cutoff": CUTOFF,
        "ordinary_corruption_below_surprise_cutoff": 0.2/3 < CUTOFF,
        "counters": metrics,
        "stationary_episode_diagnostics": details,
        "diagnosis": ("F48D_FIT_FALSE_RESET_DETECTED"
                      if metrics["reset_count_in_fixed_worlds"] > 0
                      else "F48D_FIT_FALSE_RESET_NOT_OBSERVED"),
    }
    report["report_sha256"] = f48.digest(report)
    return report


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise ValueError("F48D_USAGE: python f48d_fit_observation_audit.py /tmp/audit.json")
    report = audit_fit()
    out = Path(argv[0]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(f48.canonical(report)+b"\n")
    print("F48D_FIT_OBSERVATION_DIAGNOSIS="+report["diagnosis"])
    print("F48D_NO_EVAL_SEEDS=PASS FIT_N="+str(report["source_record_count"])
          +" REPLAYS="+str(report["stationary_policy_replays"]))
    for key in ("source_noise_rate","source_witness_flip_rate",
                "mean_nll_correct_delayed_credit",
                "mean_nll_wrong_current_action_credit"):
        print("F48D_"+key.upper()+"="+str(report[key]))
    print("F48D_FALSE_RESETS="+str(report["counters"]["reset_count_in_fixed_worlds"])
          +" ON_NOISE="+str(report["counters"]["reset_with_noise"])
          +" WITHOUT_NOISE="+str(report["counters"]["reset_without_noise"]))
    print("F48D_REPORT_SHA256="+report["report_sha256"])
    return report


if __name__ == "__main__":
    main()
