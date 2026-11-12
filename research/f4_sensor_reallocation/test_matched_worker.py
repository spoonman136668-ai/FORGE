"""F4 comparator transport, causal-read and fail-closed negative paths."""
import unittest
from types import SimpleNamespace
from matched_worker import (
    CONTROL,SET_FIXTURE,ORDER_FIXTURE,Y070_COMMIT,decoder,
    install_equal_decoder_and_sampler,validate_schedule,verify_comparators,
    score_case
)

class ComparisonTests(unittest.TestCase):
    def test_order_ablation_matches_exact_candidate_sensor_multiset(self):
        arms=verify_comparators()
        self.assertEqual(arms["F4-CONTROL"],CONTROL)
        self.assertNotEqual(arms["F4-SET"],arms["F4-ORDER-CONTROL"])
        self.assertEqual(sum(map(len,arms["F4-SET"])),10)
    def test_bad_controls_rejected(self):
        arms=verify_comparators()
        arms["F4-ORDER-CONTROL"]=CONTROL
        with self.assertRaisesRegex(ValueError,"NOT_SENSOR_SET_MATCHED"):
            verify_comparators(arms)
        arms["F4-ORDER-CONTROL"]=SET_FIXTURE
        with self.assertRaisesRegex(ValueError,"NOT_DISTINCT"):
            verify_comparators(arms)
    def test_unqualified_address_and_calibration_fail(self):
        for bad in (((0,1),)*4+((0,0),),
                    ((0,1),)*4+((16,2),),
                    ((0,1),)*4+((1,2.0),),
                    ((0,1),)*2+((2,4),)*3):
            with self.assertRaises(ValueError):
                validate_schedule(bad)
    def test_public_only_decoding_and_negative_calibration(self):
        def v(t,c):
            return (3+t+5*c)%16
        obs={t:{str(c):v(t,c) for c in pair} for t,pair in zip(
            (0,1,3,5,7),((0,1),(0,1),(0,1),(8,11),(0,1)))}
        self.assertIsNone(decoder(obs,3)["first_detection_episode"])
        obs[5]["8"]=v(5,10)
        result=decoder(obs,7)
        self.assertEqual(result["detected_pair"],{8:10,10:8})
        self.assertEqual(result["first_detection_episode"],5)
        obs[1]["1"]+=1
        with self.assertRaisesRegex(ValueError,"CALIBRATION"):
            decoder(obs,7)
    def test_instrumentation_restores_pinned_modules_after_failure(self):
        orig_sampler=lambda seed,family:{}
        orig_decoder=lambda observations,episode:None
        m=SimpleNamespace(
            y64=SimpleNamespace(dual_public_samples=orig_sampler,
               y46=SimpleNamespace(coordinate=lambda c,seed,t,family,kind:c+t)),
            y61=SimpleNamespace(y60=SimpleNamespace(public_decoder=orig_decoder)))
        y=SimpleNamespace(m=m)
        trace=[]
        with self.assertRaisesRegex(RuntimeError,"interrupt"):
            with install_equal_decoder_and_sampler(y,SET_FIXTURE,trace):
                readings=m.y64.dual_public_samples(67204,(3,1,9))
                self.assertEqual(readings[5],{"8":13,"11":16})
                self.assertEqual(sum(len(x) for x in readings.values()),10)
                self.assertIs(m.y61.y60.public_decoder,decoder)
                raise RuntimeError("interrupt")
        self.assertIs(m.y64.dual_public_samples,orig_sampler)
        self.assertIs(m.y61.y60.public_decoder,orig_decoder)
        self.assertEqual(trace,[[list(x) for x in SET_FIXTURE]])
    def test_first_use_boundary_is_rejected_pre_source(self):
        with self.assertRaisesRegex(ValueError,"NO_NEW_COHORT"):
            score_case(None,67640,(8,10),1,(3,1,9),"full","F4-SET")

if __name__=="__main__":
    unittest.main()
