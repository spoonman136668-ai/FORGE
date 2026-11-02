"""G101 deterministic contract checks; synthetic CPU only."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g101_residual_forecast import (
    DIMENSION, ERROR_LIMIT, LAYERS, QUERIES, RANKS, REGIMES, SCHEMA,
    SEEDS, SPEEDUP_FLOOR, TRIALS,
    fit_forecasters, full_forward, make_workload, predicted_forward, screen,
)


class G101Guards(unittest.TestCase):
    def test_frozen_protocol(self):
        self.assertEqual(SEEDS, (10101,10102,10103))
        self.assertEqual(REGIMES, ("iid","paired_correlated"))
        self.assertEqual(RANKS, (8,16))
        self.assertEqual((DIMENSION,LAYERS,QUERIES,TRIALS), (128,12,8,7))
        self.assertEqual((ERROR_LIMIT,SPEEDUP_FLOOR), (1e-3,1.15))

    def test_fixed_weight_identity_and_all_shapes(self):
        with threadpool_limits(limits=1):
            weights, queries = make_workload(SEEDS[0], "iid")
            self.assertEqual(weights.shape,(LAYERS,DIMENSION,DIMENSION))
            self.assertEqual(queries.shape,(QUERIES,DIMENSION))
            for rank in RANKS:
                left,right,errors = fit_forecasters(weights,rank)
                self.assertEqual(len(left),LAYERS//2)
                self.assertEqual(len(right),LAYERS//2)
                self.assertEqual(len(errors),LAYERS//2)
                self.assertEqual(left[0].shape,(DIMENSION,rank))
                self.assertEqual(right[0].shape,(rank,DIMENSION))
                out=predicted_forward(weights,(left,right,errors),queries[0])
                self.assertEqual(out.shape,(DIMENSION,))
                self.assertTrue(np.all(np.isfinite(out)))

    def test_zero_weights_cannot_invent_residuals(self):
        with threadpool_limits(limits=1):
            weights=np.zeros((LAYERS,DIMENSION,DIMENSION),dtype=np.float64)
            initial=np.arange(DIMENSION,dtype=np.float64)/DIMENSION
            for rank in RANKS:
                f=fit_forecasters(weights,rank)
                self.assertTrue(np.array_equal(full_forward(weights,initial),initial))
                self.assertTrue(np.array_equal(predicted_forward(weights,f,initial),initial))

    def test_favorable_not_claimed_real_layer_structure(self):
        normal,_=make_workload(SEEDS[0],"iid")
        favorable,_=make_workload(SEEDS[0],"paired_correlated")
        normal_gap=float(np.linalg.norm(normal[1]-normal[0]))
        favorable_gap=float(np.linalg.norm(favorable[1]-favorable[0]))
        self.assertLess(favorable_gap,normal_gap*.05)

    def test_full_screen_and_no_false_authentic_claim(self):
        with threadpool_limits(limits=1):
            data=screen()
        self.assertEqual(data["schema"],SCHEMA)
        self.assertEqual(len(data["cases"]),96)
        self.assertEqual(len(data["setup"]),12)
        self.assertTrue(all(c["finite"] and c["candidate_dense_matvecs"]==6 and
                            c["candidate_rank_corrections"]==6 for c in data["cases"]))
        self.assertEqual(data["gpu_measured"],"NOT_RUN")
        self.assertEqual(data["authentic_model"],"NOT_RUN")
        self.assertEqual(data["scientific_acceptance"],"NOT_GRANTED")
        self.assertIn(data["decision"],("NO_GO_SYNTHETIC_SCREEN",
                                       "CONDITIONAL_CPU_FEASIBILITY_ONLY"))


if __name__=="__main__":
    unittest.main()
