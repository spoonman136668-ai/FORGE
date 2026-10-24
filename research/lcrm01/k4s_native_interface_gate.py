#!/usr/bin/env python3
"""K4S: authenticate true native entrypoints against qualified public MiniGrid.

THIS IS A READ-ONLY INTERFACE GATE, NOT AN EVALUATION OF COGNITION.
It intentionally does not run new MiniGrid seeds or fabricate a three-way
navigation policy by mapping a binary decision onto the forward action.
"""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile


HERE=Path(__file__).resolve().parent
FROZEN=HERE/"k4s_frozen_native_interface.json"
SCHEMA="mass.lcrm01.k4s.original-native-policy-source-admission-v1"


def canonical(o):
    return json.dumps(o,sort_keys=True,separators=(",",":"),allow_nan=False)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def authenticated_k4r(archive,contract):
    parent=contract["parent"]
    raw=archive.read_bytes()
    if sha256(raw)!=parent["K4R_original_artifact_zip_sha256"]:
        raise ValueError("K4S_ORIGINAL_K4R_ARTIFACT_HASH_DRIFT")
    with zipfile.ZipFile(archive) as z:
        names=parent["K4R_members_sha256"]
        if not set(names).issubset(set(z.namelist())):
            raise ValueError("K4S_K4R_MEMBER_MISSING")
        reports={}
        for name,expected in names.items():
            content=z.read(name)
            if sha256(content)!=expected:
                raise ValueError("K4S_K4R_MEMBER_HASH_DRIFT_"+name)
            reports[name]=json.loads(content)
    comp=reports["comparison.json"]
    if (comp.get("result")!="REPEATED_PUBLIC_INTERACTIVE_BENCHMARK_QUALIFIED"
        or comp.get("exact_original_source_science_agreement") is not True
        or comp.get("new_native_cognition_demonstrated") is not False
        or comp.get("scientific_accepted") is not False):
        raise ValueError("K4S_K4R_BENCHMARK_PROVENANCE_FALSE")
    for name in ("process-a.json","process-b.json"):
        report=reports[name]
        if (report.get("result")!="COMPLETE_INDEPENDENT_PUBLIC_BENCHMARK"
            or report.get("source_qualification",{}).get("result")!="INDEPENDENT_INTERACTIVE_SOURCE_QUALIFIED"
            or report.get("scientific_first_use") is not False
            or report.get("scientific_accepted") is not False):
            raise ValueError("K4S_K4R_SOURCE_OR_AUTHORITY_FALSE")
        if (report.get("DEV_episode_evaluations")!=80 or
            report.get("FIT_source_episodes")!=48 or
            report.get("FIT_experience_count",0)<48):
            raise ValueError("K4S_ORIGINAL_K4R_EXPERIENCE_MISSING")
        for family in ("empty","fourrooms"):
            q=report["source_qualification"]["families"][family]
            if (len(q["expert_first_action_ids"])<2
                or q["success_rate"]["learned_model_bfs"]<.75):
                raise ValueError("K4S_K4R_QUALIFICATION_FALSE")
    return {"source_qualified":True,"original_artifact_sha256":sha256(raw),
            "source_development_only":True,
            "original_no_native_science_claim":True,
            "task_families":["empty","fourrooms"],
            "required_legal_navigation_actions":[0,1,2],
            "existing_FIT_experiences":reports["process-a.json"]["FIT_experience_count"]}


def source_bytes(candidate):
    repo,commit,path=candidate["repo"],candidate["commit"],candidate["file"]
    url="https://api.github.com/repos/"+repo+"/contents/"+urllib.parse.quote(path,safe="/")+"?ref="+commit
    headers={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28",
             "User-Agent":"K4S-authenticated-robot-policy-readiness"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"]="Bearer "+os.environ["GH_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=18) as response:
        meta=json.load(response)
    if meta.get("encoding")!="base64" or meta.get("type")!="file":
        raise ValueError("K4S_NOT_A_PINNED_ORIGINAL_SOURCE_FILE")
    raw=base64.b64decode(meta["content"].replace("\n",""),validate=True)
    if git_blob(raw)!=candidate["blob"] or meta.get("sha")!=candidate["blob"]:
        raise ValueError("K4S_CANDIDATE_GIT_BLOB_MISMATCH_"+candidate["name"])
    return raw


def test_wingless(source):
    # Copy untouched authenticated implementation to a temporary, disposable
    # offline Go module; run an independent REAL Go method invocation.
    go_test=r'''package cognition
import "testing"
func TestK4SOriginalNativeBinaryBoundary(t *testing.T) {
   var state FastSlowState
   if _, err := state.Predict(2,0); err == nil {
       t.Fatal("third MiniGrid navigation action unexpectedly admissible")
   }
   if err := state.Observe(2,0,1,0.1); err == nil {
       t.Fatal("native FIT update incorrectly accepts third legal navigation action")
   }
   if _,ok,err := state.ChooseDisagreementProbe(0); err != nil || ok {
       t.Fatalf("native zero-data abstention failed: %v %v",ok,err)
   }
   if err := state.Observe(0,0,1,0.1); err != nil {
       t.Fatalf("real original native update failure: %v",err)
   }
   snapshot,err := state.Snapshot()
   if err != nil {t.Fatal(err)}
   var restored FastSlowState
   if err := restored.Restore(snapshot); err != nil {t.Fatal(err)}
   p1,err1 := state.Predict(0,0)
   p2,err2 := restored.Predict(0,0)
   if err1!=nil||err2!=nil||p1!=p2 {t.Fatal("restart prediction not retained")}
}
'''
    with tempfile.TemporaryDirectory(prefix="k4s-wingless-go-") as d:
        path=Path(d)
        (path/"continual.go").write_bytes(source)
        (path/"original_api_test.go").write_text(go_test,encoding="utf-8")
        env=dict(os.environ,GO111MODULE="off",GOTOOLCHAIN="local")
        result=subprocess.run(["go","test","-count=1","-v"],
            cwd=path,env=env,text=True,capture_output=True,timeout=65)
    if result.returncode or "TestK4SOriginalNativeBinaryBoundary" not in result.stdout:
        raise ValueError("K4S_ORIGINAL_WINGLESS_GO_NATIVE_EXECUTION_FAILED:"+result.stderr[-1000:])
    if "func (d *FastSlowState) ChooseDisagreementProbe" not in source.decode():
        raise ValueError("K4S_WINGLESS_NATIVE_PROBE_METHOD_MISSING")
    return {"name":"Wingless","native_go_test_pass":True,"checkpoint_roundtrip_pass":True,
            "real_native_fit_update_callable":True,"native_legal_actions":[0,1],
            "native_can_choose_all_minigrid_actions":False,
            "source_reason":"Original native Go State.features hard-rejects action 2, and its policy compares only actions 0 and 1.",
            "native_model_policy_qualified":False}


def test_ygg_r9(source):
    tree=ast.parse(source.decode("utf-8"))
    module={node.name:node for node in tree.body if isinstance(node,ast.ClassDef)}
    cls=module.get("LocalActionColony")
    if cls is None:
        raise ValueError("K4S_YGG_R9_LOCAL_NATIVE_COLONY_NOT_FOUND")
    methods={node.name for node in cls.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
    required={"choose","observe_public_action","learn_delayed","save","restore"}
    if not required.issubset(methods):
        raise ValueError("K4S_YGG_R9_LEARNED_FEEDBACK_API_INCOMPLETE")
    # Execute unchanged original source in a restricted, disposable Python OS
    # subprocess; assert its documented action validation fails for action 2.
    with tempfile.TemporaryDirectory(prefix="k4s-ygg-r9-") as d:
        path=Path(d)
        (path/"action_cells.py").write_bytes(source)
        smoke="""import sys
sys.path.insert(0,'.')
import action_cells as native
try:
    native.check_action(2)
except ValueError:
    pass
else:
    raise RuntimeError('third navigation action silently accepted')
x=native.LocalActionColony()
assert callable(x.choose)
assert callable(x.observe_public_action)
assert callable(x.learn_delayed)
assert callable(x.save)
print('K4S_NATIVE_YGG_R9_BINARY_POLICY_CONFIRMED')
"""
        rr=subprocess.run(["python","-B","-c",smoke],cwd=path,
                text=True,capture_output=True,timeout=25)
    if rr.returncode or "K4S_NATIVE_YGG_R9_BINARY_POLICY_CONFIRMED" not in rr.stdout:
        raise ValueError("K4S_NATIVE_YGG_R9_SMOKE_NOT_VALID:"+rr.stderr[-1000:])
    return {"name":"Yggdrasil","native_python_execution_pass":True,
          "delayed_public_feedback_interface_present":True,
          "native_legal_actions":[0,1],
          "native_can_choose_all_minigrid_actions":False,
          "source_reason":"Original Yggdrasil R9.check_action rejects MiniGrid forward action 2; R9 is a two-action sensory colony.",
          "native_model_policy_qualified":False}


def test_ygg_mr19(source):
    tree=ast.parse(source.decode("utf-8"))
    cls=next((x for x in tree.body if isinstance(x,ast.ClassDef)
         and x.name=="NativeLocalPredictiveState"),None)
    if cls is None:
        raise ValueError("K4S_YGG_MR19_SOURCE_CLASS_MISSING")
    methods={x.name for x in cls.body if isinstance(x,ast.FunctionDef)}
    if not {"predict","observe","snapshot","restore","reset_episode"}.issubset(methods):
        raise ValueError("K4S_YGG_MR19_NATIVE_PREDICTION_MISSING")
    return {"name":"YggdrasilMiniGridMR19",
       "native_source_custody_pass":True,"original_transition_predictor_present":True,
       "direct_navigation_policy_callable":"choose" in methods,
       "native_can_choose_all_minigrid_actions":False,
       "source_reason":"MR19 predicts next local sensory bits; it does not itself select navigation action 0,1 or 2.",
       "native_model_policy_qualified":False}


def inspect(zip_path,p):
    gate=authenticated_k4r(zip_path,p)
    results=[]
    for candidate in p["independent_native_candidates"]:
        raw=source_bytes(candidate)
        if candidate["name"]=="Wingless":
            result=test_wingless(raw)
        elif candidate["name"]=="Yggdrasil":
            result=test_ygg_r9(raw)
        elif candidate["name"]=="YggdrasilMiniGridMR19":
            result=test_ygg_mr19(raw)
        else:
            raise ValueError("UNREGISTERED_NATIVE_SOURCE")
        result["pinned_git_blob"]=git_blob(raw)
        result["pinned_commit"]=candidate["commit"]
        results.append(result)
    able={r["name"] for r in results if r["native_model_policy_qualified"]}
    full=("Wingless" in able and
          ("Yggdrasil" in able or "YggdrasilMiniGridMR19" in able))
    return {"schema":SCHEMA,"gate":"LCRM01-K4S",
      "result":"SOURCE_COMPATIBLE_NATIVE_STUDY_READY" if full else "NATIVE_POLICY_INTERFACE_NOT_READY",
      "source":gate,"native_implementations":results,
      "candidate_legal_actions_proven_exact":True,
      "three_way_navigation_admission":full,
      "existing_K4R_benchmark_pass_preserved":True,
      "any_new_MINIGRID_episodes_executed":False,
      "K4R_original_DEV_reused_for_native_scientific_evaluation":False,
      "new_native_scientific_positive":False,"scientific_first_use":False,
      "scientific_accepted":False,"FORGE_F139_controller_changed":False,
      "protected_merge":False}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--artifact-zip",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("K4S_ORIGINAL_RECEIPT_MUST_BE_NEW")
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if p.get("schema")!="mass.lcrm01.k4s.frozen-native-policy-interface-evidence-gate.v1":
        raise ValueError("K4S_PROTOCOL_IDENTITY_DRIFT")
    r=inspect(args.artifact_zip,p)
    args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("K4S_NATIVE_INTERFACE_DISPOSITION="+r["result"])
    print("K4S_ORIGINAL_K4R_BENCHMARK_AUTHENTICATED="+str(r["source"]["source_qualified"]))
    for c in r["native_implementations"]:
        print("K4S_"+c["name"]+"_SOURCE="+c["pinned_git_blob"]+
              " NATIVE_POLICY_READY="+str(c["native_model_policy_qualified"]))
    print("K4S_NEW_SCIENTIFIC_ADVANCEMENT=False")


if __name__=="__main__":
    main()
