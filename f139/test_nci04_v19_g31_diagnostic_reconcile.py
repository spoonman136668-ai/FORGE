"""G31 inert diagnostic receipt-contract negative controls, no real dispatch."""
import copy
import unittest

from f139.nci04_v19_g31_diagnostic_reconcile import (
    G31Denied, SCHEMA, SOURCE, BASE, TREE, HEAD, HEAD_TREE, TARGET,
    inspect, reconcile,
)

FILES = ["test_code_atlas.py", "test_free_fanout_sidecar.py",
         "test_native_cells.py", "test_other.py", "test_portable_checkpoint.py"]
SHA_A = "a" * 64
SHA_B = "b" * 64


def row(status="PASS", count=8, tail="", failure=False):
    return {
        "status": status, "exit_code": 1 if failure else 0,
        "test_count": count, "output_sha256": "c" * 64,
        "output_bytes": 125, "output_tail": tail,
    }


def fixture(platform):
    windows = platform == "windows"
    rows = {
        "baseline_g29": row(count=4),
        "baseline_full": row(count=34 if windows else 53),
        "candidate_g29_negative": row(
            status="EXPECTED_FROZEN_ATLAS_REJECTION", count=4,
            tail="YGG_ATLAS_FAIL_CLOSED: working source mismatch: " + TARGET,
            failure=True),
        "candidate_compile": row(count=0),
    }
    for filename in FILES:
        if filename != "test_code_atlas.py":
            rows["candidate_" + filename] = row()
    if windows:
        for label in ("baseline_full", "candidate_test_free_fanout_sidecar.py"):
            rows[label] = row(
                status="EXPECTED_INHERITED_WINDOWS_RESOURCE_NEGATIVE",
                count=34, failure=True,
                tail="ModuleNotFoundError: No module named 'resource'")
    return {
        "schema": SCHEMA, "controller_source_sha": SOURCE,
        "baseline_commit": BASE, "baseline_tree": TREE,
        "candidate_head": HEAD, "candidate_tree": HEAD_TREE,
        "path": TARGET, "before_sha256": SHA_A, "after_sha256": SHA_B,
        "source_diff_exact_one_file": True,
        "frozen_atlas_maintained": True,
        "modified_candidate_full_regression_pass": False,
        "production_v19_worker_unchanged": True,
        "signed_provider_success": False,
        "scientific_first_use": False, "paid_api_calls": 0,
        "github_writes": 0, "worker_replay": False,
        "resource_accounting": "timing_only; peak RSS unavailable",
        "negative_controls": {
            "second_source_delta_rejected": True,
            "bad_candidate_digest_rejected": True,
        },
        "test_inventory": FILES,
        "results": rows,
        "baseline_g29_pass": True,
        "baseline_full_unmodified_regression_pass": not windows,
        "candidate_changed_source_applicable_tests_pass": not windows,
        "historical_modified_source_g29_negative": True,
        "experimental_split_complete": True,
        "original_full_regression_qualified": not windows,
        "cross_platform_worker_qualified": False,
        "inherited_platform_negatives":
            ["baseline_full", "candidate_test_free_fanout_sidecar.py"]
            if windows else [],
    }


class G31ReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.linux = fixture("linux")
        self.windows = fixture("windows")

    def test_reconciled_diagnostics_never_upgrade_native_or_signed_receipt(self):
        r = reconcile(self.linux, self.windows)
        self.assertTrue(r["diagnostic_reconciliation_complete"])
        for claim in ("native_qualified", "signed_provider_success",
                      "scientific_first_use", "provider_zip_authenticated",
                      "original_owner_consumed_signed_receipt",
                      "production_release_authorized"):
            self.assertIs(r[claim], False)
        self.assertEqual(r["windows_historical_regression"], "NEGATIVE_RETAINED")
        self.assertEqual(r["linux"]["historical_full_regression"], "PASS")

    def test_strict_windows_inherited_resource_failure_preserved(self):
        r = inspect(self.windows, "windows")
        self.assertEqual(r["historical_full_regression"], "NEGATIVE_RETAINED")
        self.assertIs(r["native_qualified"], False)

    def test_linux_baseline_and_applicable_candidate_checks(self):
        r = inspect(self.linux, "linux")
        self.assertEqual(r["changed_source_g29"], "EXPECTED_NEGATIVE")
        self.assertEqual(r["candidate_test_modules"], 4)

    def assert_denied(self, source, platform, edit):
        d = copy.deepcopy(source)
        edit(d)
        with self.assertRaises(G31Denied):
            inspect(d, platform)

    def test_identity_and_authority_negative_matrix(self):
        for key, value in [
            ("schema", "forge.f139.nci04.native-execution-receipt.v1"),
            ("controller_source_sha", "0" * 40),
            ("baseline_commit", "0" * 40),
            ("baseline_tree", "0" * 40),
            ("candidate_head", "0" * 40),
            ("candidate_tree", "0" * 40),
            ("path", "another.py"),
            ("before_sha256", "malformed"),
            ("after_sha256", SHA_A),
            ("source_diff_exact_one_file", False),
            ("frozen_atlas_maintained", False),
            ("experimental_split_complete", False),
            ("baseline_g29_pass", False),
            ("historical_modified_source_g29_negative", False),
            ("modified_candidate_full_regression_pass", True),
            ("cross_platform_worker_qualified", True),
            ("signed_provider_success", True),
            ("production_v19_worker_unchanged", False),
            ("scientific_first_use", True),
            ("worker_replay", True),
            ("github_writes", 1),
            ("paid_api_calls", 1),
            ("resource_accounting", "fabricated_windows_rss"),
            ("original_full_regression_qualified", True),
            ("baseline_full_unmodified_regression_pass", True),
            ("candidate_changed_source_applicable_tests_pass", True),
            ("inherited_platform_negatives", []),
        ]:
            with self.subTest(key=key):
                self.assert_denied(self.windows, "windows",
                                   lambda d, k=key, v=value: d.__setitem__(k, v))

    def test_strict_result_and_coverage_negatives(self):
        mutations = [
            lambda d: d["results"].pop("candidate_test_native_cells.py"),
            lambda d: d["results"]["candidate_test_native_cells.py"].update(
                {"test_count": 0}),
            lambda d: d["results"]["candidate_test_native_cells.py"].update(
                {"status": "SKIPPED"}),
            lambda d: d["results"]["candidate_compile"].update({"exit_code": 1}),
            lambda d: d["results"]["candidate_g29_negative"].update(
                {"status": "PASS"}),
            lambda d: d["results"]["candidate_g29_negative"].update(
                {"output_tail": "unexpected unrelated error"}),
            lambda d: d["results"]["baseline_g29"].update({"test_count": 0}),
            lambda d: d["results"]["candidate_test_native_cells.py"].update(
                {"output_sha256": "bad"}),
            lambda d: d["results"]["candidate_test_native_cells.py"].update(
                {"output_bytes": -1}),
            lambda d: d["negative_controls"].update(
                {"bad_candidate_digest_rejected": False}),
            lambda d: d["test_inventory"].append("test_new_unverified.py"),
            lambda d: d["test_inventory"].remove("test_free_fanout_sidecar.py"),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(negative=i):
                self.assert_denied(self.linux, "linux", mutate)

    def test_windows_specific_fail_closed_matrix(self):
        for mutate in [
            lambda d: d["results"]["baseline_full"].update({"status": "PASS"}),
            lambda d: d["results"]["candidate_test_free_fanout_sidecar.py"].update(
                {"exit_code": 0}),
            lambda d: d["results"]["candidate_test_free_fanout_sidecar.py"].update(
                {"output_tail": "No actual POSIX resource traceback"}),
            lambda d: d["inherited_platform_negatives"].append("candidate_compile"),
        ]:
            self.assert_denied(self.windows, "windows", mutate)

    def test_cross_platform_identity_and_inventory_drift(self):
        mutations = [
            lambda d: d.update({"after_sha256": "d" * 64}),
            lambda d: d.update({"before_sha256": "e" * 64}),
            lambda d: d["test_inventory"].append("test_another.py"),
        ]
        for mutate in mutations:
            w = copy.deepcopy(self.windows)
            mutate(w)
            with self.assertRaises(G31Denied):
                reconcile(self.linux, w)

    def test_swapping_windows_and_linux_not_accepted(self):
        with self.assertRaises(G31Denied):
            reconcile(self.windows, self.linux)


if __name__ == "__main__":
    unittest.main()
