import copy
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from f99_candidate_bridge import join,Blocked,SCHEMA
from f99_archive_extract import PINS,SCHEMA as REAL
SRC="a"*40

def fixture():
 r={"schema":REAL,"forge_source_sha":SRC,
    "cohort_source":"EXACT_PINNED_GITHUB_ACTIONS_ZIP_AND_CONTAINED_JSON_BYTES",
    "disposition":"REAL_DEV_ROW_REAGGREGATION_ONLY_NO_TRAINING_OR_NOVEL_SCIENCE_AUTHORITY",
    "distinct_authentic_dev_lane_sources":2,
    "descriptive_development_constraints_verified":2,
    "new_trainable_genenv_records":0,"new_scientific_originals":0,
    "original_first_use_authorized":False,
    "research_selection_promotion_authorized":False,
    "accepted_research_ref_mutation":False,"model_invocations":0,
    "codex_invocations":0,"external_model_api_calls":0,"lanes":[]}
 s={"schema":"forge.model-free.two-lane-untested-advisory.v1",
    "source_commit_sha":SRC,
    "evidence_type":"SYNTHETIC_FROZEN_SOURCE_ONLY_NOT_NEW_SCIENTIFIC_EVIDENCE",
    "model_invocations":0,"codex_invocations":0,"network_calls":0,
    "new_scientific_originals":0,"scientific_first_use_authorized":False,
    "policy_promotion_authorized":False,
    "real_research_progress_established":False,"accepted_ref_mutations":0,"lanes":[]}
 for lane in ("Wingless","Yggdrasil"):
  p=PINS[lane]
  r["lanes"].append(dict(lane=lane,source_commit=p["commit"],
    original_archive_run_id=p["run"],original_artifact_id=p["artifact"],
    zip_sha256=p["zip"],contained_json_sha256=p["json"],
    historical_development_pair_count=p["pairs"],
    frozen_blind_paired_correct=0,coded_oracle_paired_correct=p["pairs"],
    historical_negative_mechanism_constraint=p["mechanism"],
    source_bytes_and_rows_reaudited=True,
    stage="AUTHENTIC_HISTORICAL_DEVELOPMENT_ONLY",
    independent_original_firstuse_qualified=False,
    train_only_genenv_record_admitted=False,science_accepted=False))
  s["lanes"].append(dict(lane=lane,prompt_candidates=2,environment_candidates=2,
    negative_records=1,invalid_records=1,mixed_records=1,
    all_candidates_untested=True,full_population_screened=True,
    science_accepted=False,original_dispatch_authorized=False,
    advisory_assessment="BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY",
    proposal_ids=[lane+"-"+str(i) for i in range(4)]))
 return r,s

class F99Bridge(unittest.TestCase):
 def test_valid_source_only_binding_remains_non_authorizing(self):
  r,s=fixture()
  o=join(r,s)
  self.assertEqual(o["schema"],SCHEMA)
  self.assertEqual(len(o["two_lane_source_bound_advisory"]),2)
  self.assertEqual([x["next_development_direction_only"] for x in o["two_lane_source_bound_advisory"]],
                   [PINS["Wingless"]["mechanism"],PINS["Yggdrasil"]["mechanism"]])
  self.assertFalse(o["actual_training_history_qualified"])
  self.assertFalse(o["causal_policy_gain_qualified"])
  self.assertFalse(o["scientific_original_firstuse_authorized"])
  self.assertEqual(o["accepted_reference_mutations"],0)
 def test_invalid_training_promotion_and_external_result(self):
  for obj,field,value in [
     ("r","new_trainable_genenv_records",1),
     ("r","research_selection_promotion_authorized",True),
     ("r","original_first_use_authorized",True),
     ("s","real_research_progress_established",True),
     ("s","model_invocations",1),
     ("s","accepted_ref_mutations",1),
  ]:
   r,s=fixture()
   (r if obj=="r" else s)[field]=value
   with self.subTest(field=field),self.assertRaises(Blocked):join(r,s)
 def test_false_provenance_and_cross_lane_substitution(self):
  for field,value in (
      ("zip_sha256","0"*64),
      ("source_commit","f"*40),
      ("frozen_blind_paired_correct",10),
      ("science_accepted",True),
      ("train_only_genenv_record_admitted",True),
  ):
   r,s=fixture()
   r["lanes"][0][field]=value
   with self.subTest(field=field),self.assertRaises(Blocked):join(r,s)
  r,s=fixture()
  r["lanes"].reverse()
  with self.assertRaises(Blocked):join(r,s)
  r,s=fixture()
  s["lanes"][1]["proposal_ids"][2]=s["lanes"][1]["proposal_ids"][0]
  with self.assertRaises(Blocked):join(r,s)
if __name__=="__main__":unittest.main()
