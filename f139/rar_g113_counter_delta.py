"""RAR-G113A: nonexclusive OS counter deltas are diagnostic, never training cost.

Consumes read-only snapshots of an *unchanged existing* Linux cgroup or
Windows Job Object. Does not launch processes or create/modify OS scopes.
It cannot establish exclusive membership, lifetime coverage, or physical RSS.
"""
from __future__ import annotations


class ScopeDeltaDenied(ValueError):
    """Inconsistent or ineligible inherited kernel scope evidence."""


def _counter(record: dict, name: str) -> int:
    value = record.get(name)
    if type(value) is not int or value < 0:
        raise ScopeDeltaDenied("RAR_G113_INVALID_" + name.upper())
    return value


def diagnostic_delta(before: dict, after: dict) -> dict:
    """Return *nonexclusive* diagnostic counters; always deny scientific use.

    A matching caller-supplied scope key filters obvious cross-scope mixing;
    it is NOT authenticated scope identity or isolation proof. Both inputs
    must remain explicitly classified as nonexclusive G112 observations.
    """
    if type(before) is not dict or type(after) is not dict:
        raise ScopeDeltaDenied("RAR_G113_RECORD_TYPE")
    for field in ("platform", "method", "cpu_scope", "memory_scope", "scope_key"):
        if not isinstance(before.get(field), str) or not before[field] or before[field] != after.get(field):
            raise ScopeDeltaDenied("RAR_G113_SCOPE_MISMATCH_" + field.upper())
    if before["platform"] not in ("linux", "win32"):
        raise ScopeDeltaDenied("RAR_G113_UNSUPPORTED_PLATFORM")
    for sample in (before, after):
        if sample.get("counter_available") is not True:
            raise ScopeDeltaDenied("RAR_G113_COUNTER_UNAVAILABLE")
        for flag in ("exclusive_experiment_membership_verified",
                     "short_lived_descendants_accounted_for_exclusively",
                     "complete_native_training_cpu_rss_qualified",
                     "scientific_first_use_authorized", "process_created"):
            if sample.get(flag) is not False:
                raise ScopeDeltaDenied("RAR_G113_UNTRUSTED_FLAG_" + flag.upper())
    if before["platform"] == "linux":
        if before["method"] != "linux_cgroup_v2_read_only" or before["cpu_scope"] != "CGROUP_INCLUDING_DESCENDANTS_AND_OTHER_MEMBERS" or before["memory_scope"] != "CGROUP_CHARGED_MEMORY_NOT_PROCESS_TREE_RSS":
            raise ScopeDeltaDenied("RAR_G113_LINUX_SCOPE_CLASSIFICATION")
        start = _counter(before, "cpu_usage_usec")
        finish = _counter(after, "cpu_usage_usec")
        for sample in (before, after):
            if _counter(sample, "memory_current_bytes") > _counter(sample, "memory_peak_bytes"):
                raise ScopeDeltaDenied("RAR_G113_MEMORY_INVARIANT")
            _counter(sample, "direct_process_count")
        end_memory_peak = _counter(after, "memory_peak_bytes")
        memory_label = "CGROUP_CHARGED_PEAK_INCLUDING_OTHER_WORK"
        unit = "microseconds"
    else:
        if before["method"] != "windows_immediate_job_accounting_read_only" or before["cpu_scope"] != "IMMEDIATE_EXISTING_JOB_INCLUDING_PRIOR_MEMBERS" or before["memory_scope"] != "WINDOWS_JOB_PEAK_COMMIT_NOT_PHYSICAL_RSS":
            raise ScopeDeltaDenied("RAR_G113_WINDOWS_SCOPE_CLASSIFICATION")
        start = _counter(before, "total_user_100ns") + _counter(before, "total_kernel_100ns")
        finish = _counter(after, "total_user_100ns") + _counter(after, "total_kernel_100ns")
        for sample in (before, after):
            if _counter(sample, "active_processes") > _counter(sample, "total_processes"):
                raise ScopeDeltaDenied("RAR_G113_JOB_PROCESS_INVARIANT")
        if after["total_processes"] < before["total_processes"]:
            raise ScopeDeltaDenied("RAR_G113_JOB_PROCESS_COUNT_REGRESSED")
        end_memory_peak = None  # G112 does not expose a physical peak.
        memory_label = "UNMEASURED_PHYSICAL_RSS"
        unit = "100ns"
    if finish < start:
        raise ScopeDeltaDenied("RAR_G113_CPU_COUNTER_REGRESSED")
    return {
        "classification": "NONEXCLUSIVE_READ_ONLY_DIAGNOSTIC_NOT_TRAINING_COST",
        "platform": before["platform"],
        "cpu_delta_nonexclusive": finish - start,
        "cpu_unit": unit,
        "existing_scope_memory_peak": end_memory_peak,
        "memory_semantics": memory_label,
        "caller_scope_key_authenticated": False,
        "exclusive_experiment_membership_verified": False,
        "complete_descendant_lifetime_accounting": False,
        "physical_tree_rss_qualified": False,
        "native_training_cost_qualified": False,
        "scientific_first_use_authorized": False,
        "process_created": False,
    }
