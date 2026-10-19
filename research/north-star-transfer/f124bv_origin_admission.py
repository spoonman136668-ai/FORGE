"""F124-BV independent source birth custody + frozen scientific gate.

This module is strictly DATA ONLY. It never imports, executes, compiles or
materializes external source generators. Original GitHub provider JSON must
be supplied by a separate read-only step. Signatures and distinct providers
authenticate claimed origins; these alone cannot *prove* semantic novelty.

Any first scientific use requires a separately admitted, exact-source
prospective runner; this file does not issue or schedule first use.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from statistics import median

PROTOCOL_BLOB="5a509951aacb3de7cbec0c0e895d3b9c8ce4dce5"
PROTOCOL_COMMIT="be7e9c2b91970ec2585a499a77e7b3369617fc1a"
ORIGINAL_PROVIDER_FROZEN_AT="2026-10-19T08:09:59Z"
FORGE_OWNER="spoonman136668-ai"
EXPECTED={"A":{"fit":list(range(924000,924012)),
               "holdout":list(range(924100,924228))},
          "B":{"fit":list(range(925000,925012)),
               "holdout":list(range(925100,925228))}}
PREVIOUS_BLOBS={
    "91ad02a4f3893e3537dddc2390666e3c2d2db5d1",
    "0122190aa3a0972ffb4a709bc1bdd8179c8ba6c7",
    "94d2ae8266da792d254ac54baf3056bbd9b49412",
    "c5c2ee4fd88748f955af758889f83709fde3308d",
    "78646cd8b4e0a13a95e3f18df043b7ba1277d696",
    "4c037f55e220b22783d89e3e566b951e0eff618e",
    "b934ce6962dc9a1526d82dbdc2736d210f2db57d"
}
SHA40=re.compile(r"^[a-f0-9]{40}$")
PATH=re.compile(r"^[a-zA-Z0-9_./-]+$")
NAME=re.compile(r"^[a-zA-Z0-9_-]+$")
BANNED_IMPORTS=("f124","forge","nativeevidence","research","optimizer")
BANNED_CALLS={"eval","exec","compile","__import__"}


def need(ok,label):
    if not ok:
        raise ValueError("F124BV_FAIL_CLOSED_"+label)


def git_blob(data):
    return hashlib.sha1(
        b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def is_original_path(path):
    return (type(path) is str and bool(PATH.fullmatch(path))
            and not path.startswith(("/","."))
            and ".." not in path.split("/") and "//" not in path
            and path.endswith((".py",".json")))


def fetch_bytes(git_blob_json):
    need(type(git_blob_json) is dict
         and git_blob_json.get("encoding")=="base64"
         and type(git_blob_json.get("content")) is str
         and bool(SHA40.fullmatch(git_blob_json.get("sha",""))),
         "PROVIDER_ORIGINAL_BLOB_JSON")
    try:
        raw=base64.b64decode(git_blob_json["content"],validate=False)
    except Exception as exc:
        raise ValueError("F124BV_FAIL_CLOSED_BLOB_BASE64") from exc
    need(git_blob(raw)==git_blob_json["sha"],
         "ORIGINAL_GIT_BLOB_CONTENT_HASH")
    return raw


def static_source_boundaries(raw):
    try:
        root=ast.parse(raw.decode("utf8"))
    except (UnicodeError,SyntaxError) as exc:
        raise ValueError("F124BV_FAIL_CLOSED_SOURCE_NOT_STATIC_PYTHON") from exc
    imports=set()
    for n in ast.walk(root):
        if isinstance(n,ast.Import):
            imports.update(item.name for item in n.names)
        elif isinstance(n,ast.ImportFrom):
            imports.add(n.module or "")
        elif isinstance(n,ast.Call) and isinstance(n.func,ast.Name):
            need(n.func.id not in BANNED_CALLS,"DYNAMIC_SOURCE_EXECUTION")
    need(not any(i.lower().startswith(BANNED_IMPORTS) for i in imports),
         "INDEPENDENT_SOURCE_MUST_NOT_IMPORT_FROZEN_MODEL")
    return sorted(imports)


def _parsed_time(date):
    need(type(date) is str,"BIRTH_TIMESTAMP_MISSING")
    try:
        value=datetime.fromisoformat(date.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("F124BV_FAIL_CLOSED_BIRTH_TIMESTAMP_INVALID") from exc
    need(value.tzinfo is not None,"OFFSET_REQUIRED")
    return value.astimezone(timezone.utc)


def original_witness_one(source,witness):
    need(type(source) is dict and type(witness) is dict,
         "EXTERNAL_PROVIDER_RECEIPTS_MISSING")
    label=source.get("family")
    need(label in EXPECTED,"EXACT_TWO_FAMILY_NAMES")
    need(source.get("schema")=="mass.f124bv.external-birth-reference.v1",
         "ORIGINAL_SOURCE_MANIFEST_SCHEMA")
    need(source.get("frozen_protocol_commit")==PROTOCOL_COMMIT
         and source.get("frozen_protocol_blob")==PROTOCOL_BLOB,
         "PRECODE_FROZEN_PROTOCOL_BINDING")
    need(source.get("fit_case_ids")==EXPECTED[label]["fit"]
         and source.get("sealed_holdout_ids")==EXPECTED[label]["holdout"],
         "FROZEN_CASE_IDS_NO_REPLACEMENT")
    repo=source.get("repository")
    need(type(repo) is str and repo.count("/")==1
         and all(NAME.fullmatch(t) for t in repo.split("/"))
         and repo.split("/")[0].lower()!=FORGE_OWNER,
         "DISTINCT_EXTERNAL_SOURCE_PROVIDER")
    creator=source.get("creator_login")
    need(type(creator) is str and bool(NAME.fullmatch(creator))
         and creator.lower()!=FORGE_OWNER,
         "EXTERNAL_CREATOR_NOT_FROZEN_MODEL_OWNER")
    sha=source.get("commit_sha")
    need(type(sha) is str and bool(SHA40.fullmatch(sha))
         and witness.get("repo")==repo
         and witness.get("commit_sha")==sha
         and witness.get("provider_api_authenticated") is True,
         "GITHUB_ORIGINAL_IMMUTABLE_IDENTITY")
    commit=witness.get("git_commit")
    root=witness.get("rest_commit")
    need(type(commit) is dict and type(root) is dict
         and commit.get("sha")==sha and root.get("sha")==sha
         and len(commit.get("parents",[]))>=1
         and commit.get("verification",{}).get("verified") is True
         and root.get("author",{}).get("login")==creator,
         "PROVIDER_VERIFIED_SIGNATURE_AND_AUTHOR")
    born_at=_parsed_time(commit.get("author",{}).get("date"))
    need(source.get("precode_frozen_at")==ORIGINAL_PROVIDER_FROZEN_AT,
         "REQUIRE_PROVIDER_ACTUAL_PRECODE_TIMESTAMP_NOT_SELF_DECLARED")
    freeze_at=_parsed_time(ORIGINAL_PROVIDER_FROZEN_AT)
    need(born_at>freeze_at,"SIGNED_ORIGINAL_BIRTH_AFTER_FREEZE")
    need(source.get("future_firstuse_timestamp") is None,
         "NO_FABRICATED_FUTURE_FIRSTUSE")
    # Blob existence by itself is insufficient. The original Git tree
    # MUST contain the exact attestation, oracle, and generator path/blob.
    tree=witness.get("original_tree")
    need(type(tree) is dict
         and type(commit.get("tree")) is dict
         and tree.get("sha")==commit["tree"].get("sha")
         and tree.get("truncated") is False
         and type(tree.get("tree")) is list,
         "GITHUB_ORIGINAL_COMMIT_TREE_BOUNDARY")
    files=source.get("files")
    witness_files=witness.get("original_blobs")
    need(type(files) is dict and type(witness_files) is dict
         and set(files)==set(witness_files)=={"source","oracle","attestation"},
         "THREE_ORIGINAL_PROVIDER_FILES")
    actual={}
    for label_name in ("source","oracle","attestation"):
        obj=files[label_name]
        need(type(obj) is dict and is_original_path(obj.get("path"))
             and bool(SHA40.fullmatch(obj.get("blob_sha",""))),
             "FILE_NAME_AND_GIT_OBJECT_"+label_name)
        matches=[entry for entry in tree["tree"]
                 if entry.get("path")==obj["path"]]
        need(len(matches)==1 and matches[0].get("type")=="blob"
             and matches[0].get("sha")==obj["blob_sha"],
             "IMMUTABLE_COMMIT_TREE_CONTAINS_SIGNED_SOURCE_"+label_name)
        proof=witness_files[label_name]
        need(type(proof) is dict and proof.get("path")==obj["path"],
             "PATH_CUSTODY_"+label_name)
        raw=fetch_bytes(proof["blob"])
        need(proof["blob"]["sha"]==obj["blob_sha"]
             and obj["blob_sha"] not in PREVIOUS_BLOBS,
             "REUSED_OR_WRONG_SOURCE_BLOB_"+label_name)
        actual[label_name]=raw
    need(files["source"]["path"].endswith(".py")
         and files["oracle"]["path"].endswith(".py")
         and files["attestation"]["path"].endswith(".json"),
         "SIGNED_SOURCE_ORACLE_AND_ATTESTATION_FORMAT")
    source_imports=static_source_boundaries(actual["source"])
    oracle_imports=static_source_boundaries(actual["oracle"])
    try:
        att=json.loads(actual["attestation"].decode("utf8"))
    except (ValueError,UnicodeError) as exc:
        raise ValueError("F124BV_FAIL_CLOSED_ATTESTATION_JSON") from exc
    need(att.get("schema")=="mass.f124bv.source-independence-attestation.v1"
         and att.get("frozen_protocol_blob")==PROTOCOL_BLOB
         and att.get("family")==label
         and att.get("creator_login")==creator
         and att.get("independently_originated") is True
         and att.get("no_model_access_or_copied_source") is True
         and att.get("no_prior_case_or_seed_reuse") is True
         and att.get("no_protected_cohort_firstuse") is True
         and att.get("source_generates_only_development_when_admitted") is True,
         "SIGNED_SEPARATE_SCIENTIFIC_ORIGINATION_ATTESTATION")
    need(type(att.get("novelty_claim")) is str
         and len(att["novelty_claim"].strip())>=40,
         "MEANINGFUL_SPECIFIC_NOVEL_CAUSAL_GRAMMAR")
    return {
        "family":label,"creator":creator,"repo":repo,
        "commit_sha":sha,"provider_signature_verified":True,
        "born_at":born_at.isoformat(),
        "source_blob":files["source"]["blob_sha"],
        "oracle_blob":files["oracle"]["blob_sha"],
        "attestation_blob":files["attestation"]["blob_sha"],
        "source_imports":source_imports,"oracle_imports":oracle_imports,
        "signed_creator_claims_novelty":True,
        "semantic_novelty_proven_by_signature_alone":False,
        "source_module_executed":False
    }


def original_birth_admission(manifest,provider_witnesses):
    need(type(manifest) is dict
         and manifest.get("schema")==
             "mass.f124bv.two-independent-source-manifest.v1",
         "ORIGINAL_MANIFEST_SCHEMA")
    entries=manifest.get("families")
    need(type(entries) is list and len(entries)==2
         and [f.get("family") for f in entries]==["A","B"]
         and type(provider_witnesses) is dict
         and set(provider_witnesses)=={"A","B"},
         "BOTH_PROVIDERS_REQUIRED_AT_ONCE")
    reports=[
        original_witness_one(entries[i],provider_witnesses[key])
        for i,key in enumerate(("A","B"))]
    need(len({r["repo"] for r in reports})==2
         and len({r["creator"] for r in reports})==2
         and len({r["source_blob"] for r in reports})==2
         and len({r["oracle_blob"] for r in reports})==2,
         "DISTINCT_INDEPENDENT_ORIGINAL_GRAMMARS_AND_CREATORS")
    return {
      "schema":"mass.f124bv.provider-original-source-custody.v1",
      "families":reports,
      "provider_authenticated_separate_signed_source_origins":True,
      "signed_external_novelty_claims_present":True,
      "semantic_novelty_independently_proved":False,
      "firstuse_consumed":False,
      "protected_cohorts_used":False,
      "scientific_acceptance":False,
      "optimizer_policy_promotion":False,
      "disposition":"PROVIDER_BIRTH_CUSTODY_ONLY_EXPLICIT_NOVELTY_STILL_REQUIRES_SCIENTIFIC_EVALUATION"
    }


def _raw_samples(samples,label):
    need(type(samples) is list and len(samples)==5,
         "FIVE_REAL_WHOLE_PROCESS_SAMPLES_"+label)
    need(all(type(x) is int and x>0 for x in samples),
         "POSITIVE_OS_SAMPLE_"+label)
    return samples


def _cost_receipt(receipt,case):
    if receipt is None:
        return {"eligible":False,"reason":"MISSING_OR_ABSTAINED_NATURAL_WORK"}
    need(type(receipt) is dict
         and receipt.get("case")==case,
         "CASE_EXACT_RESOURCE_RECEIPT")
    if receipt.get("resource_eligible") is False:
        need(receipt.get("AZ_native_calls",0)!=2
             or receipt.get("BQ_native_calls",0)!=2
             or receipt.get("same_native_graphs_and_outputs") is False,
             "INELIGIBILITY_REASON_REQUIRED")
        return {"eligible":False,"reason":"NATURAL_NATIVE_WORK_UNMATCHED"}
    need(receipt.get("resource_eligible") is True
         and receipt.get("AZ_natural_route") in ("affine","feistel")
         and receipt.get("AZ_routing_forced") is False
         and receipt.get("AZ_native_calls")==2
         and receipt.get("BQ_native_calls")==2
         and receipt.get("same_native_graphs_and_outputs") is True
         and receipt.get("native_max_active",0)<=7
         and receipt.get("native_max_retained",0)<=9
         and receipt.get("full_public_fit_and_training_included") is True
         and receipt.get("full_process_peak_RSS") is True,
         "Genuine_UNFORCED_SAME_WORK_AND_COMPLETE_RESOURCE")
    a=receipt.get("AZ",{})
    b=receipt.get("BQ",{})
    need(type(a) is dict and type(b) is dict
         and a.get("allocator")=="default"
         and b.get("allocator")=="malloc",
         "FROZEN_RUNTIME_AND_ALLOCATOR")
    ac=_raw_samples(a.get("CPU_ns"),"AZ_CPU")
    ar=_raw_samples(a.get("peak_RSS_bytes"),"AZ_RSS")
    bc=_raw_samples(b.get("CPU_ns"),"BQ_CPU")
    br=_raw_samples(b.get("peak_RSS_bytes"),"BQ_RSS")
    qualified=median(bc)<=median(ac) and median(br)<=median(ar) and max(br)<=max(ar)
    return {"eligible":True,"qualified":qualified,
            "AZ_CPU_median_ns":median(ac),"BQ_CPU_median_ns":median(bc),
            "AZ_RSS_median_bytes":median(ar),"BQ_RSS_median_bytes":median(br),
            "AZ_RSS_max_bytes":max(ar),"BQ_RSS_max_bytes":max(br)}


def assess_development(records,source_receipt):
    """Deterministic posterior *report only*; never calls a model or generator."""
    need(type(source_receipt) is dict
         and source_receipt.get("provider_authenticated_separate_signed_source_origins")
             is True
         and source_receipt.get("firstuse_consumed") is False
         and source_receipt.get("protected_cohorts_used") is False,
         "TWO_AUTHENTIC_FIRSTUSE_SOURCE_BIRTHS_BEFORE_RESULT")
    need(type(records) is list and len(records)==24,
         "ALL_TWENTY_FOUR_SOURCE_CASES_PRESERVED")
    outcomes={}
    by_id={r.get("case"):r for r in records}
    need(len(by_id)==24,"NO_DUPLICATED_OR_MISSING_ORIGINAL_CASE")
    for family in ("A","B"):
        expected=EXPECTED[family]["fit"]
        outcomes[family]={"case_count":12,"hard_false_positive_case_ids":[],
                          "baseline_positive_lost_case_ids":[],
                          "new_correct_pair_case_ids":[],
                          "cost_ineligible_case_ids":[],
                          "cost_regression_case_ids":[]}
        o=outcomes[family]
        for case in expected:
            need(case in by_id,"MISSING_PROSPECTIVE_ORIGINAL_SOURCE_CASE")
            r=by_id[case]
            need(r.get("family")==family
                 and r.get("case")==case
                 and type(r.get("AZ_positive")) is bool
                 and type(r.get("AZ_hard_FP")) is bool
                 and type(r.get("BQ_positive")) is bool
                 and type(r.get("BQ_hard_FP")) is bool
                 and r.get("source_private_key_passed_to_model") is False
                 and r.get("source_truly_new_firstuse") is True
                 and r.get("protected_cases_opened") is False,
                 "ORIGINAL_RESULT_IDENTITY_AND_ORACLE_ISOLATION")
            if r["BQ_hard_FP"]:
                o["hard_false_positive_case_ids"].append(case)
            if r["AZ_positive"] and not r["BQ_positive"]:
                o["baseline_positive_lost_case_ids"].append(case)
            if (r["BQ_positive"] and not r["BQ_hard_FP"]
                and not (r["AZ_positive"] and not r["AZ_hard_FP"])):
                o["new_correct_pair_case_ids"].append(case)
            cost=_cost_receipt(r.get("resource"),case)
            if not cost["eligible"]:
                o["cost_ineligible_case_ids"].append(case)
            elif not cost["qualified"]:
                o["cost_regression_case_ids"].append(case)
        o["development_eligible"]=bool(
            not o["hard_false_positive_case_ids"]
            and not o["baseline_positive_lost_case_ids"]
            and len(o["new_correct_pair_case_ids"])>=2
            and not o["cost_ineligible_case_ids"]
            and not o["cost_regression_case_ids"])
    return {
       "schema":"mass.f124bv.original-prospective-development-admission.v1",
       "family_results":outcomes,
       "all_cases_kept_including_ineligible_and_negatives":True,
       "joint_development_eligible":all(
          v["development_eligible"] for v in outcomes.values()),
       "firstuse_completed_in_this_assessor":False,
       "protected_cohorts_consumed":False,
       "scientific_transfer_accepted":False,
       "optimizer_policy_promotion":False
    }


def pending_disposition():
    return {"schema":"mass.f124bv.readiness-original-source-absent.v1",
            "status":"BLOCKED_INDEPENDENT_SOURCE_BIRTH_NOT_PRESENT",
            "two_signed_distinct_original_GitHub_source_repos":False,
            "new_development_FIT_cases_consumed":0,
            "new_protected_128x2_cases_consumed":0,
            "source_or_original_learner_executed":False,
            "science_accepted":False,
            "optimizer_policy_promoted":False}


def live_original_provider_witness(source):
    """Get original GitHub HTTPS API responses, never trust caller's flag.

    GH_TOKEN must grant read access to each independently originated repo.
    This function does NOT download/run/compile any source in the local tree.
    """
    import os
    import subprocess
    need(bool(os.environ.get("GH_TOKEN")),
         "ORIGINAL_GITHUB_PROVIDER_AUTH_REQUIRED")
    repo=source["repository"]
    commit_sha=source["commit_sha"]
    need(type(repo) is str and bool(NAME.fullmatch(repo.split("/")[0]))
         and repo.count("/")==1
         and bool(SHA40.fullmatch(commit_sha)),
         "EXTERNAL_GITHUB_SOURCE_LOCATOR")
    def api(path):
        q=subprocess.run(["gh","api","repos/"+repo+"/"+path],
                         text=True,capture_output=True,timeout=60)
        need(q.returncode==0,
             "GITHUB_ORIGINAL_API_UNAVAILABLE_OR_UNAUTHENTICATED")
        return json.loads(q.stdout)
    git_commit=api("git/commits/"+commit_sha)
    rest_commit=api("commits/"+commit_sha)
    need(git_commit.get("sha")==commit_sha
         and rest_commit.get("sha")==commit_sha
         and type(git_commit.get("tree")) is dict,
         "GITHUB_ORIGINAL_COMMIT_AUTHENTIC")
    tree=api("git/trees/"+git_commit["tree"]["sha"]+"?recursive=1")
    original={}
    for role in ("source","oracle","attestation"):
        exact=source["files"][role]
        obj=api("git/blobs/"+exact["blob_sha"])
        original[role]={"path":exact["path"],"blob":obj}
    return {
      "repo":repo,"commit_sha":commit_sha,
      "provider_api_authenticated":True,
      "git_commit":git_commit,
      "rest_commit":rest_commit,
      "original_tree":tree,
      "original_blobs":original
    }


def main():
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path)
    p.add_argument("--live-provider",action="store_true",
                   help="Required for any real source custody: fresh GH API")
    p.add_argument("--results",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.manifest is None:
        need(not a.live_provider and a.results is None,
             "NO_RESULT_WITHOUT_INDEPENDENT_ORIGIN")
        result=pending_disposition()
    else:
        need(a.live_provider,
             "REAL_EXTERNAL_SOURCE_REQUIRES_FRESH_LIVE_GITHUB_PROVIDER")
        manifest=json.loads(a.manifest.read_text())
        need(type(manifest) is dict and
             type(manifest.get("families")) is list,
             "EXACT_SOURCE_MANIFEST")
        witnesses={family["family"]:live_original_provider_witness(family)
                   for family in manifest["families"]}
        receipt=original_birth_admission(manifest,witnesses)
        result=(assess_development(json.loads(a.results.read_text()),receipt)
                if a.results else receipt)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n")
    print("F124BV_DISPOSITION="+result.get("status",result.get("disposition",
        "PROSPECTIVE_REPORT_ONLY")))
    print("F124BV_NEW_SOURCE_AND_PROTECTED_FIRSTUSE_BY_THIS_GATE=0")
    print("F124BV_SCIENTIFIC_PROMOTION=false")


if __name__=="__main__":
    main()
