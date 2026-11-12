"""Non-consuming negative-science -> development advisory contract tests."""
import copy,hashlib,json,unittest
from f124_negative_intake import Quarantine,select_advisory,validate_science

def canonical(x):return (json.dumps(x,sort_keys=True)+"\n").encode()
def case(tag,hard,loss):
    arm=lambda pos,fp,veto:{"hard_cases":24,"original_FP":0,"positive":pos,
                              "hard_FP":fp,"positive_witness_vetoes":veto}
    models={"joint_balanced48":arm(20 if tag=="BD" else 21,hard,0),
      "joint_random48":arm(20 if tag=="BD" else 22,hard+1 if tag=="BD" else 0,0)}
    if tag=="BD":models["witness_balanced_exact"]=arm(20-loss,0,loss)
    else:models["contrast_balanced_unbacked"]=arm(21-loss,0,loss)
    for i in range(7):models["filler"+str(i)]=arm(10,0,0)
    return {"schema":"forge.research.f124bd.original-source-new-public-path-certificate.v1"
            if tag=="BD" else "forge.research.f124be.original-frozen-public-peer-contrast.v1",
      "FIT_pairs":24,"FIT_hard_cases":24,"FIT_selected":None,"SCREEN_pairs":0,
      "SCREEN_models":None,"SCREEN_not_constructed_due_to_negative_FIT":True,
      "same_48_public_responses_per_arm":True,
      "DEV_constructed":0,"Wingless_DEV_constructed":0,
      "protected_science_acceptance":False,"optimizer_promotion":False,
      "accepted_ref_mutation":False,"FIT_models":models}

class NegativeFeedbackContract(unittest.TestCase):
    def inputs(self):
        doc={"schema":"forge.research-feedback.f124-authenticated-negative-intake.v1",
          "purpose":"ADVISORY_ONLY_RESEARCH_SELECTION_NO_SCIENCE_ACCEPTANCE_OR_OPTIMIZER_TRAINING",
          "source_repo":"spoonman136668-ai/FORGE","base_main_sha":"a"*40,
          "authority":{"science":False,"promotion":False},
          "examples":[],"next_design":{
            "gate":"F124-BF","preregistered_commit":"b"*40,"freeze_blob":"c"*40,
            "hard_negatives_per_pair":4,"minimum_full_hard_panel_pairs":18,
            "matched_public_observations_per_arm":48,"source_prediction_blind":True,
            "all_baseline_accepted_positives_preserved":True,
            "Feistel_positive_IDs_preserved":True,"protected_DEV_unused":True,
            "require_baseline_hard_FP_greater_than_zero":True}}
        inputs={}
        for tag,fp,loss in (("BD",2,5),("BE",0,6)):
            x=case(tag,fp,loss)
            raw=canonical(x)
            rec={"id":"F124-"+tag,"run":123 if tag=="BD" else 124,
             "original_run_head":"d"*40,"archival_commit":"e"*40,
             "blob_sha":"f"*40,"sha256":hashlib.sha256(raw).hexdigest(),
             "bytes":len(raw),"expected_schema":x["schema"],
             "baseline_balanced_FP":fp,
             "baseline_random_FP":fp+1 if tag=="BD" else 0}
            rec["exact_balanced_positive_loss" if tag=="BD" else
                "unsupported_balanced_positive_loss"]=loss
            doc["examples"].append(rec)
            run={"id":rec["run"],"head_sha":rec["original_run_head"],
               "status":"completed","conclusion":"success","run_attempt":1,
               "event":"push","repository":{"full_name":doc["source_repo"]},
               "head_repository":{"full_name":doc["source_repo"]}}
            index={"artifacts":[]}
            inputs[rec["id"]]=(run,index,raw)
        return doc,inputs

    def test_real_negative_types_are_planning_not_scientific_wins(self):
        doc,inputs=self.inputs()
        out=select_advisory(doc,inputs)
        self.assertEqual(out["next_research_gate"],"F124-BF")
        self.assertEqual(out["negative_cohorts"],2)
        self.assertEqual(out["accepted_scientific_originals"],0)
        self.assertEqual(out["optimizer_training_labels"],0)
        self.assertEqual(out["policy_promotions"],0)
        self.assertFalse(out["live_controller_consumption_proven"])

    def test_original_payload_tamper_rejected(self):
        doc,inputs=self.inputs()
        run,art,raw=inputs["F124-BD"]
        inputs["F124-BD"]=(run,art,raw+b" ")
        with self.assertRaises(Quarantine):
            select_advisory(doc,inputs)

    def test_fabricated_run_cannot_be_used(self):
        doc,inputs=self.inputs()
        run,art,raw=inputs["F124-BE"]
        changed=copy.deepcopy(run);changed["head_sha"]="0"*40
        inputs["F124-BE"]=(changed,art,raw)
        with self.assertRaises(Quarantine):select_advisory(doc,inputs)

    def test_no_baseline_FP_means_no_FP_improvement_claim(self):
        doc,inputs=self.inputs()
        data=case("BD",0,5)
        raw=canonical(data)
        inputs["F124-BD"]=(inputs["F124-BD"][0],inputs["F124-BD"][1],raw)
        doc["examples"][0]["sha256"]=hashlib.sha256(raw).hexdigest()
        doc["examples"][0]["bytes"]=len(raw)
        doc["examples"][0]["baseline_balanced_FP"]=0
        doc["examples"][0]["baseline_random_FP"]=1
        with self.assertRaises(Quarantine):select_advisory(doc,inputs)

    def test_fake_optimizer_promotion_not_admitted(self):
        doc,inputs=self.inputs()
        doc["authority"]["promotion"]=True
        with self.assertRaises(Quarantine):select_advisory(doc,inputs)

if __name__=="__main__":unittest.main()
