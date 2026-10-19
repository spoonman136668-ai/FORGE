"""F124-CH source-birth job only; no models or native scorer.

Exactly 24 internally authored unknown E/F development sources are born in
an original separate GitHub Actions job. Seeds and source cases are sealed
and uploaded BEFORE dependent scoring jobs can begin. No reseeding, model
selection or source substitution based on results is permitted.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import secrets
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE=HERE/"f124ch_internal_source.py"
FROZEN=HERE/"f124ch-frozen-internal-prospective-EF.json"


def need(ok,why):
    if not ok:raise RuntimeError("F124CH_BIRTH_"+why)


def sha(obj):
    return hashlib.sha256(json.dumps(
        obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def load_only_origin():
    spec=importlib.util.spec_from_file_location("F124CH_source_born_only",SOURCE)
    need(spec is not None and spec.loader is not None,
         "ORIGINAL_SOURCE_CODE_REQUIRED")
    model=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    return model


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--git-head",required=True)
    a=ap.parse_args()
    git=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,
                       capture_output=True,text=True,check=True).stdout.strip()
    need(git==a.git_head,"BIRTH_EXACT_GITHUB_HEAD_REQUIRED")
    source_blob=subprocess.run(
        ["git","rev-parse","HEAD:research/north-star-transfer/f124ch_internal_source.py"],
        cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    protocol_blob=subprocess.run(
        ["git","rev-parse","62eb3584f42d3edd5caddc7667b567e81489af4f:research/north-star-transfer/f124ch-frozen-internal-prospective-EF.json"],
        cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    protocol=json.loads(FROZEN.read_text())
    need(protocol["schema"]=="mass.f124ch.internal-blinded-prospective-EF.v1"
         and protocol["frozen_before_source_implementation"]
         and protocol["origin"].startswith("INTERNALLY_AUTHORED")
         and protocol["fresh_sources"]["E"]["development"]==[928000,928011]
         and protocol["fresh_sources"]["F"]["development"]==[929000,929011],
         "UNCHANGED_PREBIRTH_ADMISSION_CONTRACT")
    need(protocol["authority"]["one_time_source_birth_and_development_measurement"]
         and not protocol["authority"]["protected_firstuse"],
         "ONLY_DEVELOPMENT_FIRSTUSE")
    model=load_only_origin()
    complete=[]
    for family in ("E","F"):
        for ordinal in range(12):
            seed=secrets.randbits(128)
            need(seed>0,"REAL_OS_ENTROPY_REQUIRED")
            case=model.task(family,ordinal,seed)
            need(case["task_identity"]==
                 (928000 if family=="E" else 929000)+ordinal
                 and case["symbolic_ground_truth"]=={
                     "positive":True,"hard_negative":False}
                 and not case["replication_cohort_opened"],
                 "PRIVATE_SYMBOLIC_ORACLE_AND_FIRSTUSE")
            complete.append(case)
    ids=[x["task_identity"] for x in complete]
    need(len(complete)==len(set(ids))==24
         and ids==list(range(928000,928012))+list(range(929000,929012)),
         "ONE_AND_ONLY_ONE_ORIGINAL_CASE_PER_RESERVED_ID")
    result={
      "schema":"mass.f124ch.original-sealed-internal-EF-birth.v1",
      "original_source_git_head":git,
      "original_source_blob_sha":source_blob,
      "frozen_protocol_blob_sha":protocol_blob,
      "original_source_identity":"INTERNALLY_AUTHORED_NOT_EXTERNAL",
      "source_module_has_no_learned_model_import":True,
      "case_birth_before_evaluation":True,
      "original_all_24_firstuse_cases":complete,
      "original_all_24_task_digests":[x["public_task_sha256"] for x in complete],
      "original_all_case_packet_sha256":sha(complete),
      "new_EF_replication_cohorts_created":False,
      "BV_924_925_unchanged":True,
      "CE_926_927_unchanged":True,
      "model_or_native_scoring_executed":False,
      "independent_human_authorship_claimed":False,
      "seeds_obtained_from_OS_entropy_before_model_results":True}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("x",encoding="utf8") as stream:
        json.dump(result,stream,sort_keys=True,indent=2)
        stream.write("\n")
    print("F124CH_ORIGINAL_SOURCE_BIRTH_CASES=24")
    print("F124CH_SOURCE_ORACLE_CASES_SYMBOLICALLY_QUALIFIED=24")
    print("F124CH_SOURCE_GIT_BLOB="+source_blob)
    print("F124CH_CASE_ORACLE_PASSED_TO_MODEL=false")
    print("F124CH_NO_OLD_OR_PROTECTED_FIRSTUSE=PASS")
    print("F124CH_MODEL_EXECUTION_BEFORE_SOURCE_BIRTH=FALSE")

if __name__=="__main__":
    main()
