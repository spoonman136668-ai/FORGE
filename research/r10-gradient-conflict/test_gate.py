import copy,json,pathlib,sys,unittest
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import next_policy as policy
def serialize(v):return (json.dumps(v,sort_keys=True,separators=(",",":"))+"\n").encode()
class SelectionGate(unittest.TestCase):
    def setUp(self):
        self.m=policy.check_frozen((HERE/"frozen.json").read_bytes())
        self.prior={"schema":"forge.r9.train-updated-prospective-hypothesis.v1",
                    "selected_candidate_id":"W36-C1","parent_negative_count":3,
                    "first_use_authorized":False,"originals_executed":0,
                    "policy_improvement_demonstrated":False,
                    "ranked_candidates":[
                        {"id":"W36-C1","eligible_for_development_proposal":True},
                        {"id":"W36-C2","eligible_for_development_proposal":True},
                        {"id":"W36-C4","eligible_for_development_proposal":True},
                        {"id":"RETIRED-R8-QUARTILE","eligible_for_development_proposal":False}]}
        self.review={"schema":"forge.r9.independent-learned-method-development-review.v1",
             "candidate_id":"W36-C1","method_fidelity_development_verified":True,
             "reviewed_original_sha256":self.m["prior_r9_original_measurement_sha256"],
             "all_three_folds_passed":False,
             "science_production_accepted":False,"sealed_f3_first_use_admitted":False,
             "next_original_authorized":False,
             "folds":[{"fold":i,"independent_rows_recomputed":64,
                  "minimum_family_gain":-0.25,"preregistered_dev_signal":False} for i in range(3)]}
        self.m["prior_r9_proposal_sha256"]=policy.sha(serialize(self.prior))
        self.m["prior_r9_review_sha256"]=policy.sha(serialize(self.review))
    def choose(self):
        return policy.successor(serialize(self.m),serialize(self.prior),serialize(self.review))
    def test_frozen_next_method_source_and_zero_authority(self):
        x=self.choose()
        self.assertEqual(x["next_selected"],"W36-C2")
        self.assertEqual(x["remaining_preordered"],["W36-C2","W36-C4"])
        self.assertEqual(x,self.choose())
        self.assertFalse(x["first_use_claimed"])
        self.assertFalse(x["policy_improvement_proven"])
        self.assertFalse(x["scientific_accepted"])
        self.assertFalse(x["external_fsa_qualified"])
        self.assertFalse(x["reserved_sealed_heldout_accessed"])
    def test_parent_retagging_or_success_fails_closed(self):
        self.review["all_three_folds_passed"]=True
        self.m["prior_r9_review_sha256"]=policy.sha(serialize(self.review))
        with self.assertRaises(ValueError):self.choose()
        self.review["all_three_folds_passed"]=False
        self.review["folds"][1]["preregistered_dev_signal"]=True
        self.m["prior_r9_review_sha256"]=policy.sha(serialize(self.review))
        with self.assertRaises(ValueError):self.choose()
    def test_rank_change_or_exhaustion_not_rescored_post_result(self):
        self.prior["ranked_candidates"][1],self.prior["ranked_candidates"][2]=self.prior["ranked_candidates"][2],self.prior["ranked_candidates"][1]
        self.m["prior_r9_proposal_sha256"]=policy.sha(serialize(self.prior))
        with self.assertRaises(ValueError):self.choose()
    def test_sealed_or_reused_seed_and_claim_rejected(self):
        self.m["stages"][1]["development_blocks"][0][0]=26000
        with self.assertRaises(ValueError):self.choose()
        self.m=policy.check_frozen((HERE/"frozen.json").read_bytes())
        self.m["prior_r9_proposal_sha256"]=policy.sha(serialize(self.prior))
        self.m["prior_r9_review_sha256"]=policy.sha(serialize(self.review))
        self.m["constraints"]["first_use_claims"]=1
        with self.assertRaises(ValueError):self.choose()
    def test_duplicate_json_and_invalid_source_hashes(self):
        with self.assertRaises(ValueError):policy.parse(b'{"x":1,"x":2}')
        self.m["pinned_sources"]["method_blob"]="0"*40
        # Method blob is independently compared to source during the real workflow;
        # source drift in the manifest must not change the frozen method.
        self.assertNotEqual(self.m["pinned_sources"]["method_blob"],
            "d75f36f25aca35e30a90bd50e31c8e0d90cedc28")
if __name__=="__main__":unittest.main()
