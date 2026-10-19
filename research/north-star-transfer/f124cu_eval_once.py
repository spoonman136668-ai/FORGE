"""F124-CU exactly one original blinded 24-case 432-process BPTT study.

No source birth, secret seed, source-law import, retrospective tuning, or
silent workload parity conversion. All native preflights and complete
CPU/RSS observations are preserved even if every model abstains.
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
import f124cu_whole_os_cost as observer

def need(ok,reason):
    if not ok:raise RuntimeError("F124CU_ORIGINAL_"+reason)

def sha(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def git(path):
    return subprocess.run(["git","rev-parse","HEAD:"+path],cwd=ROOT,
            capture_output=True,text=True,check=True).stdout.strip()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--public-dir",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    x=p.parse_args()
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,
           capture_output=True,text=True,check=True).stdout.strip()
    need(sys.platform=="linux" and head==os.environ.get("GITHUB_SHA") and
         os.environ.get("GITHUB_RUN_ATTEMPT")=="1","EXACT_ORIGINAL_LINUX_PROVIDER")
    admission=json.loads((HERE/"f124cu-original-admission.json").read_text())
    need(admission["schema"]=="mass.f124cu.original-LM-development-once.v1"
         and admission["authority"]["one_original_development_birth"]
         and not admission["authority"]["protected_firstuse"]
         and not admission["authority"]["science_accepted"],
         "NO_UNFROZEN_SCIENCE_AUTHORITY")
    for path,hash in admission["source_blobs"].items():
        need(git(path)==hash,"ORIGINAL_SCIENCE_SOURCE_DRIFT")
    manifest=json.loads((x.public_dir/"original-public-manifest.json").read_text())
    need(manifest["schema"]=="mass.f124cu.original-public-sequential-birth.v1"
         and manifest["head"]==head and manifest["source_count"]==24
         and manifest["no_private_seed_oracle_in_public_inputs"]
         and manifest["original_source_blob_sha"]==
              admission["source_blobs"]["research/north-star-transfer/f124cu_private_source_only.py"]
         and not manifest["protected_firstuse"],
         "ORIGINAL_PUBLIC_SOURCE_BIRTH_REQUIRED_BEFORE_SCORING")
    roster=manifest["original_roster"]
    need([q["id"] for q in roster]==list(observer.CASES),"FROZEN_24_NEW_SOURCE_ROSTER")
    public=x.public_dir/"public-cases"
    need(len(list(public.glob("*.json")))==24,"NO_SOURCE_SELECTION_OR_SUBSTITUTION")
    for row in roster:
        path=public/("case-"+str(row["id"])+".json")
        need(path.is_file() and sha(json.loads(path.read_text()))==row["public_sha256"],
             "IMMUTABLE_BORN_PUBLIC_CAUSAL_EPISODES")
    x.out.mkdir(parents=True,exist_ok=False)
    journal=x.out/"original-append-only-receipts.jsonl"
    preflights=[];measurements=[]
    for row in roster:
        path=public/("case-"+str(row["id"])+".json")
        for arm in observer.ARMS:
            o=observer.observe(path,arm)
            need(o["case_id"]==row["id"] and
                 o["public_case_sha256"]==row["public_sha256"] and
                 not o["synthetic_engineering_only"],
                 "ORIGINAL_FIRST_NATIVE_BOUND_TO_BORN_CASE")
            preflights.append(o)
            observer.append(journal,{"preflight":True,"reading":o})
    for row in roster:
        path=public/("case-"+str(row["id"])+".json")
        for arm in observer.ARMS:
            for rep in range(observer.REPS):
                o=observer.observe(path,arm)
                need(o["public_case_sha256"]==row["public_sha256"],
                     "ORIGINAL_OS_REPETITION_SAME_FIRSTUSE_CASE")
                measurements.append(o)
                observer.append(journal,{"preflight":False,
                                "repetition":rep,"reading":o})
    need(len(preflights)==72 and len(measurements)==360,
         "COMPLETE_72_PLUS_360_ORIGINAL_PROCESS_SAMPLES")
    review=observer.review(preflights,measurements)
    all_data={"schema":"mass.f124cu.original-complete-sequential-BPTT-study.v1",
       "original_git_head":head,
       "original_public_birth_manifest_sha256":sha(manifest),
       "private_source_digest_only":manifest["private_custody_sha256"],
       "original_roster":roster,"exact_frozen_sources":admission["source_blobs"],
       "original_72_native_preflights":preflights,
       "original_360_full_process_CPU_RSS_samples":measurements,
       "original_preliminary_review":review,
       "source_private_oracle_not_passed_to_learner":True,
       "previous_scientific_sources_not_used":True,
       "protected_firstuse":False,"scientific_acceptance":False}
    with (x.out/"original-full-evidence.json").open("x") as f:
        json.dump(all_data,f,sort_keys=True);f.write("\n")
    summary={"schema":"mass.f124cu.original-summary-before-readonly-audit.v1",
       "head":head,"original_evidence_sha256":sha(all_data),
       "original_public_manifest_sha256":sha(manifest),
       "cases":24,"native_preflights":72,"complete_OS_samples":360,
       "append_only_receipts":432,
       "family_pairs":review["family_outcomes"],
       "native_equal_work_cases":review["natural_equal_native_work_cases"],
       "all_original_failure_categories":review["failure_categories"],
       "original_science_preliminary":review[
           "preliminary_scientific_gate_met_before_independent_custody"],
       "independent_custody_complete":False,
       "all_negatives_retained":True,"protected_opened":False,"science_accepted":False}
    with (x.out/"original-public-summary.json").open("x") as f:
        json.dump(summary,f,sort_keys=True,indent=2);f.write("\n")
    print("F124CU_ORIGINAL_SOURCES=24")
    print("F124CU_ORIGINAL_WHOLE_NATIVE_PREFLIGHTS=72")
    print("F124CU_ORIGINAL_WHOLE_OS_CPU_RSS=360")
    print("F124CU_ORIGINAL_APPEND_RECEIPTS=432")
    print("F124CU_ORIGINAL_FAMILY_PAIRS="+json.dumps(review["family_outcomes"],sort_keys=True))
    print("F124CU_RESOURCE_ELIGIBLE_NATIVE_CASES="+str(review["natural_equal_native_work_cases"]))
    print("F124CU_SCIENCE_ACCEPTED=FALSE")

if __name__=="__main__":main()
