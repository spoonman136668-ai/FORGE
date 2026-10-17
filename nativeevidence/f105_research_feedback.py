"""F105: source-bound deterministic feedback into NON-EXECUTING research direction advice.

Consumes four actual F101-F104 generated public-development reports plus their
SHA-256 receipts from the *current* existing integrated GitHub Actions run.
No hardcoded evaluation outcomes, hidden model inference, scientific dispatch,
external API, optimizer promotion, or authority mutation.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f105-evidence-feedback-selection-freeze.json"
SCHEMA="forge.autonomy.f105.authentic-public-dev-feedback-selection-freeze.v1"
REPORT="forge.autonomy.f105.frozen-real-public-dev-research-feedback.v1"
FROZEN_GIT_BLOB="9a835dc724efa6bca365d838a293a10e7a8f47c1"
PARENT="7b774d705a11395fe2e804f192f0597e7df2e5b2"
SHA_RE=re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
EXPECT={
    "F101":{"lane":"Wingless","candidate":"W100-C1","trainable":4,"trainable_field":"trainable_parameter_count",
            "pairs":"development_pair_count","training":"training_pair_count",
            "assess":"public_dev_assessment_pairs","updates":"training_updates",
            "blind_updates":"control_training_updates",
            "negative":"previous_W_F10_negative_preserved",
            "booleans":["independently_accepted_scientific_gain","protected_first_use_authorized",
                        "fresh_scientific_original_executed","optimizer_promotion_authorized"],
            "zero":["accepted_ref_mutations","codex_calls","external_model_api_calls","chatgpt_work_tasks"],
            "control_shortcut":"always_yes_shortcut","all_arms":("learned_depth_conditioned","size_matched_depth_blind","depth_permuted_ablation","always_yes_shortcut","coded_exact_depth_oracle")},
    "F102":{"lane":"Yggdrasil","candidate":"Y100-C1","trainable":18,"trainable_field":"trainable_parameters",
            "pairs":"total_public_development_pairs","training":"training_pairs",
            "assess":"public_development_assessment_pairs","updates":"learned_training_updates",
            "blind_updates":"blind_control_training_updates",
            "negative":"historical_Y_F9_zero_of_192_negative_preserved",
            "booleans":["first_use_authorized","optimizer_promotion_authorized","ckb_plane_accessed"],
            "zero":["scientific_originals_executed","independent_scientific_results_accepted",
                    "accepted_ref_mutations","codex_invocations","external_model_api_calls",
                    "chatgpt_work_tasks"],"control_shortcut":"always_yes_shortcut","all_arms":("learned_typed_role_composer","size_matched_role_blind","query_role_permuted_ablation","always_yes_shortcut","coded_typed_role_oracle")},
    "F103":{"lane":"Yggdrasil","candidate":"Y100-C2","trainable":20,"trainable_field":"trainable_parameters",
            "pairs":"total_development_pairs","training":"training_pairs",
            "assess":"assessment_pairs","updates":"learned_training_updates",
            "blind_updates":"variable_blind_training_updates",
            "negative":"historical_Y_F9_negative_0_of_192_preserved",
            "booleans":["first_use_authorized","optimizer_promotion_authorized","ckb_plane_accessed"],
            "zero":["scientific_originals_executed","independent_scientific_results_accepted",
                    "accepted_ref_mutations","codex_invocations","paid_api_calls",
                    "chatgpt_work_tasks"],"control_shortcut":"always_yes_shortcut","all_arms":("learned_variable_slot_binder","size_matched_role_aware_variable_blind","independent_slot_disruption_ablation","always_yes_shortcut","coded_exact_binding_oracle")},
    "F104":{"lane":"Wingless","candidate":"W100-C2","trainable":18,"trainable_field":"trainable_parameters",
            "pairs":"total_development_pairs","training":"training_pairs",
            "assess":"public_assessment_pairs","updates":"learned_training_updates",
            "blind_updates":"blind_control_training_updates",
            "negative":"historical_W_F10_negative_0_of_96_preserved",
            "booleans":["protected_first_use_authorized","optimizer_promotion_authorized",
                        "ckb_plane_accessed"],
            "zero":["scientific_originals_executed","independently_accepted_science",
                    "accepted_ref_mutations","codex_calls","paid_model_api_calls",
                    "chatgpt_work_tasks"],"control_shortcut":"always_yes_shortcut","all_arms":("learned_query_gated_selector","size_matched_query_blind_selector","query_permuted_ablation","fixed_first_observation_shortcut","always_yes_shortcut","coded_requested_depth_oracle")}
}
class Quarantined(ValueError):pass
def require(condition,reason):
    if not condition:raise Quarantined("F105_"+reason)
def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def read_bounded(path,limit=120000):
    raw=path.read_bytes()
    require(0<len(raw)<=limit,"EMPTY_OR_OVERSIZED_SOURCE")
    return raw
def json_distinct(raw):
    def reject_duplicates(pairs):
        obj={}
        for key,value in pairs:
            require(key not in obj,"DUPLICATE_JSON_KEY")
            obj[key]=value
        return obj
    return json.loads(raw.decode("utf-8-sig"),object_pairs_hook=reject_duplicates)

def freeze():
    raw=read_bounded(FREEZE)
    require(blob(raw)==FROZEN_GIT_BLOB,"FROZEN_POLICY_HASH_DRIFT")
    cfg=json_distinct(raw)
    require(cfg.get("schema")==SCHEMA and
            cfg.get("parent_f104_exact_head_sha")==PARENT and
            cfg.get("purpose")=="AUTOMATIC_RESEARCH_DIRECTION_ADVISORY_FROM_AUTHENTIC_BOUNDED_PUBLIC_DEVELOPMENT_RESULTS",
            "POLICY_PARENT_OR_PURPOSE_DRIFT")
    src=cfg.get("source_evidence",{})
    require(set(src)==set(EXPECT) and
            set(z["candidate_id"] if "candidate_id" in z else z["id"] for z in src.values())
              =={x["candidate"] for x in EXPECT.values()},
            "INCOMPLETE_FOUR_MODEL_PROVENANCE")
    for key,entry in src.items():
        require(entry["id"]==EXPECT[key]["candidate"] and
                entry["lane"]==EXPECT[key]["lane"] and
                entry["report_path"].startswith("forge-"+key.lower()+"-development/") and
                entry["sha_path"].startswith("forge-"+key.lower()+"-development/") and
                DIGEST_RE.fullmatch(entry["source_git_blob"].lower()) is None and
                SHA_RE.fullmatch(entry["source_git_blob"]) is not None,
                "FROZEN_RESEARCH_SOURCE_IDENTITY_DRIFT")
        codefile=ROOT/"nativeevidence"/{
            "F101":"f101_wingless_public_depth.py",
            "F102":"f102_yggdrasil_public_roles.py",
            "F103":"f103_yggdrasil_public_binding.py",
            "F104":"f104_wingless_public_observations.py"}[key]
        require(blob(read_bounded(codefile,300000))==entry["source_git_blob"],
                "PARENT_MODEL_CODE_DRIFT_"+key)
    policy=cfg.get("decision_policy",{})
    require(policy.get("policy_id")=="F105-D0-FROZEN-PAIRWISE-RISK-FIRST" and
            policy.get("one_advisory_successor_per_lane") is True and
            policy.get("all_four_complete_frozen_evidence_mandatory") is True and
            set(policy.get("new_hypotheses",{}))==
               {x["candidate"] for x in EXPECT.values()} and
            policy.get("selected_output_type")==
               "NONEXECUTING_FROZEN_DEVELOPMENT_SUCCESSOR_DESIGN_ADVISORY",
            "POLICY_SCOPE_DRIFT")
    guards=cfg.get("constraints",{})
    require(guards.get("maximum_new_experiments")==0 and
            guards.get("maximum_external_model_calls")==0 and
            guards.get("source_sha_must_match_single_current_GITHUB_SHA") is True and
            guards.get("all_results_must_be_evidence_derived_not_literal") is True and
            all(guards.get(k) is True for k in (
                "no_codex","no_paid_model_api","no_ckb_plane_contact",
                "no_mind_palace_write","no_other_repo_mutation",
                "no_new_scheduler_or_controller","no_independent_scientific_acceptance",
                "no_scientific_first_use","no_auto_dispatch","no_accepted_ref_mutations")),
            "UNAUTHORIZED_FEEDBACK_ACTION")
    return cfg,hashlib.sha256(raw).hexdigest()

def fraction(value,name):
    require(type(value) in (float,int) and
            math.isfinite(value) and 0.0<=value<=1.0,"BAD_SCORE_"+name)
    require(abs(round(value*48)-value*48)<1e-6,"NOT_48_PAIR_SCORE_"+name)
    return float(value)

def read_evidence(source_sha,evidence_root,cfg):
    reports={}
    for key in ("F101","F102","F103","F104"):
        meta=cfg["source_evidence"][key]
        relative=Path(meta["report_path"])
        checksum=Path(meta["sha_path"])
        require(not relative.is_absolute() and ".." not in relative.parts and
                not checksum.is_absolute() and ".." not in checksum.parts and
                relative.parent==checksum.parent,"PATH_ESCAPES_RUN_DIR")
        raw=read_bounded(evidence_root/relative)
        checksum_raw=read_bounded(evidence_root/checksum,4096)
        expected_sha=hashlib.sha256(raw).hexdigest()
        receipt=checksum_raw.decode("utf-8-sig").strip().splitlines()
        require(len(receipt)==1 and
                re.fullmatch(r"[0-9a-f]{64}  [A-Za-z0-9_.-]+",receipt[0]) is not None,
                "MALFORMED_SOURCE_RECEIPT_"+key)
        receipt_digest,receipt_name=receipt[0].split("  ",1)
        require(receipt_digest==expected_sha and receipt_name==relative.name,
                "REPORT_CONTENT_HASH_MISMATCH_"+key)
        data=json_distinct(raw)
        require(type(data) is dict and data.get("schema")==meta["schema"] and
                data.get("source_sha")==source_sha and
                data.get("lane")==meta["lane"] and
                data.get("candidate_id")==meta["id"],
                "FOREIGN_REPORT_OR_REPLAY_"+key)
        requirements=EXPECT[key]
        require(all(type(data.get(z)) is int and data[z]==n for z,n in (
                  (requirements["pairs"],144),(requirements["training"],96),
                  (requirements["assess"],48),(requirements["trainable_field"],requirements["trainable"]),
                  (requirements["updates"],100),(requirements["blind_updates"],100))),
                "TRAINING_AND_COHORT_BUDGET_DRIFT_"+key)
        require(data.get(requirements["negative"]) is True and
                all(data.get(z) is False for z in requirements["booleans"]) and
                all(type(data.get(z)) is int and data[z]==0 for z in requirements["zero"]),
                "UNAUTHORIZED_SCIENCE_OR_RELABELED_NEGATIVE_"+key)
        if key=="F104":
            require(data.get("observation_budget_per_prediction")==1,
                    "OBSERVATION_BUDGET_ESCALATION")
        if key in ("F102","F103","F104"):
            require(data.get({"F102":"coded_oracle_only_control",
                              "F103":"oracle_only_separate_control",
                              "F104":"coded_oracle_separate_control_only"}[key]) is True,
                    "ORACLE_NOT_INDEPENDENT_"+key)
        require(data.get("source_sha")==source_sha and data.get("candidate_id")==meta["id"],
                "EVIDENCE_SUBSTITUTION_"+key)
        scores=data.get(meta["score_key"])
        require(type(scores) is dict and
                set(scores)==set(requirements["all_arms"]),
                "FULL_POPULATION_MISSING_"+key)
        for name,value in scores.items():fraction(value,name)
        require(scores[meta["oracle"]]==1.0 and
                scores[requirements["control_shortcut"]]==0.0,
                "ORACLE_OR_SHORTCUT_CONTAMINATION_"+key)
        primary=fraction(scores[meta["primary"]],key+"_primary")
        blind=fraction(scores[meta["blind"]],key+"_blind")
        worst=fraction(data.get(meta["worst_key"]),key+"_worst")
        require(worst<=primary and data.get(meta["screen_key"]) in (True,False) and
                type(data[meta["screen_key"]]) is bool,
                "INVALID_SCREEN_CLAIM_"+key)
        expected_pass=primary>=0.75 and primary-blind>=0.15-1e-9 and worst>=0.60
        if key=="F104":
            val=data.get("query_dependent_selection_fraction")
            require(type(val) in (int,float) and math.isfinite(val) and 0<=val<=1,
                    "INVALID_QUERY_SELECTION")
            expected_pass=expected_pass and val>=0.50
        if key=="F103":
            val=data.get("variable_renaming_agreement")
            require(type(val) in (int,float) and math.isfinite(val) and 0<=val<=1,
                    "INVALID_VARIABLE_RENAMING")
            expected_pass=expected_pass and val>=0.95
        require(expected_pass==data[meta["screen_key"]],
                "SCREEN_RECOMPUTATION_CONTRADICTION_"+key)
        reports[key]=dict(
            key=key,lane=meta["lane"],candidate_id=meta["id"],
            paired_accuracy=primary,blind_accuracy=blind,
            worst_group_accuracy=worst,public_screen_passed=expected_pass,
            source_report_sha256=expected_sha,
            evidence_class=data.get("evidence_class",data.get("source_type")),
            historical_negative_preserved=True)
    return reports

def choose(reports,cfg):
    require(set(reports)==set(EXPECT),"UNVERIFIED_OR_INCOMPLETE_SELECTION")
    policy=cfg["decision_policy"]
    outcomes=[]
    for lane in ("Wingless","Yggdrasil"):
        pool=[reports[k] for k in ("F101","F102","F103","F104")
              if reports[k]["lane"]==lane]
        require(len(pool)==2 and len({p["candidate_id"] for p in pool})==2,
                "DUPLICATE_OR_MISSING_LANE_LINEAGE")
        failed=[p for p in pool if not p["public_screen_passed"]]
        if failed:
            # Weakest failed first; deterministic C2 tie priority, then stable id.
            selected=sorted(failed,key=lambda p:(
                p["paired_accuracy"],p["worst_group_accuracy"],
                -int(p["candidate_id"].endswith("C2")),p["candidate_id"]))[0]
            reason="FROZEN_PUBLIC_SCREEN_NEGATIVE_FALSIFY_OR_REPAIR"
            kind="fail"
        else:
            selected=sorted(pool,key=lambda p:(
                p["worst_group_accuracy"],
                -int(p["candidate_id"].endswith("C2")),p["candidate_id"]))[0]
            reason="PUBLIC_DEV_PASSED_PRIORITIZE_NOVEL_TRANSFER_FALSIFICATION"
            kind="pass"
        successor=policy["new_hypotheses"][selected["candidate_id"]][kind]
        outcomes.append(dict(lane=lane,parent_candidate_id=selected["candidate_id"],
            selected_successor_hypothesis=successor,selection_reason=reason,
            proposed_status="UNTESTED_DEVELOPMENT_DESIGN_NOT_DISPATCH_ELIGIBLE",
            evidence_report_sha256=selected["source_report_sha256"]))
    return outcomes

def evaluate(source_sha,evidence_root):
    require(type(source_sha) is str and SHA_RE.fullmatch(source_sha) and
            (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source_sha),
            "CURRENT_GITHUB_SOURCE_SHA_REQUIRED")
    cfg,digest=freeze()
    root=Path(evidence_root).resolve()
    require(root.is_dir(),"CURRENT_WORKFLOW_EVIDENCE_NOT_MOUNTED")
    reports=read_evidence(source_sha,root,cfg)
    advisory=choose(reports,cfg)
    return dict(
        schema=REPORT,forge_source_sha=source_sha,policy_id=cfg["decision_policy"]["policy_id"],
        frozen_policy_sha256=digest,
        input_observation_count=4,development_pairs_observed=576,
        input_evidence=[reports[k] for k in ("F101","F102","F103","F104")],
        selected_successors=advisory,
        disposition="AUTOMATIC_EVIDENCE_DRIVEN_ADVISORY_ONLY_NO_EXPERIMENT_OR_GPT_INFERENCE",
        read_only=True,automatic_frozen_policy_selection=True,
        original_experiment_dispatches=0,new_scientific_originals_executed=0,
        independent_science_accepted=0,protected_first_use_authorized=False,
        optimizer_promotion_authorized=False,accepted_ref_mutations=0,
        external_model_inference_calls=0,codex_calls=0,
        work_tasks=0,ckb_plane_accessed=False,new_scheduler_created=False)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-ref",required=True)
    parser.add_argument("--evidence-root",required=True)
    args=parser.parse_args()
    print(json.dumps(evaluate(args.source_ref,args.evidence_root),
                     sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try:main()
    except (Quarantined,OSError,ValueError,TypeError,KeyError) as e:
        print("FORGE_F105_DECISION_FEEDBACK=QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
