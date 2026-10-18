"""F124-BI matched *partial* real CPU/RSS resource measurements.

Fresh, isolated Linux processes fit original AZ and frozen T1 on identical
public U/R negative fixtures. No registered cohorts, no 192-source TRAIN,
no graph scoring, no complete whole-task resource parity. All unmeasured
components are explicit null, never imputed as zero.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NATIVE = ROOT / "nativeevidence"
ARM_IDS = ("candidate", "AZ_baseline")
FIXTURES = ("U", "R")
REPEATS = 3
MODEL_BLOBS = {
    HERE / "20261018-mass-learned-kernel.py":
        "bf81ed56cc0daa2c413ad7d9c698969f92befe3d",
    NATIVE / "f124az_joint_public_inverse.py":
        "0122190aa3a0972ffb4a709bc6c7ffb124b311",  # replaced below
}
MODEL_BLOBS[NATIVE / "f124az_joint_public_inverse.py"] = (
    "0122190aa3a0972ffb4a709bc1bdd8179c8ba6c7"
)


def need(value, key):
    if not value:
        raise RuntimeError("F124BI_RESOURCE_" + key)


def git_hash(path):
    p = subprocess.run(["git", "hash-object", str(path)], cwd=ROOT,
                       text=True, check=True, stdout=subprocess.PIPE)
    return p.stdout.strip()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    need(spec and spec.loader, "MODULE")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def _matched_public(tag):
    need(tag in FIXTURES, "COHORT_DENIED")
    filename = "f124bh_u_family.py" if tag == "U" else "f124bh_r_family.py"
    m = module("bi_source_" + tag, HERE / filename)
    fixture_id = -940 if tag == "U" else -939
    public, private = m.fixture(fixture_id)
    observations = public["FIT"] + public["CHECK"]
    need(len(public["FIT"]) == 40 and len(public["CHECK"]) == 8
         and not public["source_family_sent_to_model"], "PUBLIC_BUDGET")
    need(private["family_private"] == m.FAMILY, "PRIVATE_SOURCE")
    public_hash = hashlib.sha256(json.dumps(observations, separators=(",", ":"))
                                 .encode()).hexdigest()
    # The public material alone, not oracle recipe or which family, is handed
    # to the candidate and baseline training.
    return observations, public_hash


def child(tag, arm):
    need(tag in FIXTURES and arm in ARM_IDS, "ARGUMENT_SCOPE")
    need(sys.platform.startswith("linux"), "LINUX_RSS_REQUIRED")
    import resource
    for path, blob in MODEL_BLOBS.items():
        need(git_hash(path) == blob, "MODEL_IDENTITY")
    tick = time.process_time_ns()
    observations, public_hash = _matched_public(tag)
    if arm == "candidate":
        m = module("bi_candidate", HERE / "20261018-mass-learned-kernel.py")
        weights, stats = m.fit_public(observations[:40], observations[40:])
        need(len(weights) == 4 and
             stats["public_forward_evaluations"] == 2608,
             "FROZEN_CANDIDATE")
        outcome = {"FIT_error_bits": stats["public_FIT_bit_errors"],
                   "CHECK_error_bits": stats["public_CHECK_bit_errors"],
                   "parameters_bits_lower": 32}
    else:
        sys.path.insert(0, str(NATIVE))
        m = module("bi_AZ", NATIVE / "f124az_joint_public_inverse.py")
        # Lossless conversion from the identical integer source pairs into
        # AZ's original 16-element bit-array input representation.
        demos = [{"input_bits": [(x >> i) & 1 for i in range(16)],
                  "output_bits": [(y >> i) & 1 for i in range(16)]}
                 for x, y in observations]
        need(len(demos) == 48 and
             all(sum(bit << i for i, bit in enumerate(demos[j]["input_bits"]))
                 == observations[j][0] for j in range(48)), "LOSSLESS_PAIRS")
        control = m.train(demos, "F124-BI-NONPROTECTED-SOURCE-NEUTRAL", 0)
        need(control["trained_both_from_same_40_FIT"]
             and control["public_CHECK_shared_exactly_8"]
             and control["model_receives_operator_token"] is False
             and control["model_receives_oracle_inverse"] is False,
             "AZ_COMPARATOR")
        outcome = {"route": control["choice"],
                   "parameters_bits_lower":
                       control["extra_task_model_bits_lower"]}
    cpu_ns = time.process_time_ns() - tick
    usage = resource.getrusage(resource.RUSAGE_SELF)
    max_rss_bytes = usage.ru_maxrss * 1024  # Linux unit is KiB
    need(max_rss_bytes > 0 and cpu_ns > 0, "NONPOSITIVE_MEASUREMENT")
    return {
        "schema": "mass.f124bi.fit-partial-child-measurement.v1",
        "arm": arm, "fixture": -940 if tag == "U" else -939,
        "public_48_sha256": public_hash,
        "observations": 48, "FIT": 40, "CHECK": 8,
        "source_family_visible_to_model": False,
        "CPU_ns_including_import_and_source_prep": cpu_ns,
        "peak_process_RSS_bytes": max_rss_bytes,
        "peak_RSS_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss Linux KiB",
        "runtime_identity": {
            "system": platform.platform(), "python": sys.version,
            "machine": platform.machine()},
        "fit_outcome_descriptive_only": outcome,
        "TRAIN_192_cpu_ns": None,
        "representation_scoring_cpu_ns": None,
        "full_native_graph_scoring_cpu_ns": None,
        "complete_cognition_state_bytes": None,
        "resource_parity_proven": False,
        "scientific_acceptance": False,
        "registered_source_generated": 0,
    }


def validate_measurement(item):
    need(item["schema"] == "mass.f124bi.fit-partial-child-measurement.v1",
         "CHILD_SCHEMA")
    need(item["observations"] == 48 and item["FIT"] == 40
         and item["CHECK"] == 8, "MATCHED_PUBLIC")
    need(item["source_family_visible_to_model"] is False
         and item["registered_source_generated"] == 0,
         "PROTECTED_ACCESS")
    need(item["TRAIN_192_cpu_ns"] is None
         and item["representation_scoring_cpu_ns"] is None
         and item["full_native_graph_scoring_cpu_ns"] is None
         and item["complete_cognition_state_bytes"] is None
         and not item["resource_parity_proven"]
         and not item["scientific_acceptance"], "FALSE_PARITY")


def aggregate(records):
    for row in records:
        validate_measurement(row)
    data = {}
    for fixture in FIXTURES:
        arms = {}
        for arm in ARM_IDS:
            values = [x for x in records
                      if x["fixture"] == (-940 if fixture == "U" else -939)
                      and x["arm"] == arm]
            need(len(values) == REPEATS, "REPETITION_MISMATCH")
            hashes = {x["public_48_sha256"] for x in values}
            need(len(hashes) == 1, "SOURCE_DRIFT")
            arms[arm] = {
                "CPU_ns_each": [x["CPU_ns_including_import_and_source_prep"]
                                for x in values],
                "CPU_ns_median": int(statistics.median(
                    x["CPU_ns_including_import_and_source_prep"] for x in values)),
                "whole_child_RSS_bytes_each":
                    [x["peak_process_RSS_bytes"] for x in values],
                "whole_child_RSS_bytes_median": int(statistics.median(
                    x["peak_process_RSS_bytes"] for x in values)),
                "public_48_sha256": next(iter(hashes)),
                "reported_fit": [x["fit_outcome_descriptive_only"] for x in values],
            }
        need(arms["candidate"]["public_48_sha256"] ==
             arms["AZ_baseline"]["public_48_sha256"], "PUBLIC_DATA_MISMATCH")
        data[fixture] = arms
    return {
        "schema": "mass.f124bi.matched-synthetic-partial-resource-evidence.v1",
        "protocol":"192 authentic TRAIN tasks NOT consumed; no source-original first-use",
        "recorded_arm_count": len(records),
        "synthetic_negative_fixtures_only": [-940, -939],
        "repeats_per_arm_per_fixture": REPEATS,
        "matched_measurements": data,
        "measured_only": ["task_import_public_source_and_fit_CPU_ns",
                          "fresh_python_process_peak_RSS_bytes"],
        "unqualified": ["192 authentic TRAIN amortization", "graph scoring",
                        "representation and inference", "native cognition state",
                        "whole task CPU and memory parity",
                        "scientific independent source acceptance"],
        "resource_parity_qualified": False,
        "scientific_admission": False,
        "registered_source_constructed": 0,
        "optimizer_promotion": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--child", action="store_true")
    ap.add_argument("--fixture", choices=FIXTURES)
    ap.add_argument("--arm", choices=ARM_IDS)
    ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    if a.child:
        need(a.fixture is not None and a.arm is not None, "CHILD_ARGUMENTS")
        print(json.dumps(child(a.fixture, a.arm), sort_keys=True))
        return
    need(a.output is not None, "MISSING_OUTPUT")
    need(sys.platform.startswith("linux"), "LINUX_RSS_REQUIRED")
    measurements = []
    # Opposite order on repeat 2, so scheduling history does not always
    # favor the same arm. Each child starts a fresh interpreter.
    for repeat in range(REPEATS):
        for fixture in FIXTURES:
            order = ARM_IDS if repeat % 2 == 0 else tuple(reversed(ARM_IDS))
            for arm in order:
                proc = subprocess.run(
                    [sys.executable, "-B", str(Path(__file__).resolve()),
                     "--child", "--fixture", fixture, "--arm", arm],
                    cwd=ROOT, check=True, capture_output=True, text=True,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    timeout=180)
                record = json.loads(proc.stdout)
                measurements.append(record)
    summary = aggregate(measurements)
    raw = json.dumps({"summary": summary, "raw_child_measurements": measurements},
                     indent=2, sort_keys=True) + "\n"
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(raw, encoding="utf-8")
    print("F124BI_MATCHED_SYNTHETIC_RESOURCE_SAMPLE=PASS")
    print("F124BI_RAW_CHILD_COUNT=" + str(len(measurements)))
    print("F124BI_TOTAL_RESOURCE_PARITY_QUALIFIED=false")
    print("F124BI_PROTECTED_FIRST_USE=false")
    print("F124BI_RESOURCE_RECEIPT_SHA256=" +
          hashlib.sha256(raw.encode()).hexdigest())


if __name__ == "__main__":
    main()
