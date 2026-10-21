#!/usr/bin/env python3
"""RC2-P initial-order latency boundaries: source-pinned transient Go test.

No real broker connections, no installed files, no archival financial records,
no full suite and no application build. Tests run on exact original and PR73
with a synthetic in-memory POST acknowledgment; optional synthetic same-volume
filesystem load is measured independently. Detailed fixture output is never
exported from the CI runner.
"""
import collections
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

PIN={"original":"eb5d225ae73b698a59c68d840daf1ec678e1a0ec",
     "candidate":"b8c2052d530cdff93462dfccc21b28f3824e5531"}
PROBE="TestRC2PFirstNativeBuyOrderBoundaries"
CONTROLS={"TestNativeTimingPreservesBodyAndLegacyBoundary",
          "TestDashboardOrderEvidenceDeduplicatesAndNeverResurrectsFills"}
ALLOWED={"pre_post_us","fake_http_ack_us","ack_to_execute_return_us",
         "evidence_callback_us","post_ack_dashboard_model_us",
         "initial_native_total_us","transport_ready_us","posts",
         "evidence_callbacks","native_spans"}
SPAN=re.compile(r"RC2P_SPAN stage=([A-Za-z0-9_.-]+) duration_us=([0-9]+)")
NUMBERS=re.compile(r"([a-z_]+)=(-?[0-9]+)")

def run(argv,cwd,env=None,seconds=130):
    return subprocess.run(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,text=True,
                          check=False,timeout=seconds)

def clean(source,pin,allow_probe=False):
    a=run(["git","-C",str(source),"rev-parse","HEAD"],source)
    b=run(["git","-C",str(source),"status","--porcelain"],source)
    if a.returncode or b.returncode or a.stdout.strip()!=pin:
        raise RuntimeError("FROZEN_SOURCE_IDENTITY_FAILED")
    permitted="?? pkg/rc2p_transient_first_order_test.go"
    status=b.stdout.strip().replace("\\","/")
    if status and (not allow_probe or status!=permitted):
        raise RuntimeError("TEST_WORKSPACE_DIRTY")
    return True

def synthetic_env(out):
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    env=dict(os.environ)
    env.update(GOTOOLCHAIN="local",GOTELEMETRY="off",GOFLAGS="-p=1",
       CGO_ENABLED="0",GOMAXPROCS="2",
       K_TERMINAL_EXECUTION_MODE="PAPER",
       K_TERMINAL_P5_LATENCY="0",K_TERMINAL_NATIVE_TIMING="0",
       K_TERMINAL_TEST_WORKSPACE=str(out))
    for name,sub in (
      ("KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT","native-tail"),
      ("KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT","authenticated-post"),
      ("KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT","private-v2")):
        path=out/sub
        path.mkdir(mode=0o700)
        env[name]=str(path)
    return env

def collect(stdout):
    current=None
    trials=[]
    pending=collections.Counter()
    passed=collections.Counter()
    failed=collections.Counter()
    bad=0
    packages=set()
    for line in stdout.splitlines():
        try:ev=json.loads(line)
        except ValueError:bad+=1;continue
        if ev.get("Package")!="k-terminal/pkg":continue
        action=ev.get("Action")
        name=ev.get("Test")
        if action=="run" and name:
            pending[name]+=1
            if name==PROBE:
                current={"boundaries":None,"stages":{},"status":"INCOMPLETE"}
                trials.append(current)
        if action=="pass" and name:
            passed[name]+=1
            if name==PROBE and current is not None:current["status"]="PASS"
        if action=="fail" and name:
            failed[name]+=1
            if name==PROBE and current is not None:current["status"]="FAIL"
        if action=="pass" and not name:packages.add("pass")
        if action=="fail" and not name:packages.add("fail")
        if action!="output" or name!=PROBE or current is None:continue
        msg=ev.get("Output","")
        if "RC2P_BOUNDARY " in msg:
            found={k:int(v) for k,v in NUMBERS.findall(msg.split("RC2P_BOUNDARY ",1)[1])}
            if set(found)!=ALLOWED or current["boundaries"] is not None:
                raise RuntimeError("MALFORMED_OR_DUPLICATE_ORDER_BOUNDARIES")
            current["boundaries"]=found
        elif "RC2P_SPAN stage=" in msg:
            match=SPAN.search(msg)
            if not match:raise RuntimeError("MALFORMED_NATIVE_SPAN")
            label,us=match.groups()
            prev=current["stages"].setdefault(label,{"count":0,"duration_us":0,"peak_us":0})
            prev["count"]+=1
            prev["duration_us"]+=int(us)
            prev["peak_us"]=max(prev["peak_us"],int(us))
    return trials,pending,passed,failed,bad,packages

def execute(label,source,condition,out):
    env=synthetic_env(out/(label+"-"+condition))
    selected="^(?:"+PROBE+"|"+ "|".join(sorted(CONTROLS))+")$"
    before=time.monotonic()
    try:
        p=run(["go","test","-json","-count=3","-p=1","-parallel=1",
               "-timeout=6m","-run",selected,"./pkg"],source,env,seconds=435)
        rc=p.returncode
        cases,started,passed,failed,errors,packages=collect(p.stdout)
    except subprocess.TimeoutExpired:
        rc=124
        cases=[];errors=0;started=collections.Counter()
        passed=collections.Counter();failed=collections.Counter()
        packages={"fail"}
    target_ok=(len(cases)==3 and all(x["status"]=="PASS" and
        x["boundaries"] and x["boundaries"].get("posts")==1 and
        x["boundaries"].get("evidence_callbacks",0)>=1 and
        x["boundaries"].get("native_spans",0)>=1 for x in cases))
    control_ok=all(started[x]==3 and passed[x]==3 and failed[x]==0 for x in CONTROLS)
    success=(rc==0 and errors==0 and not failed and
       "pass" in packages and "fail" not in packages and target_ok and control_ok)
    return {
      "source":label,"condition":condition,"result":"PASS" if success else "FAIL_NOT_WAIVED",
      "exit":rc,"command_wall_s":round(time.monotonic()-before,3),
      "probe_iterations_expected":3,"probe_iterations_observed":len(cases),
      "original_controls_pass":control_ok,
      "go_json_errors":errors,
      "cases":cases,
      "full_regression_substituted":False
    }

def main():
    if len(sys.argv)!=6:
        raise RuntimeError("ARGS:original candidate probe fsync_worker temp_root")
    original=pathlib.Path(sys.argv[1]).resolve(strict=True)
    candidate=pathlib.Path(sys.argv[2]).resolve(strict=True)
    probe=pathlib.Path(sys.argv[3]).resolve(strict=True)
    pressurefile=pathlib.Path(sys.argv[4]).resolve(strict=True)
    out=pathlib.Path(sys.argv[5]).resolve()
    if out.exists():raise RuntimeError("EXISTING_OUTPUT_DIRECTORY")
    out.mkdir(mode=0o700,parents=True)
    files=[("original",original),("candidate",candidate)]
    for label,source in files:clean(source,PIN[label])
    body=probe.read_bytes()
    if len(body)<3400 or b"TestRC2PFirstNativeBuyOrderBoundaries" not in body:
        raise RuntimeError("INVALID_SOURCE_BOUND_PROBE")
    report={
      "schema":"kterminal.rc2p.native-first-order-boundary-v1",
      "source_pins":PIN,"transient_probe_sha256":hashlib.sha256(body).hexdigest(),
      "fake_network_only":True,"actual_paper_order_or_fill":False,
      "true_WPF_paint_measured":False,"complete_full_regression":False,
      "results":[]}
    temporary=[]
    try:
        for label,source in files:
            dest=source/"pkg"/"rc2p_transient_first_order_test.go"
            if dest.exists():raise RuntimeError("PROBE_FILE_COLLISION")
            dest.write_bytes(body)
            temporary.append(dest)
            clean(source,PIN[label],allow_probe=True)
        for label,source in files:
            row=execute(label,source,"normal",out)
            report["results"].append(row)
            print("KTERM_RC2P_"+label.upper()+"_NORMAL="+row["result"],flush=True)
        folder=out/"fsync-load"
        folder.mkdir(mode=0o700)
        worker=subprocess.Popen([sys.executable,"-B",str(pressurefile),str(folder)],
          cwd=out,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        exit_worker=124
        terminated_early=False
        try:
            until=time.monotonic()+12
            while not (folder/"ready.flag").exists() and time.monotonic()<until:
                if worker.poll() is not None:raise RuntimeError("FSYNC_WORKER_EXIT_BEFORE_READY")
                time.sleep(.05)
            if not (folder/"ready.flag").exists():raise RuntimeError("FSYNC_WORKER_READY_TIMEOUT")
            for label,source in files:
                row=execute(label,source,"fsync_contended",out)
                report["results"].append(row)
                print("KTERM_RC2P_"+label.upper()+"_FSYNC="+row["result"],flush=True)
                terminated_early=terminated_early or worker.poll() is not None
        finally:
            (folder/"stop.flag").write_text("stop",encoding="ascii")
            try:exit_worker=worker.wait(timeout=9)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)
        summary_file=folder/"fsync-summary.json"
        pressure=json.loads(summary_file.read_text(encoding="utf-8")) if summary_file.exists() else {}
        report["pressure"]={"exit":exit_worker,
            "worker_ended_during_case":terminated_early,**pressure}
        report["pressure_valid"]=(exit_worker==0 and not terminated_early
            and pressure.get("count",0)>=20 and pressure.get("write_errors",1)==0)
    finally:
        for target in temporary:
            target.unlink(missing_ok=True)
        for label,source in files:clean(source,PIN[label])
    report["complete_cases"]=len(report["results"])
    report["all_cases_pass"]=all(x["result"]=="PASS" for x in report["results"])
    outfile=out/"rc2p-redacted-initial-order.json"
    outfile.write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    print("KTERM_RC2P_TOTAL_CASES="+str(report["complete_cases"]),flush=True)
    print("KTERM_RC2P_ALL_TARGETED_CASES="+("PASS" if report["all_cases_pass"] else "FAIL_NOT_WAIVED"),flush=True)
    print("KTERM_RC2P_FSYNC_VALID="+str(report.get("pressure_valid",False)).upper(),flush=True)
    print("KTERM_RC2P_SOURCE_RESTORED=PASS",flush=True)
    print("KTERM_RC2P_FULL_WINDOWS_REGRESSION=NOT_RUN_NOT_WAIVED",flush=True)
    print("KTERM_RC2P_INITIAL_ORDER_AND_UI_RENDER_PARITY=NOT_YET_PROVEN",flush=True)
    print("KTERM_RC2P_RELEASE_GATE=BLOCKED",flush=True)
    return 0 if report.get("pressure_valid") and report["all_cases_pass"] else 2

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("KTERM_RC2P_DIAGNOSTIC=FAIL_CLOSED:"+type(e).__name__,flush=True)
        sys.exit(2)
