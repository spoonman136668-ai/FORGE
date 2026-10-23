"""Native, source-only process resource accounting for Q21.

Captures measured process counters without creating data, dispatching tasks or
claiming experimental acceptance. Process high-water RSS is cumulative; it is
NOT mislabeled as an isolated per-model peak.
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import sys
import time


class ResourceUnavailable(RuntimeError):
    pass


def native_peak_rss_bytes() -> int:
    """OS-reported process peak resident/working-set bytes; fail closed."""
    if sys.platform.startswith("linux"):
        import resource
        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    elif sys.platform == "win32":
        from ctypes import wintypes
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.argtypes = []
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(
                kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ResourceUnavailable("Q21_WINDOWS_GETPROCESSMEMORYINFO_FAILED")
        value = int(counters.PeakWorkingSetSize)
    else:
        raise ResourceUnavailable("Q21_NATIVE_RSS_UNSUPPORTED_PLATFORM")
    if value <= 0:
        raise ResourceUnavailable("Q21_NATIVE_RSS_UNAVAILABLE")
    return value


def process_io_bytes() -> dict:
    """OS process I/O counters, not an assertion that all I/O was persisted."""
    if sys.platform.startswith("linux"):
        try:
            data = {}
            with open("/proc/self/io", encoding="ascii") as handle:
                for line in handle:
                    key, number = line.split(":", 1)
                    data[key] = int(number.strip())
            return {
                "read_transfer_bytes": data["rchar"],
                "write_transfer_bytes": data["wchar"],
                "disk_read_bytes": data["read_bytes"],
                "disk_write_bytes": data["write_bytes"],
                "measurement_source": "linux_proc_self_io",
            }
        except (OSError, ValueError, KeyError) as error:
            raise ResourceUnavailable("Q21_LINUX_PROC_IO_UNAVAILABLE") from error
    if sys.platform == "win32":
        class IOCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.argtypes = []
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        kernel.GetProcessIoCounters.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(IOCounters)
        ]
        kernel.GetProcessIoCounters.restype = ctypes.c_int
        counters = IOCounters()
        if not kernel.GetProcessIoCounters(
                kernel.GetCurrentProcess(), ctypes.byref(counters)):
            raise ResourceUnavailable("Q21_WINDOWS_GETPROCESSIOCOUNTERS_FAILED")
        return {
            "read_transfer_bytes": int(counters.ReadTransferCount),
            "write_transfer_bytes": int(counters.WriteTransferCount),
            "disk_read_bytes": None,
            "disk_write_bytes": None,
            "measurement_source": "windows_getprocessiocounters",
        }
    raise ResourceUnavailable("Q21_NATIVE_IO_UNSUPPORTED_PLATFORM")


def snapshot() -> dict:
    return {
        "process_cpu_ns": time.process_time_ns(),
        "process_peak_rss_bytes": native_peak_rss_bytes(),
        "process_io": process_io_bytes(),
        "platform": platform.system(),
    }


def measured_delta(start: dict, stop: dict, stage: str) -> dict:
    if not stage or not isinstance(stage, str):
        raise ResourceUnavailable("Q21_RESOURCE_STAGE_REQUIRED")
    if start["platform"] != stop["platform"]:
        raise ResourceUnavailable("Q21_RESOURCE_CROSS_PLATFORM_MIX")
    if stop["process_cpu_ns"] < start["process_cpu_ns"]:
        raise ResourceUnavailable("Q21_CPU_COUNTER_NONMONOTONIC")
    if stop["process_peak_rss_bytes"] < start["process_peak_rss_bytes"]:
        raise ResourceUnavailable("Q21_RSS_COUNTER_NONMONOTONIC")
    earlier, later = start["process_io"], stop["process_io"]
    if earlier["measurement_source"] != later["measurement_source"]:
        raise ResourceUnavailable("Q21_IO_MEASUREMENT_SOURCE_DRIFT")
    changes = {}
    for key in ("read_transfer_bytes", "write_transfer_bytes",
                "disk_read_bytes", "disk_write_bytes"):
        a, b = earlier[key], later[key]
        if a is None or b is None:
            changes[key] = None
        elif b < a:
            raise ResourceUnavailable("Q21_IO_COUNTER_NONMONOTONIC")
        else:
            changes[key] = b - a
    return {
        "schema": "forge.q21.native-process-resource.v1",
        "stage": stage,
        "process_cpu_seconds": (stop["process_cpu_ns"] -
                                start["process_cpu_ns"]) / 1e9,
        "process_peak_rss_bytes": stop["process_peak_rss_bytes"],
        "start_process_peak_rss_bytes": start["process_peak_rss_bytes"],
        "rss_scope": "CUMULATIVE_PROCESS_HIGH_WATER_NOT_ISOLATED_STAGE",
        "io": changes,
        "io_measurement_source": later["measurement_source"],
        "platform": stop["platform"],
    }


def canonical_payload_size(value) -> dict:
    """Measure actual UTF-8 serialization, never logical entries as bytes."""
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as error:
        raise ResourceUnavailable("Q21_CANONICAL_SERIALIZATION_FAILED") from error
    import hashlib
    return {"serialized_bytes": len(raw),
            "serialized_sha256": hashlib.sha256(raw).hexdigest(),
            "encoding": "canonical_json_utf8"}


def communication_receipt(adapter_mode: str, *, wire_bytes=None,
                          adapter_bytes=None) -> dict:
    """A zero claim is valid only if the caller explicitly declares no transport."""
    if adapter_mode == "none":
        if wire_bytes not in (None, 0) or adapter_bytes not in (None, 0):
            raise ResourceUnavailable("Q21_NONE_TRANSPORT_HAS_BYTES")
        return {"adapter_mode": "none", "wire_bytes": 0, "adapter_bytes": 0,
                "scope": "NO_EXTERNAL_TRANSPORT_DECLARED"}
    if adapter_mode == "measured":
        for amount in (wire_bytes, adapter_bytes):
            if type(amount) is not int or amount < 0:
                raise ResourceUnavailable("Q21_COMMUNICATION_BYTES_MISSING")
        return {"adapter_mode": "measured", "wire_bytes": wire_bytes,
                "adapter_bytes": adapter_bytes,
                "scope": "CALLER_REPORTED_TRANSPORT_COUNTERS"}
    raise ResourceUnavailable("Q21_UNKNOWN_COMMUNICATION_MODE")


def preflight():
    first = snapshot()
    payload = canonical_payload_size(
        {"probe": "public-fixture-only", "future_first_use": False})
    second = snapshot()
    result = measured_delta(first, second, "source_only_native_probe")
    if result["process_peak_rss_bytes"] <= 0:
        raise ResourceUnavailable("Q21_PROCESS_RESIDENT_BYTES_MISSING")
    result["serialization"] = payload
    result["communication"] = communication_receipt("none")
    result["scientific_first_use"] = False
    result["generated_development_cohorts"] = 0
    result["gate"] = "RESOURCE_COUNTER_INSTRUMENTATION_ONLY"
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight"], required=True)
    args = parser.parse_args()
    if args.mode == "preflight":
        print("Q21_NATIVE_RESOURCE_JSON=" +
              json.dumps(preflight(), sort_keys=True, separators=(",", ":")))
