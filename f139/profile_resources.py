"""Optional read-only diagnostics; no process-tree or scientific accounting.

Windows API definitions:
https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-getprocessiocounters
https://learn.microsoft.com/windows/win32/api/winnt/ns-winnt-io_counters
https://learn.microsoft.com/windows/win32/api/processthreadsapi/nf-processthreadsapi-getsystemtimes
"""
import ctypes
import os
import platform
import re
import sys
import time

IO_KEYS = ('read_operations', 'write_operations', 'other_operations',
           'read_bytes', 'write_bytes', 'other_bytes')
HOST_KEYS = ('idle', 'kernel_including_idle', 'user')


class ResourceSampler:
    def __init__(self):
        self.api = None
        if os.name == 'nt':
            from ctypes import wintypes

            class IO(ctypes.Structure):
                _fields_ = [(key, ctypes.c_ulonglong) for key in IO_KEYS]

            self.io_type = IO
            self.filetime_type = wintypes.FILETIME
            try:
                api = ctypes.WinDLL('kernel32', use_last_error=True)
                api.GetCurrentProcess.argtypes = []
                api.GetCurrentProcess.restype = wintypes.HANDLE
                api.GetProcessIoCounters.argtypes = [wintypes.HANDLE, ctypes.POINTER(IO)]
                api.GetProcessIoCounters.restype = wintypes.BOOL
                api.GetSystemTimes.argtypes = [ctypes.POINTER(wintypes.FILETIME)] * 3
                api.GetSystemTimes.restype = wintypes.BOOL
                self.api = api
            except (AttributeError, OSError):
                pass

    def sample(self):
        sample = dict(self_cpu_ns=None, process_io=None, host_cpu_100ns=None)
        try:
            sample['self_cpu_ns'] = time.process_time_ns()
            if self.api is not None:
                io = self.io_type()
                if self.api.GetProcessIoCounters(self.api.GetCurrentProcess(), ctypes.byref(io)):
                    sample['process_io'] = {key: getattr(io, key) for key in IO_KEYS}
                values = [self.filetime_type() for _ in HOST_KEYS]
                if self.api.GetSystemTimes(*(ctypes.byref(value) for value in values)):
                    sample['host_cpu_100ns'] = {key: (value.dwHighDateTime << 32) | value.dwLowDateTime
                                              for key, value in zip(HOST_KEYS, values)}
        except (OSError, AttributeError):
            # Preserve successful counters; missing dimensions remain unverified.
            pass
        return sample


def _delta(before, after, keys):
    if not isinstance(before, dict) or not isinstance(after, dict):
        return dict(status='UNVERIFIED', reason='COUNTER_UNAVAILABLE')
    if set(before) != set(keys) or set(after) != set(keys):
        return dict(status='UNVERIFIED', reason='COUNTER_SCHEMA')
    if any(type(before[k]) is not int or type(after[k]) is not int or
           before[k] < 0 or after[k] < before[k] for k in keys):
        return dict(status='UNVERIFIED', reason='COUNTER_INVALID_OR_REGRESSED')
    return dict(status='VERIFIED', delta={key: after[key] - before[key] for key in keys})


def resource_delta(before, after):
    cpu = _delta({'ns': before.get('self_cpu_ns')}, {'ns': after.get('self_cpu_ns')}, ('ns',))
    io = _delta(before.get('process_io'), after.get('process_io'), IO_KEYS)
    host = _delta(before.get('host_cpu_100ns'), after.get('host_cpu_100ns'), HOST_KEYS)
    if host['status'] == 'VERIFIED':
        # GetSystemTimes kernel includes idle; never count idle as busy CPU.
        if any(s['host_cpu_100ns']['idle'] > s['host_cpu_100ns']['kernel_including_idle']
               for s in (before, after)) or host['delta']['idle'] > host['delta']['kernel_including_idle']:
            host = dict(status='UNVERIFIED', reason='HOST_IDLE_KERNEL_INCONSISTENT')
        else:
            d = host['delta']
            d['busy'] = d['kernel_including_idle'] + d['user'] - d['idle']
    return dict(self_cpu=cpu, process_io=io, host_cpu_100ns=host)


def safe_environment():
    formats = dict(PYTHONHASHSEED=r'(?:[0-9]{1,10}|random)', GOMAXPROCS=r'[0-9]{1,5}',
                   GOFLAGS=r'-p=[0-9]{1,5}', GOMEMLIMIT=r'[0-9]{1,12}(?:[KMGT]i?B)?')
    result = {}
    for key, pattern in formats.items():
        value = os.environ.get(key)
        result[key] = value if value is None or re.fullmatch(pattern, value) else 'REDACTED_NONCANONICAL'
    return result


def telemetry_identity():
    # Only named non-secret controls; never serialize the inherited environment.
    return dict(schema='forge.f139.case-resource-diagnostics.v1',
        self_cpu_scope='CURRENT_PROCESS_ALL_THREADS_EXCLUDES_CHILDREN',
        process_io_scope='CURRENT_PROCESS_ACCOUNTED_IO_NOT_PHYSICAL_DISK_OR_FSYNC_LATENCY',
        host_cpu_scope='WINDOWS_API_PROCESSOR_GROUP_SCOPE_INCLUDES_OTHER_PROCESSES',
        host_cpu_unit='100ns', io_byte_unit='bytes', io_operation_unit='operations',
        scientific_resource_accounting=False, child_process_resources_complete=False,
        cause_attribution_proven=False, sampling_overhead_independently_measured=False,
        python_implementation=platform.python_implementation(),
        python_version=sys.version, sqlite_version=__import__('sqlite3').sqlite_version,
        pointer_bits=ctypes.sizeof(ctypes.c_void_p) * 8,
        hash_randomization_enabled=sys.flags.hash_randomization,
        environment=safe_environment())
