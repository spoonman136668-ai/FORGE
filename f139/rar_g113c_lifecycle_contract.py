"""RAR-G113C: offline Windows nested-job measurement lifecycle contract.

Validates the shape of caller-supplied events, NOT their authenticity.
No processes, Job Objects or kernel APIs are invoked. An independently
qualified witness is required before assigning training costs or scientific
first-use. Job memory peak is COMMIT, not physical process-tree RSS.
"""
from __future__ import annotations

import hashlib
import json


class LifecycleDenied(ValueError):
    """Inconsistent or ineligible proposed lifecycle evidence."""


EVENTS = (
    "job_created_empty", "child_created_suspended", "child_assigned_to_job",
    "child_resumed", "child_and_descendants_exited", "job_accounted", "job_closed",
)
_TRACE_KEYS = frozenset(("schema", "platform", "scope_id", "child_id", "events"))
_EVENT_SPECIFIC_KEYS = (
    ("job_empty", "kill_on_job_close", "breakaway_ok", "silent_breakaway_ok", "ui_restrictions"),
    ("child_id", "create_suspended", "breakaway_creation_flag"),
    ("child_id", "assignment_succeeded", "nested_job_compatible"),
    ("child_id", "resume_succeeded"),
    ("child_id", "all_descendants_exited", "exit_code"),
    ("total_user_100ns", "total_kernel_100ns", "total_processes", "active_processes",
     "peak_job_commit_bytes", "includes_parent_job", "includes_separate_per_process_cpu_sum"),
    ("last_handle_closed", "job_empty_before_close"),
)
_MAX = (1 << 63) - 1


def _nonneg_int(value: object, name: str) -> int:
    if type(value) is not int or value < 0 or value > _MAX:
        raise LifecycleDenied("RAR_G113C_INVALID_" + name.upper())
    return value


def assess_untrusted_windows_lifecycle(trace: object) -> dict:
    """Validate a seven-event, strictly bounded untrusted lifecycle trace.

    A positive result proves protocol shape only, never Win32 call outcomes,
    nested-job admission, complete descendants or physical memory.
    """
    if type(trace) is not dict or trace.get("schema") != "rar.windows-job-lifecycle.v1":
        raise LifecycleDenied("RAR_G113C_SCHEMA")
    if set(trace) != _TRACE_KEYS:
        raise LifecycleDenied("RAR_G113C_UNEXPECTED_TRACE_FIELDS")
    if trace.get("platform") != "win32":
        raise LifecycleDenied("RAR_G113C_PLATFORM")
    scope = trace.get("scope_id")
    child = trace.get("child_id")
    if (type(scope) is not str or not 1 <= len(scope) <= 128 or
            type(child) is not str or not 1 <= len(child) <= 128):
        raise LifecycleDenied("RAR_G113C_IDENTITY")
    events = trace.get("events")
    if type(events) is not list or len(events) != len(EVENTS):
        raise LifecycleDenied("RAR_G113C_EVENT_COUNT")
    for seq, (event, expected_name) in enumerate(zip(events, EVENTS)):
        if (type(event) is not dict or type(event.get("seq")) is not int or
                event["seq"] != seq or event.get("name") != expected_name or
                event.get("scope_id") != scope):
            raise LifecycleDenied("RAR_G113C_EVENT_ORDER_OR_SCOPE")
        if set(event) != {"seq", "name", "scope_id", *_EVENT_SPECIFIC_KEYS[seq]}:
            raise LifecycleDenied("RAR_G113C_UNEXPECTED_EVENT_FIELDS")

    created, suspended, assigned, resumed, exited, metered, closed = events
    if (created.get("job_empty") is not True or
            created.get("kill_on_job_close") is not True or
            created.get("breakaway_ok") is not False or
            created.get("silent_breakaway_ok") is not False or
            created.get("ui_restrictions") is not False):
        raise LifecycleDenied("RAR_G113C_JOB_CREATION_POLICY")
    if (suspended.get("child_id") != child or
            suspended.get("create_suspended") is not True or
            suspended.get("breakaway_creation_flag") is not False):
        raise LifecycleDenied("RAR_G113C_CHILD_SUSPENSION")
    if (assigned.get("child_id") != child or
            assigned.get("assignment_succeeded") is not True or
            assigned.get("nested_job_compatible") is not True):
        raise LifecycleDenied("RAR_G113C_ASSIGNMENT")
    if resumed.get("child_id") != child or resumed.get("resume_succeeded") is not True:
        raise LifecycleDenied("RAR_G113C_RESUME")
    if (exited.get("child_id") != child or
            exited.get("all_descendants_exited") is not True or
            type(exited.get("exit_code")) is not int):
        raise LifecycleDenied("RAR_G113C_EXIT")
    if (closed.get("last_handle_closed") is not True or
            closed.get("job_empty_before_close") is not True):
        raise LifecycleDenied("RAR_G113C_CLOSE")

    user = _nonneg_int(metered.get("total_user_100ns"), "total_user_100ns")
    kernel = _nonneg_int(metered.get("total_kernel_100ns"), "total_kernel_100ns")
    count = _nonneg_int(metered.get("total_processes"), "total_processes")
    active = _nonneg_int(metered.get("active_processes"), "active_processes")
    peak_commit = _nonneg_int(metered.get("peak_job_commit_bytes"), "peak_job_commit_bytes")
    if (count < 1 or active != 0 or metered.get("includes_parent_job") is not False or
            metered.get("includes_separate_per_process_cpu_sum") is not False):
        raise LifecycleDenied("RAR_G113C_JOB_METER_SCOPE")
    if user + kernel > _MAX:
        raise LifecycleDenied("RAR_G113C_CPU_OVERFLOW")

    # Hash is content identity only: an untrusted producer can forge it.
    digest = hashlib.sha256(json.dumps(trace, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=True).encode("ascii")).hexdigest()
    return {
        "trace_shape_validated": True,
        "trace_content_sha256": digest,
        "trace_digest_authenticated": False,
        "scope_identity_authenticated": False,
        "win32_call_outcomes_independently_witnessed": False,
        "nested_job_permission_qualified": False,
        "all_descendant_membership_qualified": False,
        "kernel_job_cpu_100ns_untrusted": user + kernel,
        "peak_job_commit_bytes_untrusted": peak_commit,
        "physical_tree_rss_qualified": False,
        "native_training_cost_qualified": False,
        "scientific_first_use_authorized": False,
        "process_created": False,
        "scope_created": False,
        "measurement_semantics": "WINDOWS_NESTED_JOB_CPU_AND_PEAK_COMMIT_NOT_PHYSICAL_RSS",
    }
