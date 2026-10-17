"""F129-R immutable packed-token join preimplementation admission.

Source-only: never generate FIT, TRAIN_CHECK, protected confirmation,
train a mechanism, dispatch originals or claim independent science.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "reference/research-intake/f129r-packed-token-join-freeze.json"
PARENT_FREEZE = ROOT / "reference/research-intake/f128r-early-rejection-order-freeze.json"
FREEZE_BLOB = "b02106693ea400d705d5b75feede949b39b2ed7a"
PARENT_BLOB = "fb769675deb29235f96cefad50a87ab208d97950"
PARENT_SHA = "7eb97bc83cd739bccc4081b48b367ffb9970f7bc"
SCHEMA = "forge.research.f129r.packed-word-relational-join-prereg.v1"

class Invalid(ValueError):
    pass

def need(ok, label):
    if not ok:
        raise Invalid("F129R_FREEZE_" + label)

def git_blob(data):
    data = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def validate(d):
    need(type(d) is dict and d.get("schema") == SCHEMA and
         d.get("stage") == "PREIMPLEMENTATION_SOURCE_ONLY_NO_EXPERIMENT",
         "IDENTITY")
    i = d["identity"]
    need(i["parent_pr"] == 457 and i["parent_exact_qualified_sha"] == PARENT_SHA and
         i["parent_qualification_run"] == 39066228233 and
         i["parent_freeze_git_blob"] == PARENT_BLOB and
         i["parent_status"] == "ENGINEERING_PASS_SCIENTIFIC_DEVELOPMENT_NEGATIVE" and
         i["parent_source_unmodified"] is True and
         "NOT F129 autonomy" in i["research_lane"], "PARENT")
    n = d["negative_retention"]
    need(n["F128R_Wingless_train_check_paired"] == [32,32] and
         n["F128R_Yggdrasil_train_check_paired"] == [32,32] and
         n["F128R_Wingless_bit_access_ratio"] == .53077508 and
         n["F128R_Yggdrasil_bit_access_ratio"] == .52655291 and
         n["F128R_Ubuntu_Wingless_walltime_ratio"] == 1.044001 and
         n["F128R_Ubuntu_Yggdrasil_walltime_ratio"] == 1.046555 and
         n["F128R_Windows_Wingless_walltime_ratio"] == 1.048165 and
         n["F128R_Windows_Yggdrasil_walltime_ratio"] == 1.044362 and
         n["F128R_walltime_success"] is False and
         n["F127R_Wingless_paired"] == [18,32] and
         n["F127R_Yggdrasil_paired"] == [15,32] and
         n["F127R_Wingless_indexed_exact_relative_cost"] == 9.288 and
         n["F127R_Yggdrasil_indexed_exact_relative_cost"] == 9.197 and
         n["F126R_Wingless_paired"] == [6,64] and
         n["F126R_Yggdrasil_paired"] == [18,64] and
         n["F125R_Wingless_paired"] == [0,64] and
         n["F125R_Yggdrasil_paired"] == [0,64] and
         n["all_original_negatives_retained"] is True,"NEGATIVE_RETENTION")
    h = d["hypothesis"]
    need(h["one_candidate"] == "PACKED_TOKEN_HASH_JOIN_NO_LEARNING_NO_SELECTION" and
         h["mechanism"].startswith("Encode each public sixteen-bit edge") and
         "hash join" in h["mechanism"] and
         "enumerate all edges indexed solely" in h["initial_step"] and
         "little-endian" in h["representation"] and
         "No fitted parameters" in h["learning"] and
         h["comparison_controls"] == [
             "CTRL_NATIVE_INDEXED_16_ELEMENT_VECTOR_EQUALITY",
             "CTRL_PACKED_INTEGER_INDEXED_EQUALITY_WITHOUT_JOIN",
             "CTRL_NATIVE_BYTES_INDEXED_EQUALITY",
             "F129R_PACKED_TOKEN_HASH_JOIN_NO_LEARNING_NO_SELECTION"
         ] and
         h["required_input"] == [
             "start","target","roles","edges.from","edges.to","edges.role",
             "edges.src_bits","edges.dst_bits"
         ] and h["edge_and_query_order_invariant"] is True and
         h["pack_and_index_cost_included"] is True and
         h["whole_public_graph_inference_only"] is True and
         h["limits"] == {
             "token_bits":16, "maximum_active_states":256,
             "maximum_candidate_expansions":512, "maximum_public_paths":16,
             "maximum_edges":128, "fail_closed_on_overbudget":True
         },"MECHANISM")
    s = d["source"]
    need(s["family"] == "F129R-INDEPENDENT-PUBLIC-PACKED-JOIN-V1" and
         s["graph_local_namespace"] ==
             "F129R/PUBLIC/NEW-GRAPH-TOKENS/20261017" and
         s["source_vectors_per_lane"] == 2 and
         s["source_candidate_indices"] == [2,3] and
         s["fit_pairs_per_vector"] == 16 and
         s["check_pairs_per_vector"] == 16 and
         s["graph_depths_fit_check"] == [3,5] and
         s["reserved_confirmation_depths"] == [6,8] and
         s["public_competing_paths_fit_check"] == [6,12] and
         s["reserved_confirmation_paths"] == [8,16] and
         s["frozen_full_denominator_paired_cases_per_lane"] == 32 and
         s["fit_and_train_check_seed_disjoint"] is True and
         s["confirm_seeds_not_generatable_by_development_tool"] is True and
         s["immutable_source_candidates_after_generation"] is True and
         s["protected_confirmation_generated"] is False,
         "SOURCE_FAMILY")
    cohorts = {
        "Wingless":{"FIT":[240100,240115],"TRAIN_CHECK":[240116,240131],
                    "CONFIRM":[240200,240263]},
        "Yggdrasil":{"FIT":[250100,250115],"TRAIN_CHECK":[250116,250131],
                     "CONFIRM":[250200,250263]}
    }
    need(s["lanes"] == cohorts,"SOURCE_SPLITS")
    seen = set()
    for lane in ("Wingless","Yggdrasil"):
        for stage,count in (("FIT",16),("TRAIN_CHECK",16),("CONFIRM",64)):
            lo,hi = cohorts[lane][stage]
            group = set(range(lo,hi+1))
            need(len(group) == count and not (group & seen),"SEED_COLLISION")
            seen |= group
    q = d["qualification"]
    need(q["warmup_full_passes"] == 5 and
         q["measured_alternating_full_passes"] == 30 and
         q["maximum_median_walltime_ratio_to_native_indexed"] == .75 and
         q["maximum_peak_allocated_memory_ratio_to_native_indexed"] == 1.25 and
         q["controls_all_eligible"] is True and
         q["no_retuning_from_check"] is True and
         q["no_win_if_only_slow_comparator_beaten"] is True and
         q["no_scientific_acceptance_from_development"] is True and
         q["source_and_baseline_same_public_information"] is True and
         q["mandatory_fast_baseline"].startswith("Use real indexed adjacency") and
         "include bit packing and index build" in q["benchmark"] and
         "tracemalloc" in q["memory_measurement"] and
         set(q["operation_accounting"]) == {
             "edges_indexed","edge_visits","hash_lookup_attempts",
             "bit_pack_operations","token_compares","state_allocations",
             "peak_states","public_graph_input_conversion"
         },"HONEST_BENCHMARK")
    g = d["current_gate"]
    need(g["description"].startswith("Preregister F129-R mechanism") and
         g["generated_public_fit_cases"] == 0 and
         g["generated_public_train_check_cases"] == 0 and
         g["generated_protected_confirm_cases"] == 0 and
         g["implementation_created"] is False and
         g["scientific_originals_executed"] == 0 and
         g["protected_confirmation_read"] is False and
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
         g["wingless_repo_writes"] == 0 and
         g["yggdrasil_repo_writes"] == 0,"NO_UNEARNED_AUTHORITY")
    return d

def frozen():
    data = FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(git_blob(data) == FREEZE_BLOB,"IMMUTABLE_BLOB")
    need(git_blob(PARENT_FREEZE.read_bytes()) == PARENT_BLOB,
         "PARENT_BLOB")
    return validate(json.loads(data)),hashlib.sha256(data).hexdigest()

def admission(source_sha):
    need(type(source_sha) is str and re.fullmatch("[a-f0-9]{40}",source_sha),
         "SOURCE_SHA")
    _, digest = frozen()
    return {"schema":"forge.research.f129r.source-only-custody.v1",
            "source_sha":source_sha,"freeze_git_blob":FREEZE_BLOB,
            "freeze_sha256":digest,"qualified_parent_sha":PARENT_SHA,
            "qualified_parent_freeze_blob":PARENT_BLOB,
            "public_fit_cases_generated":0,
            "train_check_cases_generated":0,
            "protected_confirmation_cases_generated":0,
            "packed_join_implemented":False,
            "scientific_originals_executed":0,
            "scientific_first_use":False,
            "scientific_acceptance":False,
            "optimizer_promotion":False,
            "accepted_ref_mutations":0,
            "codex_calls":0,"paid_model_calls":0,
            "new_scheduler":False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",required=True)
    args = p.parse_args()
    r = admission(args.source_sha)
    path = Path(args.output)
    need(path.parent.is_dir() and not path.exists(),"RECEIPT_OVERWRITE")
    path.open("xb").write(
        (json.dumps(r,sort_keys=True,separators=(",",":"))+"\n").encode())
    print("F129R_FROZEN_PREIMPLEMENTATION=PASS")
    print("F129R_CONFIRM_UNOPENED=true")

if __name__=="__main__":
    try:
        main()
    except (Invalid,OSError,TypeError,KeyError,ValueError) as exc:
        print("F129R_FAIL_CLOSED="+str(exc),file=sys.stderr)
        raise SystemExit(1)
