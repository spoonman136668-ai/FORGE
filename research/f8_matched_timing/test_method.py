"""F8 source-only causal sensing, matched-pair fidelity and first-use guards."""
import inspect
import unittest
from copy import deepcopy
from schedule import (ARMS,EPISODES,choose,validate_trace,matched_sets,
                      common_decoder)
from worker import evaluate,SEEDS,PAIRS,SOURCE_COMMIT
from advance import preflight

def fake_trace(arm):
    history={}
    for t in EPISODES:
        addresses=choose(arm,t,history)
        history[t]={k:(3+5*k+t)%16 for k in addresses}
    return history

class TimingTests(unittest.TestCase):
    def test_exact_same_sensors_and_budget_except_order(self):
        a,b=(fake_trace(arm) for arm in ARMS)
        left=validate_trace(ARMS[0],a)
        right=validate_trace(ARMS[1],b)
        self.assertTrue(matched_sets(left,right))
        self.assertEqual(left["public_reads"],right["public_reads"])
        self.assertEqual(left["distinct_nonanchors"],6)
        self.assertEqual(right["distinct_nonanchors"],6)
        self.assertEqual(set(a[3]),set(b[5]))
        self.assertEqual(set(a[5]),set(b[3]))
        self.assertEqual(set(a[7]),set(b[7]))
        self.assertEqual(set(a[0]),{0,1})

    def test_public_calibration_only_and_no_oracle(self):
        self.assertEqual(list(inspect.signature(choose).parameters),
                         ["arm","episode","history"])
        a=fake_trace(ARMS[0])
        with self.assertRaises(TypeError):
            choose(ARMS[1],3,{0:a[0],1:a[1]},true_pair=(8,10))
        with self.assertRaisesRegex(ValueError,"FUTURE_OR_UNAVAILABLE_READS"):
            choose(ARMS[0],3,a)
        with self.assertRaisesRegex(ValueError,"UNKNOWN_ARM"):
            choose("FORGED",3,{0:a[0],1:a[1]})

    def test_source_decoder_is_identical_for_both_schedules(self):
        for arm in ARMS:
            a=fake_trace(arm)
            public={t:{str(k):v for k,v in vals.items()} for t,vals in a.items()}
            self.assertIsNone(common_decoder(public,7)["first_detection_episode"])

    def test_sensor_set_tamper_fails(self):
        a,b=(fake_trace(arm) for arm in ARMS)
        x,y=validate_trace(ARMS[0],a),validate_trace(ARMS[1],b)
        y=deepcopy(y)
        y["observed_set"][-1]=15 if y["observed_set"][-1]!=15 else 14
        with self.assertRaisesRegex(ValueError,"SENSOR_SET_MISMATCH"):
            matched_sets(x,y)
        z=deepcopy(b)
        k=next(iter(z[5]))
        z[5]={14:z[5][k],15:z[5][k]}
        with self.assertRaisesRegex(ValueError,"ADDRESS_DECISION_DRIFT"):
            validate_trace(ARMS[1],z)

    def test_fresh_and_prior_training_seeds_cannot_reach_worker(self):
        for bad in (67204,67205,67240,67600,67640,67800):
            with self.assertRaisesRegex(ValueError,"FRESH_OR_TRAINING_SEED_REFUSED"):
                evaluate(None,bad,(8,10),"onset1",(3,1,9),"full",ARMS[0])
        with self.assertRaisesRegex(ValueError,"NEW_PAIR_OR_REGIME_REFUSED"):
            evaluate(None,67206,(6,9),"onset1",(3,1,9),"full",ARMS[1])
        self.assertEqual(SEEDS,(67206,67207))
        self.assertEqual(PAIRS,((8,10),(11,13)))
        self.assertEqual(SOURCE_COMMIT,"5797a257a75fe139313e8486cd1a1ae79c44b148")

    def test_signed_custody_not_inferred_from_f7_dev_results(self):
        base={"schema":"forge.f7.automatic-f6-negative-to-method-engineering.v1",
              "status":"F3_REUSED_ENGINEERING_SCIENTIFIC_CUSTODY_BLOCKED",
              "source_commit":SOURCE_COMMIT,
              "selected_proposal":"Y-FORGE-F7-EARLY-SENSOR-BUDGET-REALLOCATION-PROPOSAL",
              "already_used_f3_validation_seeds":[67206,67207],
              "already_used_f3_pairs":[[8,10],[11,13]],
              "new_originals":0,"new_first_use_claims":0,
              "new_cohort_accesses":0,"paid_api_calls":0,
              "scientific_dispatch_authorized":False,
              "no_scientific_winner_selected":True,
              "records":[{"seed":67206,"pair":[8,10]} for _ in range(192)],
              "totals":{
               "F7-REPLAY-F5-COVERAGE":{"cases":96,"pre":87,"post":4,
                                        "earliest_detection":5,"steady_errors":0},
               "F7-EARLY-SIX-COVERAGE":{"cases":96,"pre":68,"post":6,
                                         "earliest_detection":3,"steady_errors":0}}}
        witness={"schema":"forge.f7.independent-public-earliness-engineering-review.v1",
                 "status":"F3_REUSED_REAL_SOURCE_REPLAY_PASS_NOT_SCIENCE",
                 "replayed_trial_arms":192,
                 "new_first_use_claims":0,"scientific_originals":0,
                 "scientific_dispatch_authorized":False,
                 "totals":deepcopy(base["totals"])}
        self.assertEqual(preflight(base,witness),
                         "F7_EARLY_GAIN_COULD_BE_SENSOR_COUNT_OR_TIMING")
        witness["scientific_dispatch_authorized"]=True
        with self.assertRaisesRegex(ValueError,"F7_INDEPENDENT_REVIEW"):
            preflight(base,witness)
        witness["scientific_dispatch_authorized"]=False
        base["new_first_use_claims"]=1
        with self.assertRaisesRegex(ValueError,"F7_PROVENANCE"):
            preflight(base,witness)

if __name__=="__main__":
    unittest.main()
