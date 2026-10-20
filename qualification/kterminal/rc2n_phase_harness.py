#!/usr/bin/env python3
"""RC2-N measured native nine-maker retry phase audit under normal and CPU load.

The Go probe is test-only, temporary, and byte-identical between frozen original
and PR73. No application runtime file or financial data is edited. Original
two-second window, nine attempts, exact replay/idempotence assertions remain.
The original unmodified test is also executed as a control.
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

BASE="eb5d225ae73b698a59c68d840daf1ec678e1a0ec"
CANDIDATE="b8c2052d530cdff93462dfccc21b28f3824e5531"
TARGET="TestCanceledBuyRetryActualAllNineMakerAttemptsWithinOriginalWindow"
PROBE="TestRC2NNineMakerAttemptsMeasuredUnderOriginalDeadline"
PHASE_FIELDS={
    "attempt","cancel_us","confirm_us","dispatch_us","dispatch_residual_us",
    "confirm_residual_us","post_us","post_calls","balance_hook_us",
    "balance_hook_calls","book_hook_us","book_calls","after_posts",
    "elapsed_from_start_us","elapsed_from_receipt_us","deadline_remaining_us"
}
FAILURE_CLASSES={
    "TWO_SECOND_WINDOW_OR_ATTEMPT_COUNT":"full original native maker budget failed",
    "MAKER_ATTEMPT_TRUNCATION":"authorized maker budget truncated",
    "ORDER_IDENTITY_OR_QUANTITY":"attempt identity/policy/quantity changed",
    "DUPLICATE_RETRY":"duplicate terminal proof resubmitted",
    "RESERVATION_FAILURE":"logical event acquired duplicate reservations",
    "GO_TIMEOUT":"panic: test timed out",
}

def shell(argv,cwd,env=None,timeout=120):
    return subprocess.run(argv,cwd=cwd,env=env,capture_output=True,
        text=True,check=False,timeout=timeout)

def synthetic_env(base):
    base.mkdir(mode=0o700,parents=False,exist_ok=False)
    e=dict(os.environ)
    e.update(GOTOOLCHAIN="local",GOTELEMETRY="off",CGO_ENABLED="0",
             GOFLAGS="-p=1",GOMAXPROCS="2",
             K_TERMINAL_EXECUTION_MODE="PAPER",
             K_TERMINAL_NATIVE_TIMING="0",K_TERMINAL_P5_LATENCY="0",
             K_TERMINAL_TEST_WORKSPACE=str(base))
    for k,name in (
        ("KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT","native-tail"),
        ("KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT","authenticated-post"),
        ("KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT","private-v2"),
    ):
        p=base/name
        p.mkdir(mode=0o700)
        e[k]=str(p)
    return e

def parse_metrics(output,target):
    trials=[]
    current=None
    errors=0
    pkg_fail=False
    for line in output.splitlines():
        try:ev=json.loads(line)
        except ValueError:errors+=1;continue
        name=ev.get("Test")
        action=ev.get("Action")
        if action=="run" and name==target:
            current={"status":"INCOMPLETE","phases":[],"fixture":{},"reason_classes":[]}
            trials.append(current)
        elif current is not None and action in ("pass","fail") and name==target:
            current["status"]=action.upper()
        elif not name and action=="fail":
            pkg_fail=True
        if current is None or action!="output" or name!=target:
            continue
        message=ev.get("Output","")
        for reason,text in FAILURE_CLASSES.items():
            if text in message and reason not in current["reason_classes"]:
                current["reason_classes"].append(reason)
        for kind in ("RC2N_FIXTURE","RC2N_PHASE"):
            if kind not in message:continue
            rest=message.split(kind,1)[1]
            fields={}
            for match in re.finditer(r"([a-z_]+)=(-?[0-9]+)",rest):
                fields[match.group(1)]=int(match.group(2))
            if kind=="RC2N_PHASE":
                if PHASE_FIELDS != set(fields):
                    current["reason_classes"].append("MISSING_PHASE_FIELDS")
                current["phases"].append(fields)
            else:current["fixture"]=fields
    for trial in trials:
        if target==PROBE:
            attempts=trial["phases"]
            if not (len(attempts)==9 and
                    [x.get("attempt") for x in attempts]==list(range(1,10)) and
                    attempts[-1].get("after_posts")==9):
                trial["reason_classes"].append("NINE_ATTEMPT_METRICS_INCOMPLETE")
            if trial["status"]=="PASS" and (not attempts or
                attempts[-1].get("deadline_remaining_us",0)<=0):
                trial["reason_classes"].append("PASS_WITH_NO_REMAINING_RECEIPT_BUDGET")
        if trial["status"]!="PASS" and not trial["reason_classes"]:
            trial["reason_classes"].append("UNCLASSIFIED_FAILURE")
    return trials,errors,pkg_fail

def load_program():
    return ("import hashlib,time\n"
            "buf=b'RC2N_ISOLATED_CPU' * 65536\n"
            "stop=time.monotonic()+180\n"
            "while time.monotonic()<stop:\n"
            "    buf=hashlib.sha256(buf).digest()*32768\n")

def run_case(source,label,condition,kind,repeats,out):
    case_root=out/(label+"-"+condition+"-"+kind)
    env=synthetic_env(case_root)
    target=PROBE if kind=="phase_probe" else TARGET
    workers=[]
    try:
        if condition=="contended":
            for _ in range(2):
                workers.append(subprocess.Popen([sys.executable,"-c",load_program()],
                    cwd=source,env=env,stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL))
        started=time.perf_counter()
        args=["go","test","-json","-count="+str(repeats),"-p=1","-parallel=1",
              "-timeout=5m","-run","^"+target+"$","./pkg"]
        try:
            proc=shell(args,source,env=env,timeout=330)
            elapsed=round(time.perf_counter()-started,3)
            trials,bad,pkg_fail=parse_metrics(proc.stdout,target)
            rc=proc.returncode
        except subprocess.TimeoutExpired:
            elapsed=330
            trials=[]
            bad=0
            pkg_fail=True
            rc=124
        # Export no raw test output or fixture strings, only phases and categories.
        if len(trials)!=repeats:
            state="FAIL_NOT_WAIVED"
        elif rc!=0 or any(x["status"]!="PASS" or x["reason_classes"] for x in trials) or bad:
            state="FAIL_NOT_WAIVED"
        else:
            state="PASS"
        allsteps=[step for trial in trials for step in trial["phases"]]
        summary={
            "source":label,"condition":condition,"mode":kind,"expected_repeats":repeats,
            "observed_repeats":len(trials),"state":state,"go_exit":rc,
            "elapsed_command_s":elapsed,"json_decode_errors":bad,
            "package_failed":pkg_fail,
            "reason_classes":sorted({c for t in trials for c in t["reason_classes"]}),
            "successful_repeats":sum(x["status"]=="PASS" for x in trials),
            "failed_repeats":sum(x["status"]=="FAIL" for x in trials),
            "samples":trials,
        }
        if allsteps:
            maxima={k:max(s[k] for s in allsteps if k in s)
                    for k in ("cancel_us","confirm_us","dispatch_us",
                              "dispatch_residual_us","confirm_residual_us",
                              "post_us","balance_hook_us","book_hook_us",
                              "elapsed_from_start_us") if any(k in s for s in allsteps)}
            maxima["minimum_remaining_us"]=min(s["deadline_remaining_us"]
                for s in allsteps if "deadline_remaining_us" in s)
            summary["phase_maxima_us"]=maxima
        print("KTERM_RC2N_"+label.upper()+"_"+condition.upper()+"_"+kind.upper()+
            "="+state+"_PASS_"+str(summary["successful_repeats"])+
            "_FAIL_"+str(summary["failed_repeats"]))
        if allsteps:
            print("KTERM_RC2N_"+label.upper()+"_"+condition.upper()+
                "_MAX_CONFIRM_US="+str(summary["phase_maxima_us"]["confirm_us"]))
            print("KTERM_RC2N_"+label.upper()+"_"+condition.upper()+
                "_MIN_REMAINING_US="+str(summary["phase_maxima_us"]["minimum_remaining_us"]))
        return summary
    finally:
        for worker in workers:
            try:worker.terminate()
            except OSError:pass
        for worker in workers:
            try:worker.wait(timeout=3)
            except subprocess.TimeoutExpired:worker.kill()

def main():
    if len(sys.argv)!=5:raise RuntimeError("EXPECTED_ORIGINAL_CANDIDATE_PROBE_OUTPUT")
    orig=pathlib.Path(sys.argv[1]).resolve(strict=True)
    cand=pathlib.Path(sys.argv[2]).resolve(strict=True)
    probe=pathlib.Path(sys.argv[3]).resolve(strict=True)
    out=pathlib.Path(sys.argv[4]).resolve()
    if out.exists():raise RuntimeError("EVIDENCE_DIRECTORY_ALREADY_EXISTS")
    out.mkdir(mode=0o700,parents=True)
    sources=[("original",orig,BASE),("candidate",cand,CANDIDATE)]
    for label,path,sha in sources:
        a=shell(["git","-C",str(path),"rev-parse","HEAD"],path)
        b=shell(["git","-C",str(path),"status","--porcelain"],path)
        if a.returncode or b.returncode or a.stdout.strip()!=sha or b.stdout.strip():
            raise RuntimeError("KTERM_SOURCE_IDENTITY_OR_CLEANLINESS_DRIFT_"+label)
    payload=probe.read_bytes()
    if b"TestRC2NNineMakerAttemptsMeasuredUnderOriginalDeadline" not in payload or len(payload)<3000:
        raise RuntimeError("MISSING_TRANSIENT_PROBE")
    added=[]
    report={"schema":"kterminal.rc2n.nine-attempt-phase-telemetry.v1",
        "original_sha":BASE,"candidate_sha":CANDIDATE,
        "probe_sha256":hashlib.sha256(payload).hexdigest(),
        "original_retry_window_us":2000000,
        "original_maker_attempt_budget":9,
        "source_bodies_unmodified":True,"brokers_used":False,
        "full_regression_substituted":False,"results":[]}
    try:
        for _,source,_ in sources:
            dest=source/"pkg"/"rc2n_transient_instrumentation_test.go"
            if dest.exists():raise RuntimeError("PROBE_PATH_CONFLICT")
            dest.write_bytes(payload)
            added.append(dest)
        for label,src,_ in sources:
            for condition in ("normal","contended"):
                for mode,count in (("phase_probe",5),("original_test",5)):
                    summary=run_case(src,label,condition,mode,count,out)
                    report["results"].append(summary)
    finally:
        for path in added:
            path.unlink(missing_ok=True)
        for label,src,sha in sources:
            state=shell(["git","-C",str(src),"status","--porcelain"],src)
            if state.returncode or state.stdout.strip():
                raise RuntimeError("SOURCE_NOT_RESTORED_"+label)
    (out/"rc2n-redacted-phase-evidence.json").write_text(
        json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    failures=sum(result["state"]!="PASS" for result in report["results"])
    print("KTERM_RC2N_CASES="+str(len(report["results"])))
    print("KTERM_RC2N_NEGATIVE_CASES="+str(failures))
    print("KTERM_RC2N_SOURCE_CLEANUP=VERIFIED")
    print("KTERM_RC2N_ORIGINAL_ASSERTIONS=UNCHANGED")
    print("KTERM_RC2N_FULL_REGRESSION=NOT_RUN_NOT_WAIVED")
    print("KTERM_RC2N_RELEASE=BLOCKED")
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as error:
        print("KTERM_RC2N_DIAGNOSTIC=FAIL_CLOSED:"+type(error).__name__+":"+str(error).split(":")[0])
        sys.exit(2)
