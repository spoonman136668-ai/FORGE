import copy,hashlib,json,pathlib,sys,unittest
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import policy_select as policy
def blob(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
class Gate(unittest.TestCase):
    def setUp(self):
        self.m=policy.check_frozen((HERE/"frozen.json").read_bytes())
        self.history=[]
        for i,h in enumerate(self.m["history"]):
            x={"schema":"forge.r35.independent-original-review.v1" if i==0 else "forge.r8.independent-development-review.v1",
               "experiment_id":h["experiment_id"],"outcome":"NO_CONFIRMED_QUARTILE_GAIN",
               "original_sha256":"a"*64,"independently_validated":True,
               "original_replay_allowed":False,"science_production_accepted":False}
            if i>0:x["parent_experiment_id"]=policy.REVIEWS[i-1]
            self.history.append(blob(x))
            h["review_sha256"]=policy.sha(self.history[-1])
        self.terminal={"schema":"forge.r8.actual-two-new-development-originals.v1",
            "new_development_originals_executed":2,"sequential_auto_progression":True,
            "independent_row_reviews":2,"first_use_consumed":2,"historical_originals_replayed":0,
            "scientific_results_accepted":False,
            "original_one_outcome":"NO_CONFIRMED_QUARTILE_GAIN",
            "original_two_outcome":"NO_CONFIRMED_QUARTILE_GAIN"}
        self.tb=blob(self.terminal)
        self.m["parent_r8_terminal_json_sha256"]=policy.sha(self.tb)
    def run_selection(self):
        return policy.select(blob(self.m),self.history,self.tb)
    def test_frozen_real_source_identity(self):
        self.assertEqual(policy.REVIEWS[0],"W-FORGE-R35-TRAIN-QUARTILE-01")
        self.assertEqual([s["experiment_id"] for s in self.m["prepared_prospective"]],list(policy.TARGETS))
    def test_negative_updated_posterior_selects_different_learned_representation(self):
        result=self.run_selection()
        self.assertEqual(result["selected_candidate_id"],"W36-C1")
        retired=next(c for c in result["ranked_candidates"] if c["id"]=="RETIRED-R8-QUARTILE")
        self.assertEqual((retired["posterior_alpha"],retired["posterior_beta"]),(1,4))
        self.assertFalse(retired["eligible_for_development_proposal"])
        self.assertFalse(result["selected_method_fidelity_qualified"])
        self.assertFalse(result["policy_improvement_demonstrated"])
        self.assertFalse(result["first_use_authorized"])
        self.assertEqual(result["parent_negative_count"],3)
        self.assertEqual(result["originals_executed"],0)
        self.assertNotIn("quartile",result["selected_family"])
        self.assertEqual(result,self.run_selection())
    def test_no_retagging_of_negative_as_success_or_authenticity(self):
        tampered=list(self.history)
        record=policy.parse(tampered[1]);record["outcome"]="ROBUST_QUARTILE_GAIN"
        tampered[1]=blob(record)
        with self.assertRaises(ValueError):policy.select(blob(self.m),tampered,self.tb)
        forged=policy.parse(self.history[2]);forged["independently_validated"]=False
        self.history[2]=blob(forged)
        with self.assertRaises(ValueError):self.run_selection()
    def test_no_falsified_terminal_or_firstuse(self):
        self.terminal["independent_row_reviews"]=1
        self.tb=blob(self.terminal)
        self.m["parent_r8_terminal_json_sha256"]=policy.sha(self.tb)
        with self.assertRaises(ValueError):self.run_selection()
    def test_source_drift_and_retired_family_exclusion(self):
        self.m["candidate_method_source"]["source_commit"]="b"*40
        with self.assertRaises(ValueError):self.run_selection()
        self.m["candidate_method_source"]["source_commit"]="7f2f791f98d92ad932e0f530a7d23d0330a15643"
        self.m["candidates"][1]["family"]="quartile-weighting"
        with self.assertRaises(ValueError):self.run_selection()
    def test_cohort_and_authorization_mutations_rejected(self):
        self.m["prepared_prospective"][1]["reserved_sealed_heldout_seeds"][0]=24200
        with self.assertRaises(ValueError):self.run_selection()
        self.m=policy.check_frozen((HERE/"frozen.json").read_bytes())
        for i,h in enumerate(self.m["history"]):h["review_sha256"]=policy.sha(self.history[i])
        self.m["parent_r8_terminal_json_sha256"]=policy.sha(self.tb)
        self.m["constraints"]["new_originals_authorized"]=1
        with self.assertRaises(ValueError):self.run_selection()
    def test_json_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):policy.parse(b'{"x":1,"x":2}')
        with self.assertRaises(ValueError):policy.parse(b'{"x":NaN}')
if __name__=="__main__":unittest.main()
