"""F128-R immutable scientific preregistration admission; source only.

No new public FIT / TRAIN_CHECK, no protected CONFIRM, no model fitting,
scientific originals, accepted-ref mutations or optimizer promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "reference/research-intake/f128r-early-rejection-order-freeze.json"
PARENT_FREEZE = ROOT / "reference/research-intake/f127r-absolute-binding-calibration-freeze.json"
SOURCE_BLOB = "fb769675deb29235f96cefad50a87ab208d97950"
PARENT_BLOB = "0fde790b95384aaf19e9725ea5a82e7819407c3d"
PARENT_SHA = "0937af979095bfd680f517b2a3fd304455f2138c"
SCHEMA = "forge.research.f128r.learned-bit-order-early-reject-prereg.v1"

class Invalid(ValueError):
    pass

def need(ok: bool, code: str) -> None:
    if not ok:
        raise Invalid("F128R_SOURCE_" + code)

def git_blob(raw: bytes) -> str:
    raw = raw.replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def validate(c: dict) -> dict:
    need(type(c) is dict and c.get("schema") == SCHEMA and
         c.get("stage") == "SOURCE_ONLY_FROZEN_BEFORE_NEW_MODEL_OR_COHORT",
         "SCHEMA_OR_STAGE")
    i = c["identity"]
    need(i["parent_f127r_commit"] == PARENT_SHA and i["parent_pr"] == 455 and
         i["parent_exact_head_ci_run"] == 39065115084 and
         i["parent_freeze_git_blob"] == PARENT_BLOB and
         i["parent_status"] == "ENGINEERING_PASS_SCIENTIFIC_DEVELOPMENT_NEGATIVE" and
         i["parent_source_unmodified"] is True and
         "F128-R" in i["this_lane"], "PARENT_LINEAGE")
    n = c["negative_retention"]
    need(n["F127R_Wingless_TRAIN_CHECK_paired"] == [18, 32] and
         n["F127R_Yggdrasil_TRAIN_CHECK_paired"] == [15, 32] and
         n["F127R_Wingless_TRAIN_CHECK_rank"] == [32, 32] and
         n["F127R_Yggdrasil_TRAIN_CHECK_rank"] == [32, 32] and
         n["F127R_eligible_exact_paired_both_lanes"] == [32, 32] and
         n["F127R_Wingless_saved_cost_ratio_to_indexed_exact"] == 9.288 and
         n["F127R_Yggdrasil_saved_cost_ratio_to_indexed_exact"] == 9.197 and
         n["F127R_cost_superiority"] is False and
         n["F126R_paired_Wingless"] == [6, 64] and
         n["F126R_paired_Yggdrasil"] == [18, 64] and
         n["F125R_paired_Wingless"] == [0, 64] and
         n["F125R_paired_Yggdrasil"] == [0, 64] and
         n["all_original_negative_evidence_retained"] is True,
         "NEGATIVE_RECORD_REWRITTEN")
    h = c["hypothesis"]
    need(h["trainable_statistics"] == 16 and
         h["frozen_initializer"] ==
             "Stable bit order 0..15; learned sort by decreasing mismatches with original index tie break." and
         "label-blind mismatch histogram" in h["training"] and
         "No gradient, labels, oracle edges" in h["training"] and
         "check raw source/destination bits in learned order" in h["frozen_inference"] and
         "accept only after all 16 agree" in h["frozen_inference"] and
         h["boundaries"] == {
             "bit_length": 16, "training_passes": 1,
             "maximum_active_states": 256,
             "maximum_candidate_expansions": 512,
             "maximum_public_paths": 16,
             "model_parameter_storage": 16, "fail_closed_on_excess": True
         } and
         h["no_calibration_or_threshold"] is True and
         h["no_original_weights_reused"] is True and
         h["oracle_path_never_model_input"] is True,
         "UNFROZEN_MECHANISM")
    src = c["source"]
    need(src["family"] == "F128R-INDEPENDENT-PUBLIC-TOKEN-VERIFIER-V1" and
         src["salt_namespace"] == "F128R/PUBLIC/NEW-GRAPH-SALT/20261017" and
         src["candidate_indices"] == [2, 3] and
         src["authenticated_proposals_per_lane"] == 2 and
         src["fit_pairs_per_vector"] == 16 and
         src["train_check_pairs_per_vector"] == 16 and
         src["protected_confirmation_seeds_per_lane"] == 64 and
         src["public_raw_bit_length"] == 16 and
         src["fit_depths"] == [3, 5] and
         src["train_check_depths"] == [3, 5] and
         src["protected_confirm_depths"] == [6, 8] and
         src["fit_public_paths"] == [6, 12] and
         src["train_check_public_paths"] == [6, 12] and
         src["protected_confirm_public_paths"] == [8, 16] and
         src["training_labels_unavailable_to_policy"] is True and
         src["train_check_and_protected_CONFIRM_unopened_during_fit"] is True and
         src["protected_CONFIRM_generated"] is False and
         src["no_seed_reselection_after_scoring"] is True,
         "FROZEN_FAMILY")
    cohorts = {
        "Wingless": {
            "FIT": [220100, 220115],
            "TRAIN_CHECK": [220116, 220131],
            "CONFIRM": [220200, 220263]
        },
        "Yggdrasil": {
            "FIT": [230100, 230115],
            "TRAIN_CHECK": [230116, 230131],
            "CONFIRM": [230200, 230263]
        }
    }
    need(src["lanes"] == cohorts, "FROZEN_SPLITS")
    seen = set()
    for lane in ("Wingless", "Yggdrasil"):
        for stage, n_seeds in (("FIT", 16), ("TRAIN_CHECK", 16), ("CONFIRM", 64)):
            a, b = cohorts[lane][stage]
            group = set(range(a, b + 1))
            need(len(group) == n_seeds and not (group & seen),
                 "SEED_OVERLAP")
            seen |= group
    baseline = c["controls"]
    need("Already-indexed optimized" in baseline["mandatory_eligible_exact"] and
         "not compare only with an intentionally slow full-scan" in
             baseline["mandatory_eligible_exact"] and
         set(baseline["frozen_controls"]) == {
             "CTRL_OPTIMIZED_INDEXED_EXACT_VECTOR_EQUALITY",
             "CTRL_FIXED_NATURAL_0_TO_15",
             "CTRL_FIXED_REVERSE_15_TO_0",
             "CTRL_LABEL_BLIND_UNIFORM_BIT_ORDER",
             "F128R_FIT_ONLY_LEARNED_EARLY_REJECT"
         } and
         "Every TRAIN_CHECK graph" in baseline["accuracy"] and
         "Exact reference remains eligible" in baseline["accuracy"],
         "ELIGIBLE_INDEXED_EXACT")
    cost = baseline["cost"]
    need(cost["warmup_complete_passes"] == 5 and
         cost["measured_interleaved_complete_passes"] == 30 and
         cost["alternating_order"] is True and
         cost["same_python_version_and_runner"] is True and
         cost["cross_algorithm_common_event_definition_frozen_before_first_fit"] is True and
         cost["maximum_bit_comparison_ratio_to_full_16_reference"] == .75 and
         cost["maximum_median_walltime_ratio_to_optimized_exact"] == .75 and
         cost["both_metrics_required_in_both_lanes"] is True and
         cost["native_vector_comparison_is_eligible_even_if_it_outperforms_learned"] is True and
         baseline["no_false_success_from_beating_slow_baseline"] is True and
         baseline["no_train_check_based_algorithm_retuning"] is True and
         baseline["protected_confirmation_requires_separate_first_use"] is True,
         "COST_OR_AUTHORITY")
    expected_classes = {
        "index_builds", "edge_visits", "candidate_expansions", "bit_accesses",
        "bit_mismatch_checks", "state_allocations", "peak_states",
        "raw_input_conversion", "sort_comparisons"
    }
    need(set(cost["cost_events"]) == expected_classes,
         "OPERATION_TARIFF")
    g = c["scope"]
    need("Preimplementation" in g["current"] and
         g["freeze_unmodified_after_model_design"] is True and
         g["scientific_originals_executed"] == 0 and
         g["protected_CONFIRM_read"] is False and
         g["scientific_first_use"] is False and
         g["scientific_acceptance"] is False and
         g["optimizer_promotion"] is False and
         g["accepted_ref_mutations"] == 0 and
         g["merge"] is False and
         g["codex_calls"] == 0 and
         g["paid_inference_calls"] == 0 and
         g["new_scheduler"] is False and
         g["ckb_plane_dependency"] is False and
         g["cloudflare_writes"] == 0 and
         g["mind_palace_writes"] == 0 and
         g["wingless_repository_writes"] == 0 and
         g["yggdrasil_repository_writes"] == 0,
         "UNAUTHORIZED_SCIENCE")
    return c

def frozen() -> tuple[dict, str]:
    raw = FREEZE.read_bytes().replace(b"\r\n", b"\n")
    need(git_blob(raw) == SOURCE_BLOB, "IMMUTABLE_FREEZE_BLOB")
    need(git_blob(PARENT_FREEZE.read_bytes()) == PARENT_BLOB,
         "ORIGINAL_PARENT_FREEZE_BLOB")
    document = json.loads(raw)
    return validate(document), hashlib.sha256(raw).hexdigest()

def source_receipt(source_sha: str) -> dict:
    need(type(source_sha) is str and
         re.fullmatch(r"[0-9a-f]{40}", source_sha) is not None,
         "EXACT_COMMIT_SHA")
    _, digest = frozen()
    return {
        "schema": "forge.research.f128r.source-only-admission.v1",
        "source_sha": source_sha,
        "freeze_git_blob": SOURCE_BLOB,
        "freeze_sha256": digest,
        "qualified_parent_sha": PARENT_SHA,
        "parent_freeze_git_blob": PARENT_BLOB,
        "fit_cases_generated": 0, "train_check_cases_generated": 0,
        "protected_confirm_generated": 0, "learned_bit_order_fitted": False,
        "scientific_originals_executed": 0,
        "scientific_first_use": False, "scientific_acceptance": False,
        "optimizer_promotion": False, "accepted_ref_mutations": 0,
        "codex_calls": 0, "paid_model_calls": 0,
        "new_scheduler": False
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    receipt = source_receipt(args.source_sha)
    dest = Path(args.output)
    need(dest.parent.is_dir() and not dest.exists(), "RECEIPT_OVERWRITE")
    dest.open("xb").write((json.dumps(receipt, sort_keys=True,
                           separators=(",", ":")) + "\n").encode())
    print("F128R_FROZEN_PREIMPLEMENTATION=PASS")
    print("F128R_PROTECTED_CONFIRM_UNTOUCHED=true")

if __name__ == "__main__":
    try:
        main()
    except (Invalid, ValueError, KeyError, TypeError, OSError) as exc:
        print("F128R_FREEZE_FAIL_CLOSED=" + str(exc), file=sys.stderr)
        raise SystemExit(1)
