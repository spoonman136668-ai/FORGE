"""RAR-G115: bounded A/B/B/A comparison of complete Go race qualification.

This is a development-only measurement on existing hosted Linux CI.
No scientific, owner, runner, workflow-dispatch or default-pipeline authority.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "engineering/rar-g115-race-parallelism-dev-20261107"
BASE_FLAGS = "-p=2"
CANDIDATE_FLAGS = "-p=4"
GO_COMMAND = ("go", "test", "-race", "-count=1", "./...")
MIN_AGGREGATE = 1.03
MIN_EACH_PAIR = 1.0
MAX_MEMORY_RATIO = 1.30
MAX_MEMORY_BYTES = 6 * 1024 ** 3
ARM_TIMEOUT = 180
MEMORY_CURRENT = Path("/sys/fs/cgroup/memory.current")


def command(*args, env=None):
    return subprocess.check_output(
        list(args), cwd=ROOT, env=env, text=True, timeout=120).strip()


def clean_source(source, tree):
    if command("git", "rev-parse", "HEAD") != source:
        raise ValueError("G115_SOURCE_HEAD_DRIFT")
    if command("git", "rev-parse", "HEAD^{tree}") != tree:
        raise ValueError("G115_SOURCE_TREE_DRIFT")
    if command("git", "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("G115_SOURCE_NOT_CLEAN")


def memory_current():
    try:
        value = int(MEMORY_CURRENT.read_text(encoding="utf-8").strip())
        return value if value >= 0 else None
    except (OSError, ValueError):
        return None


def run_arm(index, kind, packages):
    flags = BASE_FLAGS if kind == "baseline" else CANDIDATE_FLAGS
    env = {**os.environ, "GOFLAGS": flags}
    start = time.perf_counter()
    peak = memory_current()
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as output:
        proc = subprocess.Popen(
            GO_COMMAND, cwd=ROOT, env=env, stdout=output,
            stderr=subprocess.STDOUT, start_new_session=True, text=True)
        try:
            while proc.poll() is None:
                value = memory_current()
                if value is not None:
                    peak = max(peak or 0, value)
                if time.perf_counter() - start > ARM_TIMEOUT:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=15)
                    raise ValueError("G115_ARM_TIMEOUT_" + str(index))
                time.sleep(0.1)
            rc = proc.wait()
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=15)
        elapsed = round(time.perf_counter() - start, 6)
        value = memory_current()
        if value is not None:
            peak = max(peak or 0, value)
        output.seek(0)
        result = output.read()
    if rc != 0:
        raise ValueError("G115_RACE_SUITE_FAILED_" + str(index)
                         + "_RC" + str(rc) + ":" + result[-1500:])
    recorded = {}
    for line in result.splitlines():
        m = re.match(r"^(ok|\?)\s+(\S+)\s+", line)
        if not m or m.group(2) not in packages:
            continue
        name, outcome = m.group(2), (
            "ok" if m.group(1) == "ok" else "no_test_files")
        if name in recorded:
            raise ValueError("G115_DUPLICATE_PACKAGE_" + name)
        recorded[name] = outcome
    if set(recorded) != packages:
        missing = sorted(packages - set(recorded))
        extra = sorted(set(recorded) - packages)
        raise ValueError("G115_PACKAGE_COVERAGE_DRIFT:"
                         + repr((missing, extra))[:500])
    digest = hashlib.sha256(json.dumps(
        sorted(recorded.items()), separators=(",", ":")).encode()).hexdigest()
    return {
        "arm": index, "kind": kind, "go_flags": flags,
        "elapsed_seconds": elapsed, "cgroup_memory_peak_bytes": peak,
        "package_count": len(recorded), "outcome_sha256": digest,
        "exit_code": rc,
    }


def main():
    if (sys.platform != "linux"
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_HEAD_REF") != BRANCH):
        raise ValueError("G115_DEV_LINUX_PR_ONLY")
    if (os.environ.get("GOMAXPROCS") != "2"
            or os.environ.get("GOFLAGS") != BASE_FLAGS
            or os.environ.get("GOMEMLIMIT") != "1536MiB"):
        raise ValueError("G115_FROZEN_RESOURCE_ENVIRONMENT_DRIFT")
    if not os.environ.get("RUNNER_TEMP"):
        raise ValueError("G115_MISSING_RUNNER_TEMP")
    source = command("git", "rev-parse", "HEAD")
    if source != os.environ.get("FORGE_RACE_SOURCE"):
        raise ValueError("G115_EXACT_SOURCE_DRIFT")
    tree = command("git", "rev-parse", "HEAD^{tree}")
    clean_source(source, tree)
    go_version = command("go", "version")
    go_env = command("go", "env", "GOOS", "GOARCH", "CGO_ENABLED", "GOCACHE")
    if go_env.splitlines()[:3] != ["linux", "amd64", "1"]:
        raise ValueError("G115_UNSUPPORTED_GO_PLATFORM")
    expected = tuple(sorted(set(command(
        "go", "list", "-f", "{{.ImportPath}}", "./...").splitlines())))
    if not expected or len(expected) != len(set(expected)):
        raise ValueError("G115_PACKAGE_INVENTORY_INVALID")
    packages = set(expected)
    package_hash = hashlib.sha256(
        "\n".join(expected).encode("utf-8")).hexdigest()
    arms = []
    for index, kind in enumerate(
            ("baseline", "candidate", "candidate", "baseline"), start=1):
        clean_source(source, tree)
        arms.append(run_arm(index, kind, packages))
        clean_source(source, tree)
    if len({arm["outcome_sha256"] for arm in arms}) != 1:
        raise ValueError("G115_PACKAGE_OUTCOME_DRIFT")
    a, b, c, d = (arm["elapsed_seconds"] for arm in arms)
    speedups = (a / b, d / c)
    aggregate = (a + d) / (b + c)
    mem_a, mem_b, mem_c, mem_d = (
        arm["cgroup_memory_peak_bytes"] for arm in arms)
    measured = all(
        isinstance(m, int) and m > 0
        for m in (mem_a, mem_b, mem_c, mem_d))
    mem_ratios = (
        [mem_b / mem_a, mem_c / mem_d] if measured else [])
    memory_ok = (
        measured and max(mem_b, mem_c) <= MAX_MEMORY_BYTES
        and max(mem_ratios) <= MAX_MEMORY_RATIO)
    passed = (
        min(speedups) >= MIN_EACH_PAIR
        and aggregate >= MIN_AGGREGATE and memory_ok)
    receipt = {
        "schema": "forge.rar.g115.race-parallelism.abba.dev.v1",
        "source_sha": source, "source_tree": tree,
        "branch": BRANCH, "platform": sys.platform,
        "go_version": go_version, "go_env": go_env.splitlines(),
        "command": list(GO_COMMAND), "original_go_flags": BASE_FLAGS,
        "candidate_go_flags": CANDIDATE_FLAGS,
        "unchanged_gomaxprocs": 2, "unchanged_gomemlimit": "1536MiB",
        "package_count": len(expected), "package_id_sha256": package_hash,
        "arms": arms,
        "paired_speedups": [round(x, 6) for x in speedups],
        "aggregate_speedup": round(aggregate, 6),
        "frozen_min_each_pair": MIN_EACH_PAIR,
        "frozen_min_aggregate": MIN_AGGREGATE,
        "cgroup_memory_measurement": "job-level-sampled-memory.current",
        "cgroup_memory_measured": measured,
        "candidate_over_baseline_paired_memory_ratios": [
            round(x, 6) for x in mem_ratios],
        "frozen_max_paired_memory_ratio": MAX_MEMORY_RATIO,
        "frozen_max_candidate_memory_bytes": MAX_MEMORY_BYTES,
        "memory_admission": bool(memory_ok),
        "development_verdict": "PASS_DEV_ONLY" if passed else "NO_GO",
        "whole_ci_speedup_proven": False,
        "default_ci_activation": False,
        "full_regression_required": True,
        "science_pass_claimed": False,
    }
    output = Path(os.environ["RUNNER_TEMP"]) / "f139-race-abba.json"
    output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
    print("FORGE_RAR_G115=" + receipt["development_verdict"])
    print("FORGE_RAR_G115_AGGREGATE=" + str(receipt["aggregate_speedup"]))
    clean_source(source, tree)


if __name__ == "__main__":
    main()
