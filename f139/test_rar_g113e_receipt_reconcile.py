"""RAR-G113E cross-interface negative controls with existing G113C/D fixtures."""
import copy
import unittest

from f139.rar_g113d_job_readback import read_job_accounting
from f139.rar_g113e_receipt_reconcile import (
    ReconcileDenied, reconcile_untrusted_windows_receipts,
)
from f139.test_rar_g113c_lifecycle_contract import trace
from f139.test_rar_g113d_job_readback import fake_query


def pair():
    lifecycle = trace()
    # Match the G113C fixture's user/kernel CPU, count and peak commit.
    readback = read_job_accounting(123, query=fake_query(
        user=100, kernel=20, total=2, active=0, terminated=2, peak=8192,
    ))
    return lifecycle, readback


class RARG113EReconcileTests(unittest.TestCase):
    def test_matched_synthetic_receipts_still_deny_science(self):
        lifecycle, readback = pair()
        result = reconcile_untrusted_windows_receipts(lifecycle, readback)
        self.assertTrue(result["candidate_counter_consistency_only"])
        self.assertEqual(len(result["pair_content_sha256"]), 64)
        self.assertEqual(result, reconcile_untrusted_windows_receipts(lifecycle, readback))
        self.assertNotIn("native_training_cpu_100ns", result)
        for name in ("content_digest_authenticated", "experiment_scope_authenticated",
                     "win32_call_outcomes_independently_witnessed",
                     "exclusive_experiment_membership_verified",
                     "complete_short_lived_descendants_qualified",
                     "physical_tree_rss_qualified", "native_training_cost_qualified",
                     "scientific_first_use_authorized", "process_created",
                     "scope_created", "original_controller_changed"):
            self.assertFalse(result[name], name)

    def test_cpu_component_swap_denied_even_when_sum_agrees(self):
        lifecycle, readback = pair()
        # Prevent a swapped total or compensating increase from hiding a
        # mismatched Windows user/kernel component.
        for user, kernel in ((90, 30), (110, 10), (100, 21)):
            mismatch = copy.deepcopy(readback)
            mismatch["job_total_user_100ns"] = user
            mismatch["job_total_kernel_100ns"] = kernel
            with self.subTest(user=user, kernel=kernel), self.assertRaises(ReconcileDenied):
                reconcile_untrusted_windows_receipts(lifecycle, mismatch)

    def test_scope_contamination_peak_process_and_schema_denied(self):
        lifecycle, readback = pair()
        for key, value in (("job_total_processes", 3),
                           ("job_active_processes", 1),
                           ("job_peak_memory_bytes_not_physical_rss", 8193),
                           ("kernel_job_cpu_100ns_nonexclusive_until_witnessed", 121),
                           ("job_terminated_processes", 3),
                           ("memory_semantics", "PHYSICAL_RSS"),
                           ("scope_handle_authenticated", True),
                           ("native_training_cost_qualified", True),
                           ("job_total_user_100ns", True)):
            mutated = copy.deepcopy(readback)
            mutated[key] = value
            with self.subTest(key=key), self.assertRaises(ReconcileDenied):
                reconcile_untrusted_windows_receipts(lifecycle, mutated)
        mutated = copy.deepcopy(readback)
        mutated["extra_science_authority"] = True
        with self.assertRaises(ReconcileDenied):
            reconcile_untrusted_windows_receipts(lifecycle, mutated)

    def test_lifecycle_bypass_or_forged_receipts_denied(self):
        lifecycle, readback = pair()
        for idx, field, value in ((0, "kill_on_job_close", False),
                                  (1, "create_suspended", False),
                                  (2, "assignment_succeeded", False),
                                  (4, "all_descendants_exited", False),
                                  (5, "includes_parent_job", True)):
            mutated = copy.deepcopy(lifecycle)
            mutated["events"][idx][field] = value
            with self.subTest(idx=idx, field=field), self.assertRaises(ReconcileDenied):
                reconcile_untrusted_windows_receipts(mutated, readback)
        with self.assertRaises(ReconcileDenied):
            reconcile_untrusted_windows_receipts(lifecycle, {})
        with self.assertRaises(ReconcileDenied):
            reconcile_untrusted_windows_receipts(None, readback)


if __name__ == "__main__":
    unittest.main()
