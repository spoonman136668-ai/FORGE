"""G105 frozen route/fallback controls, no authentic model or GPU."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g105_precision_route import (
    COLUMNS, GAMMA, QUERIES, REGIMES, ROWS, SCHEMA, SEEDS,
    SPEEDUP_FLOOR, TRIALS, exact, make_workload,
    routed, screen, setup_bound,
)


class G105Guards(unittest.TestCase):
    def test_frozen_parameters(self):
        self.assertEqual(SEEDS,(10501,10502,10503))
        self.assertEqual(REGIMES,("iid","hard_near_tie"))
        self.assertEqual((ROWS,COLUMNS,QUERIES,TRIALS),(512,256,8,9))
        self.assertEqual(SPEEDUP_FLOOR,1.15)
        self.assertGreater(GAMMA,0)

    def test_full_precision_reference_parity_all_seeded_queries(self):
        with threadpool_limits(limits=1):
            for seed in SEEDS:
                for regime in REGIMES:
                    w,biases,queries=make_workload(seed,regime)
                    self.assertEqual(w.shape,(ROWS,COLUMNS))
                    self.assertEqual(biases.shape,(ROWS,))
                    self.assertEqual(queries.shape,(QUERIES,COLUMNS))
                    norm=setup_bound(w)
                    for q in queries:
                        reference,_=exact(w,biases,q)
                        predicted,props=routed(w,biases,q,norm)
                        self.assertEqual(predicted,reference)
                        self.assertIn(props["chosen_precision"],("float32","float64"))
                        self.assertGreaterEqual(props["rounding_budget"],0)

    def test_adversarial_tie_falls_back_without_invalid_certificate(self):
        with threadpool_limits(limits=1):
            weights=np.zeros((ROWS,COLUMNS),dtype=np.float64)
            bias=np.zeros(ROWS,dtype=np.float64)
            bias[0]=bias[1]=100.
            query=np.ones(COLUMNS,dtype=np.float64)
            exact_choice,_=exact(weights,bias,query)
            guess,props=routed(weights,bias,query,setup_bound(weights))
            self.assertEqual(exact_choice,0)
            self.assertEqual(guess,exact_choice)
            self.assertTrue(props["fell_back"])

    def test_frozen_48_case_screen(self):
        data=screen()
        self.assertEqual(data["schema"],SCHEMA)
        self.assertEqual(len(data["cases"]),48)
        self.assertEqual(len(data["setup"]),6)
        self.assertTrue(all(c["finite"] and c["correct"] for c in data["cases"]))
        self.assertEqual(data["gpu_measured"],"NOT_RUN")
        self.assertEqual(data["authentic_model"],"NOT_RUN")
        self.assertEqual(data["scientific_acceptance"],"NOT_GRANTED")
        self.assertIn(data["decision"],("NO_GO_SYNTHETIC_SCREEN",
                                       "CONDITIONAL_CPU_FEASIBILITY_ONLY"))


if __name__=="__main__":
    unittest.main()
