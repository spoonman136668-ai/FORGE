"""F124-CU original ONE new-source-only firstuse, before BPTT evaluation.

No model import. Only source-only private original job sees hidden law,
symbolic oracle and real OS-entropy seeds. No outcome-directed re-birth.
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

def need(ok,why):
    if not ok:raise RuntimeError("F124CU_BIRTH_"+why)

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def git(path):
    return subprocess.run(["git","rev-parse","HEAD:"+path],cwd=ROOT,
             capture_output=True,text=True,check=True).stdout.strip()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path);p.add_argument("--head",required=True)
    x=p.parse_args()
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,
             capture_output=True,text=True,check=True).stdout.strip()
    need(head==x.head==os.environ.get("GITHUB_SHA") and
         os.environ.get("GITHUB_RUN_ATTEMPT")=="1","IMMUTABLE_ORIGINAL_PROVIDER_ATTEMPT")
    admission=json.loads((HERE/"f124cu-original-admission.json").read_text())
    need(admission["schema"]=="mass.f124cu.original-LM-development-once.v1"
         and admission["prereg_commit"]=="3402932e98144aeeade83b86826d6bae54f8aa67"
         and admission["authority"]["one_original_development_birth"]
         and not admission["authority"]["protected_firstuse"]
         and not admission["authority"]["science_accepted"]
         and not admission["authority"]["automatic_merge"],
         "INDEPENDENT_PRESCIENCE_ADMISSION_REQUIRED")
    for path,hash in admission["source_blobs"].items():
        need(git(path)==hash,"DRIFT_FROM_FROZEN_SOURCE_OR_LEARNER")
    need(not x.out.exists(),"SOURCE_OUTPUT_NOT_PREEXISTING")
    x.out.mkdir(parents=True)
    (x.out/"public-cases").mkdir()
    spec=importlib.util.spec_from_file_location("F124CU_ONLY_SOURCE_BIRTH",
                  HERE/"f124cu_private_source_only.py")
    need(spec is not None and spec.loader is not None,"SEPARATE_FROZEN_SOURCE_MODULE")
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    cases=[]
    for family,base in (("L",936000),("M",937000)):
        for ordinal in range(12):
            seed=secrets.randbits(128)
            need(seed>0,"OS_ENTROPY_REQUIRED")
            born=m.task(family,ordinal,seed)
            need(born["case_id"]==base+ordinal
                 and born["symbolic_oracle"]=={"positive":True,"hard_negative":False}
                 and born["previous_924_through_935_source_reused"] is False
                 and born["protected_source_opened"] is False,
                 "NEW_SEQUENTIAL_CAUSAL_SOURCE_PRIVATE_TRUTH")
            cases.append(born)
    ids=[x["case_id"] for x in cases]
    need(ids==list(range(936000,936012))+list(range(937000,937012)),
         "EXACT_FIRSTUSE_L_M_ROSTER")
    roster=[]
    for row in cases:
        need(digest(row["public_task"])==row["public_sha256"],
             "SOURCE_PUBLIC_TASK_HASH_MATCH")
        roster.append({"id":row["case_id"],"public_sha256":row["public_sha256"]})
    secret={"schema":"mass.f124cu.original-private-sequential-birth.v1",
        "head":head,"source_blob_sha":git("research/north-star-transfer/f124cu_private_source_only.py"),
        "cases":cases,"original_source_birth_precedes_evaluation":True,
        "no_candidate_or_control_in_birth":True,
        "origin":"INTERNAL_SOURCE_ONLY_NOT_EXTERNAL_REPLICATION",
        "protected_cohort_opened":False}
    manifest={"schema":"mass.f124cu.original-public-sequential-birth.v1",
        "head":head,"original_source_blob_sha":secret["source_blob_sha"],
        "original_roster":roster,"source_count":24,
        "private_custody_sha256":digest(secret),
        "no_private_seed_oracle_in_public_inputs":True,
        "source_born_before_model_training":True,
        "protected_firstuse":False}
    with (x.out/"sealed-private-original.json").open("x") as f:
        json.dump(secret,f,sort_keys=True);f.write("\n")
    for row in cases:
        with (x.out/"public-cases"/("case-"+str(row["case_id"])+".json")).open("x") as f:
            json.dump(row["public_task"],f,sort_keys=True);f.write("\n")
    with (x.out/"original-public-manifest.json").open("x") as f:
        json.dump(manifest,f,sort_keys=True);f.write("\n")
    print("F124CU_NEW_ORIGINAL_SEQUENCE_SOURCES=24")
    print("F124CU_PRIVATE_SEED_OR_ORACLE_TO_EVALUATOR=FALSE")
    print("F124CU_NEW_LM_CASE_IDS=936000-936011,937000-937011")
    print("F124CU_NO_PREVIOUS_SOURCES_OR_PROTECTED_COHORT=PASS")

if __name__=="__main__":main()
