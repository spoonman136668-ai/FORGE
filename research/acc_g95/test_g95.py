"""G95 exact RoPE replay/negative control contracts, not GPU scientific proof."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g95_rope_replay import (
    DIMENSION, MAX_ABS_ERROR, MOTIF_LENGTH, REGIMES, SCHEMA, SEEDS, SHIFTS,
    SPEEDUP_FLOOR, TRIALS, baseline, candidate, rope, screen, seed_workloads,
)


class G95Guards(unittest.TestCase):
    def test_frozen_parameters(self):
        self.assertEqual(SEEDS, (9501, 9502, 9503))
        self.assertEqual(SHIFTS, (17, 73, 511, 4097))
        self.assertEqual(REGIMES, ("identical_pre_rope", "context_drift"))
        self.assertEqual((DIMENSION, MOTIF_LENGTH, TRIALS), (64, 16, 15))
        self.assertEqual((MAX_ABS_ERROR, SPEEDUP_FLOOR), (1e-9, 1.15))

    def test_relative_rotation_identity_all_shifts(self):
        with threadpool_limits(limits=1):
            for seed in SEEDS:
                q, k, drift = seed_workloads(seed)
                source = rope(q, 0) @ rope(k, 0).T
                for shift in SHIFTS:
                    target = rope(q, shift) @ rope(k, shift).T
                    self.assertLessEqual(np.max(np.abs(target - source)), MAX_ABS_ERROR)

    def test_context_drift_never_uses_replay(self):
        with threadpool_limits(limits=1):
            for seed in SEEDS:
                q, k, drift = seed_workloads(seed)
                for shift, (other_q, other_k) in zip(SHIFTS, drift):
                    b0, b1 = baseline(q, k, other_q, other_k, shift)
                    a0, a1, reused = candidate(q, k, other_q, other_k, shift)
                    self.assertFalse(reused)
                    self.assertTrue(np.array_equal(b0, a0))
                    self.assertTrue(np.array_equal(b1, a1))
                _, _, reused = candidate(q, k, q.copy(), k.copy(), SHIFTS[0])
                self.assertTrue(reused)

    def test_full_24_case_screen(self):
        with threadpool_limits(limits=1):
            result = screen()
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(len(result["cases"]), 24)
        self.assertTrue(all(x["within_error_limit"] for x in result["cases"]))
        self.assertEqual(result["summary"]["identical_pre_rope"]["cache_hits"], 12)
        self.assertEqual(result["summary"]["context_drift"]["cache_hits"], 0)
        self.assertEqual(result["authentic_model"], "NOT_RUN")
        self.assertEqual(result["gpu_performance"], "NOT_RUN")
        self.assertEqual(result["scientific_acceptance"], "NOT_GRANTED")
        self.assertIn(result["decision"], ("NO_GO_SYNTHETIC_SCREEN", "CONDITIONAL_FEASIBILITY_ONLY"))


if __name__ == "__main__":
    unittest.main()
