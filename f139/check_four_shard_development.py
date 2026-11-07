"""Development-only four-process full-suite coverage/speed trial.

Never replaces required ordinary final regression, selection authority or
qualification results. Retains identical 1,414+ original test identities,
outcomes and skips, and requires both opposite-order paired measurements.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from collections import defaultdict

from f139.check_test_discovery_inventory import (
    case_ids, discover_profile_suite, profile_suite,
)

BRANCH = "engineering/f139-four-shard-dev-20261107"
MINIMUM_TESTS = 1414
SHARDS = 4
MIN_PAIR_SPEEDUP = 2.0


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, timeout=60).strip()


def flat(suite):
    for obj in suite:
        if isinstance(obj, unittest.TestSuite):
            yield from flat(obj)
        else:
            yield obj


def source_identity(root):
    return git(root, "rev-parse", "HEAD"), git(root, "rev-parse", "HEAD^{tree}")


def digest_rows(rows):
    rows = [(row["id"], row["outcome"]) for row in rows]
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def child(args, root):
    suite = discover_profile_suite(root)
    discovered = case_ids(suite)
    if len(discovered) < MINIMUM_TESTS or len(discovered) != len(set(discovered)):
        raise ValueError("F139 full unique-case inventory drift")
    if args.mode == "shard":
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        if plan["source_sha"] != git(root, "rev-parse", "HEAD"):
            raise ValueError("Shard plan does not match immutable source")
        tests = [test for test in flat(suite)
                 if plan["modules"].get(type(test).__module__) == args.index]
        suite = unittest.TestSuite(tests)
    ids = case_ids(suite)
    if args.mode == "shard" and not ids:
        raise ValueError("Empty shard is not qualified")
    report = profile_suite(suite, ids, stream=io.StringIO())
    if not report["successful"]:
        raise ValueError("Native test failure or incomplete shard")
    payload = dict(
        cases=report["cases"],
        suite_seconds=report["suite_seconds"],
        tests_run=report["tests_run"],
        skipped_ids=report["skipped_ids"],
        successful=report["successful"],
    )
    Path(args.output).write_text(
        json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def load_output(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not data["successful"] or data["tests_run"] != len(data["cases"]):
        raise ValueError("Incomplete or failing test worker")
    ids = [row["id"] for row in data["cases"]]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate worker test ID")
    return data


def run_worker(root, work, mode, label, *, plan=None, index=0):
    path = work / (label + ".json")
    command = [sys.executable, "-B", "-m", "f139.check_four_shard_development",
               "--mode", mode, "--output", str(path)]
    if plan is not None:
        command += ["--plan", str(plan), "--index", str(index)]
    result = subprocess.run(
        command, cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=900, check=False)
    if result.returncode:
        raise ValueError("Fail-closed test worker: " + label)
    return load_output(path)


def shard_plan(baseline, sha, work):
    weights = defaultdict(float)
    for row in baseline["cases"]:
        weights[row["module"]] += row["seconds"]
    loads = [0.0] * SHARDS
    assignments = {}
    for module, weight in sorted(weights.items(), key=lambda x: (-x[1], x[0])):
        shard = min(range(SHARDS), key=lambda i: (loads[i], i))
        assignments[module] = shard
        loads[shard] += weight
    if len(assignments) < SHARDS:
        raise ValueError("Insufficient independent modules")
    path = work / "plan.json"
    path.write_text(json.dumps(dict(source_sha=sha, modules=assignments),
                               separators=(",", ":")), encoding="utf-8")
    return path, loads


def run_shards(root, work, label, plan, baseline):
    started = time.perf_counter()
    jobs = []
    try:
        for index in range(SHARDS):
            out = work / (label + "-" + str(index) + ".json")
            command = [sys.executable, "-B", "-m", "f139.check_four_shard_development",
                       "--mode", "shard", "--output", str(out),
                       "--plan", str(plan), "--index", str(index)]
            process = subprocess.Popen(
                command, cwd=root, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            jobs.append((process, out))
        for process, _out in jobs:
            remaining = max(1, 900 - (time.perf_counter() - started))
            if process.wait(timeout=remaining) != 0:
                raise ValueError("Fail-closed original test shard")
        elapsed = time.perf_counter() - started
        results = [load_output(out) for _, out in jobs]
    finally:
        for process, _out in jobs:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=30)
    baseline_rows = baseline["cases"]
    reference = {row["id"]: row["outcome"] for row in baseline_rows}
    seen = {}
    skip_set = set()
    counts = []
    for result in results:
        counts.append(result["tests_run"])
        skip_set.update(result["skipped_ids"])
        for row in result["cases"]:
            if row["id"] in seen:
                raise ValueError("Cross-shard duplicate test")
            seen[row["id"]] = row["outcome"]
    if seen != reference or skip_set != set(baseline["skipped_ids"]):
        raise ValueError("Original full-suite outcome/skip parity lost")
    if sum(counts) != len(baseline_rows):
        raise ValueError("Original full-suite coverage lost")
    return elapsed, counts


def parent(args, root):
    if (os.environ.get("GITHUB_ACTIONS") != "true" or
            os.environ.get("GITHUB_REPOSITORY") != "spoonman136668-ai/FORGE" or
            os.environ.get("GITHUB_HEAD_REF") != BRANCH):
        raise ValueError("Isolated development PR runner required")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Dirty candidate source")
    sha, tree = source_identity(root)
    if sha != args.expected_source:
        raise ValueError("Checkout source drift")
    output = Path(args.output).resolve()
    output.relative_to(Path(os.environ["RUNNER_TEMP"]).resolve())
    with tempfile.TemporaryDirectory(
            prefix="f139-four-shard-", dir=os.environ["RUNNER_TEMP"]) as temp:
        work = Path(temp)
        original1 = run_worker(root, work, "full", "original1")
        plan, loads = shard_plan(original1, sha, work)
        candidate1, counts1 = run_shards(root, work, "candidate1", plan, original1)
        candidate2, counts2 = run_shards(root, work, "candidate2", plan, original1)
        original2 = run_worker(root, work, "full", "original2")
        if ([row["id"] for row in original1["cases"]] !=
                [row["id"] for row in original2["cases"]] or
                digest_rows(original1["cases"]) != digest_rows(original2["cases"]) or
                set(original1["skipped_ids"]) != set(original2["skipped_ids"])):
            raise ValueError("Original opposite-order baseline drift")
        if source_identity(root) != (sha, tree) or git(
                root, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("Source or tree changed during paired trial")
        original = [original1["suite_seconds"], original2["suite_seconds"]]
        candidates = [candidate1, candidate2]
        ratios = [a / b for a, b in zip(original, candidates)]
        benefit = "PASS_DEV_ONLY" if min(ratios) >= MIN_PAIR_SPEEDUP else "NO_GO"
        receipt = dict(
            schema="forge.f139.four-shard-development.v1",
            source_sha=sha, source_tree=tree,
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            workflow_run=os.environ.get("GITHUB_RUN_ID"),
            workflow_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
            platform=sys.platform, complete_original_cases=len(original1["cases"]),
            original_order_outcomes_sha256=digest_rows(original1["cases"]),
            baseline_skip_count=len(original1["skipped_ids"]),
            original_seconds=original, candidate_four_shard_seconds=candidates,
            opposite_order_pair_speedups=ratios,
            predicted_four_shard_load_seconds=loads,
            candidate_shard_test_counts=[counts1, counts2],
            full_test_parity="PASS", source_stable=True,
            threshold_each_pair=MIN_PAIR_SPEEDUP,
            benefit_status=benefit,
            final_full_regression_replaced=False, 
            default_ci_activation=False, production_change=False,
            scientific_first_use=False, external_execution=False,
            cached_test_skipping=False,
        )
        output.write_text(json.dumps(receipt, sort_keys=True, indent=2),
                          encoding="utf-8")
        print("F139_FOUR_SHARD_PARITY=PASS", flush=True)
        print("F139_FOUR_SHARD_BENEFIT=" + benefit, flush=True)
        print("F139_FOUR_SHARD_RATIOS=" + ",".join(
            format(value, ".4f") for value in ratios), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("full", "shard"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--plan")
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--expected-source")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.mode is not None:
        if args.mode == "shard" and (not args.plan or not 0 <= args.index < SHARDS):
            raise ValueError("Invalid fixed shard")
        child(args, root)
    else:
        parent(args, root)


if __name__ == "__main__":
    main()
