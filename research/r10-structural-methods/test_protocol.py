import copy,json,pathlib,sys,unittest
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import protocol,review
class R10Guards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(HERE/"frozen.json").read_bytes()
        cls.plan=protocol.frozen(cls.raw)
    def test_frozen_two_genuinely_distinct_mechanisms_and_cohorts(self):
        p=self.plan
        self.assertEqual([c["id"] for c in p["methods"]],["W36-C2","W36-C4"])
        a=sum(p["new_dev"]["training_blocks"],[])
        b=sum(p["new_dev"]["future_replication_training_blocks"],[])
        h=p["new_dev"]["reserved_sealed_heldout"]+p["new_dev"]["future_replication_heldout"]
        self.assertEqual((len(a),len(b),len(h)),(48,48,96))
        self.assertEqual(len(set(a+b+h)),192)
        self.assertTrue(all(s>=26000 for s in a+b+h))
        self.assertEqual(p["parent"]["run_id"],38662331650)
        self.assertEqual(p["parent"]["independent_review_sha256"],protocol.R9_REVIEW_SHA)
        self.assertEqual(p["new_dev"]["first_use_claims"],0)
    def test_duplicate_keys_and_forged_accepted_science_rejected(self):
        with self.assertRaises(ValueError):protocol.obj(b'{"f":0,"f":1}')
        m=copy.deepcopy(self.plan);m["scientific_accepted"]=True
        with self.assertRaises(ValueError):protocol.frozen(json.dumps(m).encode())
        m=copy.deepcopy(self.plan);m["new_dev"]["first_use_claims"]=1
        with self.assertRaises(ValueError):protocol.frozen(json.dumps(m).encode())
    def test_cohort_drift_and_family_retuning_rejected(self):
        m=copy.deepcopy(self.plan);m["new_dev"]["training_blocks"][1][0]=26400
        with self.assertRaises(ValueError):protocol.frozen(json.dumps(m).encode())
        m=copy.deepcopy(self.plan);m["methods"][0]["family"]="quartile-weighting"
        with self.assertRaises(ValueError):protocol.frozen(json.dumps(m).encode())
        m=copy.deepcopy(self.plan);m["selection"]["minimum_gain_every_fold"]=0.0
        with self.assertRaises(ValueError):protocol.frozen(json.dumps(m).encode())
    def test_parent_forgery_or_positive_classification_rejected(self):
        fake={"schema":"forge.r9.independent-learned-method-development-review.v1",
              "candidate_id":"W36-C1","all_three_folds_passed":False,
              "method_fidelity_development_verified":True,"next_original_authorized":False,
              "science_production_accepted":False,"scientific_improvement_established":False,
              "sealed_f3_first_use_admitted":False,
              "folds":[{"fold":i,"preregistered_dev_signal":False,
                        "minimum_family_gain":x} for i,x in enumerate(self.plan["parent"]["minimum_family_gains"])]}
        with self.assertRaises(ValueError):protocol.parent(json.dumps(fake).encode(),self.plan)
        fake["all_three_folds_passed"]=True
        with self.assertRaises(ValueError):protocol.parent(json.dumps(fake).encode(),self.plan)
    def test_reviewer_training_independent_and_candidate_distinction(self):
        x=tuple(([1.0]*16,1) for _ in range(576))
        groups={"A":x,"B":x,"C":x}
        c=review.replay_c2(groups)
        m=review.replay_c4(groups)
        self.assertEqual(len(c),16)
        self.assertEqual(len(m),16)
        self.assertTrue(all(v>=0 for v in c+m))
        self.assertIsNot(review.replay_c2,review.replay_c4)
if __name__=="__main__":unittest.main()
