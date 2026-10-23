"""Advisory-only, matched-context turnaround comparison for ELANG screens.

Input timings and hashes are untrusted observations. This module neither starts
experiments nor authenticates source runs, immutable provider custody or science.
"""
from __future__ import annotations

import math

import screen_contract as identity

SCHEMA = "forge.language-screen.turnaround-observation-only.v1"
STAGES = ("intake", "focused_tests", "comparator", "evidence_archive",
          "full_regression")
OBSERVATION_FIELDS = frozenset({
    "schema", "candidate_key", "environment_sha256", "suite_sha256",
    "workload_sha256", "evidence_sha256", "stages_seconds",
    "independent_evaluation_seconds", "total_cpu_seconds",
    "peak_memory_bytes", "artifact_bytes", "energy_joules",
    "task_quality", "hard_false_positives", "human_interventions",
    "regression_test_count",
})


def _number(value, name, *, positive=False):
    identity.need(type(value) in (float, int) and math.isfinite(value),
                  "TURNAROUND_INVALID_" + name.upper())
    identity.need(value > 0 if positive else value >= 0,
                  "TURNAROUND_INVALID_" + name.upper())
    return float(value)


def _integer(value, name, *, positive=False):
    identity.need(type(value) is int and
                  (value > 0 if positive else value >= 0),
                  "TURNAROUND_INVALID_" + name.upper())
    return value


def _observation(contract, candidate_key, observed):
    identity.need(type(observed) is dict and
                  set(observed) == OBSERVATION_FIELDS,
                  "TURNAROUND_OBSERVATION_FIELDS")
    identity.need(observed["schema"] == SCHEMA and
                  observed["candidate_key"] == candidate_key and
                  observed["environment_sha256"] == contract["environment_sha256"]
                  and observed["suite_sha256"] == contract["focused_suite_sha256"],
                  "TURNAROUND_CONTEXT_DRIFT")
    for name in ("workload_sha256", "evidence_sha256"):
        identity.need(identity._hex(observed[name]),
                      "TURNAROUND_BAD_" + name.upper())
    identity.need(observed["independent_evaluation_seconds"] is None,
                  "TURNAROUND_FIRST_USE_NOT_AUTHORIZED")
    stages = observed["stages_seconds"]
    identity.need(type(stages) is dict and set(stages) == set(STAGES),
                  "TURNAROUND_STAGES_INCOMPLETE")
    for name in STAGES:
        _number(stages[name], name, positive=(name == "full_regression"))
    _number(observed["total_cpu_seconds"], "total_cpu_seconds")
    _integer(observed["peak_memory_bytes"], "peak_memory_bytes")
    _integer(observed["artifact_bytes"], "artifact_bytes")
    if observed["energy_joules"] is not None:
        _number(observed["energy_joules"], "energy_joules")
    quality = _number(observed["task_quality"], "task_quality")
    identity.need(quality <= 1.0, "TURNAROUND_QUALITY_OUT_OF_RANGE")
    identity.need(_integer(observed["hard_false_positives"],
                           "hard_false_positives") == 0,
                  "TURNAROUND_HARD_FALSE_POSITIVE")
    _integer(observed["human_interventions"], "human_interventions")
    _integer(observed["regression_test_count"], "regression_test_count",
             positive=True)
    identity.canonical(observed)
    return observed


def compare_turnaround(contract, baseline, candidate):
    """Compute *unverified* matched-source deltas, never authorize cache reuse.

    Completion of mandatory timed stages is not evidence that their tests
    passed. A certified baseline, real provider/custody authentication, and
    independently verified regression outcomes remain external obligations.
    """
    key = identity.candidate_key(contract)
    a = _observation(contract, key, baseline)
    b = _observation(contract, key, candidate)
    identity.need(a["workload_sha256"] == b["workload_sha256"],
                  "TURNAROUND_WORKLOAD_DRIFT")
    identity.need(a["evidence_sha256"] != b["evidence_sha256"],
                  "TURNAROUND_REPLAYED_OBSERVATION")
    old_seconds = sum(float(a["stages_seconds"][name]) for name in STAGES)
    new_seconds = sum(float(b["stages_seconds"][name]) for name in STAGES)
    identity.need(math.isfinite(old_seconds) and math.isfinite(new_seconds)
                  and old_seconds > 0 and new_seconds > 0,
                  "TURNAROUND_TOTAL_INVALID")
    quality_nonregression = b["task_quality"] >= a["task_quality"]
    reduced = new_seconds < old_seconds
    return {
        "schema": "forge.language-screen.turnaround-comparison-advisory.v1",
        "candidate_key": key,
        "workload_sha256": a["workload_sha256"],
        "baseline_seconds": old_seconds,
        "candidate_seconds": new_seconds,
        "observed_saving_seconds": old_seconds - new_seconds,
        "observed_saving_fraction": (old_seconds - new_seconds) / old_seconds,
        "observed_quality_delta": b["task_quality"] - a["task_quality"],
        "observed_cpu_delta_seconds": (b["total_cpu_seconds"]
                                       - a["total_cpu_seconds"]),
        "observed_peak_memory_delta_bytes": (b["peak_memory_bytes"]
                                              - a["peak_memory_bytes"]),
        "observed_artifact_delta_bytes": (b["artifact_bytes"]
                                          - a["artifact_bytes"]),
        "energy_comparable": (a["energy_joules"] is not None and
                              b["energy_joules"] is not None),
        "observed_energy_delta_joules": (
            b["energy_joules"] - a["energy_joules"]
            if a["energy_joules"] is not None and
               b["energy_joules"] is not None else None),
        "observed_human_intervention_delta": (
            b["human_interventions"] - a["human_interventions"]),
        "apparent_development_gain": reduced and quality_nonregression,
        "independent_evaluation_performed": False,
        "provider_custody_independently_verified": False,
        "full_regression_independently_verified": False,
        "cached_qualification_authorized": False,
        "qualified_turnaround_gain_verified": False,
        "scientific_breakthrough_claimed": False,
        "scientific_first_use": False,
        "disposition": "UNTRUSTED_TIMINGS_REQUIRE_EXTERNAL_QUALIFICATION",
    }
