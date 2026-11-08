"""G132 DEV: read-only cProfile of original 16 typed-program F139 cases.

Run after full mandatory Windows qualification. No original tests are changed,
skipped, monkeypatched, cached or reordered; profiles are diagnostic only.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import pstats
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = "8cf1ecc115707e186f666f7aad12de8dbdc2a88c"
BRANCH = "engineering/rar-g132-typed-hotspot-callgraph-20261108"
TARGET = Path("f139/test_nci04_prompt_program.py")
EXPECTED = 16
TIMEOUT = 180

def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT,
                                   text=True, timeout=60).strip()

def assert_source(sha: str) -> None:
    if git("rev-parse", "HEAD") != sha or git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("G132_SOURCE_DIRTY_OR_DRIFT")

def relpath(path: str) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except (ValueError, OSError):
        return Path(path).name

def main() -> int:
    if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_REPOSITORY") != "spoonman136668-ai/FORGE"
            or os.environ.get("GITHUB_EVENT_NAME") != "pull_request"
            or os.environ.get("GITHUB_HEAD_REF") != BRANCH
            or not os.environ.get("RUNNER_TEMP")):
        raise ValueError("G132_WINDOWS_BRANCH_ONLY")
    source_sha = git("rev-parse", "HEAD")
    if source_sha != os.environ.get("FORGE_G132_HEAD") or git("merge-base", BASE, source_sha) != BASE:
        raise ValueError("G132_SOURCE_PIN_MISMATCH")
    if set(git("diff", "--name-only", BASE, source_sha).splitlines()) != {
        ".github/workflows/qualify.yml",
        "scripts/check_rar_g132_typed_hotspot.py",
    }:
        raise ValueError("G132_CHANGE_SCOPE_INVALID")
    assert_source(source_sha)
    target_raw = (ROOT / TARGET).read_bytes()
    module = ast.parse(target_raw.decode("utf-8"), filename=str(TARGET))
    tests = sorted(node.name for cls in module.body
                   if isinstance(cls, ast.ClassDef) and cls.name == "TypedProgramTests"
                   for node in cls.body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and node.name.startswith("test_"))
    if len(tests) != EXPECTED or len(tests) != len(set(tests)) or not any(
            name == "test_recovered_generated_sources_continue_without_resetting_negatives"
            for name in tests):
        raise ValueError("G132_ORIGINAL_TEST_INVENTORY_INVALID")
    output = Path(os.environ["RUNNER_TEMP"]) / "rar-g132-typed-hotspot.json"
    report = dict(
        schema="forge.rar-g132.typed-program-profile.v1",
        source_sha=source_sha,
        source_tree=git("rev-parse", "HEAD^{tree}"),
        source_file=str(TARGET),
        source_file_sha256=hashlib.sha256(target_raw).hexdigest(),
        original_test_names_sha256=hashlib.sha256("\n".join(tests).encode()).hexdigest(),
        original_test_names=tests,
        original_test_count=EXPECTED,
        original_test_selection="unittest discover -s f139 -p test_nci04_prompt_program.py",
        repeat_test_result_cache=False,
        profile_only=True,
        runner_os=os.environ.get("RUNNER_OS"),
        runner_arch=os.environ.get("RUNNER_ARCH"),
        runner_image=os.environ.get("ImageOS"),
        image_version=os.environ.get("ImageVersion"),
        cpu_count=os.cpu_count(),
        python_version=platform.python_version(),
        successful=False,
        verdict="UNVERIFIED",
    )
    try:
        with tempfile.TemporaryDirectory(prefix="g132-typed-", dir=os.environ["RUNNER_TEMP"]) as temp:
            stats_path = Path(temp) / "typed.pstats"
            command = [sys.executable, "-B", "-m", "cProfile", "-o", str(stats_path),
                       "-m", "unittest", "discover", "-s", "f139",
                       "-p", "test_nci04_prompt_program.py"]
            start = time.perf_counter()
            completed = subprocess.run(command, cwd=ROOT, text=True, errors="replace",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=TIMEOUT, check=False)
            report["profiled_wall_seconds"] = round(time.perf_counter()-start, 6)
            report["profile_command_exit_code"] = completed.returncode
            report["raw_test_stdout_sha256"] = hashlib.sha256(completed.stdout.encode()).hexdigest()
            report["raw_test_stderr_sha256"] = hashlib.sha256(completed.stderr.encode()).hexdigest()
            matches = re.findall(r"Ran\s+(\d+)\s+tests?\s+in\s+([0-9.]+)s", completed.stderr)
            report["reported_test_count"] = int(matches[-1][0]) if matches else None
            report["reported_unittest_seconds"] = float(matches[-1][1]) if matches else None
            report["unittest_success"] = bool(
                completed.returncode == 0
                and re.search(r"(?m)^OK\s*$", completed.stderr))
            if not report["unittest_success"] or report["reported_test_count"] != EXPECTED:
                report["test_output_tail"] = completed.stderr[-2000:]
                raise ValueError("G132_ORIGINAL_TEST_QUALIFICATION_FAILED")
            stats = pstats.Stats(str(stats_path))
            funcs = []
            for (filename, line, name), (primitive, calls, own, cumulative, callers) in stats.stats.items():
                path = relpath(filename)
                if not path.startswith("f139/"):
                    continue
                funcs.append(dict(file=path, line=line, name=name,
                                  calls=calls, primitive_calls=primitive,
                                  self_seconds=round(own, 6),
                                  cumulative_seconds=round(cumulative, 6)))
            if not funcs:
                raise ValueError("G132_F139_PROFILE_NOT_RECORDED")
            report["f139_function_count"] = len(funcs)
            report["top_cumulative"] = sorted(funcs, key=lambda x: x["cumulative_seconds"],
                                              reverse=True)[:30]
            report["top_self_time"] = sorted(funcs, key=lambda x: x["self_seconds"],
                                            reverse=True)[:30]
            report["original_test_cumulative"] = sorted([
                x for x in funcs if x["file"] == str(TARGET)
                and x["name"].startswith("test_")
            ], key=lambda x: x["cumulative_seconds"], reverse=True)
            if len(report["original_test_cumulative"]) != EXPECTED:
                raise ValueError("G132_TEST_PROFILE_IDENTITY_DRIFT")
            assert_source(source_sha)
            report["successful"] = True
            report["verdict"] = "PASS_DIAGNOSTIC_ONLY"
            return 0
    except BaseException as error:
        report["error"] = type(error).__name__ + ":" + str(error)[-1000:]
        report["verdict"] = "INVALID"
        raise
    finally:
        output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print("FORGE_RAR_G132=" + report["verdict"], flush=True)

if __name__ == "__main__":
    sys.exit(main())
