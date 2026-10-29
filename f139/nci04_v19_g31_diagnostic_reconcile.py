"""F139 V19 G31 source-only G29 diagnostic reconciliation.

This module has no worker, provider, issue, owner, queue or signature entrypoint.
It can reconcile independently produced *diagnostic* reports but MUST NOT create
or validate a signed worker receipt, override G29, or authorize a live release.
The frozen original Windows resource failure is a real negative, not a waiver.
"""
from __future__ import annotations

import re

SCHEMA = "forge.f139.v19.g29.dual-custody-experiment.v1"
BASE = "021423311027517c9096c76bed7d35ac53c4a229"
TREE = "93620bd8e46bfbae1dbcd8e4ce397e27044de4f1"
HEAD = "339276862e42a067344990dc20d907f203009b90"
HEAD_TREE = "de431210951f1f0e79e447a532914cdfa431d25f"
SOURCE = "0743ca22b76ebd943a66f05a36ea919301676be0"
TARGET = "yggdrasil/public_causal_cells.py"
ATLAS = "test_code_atlas.py"
SIDECAR = "test_free_fanout_sidecar.py"
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
MODULE = re.compile(r"test_[A-Za-z0-9_]+\.py\Z")
G31_SCHEMA = "forge.f139.v19.g31.readonly-diagnostic-reconciliation.v1"


class G31Denied(ValueError):
    pass


def require(value, message):
    if not value:
        raise G31Denied("F139_V19_G31_" + message)


def result(report, label, status, *, count_positive=True, error=False):
    row = report["results"].get(label)
    require(type(row) is dict
            and row.get("status") == status
            and type(row.get("exit_code")) is int
            and ((row["exit_code"] != 0) if error else (row["exit_code"] == 0))
            and type(row.get("test_count")) is int
            and (row["test_count"] > 0 if count_positive else row["test_count"] >= 0)
            and type(row.get("output_sha256")) is str
            and DIGEST.fullmatch(row["output_sha256"]) is not None
            and type(row.get("output_bytes")) is int
            and row["output_bytes"] >= 0,
            "RESULT_INVALID_" + label)
    return row


def inspect(report, platform):
    """Read a G29 diagnostic, preserving exactly the observed Windows negative."""
    require(type(report) is dict and platform in ("linux", "windows"),
            "REPORT_OR_PLATFORM_INVALID")
    fields = {"controller_source_sha": SOURCE, "baseline_commit": BASE,
              "baseline_tree": TREE, "candidate_head": HEAD,
              "candidate_tree": HEAD_TREE, "path": TARGET, "schema": SCHEMA}
    require(all(report.get(k) == v for k, v in fields.items()),
            "SOURCE_OR_SCHEMA_DRIFT")
    require(type(report.get("before_sha256")) is str
            and DIGEST.fullmatch(report["before_sha256"]) is not None
            and type(report.get("after_sha256")) is str
            and DIGEST.fullmatch(report["after_sha256"]) is not None
            and report["before_sha256"] != report["after_sha256"],
            "CANDIDATE_HASH_INVALID")
    require(report.get("source_diff_exact_one_file") is True
            and report.get("frozen_atlas_maintained") is True
            and report.get("experimental_split_complete") is True
            and report.get("baseline_g29_pass") is True
            and report.get("historical_modified_source_g29_negative") is True
            and report.get("modified_candidate_full_regression_pass") is False
            and report.get("cross_platform_worker_qualified") is False
            and report.get("signed_provider_success") is False
            and report.get("production_v19_worker_unchanged") is True
            and report.get("scientific_first_use") is False
            and report.get("worker_replay") is False
            and report.get("github_writes") == 0
            and type(report.get("github_writes")) is int
            and type(report.get("paid_api_calls")) is int
            and report["paid_api_calls"] == 0
            and report.get("resource_accounting") ==
                "timing_only; peak RSS unavailable",
            "FALSE_AUTHORITY_OR_RESOURCE_CLAIM")
    require(type(report.get("negative_controls")) is dict
            and report["negative_controls"] ==
                {"second_source_delta_rejected": True,
                 "bad_candidate_digest_rejected": True},
            "NEGATIVE_CONTROL_MISSING")
    inventory = report.get("test_inventory")
    require(type(inventory) is list and len(inventory) >= 5
            and len(inventory) == len(set(inventory))
            and inventory == sorted(inventory)
            and all(type(n) is str and MODULE.fullmatch(n) for n in inventory)
            and ATLAS in inventory and SIDECAR in inventory,
            "TEST_INVENTORY_INVALID")
    require(type(report.get("results")) is dict
            and set(report["results"]) ==
                {"baseline_g29", "baseline_full", "candidate_g29_negative",
                 "candidate_compile"} |
                {"candidate_" + n for n in inventory if n != ATLAS},
            "CANDIDATE_TEST_COVERAGE_INCOMPLETE")
    result(report, "baseline_g29", "PASS")
    historical = result(report, "candidate_g29_negative",
                        "EXPECTED_FROZEN_ATLAS_REJECTION", error=True)
    require("working source mismatch: " + TARGET in
            historical.get("output_tail", ""),
            "ATLAS_NEGATIVE_NOT_EXACT")
    result(report, "candidate_compile", "PASS", count_positive=False)
    expected_windows = platform == "windows"
    require(report.get("inherited_platform_negatives") ==
            (["baseline_full", "candidate_" + SIDECAR]
             if expected_windows else []),
            "PLATFORM_NEGATIVE_SET_MISMATCH")
    if expected_windows:
        for label in ("baseline_full", "candidate_" + SIDECAR):
            row = result(report, label,
                         "EXPECTED_INHERITED_WINDOWS_RESOURCE_NEGATIVE",
                         error=True)
            require("ModuleNotFoundError: No module named 'resource'"
                    in row.get("output_tail", ""),
                    "INHERITED_WINDOWS_RESOURCE_NOT_EXACT")
    else:
        result(report, "baseline_full", "PASS")
    for filename in inventory:
        if filename != ATLAS and not (expected_windows and filename == SIDECAR):
            result(report, "candidate_" + filename, "PASS")
    require(report.get("baseline_full_unmodified_regression_pass")
                is not expected_windows
            and report.get("candidate_changed_source_applicable_tests_pass")
                is not expected_windows
            and report.get("original_full_regression_qualified")
                is not expected_windows,
            "FULL_REGRESSION_FALSE_CLASSIFICATION")
    return {"platform": platform, "test_modules": len(inventory),
            "candidate_test_modules": len(inventory) - 1,
            "baseline_g29": "PASS",
            "changed_source_g29": "EXPECTED_NEGATIVE",
            "historical_full_regression":
                "NEGATIVE_RETAINED" if expected_windows else "PASS",
            "native_qualified": False, "signed_provider_success": False}


def reconcile(linux, windows):
    """Correlate two independently obtained reports. No signature is inferred."""
    a, b = inspect(linux, "linux"), inspect(windows, "windows")
    require(linux["before_sha256"] == windows["before_sha256"]
            and linux["after_sha256"] == windows["after_sha256"]
            and linux["test_inventory"] == windows["test_inventory"],
            "CROSS_OS_PROVENANCE_MISMATCH")
    return {"schema": G31_SCHEMA,
            "source_sha": SOURCE, "baseline_commit": BASE,
            "candidate_commit": HEAD,
            "diagnostic_reconciliation_complete": True,
            "linux": a, "windows": b,
            "windows_historical_regression": "NEGATIVE_RETAINED",
            "native_qualified": False, "signed_provider_success": False,
            "scientific_first_use": False,
            "provider_zip_authenticated": False,
            "original_owner_consumed_signed_receipt": False,
            "production_release_authorized": False}
