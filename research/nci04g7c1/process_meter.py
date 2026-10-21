#!/usr/bin/env python3
"""NCI-04G7C-1: Linux process-group resource meter, engineering smoke only.

This is NOT a scientific authority, a comparator launcher, or a complete
process-tree peak RSS witness. CPU is reaped with wait4 (including reaped
children); RSS is sampled from /proc and can miss short-lived peaks. A process
that detaches from the tracked group is out of scope. Report limitations in
every result; never turn a meter PASS into resource nonregression acceptance.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import tempfile
import time

SCHEMA = "forge.nci04g7c1.linux-process-resource-smoke.v1"

class MeterBlocked(ValueError):
    pass

def require(cond: bool, reason: str) -> None:
    if not cond:
        raise MeterBlocked("G7C1_METER_" + reason)

def group_rss_bytes(pgid: int) -> tuple[int,int]:
    """Observe simultaneous resident bytes across visible group members.

    The values are sampled; they are NOT verified complete peak memory.
    """
    total = 0
    members = 0
    for folder in Path("/proc").iterdir():
        if not folder.name.isdigit():
            continue
        try:
            stat = (folder / "stat").read_text()
            index = stat.rfind(")")
            if index < 0:
                continue
            fields = stat[index+2:].split()
            if len(fields) < 22 or int(fields[2]) != pgid:
                continue
            rss_pages = max(0, int(fields[21]))
            total += rss_pages * os.sysconf("SC_PAGE_SIZE")
            members += 1
        except (OSError, ValueError, ProcessLookupError, PermissionError):
            # A disappearing or inaccessible process invalidates completeness;
            # this probe never claims a complete peak anyway.
            continue
    return total, members

def command_receipt(argv: list[str], cwd: Path, *, timeout_s: float=8.0,
                    sample_interval_s: float=0.002) -> dict:
    require(platform.system() == "Linux" and Path("/proc").is_dir(),
            "LINUX_PROC_REQUIRED")
    require(type(argv) is list and 1 <= len(argv) <= 16
            and all(type(x) is str and x and len(x) <= 1024 for x in argv),
            "INVALID_ARGV")
    require(type(cwd) is Path and cwd.is_dir() and not cwd.is_symlink(),
            "INVALID_CWD")
    require(type(timeout_s) in (float,int) and 0.1 <= timeout_s <= 60.0
            and type(sample_interval_s) in (float,int)
            and 0.001 <= sample_interval_s <= 0.1,
            "METER_BOUNDS")
    started = time.perf_counter_ns()
    peak_group = 0
    max_visible = 0
    observed_samples = 0
    with tempfile.TemporaryFile(mode="w+b") as output:
        process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=output, stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE":"1",
                 "PYTHONNOUSERSITE":"1", "GOWORK":"off", "GOPROXY":"off",
                 "GOSUMDB":"off", "GOTOOLCHAIN":"local"})
        try:
            while True:
                rss, members = group_rss_bytes(process.pid)
                peak_group = max(peak_group, rss)
                max_visible = max(max_visible, members)
                observed_samples += 1
                waited, status, usage = os.wait4(process.pid, os.WNOHANG)
                if waited == process.pid:
                    exit_code = os.waitstatus_to_exitcode(status)
                    process.returncode = exit_code
                    break
                if (time.perf_counter_ns() - started) / 1e9 > timeout_s:
                    raise MeterBlocked("COMMAND_TIMEOUT")
                time.sleep(sample_interval_s)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.wait4(process.pid, 0)
            except ChildProcessError:
                pass
            process.returncode = -signal.SIGKILL
            raise
        output.seek(0)
        result = output.read(256*1024+1)
    require(len(result) <= 256*1024, "OUTPUT_TOO_LARGE")
    require(exit_code == 0, "CHILD_NONZERO_" + str(exit_code))
    wall = time.perf_counter_ns() - started
    return {
        "schema": SCHEMA,
        "command_sha256": hashlib.sha256(json.dumps(
            argv, separators=(",",":"), ensure_ascii=True).encode()).hexdigest(),
        "stdout_stderr_sha256": hashlib.sha256(result).hexdigest(),
        "exit_code":exit_code, "elapsed_wall_ns":wall,
        "reaped_group_user_system_cpu_ns":int(round(
            (usage.ru_utime+usage.ru_stime)*1e9)),
        "wait4_lineage_max_rss_kib":usage.ru_maxrss,
        "sampled_process_group_peak_rss_bytes_lower_bound":peak_group,
        "sampled_processes_max_simultaneous":max_visible,
        "sample_count":observed_samples,
        "total_executed_work_claim":"ONLY_THE_SINGLE_MEASURED_COMMAND",
        "process_group_boundary":"CHILDREN_THAT_REMAIN_IN_LEADER_PROCESS_GROUP",
        "child_escape_attested":False,
        "peak_aggregate_rss_complete":False,
        "cpu_ancestry_receipt":"OS_WAIT4_REAPED_DESCENDANTS_ONLY",
        "all_in_resource_parity_qualified":False,
        "scientific_first_use":False,
        "classification":"PARTIAL_DEVELOPMENT_RESOURCE_DIAGNOSTIC_ONLY",
    }
