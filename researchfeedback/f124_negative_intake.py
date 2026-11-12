"""Read authentic F124 scientific negatives into a development-only research agenda.

Only immutable archived FIT negatives enter this seam; never accepted science,
optimizer labels, sealed DEV, or candidate calibration. Read-only GitHub API
metadata is separately captured by an existing observer workflow.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

SCHEMA="forge.research-feedback.f124-authenticated-negative-intake.v1"
OUTPUT="forge.research-feedback.f124-original-negative-development-advisory.v1"
SHA40=re.compile(r"^[0-9a-f]{40}$")
SHA64=re.compile(r"^[0-9a-f]{64}$")
class Quarantine(ValueError):pass

def require(ok,why):
    if not ok:raise Quarantine("F124_FEEDBACK_"+why)

def strict_json(raw):
    require(type(raw) is bytes and 1<len(raw)<=1_000_000,"BOUNDED_INPUT")
    def pairs(items):
        out={}
        for key,value in items:
            require(key not in out,"DUPLICATE_JSON_KEY")
            out[key]=value
        return out
    try:return json.loads(raw.decode("utf8"),object_pairs_hook=pairs,
             parse_constant=lambda _:require(False,"NONFINITE_NUMBER"))
    except (UnicodeError,ValueError) as exc:
        if isinstance(exc,Quarantine):raise
        raise Quarantine("INVALID_JSON") from exc

def digest(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return strict_json(Path(path).read_bytes())

def validate_run(run,record,repo):
    require(type(run) is dict and run.get("id")==record["run"]
            and run.get("head_sha")==record["original_run_head"]
            and run.get("status")=="completed" and run.get("conclusion")=="success"
            and run.get("run_attempt")==1
            and run.get("repository",{}).get("full_name")==repo
            and run.get("head_repository",{}).get("full_name")==repo
            and run.get("event")=="push","RUN_SOURCE_OR_PROVENANCE")
    return True

def validate_artifacts(a,record):
    require(type(a) is dict and type(a.get("artifacts")) is list,"PROVIDER_INDEX_SHAPE")
    match=[row for row in a["artifacts"] if row.get("id")==record["artifact"]]
    if match:
        require(len(match)==1 and match[0].get("digest")==record["provider_zip_digest"]
                and match[0].get("workflow_run",{}).get("id")==record["run"],
                "PROVIDER_ARTIFACT_MISMATCH")
        return "PROVIDER_METADATA_MATCHED" if not match[0].get("expired") else "ARCHIVED_AFTER_PROVIDER_EXPIRY"
    # Long-lived immutable Git custody persists after provider's artifact TTL.
    return "GIT_ARCHIVED_PROVIDER_ARTIFACT_EXPIRED_OR_UNLISTED"

def validate_science(data,record,raw):
    require(digest(raw)==record["sha256"] and len(raw)==record["bytes"]
            and data.get("schema")==record["expected_schema"],"ARCHIVED_RAW_IDENTITY")
    require(data.get("FIT_pairs")==24 and data.get("FIT_hard_cases")==24
            and data.get("FIT_selected") is None
            and data.get("SCREEN_pairs")==0 and data.get("SCREEN_models") is None
            and data.get("SCREEN_not_constructed_due_to_negative_FIT") is True
            and data.get("same_48_public_responses_per_arm") is True
            and data.get("DEV_constructed")==0 and data.get("Wingless_DEV_constructed")==0
            and data.get("protected_science_acceptance") is False
            and data.get("optimizer_promotion") is False
            and data.get("accepted_ref_mutation") is False,"UNQUALIFIED_SCIENCE_AUTHORITY")
    models=data.get("FIT_models")
    require(type(models) is dict and len(models)==10,"ORIGINAL_TEN_ARM_COMPLETENESS")
    metrics={}
    for query in ("balanced","random"):
        base=models["joint_"+query+"48"]
        require(base["hard_cases"]==24 and base["original_FP"]==0
                and base["positive"]>=1
                and base["hard_FP"]==record["baseline_"+query+"_FP"],
                "MATCHED_BASELINE_COUNTS")
        metrics[query]={"joint_accepted_positives":base["positive"],
                        "joint_hard_FP":base["hard_FP"]}
    if record["id"]=="F124-BD":
        exact=models["witness_balanced_exact"]
        require(exact["hard_FP"]==0 and
                metrics["balanced"]["joint_accepted_positives"]-exact["positive"]==
                record["exact_balanced_positive_loss"]==5
                and exact["positive_witness_vetoes"]==5,
                "BD_FP_CORRECTION_WITH_POSITIVE_LOSS")
    elif record["id"]=="F124-BE":
        unbacked=models["contrast_balanced_unbacked"]
        require(unbacked["hard_FP"]==0 and
                metrics["balanced"]["joint_accepted_positives"]-unbacked["positive"]==
                record["unsupported_balanced_positive_loss"]==6
                and unbacked["positive_witness_vetoes"]==6,
                "BE_UNBACKED_POSITIVE_LOSS")
    else:require(False,"UNAUTHORIZED_COHORT")
    return metrics

def select_advisory(manifest, inputs):
    require(manifest.get("schema")==SCHEMA and
            manifest.get("purpose")=="ADVISORY_ONLY_RESEARCH_SELECTION_NO_SCIENCE_ACCEPTANCE_OR_OPTIMIZER_TRAINING"
            and manifest.get("source_repo")=="spoonman136668-ai/FORGE"
            and SHA40.fullmatch(manifest.get("base_main_sha",""))
            and len(manifest.get("examples",[]))==2
            and [r["id"] for r in manifest["examples"]]==["F124-BD","F124-BE"]
            and all(value is False for value in manifest["authority"].values()),
            "MANIFEST_SCOPE")
    summary=[]
    for record in manifest["examples"]:
        for key in ("original_run_head","archival_commit","blob_sha"):
            require(SHA40.fullmatch(record[key]) is not None,"GIT_IDENTITY_MALFORMED")
        require(SHA64.fullmatch(record["sha256"]) is not None,"RAW_SHA_MALFORMED")
        run,artifact,raw=inputs[record["id"]]
        provenance=validate_run(run,record,manifest["source_repo"])
        state=validate_artifacts(artifact,record)
        decoded=strict_json(raw)
        metrics=validate_science(decoded,record,raw)
        summary.append({"id":record["id"],"original_run":record["run"],
           "source_sha":record["original_run_head"],"original_git_blob":record["blob_sha"],
           "archived_original_sha256":record["sha256"],"provider_evidence":state,
           "source_verified":provenance,"metrics":metrics,
           "scientific_acceptance":False})
    b,d=summary
    require(b["metrics"]["balanced"]["joint_hard_FP"]>0
            and d["metrics"]["balanced"]["joint_hard_FP"]==0,
            "CONTRASTING_FAILURE_MODE_NOT_PRESENT")
    plan=manifest.get("next_design",{})
    require(plan.get("gate")=="F124-BF" and
            SHA40.fullmatch(plan.get("preregistered_commit","")) is not None
            and SHA40.fullmatch(plan.get("freeze_blob","")) is not None
            and plan.get("hard_negatives_per_pair")==4
            and plan.get("minimum_full_hard_panel_pairs")==18
            and plan.get("matched_public_observations_per_arm")==48
            and plan.get("source_prediction_blind") is True
            and plan.get("all_baseline_accepted_positives_preserved") is True
            and plan.get("Feistel_positive_IDs_preserved") is True
            and plan.get("protected_DEV_unused") is True
            and plan.get("require_baseline_hard_FP_greater_than_zero") is True,
            "FROZEN_NEXT_CHALLENGE_DOES_NOT_FIX_SCIENCE_DESIGN")
    return {"schema":OUTPUT,"stage":"AUTHENTIC_ARCHIVED_NEGATIVE_TO_DEVELOPMENT_ADVISORY",
      "source_repo":manifest["source_repo"],"retained_evidence":summary,
      "negative_cohorts":len(summary),
      "failure_modes":["CORRECT_HARD_FALSE_POSITIVES_BUT_LOSE_TRUE_POSITIVES",
                       "UNINFORMATIVE_ZERO_FALSE_POSITIVE_BASELINE"],
      "next_research_gate":"F124-BF",
      "frozen_next_source_commit":plan["preregistered_commit"],
      "frozen_next_source_git_blob":plan["freeze_blob"],
      "challenge_contract":{"fresh_prediction_blind_hard_panel":4,
         "minimum_full_panel_cases":18,"equal_public_observations":48,
         "baseline_FP_must_exist_to_prove_improvement":True,
         "all_baseline_positives_preserved":True,
         "Feistel_positives_preserved":True,
         "FIT_before_held_SCREEN":True,"DEV_remains_sealed":True},
      "planning_feedback_available":True,
      "live_controller_consumption_proven":False,
      "training_examples_admitted":0,"accepted_scientific_originals":0,
      "optimizer_training_labels":0,"policy_promotions":0,
      "scientific_first_use_authorized":False,"accepted_ref_mutations":0,
      "additional_scheduler_created":False}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--manifest",required=True)
    a.add_argument("--bd",required=True);a.add_argument("--be",required=True)
    a.add_argument("--run-bd",required=True);a.add_argument("--run-be",required=True)
    a.add_argument("--artifacts-bd",required=True);a.add_argument("--artifacts-be",required=True)
    a.add_argument("--output",required=True)
    x=a.parse_args()
    inputs={}
    for tag in ("BD","BE"):
        path=getattr(x,tag.lower())
        inputs["F124-"+tag]=(read(getattr(x,"run_"+tag.lower())),
            read(getattr(x,"artifacts_"+tag.lower())),Path(path).read_bytes())
    record=select_advisory(read(x.manifest),inputs)
    dest=Path(x.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("xb") as f:
        f.write((json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode())
    print("F124_AUTHENTIC_RESEARCH_NEGATIVES_TO_DEVELOPMENT_ADVISORY=PASS")
    print("F124_RETUNING_FROM_CONSUMED_RESULTS=false")
    print("F124_SCIENCE_OR_OPTIMIZER_PROMOTION=false")
if __name__=="__main__":
    try:main()
    except (Quarantine,KeyError,IndexError,TypeError,OSError,ValueError) as error:
        print("F124_FEEDBACK_FAIL_CLOSED:"+str(error),file=sys.stderr)
        sys.exit(1)
