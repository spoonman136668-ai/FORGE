"""RAR-G111: read-only kernel accounting feasibility; never a training meter.

Native development original owner and bounded sampler remain unmodified.
The probes report host capabilities without creating jobs, cgroups, children,
original-world interactions or granting scientific / execution authority.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import sys
import unittest


def linux_cgroup_readonly_probe() -> dict:
    result = {"platform": sys.platform, "probe": "linux_cgroup_v2_read_only",
              "cgroup_v2": False, "cpu_stat_readable": False,
              "memory_peak_readable": False, "memory_current_readable": False,
              "mount_readonly": None, "current_cgroup_resolved": False,
              "kernel_complete_tree_qualified": False,
              "native_training_proficiency_qualified": False,
              "first_use_authorized": False, "process_spawned": False}
    if not sys.platform.startswith("linux"):
        return result
    root = Path("/sys/fs/cgroup")
    result["cgroup_v2"] = (root / "cgroup.controllers").is_file()
    if not result["cgroup_v2"]:
        return result
    try:
        group_lines = Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
        matches = [line[3:] for line in group_lines if line.startswith("0::/")]
        if len(matches) != 1:
            return result
        base = root.resolve(strict=True)
        current = (base / matches[0].lstrip("/")).resolve(strict=True)
        if not current.is_relative_to(base):
            return result
        result["current_cgroup_resolved"] = True
        result["mount_readonly"] = bool(os.statvfs(current).f_flag & getattr(os, "ST_RDONLY", 1))
        for name, key in (("cpu.stat", "cpu_stat_readable"),
                          ("memory.peak", "memory_peak_readable"),
                          ("memory.current", "memory_current_readable")):
            try:
                payload = (current / name).read_text(encoding="ascii")
                if name == "cpu.stat":
                    values = {}
                    for line in payload.splitlines():
                        label, number = line.split()
                        if not number.isdecimal():
                            raise ValueError("non-numeric cgroup CPU field")
                        values[label] = int(number)
                    result[key] = ("usage_usec" in values and
                                   values["usage_usec"] >= 0)
                else:
                    result[key] = payload.strip().isdecimal()
            except (OSError, ValueError, UnicodeError):
                result[key] = False
    except (OSError, ValueError, UnicodeError):
        return result
    return result


def windows_job_readonly_probe() -> dict:
    result = {"platform": sys.platform, "probe": "windows_job_object_api_read_only",
              "job_api_exported": False, "current_process_job_state_readable": False,
              "current_process_in_job": None,
              "kernel_complete_tree_qualified": False,
              "native_training_proficiency_qualified": False,
              "first_use_authorized": False, "process_spawned": False}
    if sys.platform != "win32":
        return result
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    result["job_api_exported"] = all(
        hasattr(kernel, name) for name in ("CreateJobObjectW", "QueryInformationJobObject",
                                           "IsProcessInJob", "GetProcessTimes"))
    if not result["job_api_exported"]:
        return result
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.argtypes = []
    kernel.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE,
                                    ctypes.POINTER(wintypes.BOOL)]
    kernel.IsProcessInJob.restype = wintypes.BOOL
    inside = wintypes.BOOL()
    ok = kernel.IsProcessInJob(kernel.GetCurrentProcess(), None,
                               ctypes.byref(inside))
    result["current_process_job_state_readable"] = bool(ok)
    if ok:
        result["current_process_in_job"] = bool(inside.value)
    return result


class G111ReadOnlyResourceFeasibility(unittest.TestCase):
    def test_actual_host_reports_capabilities_without_claiming_measurement(self):
        result = (windows_job_readonly_probe() if sys.platform == "win32"
                  else linux_cgroup_readonly_probe())
        self.assertIs(result["process_spawned"], False)
        self.assertIs(result["first_use_authorized"], False)
        self.assertIs(result["kernel_complete_tree_qualified"], False)
        self.assertIs(result["native_training_proficiency_qualified"], False)
        self.assertIn(result["platform"], ("win32", "linux", "linux2"))
        print("RAR_G111_READ_ONLY_CAPABILITY=" + json.dumps(result, sort_keys=True))

    def test_short_lived_descendant_can_escape_periodic_samples(self):
        sample_times_ms = (0, 20, 40)
        short_lived_grandchild = {"start_ms": 3, "exit_ms": 9,
                                  "cpu_ms": 4, "rss_bytes": 4_000_000}
        seen = [t for t in sample_times_ms if
                short_lived_grandchild["start_ms"] <= t < short_lived_grandchild["exit_ms"]]
        self.assertEqual(seen, [])
        self.assertGreater(short_lived_grandchild["cpu_ms"], 0)
        self.assertGreater(short_lived_grandchild["rss_bytes"], 0)
        print("RAR_G111_PERIODIC_20MS_SHORT_CHILD_CAPTURE=FAIL_CLOSED_UNVERIFIED")

    def test_nested_cpu_receipt_must_not_be_added_twice(self):
        exclusive_cpu_ms = {"root": 10, "child": 20, "grandchild": 30}
        correct_total = sum(exclusive_cpu_ms.values())
        child_inclusive_receipt = 20 + 30
        incorrect = correct_total + child_inclusive_receipt
        self.assertEqual(correct_total, 60)
        self.assertEqual(incorrect, 110)
        self.assertNotEqual(correct_total, incorrect)

    def test_individual_peaks_do_not_prove_concurrent_tree_peak(self):
        simultaneous_rss_snapshots = (
            {"root": 10, "child_a": 90, "child_b": 0},
            {"root": 10, "child_a": 0, "child_b": 100},
        )
        true_sampled_simultaneous_peak = max(sum(x.values()) for x in simultaneous_rss_snapshots)
        sum_of_individual_peaks = sum(max(x[k] for x in simultaneous_rss_snapshots)
                                      for k in ("root", "child_a", "child_b"))
        self.assertEqual(true_sampled_simultaneous_peak, 110)
        self.assertEqual(sum_of_individual_peaks, 200)
        self.assertNotEqual(true_sampled_simultaneous_peak, sum_of_individual_peaks)

    def test_existing_worker_sampler_explicitly_denies_kernel_completeness(self):
        from f139 import nci04_v3_bounded_resource as sampler
        self.assertEqual(sampler.SAMPLE_PERIOD_SECONDS, 0.02)
        self.assertIn("Not a scientific", sampler.__doc__)
        import inspect
        source = inspect.getsource(sampler.bounded_sampled_process)
        self.assertIn("psutil-sampled-process-tree-v1", source)
        self.assertNotIn("COMPLETE_TREE_KERNEL_MEASURED", source)


if __name__ == "__main__":
    unittest.main()
