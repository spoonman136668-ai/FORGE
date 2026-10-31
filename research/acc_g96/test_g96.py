"""G96 certificate and frozen-control tests; CPU synthetic only."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g96_attention_bounds import (
    BLOCKS, BLOCK_ROWS, DIMENSION, ERROR_TOLERANCE, KEY_ROWS, QUERY_COUNT,
    REGIMES, ROUNDING_AUDIT, SCHEMA, SEEDS, SPEEDUP_FLOOR, TRIALS,
    block_metadata, block_upper_bounds, certified_attention, dense_attention,
    make_workload, screen,
)


class G96Guards(unittest.TestCase):
    def test_frozen_parameters(self):
        self.assertEqual(SEEDS, (9601, 9602, 9603))
        self.assertEqual(REGIMES, ("iid", "clustered_aligned"))
        self.assertEqual((DIMENSION, KEY_ROWS, BLOCK_ROWS, BLOCKS, QUERY_COUNT),
                         (64, 1024, 64, 16, 8))
        self.assertEqual(TRIALS, 7)
        self.assertEqual((ERROR_TOLERANCE,SPEEDUP_FLOOR), (1e-3, 1.15))

    def test_bound_and_error_certificate_on_every_query(self):
        with threadpool_limits(limits=1):
            for regime in REGIMES:
                for seed in SEEDS:
                    keys, values, queries = make_workload(seed, regime)
                    centers, radii, v_norm = block_metadata(keys, values)
                    for query in queries:
                        with self.subTest(seed=seed, regime=regime):
                            bounds = block_upper_bounds(centers, radii, query)
                            actuals = np.asarray([
                                ((keys[g*BLOCK_ROWS:(g+1)*BLOCK_ROWS] @ query) /
                                 np.sqrt(DIMENSION)).max() for g in range(BLOCKS)
                            ])
                            self.assertTrue(np.all(actuals <= bounds + ROUNDING_AUDIT))
                            base = dense_attention(keys, values, query)
                            estimate, props = certified_attention(keys, values, query,
                                                                 centers, radii, v_norm)
                            absolute = float(np.linalg.norm(base-estimate))
                            relative = absolute/max(float(np.linalg.norm(base)),1e-12)
                            self.assertLessEqual(relative,ERROR_TOLERANCE)
                            self.assertLessEqual(
                                absolute, props["certified_absolute_error"] + ROUNDING_AUDIT)
                            self.assertTrue(1 <= props["blocks_scored"] <= BLOCKS)
                            self.assertEqual(props["rows_scored"],
                                             props["blocks_scored"]*BLOCK_ROWS)

    def test_negative_control_is_independent_gaussian(self):
        keys, values, queries = make_workload(SEEDS[0], "iid")
        self.assertEqual(keys.shape, (1024, 64))
        self.assertEqual(values.shape, (1024, 64))
        self.assertEqual(queries.shape, (8, 64))
        self.assertFalse(np.array_equal(keys[:64], keys[64:128]))

    def test_complete_screen_and_scientific_nonclaims(self):
        output = screen()
        self.assertEqual(output["schema"], SCHEMA)
        self.assertEqual(len(output["cases"]), 48)
        self.assertEqual(len(output["metadata_initialization"]), 6)
        self.assertTrue(all(c["finite"] and c["certificate_valid"] and
                            c["upper_bound_valid"] and c["within_error_limit"]
                            for c in output["cases"]))
        self.assertEqual(output["authentic_model"], "NOT_RUN")
        self.assertEqual(output["gpu_measured"], "NOT_RUN")
        self.assertEqual(output["scientific_acceptance"], "NOT_GRANTED")
        self.assertIn(output["decision"], ("NO_GO_SYNTHETIC_SCREEN",
                                          "CONDITIONAL_CPU_FEASIBILITY_ONLY"))


if __name__ == "__main__":
    unittest.main()
