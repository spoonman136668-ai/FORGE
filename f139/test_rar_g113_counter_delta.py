"""RAR-G113A deterministic scope contamination and metric-label controls."""
import copy
import unittest

from f139.rar_g113_counter_delta import ScopeDeltaDenied, diagnostic_delta

FLAGS = {
    "counter_available": True,
    "exclusive_experiment_membership_verified": False,
    "short_lived_descendants_accounted_for_exclusively": False,
    "complete_native_training_cpu_rss_qualified": False,
    "scientific_first_use_authorized": False,
    "process_created": False,
}


def linux(cpu, peak=500, current=200):
    return dict(FLAGS, platform="linux", method="linux_cgroup_v2_read_only",
                cpu_scope="CGROUP_INCLUDING_DESCENDANTS_AND_OTHER_MEMBERS",
                memory_scope="CGROUP_CHARGED_MEMORY_NOT_PROCESS_TREE_RSS",
                scope_key="caller-supplied-not-authenticated", cpu_usage_usec=cpu,
                memory_peak_bytes=peak, memory_current_bytes=current,
                direct_process_count=7)


def windows(user, kernel, total=648):
    return dict(FLAGS, platform="win32", method="windows_immediate_job_accounting_read_only",
                cpu_scope="IMMEDIATE_EXISTING_JOB_INCLUDING_PRIOR_MEMBERS",
                memory_scope="WINDOWS_JOB_PEAK_COMMIT_NOT_PHYSICAL_RSS",
                scope_key="caller-supplied-not-authenticated", total_user_100ns=user,
                total_kernel_100ns=kernel, total_processes=total, active_processes=10)


class RARG113ADeltaTests(unittest.TestCase):
    def test_linux_shared_cpu_is_diagnostic_not_training_cost(self):
        result = diagnostic_delta(linux(100), linux(195, peak=700, current=250))
        self.assertEqual(result["cpu_delta_nonexclusive"], 95)
        self.assertEqual(result["cpu_unit"], "microseconds")
        self.assertEqual(result["existing_scope_memory_peak"], 700)
        self.assertFalse(result["native_training_cost_qualified"])
        self.assertFalse(result["physical_tree_rss_qualified"])
        self.assertFalse(result["caller_scope_key_authenticated"])

    def test_windows_cumulative_cpu_diagnostic_excludes_rss_claim(self):
        result = diagnostic_delta(windows(100, 150), windows(160, 230, 649))
        self.assertEqual(result["cpu_delta_nonexclusive"], 140)
        self.assertEqual(result["cpu_unit"], "100ns")
        self.assertIsNone(result["existing_scope_memory_peak"])
        self.assertFalse(result["native_training_cost_qualified"])

    def test_scope_or_counter_contamination_fails_closed(self):
        a, b = linux(100), linux(110)
        for field, value in (("scope_key", "different"), ("method", "wrong"),
                             ("cpu_scope", "wrong"), ("platform", "win32"),
                             ("memory_scope", "wrong"), ("counter_available", False),
                             ("exclusive_experiment_membership_verified", True),
                             ("process_created", True), ("scientific_first_use_authorized", True),
                             ("cpu_usage_usec", -1), ("memory_current_bytes", 1000),
                             ("direct_process_count", -1)):
            wrong = copy.deepcopy(b)
            wrong[field] = value
            with self.subTest(field=field), self.assertRaises(ScopeDeltaDenied):
                diagnostic_delta(a, wrong)
        with self.assertRaises(ScopeDeltaDenied):
            diagnostic_delta(linux(100), linux(99))
        with self.assertRaises(ScopeDeltaDenied):
            diagnostic_delta(linux(100, peak=500), linux(110, peak=499))
        # Each independent Windows CPU counter must be monotone; a larger
        # second component must not conceal regression in the first.
        with self.assertRaises(ScopeDeltaDenied):
            diagnostic_delta(windows(100, 100), windows(90, 200))
        with self.assertRaises(ScopeDeltaDenied):
            diagnostic_delta(windows(100, 100), windows(200, 90))
        with self.assertRaises(ScopeDeltaDenied):
            diagnostic_delta(windows(100, 200, 648), windows(200, 200, 647))

    def test_historical_shared_accounting_cannot_prove_speedup(self):
        before, after = linux(31_359_806), linux(31_359_900)
        result = diagnostic_delta(before, after)
        self.assertEqual(result["classification"],
                         "NONEXCLUSIVE_READ_ONLY_DIAGNOSTIC_NOT_TRAINING_COST")
        self.assertFalse(result["complete_descendant_lifetime_accounting"])
        self.assertFalse(result["exclusive_experiment_membership_verified"])
        self.assertFalse(result["scientific_first_use_authorized"])


if __name__ == "__main__":
    unittest.main()
