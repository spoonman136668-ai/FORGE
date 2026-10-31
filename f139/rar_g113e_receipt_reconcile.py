"""RAR-G113E: offline reconciliation of two *unauthenticated* Win32 receipts.

Joins G113C lifecycle shape and G113D job readback without rereading the
kernel, creating jobs/processes, or converting a matching pair into authority.
Neither a caller-supplied scope name nor content digest authenticates custody.
"""
from __future__ import annotations

import hashlib
import json

from f139.rar_g113c_lifecycle_contract import LifecycleDenied, assess_untrusted_windows_lifecycle


class ReconcileDenied(ValueError):
    """Inconsistent candidate lifecycle and job accounting receipts."""


_READBACK_KEYS = frozenset((
    "classification", "kernel_job_cpu_100ns_nonexclusive_until_witnessed",
    "job_total_user_100ns", "job_total_kernel_100ns", "job_total_processes",
    "job_active_processes", "job_terminated_processes",
    "job_peak_memory_bytes_not_physical_rss", "memory_semantics",
    "scope_handle_authenticated", "exclusive_experiment_membership_verified",
    "short_lived_descendants_exclusively_accounted", "physical_tree_rss_qualified",
    "native_training_cost_qualified", "scientific_first_use_authorized",
    "process_created", "scope_created", "original_controller_changed",
))
_DENIAL_FLAGS = (
    "scope_handle_authenticated", "exclusive_experiment_membership_verified",
    "short_lived_descendants_exclusively_accounted", "physical_tree_rss_qualified",
    "native_training_cost_qualified", "scientific_first_use_authorized",
    "process_created", "scope_created", "original_controller_changed",
)
_COUNTER_MAP = (
    ("total_user_100ns", "job_total_user_100ns"),
    ("total_kernel_100ns", "job_total_kernel_100ns"),
    ("total_processes", "job_total_processes"),
    ("active_processes", "job_active_processes"),
    ("peak_job_commit_bytes", "job_peak_memory_bytes_not_physical_rss"),
)
_MAX = (1 << 63) - 1


def reconcile_untrusted_windows_receipts(lifecycle_trace: object, job_readback: object) -> dict:
    """Return only candidate counter consistency, NEVER native science metrics."""
    try:
        shape = assess_untrusted_windows_lifecycle(lifecycle_trace)
    except (LifecycleDenied, TypeError, ValueError) as exc:
        raise ReconcileDenied("RAR_G113E_LIFECYCLE_DENIED") from exc

    if type(job_readback) is not dict or set(job_readback) != _READBACK_KEYS:
        raise ReconcileDenied("RAR_G113E_READBACK_SCHEMA")
    if job_readback.get("classification") != "EXPLICIT_JOB_HANDLE_READBACK_UNAUTHENTICATED_NOT_SCIENTIFIC_COST":
        raise ReconcileDenied("RAR_G113E_READBACK_CLASSIFICATION")
    if job_readback.get("memory_semantics") != "WINDOWS_PEAK_JOB_MEMORY_NOT_PHYSICAL_TREE_RSS":
        raise ReconcileDenied("RAR_G113E_MEMORY_SEMANTICS")
    if any(job_readback.get(flag) is not False for flag in _DENIAL_FLAGS):
        raise ReconcileDenied("RAR_G113E_UNTRUSTED_AUTHORITY_FLAG")
    event_meter = lifecycle_trace["events"][5]
    for event_field, readback_field in _COUNTER_MAP:
        left = event_meter[event_field]
        right = job_readback.get(readback_field)
        if (type(left) is not int or type(right) is not int or
                left < 0 or right < 0 or left != right or left > _MAX):
            raise ReconcileDenied("RAR_G113E_COUNTER_MISMATCH_" + event_field.upper())
    user, kernel = event_meter["total_user_100ns"], event_meter["total_kernel_100ns"]
    total = job_readback.get("kernel_job_cpu_100ns_nonexclusive_until_witnessed")
    if type(total) is not int or user + kernel > _MAX or total != user + kernel:
        raise ReconcileDenied("RAR_G113E_CPU_TOTAL_MISMATCH")
    count = job_readback.get("job_terminated_processes")
    if type(count) is not int or count < 0 or count > event_meter["total_processes"]:
        raise ReconcileDenied("RAR_G113E_TERMINATION_COUNTER_INVALID")
    if (shape.get("trace_shape_validated") is not True or
            shape.get("trace_digest_authenticated") is not False or
            shape.get("native_training_cost_qualified") is not False):
        raise ReconcileDenied("RAR_G113E_SHAPE_CLASSIFICATION")
    # Content identity only: a forged pair can satisfy every equality below.
    digest = hashlib.sha256(json.dumps(
        {"lifecycle": lifecycle_trace, "readback": job_readback},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()
    return {
        "classification": "MATCHED_UNTRUSTED_RECEIPTS_NOT_NATIVE_TRAINING_COST",
        "candidate_counter_consistency_only": True,
        "pair_content_sha256": digest,
        "content_digest_authenticated": False,
        "experiment_scope_authenticated": False,
        "win32_call_outcomes_independently_witnessed": False,
        "exclusive_experiment_membership_verified": False,
        "complete_short_lived_descendants_qualified": False,
        "physical_tree_rss_qualified": False,
        "native_training_cost_qualified": False,
        "scientific_first_use_authorized": False,
        "process_created": False,
        "scope_created": False,
        "original_controller_changed": False,
        "cpu_accounting_semantics": "UNTRUSTED_JOB_CPU_100NS_NOT_PROVEN_EXCLUSIVE",
        "memory_accounting_semantics": "UNTRUSTED_JOB_PEAK_MEMORY_NOT_PHYSICAL_RSS",
    }
