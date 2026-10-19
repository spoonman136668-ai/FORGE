"""F124-BM original source-birth preflight, without FIT/holdout construction.

This independently queries GitHub REST immutable commits/blobs at the original
precode and separate two source births. Provider authentication is not proof
of third-party origin, global novelty, or scientific acceptance.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
REPO="spoonman136668-ai/FORGE"
BASE="cd28b84817aa8fead064c7218889218cb6deea9f"
BIRTHS=(
    ("prereg","62482e31aeee2fe8735874fbfe374daded77f308",BASE,
     "f124bm-frozen-fitscreen.json","4743eb3119064bf8f6f26ca2d23b9588292f8a78"),
    ("GF2","a4e698852ddc89095327161af5ddf7eb6a173901",
     "62482e31aeee2fe8735874fbfe374daded77f308",
     "f124bm_gf2_source.py","e7df91c7270567d56ce62243196d8f67aa09c024"),
    ("ARX","81381ee34c3a2e79f6392051b62db7acd8f04337",
     "a4e698852ddc89095327161af5ddf7eb6a173901",
     "f124bm_arx_source.py","f3fbb5d04bff86d51a5a9ddb0c52979bb67924fe"),
)


def need(ok,reason):
    if not ok:
        raise RuntimeError("F124BM_BIRTH_"+reason)


def git(*args):
    p=subprocess.run(["git",*args],cwd=ROOT,check=False,capture_output=True)
    need(p.returncode==0,"LOCAL_GIT_"+args[0])
    return p.stdout


def github(obj):
    p=subprocess.run(["gh","api","repos/"+REPO+"/"+obj],
                     cwd=ROOT,capture_output=True,check=False)
    need(p.returncode==0,"GITHUB_REST")
    return json.loads(p.stdout)


def blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def verify(provider=False):
    need(git("merge-base",BASE,"HEAD").decode().strip()==BASE,
         "PARENT_IDENTITY")
    receipts=[]
    for tag,birth,parent,filename,sha in BIRTHS:
        path="research/north-star-transfer/"+filename
        source=git("show",birth+":"+path)
        need(blob(source)==sha and
             git("rev-parse","HEAD:"+path).decode().strip()==sha,
             "ORIGINAL_BLOB_"+tag)
        need(git("rev-parse",birth+"^").decode().strip()==parent,
             "FIRST_PARENT_"+tag)
        if tag!="prereg":
            tree=ast.parse(source.decode())
            imports=set()
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    imports.update(a.name for a in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module:
                    imports.add(node.module)
            need(imports<= {"__future__","copy","hashlib","random"},
                 "NO_MODEL_IN_SOURCE_"+tag)
        tree_sha=None
        if provider:
            obj=github("git/blobs/"+sha)
            need(obj.get("sha")==sha and obj.get("encoding")=="base64"
                 and base64.b64decode(obj["content"])==source,
                 "GITHUB_SOURCE_BLOB_"+tag)
            commit=github("git/commits/"+birth)
            need(commit["sha"]==birth and len(commit["parents"])==1
                 and commit["parents"][0]["sha"]==parent,
                 "GITHUB_COMMIT_PARENT_"+tag)
            tree_sha=commit["tree"]["sha"]
        receipts.append({"identity":tag,"birth_sha":birth,
                         "blob_sha":sha,"sha256":hashlib.sha256(source).hexdigest(),
                         "original_provider_tree":tree_sha})
    def load(tag,name):
        spec=importlib.util.spec_from_file_location(tag,HERE/name)
        mod=importlib.util.module_from_spec(spec)
        sys.modules[tag]=mod
        spec.loader.exec_module(mod)
        return mod
    gf=load("bm_gf_preflight","f124bm_gf2_source.py")
    ar=load("bm_ar_preflight","f124bm_arx_source.py")
    need(gf.FIT.start==914000 and gf.FIT.stop==914016
         and ar.FIT.start==915000 and ar.FIT.stop==915016
         and set(gf.FIT).isdisjoint(ar.FIT)
         and set(gf.FIT).isdisjoint(gf.HOLDOUT)
         and set(ar.FIT).isdisjoint(ar.HOLDOUT)
         and set(gf.HOLDOUT).isdisjoint(ar.HOLDOUT),
         "ORIGINAL_COHORT_SEPARATION")
    for m in (gf,ar):
        for seed in (-940,-939,900000,901000,902000,903000,
                     914100,914227,915100,915227):
            try:
                m.make(seed)
            except ValueError:
                continue
            need(False,"PROTECTED_SOURCE_CONSTRUCTED")
    return {
      "schema":"mass.f124bm.source-birth-provider-nonconsuming.v1",
      "exact_head":git("rev-parse","HEAD").decode().strip(),
      "independent_committed_source_bodies":len(receipts)==3,
      "provider_authentication":bool(provider),
      "birth_receipts":receipts,
      "FIT_or_protected_records_generated":0,
      "original_BH_U_R_firstuse":False,
      "external_thirdparty_scientific_origin":False,
      "comprehensive_historical_novelty":False,
      "scientific_acceptance":False,
      "optimizer_promotion":False,
    }


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--provider",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    data=verify(provider=args.provider)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print("F124BM_GITHUB_PROVIDER_SOURCE_BIRTH="+
          ("PASS" if args.provider else "LOCAL_ONLY"))
    print("F124BM_PROTECTED_AND_FIT_GENERATED=0")
    print("F124BM_EXTERNALLY_INDEPENDENT_NOVELTY=false")


if __name__=="__main__":
    main()
