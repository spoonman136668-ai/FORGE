"""G104 frozen fingerprint and exact-match negative controls."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g104_fingerprint import (
    DIGEST_SIZE, DIMENSION, ERROR_LIMIT, PAIRS, PERTURBATION, REGIMES,
    ROWS, SCHEMA, SEEDS, SPEEDUP_FLOOR, TRIALS,
    baseline, cached_pair, fingerprint, make_workload, screen, second_input,
)


class G104Guards(unittest.TestCase):
    def test_frozen_protocol(self):
        self.assertEqual(SEEDS,(10401,10402,10403))
        self.assertEqual(REGIMES,("identical","near_collision"))
        self.assertEqual((ROWS,DIMENSION,PAIRS,TRIALS),(512,256,8,11))
        self.assertEqual((DIGEST_SIZE,PERTURBATION,ERROR_LIMIT,SPEEDUP_FLOOR),
                         (8,.001,1e-12,1.15))

    def test_forced_fingerprint_collisions_are_never_reused(self):
        with threadpool_limits(limits=1):
            for seed in SEEDS:
                weights,inputs=make_workload(seed)
                for index,first in enumerate(inputs):
                    near=second_input(first,index,"near_collision")
                    identical=second_input(first,index,"identical")
                    self.assertFalse(np.array_equal(first,near))
                    self.assertTrue(np.array_equal(first,identical))
                    self.assertEqual(fingerprint(first),fingerprint(near))
                    self.assertEqual(fingerprint(first),fingerprint(identical))
                    ref=baseline(weights,first,near)
                    candidate=cached_pair(weights,first,near)
                    self.assertTrue(candidate[2])
                    self.assertFalse(candidate[3])
                    self.assertTrue(np.array_equal(ref[0],candidate[0]))
                    self.assertTrue(np.array_equal(ref[1],candidate[1]))
                    reused=cached_pair(weights,first,identical)
                    self.assertTrue(reused[2])
                    self.assertTrue(reused[3])

    def test_fingerprint_collision_cannot_be_correctness_certificate(self):
        with threadpool_limits(limits=1):
            weights,inputs=make_workload(SEEDS[0])
            near=second_input(inputs[0],0,"near_collision")
            self.assertEqual(fingerprint(inputs[0]),fingerprint(near))
            exact_output=weights@near
            incorrect_output=weights@inputs[0]
            self.assertGreater(np.linalg.norm(exact_output-incorrect_output),1e-9)
            _,safe_result,hash_equal,reused=cached_pair(weights,inputs[0],near)
            self.assertTrue(hash_equal)
            self.assertFalse(reused)
            self.assertTrue(np.array_equal(safe_result,exact_output))

    def test_full_48_case_screen_and_no_gpu_claim(self):
        data=screen()
        self.assertEqual(data["schema"],SCHEMA)
        self.assertEqual(len(data["cases"]),48)
        self.assertTrue(all(c["within_all_frozen_correctness_checks"] and
                            not c["false_reuse"] for c in data["cases"]))
        self.assertEqual(data["summary"]["identical"]["exact_reuses"],24)
        self.assertEqual(data["summary"]["near_collision"]["hash_collisions"],24)
        self.assertEqual(data["summary"]["near_collision"]["exact_reuses"],0)
        self.assertEqual(data["gpu_measured"],"NOT_RUN")
        self.assertEqual(data["authentic_model"],"NOT_RUN")
        self.assertEqual(data["scientific_acceptance"],"NOT_GRANTED")
        self.assertIn(data["decision"],("NO_GO_SYNTHETIC_SCREEN",
                                       "CONDITIONAL_CPU_FEASIBILITY_ONLY"))


if __name__=="__main__":
    unittest.main()
