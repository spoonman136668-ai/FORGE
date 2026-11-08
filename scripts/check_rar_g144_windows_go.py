"""RAR-G144: original full Windows Go test/vet overlap under one Job Object.

No test selection, flags retuning, result caching, special owners, or science.
The exact original full 'go build ./...' runs after BOTH original test/vet
finish. Process-tree Job Object peak and package identity fail closed.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

# Reuse the previously dual-platform-qualified Windows Job Object highwater
# meter rather than introduce an independent runner or resource controller.
from check_rar_g133_f139_suite_abba import JobTreeMemory
from check_rar_g145_pr_scope import admit_original_pr, negative_controls

ROOT = Path(__file__).resolve().parents[1]
REPO = "spoonman136668-ai/FORGE"
MAX_MEMORY = 4 * 1024**3
MAX_SECONDS = 200
ORIGINAL = {
    "test": ["go", "test", "-count=1", "./..."],
    "vet": ["go", "vet", "./..."],
    "build": ["go", "build", "./..."],
}
PACKAGE = re.compile(r"^(?:ok|\?)\s+(\S+)\s+", re.MULTILINE)


def git(*parts: str) -> str:
    return subprocess.check_output(
        ["git", *parts], cwd=ROOT, text=True, timeout=45
    ).strip()


def stable(sha: str) -> None:
    if git("rev-parse", "HEAD") != sha:
        raise ValueError("G144_HEAD_SHA_DRIFT")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("G144_WORKTREE_DIRTY")


def parse_packages(s: str) -> set[str]:
    names = PACKAGE.findall(s)
    if len(names) != len(set(names)):
        raise ValueError("G144_DUPLICATE_GO_PACKAGE")
    return set(names)


def get_packages() -> set[str]:
    listed = subprocess.check_output(
        ["go", "list", "./..."], cwd=ROOT, text=True, timeout=80
    ).splitlines()
    if len(listed) != len(set(listed)) or len(listed) < 130:
        raise ValueError("G144_EXPECTED_PACKAGE_INVENTORY_INVALID")
    return set(listed)


def permit() -> str:
    if (
        sys.platform != "win32"
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != REPO
        or os.environ.get("RUNNER_OS") != "Windows"
        or not os.environ.get("RUNNER_TEMP")
    ):
        raise ValueError("G144_WINDOWS_HOSTED_GITHUB_ONLY")
    event = os.environ.get("GITHUB_EVENT_NAME")
    if event == "pull_request":
        if os.environ.get("GITHUB_BASE_REF") != "main":
            raise ValueError("G144_PR_SOURCE_SCOPE_UNAUTHORIZED")
    elif event == "push":
        if os.environ.get("GITHUB_REF") != "refs/heads/main":
            raise ValueError("G144_MAIN_PUSH_ONLY")
    else:
        raise ValueError("G144_EVENT_UNAUTHORIZED")
    sha = git("rev-parse", "HEAD")
    if sha != os.environ.get("FORGE_G144_HEAD"):
        raise ValueError("G144_SOURCE_SHA_UNVERIFIED")
    stable(sha)
    negative_controls()
    if event == "pull_request":
        admission = admit_original_pr(sha, git)
        print("G145_PR_ADMISSION=" + admission, flush=True)
    if (os.environ.get("GOFLAGS") != "-p=2"
            or os.environ.get("GOMAXPROCS") != "2"
            or os.environ.get("GOMEMLIMIT") != "1536MiB"):
        raise ValueError("G144_ORIGINAL_GO_RESOURCE_FLAGS_DRIFT")
    return sha


def worker(mode: str, gate: Path) -> int:
    if mode not in ORIGINAL:
        raise ValueError("G144_WORKER_MODE_INVALID")
    # The parent first assigns this Python worker to a real Windows Job Object.
    # Any go.exe child then inherits the verified job, eliminating an assignment
    # race during child process creation.
    start = time.monotonic()
    while not gate.is_file():
        if time.monotonic() - start > 30:
            raise ValueError("G144_JOB_ASSIGNMENT_GATE_TIMEOUT")
        time.sleep(0.02)
    code = subprocess.call(ORIGINAL[mode], cwd=ROOT, env=os.environ.copy())
    return code


def terminate_job(meter: JobTreeMemory) -> None:
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    api.TerminateJobObject.restype = wintypes.BOOL
    if not api.TerminateJobObject(meter.handle, 1):
        raise ValueError("G144_TERMINATE_JOB_FAILED")


def main() -> int:
    sha = permit()
    if parse_packages("ok  x/a 0.01s\n?  x/b [no test files]\n") != {"x/a", "x/b"}:
        raise ValueError("G144_PARSER_POSITIVE_CONTROL")
    for invalid in ("ok  x/a 0.01s\nok  x/a 0.02s\n",):
        try:
            parse_packages(invalid)
        except ValueError:
            pass
        else:
            raise ValueError("G144_DUPLICATE_NEGATIVE_CONTROL")
    expected = get_packages()
    report_path = Path(os.environ["RUNNER_TEMP"]) / "rar-g144-windows-go.json"
    report = {
        "schema": "forge.rar-g144.windows-go.v1",
        "source_sha": sha,
        "source_tree": git("rev-parse", "HEAD^{tree}"),
        "clean_before": True,
        "go_version": subprocess.check_output(["go", "version"], cwd=ROOT, text=True).strip(),
        "runner_os": os.environ.get("RUNNER_OS"),
        "runner_image": os.environ.get("ImageOS"),
        "runner_image_version": os.environ.get("ImageVersion"),
        "gomaxprocs": os.environ["GOMAXPROCS"],
        "goflags": os.environ["GOFLAGS"],
        "gomemlimit": os.environ["GOMEMLIMIT"],
        "package_count": len(expected),
        "package_names_sha256": hashlib.sha256(
            "\n".join(sorted(expected)).encode()
        ).hexdigest(),
        "original_commands": ORIGINAL,
        "max_original_stage_seconds": MAX_SECONDS,
        "max_process_tree_peak_commit_bytes": MAX_MEMORY,
        "process_tree_memory_scope": "SINGLE_WINDOWS_JOB_OBJECT_ALL_ORIGINAL_GO_DESCENDANTS",
        "results": [],
        "status": "INVALID",
    }
    meter = None
    workers: list[subprocess.Popen] = []
    start = time.monotonic()
    failed = False
    try:
        with tempfile.TemporaryDirectory(
            prefix="rar-g144-windows-", dir=os.environ["RUNNER_TEMP"]
        ) as tmp:
            home = Path(tmp)
            meter = JobTreeMemory()
            for mode in ("test", "vet"):
                gate = home / (mode + ".gate")
                logfile = home / (mode + ".log")
                with logfile.open("wb") as out:
                    proc = subprocess.Popen(
                        [sys.executable, "-B", str(Path(__file__)), "--worker", mode, str(gate)],
                        cwd=ROOT, env=os.environ.copy(),
                        stdout=out, stderr=subprocess.STDOUT,
                    )
                workers.append(proc)
                meter.assign(proc)
                gate.write_text("assigned\n", encoding="utf-8")
            peak = 0
            while True:
                peak = max(peak, meter.peak())
                if peak > MAX_MEMORY:
                    raise ValueError("G144_WINDOWS_JOB_MEMORY_CAP_EXCEEDED")
                codes = [p.poll() for p in workers]
                if any(c is not None and c != 0 for c in codes):
                    raise ValueError("G144_ORIGINAL_TEST_OR_VET_FAILED")
                if all(c is not None for c in codes):
                    break
                if time.monotonic() - start > MAX_SECONDS:
                    raise ValueError("G144_ORIGINAL_WINDOWS_GO_TIMEOUT")
                time.sleep(0.1)

            for mode, proc in zip(("test", "vet"), workers):
                data = (home / (mode + ".log")).read_text(encoding="utf-8", errors="replace")
                if proc.wait(timeout=10) != 0:
                    raise ValueError("G144_ORIGINAL_GO_COMMAND_FAILED_" + mode)
                result = {
                    "mode": mode,
                    "exit_code": proc.returncode,
                    "log_sha256": hashlib.sha256(data.encode()).hexdigest(),
                }
                if mode == "test":
                    found = parse_packages(data)
                    if found != expected:
                        raise ValueError(
                            "G144_FULL_GO_PACKAGE_PARITY_FAILED:"
                            f" expected={len(expected)} got={len(found)}"
                        )
                    result["package_names_sha256"] = hashlib.sha256(
                        "\n".join(sorted(found)).encode()
                    ).hexdigest()
                    result["package_count"] = len(found)
                report["results"].append(result)
                print(f"G144_ORIGINAL_{mode.upper()}_OUTPUT_BEGIN", flush=True)
                print(data[-125000:], flush=True)
                print(f"G144_ORIGINAL_{mode.upper()}_OUTPUT_END", flush=True)

            build_gate = home / "build.gate"
            with (home / "build.log").open("wb") as out:
                build = subprocess.Popen(
                    [sys.executable, "-B", str(Path(__file__)), "--worker", "build", str(build_gate)],
                    cwd=ROOT, env=os.environ.copy(),
                    stdout=out, stderr=subprocess.STDOUT,
                )
            workers.append(build)
            meter.assign(build)
            build_gate.write_text("assigned\n", encoding="utf-8")
            while build.poll() is None:
                peak = max(peak, meter.peak())
                if peak > MAX_MEMORY:
                    raise ValueError("G144_WINDOWS_JOB_MEMORY_CAP_EXCEEDED")
                if time.monotonic() - start > MAX_SECONDS:
                    raise ValueError("G144_ORIGINAL_WINDOWS_GO_TIMEOUT")
                time.sleep(0.1)
            peak = max(peak, meter.peak())
            if build.wait(timeout=10) != 0:
                raise ValueError("G144_ORIGINAL_BUILD_FAILED")
            build_data = (home / "build.log").read_bytes()
            report["results"].append({
                "mode": "build", "exit_code": build.returncode,
                "log_sha256": hashlib.sha256(build_data).hexdigest(),
            })
            print("G144_ORIGINAL_BUILD_OUTPUT_BEGIN", flush=True)
            print(build_data.decode("utf-8", errors="replace")[-125000:], flush=True)
            print("G144_ORIGINAL_BUILD_OUTPUT_END", flush=True)
            if not 0 < peak <= MAX_MEMORY:
                raise ValueError("G144_WINDOWS_JOB_PEAK_UNVERIFIED")
            stable(sha)
            report.update(
                status="PASS_FULL_ORIGINAL_WINDOWS_GO_DEV",
                clean_after=True,
                original_stage_seconds=round(time.monotonic()-start, 6),
                process_tree_peak_commit_bytes=peak,
            )
            return 0
    except BaseException as exc:
        failed = True
        report["status"] = "FAIL_CLOSED"
        report["error_type"] = type(exc).__name__
        report["error_code"] = str(exc)[:180]
        raise
    finally:
        if failed and meter is not None:
            terminate_job(meter)
        for proc in workers:
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=20)
        if meter is not None:
            meter.close()
        report["elapsed_seconds"] = round(time.monotonic()-start, 6)
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print("FORGE_RAR_G144=" + report["status"], flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        sys.exit(worker(sys.argv[2], Path(sys.argv[3])))
    sys.exit(main())
