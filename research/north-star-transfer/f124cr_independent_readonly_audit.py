"""F124-CR separately hosted READ-ONLY original provider/source/science audit.

The auditor never calls a learner, imports the source generator, recreates
seeds, alters cases or publishes private ground truth. Every source ID and
original native/OS receipt is independently checked against provider jobs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request

def need(ok,msg):
    if not ok:raise RuntimeError("F124CR_AUDIT_"+msg)

def sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def provider(url):
    token=os.environ.get("GITHUB_TOKEN")
    need(bool(token),"READONLY_PROVIDER_TOKEN_REQUIRED")
    request=urllib.request.Request(url,headers={
      "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
      "X-GitHub-Api-Version":"2022-11-28"})
    with urllib.request.urlopen(request,timeout=30) as response:
        return json.loads(response.read())

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--birth",type=Path,required=True)
    p.add_argument("--measurement",type=Path,required=True)
    p.add_argument("--head",required=True)
    p.add_argument("--out",type=Path,required=True)
    x=p.parse_args()
    sealed=json.loads((x.birth/"sealed-private-birth.json").read_text())
    public=json.loads((x.birth/"birth-public-manifest.json").read_text())
    measured=json.loads((x.measurement/"original-complete-evidence.json").read_text())
    summary=json.loads((x.measurement/"original-public-summary.json").read_text())
    journal=[json.loads(line) for line in
             (x.measurement/"original-append-journal.jsonl").read_text().splitlines()]
    need(sealed["schema"]=="mass.f124cr.original-private-JK-24-birth.v1"
         and public["schema"]=="mass.f124cr.original-public-firstuse-manifest.v1"
         and measured["schema"]=="mass.f124cr.original-complete-public-native-evidence.v1"
         and sealed["original_git_head"]==public["original_git_head"]==
             measured["original_git_head"]==summary["original_git_head"]==x.head,
         "ALL_ORIGINAL_PROVIDER_SOURCE_IDENTITY")
    need(sha(sealed)==public["sealed_private_sha256"]
         and sha(public)==measured["original_public_birth_manifest_sha256"]==
             summary["original_public_manifest_sha256"]
         and sha(measured)==summary["original_complete_evidence_sha256"],
         "PRIVATE_PUBLIC_AND_ORIGINAL_MEASUREMENTS_CRYPTOGRAPHIC_BINDING")
    ids=list(range(934000,934012))+list(range(935000,935012))
    cases=sealed["cases"];roster=public["original_roster"]
    need(len(cases)==len(roster)==24
         and [c["case_id"] for c in cases]==ids
         and [r["id"] for r in roster]==ids
         and sealed["private_source_creation_precedes_any_scoring"]
         and sealed["no_learner_called_in_birth"]
         and not sealed["protected_source_used"]
         and public["public_packets_do_not_contain_seeds_or_oracle"]
         and not public["protected_source_opened"],
         "EXACT_FIRST_USE_BORN_BEFORE_ANY_SCORING")
    for case,row in zip(cases,roster):
        path=x.birth/"public-cases"/("case-"+str(row["id"])+".json")
        published=json.loads(path.read_text())
        need(published==case["public_task"]
             and sha(published)==row["public_sha256"]==case["public_sha256"]
             and case["oracle_positive"] and not case["oracle_negative"]
             and not case["old_924_through_933_cases_used"]
             and not case["protected_cohort_opened"],
             "SOURCE_ORACLE_PUBLIC_FIRSTUSE_BOUNDARY")
    need(len(list((x.birth/"public-cases").glob("*.json")))==24,
         "NO_OUTCOME_DEPENDENT_SOURCE_FILTER")
    pre=measured["original_72_native_preflights"]
    costs=measured["original_360_whole_OS_process_samples"]
    need(len(pre)==72 and len(costs)==360 and len(journal)==432
         and summary["original_native_preflights"]==72
         and summary["original_whole_OS_samples"]==360
         and summary["original_append_receipts"]==432,
         "ORIGINAL_COMPLETE_NATIVE_AND_OS_OBSERVATIONS")
    need(all(q["schema"]=="mass.f124cr.original-append-only-os-receipt.v1"
             for q in journal),"ORIGINAL_APPEND_ONLY_SCHEMA")
    expected=[{"preflight":True,"reading":o} for o in pre]
    expected += [{"preflight":False,"repetition":i%5,"reading":o}
                 for i,o in enumerate(costs)]
    need([q["observation"] for q in journal]==expected,
         "ALL_432_ORIGINAL_APPEND_RECEIPTS_UNCHANGED_IN_ORDER")
    arms=("CANDIDATE","TRAINED_CONTROL","PERSISTENCE_REFERENCE")
    source_by_id={r["id"]:r["public_sha256"] for r in roster}
    keyed={(r["case_id"],r["arm"]):r for r in pre}
    need(len(keyed)==72 and all((case,arm) in keyed for case in ids for arm in arms),
         "COMPLETE_72_CASE_ARM_IDENTITY")
    pairs={"J":{"candidate":0,"trained":0},"K":{"candidate":0,"trained":0}}
    parity=0;hard_fp=[];resource_ineligible=[]
    for case in ids:
        candidate,control,reference=(keyed[case,k] for k in arms)
        need(candidate["public_task_sha256"]==control["public_task_sha256"]==
             reference["public_task_sha256"]==source_by_id[case]
             and candidate["native_public_input_sha256"]==
             control["native_public_input_sha256"]==
             reference["native_public_input_sha256"],
             "IDENTICAL_PUBLIC_NATIVE_INPUT_GRAPH_PER_CASE")
        eligible=(candidate["natural_model_admission"] and
             control["natural_model_admission"] and
             candidate["native_graph_calls"]==control["native_graph_calls"]==2 and
             candidate["native_event_transition_calls"]==
             control["native_event_transition_calls"]==
             candidate["expected_complete_transition_calls"]==
             control["expected_complete_transition_calls"])
        parity+=int(eligible)
        if not eligible:resource_ineligible.append(case)
        if candidate["hard_false_positive"]:hard_fp.append(case)
        fam="J" if case<935000 else "K"
        pairs[fam]["candidate"]+=int(candidate["correct_paired_causal_task"])
        pairs[fam]["trained"]+=int(control["correct_paired_causal_task"])
        for arm in arms:
            head=keyed[case,arm]
            subset=[s for s in costs if s["case_id"]==case and s["arm"]==arm]
            need(len(subset)==5 and all(
               s["public_task_sha256"]==head["public_task_sha256"]
               and s["native_public_input_sha256"]==head["native_public_input_sha256"]
               and s["native_graph_calls"]==head["native_graph_calls"]
               and s["natural_model_admission"]==head["natural_model_admission"]
               and s["native_event_transition_calls"]==head["native_event_transition_calls"]
               and s["correct_paired_causal_task"]==head["correct_paired_causal_task"]
               and s["OS_measurement_includes_boot_import_fit_native_scoring"]
               and s["complete_OS_CPU_ns"]>0
               and s["complete_OS_peak_RSS_bytes"]>0 for s in subset),
               "REAL_WHOLE_PROCESS_CPU_PEAK_RSS_AND_NATIVE_STATE")
    need(parity==summary["resource_parity_eligible_cases"]
         and all(summary["family_correct_pairs"][fam]["candidate_pairs"]==pairs[fam]["candidate"]
              and summary["family_correct_pairs"][fam]["strongest_trained_pairs"]==pairs[fam]["trained"]
              for fam in pairs),"INDEPENDENT_OUTCOME_AND_RESOURCE_PARITY_COUNTS")
    repo=os.environ.get("GITHUB_REPOSITORY")
    run=os.environ.get("GITHUB_RUN_ID")
    need(repo=="spoonman136668-ai/FORGE" and bool(run),"REAL_HOSTED_PROVIDER")
    base="https://api.github.com/repos/"+repo+"/actions/runs/"+run
    provider_run=provider(base)
    jobs=provider(base+"/jobs?per_page=100")["jobs"]
    need(provider_run["head_sha"]==x.head and provider_run["run_attempt"]==1,
         "ORIGINAL_RUN_SHA_AND_NO_FIRST_USE_RETRY")
    def success(name):
        entries=[j for j in jobs if j["name"]==name]
        return len(entries)==1 and entries[0]["conclusion"]=="success"
    need(success("source-first-original-JK") and
         success("blinded-original-complete-measurements"),
         "ORIGINAL_PROVIDER_SOURCE_BIRTH_BEFORE_EVALUATION")
    report={"schema":"mass.f124cr.independent-safe-original-custody.v1",
      "provider_run_id":int(run),"original_head":x.head,
      "source_job_success":True,"evaluation_job_success":True,
      "original_firstuse_count":24,"native_preflights":72,
      "whole_OS_CPU_RSS_samples":360,"original_append_receipts":432,
      "original_artifact_manifest_sha256":sha(public),
      "original_evidence_sha256":sha(measured),
      "private_source_digest_only":sha(sealed),
      "original_public_input_digests":[x["public_sha256"] for x in roster],
      "original_independently_counted_family_pairs":pairs,
      "native_equal_work_eligible_cases":parity,
      "resource_unqualified_case_ids":resource_ineligible,
      "observed_hard_false_positive_case_ids":hard_fp,
      "source_seed_model_oracle_not_executed_or_released":True,
      "historical_source_reused":False,
      "protected_firstuse_opened":False,
      "scientific_success_accepted":False,
      "original_independent_readonly_reconciliation":True}
    x.out.mkdir(parents=True,exist_ok=False)
    with (x.out/"original-safe-audit.json").open("x") as fp:
        json.dump(report,fp,sort_keys=True,indent=2);fp.write("\n")
    print("F124CR_ORIGINAL_FIRSTUSE_CUSTODY=PASS")
    print("F124CR_SOURCE_BIRTH_AND_SCORING_PROVENANCE=PASS")
    print("F124CR_ALL_432_OS_RECEIPTS=PASS")
    print("F124CR_ORIGINAL_PAIRS="+json.dumps(pairs,sort_keys=True))
    print("F124CR_ELIGIBLE_EQUAL_NATIVE_WORK="+str(parity))
    print("F124CR_SCIENCE_ACCEPTED=FALSE")

if __name__=="__main__":main()
