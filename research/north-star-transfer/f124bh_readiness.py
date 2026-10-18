"""F124-BH read-only, nonconsuming source-birth and full-budget readiness.

No registered U/R tasks are constructed, no scientific comparison is run.
Synthetic negative fixtures exercise proposed source operators only. External
independent source-birth authentication and whole-task parity are NOT claimed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROTO = HERE / "f124bh-frozen-protocol.json"
FREEZE_COMMIT = "c906adaca213327ab4fdf2b1deaeae54088827a8"
U_COMMIT = "c62b33a830f61a99f9d28cb88ffec04ef32b0d9a"
R_COMMIT = "fa623739ebf1f2352d5636acd0b39614a38b688d"
BLOBS = {
    "f124bh-frozen-protocol.json": "38d489da4b1469896a64ac3e744e9ad9521aebdd",
    "f124bh_u_family.py": "6fe6b5bbece936bb0dfca97c0a8b454918067a19",
    "f124bh_r_family.py": "02997a32ffb3fec60073b3b725cfd0aecae4b1f8",
    "20261018-mass-learned-kernel.py": "bf81ed56cc0daa2c413ad7d9c698969f92befe3d",
    "20261018-mass-research-precode.json": "2359c97b14a34d28881895713235f7fe9cee8a73",
}
REGISTERED = {"U": range(902000, 902128), "R": range(903000, 903128)}
FIXTURES = {"U": -940, "R": -939}
COMPONENTS = (
    "metatrain_cpu_ns", "fit_cpu_ns", "representation_cpu_ns",
    "graph_scoring_cpu_ns", "inference_cpu_ns", "task_overhead_cpu_ns",
    "train_peak_rss_bytes", "task_peak_rss_bytes",
    "public_payload_bytes", "model_weight_bytes",
    "cognition_bytes", "transient_bytes", "resident_overhead_bytes",
)


def need(ok, tag):
    if not ok:
        raise ValueError("F124BH_" + tag)


def run_git(*args):
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                       text=True, check=False)
    need(p.returncode == 0, "GIT_" + args[0].upper())
    return p.stdout.strip()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, HERE / path)
    need(spec is not None and spec.loader is not None, "MODULE_LOAD")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def verify_chronology():
    freeze = json.loads(PROTO.read_text(encoding="utf-8"))
    need(freeze["schema"] ==
         "forge.mass.f124bh.frozen-source-birth-and-transfer-readiness.v1",
         "FROZEN_SCHEMA")
    need(freeze["parent_source_commit"] ==
         "aca5b279e0e0985560e3a13f0c892d4a30ae08e6", "PARENT")
    for name, expected in BLOBS.items():
        need(run_git("hash-object", str(HERE / name)) == expected,
             "IMMUTABLE_BLOB_" + name)
    for earlier, later in (
        ("aca5b279e0e0985560e3a13f0c892d4a30ae08e6", FREEZE_COMMIT),
        (FREEZE_COMMIT, U_COMMIT), (U_COMMIT, R_COMMIT),
        (R_COMMIT, run_git("rev-parse", "HEAD")),
    ):
        p = subprocess.run(["git", "merge-base", "--is-ancestor", earlier, later],
                           cwd=ROOT, capture_output=True)
        need(p.returncode == 0, "CHRONOLOGY")
    for commit, name, expected_existence in (
        (FREEZE_COMMIT, "f124bh-frozen-protocol.json", True),
        (FREEZE_COMMIT, "f124bh_u_family.py", False),
        (FREEZE_COMMIT, "f124bh_r_family.py", False),
        (U_COMMIT, "f124bh_u_family.py", True),
        (U_COMMIT, "f124bh_r_family.py", False),
        (R_COMMIT, "f124bh_u_family.py", True),
        (R_COMMIT, "f124bh_r_family.py", True),
    ):
        path = "research/north-star-transfer/" + name
        p = subprocess.run(["git", "cat-file", "-e", commit + ":" + path],
                           cwd=ROOT, capture_output=True)
        need((p.returncode == 0) is expected_existence, "BIRTH_ORDER")
    cohorts = freeze["identity_ranges"]
    need(cohorts["UNSEEN_U"] == [902000, 902127]
         and cohorts["INDEPENDENT_REPLICATION_R"] == [903000, 903127],
         "COHORT_IDENTITY")
    all_ranges = [
        range(x[0], x[1] + 1) for name, x in cohorts.items()
        if name != "NEGATIVE_ENGINEERING_FIXTURES"
    ]
    need(len(set().union(*(set(r) for r in all_ranges))) ==
         sum(len(r) for r in all_ranges), "COHORT_OVERLAP")
    need(freeze["authority"]["scientific_first_use"] is False
         and freeze["authority"]["registered_cohort_generated"] is False,
         "PREMATURE_AUTHORITY")
    return freeze


def synthetic_operator_audit():
    u = module("f124bh_u_source", "f124bh_u_family.py")
    r = module("f124bh_r_source", "f124bh_r_family.py")
    need(u.FAMILY != r.FAMILY and u.PROSPECTIVE != r.PROSPECTIVE
         and u.FIXTURE_ID != r.FIXTURE_ID, "GENERATOR_COLLISION")
    result = {}
    for tag, m in (("U", u), ("R", r)):
        private_recipe = m._recipe(FIXTURES[tag])
        # Adversarial fixed synthetic domain points; not prospective tasks.
        points = tuple(range(0, 65536, 257)) + (0, 1, 65534, 65535)
        enc = [m.forward(x, private_recipe) for x in points]
        need(len(set(enc)) == len(points), "SYNTHETIC_NONBIJECTION_" + tag)
        need(all(m.inverse(m.forward(x, private_recipe), private_recipe) == x
                 for x in points), "SYNTHETIC_INVERSE_" + tag)
        public, private = m.fixture(FIXTURES[tag])
        need(len(public["FIT"]) == 40 and len(public["CHECK"]) == 8
             and len(private["noise_positions_private"]) == 6,
             "FIXTURE_SHAPE_" + tag)
        need(public["source_family_sent_to_model"] is False,
             "SOURCE_ORACLE_LEAK_" + tag)
        for case in (REGISTERED[tag].start, REGISTERED[tag].stop - 1,
                     0, -1, 902000, 903000):
            try:
                m.fixture(case)
            except ValueError:
                pass
            else:
                raise ValueError("F124BH_REGISTERED_CASE_CONSTRUCTED_" + tag)
        d = m.source_birth_descriptor()
        need(d["registered_source_generated"] == 0
             and d["scientific_first_use"] is False
             and d["independent_provenance_witnessed"] is False,
             "FALSE_WITNESS_" + tag)
        result[tag] = {"algorithm": d["source_grammar"],
                       "source_blob": BLOBS["f124bh_" + tag.lower() + "_family.py"],
                       "birth_commit": U_COMMIT if tag == "U" else R_COMMIT,
                       "synthetic_fixed_point_count": len(points),
                       "registered_cases_generated": 0,
                       "witnessed_externally": False}
    return result


def full_budget(candidate, baseline, *, eligible_symbolic=None, denominator=128):
    """Validate the *complete* matched lifecycle receipts; never infer missing.

    All CPU components include on-task preparation and overhead; training
    amortization is reported alongside raw TRAIN cost. RSS is whole-process
    peak, with explicit logical payload floors, not Python heap alone.
    """
    need(denominator == 128, "AMORTIZATION_DENOMINATOR")
    arms = {"candidate": candidate, "baseline": baseline}
    if eligible_symbolic is not None:
        arms["eligible_symbolic"] = eligible_symbolic
    totals = {}
    for label, ledger in arms.items():
        need(set(COMPONENTS).issubset(ledger), "MISSING_COMPONENT_" + label)
        for k in COMPONENTS:
            v = ledger[k]
            need(type(v) is int and v >= 0, "UNKNOWN_RESOURCE_" + label + "_" + k)
        train = ledger["metatrain_cpu_ns"]
        on_task = sum(ledger[k] for k in (
            "fit_cpu_ns", "representation_cpu_ns", "graph_scoring_cpu_ns",
            "inference_cpu_ns", "task_overhead_cpu_ns"))
        lower = sum(ledger[k] for k in (
            "public_payload_bytes", "model_weight_bytes", "cognition_bytes",
            "transient_bytes", "resident_overhead_bytes"))
        whole_peak = max(ledger["train_peak_rss_bytes"],
                         ledger["task_peak_rss_bytes"])
        need(ledger["task_peak_rss_bytes"] >= lower,
             "PEAK_BELOW_KNOWN_PAYLOAD_" + label)
        totals[label] = {"train_cpu_raw_ns": train,
                         "task_cpu_ns": on_task,
                         "amortized_cpu_ns_ceiling": (train + denominator - 1)
                         // denominator + on_task,
                         "whole_process_peak_rss_bytes": whole_peak,
                         "known_task_payload_lower_bound_bytes": lower}
    candidate_cost = totals["candidate"]
    for label in totals:
        if label == "candidate":
            continue
        comp = totals[label]
        need(candidate_cost["amortized_cpu_ns_ceiling"] <=
             comp["amortized_cpu_ns_ceiling"]
             and candidate_cost["whole_process_peak_rss_bytes"] <=
             comp["whole_process_peak_rss_bytes"],
             "RESOURCE_PARITY_FAIL_" + label)
    return {"schema": "mass.f124bh.full-resource-matched-ledger.v1",
            "mechanically_resource_eligible": True,
            "totals": totals,
            "scientific_source_authenticated": False,
            "transfer_scientifically_accepted": False}


def negative_fixture_measurements():
    """Actual limited Python CPU/heap measurements; NOT whole RSS or parity."""
    kernel = module("f124bh_sourceblind_kernel",
                    "20261018-mass-learned-kernel.py")
    output = {}
    for tag, module_name, fixture_id in (
        ("U", "f124bh_u_family.py", -940),
        ("R", "f124bh_r_family.py", -939),
    ):
        m = module("mass_bh_fixture_" + tag, module_name)
        public, _ = m.fixture(fixture_id)
        tracemalloc.start()
        before = time.process_time_ns()
        weights, observed = kernel.fit_public(public["FIT"], public["CHECK"])
        cost = time.process_time_ns() - before
        peak_py = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        need(observed["public_forward_evaluations"] == 2608
             and observed["independent_OOD_result"] is False,
             "UNAUTHORIZED_TRANSFER")
        output[tag] = {
            "fixture": fixture_id, "fit_CPU_ns": cost,
            "Python_heap_peak_bytes_only": peak_py,
            "parameter_bits_only": len(weights) * 8,
            "FIT_bit_errors": observed["public_FIT_bit_errors"],
            "CHECK_bit_errors": observed["public_CHECK_bit_errors"],
            "whole_task_RSS_not_qualified": True,
            "TRAIN_amortization_not_qualified": True,
            "score_and_representation_cost_not_qualified": True,
        }
    return output


def readiness():
    freeze = verify_chronology()
    births = synthetic_operator_audit()
    observed = negative_fixture_measurements()
    return {
        "schema": "mass.f124bh.nonconsuming-authentic-transfer-readiness.v1",
        "exact_head": run_git("rev-parse", "HEAD"),
        "frozen_protocol_blob": BLOBS["f124bh-frozen-protocol.json"],
        "protocol_birth_commit": FREEZE_COMMIT,
        "source_born_order": [U_COMMIT, R_COMMIT],
        "separately_committed_source_algorithms": births,
        "prospective_cohort_ranges": {
            "U": [902000, 902127], "R": [903000, 903127]},
        "preregistered_gain_per_cohort": freeze["scientific_acceptance"][
            "paired_gain_minimum_correct_per_128_each_cohort"],
        "matched_control_source_blob": freeze["frozen_identities"][
            "AZ_unchanged_control_blob"],
        "negative_fixture_measurements_only": observed,
        "resource_accounting_fields": list(COMPONENTS),
        "resource_parity_qualified": False,
        "independent_external_birth_witness": False,
        "novelty_authenticated_by_independent_issuer": False,
        "registered_cohort_generated": 0,
        "registered_cohort_consumed": 0,
        "protected_first_use": False,
        "scientific_acceptance": False,
        "optimizer_policy_training": False,
        "optimizer_promotion": False,
        "accepted_ref_mutations": 0,
        "dispatch_authorized": False,
        "next_required_evidence": [
            "Independent provider-witnessed source birth and provenance disjointness",
            "Freeze exact model and strongest control against independently originated U/R",
            "Whole task calibrated CPU and peak RSS for each eligible arm plus 192 TRAIN costs",
            "Scientific admission for prospective first-use; no cohort emitted in BH",
        ],
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    data = readiness()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, sort_keys=True, indent=2) + "\n").encode()
    args.output.write_bytes(raw)
    print("F124BH_SOURCE_ORDER=PASS")
    print("F124BH_SYNTHETIC_ONLY=PASS")
    print("F124BH_REGISTERED_COHORTS_GENERATED=0")
    print("F124BH_EXTERNAL_INDEPENDENT_WITNESS=false")
    print("F124BH_TOTAL_RESOURCE_PARITY=false")
    print("F124BH_SCIENCE_ACCEPTED=false")
    print("F124BH_READY_RECEIPT_SHA256=" + hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    main()
