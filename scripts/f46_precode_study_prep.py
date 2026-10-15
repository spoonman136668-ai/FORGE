"""F46: prepare owner-intake TRAIN-only prereg drafts from exact authentic F45 successor decisions.
No experimental implementation, worker start, source freeze or primary original permitted.
"""
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA="forge.autonomy.f45-real-train-successor.v1"
EXPECTED_PARENT_SHA="a0870b70d51069c2e174b5056fd03bea1d6c7e21c9fceb778f79211576942aaf"
SOURCES={
 "Wingless":(38800310426,12003528038,
             "ff93c23e7e7f1a01e8187a765ac95c9d47c8189d",
             "3fd7fe7a4291feec517e95795367c8a40ad6e371dde605130ae3f3ff0ab6b996"),
 "Yggdrasil":(38800495808,12003268501,
             "9107ddf19ff05a0afa5a085e0c9ee477a7335db6",
             "7bb34fb448fc17fc0e4d13fa02875d5310620f5eda3e6ecd8a70d11922e9fa4c")
}
class Blocked(ValueError):pass
def require(condition,description):
 if not condition:raise Blocked("F46_PREP_"+description)
def parse(raw):
 def unique(pairs):
  d={}
  for k,v in pairs:
   require(k not in d,"DUPLICATE_JSON_KEY")
   d[k]=v
  return d
 require(isinstance(raw,bytes) and 0<len(raw)<50000,"SOURCE_SIZE")
 return json.loads(raw,object_pairs_hook=unique)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def plans(raw, expected_sha=EXPECTED_PARENT_SHA):
 require(sha(raw)==expected_sha,"UNPINNED_F45_DECISION")
 src=parse(raw)
 require(src.get("schema")==SCHEMA and src.get("fresh_train_evidence_recomputed") is True
         and src.get("future_originals_preserved") is True and
         src.get("new_science_originals_executed")==0 and
         src.get("worker_dispatch_authorized") is False and
         src.get("theta_promotion_authorized") is False and
         src.get("recursive_policy_improvement_proven") is False,"FALSE_AUTHORITY")
 decisions=src.get("decisions")
 evidence=src.get("evidence")
 require(type(decisions) is list and len(decisions)==2 and
         type(evidence) is dict and set(evidence)==set(SOURCES) and
         [d.get("lane") for d in decisions]==["Wingless","Yggdrasil"],"LANE_SOURCE_DRIFT")
 for lane,ident in SOURCES.items():
  e=evidence[lane]
  require([e.get(k) for k in ("run_id","artifact_id","source_commit","report_sha256")]==list(ident)
          and isinstance(e.get("stage"),str),"AUTHENTIC_EVIDENCE_DRIFT")
 w,y=decisions
 require(w.get("next_hypothesis")=="REPLACE_AMBIGUITY_GATE_WITH_PUBLIC_QUERY_EDGE_VALUE_OF_COMPUTATION"
         and w.get("frozen_criterion_met") is False
         and w.get("original_authorized") is False
         and w.get("trial_correct")==56 and w.get("control_correct")==56
         and w.get("total")==72 and w.get("gain_pp")==0.0
         and w.get("control_policy")=="one_step_value","WING_LESS_NEGATIVE_DRIFT")
 require(y.get("next_hypothesis")=="ISOLATE_CAUSAL_PAIRED_INTERVENTION_BENEFIT_FROM_LEARNED_BASELINE"
         and y.get("frozen_criterion_met") is False and
         y.get("original_authorized") is False and
         y.get("trial_correct")==118 and y.get("control_correct")==114
         and y.get("ablation_correct")==118 and y.get("total")==128
         and y.get("ablation_gain_pp")==0.0
         and y.get("control_policy")=="fitted_Gaussian_latent","YGG_ABLATION_DRIFT")
 common={
  "schema":"forge.autonomy.f46-precode-owner-intake.v1",
  "predecessor_selection_sha256":sha(raw),
  "stage":"PRECODE_PREREG_CANDIDATE_NOT_OWNER_ADMITTED",
  "train_only":True,"implementation_present":False,
  "owner_prereg_committed":False,"owner_original_claim_consumed":False,
  "original_worker_dispatch_authorized":False,
  "scientific_accepted":False,"accepted_ref_mutation":False,
  "f3_independent_source_custody":False,
  "native_576b_residency_established":False,
  "paid_api_calls":0,
  "source_and_cohorts_must_be_frozen_before_first_experiment":True,
  "independent_future_scientific_review_required":True
 }
 wing=dict(common,
  lane="Wingless",experiment_id="W-F46-PUBLIC-EDGE-VOC-TRAIN-PROPOSAL",
  hypothesis=w["next_hypothesis"],predecessor_artifact_id=SOURCES["Wingless"][1],
  mechanism="Select a paid mapping or bounded posterior lookahead by the expected reduction in final-answer loss per unit of publicly estimable compute, conditioned on query-edge path relevance instead of a generic ambiguity threshold",
  public_only_inputs=["visible_typed_relation_triples","ordered_query_edges","public_posterior_summary","measured_posterior_world_budget"],
  candidate_selector="query_edge_expected_answer_value_per_compute",
  train_fit_seed_range_exclusive=[391000,391012],
  train_diagnostic_seed_range_exclusive=[391100,391112],
  proposed_train_families=[500,501,502,503],
  excluded_original_seed_range_exclusive=[372000,372016],
  excluded_original_families=[464,465,466,467],
  proposed_future_original_seed_range_exclusive=[392000,392016],
  proposed_future_original_families=[504,505,506,507],
  fair_controls=["one_step_value","exact_entropy","query_frontier","no_purchase","budget_matched_rank"],
  evaluator_only_control="full_hidden_mapping_oracle",
  max_paid_mappings_per_case=2,
  max_candidate_posterior_work_ratio_vs_best_fair=1.2,
  min_gain_pp_over_best_equal_budget_fair=3.0,
  require_no_family_degradation=True,
  metered_independent_receipts_and_work_required=True,
  fail_condition="Any budget overrun, family regression, source leakage, or gain below +3pp is a scientific negative",
  source_lineage_policy="MUST_NOT_REUSE_F45_RESERVE_ORIGINALS_OR_F45_TRAIN")
 ygg=dict(common,
  lane="Yggdrasil",experiment_id="Y-F46-PAIRED-CAUSAL-ANCHORS-TRAIN-PROPOSAL",
  hypothesis=y["next_hypothesis"],predecessor_artifact_id=SOURCES["Yggdrasil"][1],
  mechanism="Separate paired-intervention information from general public anchor features using count-matched shuffled pairs, unpaired learned model, and same-capacity fitted Gaussian on unseen sensing mechanisms",
  public_only_inputs=["public_paired_calibration_anchors","public_unpaired_anchor_controls","first_purchased_channel","public_task_type"],
  candidate_selector="paired_intervention_causal_feature_model",
  train_fit_seed_range_exclusive=[401000,401008],
  train_diagnostic_seed_range_exclusive=[401100,401108],
  proposed_train_families=[520,521,522,523],
  excluded_original_seed_range_exclusive=[382000,382016],
  excluded_original_families=[484,485,486,487],
  proposed_future_original_seed_range_exclusive=[402000,402016],
  proposed_future_original_families=[524,525,526,527],
  fair_controls=["fitted_Gaussian_latent","empirical_conditional_Brier",
                 "Gaussian_kernel","learned_unpaired_ablation",
                 "count_matched_shuffled_intervention_pairs","first_masked"],
  evaluator_only_control="hidden_mechanism_oracle",
  paid_target_channels_per_case=2,
  public_reference_pairs_per_source=12,
  require_equal_anchor_count_and_model_budget=True,
  min_gain_pp_over_strongest_fair=2.0,
  require_positive_paired_vs_count_matched_shuffled_ablation=True,
  require_no_heldout_mechanism_regression=True,
  report_metrics=["accuracy","Brier","logloss","false_positive","false_negative","mechanism_strata"],
  fail_condition="No positive paired-vs-shuffled causal ablation, metric regression, or less than +2pp is a scientific negative",
  source_lineage_policy="MUST_NOT_REUSE_F45_RESERVE_ORIGINALS_OR_F45_TRAIN")
 # No overlap between proposed TRAINS, protected legacy originals or proposed future originals.
 for plan in (wing,ygg):
  ranges=[plan[k] for k in ("train_fit_seed_range_exclusive",
          "train_diagnostic_seed_range_exclusive",
          "excluded_original_seed_range_exclusive",
          "proposed_future_original_seed_range_exclusive")]
  require(all(type(v) is list and len(v)==2 and
              all(type(z) is int for z in v) and v[0]<v[1] for v in ranges)
          and all(a[1]<=b[0] or b[1]<=a[0]
                  for i,a in enumerate(ranges) for b in ranges[i+1:]),"SEED_CONFLICT")
  families=[set(plan[k]) for k in ("proposed_train_families",
                 "excluded_original_families","proposed_future_original_families")]
  require(not any(a&b for i,a in enumerate(families) for b in families[i+1:]),
          "FAMILY_CONFLICT")
 require(wing["train_fit_seed_range_exclusive"]!=ygg["train_fit_seed_range_exclusive"],
         "CROSS_LANE_SOURCE_COLLISION")
 return {"Wingless":wing,"Yggdrasil":ygg}
def canonical(d):return (json.dumps(d,sort_keys=True,separators=(",",":"))+"\n").encode()
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--successors",required=True)
 p.add_argument("--output-dir",required=True)
 a=p.parse_args()
 pth=Path(a.output_dir)
 require(pth.is_dir(),"OUTPUT_DIR_ABSENT")
 proposed=plans(Path(a.successors).read_bytes())
 hashes=[]
 for lane,plan in proposed.items():
  filename=lane.lower()+"-f46-owner-intake.json"
  raw=canonical(plan)
  (pth/filename).write_bytes(raw)
  hashes.append(sha(raw)+"  "+filename)
 (pth/"sha256-manifest.txt").write_text("\n".join(hashes)+"\n")
 print("F46_TWO_REPRODUCIBLE_OWNER_INTAKES_PREPARED_NO_SCIENCE=PASS")
if __name__=="__main__":main()
