"""F124-CR source-blind once-only original J/K development evaluation.

Reads ONLY immutable public source artifact from prior GitHub birth job,
never imports hidden source, seed, private oracle. Appends all preflights
and every whole-process measurement, retaining all negatives/abstentions.
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
import f124cr_complete_os as oscore

def need(ok,reason):
    if not ok:raise RuntimeError("F124CR_ORIGINAL_"+reason)

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
    need(sys.platform=="linux" and os.environ.get("GITHUB_RUN_ATTEMPT")=="1",
         "LINUX_EXACT_ONCE_ORIGINAL")
    actual=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,
        capture_output=True,text=True,check=True).stdout.strip()
    need(actual==os.environ.get("GITHUB_SHA"),"ORIGINAL_GITHUB_HEAD_BOUND")
    admit=json.loads((HERE/"f124cr-original-admission.json").read_text())
    need(admit["schema"]=="mass.f124cr.one-original-internal-JK-admission.v1"
         and admit["authority"]["original_development_firstuse_once"]
         and not admit["authority"]["protected_firstuse"]
         and not admit["authority"]["scientific_acceptance"],
         "ORIGINAL_FROZEN_SCIENCE_BOUNDARY")
    for path,expected in admit["exact_source_blobs"].items():
        need(git(path)==expected,"FROZEN_ORIGINAL_MODEL_SOURCE_DRIFT")
    manifest=json.loads((x.public_dir/"birth-public-manifest.json").read_text())
    need(manifest["schema"]=="mass.f124cr.original-public-firstuse-manifest.v1"
         and manifest["original_git_head"]==actual
         and manifest["original_case_count"]==24
         and manifest["public_packets_do_not_contain_seeds_or_oracle"]
         and not manifest["protected_source_opened"]
         and manifest["source_blob"]==admit["exact_source_blobs"][
             "research/north-star-transfer/f124cr_source_only.py"],
         "ONLY_AUTHENTIC_ORIGINAL_SOURCE_BIRTH")
    roster=manifest["original_roster"]
    need([q["id"] for q in roster]==list(oscore.ROSTER),
         "FROZEN_NEW_JK_24_IDENTITY")
    public=x.public_dir/"public-cases"
    need(len(list(public.glob("*.json")))==24,"NO_SOURCE_SUBSTITUTION")
    for row in roster:
        path=public/("case-"+str(row["id"])+".json")
        need(path.is_file() and sha(json.loads(path.read_text()))==row["public_sha256"],
             "ORIGINAL_PRIVATE_SOURCE_PUBLIC_HASH")
    x.out.mkdir(parents=True,exist_ok=False)
    journal=x.out/"original-append-journal.jsonl"
    preflights=[]
    samples=[]
    for row in roster:
        path=public/("case-"+str(row["id"])+".json")
        for arm in oscore.ARMS:
            receipt=oscore.measure_case(path,arm)
            need(receipt["case_id"]==row["id"] and
                 receipt["public_task_sha256"]==row["public_sha256"]
                 and not receipt["synthetic_engineering_only"],
                 "ORIGINAL_PUBLIC_NATIVE_ENTRY")
            preflights.append(receipt)
            oscore.durable_append(journal,{"preflight":True,"reading":receipt})
    for row in roster:
        path=public/("case-"+str(row["id"])+".json")
        for arm in oscore.ARMS:
            for rep in range(oscore.REPS):
                receipt=oscore.measure_case(path,arm)
                need(receipt["public_task_sha256"]==row["public_sha256"],
                     "ORIGINAL_PUBLIC_OS_COST")
                samples.append(receipt)
                oscore.durable_append(journal,{"preflight":False,
                     "repetition":rep,"reading":receipt})
    need(len(preflights)==72 and len(samples)==360,"COMPLETE_ORIGINAL_432")
    review=oscore.summarize(preflights,samples)
    evidence={"schema":"mass.f124cr.original-complete-public-native-evidence.v1",
       "original_git_head":actual,
       "original_public_birth_manifest_sha256":sha(manifest),
       "original_private_sealed_sha256":manifest["sealed_private_sha256"],
       "original_roster":roster,
       "original_72_native_preflights":preflights,
       "original_360_whole_OS_process_samples":samples,
       "original_preliminary_scientific_review":review,
       "original_source_blobs":admit["exact_source_blobs"],
       "private_source_oracle_seen_by_evaluator":False,
       "protected_cohorts_used":False,
       "science_accepted":False}
    with (x.out/"original-complete-evidence.json").open("x") as fp:
        json.dump(evidence,fp,sort_keys=True);fp.write("\n")
    safe={"schema":"mass.f124cr.original-public-science-summary.v1",
       "original_git_head":actual,
       "original_complete_evidence_sha256":sha(evidence),
       "original_public_manifest_sha256":sha(manifest),
       "original_native_preflights":len(preflights),
       "original_whole_OS_samples":len(samples),
       "original_append_receipts":len(preflights)+len(samples),
       "family_correct_pairs":review["families"],
       "resource_parity_eligible_cases":review["eligible_native_parity_cases"],
       "original_failures":review["failures"],
       "development_scientific_criteria_before_independent_audit":
                review["candidate_development_criteria_met_before_independent_audit"],
       "original_negative_retained":True,
       "independent_audit_completed":False,
       "protected_opened":False,"science_accepted":False}
    with (x.out/"original-public-summary.json").open("x") as fp:
        json.dump(safe,fp,sort_keys=True,indent=2);fp.write("\n")
    print("F124CR_ORIGINAL_CASES=24")
    print("F124CR_NATIVE_PREFLIGHTS=72")
    print("F124CR_WHOLE_OS_CPU_RSS=360")
    print("F124CR_ORIGINAL_APPEND_RECEIPTS=432")
    print("F124CR_ORIGINAL_FAMILY_PAIRS="+json.dumps(review["families"],sort_keys=True))
    print("F124CR_RESOURCE_ELIGIBLE_CASES="+str(review["eligible_native_parity_cases"]))
    print("F124CR_SCIENCE_ACCEPTED=FALSE")

if __name__=="__main__":main()
