"""F6 causal public-observation decision / frozen source safety tests."""
import inspect
import unittest
from copy import deepcopy
from learner import (choose_f6,residual_strength,fit,TRAIN_SEEDS,CHECK_SEEDS,
                     THRESHOLDS,NEXT_ID)
from worker import evaluate,install_model,SOURCE_COMMIT

def used_public_history():
    h={}
    b0,a,d=3,5,1
    for t in (0,1,3,5):
        addresses=choose_f6(t,h,1)
        h[t]={cell:(b0+a*cell+d*t)%16 for cell in addresses}
    return h

class F6MethodTests(unittest.TestCase):
    def test_training_validation_identity_is_disjoint_used_f3(self):
        self.assertEqual(TRAIN_SEEDS,(67204,67205))
        self.assertEqual(CHECK_SEEDS,(67206,67207))
        self.assertFalse(set(TRAIN_SEEDS).intersection(CHECK_SEEDS))
        self.assertEqual(THRESHOLDS,tuple(range(1,10)))
        self.assertEqual(SOURCE_COMMIT,"5797a257a75fe139313e8486cd1a1ae79c44b148")

    def test_public_only_model_decides_by_observed_strength(self):
        h=used_public_history()
        self.assertEqual(residual_strength(h),0)
        self.assertEqual(choose_f6(7,h,1),choose_f6(7,h,9))
        anomalous=deepcopy(h)
        address=next(iter(anomalous[5]))
        anomalous[5][address]=(anomalous[5][address]+5)%16
        strength=residual_strength(anomalous)
        self.assertGreater(strength,0)
        self.assertLessEqual(strength,8)
        self.assertEqual(set(choose_f6(7,anomalous,1)),set(anomalous[5]))
        self.assertNotEqual(set(choose_f6(7,anomalous,9)),set(anomalous[5]))
        self.assertEqual(list(inspect.signature(choose_f6).parameters),
                         ["episode","history","threshold"])

    def test_no_future_observations_or_oracle_seed(self):
        h=used_public_history()
        with self.assertRaisesRegex(ValueError,"FUTURE_OR_CURRENT_LEAK"):
            choose_f6(5,h,1)
        with self.assertRaises(TypeError):
            choose_f6(7,h,1,true_pair=(8,10))
        with self.assertRaisesRegex(ValueError,"FROZEN_THRESHOLD"):
            choose_f6(7,h,0)
        with self.assertRaisesRegex(ValueError,"FROZEN_THRESHOLD"):
            choose_f6(7,h,10)

    def test_new_scientific_seed_and_uninspected_pair_refused_without_source(self):
        fake={"training_seed_ids":[67204,67205],
              "untouched_validation_seed_ids":[67206,67207]}
        with self.assertRaisesRegex(ValueError,"NEW_OR_TRAINING_SEED_REFUSED"):
            evaluate(None,fake,67600,(8,10),"onset1",(1,2,3),"full")
        with self.assertRaisesRegex(ValueError,"NEW_OR_TRAINING_SEED_REFUSED"):
            evaluate(None,fake,67640,(8,10),"onset1",(1,2,3),"full")
        with self.assertRaisesRegex(ValueError,"NEW_OR_TRAINING_SEED_REFUSED"):
            evaluate(None,fake,67204,(8,10),"onset1",(1,2,3),"full")
        with self.assertRaisesRegex(ValueError,"UNKNOWN_PAIR_OR_REGIME_REFUSED"):
            evaluate(None,fake,67206,(6,9),"onset1",(1,2,3),"full")

    def test_successor_identity_blocks_unrelated_or_authorized_original(self):
        rejected={"schema":"forge.f5.automatic-evidence-to-successor-proposal.v1",
                  "disposition":"SUCCESSOR_PREPARED_CUSTODY_BLOCKED_NO_ORIGINAL",
                  "selected":{"proposal_id":NEXT_ID},
                  "selection_rule":"PUBLIC_MEMORY_RECHECK_NO_GAIN",
                  "scientific_dispatch_authorized":True,
                  "new_seed_allocations":0,"new_first_use_claims":0}
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_SUCCESSOR"):
            fit({},rejected,None)
        rejected["scientific_dispatch_authorized"]=False
        rejected["selected"]["proposal_id"]="FORGED"
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_SUCCESSOR"):
            fit({},rejected,None)

if __name__=="__main__":unittest.main()
