"""Negative-custody tests: six-method readiness must refuse premature evaluation."""
import unittest
from itd02_r8_six_method_readiness import assess_readiness, require_complete_readiness

class SixMethodReadinessTests(unittest.TestCase):
    def test_exact_blockers(self):
        result = assess_readiness()
        self.assertEqual(result["methods_count"], 6)
        self.assertEqual(result["source_only_ready_count"], 1)
        self.assertEqual(result["blocked_count"], 5)
        self.assertFalse(result["full_comparison_ready"])
        self.assertFalse(result["first_use_authorized"])
        self.assertFalse(result["scientific_accepted"])
        self.assertEqual(result["methods"]["sixfield_fit_model_route"]["status"], "READY_SOURCE_ONLY")

    def test_native_ablation_not_impersonated_by_statistical_control(self):
        self.assertEqual(assess_readiness()["methods"]["r8_previous_action_ablated"]["status"],
                         "BLOCKED_NATIVE_ABLATION")

    def test_fail_closed(self):
        with self.assertRaisesRegex(RuntimeError, "R8_SIX_METHODS_NOT_QUALIFIED"):
            require_complete_readiness()

if __name__ == "__main__":
    unittest.main()
