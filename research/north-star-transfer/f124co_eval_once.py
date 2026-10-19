"""One original public-only F124-CO prospective seven-role data evaluation.

NO source oracle, hidden family or seed in this process. Public cases are
downloaded from the sealed earlier birth job. All 72 native preflights and
360 whole-process samples are journaled. Scientific success is independent
from GitHub Actions engineering completion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import f124cn_complete_os_resource as resource
import f124cn_blind_trajectory_eval as blind

def need(ok,why):
    if not ok:raise RuntimeError("F124CO_EVAL_"+why)

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def git_blob(path):
    return subprocess.run(["git","rev-parse","HEAD:"+path],cwd=ROOT,
        check=True,capture_output=True,text=True).stdout.strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--public-dir",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    need(sys.platform=="linux" and os.environ.get("GITHUB_RUN_ATTEMPT")=="1",
         "ONE_ONLY_ORIGINAL_LINUX_FIRSTUSE_EVALUATION")
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,
         check=True,capture_output=True,text=True).stdout.strip()
    need(head==os.environ.get("GITHUB_SHA"),"ORIGINAL_EXACT_GIT_HEAD")
    freeze=json.loads((HERE/"f124co-original-admission.json").read_text())
    need(freeze["authorization"]["development_once"] is True
         and freeze["authorization"]["protected_replication"] is False
         and freeze["authorization"]["scientific_acceptance"] is False,
         "NO_UNAUTHORIZED_ADMISSION")
    for path,blob in freeze["exact_source_blobs"].items():
        need(git_blob(path)==blob,"ORIGINAL_SOURCE_BLOB_DRIFT")
    root=args.public_dir
    manifest=json.loads((root/"birth-public-manifest.json").read_text())
    need(manifest["schema"]=="mass.f124co.original-public-source-birth-manifest.v1"
         and manifest["source_firstuse_git_head"]==head
         and manifest["original_source_case_count"]==24
         and manifest["source_blob_sha"]==
             freeze["exact_source_blobs"]["research/north-star-transfer/f124cn_new_trajectory_source.py"]
         and manifest["protected_replication_opened"] is False,
         "BIRTH_ARTIFACT_FIRST_USE_IDENTITY")
    roster=manifest["original_public_roster"]
    ids=list(resource.IDS)
    need([r["id"] for r in roster]==ids and len(roster)==24,
         "EXACT_FROZEN_NO_RESAMPLING_ROSTER")
    files=sorted((root/"public-cases").glob("*.json"))
    need(len(files)==24,"PUBLIC_CASE_LIST_NO_EXTRA_OR_MISSING")
    for row in roster:
        path=root/"public-cases"/("case-"+str(row["id"])+".json")
        need(path.is_file() and digest(json.loads(path.read_text()))==row["public_sha256"],
             "BIRTH_BEFORE_MODEL_PRIVATE_TO_PUBLIC_PROOF")
    args.out.mkdir(parents=True,exist_ok=False)
    journal=args.out/"original-append-only.jsonl"
    preflights=[]
    for row in roster:
        case=row["id"]
        path=root/"public-cases"/("case-"+str(case)+".json")
        for arm in resource.ARMS:
            observed=resource.run_original_public_process(path,arm)
            need(observed["case_id"]==case
                 and observed["public_task_sha256"]==row["public_sha256"]
                 and observed["synthetic_engineering_only"] is False,
                 "NATURAL_UNMODIFIED_ORIGINAL_PREFLIGHT")
            preflights.append(observed)
            resource.append_journal(journal,{"preflight":True,"reading":observed})
    measurements=[]
    for row in roster:
        path=root/"public-cases"/("case-"+str(row["id"])+".json")
        for arm in resource.ARMS:
            for repetition in range(resource.REPS):
                observed=resource.run_original_public_process(path,arm)
                need(observed["public_task_sha256"]==row["public_sha256"],
                     "WHOLE_OS_SOURCE_INPUT_IDENTITY")
                measurements.append(observed)
                resource.append_journal(journal,{
                    "preflight":False,"repetition":repetition,"reading":observed})
    need(len(preflights)==72 and len(measurements)==360,
         "COMPLETE_432_INDEPENDENT_NATIVE_AND_OS_EVIDENCE")
    review=resource.review(preflights,measurements)
    original={"schema":"mass.f124co.original-scientific-development-observation.v1",
              "source_firstuse_git_head":head,
              "birth_manifest_sha256":digest(manifest),
              "birth_provider_private_custody_sha256":manifest["private_custody_sha256"],
              "original_source_blobs":freeze["exact_source_blobs"],
              "roster":roster,"original_72_preflights":preflights,
              "original_360_whole_process_measurements":measurements,
              "original_preliminary_review":review,
              "no_private_seed_or_oracle_imported":True,
              "no_old_source_replayed":True,
              "protected_firstuse_opened":False,
              "science_accepted":False}
    with (args.out/"original-full-evidence.json").open("x",encoding="utf8") as fp:
        json.dump(original,fp,sort_keys=True)
        fp.write("\n")
    report={"schema":"mass.f124co.original-public-review-summary.v1",
            "source_firstuse_git_head":head,
            "original_full_evidence_sha256":digest(original),
            "birth_manifest_sha256":digest(manifest),
            "original_public_roster_size":24,
            "original_72_preflights":len(preflights),
            "original_360_full_OS_measurements":len(measurements),
            "append_only_original_receipt_count":len(preflights)+len(measurements),
            "G_and_H_correct_pairs":review["family"],
            "G_and_H_net_gains":review["gain_over_trained"],
            "original_admission_failures":review["failures"],
            "all_original_cases_retained":True,
            "scientific_development_criteria_met":review["scientific_criteria_met_in_preliminary_metrics"],
            "independent_provenance_review_complete":False,
            "protected_opened":False,
            "science_accepted":False}
    with (args.out/"original-public-summary.json").open("x",encoding="utf8") as fp:
        json.dump(report,fp,sort_keys=True,indent=2);fp.write("\n")
    print("F124CO_ORIGINAL_PUBLIC_SOURCE_CASES=24")
    print("F124CO_NATIVE_PREFLIGHTS=72")
    print("F124CO_WHOLE_OS_COST_MEASUREMENTS=360")
    print("F124CO_APPEND_ONLY_ORIGINAL_RECEIPTS=432")
    print("F124CO_PRELIMINARY_GAINS="+json.dumps(review["gain_over_trained"],sort_keys=True))
    print("F124CO_SCIENTIFIC_ACCEPTANCE=FALSE")

if __name__=="__main__":main()
