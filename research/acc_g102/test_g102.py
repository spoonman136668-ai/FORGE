"""G102 source/protocol freeze and adversarial correctness guards."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g102_certified_exit import (
    DIMENSION,LAYERS,QUERIES,REGIMES,SCHEMA,SEEDS,SPEEDUP_FLOOR,
    TRIALS,VOCAB,certified_decode,full_decode,screen,setup_bounds,workload,
)


class G102Guards(unittest.TestCase):
    def test_frozen_protocol(self):
        self.assertEqual(SEEDS,(10201,10202,10203))
        self.assertEqual(REGIMES,("iid","early_dominant"))
        self.assertEqual((LAYERS,DIMENSION,VOCAB,QUERIES,TRIALS),
                         (12,64,128,8,7))
        self.assertEqual(SPEEDUP_FLOOR,1.15)

    def test_exact_bound_all_seeded_queries(self):
        with threadpool_limits(limits=1):
            for seed in SEEDS:
                for regime in REGIMES:
                    hidden,output,queries=workload(seed,regime)
                    suffix=setup_bounds(output)
                    self.assertEqual(suffix.shape,(LAYERS,))
                    for q in queries:
                        base,full=full_decode(hidden,output,q)
                        guess,props=certified_decode(hidden,output,q,suffix)
                        self.assertEqual(guess,base)
                        self.assertTrue(1<=props["layers_evaluated"]<=LAYERS)
                        self.assertGreaterEqual(props["remaining_absolute_score_bound"],0)
                        if props["layers_evaluated"]<LAYERS:
                            self.assertTrue(props["certified"])
                            self.assertGreater(
                                props["stop_margin"],
                                2*props["remaining_absolute_score_bound"])

    def test_adversarial_late_layer_cannot_be_skipped(self):
        with threadpool_limits(limits=1):
            hidden=np.zeros((LAYERS,DIMENSION,DIMENSION),dtype=np.float64)
            output=np.zeros((LAYERS,VOCAB,DIMENSION),dtype=np.float64)
            # No early score margin until the final layer. The remaining
            # bound never treats missing downstream computation as free.
            hidden[-1]=np.eye(DIMENSION)
            output[-1,1,0]=100.
            initial=np.ones(DIMENSION,dtype=np.float64)
            suffix=setup_bounds(output)
            choice,props=certified_decode(hidden,output,initial,suffix)
            baseline,_=full_decode(hidden,output,initial)
            self.assertEqual(choice,baseline)
            self.assertEqual(props["layers_evaluated"],LAYERS)

    def test_complete_frozen_screen(self):
        with threadpool_limits(limits=1):
            data=screen()
        self.assertEqual(data["schema"],SCHEMA)
        self.assertEqual(len(data["cases"]),48)
        self.assertEqual(len(data["setup"]),6)
        self.assertTrue(all(c["correct"] and c["finite"] for c in data["cases"]))
        self.assertEqual(data["gpu_measured"],"NOT_RUN")
        self.assertEqual(data["authentic_model"],"NOT_RUN")
        self.assertEqual(data["scientific_acceptance"],"NOT_GRANTED")
        self.assertIn(data["decision"],("NO_GO_SYNTHETIC_SCREEN",
                                       "CONDITIONAL_CPU_FEASIBILITY_ONLY"))


if __name__=="__main__":
    unittest.main()
