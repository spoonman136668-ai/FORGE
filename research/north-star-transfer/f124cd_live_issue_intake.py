"""F124-CD live provider-original intake from public GitHub issue #586.

Read-only; consumes NO source. Reuses frozen F124-BV source authority for the
ORIGINAL BQ/AZ protocol only, never silently promotes CB or CC. Signatures
and author accounts do not themselves establish substantive scientific
novelty, true authorship independence or trustworthy historical birth time.

Each independent source creator can post one comment directly on #586:
F124CD-ORIGINAL-EXTERNAL-BIRTH-V1
{"schema":"mass.f124bv.external-birth-reference.v1",...}
The exact JSON reference is PUBLIC PROVENANCE metadata only; do not post
private holdout content, generator bytes, private oracle or credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL=HERE/"f124bv_origin_admission.py"
MARKER="F124CD-ORIGINAL-EXTERNAL-BIRTH-V1"
ISSUE_REPO="spoonman136668-ai/FORGE"
ISSUE_NO=586
SHA40=re.compile(r"^[0-9a-f]{40}$")
LOGIN=re.compile(r"^[A-Za-z0-9_-]{1,39}$")


def original():
    spec=importlib.util.spec_from_file_location("f124cd_original_BV_frozen",ORIGINAL)
    if spec is None or spec.loader is None:
        raise RuntimeError("F124CD_BV_ORIGINAL_IMPORT_UNAVAILABLE")
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m


def require(ok,msg):
    if not ok:
        raise RuntimeError("F124CD_FAIL_CLOSED_"+msg)


def gh_api(endpoint):
    require(bool(os.environ.get("GH_TOKEN")),
            "AUTHENTICATED_PROVIDER_READ_TOKEN_REQUIRED")
    p=subprocess.run(["gh","api",endpoint],cwd=ROOT,
                     text=True,capture_output=True,timeout=60)
    require(p.returncode==0,"ACTUAL_GITHUB_PROVIDER_UNAVAILABLE")
    return json.loads(p.stdout)


def discover(issue,comments):
    require(type(issue) is dict and type(comments) is list,
            "GITHUB_ISSUE_AND_COMMENTS_DATA_TYPES")
    require(issue.get("number")==ISSUE_NO
            and issue.get("state")=="open"
            and type(issue.get("comments")) is int
            and 0<=issue["comments"]<=100
            and len(comments)==issue["comments"],
            "INCOMPLETE_OR_WRONG_OR_CLOSED_PROVIDER_ISSUE")
    entries={}
    metadata=[]
    for c in comments:
        require(type(c) is dict and type(c.get("body")) is str
                and type(c.get("user")) is dict
                and type(c.get("id")) is int,
                "PROVIDER_COMMENT_INTEGRITY")
        body=c["body"].strip()
        if not body.startswith(MARKER):
            continue
        lines=body.split("\n",1)
        require(len(lines)==2 and lines[0].strip()==MARKER
                and len(lines[1])<=15000,"ORIGINAL_SOURCE_REFERENCE_FORMAT")
        try:
            ref=json.loads(lines[1])
        except (ValueError,TypeError) as exc:
            raise RuntimeError("F124CD_FAIL_CLOSED_SOURCE_REFERENCE_JSON") from exc
        require(type(ref) is dict
                and ref.get("schema")=="mass.f124bv.external-birth-reference.v1"
                and ref.get("family") in ("A","B"),
                "FROZEN_BV_SOURCE_REFERENCE_ONLY")
        creator=ref.get("creator_login")
        commenter=c["user"].get("login")
        require(type(creator) is str and bool(LOGIN.fullmatch(creator))
                and type(commenter) is str and commenter.lower()==creator.lower()
                and commenter.lower()!=ISSUE_REPO.split("/")[0].lower(),
                "ACTUAL_COMMENTER_MUST_BE_INDEPENDENT_CREATOR")
        repo=ref.get("repository")
        require(type(repo) is str and repo.count("/")==1
                and all(LOGIN.fullmatch(name) for name in repo.split("/"))
                and repo.split("/")[0].lower()!=ISSUE_REPO.split("/")[0].lower(),
                "NO_SAME_ACCOUNT_EXTERNAL_SOURCE")
        require(type(ref.get("commit_sha")) is str
                and bool(SHA40.fullmatch(ref["commit_sha"])),
                "GITHUB_PROVIDER_SIGNED_COMMIT_REQUIRED")
        family=ref["family"]
        require(family not in entries,"DUPLICATED_SOURCE_PROVIDER_COMMENT")
        entries[family]=ref
        metadata.append({"family":family,"comment_id":c["id"],
                         "comment_creator":commenter,
                         "repository":repo,
                         "original_commit_sha":ref["commit_sha"],
                         "reference_sha256":hashlib.sha256(
                             lines[1].encode()).hexdigest()})
    if len(entries)==2:
        require(entries["A"]["creator_login"].lower()!=
                entries["B"]["creator_login"].lower()
                and entries["A"]["repository"].lower()!=
                    entries["B"]["repository"].lower(),
                "NOT_TWO_GENUINELY_DISTINCT_GITHUB_PRINCIPALS")
    return entries,metadata


def evaluate(issue,comments,provider=None):
    """By default only REAL freshly fetched Github provider input is admitted.

    The provider argument is exclusively to test the structural routing in
    local deterministic tests; a non-real provider does not count as source
    custody and never produces scientific acceptance.
    """
    entries,metadata=discover(issue,comments)
    result={
       "schema":"mass.f124cd.real-original-independent-source-intake.v1",
       "original_F124_BV_protocol":"BQ_versus_AZ_ONLY",
       "issue":f"https://github.com/{ISSUE_REPO}/issues/{ISSUE_NO}",
       "original_issue_comment_count":len(comments),
       "original_source_registration_count":len(entries),
       "source_reference_custody":metadata,
       "source_and_oracle_executed":False,
       "old_consumed_science_replayed":False,
       "BQ_BV_reserved_development_firstuse":False,
       "BQ_BV_reserved_128x2_replication_opened":False,
       "CB_CC_scientific_protocol_substituted":False,
       "CB_CC_prospective_science_admitted":False,
       "scientific_novelty_authenticated_by_signature":False,
       "independent_science_accepted":False,
       "optimizer_policy_promoted":False,
       "automatic_source_firstuse_or_merge":False
    }
    if len(entries)==0:
        result["status"]="BLOCKED_INDEPENDENT_SOURCE_BIRTH_NOT_PRESENT"
        return result
    if len(entries)<2:
        result["status"]="BLOCKED_TWO_INDEPENDENT_SOURCE_BIRTHS_REQUIRED"
        return result
    frozen=original()
    require(entries["A"]["frozen_protocol_blob"]==frozen.PROTOCOL_BLOB
            and entries["B"]["frozen_protocol_blob"]==frozen.PROTOCOL_BLOB,
            "BV_PRECODE_BLOB_NOT_CB_CC")
    if provider is None:
        manifest={"schema":"mass.f124bv.two-independent-source-manifest.v1",
                  "families":[entries["A"],entries["B"]]}
        witnessed={k:frozen.live_original_provider_witness(entries[k])
                   for k in ("A","B")}
        verified=frozen.original_birth_admission(manifest,witnessed)
        require(verified.get("provider_authenticated_separate_signed_source_origins")
                is True and verified.get("semantic_novelty_independently_proved")
                is False,"ORIGINAL_PROVIDER_SIGNED_SOURCE_ONLY")
        result["provider_original"]=verified
        result["status"]="SOURCE_CUSTODY_VERIFIED_SCIENTIFIC_NOVELTY_REVIEW_REQUIRED"
    else:
        # A mock provider is only useful for routing tests, not an admission.
        require(callable(provider),"TEST_ROUTING_PROVIDER")
        provider(entries)
        result["status"]="TEST_ONLY_TWO_SOURCE_ROUTING_NOT_AUTHENTICATED"
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    # The issue and comments are ALWAYS provider-fetched. Never use arbitrary
    # JSON response files or a self-issued verified=True receipt in real CI.
    issue=gh_api(f"repos/{ISSUE_REPO}/issues/{ISSUE_NO}")
    comments=gh_api(f"repos/{ISSUE_REPO}/issues/{ISSUE_NO}/comments?per_page=100")
    outcome=evaluate(issue,comments)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf8") as f:
        json.dump(outcome,f,indent=2,sort_keys=True)
        f.write("\n")
    print("F124CD_ISSUE_COMMENTS="+str(outcome["original_issue_comment_count"]))
    print("F124CD_EXTERNAL_ORIGIN_REFERENCE_COUNT="+str(outcome["original_source_registration_count"]))
    print("F124CD_STATUS="+outcome["status"])
    print("F124CD_ORIGINAL_BQ_VS_AZ_ONLY=TRUE")
    print("F124CD_CB_CC_SCIENCE_AUTOMATIC_ADMISSION=FALSE")
    print("F124CD_PROTECTED_FIRSTUSE=0")
    print("F124CD_SOURCE_OR_MODEL_EXECUTION=FALSE")


if __name__=="__main__":
    main()
