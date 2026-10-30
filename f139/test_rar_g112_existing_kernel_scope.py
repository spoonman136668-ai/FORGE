"""RAR-G112: bounded real OS counter readback, not a native training meter.

Read only the current GitHub runner's existing cgroup/job. Never create,
assign, reset or alter job objects, cgroups, processes or original-world state.
An inherited/shared OS scope cannot be identified with one experiment.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import sys
import unittest


def parsed_linux_cpu_stat(raw: str) -> dict[str, int]:
    """Linux cgroup v2 counter validation; reject duplicates/ambiguous units."""
    fields: dict[str, int] = {}
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) != 2 or parts[0] in fields or not parts[1].isascii() or not parts[1].isdecimal():
            raise ValueError("RAR_G112_CGROUP_CPU_STAT_INVALID")
        fields[parts[0]] = int(parts[1])
    if "usage_usec" not in fields or fields["usage_usec"] < 0:
        raise ValueError("RAR_G112_CGROUP_CPU_USAGE_MISSING")
    return fields


def linux_current_scope() -> dict:
    out = {
        "platform": sys.platform, "method": "linux_cgroup_v2_read_only",
        "counter_available": False, "current_process_direct_member": False,
        "cpu_usage_usec": None, "memory_current_bytes": None,
        "memory_peak_bytes": None, "direct_process_count": None,
        "cpu_scope": "CGROUP_INCLUDING_DESCENDANTS_AND_OTHER_MEMBERS",
        "memory_scope": "CGROUP_CHARGED_MEMORY_NOT_PROCESS_TREE_RSS",
        "exclusive_experiment_membership_verified": False,
        "short_lived_descendants_accounted_for_exclusively": False,
        "complete_native_training_cpu_rss_qualified": False,
        "scientific_first_use_authorized": False,
        "process_created": False,
    }
    if not sys.platform.startswith("linux"):
        return out
    root = Path("/sys/fs/cgroup")
    if not (root / "cgroup.controllers").is_file():
        return out
    try:
        memberships = [
            line[3:] for line in Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
            if line.startswith("0::/")
        ]
        if len(memberships) != 1:
            return out
        base = root.resolve(strict=True)
        group = (base / memberships[0].lstrip("/")).resolve(strict=True)
        if not group.is_relative_to(base):
            return out
        cpu = parsed_linux_cpu_stat((group / "cpu.stat").read_text(encoding="ascii"))
        current_raw = (group / "memory.current").read_text(encoding="ascii").strip()
        peak_raw = (group / "memory.peak").read_text(encoding="ascii").strip()
        raw_procs = (group / "cgroup.procs").read_text(encoding="ascii").splitlines()
        if not current_raw.isascii() or not current_raw.isdecimal():
            return out
        if not peak_raw.isascii() or not peak_raw.isdecimal():
            return out
        if not all(p.isascii() and p.isdecimal() for p in raw_procs):
            return out
        if int(peak_raw) < int(current_raw):
            return out
        out["cpu_usage_usec"] = cpu["usage_usec"]
        out["memory_current_bytes"] = int(current_raw)
        out["memory_peak_bytes"] = int(peak_raw)
        out["direct_process_count"] = len(raw_procs)
        out["current_process_direct_member"] = str(os.getpid()) in raw_procs
        out["counter_available"] = out["current_process_direct_member"]
    except (OSError, ValueError, UnicodeError):
        return out
    return out


def windows_current_scope() -> dict:
    out = {
        "platform": sys.platform, "method": "windows_immediate_job_accounting_read_only",
        "counter_available": False, "current_process_in_job": False,
        "total_user_100ns": None, "total_kernel_100ns": None,
        "active_processes": None, "total_processes": None,
        "cpu_scope": "IMMEDIATE_EXISTING_JOB_INCLUDING_PRIOR_MEMBERS",
        "memory_scope": "WINDOWS_JOB_PEAK_COMMIT_NOT_PHYSICAL_RSS",
        "exclusive_experiment_membership_verified": False,
        "short_lived_descendants_accounted_for_exclusively": False,
        "complete_native_training_cpu_rss_qualified": False,
        "scientific_first_use_authorized": False,
        "process_created": False,
    }
    if sys.platform != "win32":
        return out
    from ctypes import wintypes

    class BasicAccounting(ctypes.Structure):
        _fields_ = [
            ("TotalUserTime", ctypes.c_longlong),
            ("TotalKernelTime", ctypes.c_longlong),
            ("ThisPeriodTotalUserTime", ctypes.c_longlong),
            ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
            ("TotalPageFaultCount", wintypes.DWORD),
            ("TotalProcesses", wintypes.DWORD),
            ("ActiveProcesses", wintypes.DWORD),
            ("TotalTerminatedProcesses", wintypes.DWORD),
        ]

    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.argtypes = []
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.IsProcessInJob.argtypes = [
            wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)
        ]
        kernel.IsProcessInJob.restype = wintypes.BOOL
        inside = wintypes.BOOL()
        if not kernel.IsProcessInJob(kernel.GetCurrentProcess(), None, ctypes.byref(inside)):
            return out
        out["current_process_in_job"] = bool(inside.value)
        if not inside.value:
            return out
        kernel.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)
        ]
        kernel.QueryInformationJobObject.restype = wintypes.BOOL
        info = BasicAccounting()
        size = wintypes.DWORD()
        if not kernel.QueryInformationJobObject(
            None, 1, ctypes.byref(info), ctypes.sizeof(info), ctypes.byref(size)
        ):
            return out
        if (size.value != ctypes.sizeof(info) or
                info.TotalUserTime < 0 or info.TotalKernelTime < 0 or
                info.TotalProcesses < info.ActiveProcesses):
            return out
        out["total_user_100ns"] = int(info.TotalUserTime)
        out["total_kernel_100ns"] = int(info.TotalKernelTime)
        out["active_processes"] = int(info.ActiveProcesses)
        out["total_processes"] = int(info.TotalProcesses)
        out["counter_available"] = True
    except (OSError, AttributeError, ValueError):
        return out
    return out


class RARG112KernelCounterScope(unittest.TestCase):
    def test_real_readback_is_nonexecuting_and_never_science(self):
        actual = windows_current_scope() if sys.platform == "win32" else linux_current_scope()
        self.assertFalse(actual["exclusive_experiment_membership_verified"])
        self.assertFalse(actual["short_lived_descendants_accounted_for_exclusively"])
        self.assertFalse(actual["complete_native_training_cpu_rss_qualified"])
        self.assertFalse(actual["scientific_first_use_authorized"])
        self.assertFalse(actual["process_created"])
        self.assertIn("INCLUDING", actual["cpu_scope"])
        self.assertNotEqual(actual["memory_scope"], "ISOLATED_PHYSICAL_TREE_RSS")
        if actual["counter_available"]:
            if sys.platform == "win32":
                self.assertGreaterEqual(actual["total_user_100ns"], 0)
                self.assertGreaterEqual(actual["total_kernel_100ns"], 0)
                self.assertGreaterEqual(actual["total_processes"], actual["active_processes"])
            else:
                self.assertGreaterEqual(actual["cpu_usage_usec"], 0)
                self.assertGreater(actual["memory_peak_bytes"], 0)
                self.assertGreaterEqual(actual["memory_peak_bytes"], actual["memory_current_bytes"])
                self.assertTrue(actual["current_process_direct_member"])
        print("RAR_G112_EXISTING_KERNEL_SCOPE=" + json.dumps(actual, sort_keys=True))

    def test_duplicate_or_invalid_linux_cpu_fields_fail_closed(self):
        for raw in ("", "user_usec 1\n", "usage_usec -1\n",
                    "usage_usec one\n", "usage_usec 1\nusage_usec 2\n",
                    "usage_usec 1 2\n", "usage_usec 1.1\n"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parsed_linux_cpu_stat(raw)
        self.assertEqual(parsed_linux_cpu_stat(
            "usage_usec 101\nuser_usec 60\nsystem_usec 41\n"
        )["usage_usec"], 101)

    def test_shared_cgroup_delta_is_not_exact_training_cost(self):
        parent, other_runner, training = 10, 30, 15
        observed_usage_delta = parent + other_runner + training
        self.assertEqual(observed_usage_delta, 55)
        self.assertNotEqual(observed_usage_delta, training)

    def test_job_cpu_cumulative_is_not_isolated_experiment(self):
        prior_job_cpu_100ns, new_job_cpu_100ns = 400, 950
        eligible_training_cpu_100ns = 300
        self.assertEqual(new_job_cpu_100ns - prior_job_cpu_100ns, 550)
        self.assertNotEqual(550, eligible_training_cpu_100ns)

    def test_kernel_charged_memory_is_not_physical_process_rss(self):
        actual_process_rss = 100
        cgroup_file_cache = 75
        self.assertEqual(actual_process_rss + cgroup_file_cache, 175)
        self.assertNotEqual(175, actual_process_rss)


if __name__ == "__main__":
    unittest.main()
