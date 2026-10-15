"""R22: read real frozen preregistration Git blobs; no scientific authority.

Authenticates SHA-1 Git object framing, exact previous source pin and SHA-256
of underlying preregistration bytes. Does not invent signed source-birth,
independent custody, consumed first-use, or authorization.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from r20b_readonly_prereg_audit import Blocked, MANIFEST, PINS, decode, fixed_inputs, NoRedirect

FROZEN = pathlib.Path(__file__).resolve().parents[1] / "reference/research-originals/20261015-r22-original-prereg-sha256.json"
MAX_BLOB=32768
HEX40=re.compile(r"[0-9a-f]{40}\Z")

def verify_blob(pin,blob):
    if not isinstance(blob,dict) or set(("sha","size","encoding","content"))-set(blob):
        raise Blocked("BLOB_METADATA_MISSING")
    if blob["sha"] != pin["prereg_git_blob_sha"] or blob["encoding"] != "base64":
        raise Blocked("WRONG_BLOB")
    data=blob["content"]
    if not isinstance(data,str) or len(data)>MAX_BLOB*2 or blob["size"] <=0 or blob["size"]>MAX_BLOB:
        raise Blocked("BLOB_SIZE")
    try:
        raw=base64.b64decode("".join(data.split()),validate=True)
    except (ValueError,binascii.Error) as exc:
        raise Blocked("BLOB_BASE64") from exc
    if len(raw)!=blob["size"] or len(raw)>MAX_BLOB:
        raise Blocked("BLOB_LENGTH")
    git_sha=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\x00"+raw).hexdigest()
    if git_sha!=pin["prereg_git_blob_sha"]:
        raise Blocked("GIT_OBJECT_HASH_DRIFT")
    try:
        document=decode(raw)
    except (TypeError,ValueError) as exc:
        raise Blocked("PREREG_JSON_INVALID") from exc
    if not isinstance(document,dict) or not isinstance(document.get("experiment"),str) or not document["experiment"]:
        raise Blocked("PREREG_EXPERIMENT_MISSING")
    return hashlib.sha256(raw).hexdigest()

def audit(manifest,pins,read_blob):
    rows,expected=fixed_inputs(manifest,pins)
    records=[]
    for e,p in zip(rows,expected):
        if e["experiment"]!=p["experiment"] or p["source_head_sha"]!=e["head_sha"] or p["repository"]!=e["repository"]:
            raise Blocked("SOURCE_IDENTITY_DRIFT")
        result=read_blob(e["lane"],p["prereg_git_blob_sha"])
        digest=verify_blob(p,result)
        records.append({
            "lane":e["lane"],"experiment":e["experiment"],
            "source_commit_sha":e["head_sha"],
            "prereg_git_blob_sha":p["prereg_git_blob_sha"],
            "prereg_sha256":digest,
        })
    if len(records)!=6:
        raise Blocked("NOT_SIX_ORIGINALS")
    return {
        "schema":"forge.research-archive.r22-genuine-prereg-bytes.v1",
        "status":"GITHUB_ORIGINAL_SOURCE_BYTES_PINNED_NO_FIRSTUSE_AUTHORITY",
        "count":6,
        "wingless_count":3,
        "yggdrasil_count":3,
        "records":records,
        "independent_source_birth_verified":False,
        "complete_first_use_reconciled":False,
        "scientific_accepted":False,
        "optimizer_promotion_authorized":False,
        "originals_executed":0,
        "cloudflare_writes":0,
    }

def verify_frozen_observations(result, frozen):
    if not isinstance(frozen,dict) or set(frozen)!={"schema","observed_github_run_id","status","records"} or \
       frozen["schema"]!="forge.research-archive.r22-source-byte-pins.v1" or \
       frozen["status"]!="ORIGINAL_PREREG_SHA256_FROZEN_NOT_SCIENTIFIC_CUSTODY" or \
       frozen["observed_github_run_id"]!=38727033870:
        raise Blocked("R22_FROZEN_SOURCE_PROVENANCE_INVALID")
    records=frozen["records"]
    observed=result["records"]
    if not isinstance(records,list) or len(records)!=6 or len(observed)!=6:
        raise Blocked("R22_FROZEN_SOURCE_COUNT")
    seen=set()
    for want,actual in zip(records,observed):
        if not isinstance(want,dict) or set(want)!={"lane","experiment","source_commit_sha","prereg_git_blob_sha","prereg_sha256"} or want!=actual:
            raise Blocked("R22_FROZEN_SHA256_MISMATCH")
        pair=(want["lane"],want["experiment"])
        if pair in seen:
            raise Blocked("R22_DUPLICATE_FROZEN_EXPERIMENT")
        seen.add(pair)
    return True

def read_blob(lane,oid):
    if lane not in ("Wingless","Yggdrasil") or not isinstance(oid,str) or not HEX40.fullmatch(oid):
        raise Blocked("UNTRUSTED_BLOB_REQUEST")
    url="https://api.github.com/repos/spoonman136668-ai/"+lane+"/git/blobs/"+oid
    headers={"Accept":"application/vnd.github+json","User-Agent":"FORGE-R22-readonly"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"]="Bearer "+os.environ["GH_TOKEN"]
    req=urllib.request.Request(url,headers=headers,method="GET")
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=15) as response:
            if response.status!=200 or response.geturl()!=url:
                raise Blocked("BLOB_REDIRECT_OR_STATUS")
            raw=response.read(MAX_BLOB*3+4096)
    except (urllib.error.URLError,OSError) as exc:
        raise Blocked("BLOB_FETCH_FAILED") from exc
    return decode(raw)

def main():
    try:
        result=audit(decode(MANIFEST.read_bytes()),decode(PINS.read_bytes()),read_blob)
        verify_frozen_observations(result,decode(FROZEN.read_bytes()))
    except (OSError,Blocked,TypeError,KeyError,ValueError) as exc:
        print("R22_ORIGINAL_PREREG_BYTES=BLOCKED:"+(str(exc) if isinstance(exc,Blocked) else type(exc).__name__),file=sys.stderr)
        return 1
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
