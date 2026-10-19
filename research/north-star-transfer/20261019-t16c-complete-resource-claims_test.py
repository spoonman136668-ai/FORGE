"""T16C independent prospective resource-claims audit unit tests.
Synthetic metering claims only; no experimental sources are born.
"""
import importlib.util
import sys
import unittest
from pathlib import Path
p=Path(__file__).with_name("20261019-t16c-complete-resource-claims.py")
s=importlib.util.spec_from_file_location("mass_t16c_resource_claims",p)
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def row(name,correct,train=120,eval=120,validate=20,query_cpu=20,rss=8192,queries=16):
    return {"name":name,"train_cpu_ns":train,"eval_cpu_ns":eval,
      "validation_cpu_ns":validate,"source_queries_cpu_ns":query_cpu,
      "source_queries_count":queries,"train_peak_rss_bytes":rss,
      "eval_peak_rss_bytes":rss,"validation_peak_rss_bytes":rss,
      "train_tasks":24,"open_tasks":8,"public_train_sha256":"a"*64,
      "public_open_sha256":"b"*64,"measurement_environment_sha256":"c"*64,
      "correct_held_outputs":correct,"baseline_positive_regressions":0,
      "hard_false_positives":0}
class T16CFullCostTests(unittest.TestCase):
    def test_perfect_claim_never_certifies_science_or_dispatch(self):
        result=m.resource_review(row("candidate",120,100,100,10,10,8192,8),
           [row("strong-trained",100),row("strong-symbolic",110)])
        self.assertTrue(result["mathematical_complete_cost_parity_claim"])
        self.assertTrue(result["mathematical_heldout_gain_claim"])
        self.assertFalse(result["signed_source_birth_verified"])
        self.assertFalse(result["original_execution_authorized"])
        self.assertFalse(result["scientific_accepted"])
        self.assertFalse(result["optimizer_admitted"])
        self.assertFalse(result["merge_authorized"])
    def test_equal_accuracy_is_not_learned_transfer(self):
        r=m.resource_review(row("candidate",128),[row("strong-trained",128)])
        self.assertFalse(r["mathematical_heldout_gain_claim"])
    def test_inclusion_of_training_cost_blocks_fake_cpu_wins(self):
        r=m.resource_review(row("candidate",128,train=3000,eval=10),
           [row("trained",100,train=100,eval=300)])
        self.assertFalse(r["mathematical_complete_cost_parity_claim"])
    def test_query_service_cost_is_not_free(self):
        r=m.resource_review(row("candidate",120,query_cpu=1000,queries=30),
           [row("trained",100,query_cpu=20,queries=16)])
        self.assertFalse(r["mathematical_complete_cost_parity_claim"])
    def test_validation_cpu_is_counted(self):
        r=m.resource_review(row("candidate",120,validate=2000),
           [row("trained",100)])
        self.assertFalse(r["mathematical_complete_cost_parity_claim"])
    def test_peak_rss_not_serialized_state(self):
        r=m.resource_review(row("candidate",120,rss=9000),
           [row("trained",100,rss=8192)])
        self.assertFalse(r["mathematical_complete_cost_parity_claim"])
    def test_best_of_two_strong_controls(self):
        r=m.resource_review(row("candidate",120,train=70,eval=70),
           [row("trained",100,train=500,eval=500),
            row("symbolic",110,train=0,eval=20)])
        self.assertFalse(r["mathematical_complete_cost_parity_claim"])
        self.assertEqual(r["control_count"],2)
    def test_missing_cost_denied(self):
        x=row("candidate",128);x.pop("train_peak_rss_bytes")
        with self.assertRaisesRegex(ValueError,"COMPLETE_COST_SCHEMA"):
            m.resource_review(x,[row("trained",120)])
    def test_boolean_cost_denied(self):
        x=row("candidate",128);x["source_queries_count"]=True
        with self.assertRaisesRegex(ValueError,"INT_METRICS"):
            m.resource_review(x,[row("trained",120)])
    def test_unmatched_public_train_or_open_denied(self):
        for key in ("public_train_sha256","public_open_sha256","measurement_environment_sha256"):
            x=row("candidate",128);x[key]="d"*64
            with self.assertRaisesRegex(ValueError,"NOT_EQUAL_SOURCE"):
                m.resource_review(x,[row("trained",120)])
    def test_regression_never_promoted(self):
        x=row("candidate",128);x["baseline_positive_regressions"]=1
        r=m.resource_review(x,[row("trained",120)])
        self.assertFalse(r["no_reported_wrong_or_baseline_regressions"])
        self.assertFalse(r["scientific_accepted"])
    def test_false_positive_never_promoted(self):
        x=row("candidate",128);x["hard_false_positives"]=1
        r=m.resource_review(x,[row("trained",120)])
        self.assertFalse(r["no_reported_wrong_or_baseline_regressions"])
    def test_no_controls_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"STRONG_CONTROLS"):
            m.resource_review(row("candidate",100),[])
if __name__=="__main__":
    unittest.main()
