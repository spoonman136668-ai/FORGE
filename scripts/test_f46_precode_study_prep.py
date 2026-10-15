"""R46 negative qualification from prior authentic F45 decision input."""
import copy
import hashlib
import json
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import f46_precode_study_prep as f
def sample():
 return {"schema":f.SCHEMA,"fresh_train_evidence_recomputed":True,
  "future_originals_preserved":True,"new_science_originals_executed":0,
  "worker_dispatch_authorized":False,"theta_promotion_authorized":False,
  "recursive_policy_improvement_proven":False,
  "evidence":{lane:dict(zip(("run_id","artifact_id","source_commit","report_sha256"),values),
                        stage="TRAIN_ONLY") for lane,values in f.SOURCES.items()},
  "decisions":[{"lane":"Wingless","next_hypothesis":"REPLACE_AMBIGUITY_GATE_WITH_PUBLIC_QUERY_EDGE_VALUE_OF_COMPUTATION",
  "frozen_criterion_met":False,"original_authorized":False,
  "trial_correct":56,"control_correct":56,"total":72,"gain_pp":0.0,
  "control_policy":"one_step_value"},
  {"lane":"Yggdrasil","next_hypothesis":"ISOLATE_CAUSAL_PAIRED_INTERVENTION_BENEFIT_FROM_LEARNED_BASELINE",
   "frozen_criterion_met":False,"original_authorized":False,
   "trial_correct":118,"control_correct":114,"ablation_correct":118,
   "total":128,"ablation_gain_pp":0.0,
   "control_policy":"fitted_Gaussian_latent"}]}
def pack(v):return f.canonical(v)
def run(v):return f.plans(pack(v),hashlib.sha256(pack(v)).hexdigest())
class F46(unittest.TestCase):
 def test_two_lane_distinct_nonexecuting_owner_precode_plans(self):
  a=run(sample())
  self.assertEqual(set(a),{"Wingless","Yggdrasil"})
  self.assertNotEqual(a["Wingless"]["experiment_id"],a["Yggdrasil"]["experiment_id"])
  self.assertIn("count_matched_shuffled_intervention_pairs",a["Yggdrasil"]["fair_controls"])
  self.assertTrue(all(not q["implementation_present"] and not q["owner_prereg_committed"] and
     not q["original_worker_dispatch_authorized"] and q["train_only"] for q in a.values()))
  self.assertEqual(f.canonical(a),f.canonical(run(sample())))
 def test_exact_prior_sha_pin_mandatory(self):
  with self.assertRaises(f.Blocked):f.plans(pack(sample()))
 def test_unsafe_false_authority_or_missing_parent_evidence_rejected(self):
  cases=[
   ("swapped_lanes",lambda v:v["decisions"].reverse()),
   ("missing_lane",lambda v:v["decisions"].pop()),
   ("false_execution",lambda v:v.update(new_science_originals_executed=1)),
   ("unfrozen_future",lambda v:v.update(future_originals_preserved=False)),
   ("false_theta",lambda v:v.update(theta_promotion_authorized=True)),
   ("wrong_artifact",lambda v:v["evidence"]["Yggdrasil"].update(artifact_id=5)),
   ("wrong_source",lambda v:v["evidence"]["Wingless"].update(source_commit="f"*40)),
   ("premature_win",lambda v:v["decisions"][1].update(frozen_criterion_met=True)),
   ("wrong_fair_control",lambda v:v["decisions"][0].update(control_policy="oracle")),
   ("invented_ablation_gain",lambda v:v["decisions"][1].update(ablation_gain_pp=3.125)),
   ("wrong_hypothesis",lambda v:v["decisions"][0].update(next_hypothesis="REPEAT_FAILED_HEURISTIC"))
  ]
  for name,fn in cases:
   with self.subTest(name=name):
    case=copy.deepcopy(sample())
    fn(case)
    with self.assertRaises(f.Blocked):run(case)
 def test_duplicate_json_key_denied(self):
  with self.assertRaises(f.Blocked):f.parse(b'{"schema":"a","schema":"b"}')
if __name__=="__main__":unittest.main()
