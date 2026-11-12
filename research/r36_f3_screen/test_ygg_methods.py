"""Qualification of R36/F3 development-only candidate implementations."""
import unittest
from ygg_methods import DEV, SEALED, METHODS, READS, DevelopmentTrial, fit_candidate, development_detection_misses

def trial(seed, onset):
    v = tuple(float(i) for i in range(16))
    old = tuple(float(i)-0.1 for i in range(16))
    new = tuple(float(i)+(1 if i==onset else 0.0) for i in range(16))
    return DevelopmentTrial(seed, v, old, new, onset)

class MethodsQualification(unittest.TestCase):
    def setUp(self):
        self.dev = tuple(trial(seed,seed-67200) for seed in sorted(DEV))

    def test_four_distinct_methods_respect_frozen_quota(self):
        for method in METHODS:
            with self.subTest(method=method):
                a=fit_candidate(method,self.dev)
                self.assertEqual(len(a),READS)
                self.assertEqual(len(set(a)),READS)
                self.assertEqual(a,fit_candidate(method,self.dev))
                self.assertTrue(all(0<=x<16 for x in a))
                self.assertTrue(0<=development_detection_misses(a,self.dev)<=8)

    def test_sealed_or_unlisted_seed_is_rejected_before_scoring(self):
        for seed in (*sorted(SEALED), 67208, 0):
            with self.subTest(seed=seed):
                with self.assertRaisesRegex(ValueError,"F3_NON_DEVELOPMENT"):
                    fit_candidate(METHODS[0],(trial(seed,0),))

    def test_duplicate_dev_claim_and_bad_labels_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"F3_NON_DEVELOPMENT"):
            fit_candidate(METHODS[0],(self.dev[0],self.dev[0]))
        with self.assertRaisesRegex(ValueError,"F3_ONSET_LABEL"):
            fit_candidate(METHODS[0],(trial(67200,16),))
        with self.assertRaisesRegex(ValueError,"F3_UNKNOWN_CANDIDATE"):
            fit_candidate("YF3-C5",self.dev)

    def test_observation_and_plan_tamper_rejected(self):
        t=trial(67200,0)
        corrupted=DevelopmentTrial(t.seed,t.before[:-1],t.previous,t.after,t.onset_coordinate)
        with self.assertRaisesRegex(ValueError,"F3_INVALID_OBSERVATIONS"):
            fit_candidate(METHODS[0],(corrupted,))
        with self.assertRaisesRegex(ValueError,"F3_PLAN_BUDGET"):
            development_detection_misses(tuple([0]*READS),self.dev)

if __name__=="__main__":
    unittest.main()
