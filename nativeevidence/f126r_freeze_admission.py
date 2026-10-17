"""F126-R immutable preregistration admission; not an experiment.

This executable intentionally cannot generate a F126R case, train a model,
read protected confirmation, dispatch science or mutate accepted refs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f126r-binding-evidence-prereg-freeze.json"
F125R=ROOT/"reference/research-intake/f125r-path-preserving-composition-freeze.json"
SOURCE_BLOB="7d6cf0469db557c0fced95d25e6fe55b8e34c136"
PARENT_BLOB="0a2030f17123b7e096c42e730f3a536f014275bd"
PARENT_COMMIT="762a9ab4f531d4f94b5fe2b06ac732d8d0de1600"
SCHEMA="forge.research.f126r.binding-evidence-calibration-prereg.v1"

class Invalid(ValueError): pass

def require(ok,marker):
    if not ok: raise Invalid("F126R_FREEZE_"+marker)

def blob(raw):
    raw=raw.replace(b"\r\n",b"\n")
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def validate(c):
    require(type(c) is dict and c.get("schema")==SCHEMA and
            c.get("status")=="PREIMPLEMENTATION_NO_TRAIN_NO_CONFIRM_NO_ACCEPTANCE" and
            c["source"]["parent_f125r_qualified_commit"]==PARENT_COMMIT and
            c["source"]["parent_f125r_qualification_run"]==39054466624 and
            c["source"]["parent_f125r_protocol_git_blob"]==PARENT_BLOB and
            c["source"]["prior_scientific_results_unmodified"] is True,
            "SOURCE_IDENTITY")
    n=c["retained_negatives"]
    require(n["F125R_Wingless_paired"]==[0,64] and
            n["F125R_Yggdrasil_paired"]==[0,64] and
            n["F125R_positive_rank_above_negative_Wingless"]==[0,64] and
            n["F125R_positive_rank_above_negative_Yggdrasil"]==[0,64] and
            n["F125R_exact_public_symbolic_accuracy"]==[64,64] and
            n["F125R_fixed_soft_12_of_16_accuracy"]==[0,64] and
            n["F125R_wrong_role_null_prediction_flips"]==0 and
            n["F125R_inference_state_peak_max"]==10 and
            n["negative_retention_immutable"] is True,
            "NEGATIVE_REWRITTEN")
    h=c["hypothesis"]
    require(h["trainable_parameters"]==20 and
            h["optimizer_epochs"]==100 and
            h["learning_rate"]==.22 and
            h["gradient_clip"]==1.0 and
            "logistic ranking loss plus 0.5*BCE" in h["training_loss"] and
            "normalized" not in h.get("forbidden","") and
            "No hard K2 pruning" in h["forbidden"] and
            "Single public observation" in h["inference_input"] and
            "correct for public path count" in h["normalization"] and
            "graph-matched label-blind token-scramble" in h["mechanism"] and
            "Exactly one canonical label-blind" in h["negative_reference"],
            "FROZEN_MECHANISM")
    p=c["prospective_evaluation"]
    require(p["task_family"]=="F126R-TRAIN-NEW-COMPOSITION-V1" and
            p["train_structural_depth"]==[3,5] and
            p["protected_confirm_structural_depth"]==[6,8] and
            p["train_public_candidate_paths"]==[6,12] and
            p["confirm_public_candidate_paths"]==[8,16] and
            p["source_vectors_per_lane"]==2 and
            p["balanced_pairs_per_source"]==32 and
            p["same_information_for_controls"] is True and
            p["source_generated_only_after_freeze"] is True and
            p["protected_confirmation_generated"] is False and
            p["hidden_label_and_oracle_not_model_inputs"] is True,
            "GRAPH_FAMILY")
    co=p["cohorts"]
    require(co=={"Wingless":{"TRAIN":[160100,160131],"CONFIRM":[160200,160263]},
                 "Yggdrasil":{"TRAIN":[170100,170131],"CONFIRM":[170200,170263]}},
            "COHORT_RESERVATION")
    seen=set()
    for lane in ("Wingless","Yggdrasil"):
        for phase,length in (("TRAIN",32),("CONFIRM",64)):
            lo,hi=co[lane][phase]
            ids=set(range(lo,hi+1))
            require(len(ids)==length and not (ids & seen),"SEED_COLLISION")
            seen |= ids
    ctr=p["frozen_controls"]
    require(set(ctr)=={"CTRL_EXACT_PUBLIC_SYMBOLIC_ELIGIBLE",
            "CTRL_F123_DENSE_B_FRESH","CTRL_F124R_SPARSE2_FRESH",
            "CTRL_F125R_PATH_PRESERVING_FRESH","CTRL_FIXED_SOFT_12_16",
            "CTRL_ROLE_ONLY","CTRL_QUERY_ONLY",
            "CTRL_NO_NORMALIZATION_ABLATION",
            "CTRL_NO_NULL_SUBTRACTION_ABLATION"} and
            "MANDATORY ELIGIBLE" in p["exact_symbolic_control"] and
            "NEVER be excluded" in p["exact_symbolic_control"] and
            "No fixed-control headroom selection" in p["headroom_rule"],
            "ELIGIBLE_STRONG_BASELINES")
    a=p["accuracy_requirements"]
    require(a=={"minimum_paired_fraction_of_exact":.9,
                "minimum_pairwise_ranking":.9,
                "zero_unreported_depth_stratum_failures":True} and
            "0.75" in p["cost_requirement"] and
            "If exact solver is both more accurate and no more expensive" in p["no_unearned_fitness"],
            "VALID_SCIENCE_THRESHOLDS")
    g=c["science_governance"]
    require(g["current_gate"].startswith("Freeze this independent hypothesis") and
            g["protected_confirm_access"] is False and
            g["first_use_authorized"] is False and
            g["scientific_acceptance"] is False and
            g["optimizer_promotion"] is False and
            g["accepted_ref_mutations"]==0 and
            g["model_invocations"]==0 and
            g["paid_model_calls"]==0 and
            g["codex_calls"]==0 and
            g["new_scheduler"] is False and
            g["ckb_plane_dependency"] is False and
            g["cloudflare_writes"]==0 and
            g["mind_palace_writes"]==0 and
            g["scientific_originals_executed"]==0 and
            g["no_merge"] is True,
            "UNAUTHORIZED_POWER")
    return c

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    require(blob(raw)==SOURCE_BLOB,"SOURCE_GIT_BLOB")
    require(blob(F125R.read_bytes())==PARENT_BLOB,"PARENT_FREEZE_GIT_BLOB")
    obj=json.loads(raw)
    return validate(obj),hashlib.sha256(raw).hexdigest()

def admission(source):
    require(type(source) is str and re.fullmatch("[0-9a-f]{40}",source) is not None,
            "INVALID_EXACT_SHA")
    _,dig=frozen()
    return {"schema":"forge.research.f126r.source-only-freeze-admission.v1",
            "source_sha":source,"freeze_git_blob":SOURCE_BLOB,
            "freeze_sha256":dig,"parent_commit_sha":PARENT_COMMIT,
            "parent_freeze_git_blob":PARENT_BLOB,
            "train_cases_generated":0,"confirmation_cases_generated":0,
            "learned_weights_created":False,
            "scientific_first_use":False,"scientific_acceptance":False,
            "optimizer_promotion":False,"accepted_ref_mutation":False,
            "new_controller":False,"codex_or_paid_model_calls":0}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-sha",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    report=admission(args.source_sha)
    out=pathlib.Path(args.output)
    require(out.parent.is_dir() and not out.exists(),"UNAUTHORIZED_REPLACE")
    out.open("xb").write((json.dumps(report,sort_keys=True,
       separators=(",",":"))+"\n").encode())
    print("F126R_PREIMPLEMENTATION_FREEZE=PASS")
    print("F126R_CONFIRMATION_READ=false")
    print("F126R_ORIGINAL_SCIENCE=false")

if __name__=="__main__":
    try: main()
    except (Invalid,KeyError,OSError,ValueError,TypeError) as exc:
        print("F126R_FREEZE_QUARANTINED="+str(exc),file=sys.stderr)
        raise SystemExit(1)
