"""RAR-G113D: read-only kernel accounting for an explicitly supplied Windows job.

This adapter does not create/open/assign/close a Job Object or any process.
A supplied HANDLE has no authenticated experiment identity: native kernel
readback is diagnostic until independent custody and isolation are established.
Peak job memory is NOT a physical process-tree RSS measurement.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys


class JobReadbackDenied(ValueError):
    """Native query failure, unsupported metric semantics or inconsistent scope."""


class BASIC_ACCOUNTING(ctypes.Structure):
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


class BASIC_LIMITS(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class EXTENDED_LIMITS(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", BASIC_LIMITS),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x00001000
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_MAX = (1 << 63) - 1


def _native_query(job_handle: int, info_class: int, record_type: type[ctypes.Structure]):
    if sys.platform != "win32":
        raise JobReadbackDenied("RAR_G113D_WINDOWS_REQUIRED")
    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.QueryInformationJobObject.argtypes = (
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
        )
        kernel.QueryInformationJobObject.restype = wintypes.BOOL
        value = record_type()
        length = wintypes.DWORD(0)
        success = kernel.QueryInformationJobObject(
            wintypes.HANDLE(job_handle), info_class, ctypes.byref(value),
            ctypes.sizeof(value), ctypes.byref(length),
        )
        if not success or length.value != ctypes.sizeof(value):
            raise JobReadbackDenied("RAR_G113D_KERNEL_QUERY_DENIED")
        return value
    except (OSError, AttributeError, OverflowError, TypeError) as exc:
        raise JobReadbackDenied("RAR_G113D_WINAPI_UNAVAILABLE") from exc


def read_job_accounting(handle: int, *, query=None, require_quiescent: bool = True) -> dict:
    """Query an explicitly held job HANDLE, without opening or mutating it.

    query is a test-only injected reader with signature (handle, class_id, type).
    A successful read does not prove exclusive job membership, correct origin,
    that descendants could not break away, or experiment-custody authority.
    """
    if type(handle) is not int or not 0 < handle <= (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1:
        raise JobReadbackDenied("RAR_G113D_EXPLICIT_HANDLE_REQUIRED")
    if type(require_quiescent) is not bool:
        raise JobReadbackDenied("RAR_G113D_QUIESCENCE_FLAG_INVALID")
    if query is None:
        query = _native_query
    try:
        basic = query(handle, 1, BASIC_ACCOUNTING)
        limits = query(handle, 9, EXTENDED_LIMITS)
    except JobReadbackDenied:
        raise
    except Exception as exc:
        raise JobReadbackDenied("RAR_G113D_KERNEL_QUERY_FAILED") from exc
    if type(basic) is not BASIC_ACCOUNTING or type(limits) is not EXTENDED_LIMITS:
        raise JobReadbackDenied("RAR_G113D_RECORD_TYPE")
    user, kernel = int(basic.TotalUserTime), int(basic.TotalKernelTime)
    count, active = int(basic.TotalProcesses), int(basic.ActiveProcesses)
    terminated = int(basic.TotalTerminatedProcesses)
    flags = int(limits.BasicLimitInformation.LimitFlags)
    peak = int(limits.PeakJobMemoryUsed)
    if (user < 0 or kernel < 0 or user + kernel > _MAX or count < 1 or
            active > count or terminated > count or peak < 0):
        raise JobReadbackDenied("RAR_G113D_ACCOUNTING_INVARIANT")
    if require_quiescent and active:
        raise JobReadbackDenied("RAR_G113D_ACTIVE_PROCESSES_REMAIN")
    if not flags & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE:
        raise JobReadbackDenied("RAR_G113D_NO_KILL_ON_CLOSE")
    if flags & (JOB_OBJECT_LIMIT_BREAKAWAY_OK | JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK):
        raise JobReadbackDenied("RAR_G113D_BREAKAWAY_SCOPE")
    return {
        "classification": "EXPLICIT_JOB_HANDLE_READBACK_UNAUTHENTICATED_NOT_SCIENTIFIC_COST",
        "kernel_job_cpu_100ns_nonexclusive_until_witnessed": user + kernel,
        "job_total_user_100ns": user,
        "job_total_kernel_100ns": kernel,
        "job_total_processes": count,
        "job_active_processes": active,
        "job_terminated_processes": terminated,
        "job_peak_memory_bytes_not_physical_rss": peak,
        "memory_semantics": "WINDOWS_PEAK_JOB_MEMORY_NOT_PHYSICAL_TREE_RSS",
        "scope_handle_authenticated": False,
        "exclusive_experiment_membership_verified": False,
        "short_lived_descendants_exclusively_accounted": False,
        "physical_tree_rss_qualified": False,
        "native_training_cost_qualified": False,
        "scientific_first_use_authorized": False,
        "process_created": False,
        "scope_created": False,
        "original_controller_changed": False,
    }
