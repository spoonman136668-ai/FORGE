"""F9 no-oracle, split, matched-set, and no-first-use contract tests."""
import inspect
import unittest
from copy import deepcopy
from policy import (RULES,TRAIN_SEEDS,VALIDATION_SEEDS,PAIRS,choose,
                    public_start,choose_branch,trace_audit,f8)
from worker import evaluate,SOURCE_COMMIT
from advance import classify_start,preflight

def public_history(rule):
    h={}
    for t in (0,1,3,5,7):
        cells=choose(t,h,rule)
        h[t]={c:(3+5*c+t)%16 for c in cells}
    return h

class F9Tests(unittest.TestCase):
    def test_rules_only_public_history_and_ten_reads(self):
        self.assertEqual(list(inspect.signature(choose).parameters),
                         ["episode","history","rule"])
        for rule in RULES:
            h=public_history(rule)
            measured=trace_audit(rule,h)
            self.assertEqual(measured["reads"],10)
            self.assertEqual(measured["distinct_nonanchor_cells"],6)
            self.assertEqual(len(measured["physical_nonanchor_set"]),6)
            self.assertIn(measured["decision"],("EARLY","SWAP"))
            self.assertEqual(choose_branch(rule,{0:h[0],1:h[1]}),
                             measured["decision"]=="EARLY")
            self.assertEqual(classify_start(rule,public_start(h)),
                             measured["decision"]=="EARLY")

    def test_frozen_model_cannot_see_future_or_true_pair(self):
        history=public_history("START_EVEN_EARLY")
        with self.assertRaisesRegex(ValueError,"FUTURE_OR_MISSING_PUBLIC_INPUT"):
            choose(3,history,"START_EVEN_EARLY")
        with self.assertRaises(TypeError):
            choose(3,{0:history[0],1:history[1]},"START_EVEN_EARLY",
                   true_pair=(8,10))
        with self.assertRaisesRegex(ValueError,"RULE_NOT_FROZEN"):
            choose(3,{0:history[0],1:history[1]},"UNKNOWN")

    def test_frozen_sensor_set_no_leak(self):
        a=public_history("ALWAYS_EARLY")
        b=public_history("ALWAYS_SWAP")
        self.assertEqual(set(k for t in (3,5,7) for k in a[t]),
                         set(k for t in (3,5,7) for k in b[t]))
        self.assertEqual(set(a[3]),set(b[5]))
        self.assertEqual(set(a[5]),set(b[3]))
        self.assertEqual(set(a[7]),set(b[7]))

    def test_frozen_training_and_validation_separation(self):
        self.assertEqual(TRAIN_SEEDS,(67204,67205))
        self.assertEqual(VALIDATION_SEEDS,(67206,67207))
        self.assertTrue(set(TRAIN_SEEDS).isdisjoint(VALIDATION_SEEDS))
        self.assertEqual(PAIRS,((8,10),(11,13)))
        self.assertEqual(SOURCE_COMMIT,"5797a257a75fe139313e8486cd1a1ae79c44b148")

    def test_new_first_use_and_uninspected_pairs_refused(self):
        for seed in (67240,67600,67640,67800):
            with self.assertRaisesRegex(ValueError,"NEW_FIRST_USE_OR_SEED_REFUSED"):
                evaluate(None,seed,(8,10),"onset1",(1,2,3),"full",RULES[0])
        with self.assertRaisesRegex(ValueError,"NEW_PAIR_OR_REGIME_REFUSED"):
            evaluate(None,67204,(6,9),"onset1",(1,2,3),"full",RULES[0])
        with self.assertRaisesRegex(ValueError,"UNFROZEN_POLICY_REFUSED"):
            evaluate(None,67204,(8,10),"onset1",(1,2,3),"full","HIDDEN_ORACLE")

    def test_parent_requires_real_verified_f8(self):
        parent={
          "schema":"forge.f8.automatic-f7-matched-timing-engineering.v1",
          "status":"PREVIOUSLY_USED_F3_ONLY_NOT_FROZEN_SCIENCE",
          "source_commit":SOURCE_COMMIT,
          "selected_proposal":"Y-FORGE-F8-MATCHED-SENSOR-TIMING-CONTROL-PROPOSAL",
          "matched_physical_sensor_sets":True,
          "used_development_seeds":[67206,67207],
          "used_pairs":[[8,10],[11,13]],
          "public_scalar_reads":10,"winner_selected":False,
          "scientific_dispatch_authorized":False,
          "new_development_or_sealed_uses":0,"new_originals":0,
          "new_first_use_claims":0,"paid_api_calls":0,
          "records":[{} for _ in range(192)],
          "groups":{
           "F8-F7-EARLY-CONTROL":{"cases":96,"pre":68,"post":6,"steady_errors":0},
           "F8-SAME-SET-3-5-SWAP":{"cases":96,"pre":60,"post":6,"steady_errors":0}}
        }
        review={"schema":"forge.f8.independent-matched-sensor-timing-review.v1",
                "status":"USED_F3_REAL_SOURCE_REPLAY_ONLY_NO_SCIENCE",
                "replayed_trial_arms":192,"matched_set_comparisons":96,
                "totals":deepcopy(parent["groups"]),
                "new_originals":0,"first_use_claims":0,
                "scientific_dispatch_authorized":False}
        self.assertEqual(preflight(parent,review),
                         "F8_PUBLIC_TIME_ORDER_MATTERS_MATCHED_SENSOR_SET")
        parent["new_first_use_claims"]=1
        with self.assertRaisesRegex(ValueError,"F8_PARENT"):
            preflight(parent,review)

if __name__=="__main__":unittest.main()
