"""F124-BN original pre-firstuse custody: immutable model before source births.

Authenticate provider Git blobs/commits/first-parent ordering, never evaluate
a registered development or 128-case protected source in this verifier.
Separate source commits are not independent external scientific attestation.
"""
from __future__ import annotations
import ast,base64,hashlib,json,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
REPO="spoonman136668-ai/FORGE"
BASE="0956b2c192eee3cb14d799afca5eddc364628914"
BIRTHS=(
 ("protocol","9018e41158bb83fc9f92a3d38c7e4b22e33eebdb",BASE,
  "f124bn-frozen-causal-learning.json","e83fc0d8d14306dda163bad448c8dcaad40204ba"),
 ("learner","599e41577f896d1d8ade94932a8f05941878fe5a",
  "9018e41158bb83fc9f92a3d38c7e4b22e33eebdb",
  "f124bn_learned_causal.py","fc627c4d8b627cdf7368f1b6c188ed5d2214ee51"),
 ("mix","62ab98c0301396c833a5d40810159e1ab5c922d7",
  "599e41577f896d1d8ade94932a8f05941878fe5a",
  "f124bn_mix_source.py","56909261219777cae7e975b80278e9387370b552"),
 ("word","606131cdd7417f757889436be0a9d7227b7cd3cf",
  "62ab98c0301396c833a5d40810159e1ab5c922d7",
  "f124bn_word_source.py","450165b2d497d6ac0d923fcbeaccd5a29959f24c")
)


def need(ok,name):
    if not ok:raise RuntimeError("F124BN_CUSTODY_"+name)


def git(*args):
    p=subprocess.run(["git",*args],cwd=ROOT,capture_output=True)
    need(p.returncode==0,"GIT_"+args[0])
    return p.stdout


def provider(endpoint):
    p=subprocess.run(["gh","api","repos/"+REPO+"/"+endpoint],
                     cwd=ROOT,capture_output=True)
    need(p.returncode==0,"REMOTE_GITHUB_OBJECT")
    return json.loads(p.stdout)


def digest(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def verify(remote=False):
    need(git("merge-base",BASE,"HEAD").decode().strip()==BASE,
         "QUALIFIED_BM_BASE")
    verified=[]
    for role,birth,parent,name,blob in BIRTHS:
        path="research/north-star-transfer/"+name
        content=git("show",birth+":"+path)
        need(digest(content)==blob
             and git("rev-parse","HEAD:"+path).decode().strip()==blob,
             "BIRTH_BLOB_"+role)
        need(git("rev-parse",birth+"^").decode().strip()==parent,
             "FIRST_PARENT_"+role)
        if role in ("mix","word"):
            tree=ast.parse(content.decode())
            imports=set()
            for item in ast.walk(tree):
                if isinstance(item,ast.Import):
                    imports.update(x.name for x in item.names)
                elif isinstance(item,ast.ImportFrom) and item.module:
                    imports.add(item.module)
            need(imports<= {"__future__","copy","hashlib","random"},
                 "SOURCE_IMPORT_LEARNER_FORBIDDEN_"+role)
        treeid=None
        if remote:
            a=provider("git/blobs/"+blob)
            need(a["sha"]==blob and a["encoding"]=="base64"
                 and base64.b64decode(a["content"])==content,
                 "PROVIDER_BYTES_"+role)
            c=provider("git/commits/"+birth)
            need(c["sha"]==birth and len(c["parents"])==1
                 and c["parents"][0]["sha"]==parent,
                 "PROVIDER_FIRST_PARENT_"+role)
            treeid=c["tree"]["sha"]
        verified.append({"role":role,"commit":birth,"git_blob":blob,
                         "source_sha256":hashlib.sha256(content).hexdigest(),
                         "provider_tree":treeid})
    # No import of source module to verify protected identities: an AST-only
    # read never constructs or consumes an original task.
    frozen=json.loads(git("show",BIRTHS[0][1]+
                          ":research/north-star-transfer/f124bn-frozen-causal-learning.json"))
    need(frozen["parent_head"]==BASE
         and frozen["source_new"]["A"]["range"]==[916000,916011]
         and frozen["source_new"]["B"]["range"]==[917000,917011]
         and frozen["sealed_replication"]["A"]==[916100,916227]
         and frozen["sealed_replication"]["B"]==[917100,917227],
         "PREDECLARED_SEPARATE_CASES")
    return {"schema":"mass.f124bn.original-preuse-source-witness.v1",
            "exact_sha":git("rev-parse","HEAD").decode().strip(),
            "births":verified,"GitHub_provider_object_witnessed":remote,
            "learner_source_born_before_both_evaluation_sources":True,
            "independent_external_source_novelty_certified":False,
            "original_fit_constructed":0,"protected_holdouts_constructed":0,
            "old_BM_32_cases_replayed":False,"science_accepted":False}


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--provider",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    r=verify(remote=args.provider)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print("F124BN_MODEL_BEFORE_INDEPENDENT_SOURCE_BIRTH="+
          ("PROVIDER_PASS" if args.provider else "LOCAL_PASS"))
    print("F124BN_PROTECTED_SOURCE_CONSUMED=0")
    print("F124BN_THIRDPARTY_ORIGINALITY=false")


if __name__=="__main__":
    main()
