"""F124-CU separate original READONLY scientific first-use custody verifier.

Does not import/run source, model, or original evaluator. Checks GitHub
provider authentic job identity, original SHA, immutable public/private
hashes, every original case and 432 whole-OS append-only observations.
Publishes only redacted digests and aggregate findings, never seeds/oracle.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request

IDS=tuple(range(936000,936012))+tuple(range(937000,937012))
ARMS=("CANDIDATE","TRAINED_CONTROL","PERSISTENCE_REFERENCE")

def need(ok,msg):
    if not ok:raise RuntimeError("F124CU_CUSTODY_"+msg)

def sha(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def github(url):
    token=os.environ.get("GITHUB_TOKEN")
    need(bool(token),"PROVIDER_READONLY_TOKEN")
    req=urllib.request.Request(url,headers={
      "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
      "X-GitHub-Api-Version":"2022-11-28"})
    with urllib.request.urlopen(req,timeout=30) as f:
        return json.loads(f.read())

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--birth",required=True,type=Path)
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--head",required=True)
    p.add_argument("--out",required=True,type=Path)
    x=p.parse_args()
    private=json.loads((x.birth/"sealed-private-original.json").read_text())
    manifest=json.loads((x.birth/"original-public-manifest.json").read_text())
    original=json.loads((x.evidence/"original-full-evidence.json").read_text())
    summary=json.loads((x.evidence/"original-public-summary.json").read_text())
    receipts=[json.loads(y) for y in
       (x.evidence/"original-append-only-receipts.jsonl").read_text().splitlines()]
    need(private["schema"]=="mass.f124cu.original-private-sequential-birth.v1"
         and manifest["schema"]=="mass.f124cu.original-public-sequential-birth.v1"
         and original["schema"]=="mass.f124cu.original-complete-sequential-BPTT-study.v1"
         and x.head==private["head"]==manifest["head"]==
             original["original_git_head"]==summary["head"],
         "ORIGINAL_GITHUB_SHA_BOUND_TO_ALL_SOURCES")
    need(private["original_source_birth_precedes_evaluation"] and
         private["no_candidate_or_control_in_birth"]
         and not private["protected_cohort_opened"]
         and manifest["no_private_seed_oracle_in_public_inputs"]
         and manifest["source_born_before_model_training"]
         and not manifest["protected_firstuse"]
         and not original["protected_firstuse"],
         "INDEPENDENT_ORIGINAL_SOURCE_ORACLE_ISOLATION")
    need(sha(private)==manifest["private_custody_sha256"]
         and sha(manifest)==original["original_public_birth_manifest_sha256"]==
             summary["original_public_manifest_sha256"]
         and sha(original)==summary["original_evidence_sha256"],
         "ALL_FIRSTUSE_SOURCE_AND_MEASUREMENT_CONTENT_IDENTITIES")
    cases=private["cases"];roster=manifest["original_roster"]
    need(len(cases)==len(roster)==24 and
         [z["case_id"] for z in cases]==list(IDS) and
         [z["id"] for z in roster]==list(IDS),
         "NO_DROPPED_OR_REPLACED_FIRSTUSE_CASE")
    for hidden,published in zip(cases,roster):
        file=x.birth/"public-cases"/("case-"+str(published["id"])+".json")
        public=json.loads(file.read_text())
        need(public==hidden["public_task"] and
             sha(public)==published["public_sha256"]==hidden["public_sha256"]
             and hidden["symbolic_oracle"]=={"positive":True,"hard_negative":False}
             and hidden["previous_924_through_935_source_reused"] is False
             and hidden["protected_source_opened"] is False,
             "ORIGINAL_PRIVATE_ORACLE_AND_PUBLIC_TASK_PROVENANCE")
    need(len(list((x.birth/"public-cases").glob("*.json")))==24,
         "SOURCE_ORIGINAL_ROSTER_IMMUTABLE")
    pre=original["original_72_native_preflights"]
    samples=original["original_360_full_process_CPU_RSS_samples"]
    need(len(pre)==72 and len(samples)==360 and len(receipts)==432
         and summary["native_preflights"]==72 and
         summary["complete_OS_samples"]==360 and
         summary["append_only_receipts"]==432 and
         original["source_private_oracle_not_passed_to_learner"] and
         not original["scientific_acceptance"],
         "ALL_ORIGINAL_COMPLETE_PROCESS_RECEIPTS")
    need(all(r["schema"]=="mass.f124cu.original-appended-whole-OS-process.v1"
             for r in receipts),"APPEND_ONLY_SCHEMA")
    expected=[{"preflight":True,"reading":z} for z in pre]
    expected += [{"preflight":False,"repetition":i%5,"reading":z}
                 for i,z in enumerate(samples)]
    need([r["observation"] for r in receipts]==expected,
         "EVERY_ORIGINAL_RECEIPT_ORDERED_AND_CONSISTENT")
    keyed={(v["case_id"],v["arm"]):v for v in pre}
    need(len(keyed)==72 and all((i,arm) in keyed for i in IDS for arm in ARMS),
         "ALL_CASE_ARMS_INDEPENDENTLY_PRESENT")
    families={"L":{"candidate_pairs":0,"control_pairs":0},
              "M":{"candidate_pairs":0,"control_pairs":0}}
    resource_eligible=[]
    hard_fp=[]
    for case in IDS:
        a,c,ref=[keyed[case,k] for k in ARMS]
        need(a["public_case_sha256"]==c["public_case_sha256"]==
             ref["public_case_sha256"] and
             a["identical_native_public_graph_hashes"]==
             c["identical_native_public_graph_hashes"]==
             ref["identical_native_public_graph_hashes"] and
             a["identical_train_FIT_sha256"]==c["identical_train_FIT_sha256"] and
             a["identical_veto_CHECK_sha256"]==c["identical_veto_CHECK_sha256"],
             "SAME_PUBLIC_SOURCE_NATIVE_TRAINING_AND_GRAPH_IDENTITIES")
        eligible=bool(a["natural_trained_admission"] and
            c["natural_trained_admission"] and
            a["native_complete_graph_calls"]==c["native_complete_graph_calls"]==2 and
            a["native_event_count"]==c["native_event_count"]==16)
        if eligible:resource_eligible.append(case)
        if a["hard_false_positive"]:hard_fp.append(case)
        family="L" if case<937000 else "M"
        families[family]["candidate_pairs"]+=int(a["correct_positive_and_hard_negative"])
        families[family]["control_pairs"]+=int(c["correct_positive_and_hard_negative"])
        for arm in ARMS:
            p=keyed[case,arm]
            group=[s for s in samples if s["case_id"]==case and s["arm"]==arm]
            need(len(group)==5 and all(
               z["public_case_sha256"]==p["public_case_sha256"] and
               z["identical_native_public_graph_hashes"]==
                 p["identical_native_public_graph_hashes"] and
               z["natural_trained_admission"]==p["natural_trained_admission"] and
               z["native_event_count"]==p["native_event_count"] and
               z["correct_positive_and_hard_negative"]==
                 p["correct_positive_and_hard_negative"] and
               z["OS_measurement_includes_Python_start_NumPy_import_full_BPTT_and_scoring"] and
               z["full_OS_CPU_ns"]>0 and z["full_OS_peak_RSS_bytes"]>0
               for z in group),"FIVE_REAL_OS_PROCESS_COST_SAMPLES_PER_ARM_CASE")
    need(len(resource_eligible)==summary["native_equal_work_cases"] and
         all(families[family]["candidate_pairs"]==summary["family_pairs"][family]["candidate_correct_pairs"]
         and families[family]["control_pairs"]==summary["family_pairs"][family]["fully_trained_control_correct_pairs"]
         for family in families),"INDEPENDENT_SCIENCE_AND_COST_ELIGIBILITY_RECOUNT")
    repo=os.environ.get("GITHUB_REPOSITORY");run=os.environ.get("GITHUB_RUN_ID")
    need(repo=="spoonman136668-ai/FORGE" and bool(run),"ORIGINAL_GITHUB_PROVIDER_REQUIRED")
    base="https://api.github.com/repos/"+repo+"/actions/runs/"+run
    provider=github(base);jobs=github(base+"/jobs?per_page=100")["jobs"]
    need(provider["head_sha"]==x.head and provider["run_attempt"]==1,
         "SOURCE_FIRSTUSE_RUN_CANNOT_BE_RETRIED")
    def completed(name):
        hits=[j for j in jobs if j["name"]==name]
        return len(hits)==1 and hits[0]["conclusion"]=="success"
    need(completed("original-only-LM-source-birth")
         and completed("original-public-BPTT-native-evaluation"),
         "HOSTED_ORIGINAL_SOURCE_THEN_EVALUATION_JOB_COMPLETED")
    safe={"schema":"mass.f124cu.independent-original-sequence-custody.v1",
      "run_id":int(run),"original_head":x.head,"original_case_count":24,
      "original_birth_job_success":True,"original_blinded_evaluation_job_success":True,
      "native_preflights":72,"full_OS_CPU_RSS_samples":360,
      "original_append_receipts":432,
      "original_public_birth_manifest_sha256":sha(manifest),
      "original_complete_evidence_sha256":sha(original),
      "original_private_custody_digest_only":sha(private),
      "original_public_case_sha256":[q["public_sha256"] for q in roster],
      "independent_original_paired_results":families,
      "natural_equal_native_work_eligible_case_ids":resource_eligible,
      "hard_false_positive_case_ids":hard_fp,
      "original_firstuse_provider_reconciled":True,
      "no_source_or_model_reexecution_in_auditor":True,
      "private_seeds_and_symbolic_oracle_not_released_in_audit":True,
      "protected_firstuse":False,"scientific_success_accepted":False}
    x.out.mkdir(parents=True,exist_ok=False)
    with (x.out/"independent-safe-custody.json").open("x") as f:
        json.dump(safe,f,sort_keys=True,indent=2);f.write("\n")
    print("F124CU_INDEPENDENT_ORIGINAL_FIRSTUSE_CUSTODY=PASS")
    print("F124CU_ALL_432_NATIVE_AND_OS_RECEIPTS=PASS")
    print("F124CU_SOURCE_CUSTODY_AND_PRIVATE_REDACTION=PASS")
    print("F124CU_RECOUNTED_ORIGINAL_PAIRS="+json.dumps(families,sort_keys=True))
    print("F124CU_ELIGIBLE_EQUAL_NATIVE_WORK="+str(len(resource_eligible)))
    print("F124CU_SCIENCE_ACCEPTED=FALSE")

if __name__=="__main__":main()
