#!/usr/bin/env python3
"""L9 protected-unfamiliar-audit contract qualification, WITHOUT first use.

Reads only frozen code/metadata + an already-issued mixed SELECT certificate.
No WebNLG corpus/DEV reference, checkpoint, model, optimizer, audit evaluator,
scheduler, or cross-project authorization is loaded or invoked.
"""
from __future__ import annotations
from collections import defaultdict
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN_FILE = "L9_AUDIT_FIRSTUSE_CONTRACT.json"
SEALED_SHA = "667f3e93d80a218284a68188dd8169f8b602ff37f63439282456e9e638478d66"
SOURCE_GIT_BLOBS = {
    "L9_FROZEN_PROTOCOL.json": "1602946d8c03e15324d36cd730691caccd12652f",
    "L9_PROTOCOL_AMENDMENT_1.json": "3d3b0cf2f4c74f36f9cd5feea69d93cd79b8933c",
    "L9_SOURCE_MANIFEST.json": "826379955c721e9c0eb01c760586ab7ebace7520",
    "L9_SPLIT_RECEIPT.json": "ca3e41e2835713bc922c56542656489f202c55cf",
    "L9_MODEL_CONTRACT.json": "4eab05a2b9011ebbaa34d01778e7f185807704c2",
    "l9_model_suite.py": "710ce648a30ffc55647f689c5f4aa3ac13b07066",
    "l9_neural_select_only.py": "91f8108af5e6f3a25e2a8ca07dc3674bd2358f4e",
    "l9_seal_select.py": "af06d6671954b9e8c5cf23c720e5efa89d919528",
}
ROLE_SHA = "b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726"
METHODS = (
    "CANONICAL_FACTS",
    "TRAIN_REFERENCE_RETRIEVAL",
    "COMPOSITIONAL_PATTERN",
    "GRU_SEQ2SEQ-seed1701",
    "GRU_SEQ2SEQ-seed1702",
    "SMALL_TRANSFORMER-seed1701-recoveryV2",
    "SMALL_TRANSFORMER-seed1702-recoveryV2",
)
EXPECTED_SELECTED = {
    ("GRU_SEQ2SEQ",1701): "a24469cf00be1c028cd5dfb25649f7bcc523b35792eb4680fe19aa8912f01daa",
    ("GRU_SEQ2SEQ",1702): "1097e800b6ddc2acaa90df62943c6db1a34b1e1e62e51daf056f95303bb8d048",
    ("SMALL_TRANSFORMER",1701): "bf731132c64dbfd82ea5bc6121d0006c34527101b040119f9d11d83931a99a84",
    ("SMALL_TRANSFORMER",1702): "e5e7baaf4a0ad3be69213933419da96fb85842a0b40adafdecd587d00fccf5a0",
}

def require(cond: bool, reason: str) -> None:
    if not cond:
        raise ValueError("L9_AUDIT_FIRSTUSE_PREFIT_REJECT:" + reason)

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()

def json_file(p:Path):
    return json.loads(p.read_bytes())

def verify_frozen_sources(root: Path) -> dict:
    results={}
    for path,expected in SOURCE_GIT_BLOBS.items():
        actual=git_blob((root/path).read_bytes())
        require(actual==expected,"GIT_SOURCE_DRIFT_"+path)
        results[path]=actual
    return results

def check_plan(plan: dict, root: Path) -> dict:
    require(type(plan) is dict,"PLAN_NOT_OBJECT")
    require(plan.get("schema")=="forge.optimizer.language.l9.audit-firstuse-source-contract-v1","PLAN_SCHEMA")
    require(plan.get("status")=="FROZEN_EVALUATION_SPECIFICATION_BEFORE_PROTECTED_AUDIT_FIRST_USE","PLAN_STATUS")
    require(plan.get("fixed_methods")==list(METHODS),"SEVEN_FROZEN_METHODS")
    frozen=plan.get("frozen_select",{})
    require(frozen.get("mixed_select_seal_sha256")==SEALED_SHA,"SEAL_SHA")
    require(frozen.get("seal_schema")=="forge.optimizer.language.l9.mixed-gru-v1-transformer-v2-select-seal-v1","SEAL_TYPE")
    require(frozen.get("original_v1_transformer_select_success") is False,"V1_TIMEOUT_NEGATIVE")
    require(frozen.get("first_use_decisions_from_proxies") is False,"NO_GO_FROM_PROXY")
    custody=plan.get("source_custody",{})
    split=json_file(root/"L9_SPLIT_RECEIPT.json")
    native=split["deterministic_split"]
    expected={"release_sha":"a7ea49b5ffa5011edf81e8530c59b3552a965023",
       "train_tree_sha1":"f7870bce053fa71fc1e2be2c0c2013e9f1c45433",
       "dev_tree_sha1":"70487b8ec5b11d8e54bfc13b9f7ac5ad153f4cae",
       "role_identity_sha256":ROLE_SHA,
       "expected_train":8480,"expected_select":2154,"expected_audit_dev":319,
       "expected_heldout_categories":3,"expected_train_audit_graph_overlap":0,
       "quarantined_train_records":7,"test_tree_content_read":False}
    for k,v in expected.items():
        require(custody.get(k)==v,"SOURCE_CUSTODY_"+k)
    require(native["train"]==custody["expected_train"],"TRAIN_COUNT")
    require(native["select"]==custody["expected_select"],"SELECT_COUNT")
    require(native["audit_dev"]==custody["expected_audit_dev"],"AUDIT_COUNT")
    require(native["audit_categories"]==custody["expected_heldout_categories"],"AUDIT_CATEGORIES")
    require(split["structural_prefit_finding"]["quarantined_train_records"]==custody["quarantined_train_records"],"QUARANTINE")
    require(split["structural_prefit_finding"]["remaining_train_audit_graph_overlap"]==0,"GRAPH_LEAKAGE")
    require(native["cross_os_role_identity_sha256"]==ROLE_SHA,"ROLE_ID")
    sm=json_file(root/"L9_SOURCE_MANIFEST.json")
    require(sm["release_v3_full_sha"]==custody["release_sha"],"RELEASE_ID")
    require(sm["paths"]["train"]["tree_sha1"]==custody["train_tree_sha1"],"TRAIN_TREE")
    require(sm["paths"]["dev"]["tree_sha1"]==custody["dev_tree_sha1"],"DEV_TREE")
    require(sm["paths"]["test"]["protected"] is True,"OFFICIAL_TEST_MUST_REMAIN_CLOSED")
    frozen_protocol=json_file(root/"L9_FROZEN_PROTOCOL.json")
    require(len(frozen_protocol["methods"])==5,"ORIGINAL_FIVE_ARMS")
    require(set(x["id"] for x in frozen_protocol["methods"])=={
       "CANONICAL_FACTS","TRAIN_REFERENCE_RETRIEVAL","COMPOSITIONAL_PATTERN",
       "GRU_SEQ2SEQ","SMALL_TRANSFORMER"},"ORIGINAL_METHODS")
    require(frozen_protocol["frozen_split_rule"]["audit"].startswith("Use only official DEV"),"PROTECTED_AUDIT_ROLE")
    controls=plan.get("semantic_controls",{})
    needed=("evaluate_all_319_each_method","retain_all_3_heldout_categories",
       "no_category_or_seed_dropping","macro_average_each_category_equal_weight",
       "abstention_zero_coverage_include_all_denominators",
       "candidate_no_canonical_facts_fallback",
       "heldout_reference_never_fit_or_tune","trained_proxy_map_train_only",
       "no_verbal_entailment_claim_from_lexical_proxy_only",
       "no_hard_false_positive_semantic_acceptance")
    require(all(controls.get(k) is True for k in needed),"SEMANTIC_CONTROLS")
    metrics=plan.get("metrics_required",{})
    per=metrics.get("per_heldout_category",[])
    whole=metrics.get("whole_audit",[])
    require(len(per)==len(set(per))>=13,"INCOMPLETE_CATEGORY_METRICS")
    require(len(whole)==len(set(whole))>=16,"INCOMPLETE_RESOURCE_METRICS")
    for must in ("multireference_chrF","per_triple_coverage_train_derived_proxy",
                 "extra_entity_proxy","negation_marker_conflict_proxy",
                 "explicit_abstentions","missing_requested_triples"):
        require(must in per,"REQUIRED_METRIC_"+must)
    for must in ("full_train_cpu_wall_seconds","full_select_cpu_wall_seconds",
                 "peak_rss_bytes","total_serialized_model_bytes",
                 "verification_and_repair_cost_included","flops_or_NOT_MEASURED",
                 "energy_or_NOT_MEASURED","macro_average_across_categories"):
        require(must in whole,"REQUIRED_RESOURCE_"+must)
    advancement=plan.get("advancement",{})
    require(advancement.get("automated_scientific_go_from_this_contract") is False,"SCIENCE_GO_FALSE")
    require("candidate_vs_train_reference_retrieval" in advancement and
            "semantic coverage" in advancement["candidate_vs_train_reference_retrieval"],"RETRIEVAL_CONTROL")
    first=plan.get("first_use",{})
    required={"protected_audit_role":"L9_AUDIT_DEV",
      "prospective_contract_only":True,"authorization_and_independent_witness_required":True,
      "current_authorized_protected_first_use":False,
      "audit_reference_bytes_read_in_this_gate":0,
      "official_test_content_allowed":False,"scientific_go":False}
    for k,v in required.items():
        require(first.get(k)==v,"FIRST_USE_FAIL_CLOSED_"+k)
    return {"audit_count":native["audit_dev"],"heldout_categories":native["audit_categories"],
            "train_audit_graph_overlap":0,"method_count":len(METHODS),
            "first_use_authorized":False}

def check_mixed_seal(raw: bytes) -> dict:
    require(sha(raw)==SEALED_SHA,"ORIGINAL_MIXED_SEAL_SHA")
    obj=json.loads(raw)
    required={"schema":"forge.optimizer.language.l9.mixed-gru-v1-transformer-v2-select-seal-v1",
      "status":"FOUR_CHOICE_MIXED_V1_GRU_V2_TRANSFORMER_DEV_SEALED",
      "source_role_sha256":ROLE_SHA,"model_suite_git_blob":SOURCE_GIT_BLOBS["l9_model_suite.py"],
      "all_four_choices_complete":True,"original_v1_select_seal_complete":False,
      "audit_dev_references_consumed":False,"official_test_consumed":False,"scientific_go":False}
    for k,v in required.items():
        require(obj.get(k)==v,"MIXED_SEAL_"+k)
    options=obj.get("neural_checkpoint_selection",[])
    require(type(options) is list and len(options)==4,"FOUR_CHOICES_REQUIRED")
    seen=set()
    for x in options:
        require(type(x) is dict,"BAD_CHOICE")
        key=(x.get("arm"),x.get("seed"))
        require(key in EXPECTED_SELECTED and key not in seen,"CHOICE_IDENTITY")
        seen.add(key)
        require(x.get("selected_epoch")==12,"CHOICE_EPOCH")
        require(x.get("checkpoint_sha256")==EXPECTED_SELECTED[key],"CHECKPOINT_SHA")
        version=("ORIGINAL_FROZEN_V1" if key[0]=="GRU_SEQ2SEQ" else
                 "SEPARATELY_QUALIFIED_RECOVERY_V2_NOT_V1")
        require(x.get("receipt_type")==version,"SOURCE_VERSION_DRIFT")
    require(seen==set(EXPECTED_SELECTED),"MISSING_CHOICES")
    require(obj.get("candidate",{}).get("selected_config")=={
         "min_template_support":1,"max_templates_per_predicate":4,"joiner":" "},
         "COMPOSITIONAL_CANDIDATE_ID")
    return {"selected_models":len(seen),"original_v1_transformer_success":False,
            "separate_v2_transformer_seeds":2,"audit_references_consumed":False}

def per_category_macro(synthetic_rows: list[dict], categories: tuple[str,...]) -> dict:
    """Synthetic-only regression for category weights and abstention denominators.

    This is NOT a semantic metric and MUST NOT be called on protected audit data.
    """
    require(len(categories)==3 and len(set(categories))==3,"THREE_CATEGORIES_REQUIRED")
    expected={(c,m) for c in categories for m in METHODS}
    observed={}
    for row in synthetic_rows:
        require(type(row) is dict,"INVALID_SYNTHETIC_ROW")
        key=(row.get("category"),row.get("method"))
        require(key in expected and key not in observed,"MISSING_OR_DUPLICATE_METHOD_CATEGORY")
        total=row.get("total");hit=row.get("hit");abst=row.get("abstentions")
        require(all(type(n) is int for n in (total,hit,abst)) and
                total>0 and 0<=hit<=total and 0<=abst<=total,"PROXY_COUNTS")
        require(hit<=total-abst,"ABSTENTION_CANNOT_COUNT_AS_COVERAGE")
        observed[key]=hit/total
    require(set(observed)==expected,"INCOMPLETE_CATEGORY_GRID")
    result={}
    for method in METHODS:
        result[method]=round(sum(observed[(c,method)] for c in categories)/3,9)
    return result

def evaluate_source_only(root: Path, seal_raw: bytes, *, out: Path) -> dict:
    require(not out.exists(),"REFUSE_RECEIPT_OVERWRITE")
    verified=verify_frozen_sources(root)
    plan_bytes=(root/PLAN_FILE).read_bytes()
    contract=check_plan(json.loads(plan_bytes),root)
    seal=check_mixed_seal(seal_raw)
    categories=("SYNTHETIC-UNSEEN-A","SYNTHETIC-UNSEEN-B","SYNTHETIC-UNSEEN-C")
    invented=[{"category":c,"method":m,"total":5*(idx+1),"hit":0,
               "abstentions":5*(idx+1)}
              for idx,c in enumerate(categories) for m in METHODS]
    preview=per_category_macro(invented,categories)
    require(all(x==0 for x in preview.values()),"ABSTENTION_DENOMINATOR_BYPASS")
    receipt={
       "schema":"forge.optimizer.language.l9.audit-firstuse-source-prefit-receipt-v1",
       "status":"SOURCE_PREFIT_ONLY_PROTECTED_FIRST_USE_BLOCKED",
       "contract_sha256":sha(plan_bytes),
       "mixed_four_choice_seal_sha256":sha(seal_raw),
       "verified_original_git_blobs":verified,
       "role_identity_sha256":ROLE_SHA,
       "contract":contract,"sealed_selection":seal,
       "synthetic_all_abstain_category_macro":preview,
       "protected_audit_cases_scored":0,
       "protected_audit_reference_bytes_read":0,
       "official_test_bytes_read":0,
       "model_checkpoint_loaded":False,
       "fit_or_scientific_metric_executed":False,
       "source_only_first_use_readiness":True,
       "first_use_authorized":False,
       "first_use_lease_or_witness_issued":False,
       "independent_semantic_transfer_proven":False,
       "scientific_go":False,
       "next_gate":"Separate original-data first-use and semantic evaluator admission under existing FORGE-native authenticated controls",
    }
    raw=(json.dumps(receipt,sort_keys=True,ensure_ascii=False,
       separators=(",",":"))+"\n").encode("utf-8")
    out.write_bytes(raw)
    return receipt

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--mixed-seal",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args()
    result=evaluate_source_only(HERE,a.mixed_seal.read_bytes(),out=a.out)
    print("L9_FROZEN_AUDIT_FIRSTUSE_SOURCE_PREFIT=PASS")
    print("L9_PROTECTED_AUDIT_FIRST_USE_AUTHORIZED=FALSE")
    print("L9_AUDIT_REFERENCE_BYTES_READ=0")
    print("L9_SCIENTIFIC_GO=FALSE")
    print("L9_AUDIT_PREFIT_SHA256="+sha(a.out.read_bytes()))

if __name__=="__main__":
    main()
