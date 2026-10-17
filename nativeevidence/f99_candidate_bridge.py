"""Join F99 real historical DEV descriptors to existing model-free proposal screen.

Never convert archive metadata or past DEV comparisons into trainable GenEnv
history, objective policy reward, new hypothesis code, or accepted science.
"""
import json
import pathlib
import sys
try:
 from f99_archive_extract import PINS,SCHEMA as REAL_SCHEMA,Blocked,require
except ModuleNotFoundError:
 from nativeevidence.f99_archive_extract import PINS,SCHEMA as REAL_SCHEMA,Blocked,require

SCHEMA="forge.autonomy.f99.source-joined-development-constraint-advisory.v1"
SCREEN_SCHEMA="forge.model-free.two-lane-untested-advisory.v1"

def join(real,screen):
 require(type(real) is dict and real.get("schema")==REAL_SCHEMA and
         type(screen) is dict and screen.get("schema")==SCREEN_SCHEMA and
         real.get("forge_source_sha")==screen.get("source_commit_sha") and
         real.get("disposition")=="REAL_DEV_ROW_REAGGREGATION_ONLY_NO_TRAINING_OR_NOVEL_SCIENCE_AUTHORITY" and
         real.get("cohort_source")=="EXACT_PINNED_GITHUB_ACTIONS_ZIP_AND_CONTAINED_JSON_BYTES" and
         real.get("distinct_authentic_dev_lane_sources")==2 and
         real.get("descriptive_development_constraints_verified")==2 and
         real.get("new_trainable_genenv_records")==0 and
         real.get("new_scientific_originals")==0 and
         real.get("original_first_use_authorized") is False and
         real.get("research_selection_promotion_authorized") is False and
         real.get("accepted_research_ref_mutation") is False and
         real.get("model_invocations")==0 and real.get("codex_invocations")==0 and
         real.get("external_model_api_calls")==0,
         "AUTHENTIC_DEVELOPMENT_GATE")
 require(screen.get("evidence_type")=="SYNTHETIC_FROZEN_SOURCE_ONLY_NOT_NEW_SCIENTIFIC_EVIDENCE" and
         screen.get("model_invocations")==0 and screen.get("codex_invocations")==0 and
         screen.get("network_calls")==0 and screen.get("new_scientific_originals")==0 and
         screen.get("scientific_first_use_authorized") is False and
         screen.get("policy_promotion_authorized") is False and
         screen.get("real_research_progress_established") is False and
         screen.get("accepted_ref_mutations")==0,
         "SYNTHETIC_PROPOSALS_CLAIMED_SCIENCE")
 rs=real.get("lanes");ss=screen.get("lanes")
 require(type(rs) is list and type(ss) is list and len(rs)==len(ss)==2,
         "TWO_LANE_COHORT")
 joined=[]
 for lane,r,s in zip(("Wingless","Yggdrasil"),rs,ss):
  p=PINS[lane]
  require(type(r) is dict and type(s) is dict and r.get("lane")==s.get("lane")==lane and
          r.get("source_commit")==p["commit"] and
          r.get("original_archive_run_id")==p["run"] and
          r.get("original_artifact_id")==p["artifact"] and
          r.get("zip_sha256")==p["zip"] and
          r.get("contained_json_sha256")==p["json"] and
          r.get("historical_development_pair_count")==p["pairs"] and
          r.get("frozen_blind_paired_correct")==0 and
          r.get("coded_oracle_paired_correct")==p["pairs"] and
          r.get("historical_negative_mechanism_constraint")==p["mechanism"] and
          r.get("source_bytes_and_rows_reaudited") is True and
          r.get("stage")=="AUTHENTIC_HISTORICAL_DEVELOPMENT_ONLY" and
          r.get("independent_original_firstuse_qualified") is False and
          r.get("train_only_genenv_record_admitted") is False and
          r.get("science_accepted") is False and
          s.get("prompt_candidates")==2 and s.get("environment_candidates")==2 and
          s.get("negative_records")==1 and s.get("invalid_records")==1 and
          s.get("mixed_records")==1 and
          s.get("all_candidates_untested") is True and
          s.get("full_population_screened") is True and
          s.get("science_accepted") is False and
          s.get("original_dispatch_authorized") is False and
          s.get("advisory_assessment")=="BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY" and
          type(s.get("proposal_ids")) is list and len(s["proposal_ids"])==4 and
          len(set(s["proposal_ids"]))==4,
          "CROSS_LANE_OR_RECORD_PROMOTION_OR_SOURCE_MISMATCH")
  joined.append(dict(
    lane=lane,historical_source_sha=p["commit"],
    observed_negative_constraint=p["mechanism"],
    blind_paired_correct=0,oracle_paired_correct=p["pairs"],
    verified_historical_development_pairs=p["pairs"],
    synthetic_candidate_population_ids=list(s["proposal_ids"]),
    synthetic_candidates_still_untested=True,
    next_development_direction_only=p["mechanism"],
    new_trainable_records=0,scientific_result_accepted=False))
 return dict(
  schema=SCHEMA,forge_source_sha=real["forge_source_sha"],
  two_lane_source_bound_advisory=joined,
  synthetic_candidate_proposals_unmodified=True,
  actual_training_history_qualified=False,
  causal_policy_gain_qualified=False,
  scientific_original_firstuse_authorized=False,
  model_invocations=0,codex_invocations=0,
  accepted_reference_mutations=0)
def load(path):
 p=pathlib.Path(path)
 require(p.is_file() and not p.is_symlink() and p.stat().st_size<=131072,
         "INPUT_SIZE")
 return json.loads(p.read_bytes())
def main(args):
 require(len(args)==2,"EXPECTED_REAL_AND_SYNTHETIC_REPORTS")
 print(json.dumps(join(load(args[0]),load(args[1])),sort_keys=True,separators=(",",":")))
if __name__=="__main__":
 try:main(sys.argv[1:])
 except (Blocked,OSError,KeyError,ValueError,TypeError) as err:
  print("FORGE_F99_CANDIDATE_SOURCE_JOIN=QUARANTINED",file=sys.stderr)
  sys.exit(1)
