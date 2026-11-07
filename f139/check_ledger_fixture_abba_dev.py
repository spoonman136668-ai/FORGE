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

BASE = "e48693e41347942c2b581c2fa2793406020b7b67"
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



def _step(path, label, argv, *, stdin=None, env_extra=None, timeout=480):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    if env_extra:
        env.update(env_extra)
    started = time.perf_counter()
    completed = subprocess.run(
        argv, cwd=path, env=env, input=stdin, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        errors="replace", timeout=timeout)
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        raise ValueError("ABBA_WINDOWS_STAGE_FAILED_" + label
                         + "_RC_" + str(completed.returncode))
    return round(elapsed, 6), completed.stdout


def windows_pre_suite(path):
    """The original Windows qualification's executable pre-Python controls."""
    controls = (
        ("isolation-unittest", [sys.executable, "-B", "-m", "unittest",
             "discover", "-s", "isolationguard", "-p", "test_*.py", "-v"]),
        ("isolation-enforcement", [sys.executable, "-B", "isolationguard/check.py"]),
        ("fsa-scripts", [sys.executable, "-B", "-m", "unittest", "discover",
             "-s", "scripts", "-p", "test_fsa_*py", "-v"]),
        ("fsad1", [sys.executable, "-B", "-m", "unittest", "discover",
             "-s", "fsad1", "-p", "test_*.py", "-v"]),
        ("transport", [sys.executable, "-B", "-m", "unittest", "discover",
             "-s", "f139", "-p", "test_github_command_transport.py", "-v"]),
    )
    for source in ("80ae30719bcd9f179da4aa4e8f14dc36fd15818e",
                   "556d61f795cab1a042d26b46bbc1087dd436f52d"):
        _step(path, "pinned-transport-source",
              ["git", "cat-file", "-e",
               source + ":f139/local_controller.py"])
    return {name: _step(path, name, cmd)[0] for name, cmd in controls}


def windows_post_suite(path):
    """Repeat each real Go/GenEnv/Promptbreeder Windows qualification command.

    GitHub checkout/setup-go/artifact upload are shared overhead, not included
    in the separately labeled, matched executable-critical-path measurement.
    """
    report = {}
    modules = (
        ("genenv", "f139.check_genenv_source_integration"),
        ("prompt", "f139.check_prompt_source_integration"),
        ("typed", "f139.check_prompt_program_integration"),
    )
    with tempfile.TemporaryDirectory(prefix="f139-abba-genenv-") as work:
        old_result = None
        for name, module in modules:
            request_args = [sys.executable, "-B", "-m", module, "--request"]
            elapsed, request = _step(path, name + "-request", request_args)
            report[name + "-request"] = elapsed
            env = {"CGO_ENABLED": "0", "GOTOOLCHAIN": "local"}
            elapsed, result = _step(
                path, name + "-go-run",
                ["go", "run", "./cmd/f139-genenv-source"], stdin=request,
                env_extra=env, timeout=600)
            report[name + "-go-run"] = elapsed
            output = Path(work) / (name + ".json")
            output.write_text(result, encoding="utf-8")
            elapsed, _ = _step(
                path, name + "-validate",
                [sys.executable, "-B", "-m", module, "--result", str(output)])
            report[name + "-validate"] = elapsed
            if name == "typed":
                old_result = output
                elapsed, request = _step(
                    path, "typed-next-request",
                    [sys.executable, "-B", "-m", module, "--request",
                     "--previous", str(old_result)])
                report["typed-next-request"] = elapsed
                elapsed, result = _step(
                    path, "typed-next-go-run",
                    ["go", "run", "./cmd/f139-genenv-source"], stdin=request,
                    env_extra=env, timeout=600)
                report["typed-next-go-run"] = elapsed
                output2 = Path(work) / "typed-next.json"
                output2.write_text(result, encoding="utf-8")
                elapsed, _ = _step(
                    path, "typed-next-validate",
                    [sys.executable, "-B", "-m", module, "--result",
                     str(output2), "--previous", str(old_result)])
                report["typed-next-validate"] = elapsed
    for label, command in (
        ("go-test", ["go", "test", "-count=1", "./..."]),
        ("go-vet", ["go", "vet", "./..."]),
        ("go-build", ["go", "build", "./..."]),
    ):
        report[label] = _step(path, label, command, timeout=720)[0]
    return report


def execute(path, kind, index):
    # TextTestRunner's verbose output is not an outcome inventory: tests may
    # print during a case, or use non-test_* names. The repository's existing
    # ProfileResult records every original case lifecycle instead.
    code = r'''
import hashlib, io, json
from pathlib import Path
from f139.check_test_discovery_inventory import (
    discover_profile_suite, case_ids, profile_suite)
suite = discover_profile_suite(Path.cwd())
ids = case_ids(suite)
report = profile_suite(suite, ids, stream=io.StringIO())
if not (report["successful"] and report["complete_inventory_and_order"]
        and report["tests_run"] == len(ids) == 1420
        and report["failures"] == report["errors"] == 0
        and report["unexpected_successes"] == 0):
    raise SystemExit("ABBA_ORIGINAL_FULL_SUITE_FAILED")
outcomes = [(row["id"], row["outcome"]) for row in report["cases"]]
if len(outcomes) != 1420 or any(
        outcome not in ("success", "skipped", "expected_failure")
        for _identity, outcome in outcomes):
    raise SystemExit("ABBA_OUTCOME_IDENTITY_INCOMPLETE")
print("ABBA_RESULT=" + json.dumps({
    "tests": report["tests_run"],
    "skips": len(report["skipped_ids"]),
    "skipped_sha256": hashlib.sha256(
        "\n".join(sorted(report["skipped_ids"])).encode()).hexdigest(),
    "outcomes_sha256": hashlib.sha256(
        json.dumps(outcomes, separators=(",", ":")).encode()).hexdigest(),
}, sort_keys=True))
'''
    pipeline_started = time.perf_counter()
    component_seconds = windows_pre_suite(path) if os.name == "nt" else {}
    started = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-B", "-c", code], cwd=path,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors="replace", timeout=1200)
    seconds = time.perf_counter() - started
    matches = re.findall(r"(?m)^ABBA_RESULT=(\{[^\r\n]+\})$",
                         result.stdout)
    if result.returncode or len(matches) != 1:
        raise ValueError("ABBA_FULL_SUITE_FAILED_" + kind + "_" + str(index)
                         + "_rc" + str(result.returncode))
    doc = json.loads(matches[0])
    if doc["tests"] != 1420 or doc["skips"] != EXPECTED_SKIPS:
        raise ValueError("ABBA_COVERAGE_OR_SKIP_DRIFT")
    if os.name == "nt":
        component_seconds["python-f139-full-suite"] = round(seconds, 6)
        component_seconds.update(windows_post_suite(path))
    executable_seconds = time.perf_counter() - pipeline_started
    return {"arm": index, "kind": kind, "elapsed_seconds": round(seconds, 6),
            "windows_executable_seconds": (
                round(executable_seconds, 6) if os.name == "nt" else None),
            "components_seconds": component_seconds,
            "tests": doc["tests"], "skips": doc["skips"],
            "skipped_sha256": doc["skipped_sha256"],
            "outcomes_sha256": doc["outcomes_sha256"],
            "exit_code": result.returncode}


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
            if ids["baseline"] != ids["candidate"] or ids["baseline"][0] != 1420:
                raise ValueError("ABBA_DISCOVERY_IDENTITY_DRIFT")
            timings = []
            for n, kind in enumerate(("baseline", "candidate",
                                      "candidate", "baseline"), start=1):
                sha = BASE if kind == "baseline" else candidate
                tree = base_tree if kind == "baseline" else candidate_tree
                clean_and_pinned(paths[kind], sha, tree)
                timings.append(execute(paths[kind], kind, n))
                clean_and_pinned(paths[kind], sha, tree)
            if (len({x["outcomes_sha256"] for x in timings}) != 1 or
                    len({x["skipped_sha256"] for x in timings}) != 1):
                raise ValueError("ABBA_TEST_OUTCOME_DRIFT")
            a, b, c, d = (x["elapsed_seconds"] for x in timings)
            ratios = [a/b, d/c]
            aggregate = (a+d)/(b+c)
            passed = (min(ratios) >= 1.0 and aggregate >= 1.03)
            whole_windows = None
            if os.name == "nt":
                times = [x["windows_executable_seconds"] for x in timings]
                wa, wb, wc, wd = times
                windows_pairs = [wa / wb, wd / wc]
                windows_aggregate = (wa + wd) / (wb + wc)
                whole_windows = {
                    "kind": "matched_windows_executable_ci_critical_path",
                    "excluded_common_overhead": [
                        "checkout_action", "setup_go_action",
                        "artifact_upload_action", "runner_allocation"],
                    "pair_speedups": [round(x, 6) for x in windows_pairs],
                    "aggregate_speedup": round(windows_aggregate, 6),
                    "minimum_each_pair": 1.0,
                    "minimum_aggregate": 1.0,
                    "critical_path_improvement": (
                        min(windows_pairs) > 1.0
                        and windows_aggregate > 1.0),
                }
            receipt = {
                "schema": "forge.f139.ledger-fixture-abba.dev.v2",
                "source_sha": candidate, "source_tree": candidate_tree,
                "baseline_sha": BASE, "baseline_tree": base_tree,
                "platform": sys.platform, "python": sys.version.split()[0],
                "test_id_sha256": ids["baseline"][1], "cases": 1420,
                "skips": EXPECTED_SKIPS, "arms": timings,
                "paired_speedups": [round(q, 6) for q in ratios],
                "aggregate_speedup": round(aggregate, 6),
                "frozen_min_aggregate": 1.03, "frozen_min_each": 1.0,
                "development_verdict": "PASS_DEV_ONLY" if passed else "NO_GO",
                "windows_executable_ci": whole_windows,
                "whole_ci_speedup_proven": False,
                "default_ci_activation": False,
            }
            output = Path(os.environ["RUNNER_TEMP"])/"f139-ledger-abba.json"
            output.write_text(json.dumps(receipt, sort_keys=True, indent=2)+"\n",
                              encoding="utf-8")
            print("FORGE_F139_LEDGER_ABBA="+receipt["development_verdict"])
            if whole_windows is not None:
                print("FORGE_F139_WINDOWS_CRITICAL_PATH="+(
                    "PASS_DEV_ONLY" if whole_windows["critical_path_improvement"]
                    else "NO_GO"))
        finally:
            for name in reversed(installed):
                subprocess.run(["git", "-C", str(ROOT), "worktree",
                                "remove", "--force", str(paths[name])],
                               check=True, timeout=180)
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("ABBA_FINAL_SOURCE_DIRTY")


if __name__ == "__main__":
    main()
