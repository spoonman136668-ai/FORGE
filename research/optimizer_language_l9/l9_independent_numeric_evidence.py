#!/usr/bin/env python3
"""Independent numeric-only authentication of L9's ONE existing held-out audit.

Post-run review; NEVER reads WebNLG source, hidden labels, predictions or model
weights. Does not launch/rerun an experiment, select a new model, or grant GO.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

RUN_SCHEMA="forge.optimizer.language.l9.unfamiliar-category-one-shot-numeric-v1"
BUNDLE_SCHEMA="forge.optimizer.language.l9.seven-arm-numeric-audit-bundle-v1"
ARM_SCHEMA="forge.optimizer.language.l9.unfamiliar-category-numeric-first-use-v1"
ROLE="b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726"
SUITE="710ce648a30ffc55647f689c5f4aa3ac13b07066"
SELECT="bbee9d6a6a92c3fbec536dbf8364ecae6b05ae46d86fbdef667f23d3179abc09"
PRE="910a5bc252b43818a8af7d4783dd4f25208c590e9b48f019bafd85faead7428f"
CAND="6bfcae415a3f1145397875b715c7d5015143e1544381be6a031eed636be88c3c"
RETR="ed7b21b6c4f648b337491aa5240ed1a7326f23164a13a0503748aded689e377b"
METHODS=("CANONICAL_FACTS_NONFLUENT_CONTROL","TRAIN_REFERENCE_RETRIEVAL","COMPOSITIONAL_PATTERN",
         "GRU_SEQ2SEQ-1701","GRU_SEQ2SEQ-1702",
         "SMALL_TRANSFORMER-1701","SMALL_TRANSFORMER-1702")
CHECKPOINTS={
    "GRU_SEQ2SEQ-1701":"a24469cf00be1c028cd5dfb25649f7bcc523b35792eb4680fe19aa8912f01daa",
    "GRU_SEQ2SEQ-1702":"1097e800b6ddc2acaa90df62943c6db1a34b1e1e62e51daf056f95303bb8d048",
    "SMALL_TRANSFORMER-1701":"bf731132c64dbfd82ea5bc6121d0006c34527101b040119f9d11d83931a99a84",
    "SMALL_TRANSFORMER-1702":"e5e7baaf4a0ad3be69213933419da96fb85842a0b40adafdecd587d00fccf5a0"}
CATEGORIES={
   "6c58160fe1935610171c4ef8e12c2fcb96cbb168db852a927e968b8dda7b0e11":31,
   "70b1e8e06785cae451496104850781f33faf6cc8e0777ecd3a9ccaaefb154b2d":153,
   "ccc9ff052aee8da1c7d607bee2283e981bd0bdce2de409fe3789ada64e20e080":135}
METRICS=("requested_content_proxy_coverage","normalized_entity_slot_coverage",
         "chrF_all_references_mean_per_example","token_f1_all_references_mean_per_example")
COUNT_KEYS=("triple_proxy_hits","triple_denominator","missing_triples_proxy","entity_slot_hits",
            "entity_slot_denominator","abstentions","reference_count","reference_bytes",
            "negation_marker_examples","extra_train_entity_mentions","terminal_punctuation_examples",
            "unresolved_placeholder_examples","repeated_adjacent_token_count")
CATEGORY_KEYS=set(COUNT_KEYS)|{"category_sha256","examples","triples"}|set(METRICS)
ARM_KEYS={"schema","status","arm","source_role_sha256","frozen_model_suite_git_blob","role",
          "categories","macro_by_heldout_category","micro_requested_content_proxy_coverage",
          "records","triple_denominator","serial_wall_seconds","serial_cpu_seconds",
          "resource_flops","resource_energy","all_original_references_scored",
          "model_reference_input_count","reference_contents_saved","raw_outputs_saved",
          "official_test_consumed","scientific_go"}
TOP_KEYS={"schema","status","source_role_sha256","model_suite_git_blob","arm_count",
          "heldout_categories","heldout_examples","arms","official_test_consumed","scientific_go",
          "one_shot_schema","selected_checkpoint_epoch","pre_admission_sha256",
          "development_select_seal_sha256","trained_candidate_state_sha256",
          "trained_retrieval_state_sha256","selected_checkpoint_sha256",
          "reconstructed_train_fit_wall_seconds","reconstructed_train_fit_cpu_seconds",
          "model_load_and_graph_custody_wall_seconds","all_seven_arms_prediction_wall_seconds",
          "reference_read_wall_seconds","total_pipeline_wall_seconds",
          "total_pipeline_cpu_seconds","python_peak_traced_bytes","resource_energy","resource_flops",
          "source_reference_leakage_to_model","all_seven_methods_completed_before_any_reference_access",
          "all_original_references_averaged_per_example",
          "additional_entity_mentions_inferred_from_train_vocabulary","audit_reference_read_count",
          "independent_semantic_adjudication_complete"}
def must(value,why):
    if not value:raise ValueError("L9_INDEPENDENT_AUDIT_FAIL_CLOSED:"+why)
def integer(value,minimum=0):
    return type(value) is int and value>=minimum
def number(value,minimum=0,maximum=None):
    return type(value) in (int,float) and math.isfinite(value) and value>=minimum and (maximum is None or value<=maximum)
def near(a,b):
    return number(a) and abs(a-b)<=2.01e-9
def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode("utf-8")
def pairs(items):
    result={}
    for k,v in items:
        must(k not in result,"duplicate JSON key")
        result[k]=v
    return result
def reject_constant(value):
    raise ValueError("unrecognized JSON numeric constant: "+value)
def load_numeric_bytes(raw:bytes):
    must(0<len(raw)<100000,"original JSON receipt size")
    # Reproduce original model-suite canonical JSON requirement without source imports.
    data=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject_constant)
    must(raw==canonical(data),"noncanonical or mutated original receipt bytes")
    return data
def check(original:dict):
    d=original
    must(type(d) is dict and set(d)==TOP_KEYS,"exact top-level numeric-only keys")
    required={"schema":BUNDLE_SCHEMA,
      "one_shot_schema":RUN_SCHEMA,
      "status":"UNFAMILIAR_AUDIT_NUMERIC_FIRST_USE_NOT_SEMANTIC_GO",
      "source_role_sha256":ROLE,"model_suite_git_blob":SUITE,
      "arm_count":7,"heldout_categories":3,"heldout_examples":319,
      "selected_checkpoint_epoch":12,"pre_admission_sha256":PRE,
      "development_select_seal_sha256":SELECT,
      "trained_candidate_state_sha256":CAND,"trained_retrieval_state_sha256":RETR,
      "selected_checkpoint_sha256":CHECKPOINTS,
      "resource_energy":"NOT_MEASURED","resource_flops":"NOT_MEASURED",
      "source_reference_leakage_to_model":False,
      "all_seven_methods_completed_before_any_reference_access":True,
      "all_original_references_averaged_per_example":True,
      "additional_entity_mentions_inferred_from_train_vocabulary":"NOT_MEASURED",
      "audit_reference_read_count":319,"official_test_consumed":False,
      "scientific_go":False,"independent_semantic_adjudication_complete":False}
    for k,v in required.items():
        must(d.get(k)==v,"provenance or scientific admission "+k)
    for k in ("reconstructed_train_fit_wall_seconds","reconstructed_train_fit_cpu_seconds",
              "model_load_and_graph_custody_wall_seconds","all_seven_arms_prediction_wall_seconds",
              "reference_read_wall_seconds","total_pipeline_wall_seconds","total_pipeline_cpu_seconds"):
        must(number(d[k]),"invalid resource "+k)
    must(integer(d["python_peak_traced_bytes"],1),"invalid peak memory")
    must(d["total_pipeline_wall_seconds"]+0.005>=sum(d[x] for x in (
      "reconstructed_train_fit_wall_seconds","model_load_and_graph_custody_wall_seconds",
      "all_seven_arms_prediction_wall_seconds","reference_read_wall_seconds")),
      "contradictory timing totals")
    arms=d["arms"]
    must(type(arms) is list and len(arms)==7 and [v.get("arm") for v in arms]==list(METHODS),
         "missing or reordered experimental/control arms")
    reference_counts=None
    reference_bytes=None
    for arm in arms:
        must(set(arm)==ARM_KEYS,"missing/extra arm numeric fields")
        for k,v in {"schema":ARM_SCHEMA,
                    "status":"NUMERICAL_PROXIES_ONLY_NOT_INDEPENDENT_SEMANTIC_GO",
                    "source_role_sha256":ROLE,"frozen_model_suite_git_blob":SUITE,
                    "role":"L9_AUDIT_DEV","records":319,
                    "model_reference_input_count":0,"reference_contents_saved":False,
                    "raw_outputs_saved":False,"official_test_consumed":False,
                    "scientific_go":False,"all_original_references_scored":True,
                    "resource_energy":"NOT_MEASURED","resource_flops":"NOT_MEASURED"}.items():
            must(arm.get(k)==v,"arm drift "+k)
        must(number(arm["serial_wall_seconds"]) and number(arm["serial_cpu_seconds"]),
             "arm resource invalid")
        cats=arm["categories"]
        must(type(cats) is list and len(cats)==3,"missing category report")
        must({r.get("category_sha256") for r in cats}==set(CATEGORIES),"unfamiliar category mismatch")
        must([r["category_sha256"] for r in cats]==sorted(CATEGORIES),"category order drift")
        totals={k:0 for k in ("examples","triples","triple_proxy_hits","triple_denominator",
               "missing_triples_proxy","abstentions","reference_count","reference_bytes")}
        for r in cats:
            must(type(r) is dict and set(r)==CATEGORY_KEYS,"category field omission or raw text")
            n=CATEGORIES[r["category_sha256"]]
            must(integer(r["examples"],1) and r["examples"]==n,"frozen heldout counts")
            for k in COUNT_KEYS+("examples","triples"):
                must(integer(r[k]),"noninteger category "+k)
            must(r["triples"]==r["triple_denominator"] and r["triples"]>=n,
                 "triple denominator")
            must(r["triple_proxy_hits"]+r["missing_triples_proxy"]==r["triples"],
                 "triple identity")
            must(r["entity_slot_denominator"]==2*r["triples"] and r["entity_slot_hits"]<=r["entity_slot_denominator"],
                 "entity slot denominator")
            must(r["abstentions"]<=n and r["reference_count"]>=n and r["reference_bytes"]>0,
                 "reference/abstention completeness")
            for k in ("negation_marker_examples","terminal_punctuation_examples",
                      "unresolved_placeholder_examples"):
                must(r[k]<=n,"indicator outside case count")
            for k in METRICS:
                must(number(r[k],0,1),"invalid bounded quality proxy "+k)
            must(near(r["requested_content_proxy_coverage"],
                      r["triple_proxy_hits"]/r["triple_denominator"]),
                      "triple proxy ratio drift")
            must(near(r["normalized_entity_slot_coverage"],
                      r["entity_slot_hits"]/r["entity_slot_denominator"]),
                      "entity slot ratio drift")
            for k in totals:totals[k]+=r[k]
        must(totals["examples"]==319 and totals["triples"]==arm["triple_denominator"],
             "per-arm total mismatch")
        must(near(arm["micro_requested_content_proxy_coverage"],
                  totals["triple_proxy_hits"]/totals["triples"]),"micro aggregate drift")
        must(type(arm["macro_by_heldout_category"]) is dict and
             set(arm["macro_by_heldout_category"])==set(METRICS),"macro fields")
        for k in METRICS:
            must(near(arm["macro_by_heldout_category"][k],sum(v[k] for v in cats)/3),
                 "macro category mean drift "+k)
        signature=[r["reference_count"] for r in cats]
        byte_sig=[r["reference_bytes"] for r in cats]
        if reference_counts is None:
            reference_counts,reference_bytes=signature,byte_sig
        else:
            must(signature==reference_counts and byte_sig==reference_bytes,
                 "control methods scored different reference sets")
    candidate=arms[2]
    retrieval=arms[1]
    candidate_macro=candidate["macro_by_heldout_category"]["requested_content_proxy_coverage"]
    retrieval_macro=retrieval["macro_by_heldout_category"]["requested_content_proxy_coverage"]
    qualitative=("CANDIDATE_PROXY_GREATER" if candidate_macro>retrieval_macro+2.01e-9 else
                 "CANDIDATE_PROXY_LOWER" if candidate_macro<retrieval_macro-2.01e-9 else
                 "PROXY_TIED_WITHIN_ROUNDING")
    return {
      "schema":"forge.optimizer.language.l9.independent-numeric-evidence-verification-v1",
      "status":"VERIFIED_NUMERIC_RECEIPT_NOT_INDEPENDENT_SEMANTIC_VALIDATION",
      "arm_count":7,"heldout_examples":319,"heldout_categories":3,
      "category_example_counts":[CATEGORIES[k] for k in sorted(CATEGORIES)],
      "candidate_vs_retrieval_macro_proxy_direction":qualitative,
      "candidate_macro_requested_content_proxy":candidate_macro,
      "retrieval_macro_requested_content_proxy":retrieval_macro,
      "method_coverage":{"all_arms":True,"all_original_references":True,
                         "no_partial_category":True,"no_raw_corpus_fields":True},
      "limitations":["Lexical content proxy is not semantic entailment.",
          "Entity and negation indicators do not establish factual correctness.",
          "Reported serial inference wall time does not include total training/energy/FLOPs.",
          "No independently adjudicated heldout semantic correctness or significance test."],
      "scientific_go":False,
      "original_test_consumed":False,
      "no_new_audit_read":True}
def verify(raw:bytes):
    return check(load_numeric_bytes(raw))
def main():
    p=argparse.ArgumentParser(description="Verify only the original numeric-only first-use receipt")
    p.add_argument("--original-numeric-receipt",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    must(not args.output.exists(),"independent report cannot overwrite")
    raw=args.original_numeric_receipt.read_bytes()
    report=verify(raw)
    report["input_original_numeric_sha256"]=hashlib.sha256(raw).hexdigest()
    result=canonical(report)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(result)
    print("L9_INDEPENDENT_NUMERIC_EVIDENCE_VALIDATED=PASS",flush=True)
    print("L9_INDEPENDENT_NUMERIC_EVIDENCE_SHA256="+hashlib.sha256(result).hexdigest(),flush=True)
    print("L9_SCIENTIFIC_GO=FALSE",flush=True)
if __name__=="__main__":main()
