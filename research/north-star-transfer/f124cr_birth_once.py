"""F124-CR one authentic source-only ORIGINAL J/K first-use birth.

Separate GitHub-hosted job before any learner can score a public task.
Never expose private source/seed/ground truth to the evaluation runner.
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
BIRTH_SOURCE=HERE/"f124cr_source_only.py"
ADMISSION=HERE/"f124cr-original-admission.json"
FIRST_FREEZE="b3a18f099b58681a511bfc3205a9a60cb678c8d8"

def need(ok,reason):
    if not ok:raise RuntimeError("F124CR_BIRTH_"+reason)

def canon(v):
    return json.dumps(v,sort_keys=True,separators=(",",":")).encode()

def sha(v):
    return hashlib.sha256(canon(v)).hexdigest()

def git(path):
    return subprocess.run(["git","rev-parse","HEAD:"+path],cwd=ROOT,
        capture_output=True,text=True,check=True).stdout.strip()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--head",required=True);p.add_argument("--out",required=True,type=Path)
    x=p.parse_args()
    actual=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,
                 capture_output=True,text=True,check=True).stdout.strip()
    need(actual==x.head==os.environ.get("GITHUB_SHA"),
         "FROZEN_GITHUB_HEAD_AT_FIRSTUSE")
    need(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","ORIGINAL_ATTEMPT_ONLY")
    admit=json.loads(ADMISSION.read_text())
    need(admit["schema"]=="mass.f124cr.one-original-internal-JK-admission.v1"
         and admit["prereg_commit"]==FIRST_FREEZE
         and admit["authority"]["original_development_firstuse_once"]
         and not admit["authority"]["protected_firstuse"]
         and not admit["authority"]["scientific_acceptance"]
         and not admit["authority"]["automatic_merge"],
         "SOURCE_FIRSTUSE_NOT_INDEPENDENTLY_FROZEN")
    for path,expected in admit["exact_source_blobs"].items():
        need(git(path)==expected,"FROZEN_GIT_BLOB_DRIFT")
    need(not x.out.exists(),"ORIGINAL_BIRTH_NOT_OVERWRITTEN")
    x.out.mkdir(parents=True)
    public=x.out/"public-cases";public.mkdir()
    spec=importlib.util.spec_from_file_location("F124CR_PRIVATE_ORIGIN_ONLY",BIRTH_SOURCE)
    origin=importlib.util.module_from_spec(spec);spec.loader.exec_module(origin)
    cases=[]
    for family,base in (("J",934000),("K",935000)):
        for i in range(12):
            seed=secrets.randbits(128)
            need(seed>0,"REAL_OS_ENTROPY")
            case=origin.task(family,i,seed)
            need(case["case_id"]==base+i and
                 not case["old_924_through_933_cases_used"]
                 and not case["protected_cohort_opened"]
                 and case["oracle_positive"] and not case["oracle_negative"],
                 "NEW_ORIGINAL_PRIVATE_SYMBOLIC_SOURCE")
            cases.append(case)
    ids=[v["case_id"] for v in cases]
    need(ids==list(range(934000,934012))+list(range(935000,935012))
         and len(set(ids))==24,"EXACT_NEW_ORIGINAL_ROSTER")
    roster=[]
    for case in cases:
        need(sha(case["public_task"])==case["public_sha256"],
             "PRIVATE_TO_PUBLIC_HASH_BOUND")
        roster.append({"id":case["case_id"],"public_sha256":case["public_sha256"]})
    sealed={"schema":"mass.f124cr.original-private-JK-24-birth.v1",
            "original_git_head":actual,"firstuse_source_blob":
               git("research/north-star-transfer/f124cr_source_only.py"),
            "cases":cases,"private_source_creation_precedes_any_scoring":True,
            "no_learner_called_in_birth":True,"protected_source_used":False,
            "source_origin":"INTERNAL_SOURCE_ONLY_NOT_EXTERNAL_AUTHOR"}
    manifest={"schema":"mass.f124cr.original-public-firstuse-manifest.v1",
            "original_git_head":actual,"source_blob":sealed["firstuse_source_blob"],
            "original_roster":roster,"original_case_count":24,
            "sealed_private_sha256":sha(sealed),
            "public_packets_do_not_contain_seeds_or_oracle":True,
            "protected_source_opened":False}
    with (x.out/"sealed-private-birth.json").open("x",encoding="utf8") as fp:
        json.dump(sealed,fp,sort_keys=True);fp.write("\n")
    for case in cases:
        with (public/("case-"+str(case["case_id"])+".json")).open("x",encoding="utf8") as fp:
            json.dump(case["public_task"],fp,sort_keys=True);fp.write("\n")
    with (x.out/"birth-public-manifest.json").open("x",encoding="utf8") as fp:
        json.dump(manifest,fp,sort_keys=True);fp.write("\n")
    print("F124CR_ORIGINAL_SOURCE_BIRTH=24")
    print("F124CR_J_K_ORIGINAL_FIRSTUSE_IDS=934000-934011,935000-935011")
    print("F124CR_PRIVATE_TO_EVALUATOR=FALSE")
    print("F124CR_PREVIOUS_SOURCES_USED=FALSE")

if __name__=="__main__":main()
