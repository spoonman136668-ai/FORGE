"""Independent read-only F124-CO original custody audit.

Reads original provider artifacts in a separate hosted job. Never imports
source/oracle/model/evaluator, never regenerates private seeds, never replays
any original scientific case or emits private packets in logs/artifacts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request

def need(ok,why):
    if not ok:raise RuntimeError("F124CO_AUDIT_"+why)

def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def provider(url):
    token=os.environ.get("GITHUB_TOKEN")
    need(bool(token),"REQUIRES_GITHUB_ACTIONS_READ_TOKEN")
    req=urllib.request.Request(url,headers={
       "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
       "X-GitHub-Api-Version":"2022-11-28"})
    with urllib.request.urlopen(req,timeout=30) as resp:
        return json.loads(resp.read())

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--birth-dir",type=Path,required=True)
    p.add_argument("--result-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--head",required=True)
    a=p.parse_args()
    private=json.loads((a.birth_dir/"sealed-private-birth.json").read_text())
    public=json.loads((a.birth_dir/"birth-public-manifest.json").read_text())
    observed=json.loads((a.result_dir/"original-full-evidence.json").read_text())
    summary=json.loads((a.result_dir/"original-public-summary.json").read_text())
    journal=[json.loads(x) for x in
             (a.result_dir/"original-append-only.jsonl").read_text().splitlines()]
    need(public["source_firstuse_git_head"]==a.head==
         private["source_firstuse_git_head"]==
         observed["source_firstuse_git_head"]==
         summary["source_firstuse_git_head"],"ORIGINAL_ONE_EXACT_HEAD")
    need(private["schema"]=="mass.f124co.original-24-private-source-birth.v1"
         and private["source_birth_before_any_model_scoring"]
         and not private["protected_cohorts_opened"]
         and public["no_private_seed_or_oracle_in_public_case"],
         "ORIGINAL_PRIVATE_BIRTH_CUSTODY")
    need(sha(private)==public["private_custody_sha256"]
         and sha(public)==observed["birth_manifest_sha256"]==
             summary["birth_manifest_sha256"],
         "ORIGINAL_ARCHIVE_SHA256_OR_REDACTION")
    ids=list(range(932000,932012))+list(range(933000,933012))
    records=private["cases"]; roster=public["original_public_roster"]
    need(len(records)==len(roster)==24
         and [r["case_id"] for r in records]==ids
         and [x["id"] for x in roster]==ids,
         "ORIGINAL_EXACT_FIRSTUSE_ROSTER")
    for record,row in zip(records,roster):
        source=json.loads((a.birth_dir/"public-cases"/("case-"+str(row["id"])+".json")).read_text())
        need(source==record["public_task"] and
             sha(source)==row["public_sha256"]==record["public_sha256"]
             and record["oracle"]=={"positive":True,"hard_negative":False}
             and not record["old_924_931_sources_used"]
             and not record["protected_cohort_opened"],
             "ORIGINAL_NEW_SOURCE_AND_BLIND_FORWARDING")
    need(len(list((a.birth_dir/"public-cases").glob("case-*.json")))==24,
         "NO_SOURCE_SELECTION")
    pre=observed["original_72_preflights"]
    cost=observed["original_360_whole_process_measurements"]
    need(len(pre)==72 and len(cost)==360 and len(journal)==432
         and summary["append_only_original_receipt_count"]==432
         and observed["no_private_seed_or_oracle_imported"]
         and not observed["science_accepted"] and not summary["science_accepted"],
         "ALL_ORIGINAL_PROCESS_RECEIPTS")
    need(sha(observed)==summary["original_full_evidence_sha256"],
         "SUMMARY_ORIGINAL_EVIDENCE_SHA256")
    need(all(row["schema"]=="mass.f124cn.append-only-original-OS-measurement.v1"
             for row in journal),"APPEND_ONLY_EVIDENCE_SCHEMA")
    expect=([{"preflight":True,"reading":e} for e in pre]+
             [{"preflight":False,"repetition":i%5,"reading":e}
              for i,e in enumerate(cost)])
    # Original evaluator emits all preflights first, then all repeated processes.
    need([j["observation"] for j in journal]==expect,
         "EXACT_ORDERED_432_ORIGINAL_APPEND_RECEIPTS")
    pre_by={(p["case_id"],p["arm"]):p for p in pre}
    allowed=("CANDIDATE","TRAINED_CONTROL","PERSISTENCE_REFERENCE")
    need(len(pre_by)==72 and all(
        (case,arm) in pre_by for case in ids for arm in allowed),
        "ORIGINAL_EACH_ARM_EACH_CASE_PREFLIGHT")
    for case in ids:
        current=[pre_by[case,arm] for arm in allowed]
        source=next(r["public_sha256"] for r in roster if r["id"]==case)
        need(len({r["public_task_sha256"] for r in current})==1
             and current[0]["public_task_sha256"]==source
             and len({json.dumps(r["graph_sha256"],sort_keys=True) for r in current})==1,
             "ALL_ARMS_SAME_PUBLIC_GRAPH")
        for arm in allowed:
            p=pre_by[case,arm]
            samples=[x for x in cost if x["case_id"]==case and x["arm"]==arm]
            need(len(samples)==5 and all(x["public_task_sha256"]==source
                    and x["natural_admission"]==p["natural_admission"]
                    and x["native_event_transition_calls"]==p["native_event_transition_calls"]
                    and x["correct_pair"]==p["correct_pair"]
                    and x["whole_OS_boot_import_train_score_included"]
                    and x["whole_OS_process_CPU_ns"]>0
                    and x["whole_OS_process_peak_RSS_bytes"]>0
                    for x in samples),"ORIGINAL_NATIVE_AND_OS_COST_COHERENCE")
    # Separately corroborate provider run and job names/status, not just files.
    repo=os.environ.get("GITHUB_REPOSITORY")
    run=os.environ.get("GITHUB_RUN_ID")
    need(repo=="spoonman136668-ai/FORGE" and bool(run),"HOSTED_PROVIDER_IDENTITY")
    base="https://api.github.com/repos/"+repo+"/actions/runs/"+run
    runstate=provider(base)
    jobs=provider(base+"/jobs?per_page=100")["jobs"]
    need(runstate["head_sha"]==a.head and runstate["run_attempt"]==1,
         "FIRST_PROVIDER_SHA_SINGLE_ATTEMPT")
    def ok_job(name):
        matches=[j for j in jobs if j["name"]==name]
        return len(matches)==1 and matches[0]["conclusion"]=="success"
    need(ok_job("original-firstuse-source-birth") and
         ok_job("original-public-blinded-evaluation"),
         "BIRTH_FIRST_THEN_EVALUATOR_COMPLETED_ON_PROVIDER")
    digest_safe={
      "schema":"mass.f124co.independent-original-readonly-custody.v1",
      "provider_run":int(run),
      "original_head":a.head,
      "original_birth_job":"success",
      "original_evaluation_job":"success",
      "source_birth_before_scoring_verified":True,
      "source_case_count":24,
      "original_public_case_shas":[x["public_sha256"] for x in roster],
      "original_72_native_preflights":72,
      "original_360_full_OS_samples":360,
      "original_ordered_append_receipts":432,
      "original_full_evidence_sha256":sha(observed),
      "original_public_manifest_sha256":sha(public),
      "private_custody_digest_only":sha(private),
      "original_scientific_gain_by_family":summary["G_and_H_net_gains"],
      "original_scientific_admission_failures":summary["original_admission_failures"],
      "original_scientific_criteria_met":summary["scientific_development_criteria_met"],
      "private_source_oracle_seed_not_retained_in_audit":True,
      "source_or_model_reexecution":False,
      "protected_firstuse_opened":False,
      "independent_review_completed":True,
      "science_accepted":False}
    a.out.mkdir(parents=True,exist_ok=False)
    with (a.out/"independent-safe-custody.json").open("x",encoding="utf8") as f:
        json.dump(digest_safe,f,sort_keys=True,indent=2);f.write("\n")
    print("F124CO_ORIGINAL_PROVIDER_AUTHENTIC=PASS")
    print("F124CO_FIRSTUSE_ORIGINAL_ROSTER=24")
    print("F124CO_ORIGINAL_NATIVE_PROCESS_OBSERVATIONS=432")
    print("F124CO_INDEPENDENT_READONLY_CUSTODY=PASS")
    print("F124CO_PRIVATE_SOURCE_LOGGED=FALSE")
    print("F124CO_SCIENCE_ACCEPTED=FALSE")

if __name__=="__main__":main()
