"""F124-BP original source birth authentication, before *any* first-use.

Uses only Git/GitHub immutable blob/commit identity and AST. It does NOT call
source make() or learner FIT. Authenticates provider custody, NOT external
scientific source novelty or independence of the broader research history.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
REPO="spoonman136668-ai/FORGE"
BASE="086ecf9437a45b3e10a4557b2dab35e7a8ed247c"
BIRTHS=(
  ("protocol","8fac42d2cf0afb4a2c1ea37806df468662e7a037",BASE,
   "f124bp-frozen-composition.json","fea917eb7f604d6f70c903054e4e42d9780bbb8d"),
  ("compact_learner","ac50fbc376424205e547ea3f64ccb1e4ab46eea9",
   "8fac42d2cf0afb4a2c1ea37806df468662e7a037",
   "f124bp_compact_learner.py","fec421e5e0f4501125e5c8307a290e7a473d3b38"),
  ("procedural_source","8f40e7b7bab68893f8be84651636e8f719f80bef",
   "ccc932bca9ca6bae92377d7a71353f177ecf19d9",
   "f124bp_procedural_source.py","c5c2ee4fd88748f955af758889f83709fde3308d"),
  ("feedback_source","b3b55e0a8eb0a366ddd60ccc1c72490ca22d1248",
   "8f40e7b7bab68893f8be84651636e8f719f80bef",
   "f124bp_feedback_source.py","78646cd8b4e0a13a95e3f18df043b7ba1277d696")
)


def need(ok,what):
    if not ok:raise RuntimeError("F124BP_PROVIDER_"+what)


def git(*args):
    p=subprocess.run(["git",*args],cwd=ROOT,capture_output=True)
    need(p.returncode==0,"LOCAL_GIT_"+args[0])
    return p.stdout


def remote(endpoint):
    p=subprocess.run(["gh","api","repos/"+REPO+"/"+endpoint],
                     cwd=ROOT,capture_output=True)
    need(p.returncode==0,"GITHUB_API_OBJECT")
    return json.loads(p.stdout)


def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def check(provider=False):
    need(git("merge-base",BASE,"HEAD").decode().strip()==BASE,
         "PARENT_ORIGINAL_QUALIFIED_BO_EVIDENCE")
    verified=[]
    for kind,commit,parent,file,object_id in BIRTHS:
        path="research/north-star-transfer/"+file
        raw=git("show",commit+":"+path)
        need(blob(raw)==object_id and
             git("rev-parse","HEAD:"+path).decode().strip()==object_id,
             "IMMUTABLE_ORIGINAL_BIRTH_BLOB_"+kind)
        need(git("rev-parse",commit+"^").decode().strip()==parent,
             "SEPARATE_FIRST_PARENT_"+kind)
        if kind.endswith("_source"):
            imports=set()
            for n in ast.walk(ast.parse(raw.decode("utf-8"))):
                if isinstance(n,ast.Import):
                    imports.update(a.name for a in n.names)
                elif isinstance(n,ast.ImportFrom) and n.module:
                    imports.add(n.module)
            need(imports<={"__future__","copy","hashlib","random"},
                 "SOURCE_MUST_NOT_IMPORT_MODEL_"+kind)
        tree=None
        if provider:
            b=remote("git/blobs/"+object_id)
            need(b["sha"]==object_id and b["encoding"]=="base64"
                 and base64.b64decode(b["content"])==raw,
                 "PROVIDER_IMMUTABLE_BLOB_"+kind)
            c=remote("git/commits/"+commit)
            need(c["sha"]==commit and len(c["parents"])==1
                 and c["parents"][0]["sha"]==parent,
                 "PROVIDER_INDEPENDENT_SOURCE_BIRTH_"+kind)
            tree=c["tree"]["sha"]
        verified.append({"role":kind,"commit":commit,"blob":object_id,
                         "sha256":hashlib.sha256(raw).hexdigest(),
                         "provider_tree":tree})
    proto=json.loads(git("show",BIRTHS[0][1]+
        ":research/north-star-transfer/f124bp-frozen-composition.json"))
    need(proto["new_origination"]["family_A"]["new_development_ids"]==
         [922000,922011]
         and proto["new_origination"]["family_B"]["new_development_ids"]==
         [923000,923011]
         and proto["new_origination"]["family_A"]["protected_ids"]==
         [922100,922227]
         and proto["new_origination"]["family_B"]["protected_ids"]==
         [923100,923227],
         "ORIGINAL_PRECODE_PROTECTED_AND_NEW_IDS")
    return {"schema":"mass.f124bp.original-github-source-birth.v1",
            "verified":verified,
            "provider_GitHub_authentic":provider,
            "original_source_birth_after_qualified_model":True,
            "registered_cases_generated":0,
            "protected_source_cases_generated":0,
            "old_consumed_source_reissued":False,
            "third_party_external_scientific_novelty":False,
            "scientific_admission":False,
            "optimizer_promotion":False,
            "exact_HEAD":git("rev-parse","HEAD").decode().strip()}


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--provider",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    data=check(provider=a.provider)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    print("F124BP_NEW_ORIGINAL_SOURCE_BIRTH="+(
        "PROVIDER_PASS" if a.provider else "LOCAL_PASS"))
    print("F124BP_PROSPECTIVE_SOURCE_CONSUMED=0")


if __name__=="__main__":
    main()
