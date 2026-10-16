"""F100: frozen development-only successor hypotheses from F99 real negatives.

This is a *source-only preregistration verifier*, not inference or an experiment.
No external GitHub calls, model, optimizer, first-use or outcome selection.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
F99=ROOT/"reference/research-intake/f99-authentic-development-negative-history.json"
F100=ROOT/"reference/research-intake/f100-frozen-successor-contract.json"
SCHEMA="forge.autonomy.f100.frozen-negative-driven-development-contract.v1"
REPORT="forge.autonomy.f100.development-successor-preregistration-proof.v1"
BASE="4218c64f310c59b3a9124ec309d727475e6f2bf3"
PARENT_BLOB="a280814e324d80bcc2590bbab939446180683e45"
HEX40=re.compile(r"^[0-9a-f]{40}$")
class Rejected(ValueError):pass
def need(condition,message):
    if not condition:raise Rejected("F100_"+message)
def strict_pairs(kvs):
    out={}
    for k,v in kvs:
        need(k not in out,"DUPLICATE_JSON_KEY")
        out[k]=v
    return out
def read_json(path):
    raw=pathlib.Path(path).read_bytes()
    need(0<len(raw)<=128000,"INVALID_JSON_LENGTH")
    try:
        obj=json.loads(raw.decode("utf-8"),object_pairs_hook=strict_pairs,
                       parse_constant=lambda _ :need(False,"NONFINITE_JSON"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise Rejected("F100_INVALID_JSON") from exc
    need(type(obj) is dict,"INVALID_DOCUMENT")
    return obj,raw
def git_blob_sha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\x00"+data).hexdigest()
def check_contract(f100,f99,parent_bytes):
    need(f100.get("schema")==SCHEMA,"F100_CONTRACT_SCHEMA_DRIFT")
    need(f100.get("prior_f99_head_sha")==BASE,"F99_EXACT_HEAD_DRIFT")
    need(f100.get("prior_f99_repository")=="spoonman136668-ai/FORGE" and
         f100.get("prior_f99_manifest_path")=="reference/research-intake/f99-authentic-development-negative-history.json",
         "F99_SOURCE_PATH_DRIFT")
    need(f100.get("prior_f99_manifest_git_blob_sha")==PARENT_BLOB,
         "F99_CONTRACT_BLOB_DRIFT")
    need(git_blob_sha(parent_bytes)==PARENT_BLOB,"F99_ACTUAL_BLOB_HASH_DRIFT")
    need(f99.get("schema")=="forge.autonomy.f99.authentic-development-negative-history.v1" and
         f99.get("purpose")=="FROZEN_ARCHIVED_DEVELOPMENT_NEGATIVES_FOR_READONLY_METHOD_PLANNING_ONLY","PARENT_F99_NEGATIVE_SOURCE_MISSING")
    need(f100.get("scientific_status")=="SOURCE_ONLY_PREREGISTRATION_NO_NEW_EXPERIMENT_OR_AUTONOMOUS_MODEL" and
         f100.get("preregistration_sealed_before_implementation") is True,
         "NOT_PREREGISTERED_BEFORE_IMPLEMENTATION")
    alloc=f100.get("allocation")
    need(type(alloc) is dict and alloc.get("Wingless")==1 and alloc.get("Yggdrasil")==1 and
         alloc.get("selection_method")=="SCREEN_ALL_FOUR_NO_AUTOMATIC_BEST_CANDIDATE_PROMOTION",
         "ALLOCATION_OR_SELECTION_DRIFT")
    authority=f100.get("authorization")
    need(type(authority) is dict,"AUTHORITY_OBJECT_MISSING")
    for x in ("prospective_scientific_original_authorized","protected_first_use_authorized",
              "independently_accepted_science","model_inference_configured",
              "genenv_training_activated","optimizer_promotion_authorized",
              "new_research_experiment_executed","ckb_plane_contact"):
        need(authority.get(x) is False,"UNAUTHORIZED_"+x.upper())
    for x in ("accepted_ref_mutations","codex_calls","paid_model_api_calls"):
        need(type(authority.get(x)) is int and authority[x]==0,"NONZERO_"+x.upper())
    need(f100.get("disposition")=="PUBLIC_DEV_DESIGN_ONLY_AWAITING_SEPARATELY_FROZEN_IMPLEMENTATIONS_NO_FIRST_USE","DISPOSITION_DRIFT")
    lanes=f100.get("lanes")
    parents=f99.get("cohorts")
    need(type(lanes) is list and type(parents) is list and len(lanes)==len(parents)==2 and
         [r.get("lane") for r in lanes]==[r.get("lane") for r in parents]==["Wingless","Yggdrasil"],
         "LANE_ISOLATION_DRIFT")
    all_ids=set()
    records=[]
    for lane,old in zip(lanes,parents):
        name=lane["lane"]
        wing=name=="Wingless"
        obs=lane.get("observed_development_negative",{})
        need(old.get("lane")==name and lane.get("parent_experiment")==old.get("experiment") and
             lane.get("parent_artifact_id")==old.get("artifact_id") and
             lane.get("parent_payload_sha256")==old.get("payload_sha256") and
             obs.get("paired_total")==old.get("pair_count") and
             obs.get("frozen_learned_paired_correct")==old.get("learned_correct_pairs")==0 and
             obs.get("coded_depth_oracle_paired_correct" if wing else "coded_role_oracle_paired_correct")==old.get("coded_control_correct_pairs")==old.get("pair_count") and
             obs.get("classification")==old.get("classification"),
             "AUTHENTIC_HISTORICAL_NEGATIVE_WAS_CHANGED")
        missing=("REQUESTED_REASONING_DEPTH_ABSENT_FROM_LEARNED_INPUT" if wing else
                 "TYPED_RELATION_ROLES_AND_VARIABLE_BINDING_ABSENT_FROM_LEARNED_STATE")
        need(lane.get("diagnosed_missing_information")==missing,"WRONG_INFORMATION_DEFICIT")
        specs=lane.get("candidates")
        need(type(specs) is list and len(specs)==2,"CANDIDATE_POPULATION_INCOMPLETE")
        expected=({"W100-C1","W100-C2"} if wing else {"Y100-C1","Y100-C2"})
        seen=set()
        mechanisms=set()
        for c in specs:
            need(type(c) is dict and set(c)=={
                "id","mechanism_family","new_input","new_state","new_consumer",
                "falsifiable_mechanism","no_hardcoded_oracle_in_candidate"},"CANDIDATE_SCHEMA_DRIFT")
            cid=c["id"]
            need(cid in expected and cid not in seen and cid not in all_ids and
                 c["no_hardcoded_oracle_in_candidate"] is True,
                 "CHERRY_PICKED_OR_HARDCODED_CANDIDATE")
            seen.add(cid)
            all_ids.add(cid)
            for field in ("mechanism_family","new_input","new_state","new_consumer","falsifiable_mechanism"):
                need(type(c[field]) is str and 12<=len(c[field])<=240,"UNDERSPECIFIED_CANDIDATE")
            mechanisms.add(c["mechanism_family"])
            need(("depth" in c["falsifiable_mechanism"] if wing else
                  ("role" in c["falsifiable_mechanism"] or "binding" in c["falsifiable_mechanism"])),
                 "MISSING_INFORMATION_SENSITIVE_FALSIFIER")
        need(seen==expected and len(mechanisms)==2,"DUPLICATE_MECHANISM_FAMILY")
        controls=lane.get("controls")
        required=(["frozen_depth_blind_W_F10","size_matched_depth_input_removed",
                   "requested_depth_randomly_permuted","always_yes_shortcut","coded_depth_aware_oracle"]
                  if wing else
                  ["frozen_role_blind_Y_F9","size_matched_role_input_removed",
                   "typed_role_codes_randomly_permuted","always_yes_shortcut","coded_typed_role_oracle"])
        need(controls==required,"MISSING_STRONG_OR_ADVERSARIAL_CONTROLS")
        blocks=lane.get("public_development_seed_blocks")
        need(type(blocks) is list and len(blocks)==3 and
             all(type(block) is list and len(block)==2 and
                 all(type(i) is int for i in block) and block[1]-block[0]==15
                 for block in blocks),"PUBLIC_DEV_SEED_BLOCKS_DRIFT")
        seeds=[i for x,y in blocks for i in range(x,y+1)]
        need(len(seeds)==len(set(seeds))==48 and
             all(i not in (range(51100,51124) if wing else range(51400,51448)) for i in seeds) and
             min(seeds)>=63000 and max(seeds)<=63999,
             "PUBLIC_DEVELOPMENT_SEED_REUSE")
        budget=lane.get("budget")
        need(type(budget) is dict and
             budget=={"max_trainable_parameters":128,"max_update_steps":100,
                      "max_public_development_graph_pairs":144,"external_llm_calls":0},
             "UNFROZEN_COMPUTE_BUDGET")
        need(len(seeds)<=budget["max_public_development_graph_pairs"],"UNBOUNDED_COHORT")
        metrics=lane.get("secondary_metrics")
        require_metrics=(["worst_depth_paired_accuracy","worst_public_generator_paired_accuracy",
                          "calibration_error","compute_per_pair"] if wing else
                         ["worst_role_family_paired_accuracy","variable_renaming_consistency",
                          "role_swap_false_positive_rate","compute_per_pair"])
        need(lane.get("primary_metric")=="paired_counterfactual_accuracy" and
             metrics==require_metrics,"EVALUATION_METRIC_DRIFT")
        rule=lane.get("preliminary_development_screen")
        need(rule=={"minimum_paired_accuracy":0.75,
                    "minimum_improvement_vs_size_matched_blind":0.15,
                    "minimum_worst_group_paired_accuracy":0.60},
             "POST_HOC_SUCCESS_THRESHOLD_DRIFT")
        need(type(lane.get("group_strata")) is list and len(lane["group_strata"])==3 and
             type(lane.get("failure_conditions")) is list and
             len(lane["failure_conditions"])>=6 and
             "unfrozen_after_result_tuning" in lane["failure_conditions"],
             "FAILURE_OR_STRATA_UNFROZEN")
        records.append({
            "lane":name,"historical_source_experiment":old["experiment"],
            "authentic_negative_pairs":old["pair_count"],
            "retrospective_learned_correct_pairs":0,
            "retrospective_coded_control_pairs":old["pair_count"],
            "candidate_ids":sorted(seen),
            "novel_mechanism_families_proposed":2,
            "public_development_seed_count":len(seeds),
            "protected_originals_allocated":0,
            "implementation_started":False,
            "science_first_use_authorized":False})
    need(len(all_ids)==4,"FOUR_CANDIDATE_POPULATION_MISSING")
    return records
def audit(parent_path=F99,contract_path=F100,source_sha=""):
    need(type(source_sha) is str and HEX40.fullmatch(source_sha) is not None and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source_sha),
         "FORGE_SOURCE_REF_INVALID")
    f99,raw=read_json(parent_path)
    f100,contract_raw=read_json(contract_path)
    records=check_contract(f100,f99,raw)
    return {
        "schema":REPORT,"forge_source_sha":source_sha,
        "f99_parent_git_blob_sha":git_blob_sha(raw),
        "f100_frozen_contract_sha256":hashlib.sha256(contract_raw).hexdigest(),
        "status":"PREREGISTRATION_ONLY_NOT_MODEL_EXECUTION",
        "candidates_frozen":sum(len(z["candidate_ids"]) for z in records),
        "historical_development_negative_pairs":sum(z["authentic_negative_pairs"] for z in records),
        "lanes":records,"new_experiments_executed":0,"new_results_observed":0,
        "trainable_policy_updates":0,"model_calls":0,"codex_calls":0,
        "paid_external_model_calls":0,"scientific_first_use_authorized":False,
        "autonomous_research_established":False,"accepted_ref_mutations":0}
def main(argv):
    p=argparse.ArgumentParser()
    p.add_argument("--source-ref",required=True)
    args=p.parse_args(argv)
    result=audit(source_sha=args.source_ref)
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
if __name__=="__main__":
    try:main(sys.argv[1:])
    except (Rejected,KeyError,TypeError,OSError) as exc:
        print("FORGE_F100_FROZEN_PREREG=QUARANTINED "+str(exc),file=sys.stderr)
        raise SystemExit(1)
