"""F7 mechanism fidelity, ten-read budget, and first-use prohibition."""
import inspect
import unittest
from policy import (POLICIES,OFFSETS,READ_TIMES,select,common_decoder,
                    verify_observations,geometry_certificate)
from worker import evaluate,SEEDS,PAIRS
from advance import qualify_parent

def public_history(policy):
    h={}
    for t in READ_TIMES:
        cells=select(policy,t,h)
        h[t]={c:(3+5*c+t)%16 for c in cells}
    return h

class F7MethodTests(unittest.TestCase):
    def test_budget_earliness_and_exhaustive_geometry_bound(self):
        self.assertEqual(OFFSETS,(0,1,2,3,5,10))
        cert=geometry_certificate()
        self.assertEqual(cert["pairs"],91)
        self.assertEqual(cert["starts"],14)
        self.assertEqual(cert["min_visible_starts"],9)
        self.assertEqual(cert["max_visible_starts"],11)
        self.assertEqual(cert["mean_visible_starts_numerator"],882)
        for p in POLICIES:
            h=public_history(p)
            self.assertEqual(sum(map(len,h.values())),10)
            observed=verify_observations(p,h)
            self.assertEqual(observed["public_scalar_reads"],10)
            self.assertEqual(observed["distinct_nonanchor_addresses"],6 if p==POLICIES[1] else 4)
        self.assertEqual(set(public_history(POLICIES[0])[3]),{0,1})
        self.assertTrue(set(public_history(POLICIES[1])[3]).isdisjoint({0,1}))

    def test_decoder_same_for_both_arms_and_early_onset(self):
        h=public_history(POLICIES[1])
        public={t:{str(c):v for c,v in vals.items()} for t,vals in h.items()}
        self.assertIsNone(common_decoder(public,7)["first_detection_episode"])
        cell=h[3].keys().__iter__().__next__()
        other=next(k for k in range(2,16) if k!=cell)
        public[3][str(cell)]=(3+5*other+3)%16
        self.assertEqual(common_decoder(public,7)["first_detection_episode"],3)
        self.assertEqual(common_decoder(public,3)["first_detection_episode"],3)

    def test_inference_receives_no_hidden_pair_or_seed(self):
        self.assertEqual(list(inspect.signature(select).parameters),
                         ["policy","episode","history"])
        h=public_history(POLICIES[1])
        self.assertEqual(set(h[3]),set(select(POLICIES[1],3,{t:h[t] for t in (0,1)})))
        with self.assertRaises(TypeError):
            select(POLICIES[1],3,{t:h[t] for t in (0,1)},true_pair=(8,10))
        with self.assertRaisesRegex(ValueError,"CAUSAL_HISTORY"):
            select(POLICIES[1],3,h)

    def test_sealed_and_new_pair_refused_without_loading_y070(self):
        for bad in (67600,67640,67204,67205,67240):
            with self.assertRaisesRegex(ValueError,"NEW_SEED_OR_FIRST_USE_REFUSED"):
                evaluate(None,bad,(8,10),"onset1",(3,1,9),"full",POLICIES[1])
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_NEW_PAIR_OR_REGIME"):
            evaluate(None,67206,(6,9),"onset1",(3,1,9),"full",POLICIES[1])
        self.assertEqual(SEEDS,(67206,67207))
        self.assertEqual(PAIRS,((8,10),(11,13)))

    def test_f6_negative_must_be_independently_reviewed(self):
        record={
            "schema":"forge.f6.automatic-trained-engineering-evidence.v1",
            "status":"HISTORICAL_F3_USED_ONLY_INDEPENDENT_REVIEW_REQUIRED",
            "parent_y070_commit":"5797a257a75fe139313e8486cd1a1ae79c44b148",
            "successor_id":"Y-FORGE-F6-UNCERTAINTY-CALIBRATION-PROPOSAL",
            "model":{"schema":"forge.f6.public-only.calibrated-memory-threshold.v1",
                     "status":"TRAINED_ON_PREVIOUSLY_USED_F3_DEVELOPMENT_ONLY",
                     "frozen_threshold":3,"training_seed_ids":[67204,67205],
                     "untouched_validation_seed_ids":[67206,67207],
                     "scientific_dispatch_authorized":False},
            "validation_summary":{"cases":96,"steady_errors":0,"rechecks":0},
            "validation_records":[{"seed":67206,"pair":[8,10],
                   "arm":"F6-LEARNED-UNCERTAINTY"} for _ in range(96)],
            "matched_f5_validation_controls":{
                "F5-COVERAGE":{"cases":96},
                "F5-MEMORY":{"cases":96}},
            "new_first_use_claims":0,"new_originals":0,
            "new_cohort_accesses":0,"paid_api_calls":0,
            "scientific_authority":False}
        reviewer={"schema":"forge.f6.independent-learned-uncertainty-engineering-review.v1",
                  "status":"F3_USED_SPLIT_REPLAY_QUALIFIED_NOT_PROSPECTIVE_SCIENCE",
                  "validation_cases":96,
                  "validation_summary":record["validation_summary"],
                  "learned_threshold":3,"scientific_dispatch_authorized":False}
        self.assertEqual(qualify_parent(record,reviewer),
                         "F6_MEMORY_INACTIVE_VALIDATED_F3_USED")
        record["validation_summary"]["rechecks"]=1
        with self.assertRaisesRegex(ValueError,"INDEPENDENT_PARENT_REVIEW"):
            qualify_parent(record,reviewer)
        record["validation_summary"]["rechecks"]=0
        reviewer["validation_summary"]=record["validation_summary"]
        record["new_first_use_claims"]=1
        with self.assertRaisesRegex(ValueError,"NO_AUTHORITY"):
            qualify_parent(record,reviewer)

if __name__=="__main__":unittest.main()
