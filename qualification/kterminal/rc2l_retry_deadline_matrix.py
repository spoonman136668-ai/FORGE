#!/usr/bin/env python3
"""RC2-L bounded Windows diagnosis of one already-failing two-second retry test.

Frozen original and PR #73 sources only. Go tests execute in isolated temporary
test workspaces with simulated local transport; no production app launch, user
data, broker credentials, or source edits. All original retry assertions remain.
The script produces categories and timing only; never prints fixture payloads.
"""
import collections
import json
import os
import pathlib
import re
import subprocess
import sys
import time

BASE="eb5d225ae73b698a59c68d840daf1ec678e1a0ec"
CANDIDATE="b8c2052d530cdff93462dfccc21b28f3824e5531"
TARGET="TestCanceledBuyRetryActualAllNineMakerAttemptsWithinOriginalWindow"
NEIGHBOR="TestCanceledBuyRetryActualReadyContinuesSameEventAndTimer"
PATTERNS={
 "MAKER_WINDOW_EXPIRED_OR_BUDGET":"full original native maker budget failed",
 "MAKER_ATTEMPT_TRUNCATED":"authorized maker budget truncated",
 "REPLACEMENT_ORDER_IDENTITY":"attempt identity/policy/quantity changed",
 "DUPLICATE_RETRY":"duplicate terminal proof resubmitted",
 "RESERVATION_MISMATCH":"logical event acquired duplicate reservations",
 "TEST_TIMEOUT":"panic: test timed out",
}
CASES=(
 ("solo_repeated", "^(?:"+TARGET+")$",4,0),
 ("preceding_fixture_repeated","^(?:"+NEIGHBOR+"|"+TARGET+")$",3,0),
 ("cpu_contended_repeated","^(?:"+TARGET+")$",4,2),
)

def run(argv,cwd,env=None,timeout=120):
    return subprocess.run(argv,cwd=cwd,env=env,capture_output=True,
        text=True,check=False,timeout=timeout)

def fixture_environment(workspace):
    workspace.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ)
    env["K_TERMINAL_TEST_WORKSPACE"]=str(workspace)
    for name,child in (
        ("KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT","native-tail"),
        ("KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT","authenticated-post"),
        ("KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT","private-v2"),
    ):
        path=workspace/child
        path.mkdir(mode=0o700)
        env[name]=str(path)
    env.update(GOTOOLCHAIN="local",GOTELEMETRY="off",GOFLAGS="-p=1",
        GOMAXPROCS="2",CGO_ENABLED="0",K_TERMINAL_EXECUTION_MODE="PAPER",
        K_TERMINAL_NATIVE_TIMING="0",K_TERMINAL_P5_LATENCY="0")
    return env

def pressure_program():
    return ('import hashlib,time; d=b"KTERM_RC2L_LOAD" * 1024; stop=time.monotonic()+95; '
            'exec("while time.monotonic()<stop:\n d=hashlib.sha256(d).digest()*1024")')

def run_case(directory,label,condition,regex,count,pressure,workspace):
    env=fixture_environment(workspace)
    workers=[]
    try:
        for _ in range(pressure):
            workers.append(subprocess.Popen([sys.executable,"-c",pressure_program()],
                cwd=directory,env=env,stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL))
        cmd=["go","test","-json","-count="+str(count),"-p=1","-parallel=1",
            "-timeout=4m","-run",regex,"./pkg"]
        started=time.perf_counter()
        try:
            proc=run(cmd,directory,env,timeout=300)
        except subprocess.TimeoutExpired:
            return {"label":label,"mode":condition,"status":"FAIL_NOT_WAIVED",
                    "reason_classes":["GO_PROCESS_TIMEOUT"],"go_exit":124,
                    "target_pass":0,"target_fail":0,"target_run":0,
                    "elapsed_s":300,"target_elapsed_s":[],"neighbor_pass":0}
        elapsed=round(time.perf_counter()-started,3)
        counts=collections.Counter()
        markers=set()
        durations=[]
        reasonclasses=set()
        missing_json=0
        for line in proc.stdout.splitlines():
            try:e=json.loads(line)
            except ValueError:missing_json+=1;continue
            action=e.get("Action")
            name=e.get("Test")
            if name in (TARGET,NEIGHBOR) and action in ("run","pass","fail"):
                counts[(name,action)]+=1
                if name==TARGET and action in ("pass","fail") and isinstance(e.get("Elapsed"),(int,float)):
                    durations.append(round(e["Elapsed"],6))
            if action=="output" and (name==TARGET or name is None):
                msg=e.get("Output","")
                for code,needle in PATTERNS.items():
                    if needle in msg:reasonclasses.add(code)
                if "FAIL" in msg and not name:markers.add("PACKAGE_FAIL_OUTPUT")
        target_ok=(counts[(TARGET,"pass")]==count and
            counts[(TARGET,"run")]==count and counts[(TARGET,"fail")]==0)
        neighbor_expected=count if condition=="preceding_fixture_repeated" else 0
        neighbor_ok=counts[(NEIGHBOR,"pass")]==neighbor_expected and counts[(NEIGHBOR,"fail")]==0
        good=proc.returncode==0 and target_ok and neighbor_ok and missing_json==0
        if not good and not reasonclasses:
            reasonclasses.add("UNCLASSIFIED_FAILURE_NEEDS_LOCAL_JSON")
        return {"label":label,"mode":condition,
            "status":"PASS" if good else "FAIL_NOT_WAIVED",
            "go_exit":proc.returncode,
            "target_run":counts[(TARGET,"run")],
            "target_pass":counts[(TARGET,"pass")],
            "target_fail":counts[(TARGET,"fail")],
            "neighbor_pass":counts[(NEIGHBOR,"pass")],
            "reason_classes":sorted(reasonclasses),
            "elapsed_s":elapsed,"target_elapsed_s":durations,
            "json_error_count":missing_json}
    finally:
        for worker in workers:
            try:worker.terminate()
            except OSError:pass
        for worker in workers:
            try:worker.wait(timeout=3)
            except subprocess.TimeoutExpired:worker.kill()

def main():
    if len(sys.argv)!=4:raise RuntimeError("EXPECTED_ORIGINAL_CANDIDATE_TEMP")
    original=pathlib.Path(sys.argv[1]).resolve(strict=True)
    candidate=pathlib.Path(sys.argv[2]).resolve(strict=True)
    root=pathlib.Path(sys.argv[3]).resolve()
    if root.exists():raise RuntimeError("WORKSPACE_ALREADY_EXISTS")
    root.mkdir(mode=0o700)
    for path,sha in ((original,BASE),(candidate,CANDIDATE)):
        p=run(["git","-C",str(path),"rev-parse","HEAD"],path)
        if p.returncode or p.stdout.strip()!=sha:raise RuntimeError("SOURCE_IDENTITY_DRIFT")
        d=run(["git","-C",str(path),"status","--porcelain"],path)
        if d.returncode or d.stdout.strip():raise RuntimeError("SOURCE_DIRTY")
    result={"schema":"kterminal.rc2l.retry-deadline-load-interaction.v1",
        "original_sha":BASE,"candidate_sha":CANDIDATE,
        "hard_two_second_window_unmodified":True,"all_assertions_unmodified":True,
        "no_live_broker":True,"cases":[]}
    for label,directory in (("original",original),("candidate",candidate)):
        for condition,regex,count,pressure in CASES:
            row=run_case(directory,label,condition,regex,count,pressure,
                root/(label+"-"+condition))
            result["cases"].append(row)
            print("KTERM_RC2L_"+label.upper()+"_"+condition.upper()+
                "="+row["status"]+"_TARGET_PASS_"+str(row["target_pass"])+
                "_TARGET_FAIL_"+str(row["target_fail"]))
            if row["reason_classes"]:
                print("KTERM_RC2L_REASON_CLASSES="+",".join(row["reason_classes"]))
    out=root/"rc2l-redacted-evidence.json"
    out.write_text(json.dumps(result,sort_keys=True,indent=2),encoding="utf-8")
    negatives=[x for x in result["cases"] if x["status"]!="PASS"]
    if negatives:print("KTERM_RC2L_STABILITY=NEGATIVES_RETAINED_NOT_WAIVED")
    else:print("KTERM_RC2L_STABILITY=ALL_TARGETED_CASES_PASS_NO_FULL_SUITE_CLAIM")
    print("KTERM_RC2L_FULL_WINDOWS_REGRESSION=NOT_RUN")
    print("KTERM_RC2L_RELEASE=BLOCKED")
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("KTERM_RC2L_DIAGNOSTIC_SETUP=FAIL_CLOSED:"+type(e).__name__)
        sys.exit(2)
