"""F124-N authenticated original-weight source-disjoint DEVELOPMENT comparison.

Unchanged F124-H forward bytecode, no fitting, no protected first-use.
Scores the new frozen public FIT/DEV sources with identical causal labels.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import inspect
import json
from pathlib import Path
import sys
from types import FunctionType, SimpleNamespace

import f124h_source as old_source
import f124h_signed_evidence as old_model
import f124h_train_receipt as old_control
import f124n_novel_structure_source as source

TRAIN_SHA = "3ce0356ad9c19aeb4557ffe0b138908707c65ab3ce4b6af952adbf9899988254"
MODEL_BLOB = "599d7a87f0812f3a7d2c8680861b6360d3640bc0"
SOURCE_BLOB = "3feab91460f29ec169e1904479a134bb04691937"
SCHEMA = "forge.research.f124n.authenticated-original-weight-new-structure-development.v1"


def need(ok, code):
    source.need(ok, "EVIDENCE_" + code)


def blob(module):
    raw = Path(module.__file__).read_bytes().replace(b"\r\n", b"\n")
    return source.git_blob(raw)


def clone_single_validator(fn, global_name):
    """Retain original Python bytecode, change exactly one validator global."""
    refs = [n for n in ast.walk(ast.parse(inspect.getsource(fn)))
            if isinstance(n, ast.Attribute)
            and isinstance(n.value, ast.Name) and n.value.id == global_name]
    need(len(refs) == 1 and refs[0].attr == "validate",
         "ONE_VALIDATION_GLOBAL_ONLY")
    g = dict(fn.__globals__)
    g[global_name] = SimpleNamespace(validate=source.validate_public)
    clone = FunctionType(fn.__code__, g, fn.__name__, fn.__defaults__,
                         fn.__closure__)
    clone.__kwdefaults__ = fn.__kwdefaults__
    need(clone.__code__ is fn.__code__ and
         fn.__globals__[global_name] is not g[global_name],
         "CODE_IDENTITY_OR_GLOBAL_MUTATION")
    return clone


def authenticate(path):
    source.frozen()
    need(blob(old_model) == MODEL_BLOB and blob(old_source) == SOURCE_BLOB
         and old_model.frozen(), "ORIGINAL_CODE_OR_DEPENDENCY_DRIFT")
    raw = Path(path).read_bytes()
    need(hashlib.sha256(raw).hexdigest() == TRAIN_SHA,
         "AUTHENTIC_ORIGINAL_TRAIN_WEIGHTS_RECEIPT")
    r = json.loads(raw)
    need(r["schema"] == "forge.research.f124h.train-only-signed-competing-evidence.v1"
         and r["source_sha"] == "409f9129442f3d47b3d9bc032342f48042f3127a"
         and r["model_git_blob"] == MODEL_BLOB
         and r["source_git_blob"] == SOURCE_BLOB
         and r["phase"] == "TRAIN_ONLY"
         and r["protected_confirmation_cases_generated"] == 0
         and r["independent_original_first_use"] is False
         and r["scientific_acceptances"] == 0
         and len(r["lanes"]) == 2, "ORIGINAL_TRAIN_CUSTODY")
    weights = {}
    for row in r["lanes"]:
        lane = row["lane"]
        need(lane in source.COHORTS and lane not in weights
             and row["selected_arm_train_only"] == "B",
             "FROZEN_SELECTED_B_ONLY")
        arm = row["arms"]["B"]
        w = arm["weights"]
        need(arm["epochs"] == 100 and arm["phase"] == "TRAIN_ONLY"
             and len(w) == 21 and old_model.sha(w) == arm["weight_sha256"],
             "ORIGINAL_ARM_B_WEIGHT_DRIFT")
        weights[lane] = tuple(w)
    need(set(weights) == set(source.COHORTS), "BOTH_LANES_CUSTODY")
    return weights


def score_one(graph, weights, fwd, fixed):
    try:
        prob, logit, gradients, work = fwd(graph, list(weights), "B")
        need(gradients is None, "TRAINING_OCCURRED")
        fixed_answer, fixed_work = fixed(graph)
        return {"B": prob >= 0.5, "B_logit": logit,
                "fixed": bool(fixed_answer), "failed": False,
                "B_edge_scans": work["public_edge_scans"],
                "B_bit_ops": work["raw_bit_multiply_adds"],
                "fixed_edge_scans": fixed_work["public_edge_scans"],
                "fixed_bit_ops": fixed_work["bit_comparisons"]}
    except (old_source.Invalid, OverflowError, ArithmeticError) as exc:
        return {"B": False, "fixed": False, "failed": True,
                "failure": type(exc).__name__ + ":" + str(exc)[:160],
                "B_edge_scans": 0, "B_bit_ops": 0,
                "fixed_edge_scans": 0, "fixed_bit_ops": 0}


def evaluate(lane, phase, weights, fwd, fixed):
    per_depth = {str(k): {"pairs": 0, "B_paired": 0, "fixed_paired": 0,
                          "B_failures": 0} for k in (7, 8, 9)}
    counts = {"pairs": 0, "B_paired": 0, "fixed_paired": 0,
              "role_only_paired": 0, "exact_paired": 0,
              "B_failures": 0, "B_edge_scans": 0, "B_bit_ops": 0,
              "fixed_edge_scans": 0, "fixed_bit_ops": 0}
    hashes = []
    for vector in source.VECTORS:
        for seed in source.COHORTS[lane][phase]:
            positive, negative = source.build(lane, seed, vector, phase)
            a = score_one(positive, weights, fwd, fixed)
            b = score_one(negative, weights, fwd, fixed)
            # Any execution error is a negative for BOTH comparisons. Never
            # drop the denominator or cherry-pick recovered successes.
            ok_b = not (a["failed"] or b["failed"]) and a["B"] and not b["B"]
            ok_f = not (a["failed"] or b["failed"]) and a["fixed"] and not b["fixed"]
            failed = bool(a["failed"] or b["failed"])
            need(source.public_routes(positive) == 1
                 and source.public_routes(negative) == 0,
                 "ORACLE_ADMISSION_DRIFT")
            depth = str(len(positive["roles"]))
            row = per_depth[depth]
            row["pairs"] += 1
            row["B_paired"] += int(ok_b)
            row["fixed_paired"] += int(ok_f)
            row["B_failures"] += int(failed)
            counts["pairs"] += 1
            counts["B_paired"] += int(ok_b)
            counts["fixed_paired"] += int(ok_f)
            counts["B_failures"] += int(failed)
            counts["exact_paired"] += 1
            counts["role_only_paired"] += int(
                source.public_routes(positive, True) > 0
                and source.public_routes(negative, True) == 0)
            for k in ("B_edge_scans", "B_bit_ops",
                      "fixed_edge_scans", "fixed_bit_ops"):
                counts[k] += a[k] + b[k]
            case = {"lane": lane, "phase": phase, "seed": seed,
                    "vector": list(vector), "depth": int(depth),
                    "B_pair": bool(ok_b), "fixed_pair": bool(ok_f),
                    "B_failed": failed}
            hashes.append(hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest())
    need(counts["pairs"] == 48 and counts["exact_paired"] == 48
         and counts["role_only_paired"] == 0
         and all(x["pairs"] == 16 for x in per_depth.values()),
         "FULL_BALANCED_SOURCE_DENOMINATOR")
    counts["depth"] = per_depth
    counts["case_hashes"] = hashes
    return counts


def produce(train_receipt):
    weights = authenticate(train_receipt)
    fwd = clone_single_validator(old_model.forward, "source")
    fixed = clone_single_validator(old_control.fixed_comparator, "graph")
    out = {"schema": SCHEMA, "freeze_git_blob": source.PROTOCOL_BLOB,
           "original_train_receipt_sha256": TRAIN_SHA,
           "original_model_git_blob": MODEL_BLOB,
           "frozen_B_weights_unchanged": True,
           "forward_code_object_unchanged": True,
           "development_only": True, "lanes": [],
           "protected_examples_generated": 0,
           "protected_examples_scored": 0,
           "independent_first_use": False, "scientific_acceptances": 0,
           "accepted_ref_mutations": 0, "optimizer_promotions": 0,
           "new_trained_mechanisms": 0, "codex_calls": 0, "paid_api_calls": 0}
    for lane in ("Wingless", "Yggdrasil"):
        fit = evaluate(lane, "FIT", weights[lane], fwd, fixed)
        dev = evaluate(lane, "DEV", weights[lane], fwd, fixed)
        out["lanes"].append({"lane": lane,
                             "frozen_original_B_weight_sha256": old_model.sha(list(weights[lane])),
                             "fit": fit, "dev": dev,
                             "development_verdict": (
                                 "ORIGINAL_B_BEATS_FIXED_APPROX_ON_FRESH_DEV"
                                 if dev["B_paired"] > dev["fixed_paired"]
                                 else "ORIGINAL_B_DOES_NOT_BEAT_FIXED_APPROX_ON_FRESH_DEV")})
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--original-train", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    output = Path(args.output)
    need(output.parent.is_dir() and not output.exists(), "IMMUTABLE_OUTPUT")
    result = produce(args.original_train)
    payload = (json.dumps(result, sort_keys=True, indent=2) + "\n").encode()
    with output.open("xb") as f:
        f.write(payload)
    print("F124N_DEVELOPMENT_EVIDENCE_SHA256=" + hashlib.sha256(payload).hexdigest())
    for lane in result["lanes"]:
        r = lane["dev"]
        print("F124N_DEV=" + lane["lane"] + ":B=" + str(r["B_paired"]) +
              "/48:fixed=" + str(r["fixed_paired"]) +
              "/48:B_failures=" + str(r["B_failures"]))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("F124N_FAIL_CLOSED:" + str(e), file=sys.stderr)
        sys.exit(1)
