"""DEV-only Windows CI overlap experiment: run original F139 and Go checks together.

The four-arm ABBA trial changes only scheduling and repeats every full original check. It does not select tests, change source fixtures,
relax Windows durability semantics, cache test results or change default CI.
Untrusted raw child logs remain private in RUNNER_TEMP and are never uploaded.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time


BRANCH = "engineering/f139-windows-ci-overlap-dev-20261107"
EXPECTED_REPO = "spoonman136668-ai/FORGE"
EXPECTED_PY_TESTS = 1414
EXPECTED_WIN_SKIPS = 7


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, timeout=60,
    ).strip()


def python_result(log):
    # CPython's unchanged unittest CLI emits these final terminal summary lines.
    end = log[-12000:]
    hit = re.search(r"Ran (\d+) tests? in [0-9.]+s", end)
    skip = re.search(r"OK\s*\(skipped=(\d+)\)", end)
    if not hit or int(hit.group(1)) != EXPECTED_PY_TESTS:
        raise ValueError("F139 original test count mismatch")
    if not skip or int(skip.group(1)) != EXPECTED_WIN_SKIPS:
        raise ValueError("F139 original Windows skip count mismatch")
    if re.search(r"FAILED\s*\(", end):
        raise ValueError("F139 original test failure")
    return int(hit.group(1)), int(skip.group(1))


def self_test():
    clean = "...\nRan 1414 tests in 40.1s\n\nOK (skipped=7)\n"
    if python_result(clean) != (1414, 7):
        raise ValueError("Summary positive control invalid")
    bad = [clean.replace("1414", "1413"),
           clean.replace("skipped=7", "skipped=8"),
           clean.replace("OK (skipped=7)", "FAILED (failures=1)")]
    for specimen in bad:
        try:
            python_result(specimen)
        except ValueError:
            continue
        raise ValueError("Summary negative control was not rejected")
    print("F139_WINDOWS_CI_OVERLAP_NEGATIVE_CONTROLS=PASS")


def command(cmd, root, out, err, barrier, limit):
    barrier.wait(timeout=30)
    start = time.perf_counter()
    with out.open("wb") as stdout, err.open("wb") as stderr:
        try:
            cp = subprocess.run(cmd, cwd=root, stdout=stdout, stderr=stderr,
                                check=False, timeout=limit)
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Bounded original command timed out") from exc
    if cp.returncode:
        raise ValueError("Original mandatory test/build returned failure")
    return time.perf_counter() - start


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    root = Path(__file__).resolve().parents[1]
    runner = Path(os.environ["RUNNER_TEMP"]).resolve()
    output = Path(args.output).resolve()
    output.relative_to(runner)
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_OS") != "Windows"
            or os.environ.get("GITHUB_HEAD_REF") != BRANCH
            or os.environ.get("GITHUB_REPOSITORY") != EXPECTED_REPO):
        raise ValueError("Hosted exact-branch Windows development guard refused")
    for key, value in (("GOMAXPROCS", "2"), ("GOFLAGS", "-p=2"),
                       ("GOMEMLIMIT", "1536MiB")):
        if os.environ.get(key) != value:
            raise ValueError("Existing resource budget drift: " + key)
    sha, tree = git(root, "rev-parse", "HEAD"), git(root, "rev-parse", "HEAD^{tree}")
    if sha != args.expected_source or git(
        root, "status", "--porcelain", "--untracked-files=all"
    ):
        raise ValueError("Exact clean source preflight failed")
    toolchain = subprocess.check_output(
        ["go", "version"], cwd=root, text=True, timeout=60
    ).strip()
    py_cmd = [sys.executable, "-B", "-m", "unittest", "discover",
              "-s", "f139", "-p", "test_*.py"]
    # The three original Go commands remain complete and unspecialized.
    go_commands = [["go", "test", "-count=1", "./..."],
                   ["go", "vet", "./..."], ["go", "build", "./..."]]
    folder = runner / "f139-windows-ci-overlap-private"
    folder.mkdir(exist_ok=True)
    records = []

    def trial(index, overlap):
        local = folder / ("arm" + str(index))
        local.mkdir(exist_ok=False)
        py_out, py_err = local / "python.stdout", local / "python.stderr"
        barrier = threading.Barrier(2 if overlap else 1)
        def go_work():
            barrier.wait(timeout=30)
            started = time.perf_counter()
            steps = []
            for i, cmd in enumerate(go_commands):
                t0 = time.perf_counter()
                stdout, stderr = local / ("go%d.stdout" % i), local / ("go%d.stderr" % i)
                with stdout.open("wb") as out, stderr.open("wb") as err:
                    try:
                        proc = subprocess.run(
                            cmd, cwd=root, stdout=out, stderr=err,
                            timeout=600, check=False
                        )
                    except subprocess.TimeoutExpired as exc:
                        raise ValueError("Original complete Go command timed out") from exc
                if proc.returncode:
                    raise ValueError("Original complete Go check failed: stage "+str(i))
                steps.append(round(time.perf_counter() - t0, 6))
            return time.perf_counter() - started, steps

        t0 = time.perf_counter()
        if overlap:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                py_future = pool.submit(
                    command, py_cmd, root, py_out, py_err, barrier, 1100
                )
                go_future = pool.submit(go_work)
                py_elapsed = py_future.result()
                go_elapsed, steps = go_future.result()
        else:
            py_elapsed = command(py_cmd, root, py_out, py_err, barrier, 1100)
            go_elapsed, steps = go_work()
        wall = time.perf_counter() - t0
        count, skipped = python_result(
            py_err.read_text(encoding="utf-8", errors="replace")
        )
        if git(root, "rev-parse", "HEAD") != sha or git(
            root, "rev-parse", "HEAD^{tree}"
        ) != tree or git(root, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("Source/tree became dirty after full original checks")
        record = {
            "arm": index,
            "mode": "overlap" if overlap else "serial",
            "python_tests": count,
            "python_skips": skipped,
            "python_exit": 0,
            "go_test_exit": 0,
            "go_vet_exit": 0,
            "go_build_exit": 0,
            "python_seconds": round(py_elapsed, 6),
            "go_seconds": round(go_elapsed, 6),
            "go_check_seconds": steps,
            "stage_seconds": round(wall, 6),
        }
        records.append(record)
        print("F139_WINDOWS_ABBA_ARM_%d=PASS" % index, flush=True)

    overall_start = time.perf_counter()
    for index, overlap in enumerate((False, True, True, False), start=1):
        trial(index, overlap)
    elapsed = time.perf_counter() - overall_start
    from f139.check_test_discovery_inventory import collect
    inventory = collect(root)
    ids = inventory["ids"]
    if (len(ids) != EXPECTED_PY_TESTS
            or len(set(ids)) != EXPECTED_PY_TESTS
            or len(inventory["skipped"]) != EXPECTED_WIN_SKIPS):
        raise ValueError("Original test identity and skip inventory drift")
    serial1, parallel1, parallel2, serial2 = records
    paired = [
        serial1["stage_seconds"] / parallel1["stage_seconds"],
        serial2["stage_seconds"] / parallel2["stage_seconds"],
    ]
    aggregate = (
        serial1["stage_seconds"] + serial2["stage_seconds"]
    ) / (
        parallel1["stage_seconds"] + parallel2["stage_seconds"]
    )
    # Frozen in the PR before this full ABBA measurement: 10% both directional
    # comparisons and at least 15% aggregate; NOT the 2x whole-pipeline target.
    verdict = (
        "PASS_DEV_ONLY"
        if min(paired) >= 1.10 and aggregate >= 1.15 else "NO_GO"
    )
    receipt = {
        "schema": "forge.f139.windows-ci-stage-overlap-abba.dev.v1",
        "candidate_sha": sha,
        "candidate_tree": tree,
        "job_run": os.environ["GITHUB_RUN_ID"],
        "runner_os": "Windows",
        "go_toolchain": toolchain,
        "resource": {"GOMAXPROCS": "2", "GOFLAGS": "-p=2", "GOMEMLIMIT": "1536MiB"},
        "run_order": ["serial", "overlap", "overlap", "serial"],
        "arms": records,
        "original_python_tests": EXPECTED_PY_TESTS,
        "original_python_skips": EXPECTED_WIN_SKIPS,
        "python_test_ids_sha256": hashlib.sha256(
            ("\n".join(ids)+"\n").encode("utf-8")).hexdigest(),
        "original_python_unittest_exit": 0,
        "original_go_test_exit": 0,
        "original_go_vet_exit": 0,
        "original_go_build_exit": 0,
        "paired_stage_ratios": paired,
        "aggregate_stage_ratio": aggregate,
        "paired_minimum": 1.10,
        "aggregate_minimum": 1.15,
        "experimental_wall_seconds": round(elapsed, 6),
        "performance_verdict": verdict,
        "performance_acceptance": "DEV_ONLY_NOT_WHOLE_PIPELINE",
        "default_ci_promotion_allowed": False,
        "ci_policy_adoption_allowed": False,
        "mandatory_suite_replaced_or_skipped": False,
        "source_dirty": False,
        "raw_logs_publicly_uploaded": False,
    }
    output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
    print("F139_WINDOWS_FULL_REGRESSION_ALL_FOUR_ARMS=PASS", flush=True)
    print("F139_WINDOWS_FULL_GO_CHECKS_ALL_FOUR_ARMS=PASS", flush=True)
    print("F139_WINDOWS_OVERLAP_ABBA_DEV=" + verdict, flush=True)
    print("F139_WINDOWS_OVERLAP_ABBA_RATIOS=" +
          ",".join("%.4f" % v for v in paired), flush=True)


if __name__ == "__main__":
    main()
