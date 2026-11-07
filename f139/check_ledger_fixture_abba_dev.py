"""Frozen same-runner ABBA screen for the entire unchanged F139 Python suite.

Development only: performance NO_GO never changes regression acceptance.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

BASE = "1429fbcf38eb3e4cbbf79b87231c2eafe13a7f20"
ROOT = Path(__file__).resolve().parents[1]
RUNNER_BRANCH = "engineering/f139-ledger-cold-fixture-dev-20261107"
EXPECTED_SKIPS = 7 if os.name == "nt" else 24


def git(*args, cwd=ROOT):
    return subprocess.check_output(
        ["git", "-C", str(cwd), *args], text=True, timeout=90).strip()


def clean_and_pinned(path, sha, tree):
    if git("rev-parse", "HEAD", cwd=path) != sha:
        raise ValueError("ABBA_SHA_DRIFT")
    if git("rev-parse", "HEAD^{tree}", cwd=path) != tree:
        raise ValueError("ABBA_TREE_DRIFT")
    if git("status", "--porcelain", "--untracked-files=all", cwd=path):
        raise ValueError("ABBA_SOURCE_DIRTY")


def discover_ids(path):
    code = (
        "import hashlib,sys;from pathlib import Path;"
        "root=Path.cwd();sys.path.insert(0,str(root/'f139'));"
        "from f139.check_test_discovery_inventory import "
        "discover_profile_suite,case_ids;"
        "ids=case_ids(discover_profile_suite(root));"
        "print('ABBA_IDS='+str(len(ids))+':'+"
        "hashlib.sha256('\\n'.join(ids).encode()).hexdigest())"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", code], cwd=path,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=180)
    if result.returncode:
        raise ValueError("ABBA_DISCOVERY_FAILED:" + str(result.returncode))
    matches = re.findall(r"ABBA_IDS=(\d+):([0-9a-f]{64})", result.stdout)
    if len(matches) != 1:
        raise ValueError("ABBA_DISCOVERY_RECEIPT_MISSING")
    return int(matches[0][0]), matches[0][1]


def execute(path, kind, index):
    cmd = [sys.executable, "-B", "-m", "unittest", "discover",
           "-s", "f139", "-p", "test_*.py", "-v"]
    started = time.perf_counter()
    result = subprocess.run(
        cmd, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors="replace", timeout=1200)
    seconds = time.perf_counter() - started
    output = result.stdout
    cases = re.findall(r"Ran (\d+) tests? in [0-9.]+s", output)
    skips = re.findall(r"OK \(skipped=(\d+)\)", output)
    if result.returncode or len(cases) != 1 or len(skips) != 1:
        raise ValueError("ABBA_FULL_SUITE_FAILED_" + kind + "_" + str(index)
                         + "_rc" + str(result.returncode))
    if int(cases[0]) != 1415 or int(skips[0]) != EXPECTED_SKIPS:
        raise ValueError("ABBA_COVERAGE_OR_SKIP_DRIFT")
    # Original individual test results remain in memory only, never exported.
    verdicts = re.findall(
        r"(?m)^test_\S+ \([^\n]+\) \.\.\. (?:ok|skipped .+)$",
        output)
    if len(verdicts) != 1415:
        raise ValueError("ABBA_VERBOSE_OUTCOME_INCOMPLETE:" + str(len(verdicts)))
    fingerprint = hashlib.sha256(
        "\n".join(sorted(verdicts)).encode("utf-8")).hexdigest()
    return {"arm": index, "kind": kind, "elapsed_seconds": round(seconds, 6),
            "tests": int(cases[0]), "skips": int(skips[0]),
            "outcomes_sha256": fingerprint, "exit_code": result.returncode}


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or (
            os.environ.get("GITHUB_HEAD_REF") != RUNNER_BRANCH):
        raise ValueError("ABBA_BRANCH_OR_RUNNER_NOT_AUTHORIZED")
    candidate = git("rev-parse", "HEAD")
    if candidate != os.environ.get("FORGE_BENCH_SOURCE"):
        raise ValueError("ABBA_EXPECTED_SOURCE_DRIFT")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("ABBA_UNCLEAN_CHECKOUT")
    candidate_tree = git("rev-parse", "HEAD^{tree}")
    base_tree = git("rev-parse", BASE+"^{tree}")
    with tempfile.TemporaryDirectory(prefix="forge-abba-") as tmp:
        paths = {name: Path(tmp)/name for name in ("baseline", "candidate")}
        installed = []
        try:
            for name, sha in (("baseline", BASE), ("candidate", candidate)):
                subprocess.run(["git", "-C", str(ROOT), "worktree", "add",
                                "--detach", "-q", str(paths[name]), sha],
                               check=True, timeout=180)
                installed.append(name)
            for name, sha, tree in (
                ("baseline", BASE, base_tree),
                ("candidate", candidate, candidate_tree)):
                clean_and_pinned(paths[name], sha, tree)
            ids = {name: discover_ids(path) for name, path in paths.items()}
            if ids["baseline"] != ids["candidate"] or ids["baseline"][0] != 1415:
                raise ValueError("ABBA_DISCOVERY_IDENTITY_DRIFT")
            timings = []
            for n, kind in enumerate(("baseline", "candidate",
                                      "candidate", "baseline"), start=1):
                sha = BASE if kind == "baseline" else candidate
                tree = base_tree if kind == "baseline" else candidate_tree
                clean_and_pinned(paths[kind], sha, tree)
                timings.append(execute(paths[kind], kind, n))
                clean_and_pinned(paths[kind], sha, tree)
            if len({x["outcomes_sha256"] for x in timings}) != 1:
                raise ValueError("ABBA_TEST_OUTCOME_DRIFT")
            a, b, c, d = (x["elapsed_seconds"] for x in timings)
            ratios = [a/b, d/c]
            aggregate = (a+d)/(b+c)
            passed = (min(ratios) >= 1.0 and aggregate >= 1.03)
            receipt = {
                "schema": "forge.f139.ledger-fixture-abba.dev.v1",
                "source_sha": candidate, "source_tree": candidate_tree,
                "baseline_sha": BASE, "baseline_tree": base_tree,
                "platform": sys.platform, "python": sys.version.split()[0],
                "test_id_sha256": ids["baseline"][1], "cases": 1415,
                "skips": EXPECTED_SKIPS, "arms": timings,
                "paired_speedups": [round(q, 6) for q in ratios],
                "aggregate_speedup": round(aggregate, 6),
                "frozen_min_aggregate": 1.03, "frozen_min_each": 1.0,
                "development_verdict": "PASS_DEV_ONLY" if passed else "NO_GO",
                "whole_ci_speedup_proven": False,
                "default_ci_activation": False,
            }
            output = Path(os.environ["RUNNER_TEMP"])/"f139-ledger-abba.json"
            output.write_text(json.dumps(receipt, sort_keys=True, indent=2)+"\n",
                              encoding="utf-8")
            print("FORGE_F139_LEDGER_ABBA="+receipt["development_verdict"])
        finally:
            for name in reversed(installed):
                subprocess.run(["git", "-C", str(ROOT), "worktree",
                                "remove", "--force", str(paths[name])],
                               check=True, timeout=180)
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("ABBA_FINAL_SOURCE_DIRTY")


if __name__ == "__main__":
    main()
