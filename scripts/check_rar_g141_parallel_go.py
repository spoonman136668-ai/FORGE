"""RAR-G141: run both ORIGINAL full Linux Go test suites concurrently.

Engineering-only orchestration, no new tests, test filters, cache, owner, or
scientific execution. Each original command keeps its frozen Go flags.
Fail closed on any missing package, subprocess failure, source drift, timeout,
or unverified Linux cgroup memory.
"""
from __future__ import annotations

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

from check_rar_g145_pr_scope import admit_original_pr, negative_controls

ROOT = Path(__file__).resolve().parents[1]
REPO = "spoonman136668-ai/FORGE"
MAX_SECONDS = 180
MAX_CGROUP_BYTES = 4 * (1024**3)
PACKAGE_RE = re.compile(r"^(?:ok|\?)\s+(\S+)\s+", re.MULTILINE)


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, timeout=45
    ).strip()


def exact_source(source_sha: str) -> None:
    if git("rev-parse", "HEAD") != source_sha:
        raise ValueError("G141_SOURCE_SHA_DRIFT")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("G141_WORKTREE_NOT_CLEAN")


def parse_packages(log: str) -> set[str]:
    names = PACKAGE_RE.findall(log)
    if len(names) != len(set(names)):
        raise ValueError("G141_DUPLICATE_PACKAGE_RESULT")
    return set(names)


def memory_files() -> tuple[Path, Path]:
    candidates = [
        line.strip().split(":", 2)
        for line in Path("/proc/self/cgroup").read_text().splitlines()
    ]
    roots = [x[2] for x in candidates if len(x) == 3 and x[0] == "0" and x[1] == ""]
    if len(roots) != 1:
        raise ValueError("G141_CGROUP_V2_IDENTITY_UNVERIFIED")
    base = Path("/sys/fs/cgroup").resolve()
    folder = (base / roots[0].lstrip("/")).resolve()
    if not folder.is_relative_to(base):
        raise ValueError("G141_CGROUP_ROOT_ESCAPE")
    member_file = folder / "cgroup.procs"
    if str(os.getpid()) not in member_file.read_text().splitlines():
        raise ValueError("G141_CGROUP_PROCESS_MEMBERSHIP_UNVERIFIED")
    current, peak = folder / "memory.current", folder / "memory.peak"
    for x in (current, peak):
        if not x.is_file() or not x.read_text().strip().isdigit():
            raise ValueError("G141_CGROUP_MEMORY_UNVERIFIED")
    return current, peak


def checked_number(path: Path) -> int:
    s = path.read_text().strip()
    if not s.isdecimal():
        raise ValueError("G141_CGROUP_MEMORY_UNVERIFIED")
    return int(s)


def kill_children(children: list[subprocess.Popen]) -> None:
    for proc in children:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    for proc in children:
        try:
            proc.wait(timeout=12)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=12)


def partial_failure_log(path: Path, expected_packages: set[str]) -> tuple[dict, str]:
    """Report bounded progress and a short log tail without rerunning tests."""
    size = path.stat().st_size
    completed: set[str] = set()
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            match = PACKAGE_RE.match(line)
            if match:
                completed.add(match.group(1))
    with path.open("rb") as stream:
        stream.seek(max(0, size - 8192))
        tail = stream.read().decode("utf-8", errors="replace")
    return dict(
        output_bytes=size,
        completed_package_count=len(completed),
        completed_packages=sorted(completed),
        pending_packages=sorted(expected_packages - completed),
        tail_limit_bytes=8192,
    ), tail


def partial_log_negative_control() -> None:
    with tempfile.TemporaryDirectory(prefix="rar-g141-partial-control-") as tmp:
        path = Path(tmp) / "probe.log"
        path.write_text(
            "ok  example/a 0.01s\n?  example/b [no test files]\n"
            "PARTIAL-PACKAGE-STILL-RUNNING\n",
            encoding="utf-8",
        )
        result, tail = partial_failure_log(path, {"example/a", "example/b", "example/c"})
        if (result["completed_packages"] != ["example/a", "example/b"]
                or result["pending_packages"] != ["example/c"]
                or not tail.endswith("PARTIAL-PACKAGE-STILL-RUNNING\n")):
            raise ValueError("G160_PARTIAL_LOG_NEGATIVE_CONTROL_FAILED")


def emit_partial_failure_evidence(
    logs: list[tuple[str, Path, object]],
    children: list[subprocess.Popen],
    expected_packages: set[str],
    elapsed: float,
) -> dict:
    evidence = {}
    for (label, path, handle), child in zip(logs, children):
        try:
            handle.flush()
            details, tail = partial_failure_log(path, expected_packages)
            details.update(exit_code=child.poll(), elapsed_seconds=round(elapsed, 6))
            evidence[label] = details
            print("G160_PARTIAL_" + label.upper() + "="
                  + json.dumps(details, sort_keys=True), flush=True)
            print("G160_" + label.upper() + "_TAIL_BEGIN", flush=True)
            print(tail, flush=True)
            print("G160_" + label.upper() + "_TAIL_END", flush=True)
        except Exception as exc:
            evidence[label] = dict(diagnostic_available=False, error_class=type(exc).__name__)
            print("G160_PARTIAL_" + label.upper() + "_UNAVAILABLE="
                  + type(exc).__name__, flush=True)
    return evidence


def main() -> int:
    if (
        sys.platform != "linux"
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != REPO
        or os.environ.get("RUNNER_OS") != "Linux"
        or not os.environ.get("RUNNER_TEMP")
    ):
        raise ValueError("G141_ORIGINAL_HOSTED_LINUX_ONLY")
    event = os.environ.get("GITHUB_EVENT_NAME")
    if event == "pull_request":
        if os.environ.get("GITHUB_BASE_REF") != "main":
            raise ValueError("G141_PR_SCOPE_INVALID")
    elif event == "push":
        if os.environ.get("GITHUB_REF") != "refs/heads/main":
            raise ValueError("G141_PUSH_SCOPE_INVALID")
    else:
        raise ValueError("G141_GITHUB_EVENT_UNAUTHORIZED")

    sha = git("rev-parse", "HEAD")
    if sha != os.environ.get("FORGE_G141_HEAD"):
        raise ValueError("G141_EXPECTED_SOURCE_MISMATCH")
    exact_source(sha)
    negative_controls()
    if event == "pull_request":
        admission = admit_original_pr(sha, git)
        print("G145_PR_ADMISSION=" + admission, flush=True)
    expected_list = subprocess.check_output(
        ["go", "list", "./..."], text=True, cwd=ROOT, timeout=80
    ).splitlines()
    expected_packages = set(expected_list)
    if len(expected_packages) != len(expected_list) or len(expected_packages) < 130:
        raise ValueError("G141_EXPECTED_PACKAGE_INVENTORY_INVALID")

    # Negative controls for the package parser, not for test-result selection.
    if parse_packages("ok  example/a 0.03s\n?  example/b [no test files]\n") != {
        "example/a", "example/b"
    }:
        raise ValueError("G141_RESULT_PARSER_FAILED")
    try:
        parse_packages("ok  example/a 0.03s\nok  example/a 0.02s\n")
    except ValueError:
        pass
    else:
        raise ValueError("G141_NEGATIVE_PARSER_CONTROL_FAILED")
    partial_log_negative_control()

    current_file, peak_file = memory_files()
    starting_current = checked_number(current_file)
    starting_peak = checked_number(peak_file)
    if starting_peak < starting_current or starting_peak > MAX_CGROUP_BYTES:
        raise ValueError("G141_CGROUP_PRECONDITION_EXCEEDS_CAP")

    receipt_path = Path(os.environ["RUNNER_TEMP"]) / "rar-g141-parallel-original-go.json"
    report = dict(
        schema="forge.rar-g141.parallel-original-go.v1",
        source_sha=sha,
        source_tree=git("rev-parse", "HEAD^{tree}"),
        source_clean_before=True,
        go_version=subprocess.check_output(["go", "version"], text=True, cwd=ROOT).strip(),
        package_count=len(expected_packages),
        package_names_sha256=hashlib.sha256(
            "\n".join(sorted(expected_packages)).encode("utf-8")
        ).hexdigest(),
        runner_os=os.environ.get("RUNNER_OS"),
        runner_image=os.environ.get("ImageOS"),
        image_version=os.environ.get("ImageVersion"),
        host_cpu_count=os.cpu_count(),
        goflags=os.environ.get("GOFLAGS"),
        gomaxprocs=os.environ.get("GOMAXPROCS"),
        gomemlimit=os.environ.get("GOMEMLIMIT"),
        original_full_regular=["go", "test", "-count=1", "./..."],
        original_full_race=["go", "test", "-race", "-count=1", "./..."],
        original_race_goflags="-p=4",
        full_package_identity_required=True,
        go_test_result_cache_disabled=True,
        concurrent_same_repository_source=True,
        cgroup_starting_current_bytes=starting_current,
        cgroup_starting_peak_bytes=starting_peak,
        cgroup_limit_bytes=MAX_CGROUP_BYTES,
        cgroup_scope="SHARED_READ_ONLY_V2_WORKER_CGROUP",
        result="INVALID",
        children=[],
    )
    children: list[subprocess.Popen] = []
    run_start = time.perf_counter()

    try:
        with tempfile.TemporaryDirectory(
            prefix="rar-g141-go-", dir=os.environ["RUNNER_TEMP"]
        ) as tmp:
            directory = Path(tmp)
            logs = []
            for label, command, extra_env in (
                ("regular", ["go", "test", "-count=1", "./..."], {}),
                ("race", ["go", "test", "-race", "-count=1", "./..."], {"GOFLAGS": "-p=4"}),
            ):
                logfile = directory / f"{label}.log"
                handle = logfile.open("wb")
                logs.append((label, logfile, handle))
                child = subprocess.Popen(
                    command,
                    cwd=ROOT,
                    env={**os.environ, **extra_env, "GOTOOLCHAIN": "local"},
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                children.append(child)
            sampled_peak = starting_current
            try:
                while True:
                    sampled = checked_number(current_file)
                    sampled_peak = max(sampled_peak, sampled)
                    if sampled_peak > MAX_CGROUP_BYTES:
                        raise ValueError("G141_CGROUP_MEMORY_CAP_EXCEEDED")
                    exits = [x.poll() for x in children]
                    if any(x is not None and x != 0 for x in exits):
                        raise ValueError("G141_ORIGINAL_GO_TEST_OR_RACE_FAILED")
                    if all(x is not None for x in exits):
                        break
                    if time.perf_counter() - run_start > MAX_SECONDS:
                        raise ValueError("G141_PARALLEL_GO_TIMEOUT")
                    time.sleep(0.10)
            except BaseException:
                kill_children(children)
                report["failure_diagnostics"] = emit_partial_failure_evidence(
                    logs, children, expected_packages,
                    time.perf_counter() - run_start,
                )
                raise
            for _, _, handle in logs:
                handle.close()
            full_peak = checked_number(peak_file)
            if full_peak < sampled_peak or full_peak > MAX_CGROUP_BYTES:
                raise ValueError("G141_CGROUP_PEAK_INVALID_OR_EXCEEDS_CAP")
            for (label, path, _), child in zip(logs, children):
                data = path.read_text(encoding="utf-8", errors="replace")
                actual = parse_packages(data)
                if actual != expected_packages:
                    raise ValueError(
                        f"G141_{label.upper()}_PACKAGE_PARITY_MISMATCH: "
                        f"expected={len(expected_packages)} actual={len(actual)}"
                    )
                print(f"G141_ORIGINAL_{label.upper()}_GO_RESULTS_BEGIN", flush=True)
                print(data[-120000:], flush=True)
                print(f"G141_ORIGINAL_{label.upper()}_GO_RESULTS_END", flush=True)
                report["children"].append(
                    dict(
                        mode=label,
                        exit_code=child.returncode,
                        package_count=len(actual),
                        package_names_sha256=hashlib.sha256(
                            "\n".join(sorted(actual)).encode("utf-8")
                        ).hexdigest(),
                        output_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
                )
            exact_source(sha)
            report.update(
                result="PASS_ORIGINAL_PARALLEL_GO_DEV",
                source_clean_after=True,
                full_parallel_go_seconds=round(time.perf_counter() - run_start, 6),
                cgroup_sampled_peak_current_bytes=sampled_peak,
                cgroup_cumulative_peak_bytes=full_peak,
            )
            return 0
    except BaseException as exc:
        report["result"] = "FAIL_CLOSED"
        report["error_class"] = type(exc).__name__
        report["error_code"] = str(exc)[:150]
        raise
    finally:
        kill_children(children)
        report["elapsed_seconds"] = round(time.perf_counter() - run_start, 6)
        receipt_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        print("FORGE_RAR_G141=" + report["result"], flush=True)


if __name__ == "__main__":
    sys.exit(main())
