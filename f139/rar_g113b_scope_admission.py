"""RAR-G113B: read-only admission hints for a future exclusive OS resource meter.

This module never creates, assigns, opens-for-write, kills or launches any
process, Job Object or cgroup. A writable hint or exported API is not authority,
delegation, exclusive lifetime evidence, or native training qualification.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import sys


def _base(platform: str) -> dict:
    return {
        "platform": platform,
        "probe": "RAR_G113B_READ_ONLY_SCOPE_ADMISSION",
        "current_scope_resolved": False,
        "current_process_direct_member": False,
        "cpu_memory_controllers_available": False,
        "cpu_memory_subtree_enabled": False,
        "scope_writable_hint": False,
        "mount_readonly": None,
        "windows_api_exports_present": False,
        "scope_creation_tested": False,
        "exclusive_experiment_membership_verified": False,
        "short_lived_descendants_accounted_for_exclusively": False,
        "full_native_training_cpu_rss_qualified": False,
        "scientific_first_use_authorized": False,
        "process_created": False,
        "scope_created": False,
        "original_controller_changed": False,
    }


def _under_root(root: Path, relative: str) -> Path:
    if not relative.startswith("/") or "\x00" in relative or "\\" in relative:
        raise ValueError("RAR_G113B_INVALID_CGROUP_MEMBERSHIP")
    base = root.resolve(strict=True)
    path = (base / relative.lstrip("/")).resolve(strict=True)
    if not path.is_relative_to(base):
        raise ValueError("RAR_G113B_CGROUP_PATH_ESCAPE")
    return path


def linux_admission_hint(
    mount_root: Path = Path("/sys/fs/cgroup"),
    membership_file: Path = Path("/proc/self/cgroup"),
    *,
    pid: int | None = None,
) -> dict:
    """Read the current *existing* v2 cgroup. Never test admission by writing."""
    out = _base("linux")
    try:
        if not (mount_root / "cgroup.controllers").is_file():
            return out
        memberships = [line[3:] for line in membership_file.read_text(encoding="ascii").splitlines()
                       if line.startswith("0::/")]
        if len(memberships) != 1:
            return out
        group = _under_root(mount_root, memberships[0])
        out["current_scope_resolved"] = True
        procs = (group / "cgroup.procs").read_text(encoding="ascii").splitlines()
        if not all(p.isascii() and p.isdecimal() for p in procs):
            return out
        out["current_process_direct_member"] = str(os.getpid() if pid is None else pid) in procs
        controllers = set((group / "cgroup.controllers").read_text(encoding="ascii").split())
        subtree = set((group / "cgroup.subtree_control").read_text(encoding="ascii").split())
        out["cpu_memory_controllers_available"] = {"cpu", "memory"}.issubset(controllers)
        out["cpu_memory_subtree_enabled"] = {"cpu", "memory"}.issubset(subtree)
        out["mount_readonly"] = bool(os.statvfs(group).f_flag & getattr(os, "ST_RDONLY", 1))
        out["scope_writable_hint"] = os.access(group, os.W_OK | os.X_OK)
    except (OSError, ValueError, UnicodeError):
        return out
    # No read-only inspection can prove writable delegation, race-free
    # assign-before-exec, descendants, or an experiment-exclusive scope.
    return out


def windows_admission_hint() -> dict:
    """Inspect export availability, never call any mutating Win32 function."""
    out = _base("win32")
    if sys.platform != "win32":
        return out
    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        out["windows_api_exports_present"] = all(hasattr(kernel, name) for name in (
            "CreateJobObjectW", "SetInformationJobObject",
            "AssignProcessToJobObject", "QueryInformationJobObject",
            "CreateProcessW", "ResumeThread", "TerminateJobObject"
        ))
    except (OSError, AttributeError):
        pass
    # Inherited job nesting and assignment permissions remain untested.
    return out


def current_host_admission_hint() -> dict:
    if sys.platform == "win32":
        return windows_admission_hint()
    if sys.platform.startswith("linux"):
        return linux_admission_hint()
    return _base(sys.platform)
