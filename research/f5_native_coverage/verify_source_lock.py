"""F5 engineering content-lock verifier; never a scientific execution permit.

Read Git objects, not CRLF-normalized checkout files. This exact-qualified
source lock does NOT freeze or allocate prospective seeds. No authority
is inferred from a successful GitHub workflow or a content hash.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

MANIFEST=Path(__file__).with_name("source_content_lock.json")
GIT_HEX=re.compile(r"^[0-9a-f]{40}$")
ALLOWED_FILES=frozenset({
 "research/f5_native_coverage/policy.py",
 "research/f5_native_coverage/worker.py",
 "research/f5_native_coverage/coverage_geometry.py",
 "research/f5_native_coverage/prospective_protocol.json",
 "research/f5_native_coverage/run_historical.py",
 "research/f5_native_coverage/verify_historical.py",
})

def need(condition,message):
    if not condition:raise ValueError("F5_SOURCE_LOCK_"+message)

def verify_manifest(data,blobs):
    need(data.get("schema")=="forge.f5.non_authorizing-source-content-lock.v1","SCHEMA")
    need(data.get("status")==
         "IMPLEMENTATION_AND_PROTOCOL_GIT_BLOBS_PINNED_SCIENTIFIC_FREEZE_BLOCKED",
         "STATE")
    need(set(data.get("git_blob_sha1",{}))==ALLOWED_FILES,"FILES")
    need(data.get("git_blob_sha1")==blobs,"CONTENT_IDENTITY")
    need(all(GIT_HEX.fullmatch(blob or "") for blob in blobs.values()),"OBJECT_SHA")
    need(data.get("external_parent",{}).get("commit")==
         "5797a257a75fe139313e8486cd1a1ae79c44b148","PARENT")
    need(data.get("frozen_method_ids")==["F5-FIXED","F5-COVERAGE","F5-MINIMAX","F5-MEMORY"],
         "ARMS")
    need(data.get("approved_for")=="ENGINEERING_ONLY_NO_NEW_SCIENTIFIC_DATA",
         "NO_SCIENCE")
    pending=data.get("not_frozen",{})
    need(pending.get("development_seeds")=="UNALLOCATED" and
         pending.get("sealed_seeds")=="UNALLOCATED" and
         pending.get("evaluator_sealed_pairs")=="UNALLOCATED" and
         pending.get("once_only_original_id")=="UNALLOCATED" and
         pending.get("prospective_first_use")=="UNAUTHORIZED",
         "PREMATURE_ORIGINAL")
    custody=data.get("custody_requirements",{})
    need(custody.get("out_of_band_signer_public_key")=="NOT_PROVISIONED" and
         custody.get("signed_snapshot")=="NOT_RECEIVED" and
         custody.get("external_monotonic_revision")=="NOT_AUTHENTICATED" and
         custody.get("forbid_unsigned_github_metadata_substitution") is True,
         "FALSE_CUSTODY")
    need(data.get("scientific_execution_authorized") is False and
         data.get("scientific_original_started") is False and
         data.get("first_use_claims_consumed")==0,"AUTHORITY")
    need(data.get("status_for_science")==
         "BLOCKED_MISSING_SIGNED_ALL_LANE_CUSTODY_AND_COHORT_ALLOCATION",
         "FAIL_CLOSED")
    return {"schema":"forge.f5.independent-source-content-identity-review.v1",
            "status":"CONTENT_PIN_PASS_SCIENTIFIC_FREEZE_NOT_AUTHORIZED",
            "verified_git_blob_count":len(blobs),
            "scientific_originals":0,
            "first_use_claims":0,
            "scientific_execution_authorized":False}

def run(root):
    root=Path(root).resolve(strict=True)
    def git(*args):
        return subprocess.check_output(["git","-C",str(root),*args],
                                       stderr=subprocess.DEVNULL).decode().strip()
    need(Path(git("rev-parse","--show-toplevel")).resolve()==root,"CHECKOUT_ROOT")
    need(not git("status","--porcelain"),"DIRTY_SOURCE")
    # Both the source lock and all methods must be owned by the exact
    # HEAD Git tree. The parent content is not inferred from filesystem.
    raw=subprocess.check_output(["git","-C",str(root),"show",
       "HEAD:research/f5_native_coverage/source_content_lock.json"])
    lock=json.loads(raw)
    names=lock.get("git_blob_sha1",{})
    need(set(names)==ALLOWED_FILES,"SOURCE_FILES")
    actual={}
    for path in sorted(names):
        actual[path]=git("rev-parse","HEAD:"+path)
    return verify_manifest(lock,actual)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--out")
    options=ap.parse_args()
    report=run(options.repo_root)
    content=(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n")
    if options.out:
        with open(options.out,"x",encoding="utf-8",newline="\n") as f:f.write(content)
    print("F5_IMMUTABLE_ENGINEERING_SOURCE_CONTENT=PASS")
    print("F5_SCIENTIFIC_FREEZE=BLOCKED_EXTERNAL_CUSTODY_NOT_PRESENT")
    print(content,end="")
