"""G97 48-case frozen-head-budget guard tests, no original model claim."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g97_head_budget import (
    BOUND_INFLATION, DIMENSION, HEADS, KEY_ROWS, OUTPUT_DIM,
    QUERY_COUNT, REGIMES, RELATIVE_TOLERANCE, ROUNDING_AUDIT, SCHEMA,
    SEEDS, SPEEDUP_FLOOR, TRIALS, budget_attention, full_attention,
    head_bounds, make_workload, screen, single_head,
)


class G97Guards(unittest.TestCase):
    def test_frozen_contract(self):
        self.assertEqual(SEEDS, (9701, 9702, 9703))
        self.assertEqual(REGIMES, ("normal", "three_near_zero_heads"))
        self.assertEqual((HEADS, KEY_ROWS, DIMENSION, OUTPUT_DIM, QUERY_COUNT),
                         (8,128,16,64,8))
        self.assertEqual((TRIALS, RELATIVE_TOLERANCE, SPEEDUP_FLOOR), (7,1e-3,1.15))

    def test_both_regimes_and_true_head_bounds(self):
        with threadpool_limits(limits=1):
            for seed in SEEDS:
                for regime in REGIMES:
                    k,v,qs,w=make_workload(seed,regime)
                    self.assertEqual(k.shape, (8,128,16))
                    self.assertEqual(w.shape, (8,16,64))
                    bounds=head_bounds(v,w)
                    for q in qs:
                        for h in range(HEADS):
                            self.assertLessEqual(np.linalg.norm(single_head(k,v,q,w,h)),
                                                 bounds[h]+ROUNDING_AUDIT)
                        reference=full_attention(k,v,q,w)
                        output,props=budget_attention(k,v,q,w,bounds)
                        abs_error=float(np.linalg.norm(reference-output))
                        relative=abs_error/max(float(np.linalg.norm(reference)),1e-12)
                        self.assertLessEqual(relative, RELATIVE_TOLERANCE)
                        self.assertLessEqual(abs_error,
                                             props["certified_absolute_error"]+ROUNDING_AUDIT)
                        self.assertEqual(props["heads_visited"]+props["heads_skipped"],HEADS)

    def test_favorable_regime_only_scales_expected_three_heads(self):
        # Draw order and values are independent per regime. Check actual scales
        # relative to the frozen normal distribution rather than identity of RNG.
        _,_,_,normal=make_workload(SEEDS[0],"normal")
        _,_,_,favorable=make_workload(SEEDS[0],"three_near_zero_heads")
        self.assertTrue(np.array_equal(favorable[:5],normal[:5]))
        self.assertTrue(np.allclose(favorable[5:8],normal[5:8]*1e-6,
                                    rtol=1e-12,atol=0.))

    def test_adversarial_unvisited_values_block_unsafe_pruning(self):
        # Large contribution from the very last head cannot be ignored even
        # if all prior heads produce zero. No predictor-based false certificate.
        with threadpool_limits(limits=1):
            k=np.zeros((HEADS,KEY_ROWS,DIMENSION),dtype=np.float64)
            v=np.zeros_like(k)
            w=np.zeros((HEADS,DIMENSION,OUTPUT_DIM),dtype=np.float64)
            q=np.ones((HEADS,DIMENSION),dtype=np.float64)
            v[7]=10.
            w[7]=1.
            upper=head_bounds(v,w)
            actual,props=budget_attention(k,v,q,w,upper)
            reference=full_attention(k,v,q,w)
            self.assertTrue(np.allclose(actual,reference,rtol=1e-12,atol=1e-12))
            self.assertLessEqual(float(np.linalg.norm(actual-reference)),
                                 props["certified_absolute_error"]+ROUNDING_AUDIT)

    def test_complete_48_case_screen_and_nonclaims(self):
        results=screen()
        self.assertEqual(results["schema"],SCHEMA)
        self.assertEqual(len(results["cases"]),48)
        self.assertEqual(len(results["metadata_initialization"]),6)
        self.assertTrue(all(c["finite"] and c["head_bounds_valid"] and
                            c["certificate_valid"] and c["within_relative_tolerance"]
                            for c in results["cases"]))
        self.assertEqual(results["authentic_model"],"NOT_RUN")
        self.assertEqual(results["gpu_measured"],"NOT_RUN")
        self.assertEqual(results["scientific_acceptance"],"NOT_GRANTED")
        self.assertIn(results["decision"],("NO_GO_SYNTHETIC_SCREEN",
                                         "CONDITIONAL_CPU_FEASIBILITY_ONLY"))


if __name__=="__main__":
    unittest.main()
