"""DEV-only Windows CI overlap experiment: run original F139 and Go checks together.

This changes only scheduling. It does not select tests, change source fixtures,
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
    if sha != args.expected_source:
        raise ValueError("Exact source SHA mismatch")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Dirty preflight checkout")
    toolchain = subprocess.check_output(
        ["go", "version"], cwd=root, text=True, timeout=60
    ).strip()
    # Same full original commands; the extra JSON emission does not change Go
    # -count=1 semantics or package selection.
    py_cmd = [sys.executable, "-B", "-m", "unittest", "discover",
              "-s", "f139", "-p", "test_*.py"]
    go_commands = [["go", "test", "-count=1", "./..."],
                   ["go", "vet", "./..."], ["go", "build", "./..."]]
    barrier = threading.Barrier(2)
    folder = runner / "f139-windows-ci-overlap-private"
    folder.mkdir(exist_ok=True)
    py_out, py_err = folder / "python.stdout", folder / "python.stderr"
    go_steps = []
    def go_work():
        barrier.wait(timeout=30)
        started = time.perf_counter()
        for i, cmd in enumerate(go_commands):
            stdout, stderr = folder / ("go%d.stdout" % i), folder / ("go%d.stderr" % i)
            t0 = time.perf_counter()
            with stdout.open("wb") as out, stderr.open("wb") as err:
                try:
                    result = subprocess.run(cmd, cwd=root, stdout=out, stderr=err,
                                            timeout=600, check=False)
                except subprocess.TimeoutExpired as exc:
                    raise ValueError("Original Go command timed out") from exc
            if result.returncode:
                raise ValueError("Mandatory Go test/vet/build failure at stage " + str(i))
            go_steps.append(round(time.perf_counter()-t0, 6))
        return time.perf_counter() - started
    overall_started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        python_future = pool.submit(command, py_cmd, root, py_out, py_err, barrier, 1100)
        go_future = pool.submit(go_work)
        py_seconds = python_future.result()
        go_seconds = go_future.result()
    elapsed = time.perf_counter() - overall_started
    count, skipped = python_result(py_err.read_text(encoding="utf-8", errors="replace"))
    from f139.check_test_discovery_inventory import collect
    discovery = collect(root)
    identities = discovery["ids"]
    if (len(identities) != EXPECTED_PY_TESTS
            or len(set(identities)) != EXPECTED_PY_TESTS
            or len(discovery["skipped"]) != EXPECTED_WIN_SKIPS):
        raise ValueError("Original test identity/skip inventory drift")
    if git(root, "rev-parse", "HEAD") != sha or git(
        root, "rev-parse", "HEAD^{tree}"
    ) != tree or git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Source mutated by overlapped mandatory checks")
    receipt = {
        "schema": "forge.f139.windows-ci-stage-overlap.dev.v1",
        "candidate_sha": sha,
        "candidate_tree": tree,
        "job_run": os.environ["GITHUB_RUN_ID"],
        "runner_os": "Windows",
        "go_toolchain": toolchain,
        "resource": {"GOMAXPROCS": "2", "GOFLAGS": "-p=2", "GOMEMLIMIT": "1536MiB"},
        "original_python_tests": count,
        "original_python_skips": skipped,
        "python_test_ids_sha256": hashlib.sha256(
            ("\n".join(identities)+"\n").encode("utf-8")).hexdigest(),
        "original_python_unittest_exit": 0,
        "original_go_test_exit": 0,
        "original_go_vet_exit": 0,
        "original_go_build_exit": 0,
        "python_wall_seconds": round(py_seconds, 6),
        "go_wall_seconds": round(go_seconds, 6),
        "go_command_wall_seconds": go_steps,
        "combined_overlap_wall_seconds": round(elapsed, 6),
        "baseline_prior_windows_job_seconds": 565.0,
        "baseline_is_independent_host_and_source": True,
        "performance_acceptance": "UNVERIFIED_UNPAIRED",
        "ci_policy_adoption_allowed": False,
        "mandatory_suite_replaced_or_skipped": False,
        "source_dirty": False,
        "raw_logs_publicly_uploaded": False,
    }
    output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
    print("F139_WINDOWS_ORIGINAL_FULL_PYTHON=PASS")
    print("F139_WINDOWS_ORIGINAL_GO_TEST_VET_BUILD=PASS")
    print("F139_WINDOWS_OVERLAP_SOURCE_PARITY=PASS")
    print("F139_WINDOWS_OVERLAP_DEV_SECONDS=%.3f" % elapsed)


if __name__ == "__main__":
    main()
