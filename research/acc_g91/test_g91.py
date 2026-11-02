"""G91 CPU screening contracts; technical validity, not scientific acceptance."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g91_certified_vocab import (
    DIMENSION, GROUPS, GROUP_ROWS, REGIMES, SEEDS, SLACK, TRIALS,
    bounds_setup, build_case, certified_projection, dense_projection, screen,
)


class G91Guards(unittest.TestCase):
    def test_frozen_parameters(self):
        self.assertEqual((DIMENSION, GROUPS, GROUP_ROWS, TRIALS), (128, 64, 128, 7))
        self.assertEqual(SEEDS, (9101, 9102, 9103))
        self.assertEqual(REGIMES, ("iid", "clustered"))

    def test_bounds_and_exact_winner_all_workloads(self):
        with threadpool_limits(limits=1):
            for regime in REGIMES:
                for seed in SEEDS:
                    weights, queries, labels = build_case(seed, regime)
                    centers, radii = bounds_setup(weights)
                    self.assertEqual(len(queries), 8)
                    self.assertEqual(len(labels), 8)
                    flat = weights.reshape(-1, DIMENSION)
                    for query in queries:
                        upper = centers @ query + radii * np.linalg.norm(query)
                        group_actual = (weights @ query).max(axis=1)
                        self.assertTrue(np.all(group_actual <= upper + SLACK * (1 + np.abs(upper))))
                        baseline_index, _ = dense_projection(flat, query)
                        candidate_index, _, rows = certified_projection(weights, centers, radii, query)
                        self.assertEqual(candidate_index, baseline_index)
                        self.assertGreater(rows, 0)
                        self.assertLessEqual(rows, GROUPS * GROUP_ROWS)

    def test_negative_regime_is_not_aligned(self):
        _, _, labels = build_case(SEEDS[0], "iid")
        self.assertEqual(labels, ["random"] * 8)

    def test_full_screen_contract(self):
        result = screen()
        self.assertEqual(len(result["cases"]), 48)
        self.assertEqual(len(result["initialization_ms"]), 6)
        self.assertTrue(all(x["exact_index"] for x in result["cases"]))
        self.assertEqual(result["scientific_acceptance"], "NOT_GRANTED")
        self.assertEqual(result["gpu_model_evidence"], "NOT_RUN")
        self.assertIn(result["decision"], ("NO_GO_SYNTHETIC_SCREEN", "CONDITIONAL_FEASIBILITY_ONLY"))


if __name__ == "__main__":
    unittest.main()
