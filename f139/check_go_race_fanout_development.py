"""DEV-only full Go race-test fanout screen; never changes accepted CI.

This ABBA opposite-order paired development trial compares p2/p4/p4/p2
with complete source-bound Go race-test outcome parity. Both speed ratios
must exceed the unchanged 2.0 threshold before development consideration.
Even a positive trial is not a whole-CI adoption or speedup qualification.
All tests run with -race and -count=1. Only sanitized aggregates are exported.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


BRANCH = "engineering/f139-go-race-fanout-dev-20261107"
REPO = "spoonman136668-ai/FORGE"


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, timeout=60
    ).strip()


def stable_identity(root):
    return git(root, "rev-parse", "HEAD"), git(root, "rev-parse", "HEAD^{tree}")


def summary(path):
    test_outcomes = {}
    package_outcomes = {}
    malformed = 0
    lines = 0
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            lines += 1
            try:
                event = json.loads(line)
            except (ValueError, UnicodeError):
                malformed += 1
                continue
            if not isinstance(event, dict) or "Action" not in event:
                malformed += 1
                continue
            action = event.get("Action")
            if action not in ("pass", "fail", "skip"):
                continue
            package = event.get("Package")
            if not isinstance(package, str) or not package:
                raise ValueError("Missing Go package identity")
            test = event.get("Test")
            if test is None:
                key, dest = package, package_outcomes
            elif isinstance(test, str) and test:
                key, dest = package + "::" + test, test_outcomes
            else:
                raise ValueError("Invalid Go test identity")
            if key in dest:
                raise ValueError("Duplicate terminal Go test/package event")
            dest[key] = action
    if malformed or not test_outcomes or not package_outcomes:
        raise ValueError("Incomplete or malformed Go race JSON report")
    if any(v == "fail" for v in test_outcomes.values()) or any(
        v == "fail" for v in package_outcomes.values()
    ):
        raise ValueError("Race test failure")
    def fingerprint(mapping):
        return hashlib.sha256(json.dumps(
            sorted(mapping.items()), separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")).hexdigest()
    return {
        "json_events": lines,
        "test_cases": len(test_outcomes),
        "packages": len(package_outcomes),
        "skips": sum(x == "skip" for x in test_outcomes.values()),
        "test_outcome_sha256": fingerprint(test_outcomes),
        "package_outcome_sha256": fingerprint(package_outcomes),
    }


def trial(root, work, label, parallel):
    env = os.environ.copy()
    env["GOMAXPROCS"] = "2"
    env["GOFLAGS"] = "-p=" + str(parallel)
    env["GOMEMLIMIT"] = "1536MiB"
    output = work / (label + ".jsonl")
    errors = work / (label + ".stderr")
    started = time.perf_counter()
    with output.open("wb") as out, errors.open("wb") as err:
        completed = subprocess.run(
            ["go", "test", "-race", "-count=1", "-json", "./..."],
            cwd=root, env=env, stdout=out, stderr=err,
            timeout=900, check=False,
        )
    elapsed = time.perf_counter() - started
    if completed.returncode:
        raise ValueError("Full Go race arm failed: " + label)
    result = summary(output)
    result["wall_seconds"] = elapsed
    result["go_package_parallelism"] = parallel
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    output = Path(args.output).resolve()
    output.relative_to(runner_temp)
    if (os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != REPO
        or os.environ.get("GITHUB_HEAD_REF") != BRANCH
        or os.environ.get("RUNNER_OS") != "Linux"):
        raise ValueError("Development-only hosted Linux PR boundary refused")
    if (os.environ.get("GOMAXPROCS") != "2"
        or os.environ.get("GOFLAGS") != "-p=2"
        or os.environ.get("GOMEMLIMIT") != "1536MiB"):
        raise ValueError("Original CI resource budget drift")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Dirty source before Go race screen")
    sha, tree = stable_identity(root)
    if sha != args.expected_source:
        raise ValueError("Exact Go source/commit mismatch")
    go_version = subprocess.check_output(
        ["go", "version"], text=True, cwd=root, timeout=60
    ).strip()
    with tempfile.TemporaryDirectory(
        prefix="f139-go-race-fanout-", dir=runner_temp
    ) as directory:
        work = Path(directory)
        original1 = trial(root, work, "original1-p2", 2)
        candidate1 = trial(root, work, "candidate1-p4", 4)
        candidate2 = trial(root, work, "candidate2-p4", 4)
        original2 = trial(root, work, "original2-p2", 2)
        for field in ("test_cases", "packages", "skips",
                      "test_outcome_sha256", "package_outcome_sha256"):
            expected = original1[field]
            if any(arm[field] != expected
                   for arm in (candidate1, candidate2, original2)):
                raise ValueError("Complete Go race ABBA parity drift: " + field)
        if stable_identity(root) != (sha, tree) or git(
            root, "status", "--porcelain", "--untracked-files=all"
        ):
            raise ValueError("Source/tree changed during Go race ABBA comparison")
        baselines = [original1, original2]
        candidates = [candidate1, candidate2]
        ratios = [a["wall_seconds"] / b["wall_seconds"]
                  for a, b in zip(baselines, candidates)]
        verdict = "PASS_DEV_ONLY" if min(ratios) >= 2.0 else "NO_GO"
        receipt = {
            "schema": "forge.f139.go-race-fanout-opposite-order.v1",
            "source_sha": sha,
            "source_tree": tree,
            "runner_os": "Linux",
            "go_version": go_version,
            "workflow_run": os.environ.get("GITHUB_RUN_ID"),
            "environment": {"GOMAXPROCS": "2", "GOMEMLIMIT": "1536MiB"},
            "run_order": ["p2", "p4", "p4", "p2"],
            "baseline_p2": baselines,
            "candidate_p4": candidates,
            "opposite_order_pair_ratios": ratios,
            "outcome_parity": "PASS",
            "frozen_development_ratio_per_pair": 2.0,
            "frozen_full_pipeline_target_speedup": 2.0,
            "initial_cold_compilation_bias_controlled": True,
            "performance_verdict": verdict,
            "adoption_allowed": False,
            "default_ci_unchanged": True,
            "full_final_regression_replaced": False,
            "no_cached_test_skipping": True,
            "no_controller_or_science_execution": True,
        }
        output.write_text(json.dumps(
            receipt, sort_keys=True, indent=2
        ) + "\n", encoding="utf-8")
        print("F139_GO_RACE_FANOUT_ABBA_PARITY=PASS", flush=True)
        print("F139_GO_RACE_FANOUT_ABBA_DEV=" + verdict, flush=True)
        print("F139_GO_RACE_FANOUT_ABBA_RATIOS=" + ",".join(
            format(ratio, ".4f") for ratio in ratios
        ), flush=True)


if __name__ == "__main__":
    main()
