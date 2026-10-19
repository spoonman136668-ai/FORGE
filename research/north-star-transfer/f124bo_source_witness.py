"""F124-BO source birth verifier -- does not construct a registered task."""
from __future__ import annotations
import ast,base64,hashlib,json,subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
REPO="spoonman136668-ai/FORGE"
BASE="6958d6c4838e37e8431d0d078abdab84d7fda1b2"
BIRTHS=(
 ("freeze","d9b9f60f944d1ef10cf752a332839c70ec52cfb4",BASE,
  "f124bo-freeze.json","acc26b376bb006ab36e2dd77b2c3e46eaf335d38"),
 ("learner","a004bbb2ca4389c2ec22fa0828a139f235eb0170",
  "d9b9f60f944d1ef10cf752a332839c70ec52cfb4",
  "f124bo_nonlinear_learner.py","fe1229770fa76185779678fc6155f87d28415cef"),
 ("modular","b6da89a4cc6a18cc26587d29a9acb73a5e97e112",
  "bc36614087aa6cc21ac68d0ef613724b43e0d7dd",
  "f124bo_mod_source.py","4c037f55e220b22783d89e3e566b951e0eff618e"),
 ("feistel","6f8cedfca91e6ce1003480144775e76792c8adfb",
  "b6da89a4cc6a18cc26587d29a9acb73a5e97e112",
  "f124bo_feistel_source.py","b934ce6962dc9a1526d82dbdc2736d210f2db57d")
)


def need(ok,label):
    if not ok:raise RuntimeError("F124BO_CUSTODY_"+label)


def git(*args):
    z=subprocess.run(["git",*args],cwd=ROOT,capture_output=True)
    need(z.returncode==0,"LOCAL_GIT_"+args[0])
    return z.stdout


def provider(endpoint):
    r=subprocess.run(["gh","api","repos/"+REPO+"/"+endpoint],
                     cwd=ROOT,capture_output=True)
    need(r.returncode==0,"GITHUB_ORIGINAL_OBJECT")
    return json.loads(r.stdout)


def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def verify(remote=False):
    need(git("merge-base",BASE,"HEAD").decode().strip()==BASE,
         "QUALIFIED_PARENT")
    receipts=[]
    for role,commit,parent,file,identity in BIRTHS:
        path="research/north-star-transfer/"+file
        raw=git("show",commit+":"+path)
        need(blob(raw)==identity
             and git("rev-parse","HEAD:"+path).decode().strip()==identity,
             "IMMUTABLE_BLOB_"+role)
        need(git("rev-parse",commit+"^").decode().strip()==parent,
             "ORIGINAL_PARENT_"+role)
        if role in ("modular","feistel"):
            tree=ast.parse(raw.decode("utf-8"))
            imports=set()
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):
                    imports.update(x.name for x in n.names)
                if isinstance(n,ast.ImportFrom) and n.module:
                    imports.add(n.module)
            need(imports<={"__future__","copy","hashlib","random"},
                 "INDEPENDENT_SOURCE_NO_MODEL_IMPORT_"+role)
        treeid=None
        if remote:
            item=provider("git/blobs/"+identity)
            need(item["sha"]==identity and item["encoding"]=="base64"
                 and base64.b64decode(item["content"])==raw,
                 "GITHUB_PROVIDER_BLOB_"+role)
            commit_obj=provider("git/commits/"+commit)
            need(commit_obj["sha"]==commit
                 and len(commit_obj["parents"])==1
                 and commit_obj["parents"][0]["sha"]==parent,
                 "GITHUB_PROVIDER_PARENT_"+role)
            treeid=commit_obj["tree"]["sha"]
        receipts.append({"role":role,"born_at":commit,"git_blob":identity,
                         "sha256":hashlib.sha256(raw).hexdigest(),
                         "provider_tree":treeid})
    frozen=json.loads(git("show",BIRTHS[0][1]+
                          ":research/north-star-transfer/f124bo-freeze.json"))
    need(frozen["schema"]==
         "mass.f124bo.preimplementation.learned-modular-nonlinear-selective-cognition.v1"
         and frozen["candidate"]["name"]==
         "N16 learnable odd-multiplier modular affine plus xor-mask inverse",
         "PROTOCOL")
    need(frozen["new_source_origination"]["A"]["new_FIT"]==[920000,920011]
         and frozen["new_source_origination"]["B"]["new_FIT"]==[921000,921011]
         and frozen["new_source_origination"]["A"]["protected"]==[920100,920227]
         and frozen["new_source_origination"]["B"]["protected"]==[921100,921227],
         "SOURCE_HOLDOUT_IDENTITY")
    return {"schema":"mass.f124bo.original-before-first-use-provider-witness.v1",
            "exact_head":git("rev-parse","HEAD").decode().strip(),
            "original_births":receipts,
            "source_GitHub_provider_authenticated":remote,
            "source_birth_after_frozen_learner":True,
            "registered_FIT_cases_constructed":0,
            "protected_U_R_and_new_holdouts_constructed":0,
            "independent_external_thirdparty_origin_certified":False,
            "original_192_TRAIN_replayed":False,
            "scientific_acceptance":False,
            "optimizer_promotion":False}


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--provider",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    record=verify(a.provider)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")
    print("F124BO_ORIGINAL_SOURCE_BIRTH="+(
        "PROVIDER_PASS" if a.provider else "LOCAL_PASS"))
    print("F124BO_REGISTERED_OR_PROTECTED_CASES_CONSTRUCTED=0")


if __name__=="__main__":
    main()
