"""F124-R immutable *preimplementation* scientific contract admission.

No F124-R graph constructor, learner, training, protected confirmation,
scientific dispatch, or optimizer promotion is imported or executed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FREEZE = ROOT / "reference/research-intake/f124r-sparse-causal-routing-freeze.json"
F123_FREEZE = ROOT / "reference/research-intake/f123-learned-multipath-routing-freeze.json"
EXPECTED_FREEZE_BLOB = "891c950e1d25eea90fbe5191abf8e9c1ab4eac7f"
F123_FREEZE_BLOB = "9663e453051642bd798f9647df9993c3470c8672"
F123_PARENT_SHA = "fc913d03f9cdeb7daa0b289dcdc50d4c465cd9f8"
SCHEMA = "forge.autonomy.f124r.sparse-causal-routing-preimplementation-freeze.v1"


class Invalid(ValueError):
    pass


def need(ok, marker):
    if not ok:
        raise Invalid("F124R_SOURCE_FREEZE_" + marker)


def blob(raw):
    raw = raw.replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()


def validate(cfg):
    need(type(cfg) is dict and cfg.get("schema") == SCHEMA and
         cfg.get("status") == "PREIMPLEMENTATION_SOURCE_ONLY_NO_SCIENCE" and
         cfg.get("gate") == "F124-R" and
         cfg.get("parent", {}).get("f123_exact_head") == F123_PARENT_SHA and
         cfg["parent"].get("f123_frozen_protocol_git_blob") == F123_FREEZE_BLOB and
         cfg["parent"].get("f123_reserved_CONFIRM_not_read") is True,
         "PARENT_IDENTITY")
    p = cfg["parent"]
    need(p.get("f123_training_ubuntu_report_sha256") ==
         "1700ba9740c39a0cbd7a98e5ad2f7e4564c69d36b2492b48ebd8ca466241109f"
         and p["f123_arm_b_train_weights_sha256"] == {
             "Wingless": "de0c41815d882690127c59c7378fd2eb83be30be01daa240d6bc61b0bcf087f5",
             "Yggdrasil": "a17f5dc19378590f6d96dd867437ad298c97ad53a3d5596cb76cb8e6fee94b1f"
         } and p["f123_train_outcome"]["Wingless"] == {
             "learned_paired": 48, "strongest_nonoracle_paired": 47,
             "train_pairs": 48, "meets_frozen_margin": False
         } and p["f123_train_outcome"]["Yggdrasil"] == {
             "learned_paired": 46, "strongest_nonoracle_paired": 43,
             "train_pairs": 48, "meets_frozen_margin": True
         }, "F123_TRAIN_NEGATIVE_MUST_STAY")
    arm = cfg["proposed_mechanism"]
    need(arm.get("name") == "Sparse-2 edge-state attention router"
         and arm.get("candidate_arms") == ["S2"]
         and arm.get("beam_width") == arm.get("per_hop_budget") == 2
         and arm.get("max_trainable_parameters") == 20
         and arm.get("optimizer_epochs") == 100
         and arm.get("learning_rate") == 0.22
         and arm.get("training_without_hindsight") is True
         and arm.get("no_previous_F123_train_as_F124_fit") is True
         and "precomputed" in arm.get("path_ties", ""),
         "LEARNER_SCOPE_DRIFT")
    env = cfg["environment"]
    need(env["family_id"] == "F124R-NEW-GRAPH-FAMILY-NO-F123-SEED-OR-SALT-REUSE"
         and env["train_hops"] == [3, 4] and env["confirm_hops"] == [5, 7]
         and env["train_path_count"] == [4, 6]
         and env["confirm_path_count"] == [5, 8]
         and env["public_graph_fields"] == ["start", "target", "roles", "edges"]
         and env["public_edge_fields"] ==
         ["from", "to", "role", "src_bits", "dst_bits"]
         and env["no_engineered_true_path_or_equality"] is True
         and env["reject_ambiguous_or_unsatisfiable"] is True,
         "GRAPH_LEAKAGE_OR_FAMILY")
    co = cfg["cohorts"]
    need(co.get("Wingless") == {"TRAIN": [98100, 98131],
                               "CONFIRM": [98200, 98263]}
         and co.get("Yggdrasil") == {"TRAIN": [99100, 99131],
                                    "CONFIRM": [99200, 99263]}
         and co.get("two_candidates_per_lane") == 2
         and co.get("train_pairs_per_candidate") == 32
         and co.get("confirm_pairs_per_candidate") == 64
         and co.get("labels_per_pair") == 2
         and co.get("confirm_is_reserved") is True
         and co.get("train_selection_only") is True
         and co.get("no_F123_confirm_reuse") is True
         and co.get("disjoint_family_seed_and_salt") is True
         and co.get("confirm_access") ==
         "PROHIBITED_UNTIL_SEPARATE_AUTHENTIC_FIRST_USE_ELIGIBILITY",
         "COHORT_DISCIPLINE")
    historical = set(range(96000, 96024)) | set(range(96100, 96148)) | (
        set(range(97000, 97024)) | set(range(97100, 97148)))
    seen = set()
    for lane in ("Wingless", "Yggdrasil"):
        for phase, n in (("TRAIN", 32), ("CONFIRM", 64)):
            low, high = co[lane][phase]
            seeds = set(range(low, high + 1))
            need(len(seeds) == n and not seen.intersection(seeds)
                 and not historical.intersection(seeds), "SEED_OVERLAP")
            seen.update(seeds)
    ev = cfg["evaluation"]
    need(ev.get("frozen_success_margin_absolute") == 0.05
         and ev.get("minimum_margin_both_lanes") is True
         and ev.get("required_no_stratum_degradation") is True
         and ev.get("min_paired_accuracy_noninferiority_against_F123_dense_B") is True
         and ev.get("max_relative_s2_operations_to_dense_b") == 0.75
         and ev.get("resource_reduction_must_hold_each_lane") is True
         and ev.get("full_input_information_parity") is True
         and ev.get("parameter_limit") == 20
         and ev.get("scientific_ceiling_separate") is True
         and ev.get("no_prospective_science_claim_without_independent_original") is True,
         "FROZEN_SUCCESS_DRIFT")
    need(set(cfg["controls"]) == {
        "CTRL_F123_DENSE_B", "CTRL_F122_NO_ROUTING",
        "CTRL_FIXED_SOFT_PATH", "CTRL_ROLE_ONLY", "CTRL_QUERY_ONLY",
        "CTRL_EXACT_SYMBOLIC_CEILING", "CTRL_CUT_K_ABLATION"
    } and all(cfg.get("authority", {}).values())
        and len(cfg["authority"]) == 15, "AUTHORITY_OR_CONTROLS")
    need(cfg.get("qualification", {}).get("gate_now") ==
         "Freeze protocol and source-only contract validator only; do not simulate scientific success.",
         "PREIMPLEMENTATION_ONLY")
    return cfg


def frozen():
    raw = FREEZE.read_bytes().replace(b"\r\n", b"\n")
    need(blob(raw) == EXPECTED_FREEZE_BLOB, "FREEZE_GIT_BLOB")
    need(blob(F123_FREEZE.read_bytes()) == F123_FREEZE_BLOB,
         "IMMUTABLE_F123_CONTRACT_DRIFT")
    cfg = validate(json.loads(raw))
    return cfg, hashlib.sha256(raw).hexdigest()


def receipt(sha):
    need(isinstance(sha, str) and
         re.fullmatch("[0-9a-f]{40}", sha) is not None,
         "UNQUALIFIED_SHA")
    _, freeze_digest = frozen()
    return {
        "schema": "forge.autonomy.f124r.preimplementation-source-admission.v1",
        "source_commit_sha": sha,
        "parent_F123_exact_sha": F123_PARENT_SHA,
        "F124R_freeze_git_blob": EXPECTED_FREEZE_BLOB,
        "F124R_freeze_sha256": freeze_digest,
        "F123_freeze_git_blob": F123_FREEZE_BLOB,
        "cohorts_read": 0,
        "protected_confirmation_read": False,
        "learned_model_implemented": False,
        "train_weights_created": False,
        "scientific_first_use": False,
        "scientific_acceptance": False,
        "optimizer_promotion": False,
        "accepted_ref_mutation": False,
        "new_scheduler": False,
        "codex_calls": 0,
        "paid_model_calls": 0
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--source-ref", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    doc = receipt(a.source_ref)
    output = pathlib.Path(a.output)
    need(output.parent.is_dir() and not output.exists(), "RECEIPT_REPLACEMENT")
    output.open("xb").write((json.dumps(doc, sort_keys=True,
                         separators=(",", ":")) + "\n").encode())
    print("F124R_PREIMPLEMENTATION_FREEZE_SOURCE_ONLY=PASS")
    print("F124R_NO_CONFIRMATION_OR_SCIENCE=true")


if __name__ == "__main__":
    try:
        main()
    except (Invalid, OSError, ValueError, KeyError, TypeError) as e:
        print("F124R_PREIMPLEMENTATION_QUARANTINED="+str(e), file=sys.stderr)
        raise SystemExit(1)
