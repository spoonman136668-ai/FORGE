"""F124-BJ single authenticated TRAIN-cost qualification, no U/R/VALIDATE.

This performs exactly one 192-task TRAIN generation after the independent
provider-witness job succeeds. Uses frozen T1 learned_prior unchanged, emits
complete public-source SHA receipts, actual process CPU and peak RSS. Full
graph/cognition execution does not exist in the T1 kernel: no parity claim.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NATIVE = ROOT / "nativeevidence"
AZ_BLOB = "0122190aa3a0972ffb4a709bc1bdd8179c8ba6c7"
KERNEL_BLOB = "bf81ed56cc0daa2c413ad7d9c698969f92befe3d"


def need(cond, reason):
    if not cond:
        raise RuntimeError("F124BJ_TRAIN_" + reason)


def file_blob(path):
    p = subprocess.run(["git", "rev-parse", "HEAD:" +
                        str(Path(path).relative_to(ROOT)).replace("\\", "/")],
                       cwd=ROOT, capture_output=True, text=True)
    need(p.returncode == 0, "SOURCE_IDENTITY_LOOKUP")
    return p.stdout.strip()


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    need(spec and spec.loader, "IMPORT")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def source_public(tag):
    need(tag in ("U", "R"), "DENY_PROSPECTIVE")
    name = "f124bh_u_family.py" if tag == "U" else "f124bh_r_family.py"
    fixture = -940 if tag == "U" else -939
    source = load("bj_negative_" + tag, HERE / name)
    public, private = source.fixture(fixture)
    need(public["source_family_sent_to_model"] is False
         and len(public["FIT"]) == 40
         and len(public["CHECK"]) == 8, "PROTECTED_ISOLATION")
    return public["FIT"], public["CHECK"]


def meta_train():
    need(sys.platform == "linux", "LINUX_PROCESS_RESOURCES")
    import resource
    need(file_blob(NATIVE / "f124az_joint_public_inverse.py") == AZ_BLOB
         and file_blob(HERE / "20261018-mass-learned-kernel.py") == KERNEL_BLOB,
         "IMMUTABLE_FROZEN_MODELS")
    t0 = time.process_time_ns()
    a = load("bj_independent_affine", HERE / "f124bj_affine_source.py")
    b = load("bj_independent_shear", HERE / "f124bj_shear_source.py")
    task_public = []
    public_hashes = []
    for idx in range(900000, 900192):
        source = a if idx < 900096 else b
        task, private = source.make(idx)
        need(private["task_private"] == idx and
             len(private["corruption_private"]) == 6 and
             len(task[0]) == 40 and len(task[1]) == 8,
             "FROZEN_48_RESPONSES")
        # Never hand private recipe/corruption/oracle source to learner.
        task_public.append(task)
        canonical = json.dumps([idx, task[0], task[1]],
                               sort_keys=True, separators=(",", ":")).encode()
        public_hashes.append({"task_id": idx,
                              "public_sha256": hashlib.sha256(canonical).hexdigest()})
    create_cpu_ns = time.process_time_ns() - t0
    need(len(public_hashes) == 192
         and len({x["public_sha256"] for x in public_hashes}) == 192,
         "TRAIN_TASK_UNIQUENESS")
    kernel = load("bj_frozen_learned_kernel",
                  HERE / "20261018-mass-learned-kernel.py")
    t1 = time.process_time_ns()
    weights, receipt = kernel.learned_prior(task_public)
    fit_cpu_ns = time.process_time_ns() - t1
    total_cpu_ns = time.process_time_ns() - t0
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    need(len(weights) == 4 and receipt["public_training_task_count"] == 192
         and receipt["training_forward_evaluations"] == 192 * 2608,
         "FROZEN_PRIOR_TRAIN")
    ids = [r["task_id"] for r in public_hashes]
    need(ids == list(range(900000, 900192)), "TRAIN_IDENTITY_SET")
    return {
        "schema": "mass.f124bj.original-192-train-public-prior-cost.v1",
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "candidate_original_blob": KERNEL_BLOB,
        "baseline_original_blob": AZ_BLOB,
        "registered_TRAIN_task_count": 192,
        "registered_TRAIN_uses": 1,
        "TRAIN_consumed_once": True,
        "training_public_receipts": public_hashes,
        "observation_count_each": 48,
        "fit_count_each": 40, "check_count_each": 8,
        "TRAIN_source_creation_CPU_ns": create_cpu_ns,
        "TRAIN_frozen_prior_CPU_ns": fit_cpu_ns,
        "TRAIN_total_cpu_ns": total_cpu_ns,
        "TRAIN_peak_process_RSS_bytes": rss,
        "amortized_training_CPU_ns_ceiling_per_128":
            (total_cpu_ns + 127) // 128,
        "training_forward_evaluations": receipt["training_forward_evaluations"],
        "learned_prior_sha256": hashlib.sha256(weights).hexdigest(),
        "learned_prior_weights_hex": weights.hex(),
        "learned_prior_weight_bytes_only": 4,
        "native_graph_scoring_CPU_ns": None,
        "native_memory_cognition_RSS_bytes": None,
        "whole_task_cpu_and_memory_parity": False,
        "independent_external_source_novelty_certified": False,
        "validation_or_unseen_source_consumed": 0,
        "scientific_admission": False,
        "optimizer_promotion": False,
        "os_python": {"platform": platform.platform(),
                      "version": sys.version, "architecture": platform.machine()},
    }


def task_fit(arm, tag, prior_hex):
    need(arm in ("AZ", "prior_kernel") and tag in ("U", "R"),
         "FIT_SCOPE_DENIED")
    need(sys.platform == "linux", "LINUX_PROCESS_RESOURCES")
    need(file_blob(NATIVE / "f124az_joint_public_inverse.py") == AZ_BLOB
         and file_blob(HERE / "20261018-mass-learned-kernel.py") == KERNEL_BLOB,
         "MODEL_SOURCE_DRIFT")
    t0 = time.process_time_ns()
    fit, check = source_public(tag)
    observations = fit + check
    public_sha = hashlib.sha256(json.dumps(
        observations, separators=(",", ":")).encode()).hexdigest()
    if arm == "prior_kernel":
        kernel = load("bj_prior_kernel_fit", HERE / "20261018-mass-learned-kernel.py")
        prior = bytes.fromhex(prior_hex)
        need(len(prior) == 4, "NONFOURBYTE_PRIOR")
        weights, data = kernel.fit_public(fit, check, init=prior)
        need(data["public_forward_evaluations"] == 2608,
             "IMMUTABLE_KERNEL_FIT")
        route = {"fit_bits": data["public_FIT_bit_errors"],
                 "check_bits": data["public_CHECK_bit_errors"],
                 "learned_task_bits_lower": len(weights)*8}
    else:
        sys.path.insert(0, str(NATIVE))
        baseline = load("bj_original_AZ_fit", NATIVE / "f124az_joint_public_inverse.py")
        demos = [{"input_bits": [(x >> i) & 1 for i in range(16)],
                  "output_bits": [(y >> i) & 1 for i in range(16)]}
                 for x, y in observations]
        data = baseline.train(demos, "BJ-NEGATIVE-PUBLIC-ONLY", 0)
        need(data["trained_both_from_same_40_FIT"] and
             data["public_CHECK_shared_exactly_8"] and
             data["model_receives_operator_token"] is False,
             "FROZEN_AZ")
        route = {"AZ_public_route": data["choice"],
                 "AZ_bits_lower": data["extra_task_model_bits_lower"]}
    cpu = time.process_time_ns() - t0
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    return {"schema": "mass.f124bj.same-input-task-fit-partial.v1",
            "arm": arm, "synthetic_fixture": -940 if tag == "U" else -939,
            "public_sha256": public_sha,
            "child_CPU_ns": cpu, "child_peak_process_RSS_bytes": peak,
            "route_or_fit_descriptive": route, "public_n": 48,
            "complete_native_graph_CPU_ns": None,
            "complete_cognition_state_memory": None,
            "scientific_source": False, "resource_parity": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("TRAIN", "FIT"), required=True)
    parser.add_argument("--arm", choices=("AZ", "prior_kernel"))
    parser.add_argument("--tag", choices=("U", "R"))
    parser.add_argument("--prior-hex")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "TRAIN":
        need(args.output is not None
             and not args.arm and not args.tag, "TRAIN_ARGS")
        result = meta_train()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(result, sort_keys=True, indent=2) + "\n"
        args.output.write_text(data, encoding="utf-8")
        print("F124BJ_TRAIN_192_ORIGINAL_PUBLIC_FIRST_USE=COMPLETE")
        print("F124BJ_TRAIN_FORWARD_EVALUATIONS=" +
              str(result["training_forward_evaluations"]))
        print("F124BJ_TRAIN_COST_CPU_NS=" + str(result["TRAIN_total_cpu_ns"]))
        print("F124BJ_TRAIN_PEAK_RSS_BYTES=" +
              str(result["TRAIN_peak_process_RSS_bytes"]))
        print("F124BJ_TRAIN_EVIDENCE_SHA256=" +
              hashlib.sha256(data.encode()).hexdigest())
    else:
        need(args.arm and args.tag and args.prior_hex and
             args.output is None, "FIT_ARGS")
        print(json.dumps(task_fit(args.arm, args.tag, args.prior_hex),
                         sort_keys=True))


if __name__ == "__main__":
    main()
