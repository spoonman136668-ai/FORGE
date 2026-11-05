"""Frozen G101 final-mechanism verdict and negative-control tests."""
import unittest
from research.cpu_g97.g101_final_diagnostic import (
    BACKENDS, PATTERN, final_verdict, pair_report, PAIRS_PER_BACKEND)


class FinalDecisionTests(unittest.TestCase):
    @staticmethod
    def arm(exact=True):
        return {"pairs": [{"exact": exact} for _ in range(PAIRS_PER_BACKEND)],
                "generated_token_parity": True,
                "model_calls": len(PATTERN) * 8,
                "extra_prefix_forwards": 0,
                "max_resident_kv_bytes": 86114304}

    def test_retire_when_both_backends_not_exact(self):
        verdict, feasible = final_verdict({b: self.arm(False) for b in BACKENDS})
        self.assertEqual((verdict, feasible), ("RETIRE_G101_EXACT_CAPTURE", []))

    def test_one_strictly_exact_backend_only_marks_feasible(self):
        a = {BACKENDS[0]: self.arm(False), BACKENDS[1]: self.arm(True)}
        decision, feasible = final_verdict(a)
        self.assertEqual((decision, feasible), ("EXACT_CAPTURE_FEASIBLE", ["eager"]))
        a["eager"]["pairs"][9]["exact"] = False
        self.assertEqual(final_verdict(a)[0], "RETIRE_G101_EXACT_CAPTURE")

    def test_incomplete_matrix_rejected_not_a_false_retirement(self):
        with self.assertRaisesRegex(RuntimeError, "MISSING_BACKEND"):
            final_verdict({"sdpa": self.arm(False)})
        a = {b: self.arm(False) for b in BACKENDS}
        a["eager"]["pairs"].pop()
        with self.assertRaisesRegex(RuntimeError, "INCOMPLETE_PAIR_MATRIX"):
            final_verdict(a)

    def test_token_forward_and_residency_guards(self):
        for name, value, marker in (
            ("generated_token_parity", False, "TOKEN_PARITY"),
            ("model_calls", 79, "FORWARD_COUNT"),
            ("extra_prefix_forwards", 1, "HIDDEN_PREFIX"),
            ("max_resident_kv_bytes", 86114305, "MEMORY_CAP")):
            a = {b: self.arm(False) for b in BACKENDS}
            a["sdpa"][name] = value
            with self.assertRaisesRegex(RuntimeError, marker):
                final_verdict(a)


if __name__ == "__main__":
    unittest.main()
