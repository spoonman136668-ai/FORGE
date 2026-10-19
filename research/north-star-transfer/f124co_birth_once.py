"""F124-CO: ONE authentic source-only first-use birth, after signed Git head freeze.

This entry point is only called by the fenced GitHub Actions birth job.
The independent evaluator only downloads public source artifact, never
this private seed/oracle artifact. No retries after any source creation.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN=HERE/"f124co-original-admission.json"
SOURCE=HERE/"f124cn_new_trajectory_source.py"

def need(ok,why):
    if not ok:raise RuntimeError("F124CO_BIRTH_"+why)

def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def blob(path):
    return subprocess.run(["git","rev-parse","HEAD:"+str(path)],
        cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--head",required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    current=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,
            capture_output=True,text=True,check=True).stdout.strip()
    need(current==args.head and current==os.environ.get("GITHUB_SHA"),
         "SOURCE_HEAD_AND_PROVIDER_IDENTITY_REQUIRED")
    need(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","NO_RETRY_AFTER_SOURCE_BIRTH")
    freeze=json.loads(FROZEN.read_text())
    need(freeze["schema"]=="mass.f124co.original-firstuse-admission.v1"
         and freeze["authorization"]["development_once"] is True
         and freeze["authorization"]["operator_directive_received"] is True
         and freeze["authorization"]["protected_replication"] is False
         and freeze["authorization"]["scientific_acceptance"] is False
         and freeze["source_contract_commit"]=="c956013ff7d7adbab99e66f22a54593581b8a0bc",
         "ORIGINAL_SOURCE_FIRSTUSE_FREEZE")
    for path,expected in freeze["exact_source_blobs"].items():
        need(blob(path)==expected,"EXACT_FROZEN_SOURCE_DRIFT")
    need(not args.out.exists(),"ONE_BIRTH_DESTINATION")
    args.out.mkdir(parents=True)
    public_dir=args.out/"public-cases"
    public_dir.mkdir()
    private_file=args.out/"sealed-private-birth.json"
    summary_file=args.out/"birth-public-manifest.json"
    spec=importlib.util.spec_from_file_location("F124CO_SOURCE_ONLY",SOURCE)
    need(spec is not None and spec.loader is not None,"FROZEN_SOURCE_REQUIRED")
    origin=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(origin)
    records=[]
    for family,base in (("G",932000),("H",933000)):
        for idx in range(12):
            seed=secrets.randbits(128)
            need(seed>0,"OS_ENTROPY_128")
            case=origin.task(family,idx,seed)
            need(case["case_id"]==base+idx
                 and case["old_924_931_sources_used"] is False
                 and case["protected_cohort_opened"] is False
                 and case["oracle"]=={"positive":True,"hard_negative":False},
                 "UNALTERED_NEW_PRIVATE_FIRSTUSE")
            records.append(case)
    ids=[x["case_id"] for x in records]
    need(ids==list(range(932000,932012))+list(range(933000,933012)),
         "EXACT_24_FRESH_PROSPECTIVE_CASES")
    public_roster=[]
    for case in records:
        record={"public_task":case["public_task"],
                "public_sha256":case["public_sha256"]}
        need(sha(case["public_task"])==record["public_sha256"],"PUBLIC_IDENTITY")
        public_roster.append({"id":case["case_id"],"public_sha256":case["public_sha256"]})
    private={"schema":"mass.f124co.original-24-private-source-birth.v1",
             "source_firstuse_git_head":current,
             "source_blob_sha":blob("research/north-star-transfer/f124cn_new_trajectory_source.py"),
             "case_ids":ids,
             "cases":records,
             "origin":"INTERNALLY_AUTHORED_SEPARATE_SOURCE_ONLY",
             "source_birth_before_any_model_scoring":True,
             "new_model_called":False,
             "protected_cohorts_opened":False}
    summary={"schema":"mass.f124co.original-public-source-birth-manifest.v1",
             "source_firstuse_git_head":current,
             "source_blob_sha":private["source_blob_sha"],
             "operator_development_only":True,
             "original_public_roster":public_roster,
             "private_custody_sha256":sha(private),
             "no_private_seed_or_oracle_in_public_case":True,
             "original_source_case_count":24,
             "protected_replication_opened":False}
    # Every source is assembled before writing ANY artifact. No selection on outcomes.
    with private_file.open("x",encoding="utf8") as stream:
        json.dump(private,stream,sort_keys=True)
        stream.write("\n")
    for case in records:
        with (public_dir/("case-"+str(case["case_id"])+".json")).open("x",encoding="utf8") as stream:
            json.dump(case["public_task"],stream,sort_keys=True)
            stream.write("\n")
    with summary_file.open("x",encoding="utf8") as stream:
        json.dump(summary,stream,sort_keys=True)
        stream.write("\n")
    print("F124CO_FIRSTUSE_ORIGINAL_CASES=24")
    print("F124CO_ORIGIN=INTERNAL_SOURCE_ONLY_OS_ENTROPY")
    print("F124CO_CASES=932000-932011,933000-933011")
    print("F124CO_MODEL_EVALUATION_BEFORE_ORIGIN=FALSE")
    print("F124CO_PROTECTED_USED=FALSE")

if __name__=="__main__":main()
