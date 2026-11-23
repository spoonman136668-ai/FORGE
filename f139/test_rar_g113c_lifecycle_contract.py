"""RAR-G113C deterministic negative controls; no Win32 calls or process spawn."""
import copy
import unittest

from f139.rar_g113c_lifecycle_contract import (
    LifecycleDenied, assess_untrusted_windows_lifecycle,
)


def trace():
    scope, child = "new-empty-job", "suspended-child"
    names = (
        "job_created_empty", "child_created_suspended", "child_assigned_to_job",
        "child_resumed", "child_and_descendants_exited", "job_accounted", "job_closed",
    )
    events = [{"seq": i, "name": name, "scope_id": scope} for i, name in enumerate(names)]
    events[0].update(job_empty=True, kill_on_job_close=True, breakaway_ok=False,
                     silent_breakaway_ok=False, ui_restrictions=False)
    events[1].update(child_id=child, create_suspended=True, breakaway_creation_flag=False)
    events[2].update(child_id=child, assignment_succeeded=True, nested_job_compatible=True)
    events[3].update(child_id=child, resume_succeeded=True)
    events[4].update(child_id=child, all_descendants_exited=True, exit_code=0)
    events[5].update(total_user_100ns=100, total_kernel_100ns=20,
                     total_processes=2, active_processes=0, peak_job_commit_bytes=8192,
                     includes_parent_job=False, includes_separate_per_process_cpu_sum=False)
    events[6].update(last_handle_closed=True, job_empty_before_close=True)
    return {"schema": "rar.windows-job-lifecycle.v1", "platform": "win32",
            "scope_id": scope, "child_id": child, "events": events}


class RARG113CContractTests(unittest.TestCase):
    def test_nominal_synthetic_trace_never_authorizes_science(self):
        actual = assess_untrusted_windows_lifecycle(trace())
        self.assertTrue(actual["trace_shape_validated"])
        self.assertEqual(actual["kernel_job_cpu_100ns_untrusted"], 120)
        self.assertEqual(actual["peak_job_commit_bytes_untrusted"], 8192)
        self.assertEqual(len(actual["trace_content_sha256"]), 64)
        for name in ("trace_digest_authenticated", "scope_identity_authenticated",
                     "win32_call_outcomes_independently_witnessed",
                     "nested_job_permission_qualified", "all_descendant_membership_qualified",
                     "physical_tree_rss_qualified", "native_training_cost_qualified",
                     "scientific_first_use_authorized", "process_created", "scope_created"):
            self.assertIs(actual[name], False, name)
        self.assertIn("NOT_PHYSICAL_RSS", actual["measurement_semantics"])

    def test_out_of_order_missing_duplicate_or_mixed_scope_denied(self):
        cases = []
        x = trace(); x["events"][2], x["events"][3] = x["events"][3], x["events"][2]; cases.append(x)
        x = trace(); x["events"].pop(1); cases.append(x)
        x = trace(); x["events"][3] = copy.deepcopy(x["events"][2]); cases.append(x)
        x = trace(); x["events"][4]["scope_id"] = "foreign-job"; cases.append(x)
        x = trace(); x["events"][4]["seq"] = True; cases.append(x)
        x = trace(); x["schema"] = "unknown"; cases.append(x)
        x = trace(); x["scientific_first_use_authorized"] = True; cases.append(x)
        x = trace(); x["events"][5]["physical_tree_rss_bytes"] = 1; cases.append(x)
        for case in cases:
            with self.subTest(case=case), self.assertRaises(LifecycleDenied):
                assess_untrusted_windows_lifecycle(case)

    def test_unbound_resumed_or_escaped_descendants_denied(self):
        for index, key, invalid in ((0, "job_empty", False),
                                    (0, "breakaway_ok", True),
                                    (0, "silent_breakaway_ok", True),
                                    (1, "create_suspended", False),
                                    (1, "breakaway_creation_flag", True),
                                    (2, "assignment_succeeded", False),
                                    (2, "nested_job_compatible", False),
                                    (3, "resume_succeeded", False),
                                    (4, "all_descendants_exited", False),
                                    (6, "last_handle_closed", False)):
            case = trace(); case["events"][index][key] = invalid
            with self.subTest(index=index, key=key), self.assertRaises(LifecycleDenied):
                assess_untrusted_windows_lifecycle(case)

    def test_counter_integrity_double_count_and_physical_rss_denied(self):
        for key, invalid in (("total_user_100ns", True),
                             ("total_kernel_100ns", -1),
                             ("total_processes", 0),
                             ("active_processes", 1),
                             ("peak_job_commit_bytes", -1),
                             ("includes_parent_job", True),
                             ("includes_separate_per_process_cpu_sum", True)):
            case = trace(); case["events"][5][key] = invalid
            with self.subTest(key=key), self.assertRaises(LifecycleDenied):
                assess_untrusted_windows_lifecycle(case)
        case = trace(); case["events"][5]["total_user_100ns"] = (1 << 63) - 1
        with self.assertRaises(LifecycleDenied):
            assess_untrusted_windows_lifecycle(case)


if __name__ == "__main__":
    unittest.main()
