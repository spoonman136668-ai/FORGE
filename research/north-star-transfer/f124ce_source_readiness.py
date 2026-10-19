"""F124-CE: distinct CB/CC prospective pre-first-use protocol and live issue check.

Data-only source admission readiness. Does NOT parse/execute untrusted Python,
trust invented source signatures, register firstuse or authorize experiment.
Original BV BQ/AZ firstuse IDs are permanently excluded.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
PROTOCOL=HERE/"f124ce-frozen-CB-CC-independent-science.json"
ISSUE_REPO="spoonman136668-ai/FORGE"
ISSUE_NUMBER=605
MARKER="F124CE-EXTERNAL-BIRTH-V1"
PROTOCOL_COMMIT="264f12cfcd1f37a401f8eb9fbe1689ee274f3afc"
PROTOCOL_BLOB="df770890b0131e259ce30012ae9c599ca15bbfab"
SHA40=re.compile(r"^[0-9a-f]{40}$")
GITHUB_NAME=re.compile(r"^[A-Za-z0-9_-]{1,39}$")
PATH=re.compile(r"^[A-Za-z0-9_./-]+$")
BANNED_IDS=set(range(924000,924012))|set(range(925000,925012))|set(range(924100,924228))|set(range(925100,925228))


def need(ok,why):
    if not ok:
        raise ValueError("F124CE_FAIL_CLOSED_"+why)


def verify_protocol():
    p=json.loads(PROTOCOL.read_text())
    need(p["schema"]=="mass.f124ce.independent-CB-CC-prospective-prebirth.v1",
         "FROZEN_PROTOCOL_SCHEMA")
    o=p["original_BV_scope"]
    need(o["frozen_blob"]=="5a509951aacb3de7cbec0c0e895d3b9c8ce4dce5"
         and o["comparison"]=="BQ versus AZ ONLY"
         and o["not_reused"] is True,"ORIGINAL_BV_SCOPE_PRESERVED")
    expected={"C":((926000,926011),(926100,926227)),
              "D":((927000,927011),(927100,927227))}
    ids=set()
    for family,((a,b),(c,d)) in expected.items():
        spec=p["new_source_cohorts"][family]
        need(spec["development"]==[a,b] and spec["replication"]==[c,d]
             and spec["development_count"]==12 and spec["replication_count"]==128,
             "NEW_SOURCE_IDENTITY_DRIFT_"+family)
        ids.update(range(a,b+1))
        ids.update(range(c,d+1))
    need(len(ids)==280 and not (ids&BANNED_IDS),
         "NO_OLD_BV_OR_CONSUMED_ID_REUSE")
    ctl={x["arm"]:x for x in p["frozen_controls"]}
    need(set(ctl)=={"CB","CC","AZ","BQ","BX","BZ","CA","AG_NATIVE"},
         "STRONGEST_TRAINED_CONTROLS_ABSENT")
    need(ctl["CB"]["blob"]=="8a10bf8cec12afc7d8703e3586d8eba91ebfdc7c"
         and ctl["CC"]["blob"]=="29c0c02f54ea539bed0910fe82adcc86d3aff94d"
         and ctl["CB"]["persistent_bits"]==ctl["CC"]["persistent_bits"]==32
         and ctl["CB"]["fit_residual_scans"]==ctl["CC"]["fit_residual_scans"]==6560,
         "UNCHANGED_EQUALLY_TRAINED_LEARNERS")
    task=p["task"];dev=p["development_acceptance"];rep=p["sealed_replication_acceptance"]
    need(task["public_fit_count"]==40 and task["public_check_count"]==8
         and task["maximum_persistent_model_bits"]==32
         and task["native_max_active"]==7 and task["native_max_retained"]==9,
         "FROZEN_SOURCE_AND_NATIVE_WORK_BUDGET")
    need(dev["hard_false_positives_max"]==0
         and dev["accepted_positive_losses_max"]==0
         and dev["new_correct_paired_positive_and_hard_negative_over_strongest_trained_peer_per_family_min"]==2
         and dev["both_family_all_cases_natural_CB_CC_matched_required"]
         and dev["both_family_all_cases_resource_nonregression_required"],
         "NO_RELAXED_DEVELOPMENT_SCIENCE")
    need(rep["new_correct_paired_cases_net_over_strongest_eligible_trained_controls_min"]==7
         and rep["hard_false_positives_max"]==0
         and rep["previously_accepted_positive_losses_max"]==0
         and rep["complete_resource_nonregression_all_cases_required"]
         and rep["separately_authorized_firstuse_required"],
         "NO_HOLDOUT_FIRSTUSE_OR_RETUNING")
    auth=p["authority"]
    need(auth["source_registration_and_review_only"]
         and all(auth[k] is False for k in (
              "development_firstuse","protected_firstuse",
              "scientific_acceptance","optimizer_promotion","production",
              "merge","new_controller","paid_inference","original_BV_modification")),
         "NO_UNAUTHORIZED_FIRSTUSE_OR_PROMOTION")
    return p


def _same_author_comment(body):
    # Only an exact marker at the start of a comment can be considered.
    return body.strip().startswith(MARKER)


def scan_issue(issue,comments):
    verify_protocol()
    need(type(issue) is dict and issue.get("number")==ISSUE_NUMBER
         and issue.get("state")=="open"
         and type(issue.get("comments")) is int
         and 0<=issue["comments"]<=100
         and type(comments) is list and len(comments)==issue["comments"],
         "ORIGINAL_GITHUB_ISSUE_AND_COMPLETE_COMMENTS")
    submissions={}
    provenance=[]
    for comment in comments:
        need(type(comment) is dict and type(comment.get("body")) is str
             and type(comment.get("user")) is dict
             and type(comment.get("id")) is int,
             "ORIGINAL_PROVIDER_COMMENT")
        body=comment["body"].strip()
        if not _same_author_comment(body):
            continue
        split=body.split("\n",1)
        need(len(split)==2 and split[0].strip()==MARKER
             and len(split[1])<=16000,
             "EXACT_NEW_SOURCE_REFERENCE_JSON_FORMAT")
        try:
            source=json.loads(split[1])
        except ValueError as exc:
            raise ValueError("F124CE_FAIL_CLOSED_BAD_SOURCE_REFERENCE_JSON") from exc
        need(type(source) is dict
             and source.get("schema")=="mass.f124ce.external-birth-reference.v1"
             and source.get("family") in ("C","D")
             and source.get("frozen_protocol_commit")==PROTOCOL_COMMIT
             and source.get("frozen_protocol_blob")==PROTOCOL_BLOB,
             "DISTINCT_CB_CC_PROTOCOL_NOT_ORIGINAL_BV")
        author=comment["user"].get("login")
        creator=source.get("creator_login")
        repo=source.get("repository")
        sha=source.get("commit_sha")
        need(type(author) is str and type(creator) is str
             and GITHUB_NAME.fullmatch(creator)
             and author.lower()==creator.lower()
             and author.lower()!="spoonman136668-ai",
             "EXTERNAL_CREATOR_MUST_POST_SOURCE_REFERENCE")
        need(type(repo) is str and repo.count("/")==1
             and all(GITHUB_NAME.fullmatch(x) for x in repo.split("/"))
             and repo.split("/")[0].lower()!="spoonman136668-ai"
             and type(sha) is str and SHA40.fullmatch(sha),
             "EXTERNAL_PROVIDER_SOURCE_COMMIT_METADATA")
        files=source.get("files")
        need(type(files) is dict and set(files)=={"source","oracle","attestation"},
             "ORIGINAL_THREE_SOURCE_ORACLE_ATTESTATION_BLOBS")
        for role,extension in [("source",".py"),("oracle",".py"),
                               ("attestation",".json")]:
            item=files[role]
            need(type(item) is dict and type(item.get("path")) is str
                 and PATH.fullmatch(item["path"])
                 and item["path"].endswith(extension)
                 and not item["path"].startswith(("/","."))
                 and ".." not in item["path"].split("/")
                 and type(item.get("blob_sha")) is str
                 and SHA40.fullmatch(item["blob_sha"]),
                 "INVALID_SIGNED_SOURCE_ROLE_"+role)
        family=source["family"]
        need(family not in submissions,
             "DUPLICATE_FAMILY_SOURCE_REFERENCE")
        submissions[family]=source
        provenance.append({
            "family":family,"comment_id":comment["id"],
            "external_claimed_creator":creator,
            "external_claimed_repository":repo,
            "original_commit_reference":sha,
            "source_reference_sha256":hashlib.sha256(
                split[1].encode()).hexdigest(),
            "source_provider_authenticated":False,
            "semantic_novelty_independently_proven":False
        })
    if len(submissions)==2:
        need(submissions["C"]["creator_login"].lower() !=
             submissions["D"]["creator_login"].lower()
             and submissions["C"]["repository"].lower() !=
             submissions["D"]["repository"].lower()
             and submissions["C"]["commit_sha"] != submissions["D"]["commit_sha"],
             "TWO_DISTINCT_OUTSIDE_SOURCE_CREATORS_REQUIRED")
    return {"schema":"mass.f124ce.original-CB-CC-external-source-readiness.v1",
            "issue":f"https://github.com/{ISSUE_REPO}/issues/{ISSUE_NUMBER}",
            "source_protocol_commit":PROTOCOL_COMMIT,
            "source_protocol_blob":PROTOCOL_BLOB,
            "original_issue_comments_checked":len(comments),
            "source_reference_count":len(submissions),
            "source_reference_metadata":provenance,
            "status":("BLOCKED_INDEPENDENT_NEW_CB_CC_SOURCE_BIRTH_NOT_PRESENT"
                      if not submissions else
                      "BLOCKED_TWO_DISTINCT_CB_CC_SOURCES_REQUIRED"
                      if len(submissions)==1 else
                      "BLOCKED_SIGNED_PROVIDER_ORIGINAL_AND_SEMANTIC_NOVELTY_QUALIFICATION_REQUIRED"),
            "source_provider_signed_original_commits_verified":False,
            "scientific_novelty_and_independent_authorship_proven":False,
            "source_generator_or_oracle_executed":False,
            "new_CB_CC_development_cases_created":0,
            "new_CB_CC_protected_cases_created":0,
            "original_BV_science_sources_touched":False,
            "original_CB_CC_or_native_scoring_rerun":False,
            "science_accepted":False,
            "optimizer_or_production_promoted":False,
            "merge_or_firstuse_authorized":False}


def gh_api(endpoint):
    need(bool(os.environ.get("GH_TOKEN")),"GH_ORIGINAL_PROVIDER_TOKEN_REQUIRED")
    res=subprocess.run(["gh","api",endpoint],
                       text=True,capture_output=True,timeout=60)
    need(res.returncode==0,"ACTUAL_GITHUB_PROVIDER_API_FAILED")
    return json.loads(res.stdout)


def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--output",type=Path,required=True)
    opts=arg.parse_args()
    # No file-input override; provider issue/comments must be fetched live.
    issue=gh_api(f"repos/{ISSUE_REPO}/issues/{ISSUE_NUMBER}")
    comments=gh_api(f"repos/{ISSUE_REPO}/issues/{ISSUE_NUMBER}/comments?per_page=100")
    record=scan_issue(issue,comments)
    opts.output.parent.mkdir(parents=True,exist_ok=True)
    with opts.output.open("x",encoding="utf8") as stream:
        json.dump(record,stream,indent=2,sort_keys=True)
        stream.write("\n")
    print("F124CE_STATUS="+record["status"])
    print("F124CE_NEW_CB_CC_ORIGIN_REFERENCES="+str(record["source_reference_count"]))
    print("F124CE_SOURCE_METADATA_NOT_AUTHENTICATED=true")
    print("F124CE_SCIENTIFIC_FIRSTUSE=0")
    print("F124CE_NO_SYNTHETIC_SOURCE_RERUN=true")


if __name__=="__main__":
    main()
