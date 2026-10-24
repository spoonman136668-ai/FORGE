#!/usr/bin/env python3
"""K4V: AUTHENTIC already-consumed FIT replay, no MiniGrid simulator or new reset.

Source files are fetched from exact native-owned commits and SHA1 Git blob pinned.
Only K4R's recorded FIT source is allowed for replay. CHECK/DEV are not evaluated.
"""
import argparse
import base64
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"k4v_frozen_native_fit_replay.json"
def sha256(raw):
    return hashlib.sha256(raw).hexdigest()
def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\0"+raw).hexdigest()
def fail(reason):
    raise RuntimeError("K4V_FAIL_CLOSED_"+reason)

def extract_frozen(archive,contract):
    raw=archive.read_bytes()
    pinned=contract["source"]
    if sha256(raw)!=pinned["artifact_zip_sha256"]:
        fail("K4R_ZIP_HASH")
    with zipfile.ZipFile(archive) as z:
        if not set(pinned["members_sha256"]).issubset(set(z.namelist())):
            fail("K4R_MISSING_ARCHIVE_MEMBER")
        files={}
        for name,digest in pinned["members_sha256"].items():
            member=z.read(name)
            if sha256(member)!=digest:fail("K4R_MEMBER_SHA_"+name)
            files[name]=json.loads(member)
    comp=files["comparison.json"]
    if (comp.get("result")!="REPEATED_PUBLIC_INTERACTIVE_BENCHMARK_QUALIFIED"
        or comp.get("exact_original_source_science_agreement") is not True
        or comp.get("scientific_first_use") is not False
        or comp.get("scientific_accepted") is not False):
        fail("ORIGINAL_BENCHMARK_AUTHORITY")
    return files

def source_bytes(spec):
    repo,commit,path=spec["repo"],spec["commit"],spec["file"]
    if not re.fullmatch(r"[a-f0-9]{40}",commit):
        fail("SOURCE_COMMIT_NOT_IMMUTABLE")
    url="https://api.github.com/repos/"+repo+"/contents/"+urllib.parse.quote(path,safe="/")+"?ref="+commit
    headers={"Accept":"application/vnd.github+json","User-Agent":"mass-k4v-readonly-fit-verifier",
             "X-GitHub-Api-Version":"2022-11-28"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"]="Bearer "+os.environ["GH_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=20) as response:
        meta=json.load(response)
    if meta.get("encoding")!="base64" or meta.get("type")!="file":
        fail("NATIVE_FILE_RESPONSE")
    raw=base64.b64decode(meta["content"].replace("\\n",""),validate=True)
    if git_blob(raw)!=spec["git_blob"] or meta["sha"]!=spec["git_blob"]:
        fail("NATIVE_BLOB_IDENTITY_"+spec["name"])
    return raw

def state_key(family,pos,direction,goal,blocked):
    x,y=pos;gx,gy=goal;dx,dy=gx-x,gy-y
    return ":".join(map(str,(family,(dx>0)-(dx<0),(dy>0)-(dy<0),
                              min(3,(abs(dx)+abs(dy))//4),direction,int(blocked))))
def to_public(family,pos,direction,key,goal):
    if len(pos)!=2 or any(type(x) is not int or not 0<=x<=64 for x in pos):
        fail("PUBLIC_POSITION")
    if type(direction) is not int or not 0<=direction<=3:
        fail("PUBLIC_DIRECTION")
    parts=key.split(":")
    if len(parts)!=6 or parts[-1] not in ("0","1"):
        fail("PUBLIC_KEY_FORMAT")
    blocked=parts[-1]=="1"
    if state_key(family,pos,direction,goal,blocked)!=key:
        fail("SOURCE_PUBLIC_KEY_MISMATCH")
    return {"x":pos[0],"y":pos[1],"goal_x":goal[0],"goal_y":goal[1],
            "direction":direction,"front_blocked":blocked}

def original_fit(report,contract):
    if (report.get("schema")!="mass.lcrm01.k4r.original-independent-interactive-world-source.v1"
        or report.get("gate")!="LCRM01-K4R"
        or report.get("source_commit")!=contract["source"]["upstream_minigrid_commit"]
        or report.get("result")!="COMPLETE_INDEPENDENT_PUBLIC_BENCHMARK"
        or report.get("scientific_first_use") is not False
        or report.get("scientific_accepted") is not False
        or report.get("FIT_source_episodes")!=48
        or report.get("FIT_experience_count")!=5955):
        fail("FIT_PROTOCOL_IDENTITY")
    orig=report["FIT_original_start_records"]
    if len(orig)!=48:fail("FIT_START_COUNT")
    goals={}
    for item in orig:
        family,seed=item["family"],item["seed"]
        if (family not in ("empty","fourrooms") or type(seed) is not int
            or seed not in range(1100,1124) or
            not isinstance(item.get("public_start_sha256"),str)
            or not re.fullmatch("[a-f0-9]{64}",item["public_start_sha256"])):
            fail("FIT_START_ROLE")
        key=(family,seed)
        if key in goals:fail("FIT_DUPLICATE_START")
        goal=item["public_goal"]
        if len(goal)!=2 or any(type(n) is not int or not 0<=n<=64 for n in goal):
            fail("FIT_GOAL_NOT_PUBLIC")
        goals[key]=goal
    if len(goals)!=48 or any(sum(k[0]==family for k in goals)!=24 for family in ("empty","fourrooms")):
        fail("FIT_FAMILY_EXHAUSTIVENESS")
    rows=report["FIT_source_transitions"]
    if len(rows)!=5955:fail("FIT_ORIGINAL_TRANSITION_COUNT")
    projected=[]
    input_actions=[0,0,0]
    for i,r in enumerate(rows):
        family,seed=r["family"],r["world_seed"]
        if type(seed) is not int or (family,seed) not in goals:fail("FIT_ROW_NOT_ORIGINAL")
        a=r["action"]; reward=r["reward"]
        if type(a) is not int or a not in (0,1,2):fail("FIT_ILLEGAL_ACTION")
        if type(reward) not in (int,float) or not math.isfinite(reward):
            fail("FIT_NONFINITE_REWARD")
        if type(r["terminated"]) is not bool:fail("FIT_TERMINAL_TYPE")
        goal=goals[(family,seed)]
        before=to_public(family,r["pos"],r["dir"],r["start_key"],goal)
        after=to_public(family,r["next_pos"],r["next_dir"],r["next_key"],goal)
        if (a in (0,1) and before["x"]!=after["x"]) or (
              a in (0,1) and before["y"]!=after["y"]):
            fail("FIT_TURN_MOVED")
        if a==2 and before["direction"]!=after["direction"]:
            fail("FIT_FORWARD_ROTATED")
        input_actions[a]+=1
        projected.append({"before":before,"action":a,"after":after,
                          "reward":float(reward),"terminal":r["terminated"]})
    if min(input_actions)<=0:fail("FIT_NO_TRI_ACTION_SUPPORT")
    return projected,input_actions

def replay_wing(rows,source,test_source,tempdir,tag):
    folder=tempdir/("wing-"+tag);folder.mkdir()
    (folder/"policy.go").write_bytes(source)
    (folder/"k4v_wing_native_fit_test.go").write_bytes(test_source)
    (folder/"original_fit.json").write_bytes(canonical(rows))
    env=dict(os.environ,GO111MODULE="off",GOTOOLCHAIN="local",K4V_INPUT=str(folder/"original_fit.json"),
             K4V_OUTPUT=str(folder/"receipt.json"),K4V_SNAPSHOT=str(folder/"snapshot.json"),
             K4V_SENTINEL=str(folder/"sentinel.json"))
    start=time.process_time()
    result=subprocess.run(["go","test","-count=1","-run","^TestK4VActualFITReplay$","-v"],
                          env=env,cwd=folder,text=True,capture_output=True,timeout=150)
    if result.returncode!=0:
        fail("WINGLESS_ORIGINAL_NATIVE_RUN_"+result.stdout[-800:]+result.stderr[-500:])
    if "K4V_WINGLESS_FIT_REPLAY=PASS" not in result.stdout:fail("WINGLESS_SOURCE_RECEIPT")
    receipt=json.loads((folder/"receipt.json").read_text())
    if (receipt.get("replayed")!=5955 or receipt.get("updates")!=5955
        or receipt.get("action_counts")!=[sum(x["action"]==a for x in rows) for a in range(3)]
        or receipt.get("cold_restored") is not True):
        fail("WINGLESS_FIT_REPLAY_ACCOUNTING")
    receipt["elapsed_python_cpu_seconds"]=time.process_time()-start
    return receipt

def replay_ygg(rows,source,tempdir,tag):
    folder=tempdir/("ygg-"+tag);folder.mkdir()
    (folder/"native_policy.py").write_bytes(source)
    sys.path.insert(0,str(folder))
    previous=sys.modules.pop("native_policy",None)
    try:
        native=importlib.import_module("native_policy")
        policy=native.GridColony()
        chosen=[0,0,0];acted=[0,0,0]
        start=time.process_time()
        for row in rows:
            before=native.PublicGrid(**row["before"])
            after=native.PublicGrid(**row["after"])
            action=policy.choose(before)
            if action not in (0,1,2):fail("YGG_ILLEGAL_NATIVE_CHOICE")
            chosen[action]+=1;acted[row["action"]]+=1
            policy.observe(before,row["action"],after,row["reward"],row["terminal"])
        if policy.feedback_updates!=len(rows):
            fail("YGG_MISSED_ORIGINAL_FIT_UPDATE")
        payload=policy.save()
        restored=native.GridColony.restore(payload)
        last=native.PublicGrid(**rows[-1]["after"])
        expected=policy.choose(last)
        if restored.choose(last)!=expected:fail("YGG_RESTORE_ACTION_DRIFT")
        (folder/"snapshot.json").write_bytes(payload)
        (folder/"sentinel.json").write_bytes(canonical(row["after"]))
        check="""import sys,json,pathlib
sys.path.insert(0,sys.argv[1])
from native_policy import GridColony,PublicGrid
p=GridColony.restore(pathlib.Path(sys.argv[2]).read_bytes())
v=PublicGrid(**json.loads(pathlib.Path(sys.argv[3]).read_bytes()))
assert p.choose(v)==int(sys.argv[4])
print('K4V_YGG_FIT_COLD_RESTORE=PASS')
"""
        cold=subprocess.run([sys.executable,"-B","-c",check,str(folder),str(folder/"snapshot.json"),
             str(folder/"sentinel.json"),str(expected)],text=True,capture_output=True,timeout=20)
        if cold.returncode or "K4V_YGG_FIT_COLD_RESTORE=PASS" not in cold.stdout:
            fail("YGG_FIT_COLD_RESTORE")
        return {"schema":"mass.lcrm01.k4v.yggdrasil-actual-fit-replay.v1",
                "replayed":len(rows),"action_counts":acted,"choice_counts":chosen,
                "updates":policy.feedback_updates,"cold_restored":True,
                "checkpoint_sha256":sha256(payload),"last_action":expected,
                "elapsed_python_cpu_seconds":time.process_time()-start}
    finally:
        sys.modules.pop("native_policy",None)
        if previous is not None:sys.modules["native_policy"]=previous
        sys.path.pop(0)

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--archive",required=True,type=Path)
    a.add_argument("--output",required=True,type=Path)
    a.add_argument("--wing-test",required=True,type=Path)
    args=a.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():fail("RECEIPT_ALREADY_EXISTS")
    contract=json.loads(FROZEN.read_text())
    if contract.get("schema")!="mass.lcrm01.k4v.frozen-authentic-fit-only-native-policy-replay-v1":
        fail("FROZEN_PROTOCOL_DRIFT")
    files=extract_frozen(args.archive,contract)
    natives={r["name"]:source_bytes(r) for r in contract["pinned_independent_native"]}
    with tempfile.TemporaryDirectory(prefix="k4v-fit-source-only-") as scratch:
        root=Path(scratch);cases={}
        for label in ("a","b"):
            rows,counts=original_fit(files["process-"+label+".json"],contract)
            wing=replay_wing(rows,natives["Wingless"],args.wing_test.read_bytes(),root,label)
            ygg=replay_ygg(rows,natives["Yggdrasil"],root,label)
            for receipt in (wing,ygg):
                if receipt["action_counts"]!=counts:
                    fail("NATIVE_ORIGINAL_ACTION_ACCOUNTING")
            cases[label]={"fit_sha256":sha256(canonical(rows)),"original_source_transition_count":len(rows),
                          "source_action_counts":counts,"wingless":wing,"yggdrasil":ygg}
        def science_only(d):
            return json.loads(json.dumps(d,sort_keys=True),object_hook=lambda obj:{
                k:v for k,v in obj.items() if k!="elapsed_python_cpu_seconds"})
        if science_only(cases["a"])!=science_only(cases["b"]):
            fail("ORIGINAL_PROCESS_REPLAY_NONREPRODUCIBLE")
    receipt={"schema":"mass.lcrm01.k4v.authenticated-fit-only-native-replay.v1",
      "gate":"K4V","result":"AUTHENTIC_FIT_NATIVE_SOURCE_ONLY_REPLAY_PASS",
      "original_k4r_artifact_sha256":contract["source"]["artifact_zip_sha256"],
      "pinned_native_git_blobs":{s["name"]:s["git_blob"] for s in contract["pinned_independent_native"]},
      "source_fit_only":True,"new_original_minigrid_episodes":0,
      "original_check_dev_reused_for_evaluation":False,
      "native_scientific_accepted":False,"scientific_first_use":False,
      "independent_host_replication":False,"cases":cases}
    args.output.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\\n")
    print("K4V_AUTHENTIC_ORIGINAL_FIT_ONLY=PASS transitions_per_process=5955")
    print("K4V_SOURCE_STREAMS_IDENTICAL=PASS")
    print("K4V_NATIVE_POLICY_REPLAY_AND_COLD_RESTORE=PASS")
    print("K4V_NEW_MINIGRID_EPISODES=0")
    print("K4V_NO_SCIENTIFIC_FIRST_USE_OR_TRANSFER=TRUE")
if __name__=="__main__":
    main()
