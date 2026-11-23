"""RAR-G113D deterministic, no-kernel-call explicit-handle accounting tests."""
import ctypes
import sys
import unittest

from f139.rar_g113d_job_readback import (
    BASIC_ACCOUNTING, EXTENDED_LIMITS, JobReadbackDenied,
    JOB_OBJECT_LIMIT_BREAKAWAY_OK, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK, read_job_accounting,
)


def fake_query(*, user=100, kernel=20, total=3, active=0, terminated=3,
               peak=8192, flags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
               malformed=False):
    def get(handle, info_class, record_type):
        if malformed:
            return object()
        record = record_type()
        if info_class == 1:
            record.TotalUserTime = user
            record.TotalKernelTime = kernel
            record.TotalProcesses = total
            record.ActiveProcesses = active
            record.TotalTerminatedProcesses = terminated
        elif info_class == 9:
            record.BasicLimitInformation.LimitFlags = flags
            record.PeakJobMemoryUsed = peak
        else:
            raise AssertionError("unexpected class")
        return record
    return get


class RARG113DJobReadbackTests(unittest.TestCase):
    def test_explicit_job_readback_remains_unqualified(self):
        result = read_job_accounting(123, query=fake_query())
        self.assertEqual(result["kernel_job_cpu_100ns_nonexclusive_until_witnessed"], 120)
        self.assertEqual(result["job_total_processes"], 3)
        self.assertEqual(result["job_peak_memory_bytes_not_physical_rss"], 8192)
        for name in ("scope_handle_authenticated", "exclusive_experiment_membership_verified",
                     "short_lived_descendants_exclusively_accounted",
                     "physical_tree_rss_qualified", "native_training_cost_qualified",
                     "scientific_first_use_authorized", "process_created", "scope_created",
                     "original_controller_changed"):
            self.assertFalse(result[name], name)
        self.assertIn("NOT_PHYSICAL_TREE_RSS", result["memory_semantics"])

    def test_zero_noninteger_or_out_of_range_handle_denied(self):
        for handle in (None, 0, -1, True, "123", (1 << (ctypes.sizeof(ctypes.c_void_p) * 8))):
            with self.subTest(handle=handle), self.assertRaises(JobReadbackDenied):
                read_job_accounting(handle, query=fake_query())

    def test_bad_job_policy_active_process_and_untrusted_struct_denied(self):
        for args in (
            {"flags": 0},
            {"flags": JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_BREAKAWAY_OK},
            {"flags": JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK},
            {"active": 1}, {"total": 0}, {"total": 1, "terminated": 3},
            {"user": -1}, {"kernel": -1}, {"user": (1 << 63) - 1, "kernel": 2},
            {"malformed": True},
        ):
            with self.subTest(args=args), self.assertRaises(JobReadbackDenied):
                read_job_accounting(123, query=fake_query(**args))

    def test_nonwindows_native_read_denied_and_win_layout(self):
        if sys.platform != "win32":
            with self.assertRaises(JobReadbackDenied):
                read_job_accounting(123)
        else:
            self.assertEqual(ctypes.sizeof(BASIC_ACCOUNTING), 48)
            self.assertEqual(ctypes.sizeof(EXTENDED_LIMITS), 144)
        # Test-only untrusted reader may inspect a running job without
        # asserting that it covers an exclusive experiment.
        result = read_job_accounting(123, query=fake_query(active=2, terminated=1),
                                     require_quiescent=False)
        self.assertFalse(result["native_training_cost_qualified"])
        self.assertEqual(result["job_active_processes"], 2)


if __name__ == "__main__":
    unittest.main()
