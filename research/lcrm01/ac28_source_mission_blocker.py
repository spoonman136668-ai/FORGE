"""AC-28 exact original source mission-boundary negative evidence (no env imports)."""
from __future__ import annotations
import argparse, ast, hashlib, json, pathlib, subprocess

SCHEMA="forge.ac28.original-cross-family-public-mission-boundary.v1"
OUTCOME="AC28_PUBLIC_MISSION_INCOMPATIBLE__TARGET_TRANSFER_NOT_TESTED"
SOURCE_COMMIT="7f5853792ea7f04f75614661006d87fcf949f26d"
SOURCE_BLOB="974acd6f59d03a3accde838918cf154fedc94c24"
YGG_COMMIT="770244b04d011466458b2335d3951daf7653dc8f"
YGG_R10_BLOB="3917d36ce9f86a2c1b998a0a2f93fb27674a9205"
SOURCE_PATH="minigrid/envs/unlock.py"
R10_PATH="research/native/itd02/r10/public_adapter.py"
ORIGINAL_AC28_FAILED_HEAD="4eee44fe6205a56293c89a03f8bf36702f284ce8"
ORIGINAL_AC28_FAILED_RUN=40844398914

def git(path,*args):
    r=subprocess.run(["git","-C",str(path),*args],capture_output=True,
                      text=True,timeout=15)
    if r.returncode:raise RuntimeError("AC28_PINNED_ORIGINAL_GIT_READ_FAILED")
    return r.stdout.strip()

def pinned(root,commit,path,blob):
    if (git(root,"rev-parse","HEAD")!=commit or
        git(root,"rev-parse","HEAD:"+path)!=blob or
        git(root,"status","--porcelain","--untracked-files=no")):
        raise RuntimeError("AC28_ORIGINAL_SOURCE_BLOB_DRIFT")
    p=subprocess.run(["git","-C",str(root),"show","HEAD:"+path],
                     capture_output=True,timeout=15)
    if p.returncode or not p.stdout:raise RuntimeError("AC28_ORIGINAL_BLOB_MISSING")
    return p.stdout.decode("utf-8")

def original_missions(unlock,ygg):
    tree=ast.parse(unlock)
    clazz=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="UnlockEnv"),None)
    if clazz is None:raise RuntimeError("AC28_ORIGINAL_UNLOCK_CLASS_MISSING")
    method=next((n for n in clazz.body if isinstance(n,ast.FunctionDef) and n.name=="_gen_mission"),None)
    if method is None:raise RuntimeError("AC28_ORIGINAL_UNLOCK_MISSION_METHOD_MISSING")
    source=next((n.value.value for n in ast.walk(method)
                 if isinstance(n,ast.Return) and isinstance(n.value,ast.Constant)
                 and isinstance(n.value.value,str)),None)
    if source!="open the door":
        raise RuntimeError("AC28_ORIGINAL_UNLOCK_PUBLIC_MISSION_CHANGED")
    y=ast.parse(ygg)
    valid=next((n.value.value for n in y.body
                if isinstance(n,ast.Assign) and any(
                    isinstance(t,ast.Name) and t.id=="MISSION" for t in n.targets)
                and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)),None)
    pub=next((n for n in y.body if isinstance(n,ast.FunctionDef)
              and n.name=="public_observation"),None)
    if (valid!="use the key to open the door and then get to the goal" or
        pub is None or
        not any(isinstance(n,ast.Raise) and isinstance(n.exc,ast.Call)
                and any(isinstance(a,ast.Constant) and a.value=="R10_PUBLIC_MISSION"
                        for a in n.exc.args) for n in ast.walk(pub)) or
        source==valid):
        raise RuntimeError("AC28_ORIGINAL_MISSION_GUARD_NO_LONGER_CONFLICTS")
    return source,valid

def archived_blocked(raw):
    x=json.loads(raw)
    if (type(x) is not dict or
        x.get("schema")!="itd02.ac28.original-unlock-public-transfer-development.v1" or
        x.get("classification")!="AC28_SOURCE_OR_PROTOCOL_BLOCKED__NO_SCIENCE" or
        x.get("scientific_first_use") is not False or
        x.get("error_type")!="ValueError" or
        x.get("error")!="R10_PUBLIC_MISSION" or
        x.get("canonical_original_source_evidence") is not None or
        x.get("canonical_original_source_sha256") is not None or
        type(x.get("trace_tail")) is not list or
        not any("r10/public_adapter.py" in t for t in x["trace_tail"]) or
        not any('R10_PUBLIC_MISSION' in t for t in x["trace_tail"])):
        raise RuntimeError("AC28_BLOCKED_SOURCE_EVIDENCE_NOT_AUTHENTIC")
    return hashlib.sha256(raw).hexdigest()

def run(unlockroot,yggroot,source_file,out):
    unlock=pinned(unlockroot,SOURCE_COMMIT,SOURCE_PATH,SOURCE_BLOB)
    ygg=pinned(yggroot,YGG_COMMIT,R10_PATH,YGG_R10_BLOB)
    target,expected=original_missions(unlock,ygg)
    digest=archived_blocked(pathlib.Path(source_file).read_bytes())
    report={
        "schema":SCHEMA,"classification":OUTCOME,
        "original_target_env":"MiniGrid-Unlock-v0",
        "original_target_mission":target,"original_r10_required_mission":expected,
        "unaltered_original_unlock_commit":SOURCE_COMMIT,
        "unaltered_original_unlock_blob":SOURCE_BLOB,
        "unaltered_original_ygg_r17_commit":YGG_COMMIT,
        "unaltered_original_ygg_r10_blob":YGG_R10_BLOB,
        "archived_blocked_original_trial_run":ORIGINAL_AC28_FAILED_RUN,
        "archived_blocked_original_trial_head":ORIGINAL_AC28_FAILED_HEAD,
        "archived_blocked_source_report_sha256":digest,
        "original_source_first_new_episode_actions":"NOT_ATTESTED_FROM_BLOCKED_PROCESS",
        "native_transfer_score":"NOT_EVALUABLE",
        "original_target_episodes_newly_executed_by_audit":0,
        "original_target_env_imported_or_reset_by_audit":False,
        "source_public_mission_rewritten":False,
        "original_native_models_edited":False,
        "native_model_or_classical_goal_superiority":False,
        "hidden_objective_or_pose_used":False,
        "scientific_first_use":False,"scientific_admission":False,
        "controller_protected_main_or_queue_changed":False,
    }
    out=pathlib.Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return report
if __name__=="__main__":
    q=argparse.ArgumentParser()
    for k in ("unlockroot","yggroot","source-file","out"):
        q.add_argument("--"+k,type=pathlib.Path,required=True)
    x=q.parse_args()
    r=run(x.unlockroot,x.yggroot,x.source_file,x.out)
    print("AC28_ORIGINAL_CROSS_FAMILY_MISSION_BARRIER=VERIFIED")
    print("AC28_TRANSFER_PERFORMANCE=NOT_TESTED")
    print("AC28_NO_NEW_ORIGINAL_ENV_CALLS_BY_AUDIT=PASS")
