"""F127-R immutable source-only scientific preregistration admission.

No new TRAIN sources, model training, reserved CONFIRM, first-use, accepted
scientific evidence, optimizer promotion, or new remote inference/controller.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f127r-absolute-binding-calibration-freeze.json"
PARENT=ROOT/"reference/research-intake/f126r-binding-evidence-prereg-freeze.json"
FREEZE_BLOB="0fde790b95384aaf19e9725ea5a82e7819407c3d"
PARENT_BLOB="7d6cf0469db557c0fced95d25e6fe55b8e34c136"
PARENT_SHA="a5eee2ed8c284ddcd4a9242ee0885bc77d2185af"
SCHEMA="forge.research.f127r.calibrated-relational-evidence-prereg.v1"

class Quarantined(ValueError):
    pass
def require(test,code):
    if not test: raise Quarantined("F127R_SOURCE_"+code)
def git_blob(raw):
    raw=raw.replace(b"\r\n",b"\n")
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def validate(p):
    require(type(p) is dict and p.get("schema")==SCHEMA and
            p.get("status")=="FROZEN_BEFORE_IMPLEMENTATION_SOURCE_ONLY" and
            p.get("stage")=="SOURCE_ONLY_PREREGISTRATION_NOT_SCIENTIFIC_ORIGINAL",
            "SCHEMA_OR_STATE")
    lin=p["lineage"]
    require(lin.get("parent_pr")==452 and
            lin.get("parent_qualified_source_sha")==PARENT_SHA and
            lin.get("parent_exact_head_ci_run")==39056224420 and
            lin.get("parent_f126r_frozen_git_blob")==PARENT_BLOB and
            lin.get("untouched_parent_source") is True and
            lin.get("no_dependency_on_f127_program_synthesis") is True and
            lin.get("no_dependency_on_ckb_plane") is True and
            lin.get("parent_result")==
                "ENGINEERING_PASS_SCIENTIFIC_DEVELOPMENT_NEGATIVE",
            "QUALIFIED_PARENT_DRIFT")
    n=p["retained_negatives"]
    require(n.get("F126R_Wingless_train_paired")==[6,64] and
            n.get("F126R_Yggdrasil_train_paired")==[18,64] and
            n.get("F126R_Wingless_train_rank")==[51,64] and
            n.get("F126R_Yggdrasil_train_rank")==[52,64] and
            n.get("F126R_no_null_ablation_rank_Wingless")==[64,64] and
            n.get("F126R_no_null_ablation_rank_Yggdrasil")==[64,64] and
            n.get("F126R_no_null_ablation_paired_Wingless")==[0,64] and
            n.get("F126R_no_null_ablation_paired_Yggdrasil")==[0,64] and
            n.get("F126R_exact_eligible_baseline_paired")==[64,64] and
            n.get("F126R_cost_advantage_proven") is False and
            n.get("F126R_full_cohort_F124R_sparse2")==
                "BLOCKED_FROZEN_INTERFACE_DEPTH_5" and
            n.get("F125R_Wingless_train_paired")==[0,64] and
            n.get("F125R_Yggdrasil_train_paired")==[0,64] and
            n.get("all_negatives_retained") is True,
            "NEGATIVE_HISTORY_REWRITTEN")
    h=p["hypothesis"]
    require(h.get("parameters")==22 and
            h.get("parameter_layout")==[
                "16 signed raw-bit junction weights",
                "one local compatibility bias",
                "one normalized evidence gain",
                "one output logit gain",
                "one decision intercept",
                "one bounded depth-residual coefficient",
                "one bounded candidate-count residual coefficient"] and
            h.get("init")=="fixed [0.12]*16 + [0.05,1.0,3.0,0.5,0.0,0.0]" and
            h.get("training",{}).get("epochs")==100 and
            h["training"].get("learning_rate")==.22 and
            h["training"].get("gradient_clip")==1.0 and
            h["training"].get("output_threshold")==.5 and
            h["training"].get("pair_not_in_inference") is True and
            "0.5 balanced individual BCE" in h["training"]["objective"] and
            "0.01 squared nuisance" in h["training"]["objective"] and
            "FIT only" in h["training"]["calibration"] and
            "No post-result" not in h.get("new_mechanism",""), "MODEL_OR_OBJECTIVE")
    s=h["safety"]
    require(s.get("max_parameter_count")==22 and
            s.get("max_public_candidate_paths")==16 and
            s.get("max_graph_expansions")==512 and
            s.get("max_retained_states")==256 and
            all(s.get(key) is True for key in (
                "exclude_hidden_answer","exclude_oracle_selected_route",
                "exclude_f126r_fitted_weights",
                "exclude_pair_partner_at_inference",
                "no_approximate_label_feature","no_manual_true_path_pruning",
                "reject_overbudget_as_failed_case",
                "canonical_edge_ordering","graph_local_salt_new")),
            "CAPACITY_OR_LEAKAGE")
    require(h["single_graph_public_inputs"]==
        ["start","target","roles","edges.from","edges.to","edges.role",
         "edges.src_bits","edges.dst_bits"],"PUBLIC_OBSERVATION")
    c=p["source_cohorts"]
    require(c.get("source_family")==
            "F127R-ABSOLUTE-BINDING-CALIBRATION-TRAIN-V1" and
            c.get("source_candidates_per_lane")==2 and
            c.get("fit_pairs_per_candidate")==16 and
            c.get("train_check_pairs_per_candidate")==16 and
            c.get("confirm_pairs_per_candidate")==64 and
            c.get("fit_and_check_disjoint") is True and
            c.get("Wingless")=={
                "FIT":[180100,180115],"TRAIN_CHECK":[180116,180131],
                "CONFIRM":[180200,180263]} and
            c.get("Yggdrasil")=={
                "FIT":[190100,190115],"TRAIN_CHECK":[190116,190131],
                "CONFIRM":[190200,190263]} and
            "candidate indices 2 and 3" in c.get("candidate_vectors",""),
            "UNOPENED_SPLIT")
    seen=set()
    for lane in ("Wingless","Yggdrasil"):
        for stage,amount in (("FIT",16),("TRAIN_CHECK",16),("CONFIRM",64)):
            lo,hi=c[lane][stage]
            seeds=set(range(lo,hi+1))
            require(len(seeds)==amount and not(seeds & seen),
                    "COHORT_OVERLAP")
            seen.update(seeds)
    structure=c["structure"]
    require(structure.get("FIT_depths")==[3,5] and
            structure.get("TRAIN_CHECK_depths")==[3,5] and
            structure.get("CONFIRM_depths")==[6,8] and
            structure.get("FIT_public_paths")==[6,12] and
            structure.get("TRAIN_CHECK_public_paths")==[6,12] and
            structure.get("CONFIRM_public_paths")==[8,16] and
            structure.get("no_protected_graph_generated_before_first_use") is True,
            "SOURCE_FAMILY")
    e=p["frozen_comparison"]
    require(e.get("minimum_paired_correct_fraction_of_exact")==.9 and
            e.get("minimum_rank_correct_fraction")==.9 and
            e.get("minimum_positive_correct_fraction")==.9 and
            e.get("minimum_negative_correct_fraction")==.9 and
            e.get("no_subgroup_failure_suppression") is True and
            "Mandatory strongest same-information" in
               e.get("eligible_exact_symbolic","") and
            "never excluded" in e["eligible_exact_symbolic"] and
            e.get("ablation_scoring","").startswith("Diagnostic only") and
            "TRAIN_CHECK" in e.get("primary",""),
            "FROZEN_SUCCESS_CRITERION")
    require(set(e["fixed_controls"])=={
        "CTRL_EXACT_PUBLIC_SYMBOLIC_ELIGIBLE",
        "CTRL_F126R_ORIGINAL_ARCH_FRESH_FIT",
        "CTRL_F125R_PATH_PRESERVING_FRESH_FIT",
        "CTRL_F123_DENSE_B_FRESH_FIT",
        "CTRL_F124R_SPARSE2_FROZEN_INTERFACE_BLOCKED_AT_DEPTH5",
        "CTRL_FIXED_SOFT_12_OF_16","CTRL_ROLE_ONLY",
        "CTRL_QUERY_ONLY_FRESH_FIT",
        "CTRL_F127R_NO_DEPTH_AND_PATH_RESIDUAL_ABLATION",
        "CTRL_F127R_GRAPH_NULL_SUBTRACTION_ABLATION"
    }, "STRONG_COMPARATORS")
    cost=p["cost_verification"]
    require(cost.get("target_cost_ratio_to_exact")==.75 and
            cost.get("required_both_lanes") is True and
            cost.get("both_event_and_median_walltime_must_pass") is True and
            cost.get("no_credit_for_solver_not_optimized") is True and
            cost.get("no_equivalent_cost_from_heterogeneous_counters") is True and
            "30 measured interleaved" in cost["runtime"] and
            cost.get("if_exact_is_at_least_as_accurate_and_cheaper")=="FAIL_COST",
            "COST_HONESTY")
    g=p["current_gate"]
    require(g.get("scope","").startswith("Immutable preimplementation freeze")
            and g.get("protected_CONFIRM_used") is False and
            g.get("scientific_first_use") is False and
            g.get("scientific_acceptance") is False and
            g.get("optimizer_promotion") is False and
            g.get("accepted_ref_mutation") is False and
            g.get("merge") is False and
            g.get("scientific_originals_executed")==0 and
            g.get("codex_calls")==0 and
            g.get("paid_API_calls")==0 and
            g.get("new_scheduler") is False and
            g.get("ckb_plane_contact") is False and
            g.get("cloudflare_writes")==0 and
            g.get("mind_palace_writes")==0 and
            g.get("wingless_repo_writes")==0 and
            g.get("yggdrasil_repo_writes")==0,
            "AUTHORITY_ESCALATION")
    return p

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    require(git_blob(raw)==FREEZE_BLOB,"IMMUTABLE_SOURCE_DRIFT")
    require(git_blob(PARENT.read_bytes())==PARENT_BLOB,
            "F126R_IMMUTABLE_PARENT_DRIFT")
    obj=json.loads(raw)
    validate(obj)
    return obj,hashlib.sha256(raw).hexdigest()

def receipt(sha):
    require(type(sha) is str and re.fullmatch("[0-9a-f]{40}",sha),
            "SOURCE_COMMIT_INVALID")
    _,digest=frozen()
    return {
        "schema":"forge.research.f127r.source-only-custody.v1",
        "source_sha":sha,"f127r_freeze_blob":FREEZE_BLOB,
        "f127r_freeze_sha256":digest,
        "parent_sha":PARENT_SHA,"parent_freeze_blob":PARENT_BLOB,
        "public_fit_cases_generated":0,
        "train_check_cases_generated":0,
        "protected_confirm_cases_generated":0,
        "trained_weights_created":False,
        "scientific_first_use":False,
        "scientific_acceptance":False,
        "optimizer_promotion":False,
        "accepted_ref_mutations":0,
        "codex_or_paid_model_calls":0
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    doc=receipt(a.source_sha)
    dest=Path(a.output)
    require(dest.parent.is_dir() and not dest.exists(),"CUSTODY_OVERWRITE")
    dest.open("xb").write((json.dumps(doc,sort_keys=True,
        separators=(",",":"))+"\n").encode())
    print("F127R_FROZEN_PREIMPLEMENTATION=PASS")
    print("F127R_PROTECTED_CONFIRM_UNTOUCHED=true")

if __name__=="__main__":
    try:main()
    except (Quarantined,KeyError,TypeError,ValueError,OSError) as e:
        print("F127R_SOURCE_FAIL_CLOSED="+str(e),file=sys.stderr)
        raise SystemExit(1)
