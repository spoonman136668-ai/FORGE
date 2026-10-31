"""G103 fixed-shape dispatch protocol and 192-case correctness guards."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g103_shape_dispatch import (
    ERROR_LIMIT, QUERIES, REGIMES, SCHEMA, SEEDS, SHAPES, SMALL_SIZE_LIMIT,
    SPARSE_ZERO_RATE, SPEEDUP_FLOOR, TRIALS, baseline, dispatched,
    make_workload, screen,
)


class G103Guards(unittest.TestCase):
    def test_frozen_shape_contract(self):
        self.assertEqual(SEEDS, (10301, 10302, 10303))
        self.assertEqual(SHAPES, (("tiny",32,32),("skinny",2048,32),
                                  ("wide",64,2048),("balanced",512,512)))
        self.assertEqual(REGIMES,("dense_iid","sparse_zero"))
        self.assertEqual((QUERIES,TRIALS,SMALL_SIZE_LIMIT),(8,9,4096))
        self.assertEqual((SPARSE_ZERO_RATE,ERROR_LIMIT,SPEEDUP_FLOOR),(.9,1e-10,1.15))

    def test_selected_path_and_equivalent_outputs(self):
        with threadpool_limits(limits=1):
            for name,rows,cols in SHAPES:
                for regime in REGIMES:
                    w,queries=make_workload(SEEDS[0],name,regime)
                    self.assertEqual(w.shape,(rows,cols))
                    self.assertEqual(queries.shape,(QUERIES,cols))
                    for query in queries:
                        base=baseline(w,query)
                        candidate=dispatched(w,query)
                        relative=float(np.linalg.norm(candidate-base) /
                                       max(float(np.linalg.norm(base)),1e-12))
                        self.assertLessEqual(relative,ERROR_LIMIT)

    def test_controls_share_initial_dense_weights(self):
        for name,_,_ in SHAPES:
            w_dense,q_dense=make_workload(SEEDS[0],name,"dense_iid")
            w_sparse,q_sparse=make_workload(SEEDS[0],name,"sparse_zero")
            self.assertTrue(np.array_equal(q_dense,q_sparse))
            self.assertTrue(np.all((w_sparse==w_dense)|(w_sparse==0)))
            self.assertGreater(np.count_nonzero(w_sparse==0),w_sparse.size*.80)

    def test_complete_screen_and_nonclaims(self):
        data=screen()
        self.assertEqual(data["schema"],SCHEMA)
        self.assertEqual(len(data["cases"]),192)
        self.assertTrue(all(c["finite"] and c["within_error_limit"] for c in data["cases"]))
        self.assertEqual(data["authentic_model"],"NOT_RUN")
        self.assertEqual(data["gpu_measured"],"NOT_RUN")
        self.assertEqual(data["scientific_acceptance"],"NOT_GRANTED")
        self.assertIn(data["decision"],("NO_GO_SYNTHETIC_SCREEN",
                                       "CONDITIONAL_CPU_FEASIBILITY_ONLY"))


if __name__=="__main__":
    unittest.main()
