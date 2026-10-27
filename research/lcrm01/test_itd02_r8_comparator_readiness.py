"""Fail-closed comparator readiness and observation-budget regression."""
import unittest
from itd02_r8_six_method_readiness import assess_readiness, require_complete_readiness

class ComparatorReadinessTest(unittest.TestCase):
    def test_six_methods_and_three_blockers(self):
        report=assess_readiness()
        self.assertEqual(report["methods_count"],6)
        self.assertEqual(report["source_only_ready_count"],3)
        self.assertEqual(set(report["blocked"]),{
            "independent_conditional_beta",
            "fit_dynamics_bfs_equal_information",
            "r8_previous_action_ablated",
        })
        self.assertFalse(report["full_comparison_ready"])
        self.assertFalse(report["first_use_authorized"])
        self.assertFalse(report["scientific_accepted"])
    def test_missing_comparators_prohibit_original_world_comparison(self):
        with self.assertRaisesRegex(RuntimeError,"R8_SIX_METHODS_NOT_QUALIFIED"):
            require_complete_readiness()
    def test_full_map_control_never_misrepresented_as_equal_information(self):
        row=assess_readiness()["methods"]["fit_dynamics_bfs_equal_information"]
        self.assertEqual(row["status"],"BLOCKED_EQUAL_INFORMATION_BFS")

if __name__=="__main__":
    unittest.main()
