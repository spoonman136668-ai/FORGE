"""Frozen RAR-G117 complete F139 unittest A/B/B/A development-only benchmark."""
import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = "9085b5829b1ac7e0cb055cb665573145ef13af72"
BRANCH = "engineering/rar-g117-two-negative-fixture-20261107"
SUITE = ["-B", "-m", "unittest", "discover", "-s", "f139", "-p", "test_*.py"]
MAX_ARM_SEC = 600
MIN_AGGREGATE = 1.03
MIN_PAIR = 1.00
DISCOVERY = """
import json, unittest
suite=unittest.defaultTestLoader.discover("f139",pattern="test_*.py")
def flatten(node):
 for case in node:
  if isinstance(case,unittest.TestSuite): yield from flatten(case)
  else: yield case
cases=list(flatten(suite))
if any(isinstance(case,unittest.loader._FailedTest) for case in cases):
 raise RuntimeError("G117_DISCOVERY_IMPORT_FAILED")
ids=[case.id() for case in cases]
skips=sorted(case.id() for case in cases if getattr(type(case),"__unittest_skip__",False)
    or getattr(getattr(case,case._testMethodName),"__unittest_skip__",False))
print(json.dumps({"ids":ids,"skips":skips}))
"""


def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],
                                   text=True,timeout=90).strip()


def stable(root,source):
    if (git(root,"rev-parse","HEAD")!=source or
            git(root,"status","--porcelain","--untracked-files=all")):
        raise ValueError("G117_SOURCE_DIRTY_OR_MOVED")


def inventory(root):
    v=subprocess.check_output([sys.executable,"-B","-c",DISCOVERY],
        cwd=root,text=True,timeout=120,
        env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
    return json.loads(v)


def methods(root):
    tree=ast.parse((root/"f139/test_nci04_two_negative_transition.py").read_text())
    return [ast.dump(node,include_attributes=False) for top in tree.body
            if isinstance(top,ast.ClassDef) for node in top.body
            if isinstance(node,ast.FunctionDef) and node.name.startswith("test_")]


def arm(root,source,index,name,inv):
    stable(root,source)
    start=time.perf_counter()
    with tempfile.TemporaryFile(mode="w+t",encoding="utf-8") as output:
        p=subprocess.run([sys.executable,*SUITE],cwd=root,timeout=MAX_ARM_SEC,
            stdout=output,stderr=subprocess.STDOUT,text=True,
            env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
        elapsed=round(time.perf_counter()-start,6)
        output.seek(0)
        body=output.read()
    found=re.findall(r"(?m)^Ran (\d+) tests in [\d.]+s\s*$",body)
    if p.returncode or len(found)!=1 or int(found[0])!=len(inv["ids"]) or "\nOK" not in body:
        raise ValueError("G117_FAILED_FULL_SUITE_"+name+"_"+str(index)+":"+body[-2300:])
    skips=re.search(r"(?m)^OK \(skipped=(\d+)\)",body)
    runtime_skips = int(skips.group(1)) if skips else 0
    if runtime_skips < len(inv["skips"]):
        raise ValueError("G117_DECLARED_SKIPS_LOST")
    stable(root,source)
    return {"index":index,"name":name,"seconds":elapsed,
            "tests":int(found[0]),"skips":runtime_skips,
            "declared_skips":len(inv["skips"]),"returncode":p.returncode}


def main():
    if (os.environ.get("GITHUB_ACTIONS")!="true" or
            os.environ.get("GITHUB_HEAD_REF")!=BRANCH or
            os.environ.get("GITHUB_REPOSITORY")!="spoonman136668-ai/FORGE" or
            os.environ.get("GITHUB_EVENT_NAME")!="pull_request"):
        raise ValueError("G117_NOT_EXISTING_DEV_PR_CI")
    head=git(ROOT,"rev-parse","HEAD")
    if (head!=os.environ.get("FORGE_G117_HEAD") or
            git(ROOT,"merge-base",BASE,"HEAD")!=BASE):
        raise ValueError("G117_SOURCE_OR_ANCESTOR_DRIFT")
    changed=set(git(ROOT,"diff","--name-only",BASE,"HEAD").splitlines())
    if changed != {".github/workflows/qualify.yml",
                   "f139/test_nci04_two_negative_transition.py",
                   "scripts/check_rar_g117_abba.py"}:
        raise ValueError("G117_CANDIDATE_PATCH_SCOPE_DRIFT")
    tree=git(ROOT,"rev-parse","HEAD^{tree}")
    stable(ROOT,head)
    with tempfile.TemporaryDirectory(dir=os.environ["RUNNER_TEMP"],
                                      prefix="rar-g117-") as temp:
        baseline=Path(temp)/"baseline"
        subprocess.run(["git","-C",str(ROOT),"worktree","add","--detach",
                        str(baseline),BASE],check=True,timeout=90,
                       stdout=subprocess.DEVNULL)
        try:
            stable(baseline,BASE)
            a,b=inventory(baseline),inventory(ROOT)
            if a!=b or len(a["ids"])!=len(set(a["ids"])):
                raise ValueError("G117_CHANGED_IDS_OR_SKIP_IDENTITIES")
            original_methods=methods(baseline)
            if not original_methods or original_methods!=methods(ROOT):
                raise ValueError("G117_CHANGED_TEST_METHOD_BODIES")
            runs=[]
            for i,label in enumerate(("baseline","candidate","candidate","baseline"),1):
                path=baseline if label=="baseline" else ROOT
                sha=BASE if label=="baseline" else head
                runs.append(arm(path,sha,i,label,a))
            if len({r["skips"] for r in runs}) != 1:
                raise ValueError("G117_RUNTIME_SKIP_COUNT_DRIFT")
        finally:
            subprocess.run(["git","-C",str(ROOT),"worktree","remove","--force",
                            str(baseline)],check=True,timeout=90,
                           stdout=subprocess.DEVNULL)
    stable(ROOT,head)
    x,y,z,w=[r["seconds"] for r in runs]
    pairs=[x/y,w/z]
    gain=(x+w)/(y+z)
    passed=gain>=MIN_AGGREGATE and all(p>=MIN_PAIR for p in pairs)
    receipt={"schema":"forge.rar.g117.full-suite.abba.dev.v1",
            "source":head,"tree":tree,"baseline":BASE,
            "run":os.environ.get("GITHUB_RUN_ID"),"attempt":os.environ.get("GITHUB_RUN_ATTEMPT"),
            "platform":platform.platform(),"python":sys.version,
            "full_suite_command":SUITE,"test_count":len(a["ids"]),
            "declared_skips":len(a["skips"]),
            "runtime_skips_each_arm":[r["skips"] for r in runs],
            "cases_sha256":hashlib.sha256("\n".join(a["ids"]).encode()).hexdigest(),
            "method_ast_sha256":hashlib.sha256(json.dumps(original_methods).encode()).hexdigest(),
            "arms":runs,"pair_speedups":[round(v,6) for v in pairs],
            "aggregate_speedup":round(gain,6),
            "min_pair":MIN_PAIR,"min_aggregate":MIN_AGGREGATE,
            "development_verdict":"PASS_DEV_ONLY" if passed else "NO_GO",
            "whole_ci_speedup_proven":False,"scientific_first_use":False,
            "automatic_main_activation":False,"full_regression":True}
    (Path(os.environ["RUNNER_TEMP"])/"rar-g117-abba.json").write_text(
        json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("FORGE_RAR_G117="+receipt["development_verdict"],flush=True)
    print("FORGE_RAR_G117_AGGREGATE="+str(receipt["aggregate_speedup"]),flush=True)


if __name__=="__main__":
    main()
