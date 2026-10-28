"""AC-10: inspect an AUTHENTIC upstream Causal-Gymnasium checkout, without episodes.

Source-authenticated read-only Python contract and attempted unmodified import.
This script intentionally DOES NOT train, interact with, reset or call .do on
DTR; external-source discovery is not a scientific first-use permit.

Usage: python -B ac10_upstream_contract.py --upstream DIR --out FILE
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA = "forge.ac10.upstream-dtr-source-compatibility.v1"
SOURCE_COMMIT = "c94e9a4cd3641588b6b8507e71ccee5c27032bdf"
SOURCE_TREE = "fd8d8a67c1fc7fa62274dc7e12fb1e77945632f0"
BLOBS = {
    "causal_gym/envs/dtr.py": "6af2371dce21804140ea141ccb7be14e003ba275",
    "causal_gym/envs/mdp.py": "6264ec5450754c009e98c3e85f6d5927ece0a9ab",
    "causal_gym/core/pch.py": "ff37780c6b791877c70583b8d5f699be7fcd8817",
    "LICENSE": "993e3a4922f003dced0fd061735697c850ea7205",
    "setup.py": "31097c35f908e393bfd4763a298c1d5f4ab60600"
}
# Public-development plan only. Never run original scientific families.
PROTO = {
    "frozen_before_source_interactions": True,
    "source": SOURCE_COMMIT,
    "allowed_calls": ["reset", "do"],
    "allowed_event_fields": [
        "stage", "observation", "action", "next_observation",
        "reward", "terminated", "truncated", "valid_actions"
    ],
    "forbidden_to_learner": [
        "get_graph", "ctf_do", "u", "env", "full_info",
        "private_scm", "oracle", "source_code"
    ],
    "public_smoke_seeds": [759011, 759013],
    "fit_seeds_reserved_not_run": list(range(760000, 760008)),
    "validation_seeds_reserved_not_run": list(range(760100, 760104)),
    "dev_seeds_reserved_not_run": list(range(760200, 760204)),
    "max_actions_per_episode": 2,
    "model_fitted": False,
    "independent_scientific_source_birth": False,
    "protected_original_first_use": False,
    "equal_information_baselines_planned": [
        "fitted_tabular_context_value",
        "fitted_recurrent_or_episodic_predictor"
    ]
}

def git(repo: Path, *args: str) -> str:
    cmd = ["git", "-C", str(repo), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if proc.returncode:
        raise RuntimeError("UPSTREAM_GIT_CUSTODY_INVALID:" + " ".join(args))
    return proc.stdout.strip()

def methods(source: bytes, cls: str) -> set[str]:
    tree=ast.parse(source.decode("utf-8"))
    return {
        method.name
        for definition in tree.body
        if isinstance(definition,ast.ClassDef) and definition.name==cls
        for method in definition.body
        if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef))
    }

def inspect_upstream(root: Path) -> dict:
    root=root.resolve(strict=True)
    head=git(root,"rev-parse","HEAD")
    tree=git(root,"rev-parse","HEAD^{tree}")
    if head!=SOURCE_COMMIT or tree!=SOURCE_TREE:
        raise RuntimeError("AC10_EXACT_UPSTREAM_COMMIT_OR_TREE_MISMATCH")
    actual={}
    for name,expected in BLOBS.items():
        file=root/name
        if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(root):
            raise RuntimeError("AC10_UPSTREAM_FILE_MISSING_OR_UNSAFE:"+name)
        blob=git(root,"hash-object","--",name)
        if blob!=expected:
            raise RuntimeError("AC10_UPSTREAM_BLOB_MISMATCH:"+name)
        actual[name]=blob
    if git(root,"status","--porcelain","--untracked-files=no"):
        raise RuntimeError("AC10_AUTHENTIC_CHECKOUT_MODIFIED")
    # Use committed Git blob bytes, not checkout LF/CRLF working-tree bytes:
    # Windows checkout can render different physical newline sequences.
    blob_proc=subprocess.run(
        ["git","-C",str(root),"show","HEAD:causal_gym/envs/dtr.py"],
        capture_output=True,timeout=15)
    if blob_proc.returncode:
        raise RuntimeError("AC10_CANNOT_READ_AUTHENTIC_DTR_GIT_BLOB")
    dtr_blob=blob_proc.stdout
    if hashlib.sha1(
        b"blob "+str(len(dtr_blob)).encode("ascii")+b"\\0"+dtr_blob
    ).hexdigest()!=BLOBS["causal_gym/envs/dtr.py"]:
        raise RuntimeError("AC10_DTR_GIT_BLOB_CONTENT_DRIFT")
    dtr=(root/"causal_gym/envs/dtr.py").read_bytes()
    pch=(root/"causal_gym/core/pch.py").read_bytes()
    init=(root/"causal_gym/envs/__init__.py").read_text(encoding="utf-8")
    dtr_scm=methods(dtr,"DTRSCM")
    dtr_pch=methods(dtr,"DTRPCH")
    wrapper=methods(pch,"PCH")
    if not {"reset","step","get_graph"}.issubset(dtr_scm):
        raise RuntimeError("AC10_UPSTREAM_SCM_API_DRIFT")
    if not {"do","see","ctf_do"}.issubset(dtr_pch):
        raise RuntimeError("AC10_UPSTREAM_DTR_PCH_API_DRIFT")
    if not {"_permission_check","__getattribute__","do"}.issubset(wrapper):
        raise RuntimeError("AC10_UPSTREAM_PERMISSION_WRAPPER_DRIFT")
    if "from .dtr import DTRSCM, DTRPCH" not in init:
        raise RuntimeError("AC10_ROOT_ENV_IMPORT_DRIFT")
    if not {"get_graph","ctf_do","env","u"}.issubset(set(PROTO["forbidden_to_learner"])):
        raise RuntimeError("AC10_ALLOWLIST_REGRESSION")
    if not set(PROTO["allowed_calls"]).isdisjoint(PROTO["forbidden_to_learner"]):
        raise RuntimeError("AC10_CALL_WHITELIST_COLLISION")
    if len(PROTO["public_smoke_seeds"])!=2 or not set(PROTO["fit_seeds_reserved_not_run"]).isdisjoint(PROTO["validation_seeds_reserved_not_run"]):
        raise RuntimeError("AC10_FROZEN_PUBLIC_DEVELOPMENT_SEED_DRIFT")
    return {
        "sha":head,"tree":tree,
        "verified_git_blobs":actual,
        "dtr_original_git_blob_sha256":hashlib.sha256(dtr_blob).hexdigest(),
        "dtr_scm_methods":sorted(dtr_scm),
        "dtr_pch_methods":sorted(dtr_pch),
        "pch_permission_methods_verified":True,
        "root_import_fanout":len([line for line in init.splitlines()
                                  if line.startswith("from .")]),
        "required_original_dependencies_visible":True,
        "source_native_episodes_executed":0
    }

def import_probe(root: Path) -> dict:
    # Exact source import. No custom fork, no stub/shim, no step/reset/do.
    # Intentionally no setup.py extra dependency installation: assess whether
    # the exact source works with only the isolated qualification environment.
    env=os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"]="1"
    env["PYTHONPATH"]=str(root)
    code="from causal_gym.envs.dtr import DTRPCH, DTRSCM; print('AC10_REAL_UPSTREAM_DTR_IMPORT_PASS')"
    try:
        p=subprocess.run([sys.executable,"-B","-c",code],
                         cwd=root,env=env,capture_output=True,text=True,
                         timeout=25)
    except subprocess.TimeoutExpired:
        return {"status":"UPSTREAM_IMPORT_TIMEOUT","exit_code":None,
                "failure_class":"IMPORT_TIMEOUT","upstream_code_modified":False}
    ok=p.returncode==0 and "AC10_REAL_UPSTREAM_DTR_IMPORT_PASS" in p.stdout
    # Never copy uncontrolled stderr/stdout to durable report; classify the
    # result. Avoid laundering import failure into source-native execution.
    last=(p.stderr or "").strip().splitlines()
    excerpt=last[-1][:256] if last else ""
    return {
        "status":"UPSTREAM_IMPORT_OK_NO_EPISODES" if ok else "UPSTREAM_IMPORT_BLOCKED",
        "exit_code":p.returncode,
        "failure_class":None if ok else (
            "UPSTREAM_DEPENDENCY_MISSING" if "ModuleNotFoundError" in p.stderr else
            "UPSTREAM_IMPORT_ERROR"),
        "diagnostic_tail":excerpt if not ok else "",
        "upstream_code_modified":False,
        "episode_executed":False
    }

def run(root: Path) -> dict:
    inspected=inspect_upstream(root)
    imported=import_probe(root.resolve())
    result={
        "schema":SCHEMA,
        "scope":"EXACT_UPSTREAM_CODE_COMPATIBILITY_ONLY",
        "upstream":inspected,
        "import_probe":imported,
        "frozen_public_development_plan":PROTO,
        "original_source_interactions_performed":0,
        "native_model_training_performed":False,
        "scientific_first_use":False,
        "original_source_birth_attested":False,
        "controller_or_f139_queue_changed":False,
        "accepted_science_or_native_models_changed":False,
        "source_native_runtime_qualified":imported["status"]=="UPSTREAM_IMPORT_OK_NO_EPISODES",
        "public_dev_fit_or_control_results":None
    }
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--upstream",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    report=run(a.upstream)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("AC10_SOURCE_PINNED=PASS")
    print("AC10_IMPORT_STATUS="+report["import_probe"]["status"])
    print("AC10_SCIENTIFIC_ADMISSION=NO")
    print("AC10_RESULT_SHA256="+hashlib.sha256(a.out.read_bytes()).hexdigest())

if __name__=="__main__":
    main()
