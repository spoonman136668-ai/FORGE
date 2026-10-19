"""F124-BN v2 original pre-firstuse custody: immutable model before source births.

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
BASE="81a348003ac1940056af36ed0b8c497bfb06e9df"
BIRTHS=(
 ("protocol","9f36522d0993f9a48cfd984928440cd3f05ccf3a",BASE,
  "f124bn-v2-freeze.json","62758d245c89b72ba7638f7197ab27b4d8c877ae"),
 ("learner","3e4f8f3421ded778861b965c903cbe1a2724f845",
  "9f36522d0993f9a48cfd984928440cd3f05ccf3a",
  "f124bn_v2_learner.py","d928e5716e6494f61f709120f9659f944610482d"),
 ("mix","7bc6f9dd1f97ee2d64242876d4595a8382a33c03",
  "3e4f8f3421ded778861b965c903cbe1a2724f845",
  "f124bn_v2_triangular_source.py","586516f3fdb0136b462f21a4fe235dac7b32f5bb"),
 ("word","89644c7e5e86993421334abe25adc94ffae3a05e",
  "7bc6f9dd1f97ee2d64242876d4595a8382a33c03",
  "f124bn_v2_coupled_source.py","fb56effb6e689899626af108f6f435930f88dfab")
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
                          ":research/north-star-transfer/f124bn-v2-freeze.json"))
    need(frozen["schema"]=="mass.f124bn.v2.preimplementation-bounded-linear-learning.v1"
         and frozen["new_sources"]["A"]["cohort"]==[918000,918011]
         and frozen["new_sources"]["B"]["cohort"]==[919000,919011]
         and frozen["new_sources"]["A"]["protected"]==[918100,918227]
         and frozen["new_sources"]["B"]["protected"]==[919100,919227],
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
