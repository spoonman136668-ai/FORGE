"""F124-CF provider-original external signed source custody, READ ONLY.

The real entry point accepts no caller-supplied JSON. Fetch issue #605 from
GitHub, and, only if BOTH C/D original creator comments exist, fetch fresh
GitHub original commit, REST author, tree and three complete blob responses.
Never import/compile/execute external source/oracle, and never persist the
oracle/source bytes. An authenticated signature does NOT prove independently
authored genuinely novel science or grant CB/CC first-use.
"""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PARENT=HERE/"f124ce_source_readiness.py"
FREEZE=HERE/"f124cf-frozen-provider-authentication.json"
REF_MARKER="F124CE-EXTERNAL-BIRTH-V1"
HASH=re.compile(r"^[0-9a-f]{40}$")
BANNED_IMPORTS=("f124","forge","nativeevidence","research","optimizer")
BANNED_FUNCTIONS={"eval","exec","compile","__import__"}
MAX_BYTES={"source":100000,"oracle":100000,"attestation":30000}


def need(condition,reason):
    if not condition:
        raise ValueError("F124CF_FAIL_CLOSED_"+reason)


def parent_gate():
    s=importlib.util.spec_from_file_location("CF_frozen_original_CE",PARENT)
    need(s is not None and s.loader is not None,"EXISTING_CE_READONLY_GATE")
    mod=importlib.util.module_from_spec(s)
    sys.modules[s.name]=mod
    s.loader.exec_module(mod)
    return mod


def freeze():
    doc=json.loads(FREEZE.read_text())
    need(doc["schema"]==
         "mass.f124cf.original-provider-signature-and-source-static-custody-precode.v1"
         and doc["preimplementation_freeze"] is True
         and doc["original_CE_protocol_commit"]==
             "264f12cfcd1f37a401f8eb9fbe1689ee274f3afc"
         and doc["original_CE_protocol_blob"]==
             "df770890b0131e259ce30012ae9c599ca15bbfab"
         and doc["no_scientific_firstuse"] is True
         and doc["no_model_calls"] is True
         and doc["no_protected_open"] is True,
         "PRECODE_SOURCE_ONLY_POLICY")
    return doc


def extract_live_refs(issue,comments):
    ce=parent_gate()
    ce.scan_issue(issue,comments) # immutable original parsing / default deny
    entries={}
    for comment in comments:
        body=comment["body"].strip()
        if not body.startswith(REF_MARKER+"\n"):
            continue
        lines=body.split("\n",1)
        ref=json.loads(lines[1])
        fam=ref["family"]
        need(fam not in entries and fam in ("C","D"),
             "DUPLICATE_OR_WRONG_SOURCE_FAMILY")
        entries[fam]=ref
    return entries


def git_object(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def blob_bytes(meta,expected,role):
    need(type(meta) is dict and meta.get("encoding")=="base64"
         and type(meta.get("content")) is str
         and meta.get("sha")==expected and bool(HASH.fullmatch(expected)),
         "ORIGINAL_PROVIDER_BLOB_RESPONSE_"+role)
    try:
        raw=base64.b64decode(meta["content"],validate=False)
    except Exception as exc:
        raise ValueError("F124CF_FAIL_CLOSED_BASE64_"+role) from exc
    need(len(raw)<=MAX_BYTES[role] and git_object(raw)==expected,
         "VERIFIED_CONTENT_ADDRESSED_SOURCE_BLOB_"+role)
    return raw


def static_python(data,role):
    try:
        parsed=ast.parse(data.decode("utf8"))
    except (SyntaxError,UnicodeError) as exc:
        raise ValueError("F124CF_FAIL_CLOSED_STATIC_PYTHON_"+role) from exc
    imports=[]
    for node in ast.walk(parsed):
        if isinstance(node,ast.Import):
            imports.extend(n.name for n in node.names)
        elif isinstance(node,ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
            need(node.func.id not in BANNED_FUNCTIONS,
                 "DYNAMIC_EXECUTION_REFERENCE_"+role)
    need(not any(name.lower().startswith(BANNED_IMPORTS)
                 for name in imports),
         "PRIOR_MODEL_IMPORT_IN_ORIGINAL_"+role)
    return sorted(imports)


def verify_one(ref,witness):
    """Only signed-origin identity; NEVER novelty or scientific first-use."""
    ce=parent_gate()
    ce.verify_protocol()
    freeze()
    need(type(ref) is dict and type(witness) is dict,
         "TWO_PROVIDER_ORIGINALS_MISSING")
    family=ref["family"]
    repo=ref["repository"]
    sha=ref["commit_sha"]
    creator=ref["creator_login"]
    need(family in ("C","D") and type(repo) is str
         and type(sha) is str and bool(HASH.fullmatch(sha))
         and witness.get("repo")==repo and witness.get("sha")==sha,
         "ORIGINAL_REPOSITORY_COMMIT_UNTRUSTED")
    git=witness.get("git_commit")
    rest=witness.get("rest_commit")
    tree=witness.get("tree")
    blobs=witness.get("blobs")
    need(type(git) is dict and type(rest) is dict
         and type(tree) is dict and type(blobs) is dict,
         "MISSING_ACTUAL_GITHUB_PROVIDER_RECEIPTS")
    v=git.get("verification",{})
    need(git.get("sha")==sha and rest.get("sha")==sha
         and type(v) is dict and v.get("verified") is True
         and type(v.get("signature")) is str and bool(v["signature"].strip())
         and type(v.get("reason")) is str and bool(v["reason"].strip())
         and rest.get("author",{}).get("login","").lower()==creator.lower(),
         "SIGNED_COMMIT_ACTUAL_GITHUB_IDENTITY")
    need(type(git.get("tree")) is dict and tree.get("sha")==git["tree"].get("sha")
         and tree.get("truncated") is False
         and type(tree.get("tree")) is list,
         "ORIGINAL_NONTRUNCATED_COMMIT_TREE")
    need(set(blobs)=={"source","oracle","attestation"},
         "ALL_THREE_ORIGINAL_BLOBS")
    literal=ref["files"]
    actual={}
    imports={}
    for role in ("source","oracle","attestation"):
        file=literal[role]
        path=file["path"]
        blob=file["blob_sha"]
        need(type(path) is str and type(blob) is str
             and bool(HASH.fullmatch(blob)),
             "EXACT_SIGNED_FILE_METADATA_"+role)
        item=[t for t in tree["tree"] if t.get("path")==path]
        need(len(item)==1 and item[0].get("type")=="blob"
             and item[0].get("sha")==blob,
             "ORIGINAL_TREE_BLOB_IDENTITY_"+role)
        actual[role]=blob_bytes(blobs[role],blob,role)
        if role in ("source","oracle"):
            imports[role]=static_python(actual[role],role)
    need(len({literal[k]["blob_sha"] for k in literal})==3,
         "REUSED_SOURCE_ORACLE_ATTESTATION_OBJECT")
    try:
        att=json.loads(actual["attestation"].decode("utf8"))
    except (UnicodeError,ValueError) as exc:
        raise ValueError("F124CF_FAIL_CLOSED_SIGNED_ATTESTATION_JSON") from exc
    need(type(att) is dict
         and att.get("schema")=="mass.f124cf.signed-origin-attestation.v1"
         and att.get("family")==family and
         att.get("creator_login","").lower()==creator.lower()
         and att.get("frozen_protocol_commit")==
             "264f12cfcd1f37a401f8eb9fbe1689ee274f3afc"
         and att.get("frozen_protocol_blob")==
             "df770890b0131e259ce30012ae9c599ca15bbfab"
         and all(att.get(k) is True for k in
                 ("independently_originated",
                  "no_model_access_or_copied_source",
                  "no_prior_case_or_seed_reuse",
                  "no_protected_firstuse"))
         and type(att.get("novelty_claim")) is str
         and len(att["novelty_claim"].strip())>=40,
         "SOURCE_CLAIMS_OR_FROZEN_ATTESTATION_NOT_BOUND")
    # It is not possible to authenticate actual historical birth from
    # Git author/committer timestamps; both can be controlled by authors.
    return {
        "family":family,"provider_repo":repo,
        "provider_creator":creator,
        "original_git_commit_sha":sha,
        "original_tree_sha":tree["sha"],
        "source_blob_sha":literal["source"]["blob_sha"],
        "oracle_blob_sha":literal["oracle"]["blob_sha"],
        "attestation_blob_sha":literal["attestation"]["blob_sha"],
        "original_source_imports":imports["source"],
        "original_oracle_imports":imports["oracle"],
        "signature_provider_verified":True,
        "attestation_claims_signed":True,
        "semantic_novelty_independently_verified":False,
        "true_authorship_independently_proved":False,
        "independent_postfreeze_birth_chronology_proved":False,
        "source_and_oracle_never_executed":True
    }


def pair(refs,witnesses,real_provider=False):
    need(type(refs) is dict and set(refs)=={"C","D"}
         and type(witnesses) is dict and set(witnesses)=={"C","D"},
         "BOTH_SOURCE_FAMILIES_REQUIRE_REAL_PROVIDER")
    verified=[verify_one(refs[f],witnesses[f]) for f in ("C","D")]
    need(len({i["provider_repo"].lower() for i in verified})==2
         and len({i["provider_creator"].lower() for i in verified})==2
         and len({i["original_git_commit_sha"] for i in verified})==2
         and len({i["source_blob_sha"] for i in verified})==2
         and len({i["oracle_blob_sha"] for i in verified})==2,
         "C_D_ACTUALLY_DIFFERENT_SIGNED_ORIGINALS")
    return {
        "schema":"mass.f124cf.original-provider-source-custody.v1",
        "original_provider_witnesses":verified,
        "source_custody_qualified":bool(real_provider),
        "status":("SOURCE_CUSTODY_ONLY_PENDING_INDEPENDENT_NOVELTY_AUTHORSHIP_CHRONOLOGY"
                  if real_provider else
                  "TEST_FIXTURE_ONLY_NO_EXTERNAL_AUTHENTICATION"),
        "independent_novelty_accepted":False,
        "scientific_source_firstuse_authorized":False,
        "protected_cohorts_opened":False,
        "models_executed":False,
        "scientific_acceptance":False,
        "optimizer_or_production_promoted":False
    }


def provider_api(repository,path):
    # User-supplied paths never enter subprocess arguments directly.
    # Original metadata format is validated by frozen CE before access.
    p=subprocess.run(["gh","api","repos/"+repository+"/"+path],
                     capture_output=True,text=True,timeout=60)
    need(p.returncode==0,"GITHUB_ORIGINAL_PROVIDER_CUSTODY_UNAVAILABLE")
    return json.loads(p.stdout)


def original_witness(ref):
    repo=ref["repository"]
    sha=ref["commit_sha"]
    git=provider_api(repo,"git/commits/"+sha)
    rest=provider_api(repo,"commits/"+sha)
    need(git.get("sha")==sha and
         type(git.get("tree")) is dict
         and bool(HASH.fullmatch(git["tree"].get("sha",""))),
         "GITHUB_SIGNED_COMMIT_TREE_NOT_REAL")
    tree=provider_api(repo,"git/trees/"+git["tree"]["sha"]+"?recursive=1")
    blobs={role:provider_api(repo,"git/blobs/"+ref["files"][role]["blob_sha"])
           for role in ("source","oracle","attestation")}
    return {"repo":repo,"sha":sha,"git_commit":git,
            "rest_commit":rest,"tree":tree,"blobs":blobs}


def live():
    import os
    need(bool(os.environ.get("GH_TOKEN")),
         "PROVIDER_GITHUB_READ_TOKEN_MISSING")
    ce=parent_gate()
    issue=ce.gh_api("repos/spoonman136668-ai/FORGE/issues/605")
    comments=ce.gh_api("repos/spoonman136668-ai/FORGE/issues/605/comments?per_page=100")
    refs=extract_live_refs(issue,comments)
    result={"schema":"mass.f124cf.live-source-provider-readiness.v1",
            "issue":"https://github.com/spoonman136668-ai/FORGE/issues/605",
            "frozen_CB_CC_protocol_blob":"df770890b0131e259ce30012ae9c599ca15bbfab",
            "original_external_reference_count":len(refs),
            "source_custody_qualified":False,
            "source_and_oracle_executed":False,
            "science_firstuse_cases_created":0,
            "protected_replication_cases_opened":0,
            "scientific_novelty_proven":False,
            "CB_CC_models_executed":False,
            "scientific_accepted":False,
            "optimizer_production_promoted":False}
    if len(refs)<2:
        result["status"]=("BLOCKED_NO_EXTERNALLY_AUTHORED_ORIGINS"
                          if not refs else
                          "BLOCKED_TWO_EXTERNAL_SIGNED_SOURCE_FAMILIES_REQUIRED")
    else:
        proof=pair(refs,{fam:original_witness(refs[fam])
                         for fam in ("C","D")},real_provider=True)
        result["source_custody_qualified"]=proof["source_custody_qualified"]
        result["source_commit_proofs"]=proof["original_provider_witnesses"]
        result["status"]=proof["status"]
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=live()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n")
    print("F124CF_ORIGINAL_EXTERNAL_REFERENCE_COUNT="+str(
          result["original_external_reference_count"]))
    print("F124CF_LIVE_GITHUB_PROVIDER_DISPOSITION="+result["status"])
    print("F124CF_ORIGINAL_EXTERNAL_ORACLE_BYTES_PERSISTED=FALSE")
    print("F124CF_CB_CC_DEVELOPMENT_FIRSTUSE=0")
    print("F124CF_PROTECTED_COHORTS_OPENED=0")


if __name__=="__main__":
    main()
