"""G94 deterministic correctness and frozen-protocol guards (no model/GPU)."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g94_delta_projection import (
    CHANGED_COORDINATES, DIM_IN, DIM_OUT, ERROR_LIMIT, REGIMES, SCHEMA,
    SEEDS, SPEEDUP_FLOOR, TRANSITIONS, TRIALS, dense_sequence,
    delta_sequence, generate, screen,
)


class G94Guards(unittest.TestCase):
    def test_frozen_protocol(self):
        self.assertEqual(SEEDS, (9401, 9402, 9403))
        self.assertEqual(REGIMES, ("iid", "exact_sparse"))
        self.assertEqual((DIM_IN, DIM_OUT, TRANSITIONS), (256, 512, 16))
        self.assertEqual((CHANGED_COORDINATES, TRIALS), (8, 9))
        self.assertEqual((ERROR_LIMIT, SPEEDUP_FLOOR), (1e-9, 1.15))

    def test_delta_support_and_exact_identity(self):
        with threadpool_limits(limits=1):
            for regime in REGIMES:
                for seed in SEEDS:
                    weights, states = generate(seed, regime)
                    self.assertEqual(states.shape, (17, 256))
                    baseline = dense_sequence(weights, states)
                    candidate = delta_sequence(weights, states)
                    self.assertEqual(len(candidate), 17)
                    for t in range(1, 17):
                        with self.subTest(regime=regime, seed=seed, t=t):
                            count = np.count_nonzero(states[t] - states[t-1])
                            if regime == "exact_sparse":
                                self.assertEqual(count, 8)
                            else:
                                self.assertEqual(count, 256)
                            error = float(np.linalg.norm(candidate[t] - baseline[t]) /
                                          max(float(np.linalg.norm(baseline[t])), 1e-12))
                            self.assertLessEqual(error, ERROR_LIMIT)

    def test_complete_screen_custody(self):
        output = screen()
        self.assertEqual(output["schema"], SCHEMA)
        self.assertEqual(len(output["cases"]), 96)
        self.assertEqual(len(output["sequence_timings"]), 6)
        self.assertTrue(all(c["within_error_limit"] for c in output["cases"]))
        self.assertEqual(output["authentic_model"], "NOT_RUN")
        self.assertEqual(output["gpu_performance"], "NOT_RUN")
        self.assertEqual(output["scientific_acceptance"], "NOT_GRANTED")
        self.assertIn(output["decision"], ("NO_GO_SYNTHETIC_SCREEN",
                                          "CONDITIONAL_FEASIBILITY_ONLY"))


if __name__ == "__main__":
    unittest.main()
