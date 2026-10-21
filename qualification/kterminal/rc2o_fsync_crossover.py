#!/usr/bin/env python3
"""RC2-O paired, same-run, safe Windows fsync pressure comparison.

Run *unchanged* original and PR73 retry tests and a temporary test-only
nine-maker phase probe before and during bounded same-volume fsync pressure.
This intentionally does not modify trading logic, accounting, 2s deadlines,
test assertions, K-Terminal original history, or the user workstation.

Fail closed if the fsync worker is unavailable, ends before the stressed
measurements, or either checkout/source identity differs.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

ORIGINAL="eb5d225ae73b698a59c68d840daf1ec678e1a0ec"
CANDIDATE="b8c2052d530cdff93462dfccc21b28f3824e5531"

def git_sha(path):
    cp=subprocess.run(["git","-C",str(path),"rev-parse","HEAD"],
        capture_output=True,text=True,timeout=30)
    if cp.returncode:raise RuntimeError("SOURCE_GIT_IDENTITY_UNAVAILABLE")
    return cp.stdout.strip()

def integrity(paths):
    for path,expected in paths:
        if git_sha(path)!=expected:raise RuntimeError("SOURCE_SHA_DRIFT")
        cp=subprocess.run(["git","-C",str(path),"status","--porcelain"],
            capture_output=True,text=True,timeout=30)
        if cp.returncode or cp.stdout.strip():
            raise RuntimeError("SOURCE_UNCLEAN")

def run_harness(script,original,candidate,probe,out):
    env=dict(os.environ)
    env["KTERM_RC2N_NATIVE_SPANS"]="1"
    env["KTERM_RC2O_ONLY_NORMAL"]="1"
    env["KTERM_RC2O_WITH_CONTROLS"]="1"
    args=[sys.executable,"-B",str(script),str(original),str(candidate),str(probe),str(out)]
    started=time.monotonic()
    try:
        cp=subprocess.run(args,cwd=script.parent.parent.parent,env=env,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=330)
        exit_code=cp.returncode
    except subprocess.TimeoutExpired:
        exit_code=124
    resultpath=out/"rc2n-redacted-phase-evidence.json"
    if resultpath.exists():
        result=json.loads(resultpath.read_text(encoding="utf-8"))
    else:result={"results":[]}
    if exit_code or len(result.get("results",[]))!=4:
        raise RuntimeError("INSTRUMENTED_HARNESS_FAILED_OR_INCOMPLETE")
    cases=result["results"]
    if any(v["state"]!="PASS" for v in cases):
        # Keep individual failures in artifact; this diagnostic is NOT full
        # qualification and does not waive negative observations.
        status="NEGATIVE_RETAINED"
    else:status="PASS"
    return {"harness_exit":exit_code,"run_seconds":round(time.monotonic()-started,3),
        "status":status,"evidence":result}

def summarize(report):
    out={}
    for x in report["evidence"]["results"]:
        key=x["source"]+"_"+x["mode"]
        spans=x.get("native_span_aggregates",{})
        samples=x["samples"]
        profiles=[{
            "last_deadline_remaining_us":
               p.get("phases",[{}])[-1].get("deadline_remaining_us"),
            "first_attempt_elapsed_us":
               p.get("phases",[{}])[0].get("elapsed_from_start_us"),
            "last_attempt_elapsed_us":
               p.get("phases",[{}])[-1].get("elapsed_from_start_us"),
            "all_nine_posts":
               p.get("phases",[{}])[-1].get("after_posts") if p.get("phases") else None,
            "status":p.get("status"),"reasons":p.get("reason_classes")
        } for p in samples]
        out[key]={"state":x["state"],"success":x["successful_repeats"],
            "failed":x["failed_repeats"],
            "phase_maxima_us":x.get("phase_maxima_us",{}),
            "spans":spans,"samples":profiles}
    return out

def main():
    if len(sys.argv)!=6:raise RuntimeError("EXPECTED_ORIG_CAND_PROBE_PRESSURE_OUT")
    original=pathlib.Path(sys.argv[1]).resolve(strict=True)
    candidate=pathlib.Path(sys.argv[2]).resolve(strict=True)
    probe=pathlib.Path(sys.argv[3]).resolve(strict=True)
    pressure_script=pathlib.Path(sys.argv[4]).resolve(strict=True)
    out=pathlib.Path(sys.argv[5]).resolve()
    root=pathlib.Path(__file__).resolve().parent
    harness=root/"rc2n_phase_harness.py"
    for x in (harness,probe,pressure_script):
        if not x.is_file():raise RuntimeError("QUALIFIED_DIAGNOSTIC_FILE_MISSING")
    if out.exists():raise RuntimeError("EVIDENCE_OUTPUT_ALREADY_PRESENT")
    out.mkdir(mode=0o700,parents=True)
    pins=[(original,ORIGINAL),(candidate,CANDIDATE)]
    integrity(pins)
    # Windows same-device only. Absolute addresses never appear in reports.
    odrive=original.drive.lower()
    cdrive=candidate.drive.lower()
    tdrive=out.drive.lower()
    if not odrive or (odrive,cdrive)!=(tdrive,tdrive):
        raise RuntimeError("REPOS_AND_PRESSURE_WORKSPACE_NOT_SAME_VOLUME")
    print("KTERM_RC2O_FROZEN_SOURCE_AND_VOLUME=PASS",flush=True)
    control=run_harness(harness,original,candidate,probe,out/"control")
    integrity(pins)
    print("KTERM_RC2O_NORMAL="+control["status"],flush=True)
    folder=out/"pressure"
    folder.mkdir(mode=0o700,exist_ok=False)
    pressure=subprocess.Popen([sys.executable,"-B",str(pressure_script),str(folder)],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,cwd=out)
    worker_started=time.monotonic()
    stressed=None
    pressure_exit=None
    try:
        until=time.monotonic()+15
        while not (folder/"ready.flag").exists() and time.monotonic()<until:
            if pressure.poll() is not None:raise RuntimeError("FSYNC_WORKER_DID_NOT_START")
            time.sleep(.05)
        if not (folder/"ready.flag").exists():raise RuntimeError("FSYNC_WORKER_READY_TIMEOUT")
        time.sleep(.2)
        if pressure.poll() is not None:raise RuntimeError("FSYNC_WORKER_ENDED_EARLY")
        stressed=run_harness(harness,original,candidate,probe,out/"stressed")
        ended_while_running=pressure.poll() is not None
    finally:
        (folder/"stop.flag").write_text("stop",encoding="ascii")
        try:pressure_exit=pressure.wait(timeout=12)
        except subprocess.TimeoutExpired:
            pressure.kill()
            pressure.wait(timeout=4)
            pressure_exit=124
    integrity(pins)
    pressure_summary_file=folder/"fsync-summary.json"
    if not pressure_summary_file.exists():raise RuntimeError("PRESSURE_SUMMARY_MISSING")
    pressure_summary=json.loads(pressure_summary_file.read_text(encoding="utf-8"))
    evidence={
        "schema":"kterminal.rc2o.windows-fsync-crossover.v1",
        "base_source_sha":ORIGINAL,"candidate_source_sha":CANDIDATE,
        "no_source_changes":True,"same_volume":True,
        "hard_two_second_window_preserved":True,
        "nine_attempts_preserved":True,
        "financial_assertions_preserved":True,
        "control":summarize(control),"fsync_stressed":summarize(stressed),
        "pressure":{"exit":pressure_exit,"ended_before_measurements_completed":ended_while_running,
            "worker_wall_s":round(time.monotonic()-worker_started,3),
            **pressure_summary},
        "all_results_clean":control["status"]=="PASS" and stressed["status"]=="PASS",
        "full_regression_run":False,"release_approved":False
    }
    (out/"rc2o-redacted-comparison.json").write_text(
        json.dumps(evidence,indent=2,sort_keys=True),encoding="utf-8")
    print("KTERM_RC2O_FILESYSTEM="+stressed["status"],flush=True)
    print("KTERM_RC2O_FSYNCS="+str(pressure_summary.get("count")),flush=True)
    print("KTERM_RC2O_FSYNC_P95_MS="+str(pressure_summary.get("p95_fsync_ms")),flush=True)
    print("KTERM_RC2O_FSYNC_MAX_MS="+str(pressure_summary.get("max_fsync_ms")),flush=True)
    for name in ("original","candidate"):
        key=name+"_phase_probe"
        c=evidence["control"][key]
        p=evidence["fsync_stressed"][key]
        print("KTERM_RC2O_"+name.upper()+"_NORMAL_MAX_CONFIRM_US="+str(c["phase_maxima_us"].get("confirm_us")),flush=True)
        print("KTERM_RC2O_"+name.upper()+"_PRESSURE_MAX_CONFIRM_US="+str(p["phase_maxima_us"].get("confirm_us")),flush=True)
        print("KTERM_RC2O_"+name.upper()+"_NORMAL_MIN_REMAINING_US="+str(c["phase_maxima_us"].get("minimum_remaining_us")),flush=True)
        print("KTERM_RC2O_"+name.upper()+"_PRESSURE_MIN_REMAINING_US="+str(p["phase_maxima_us"].get("minimum_remaining_us")),flush=True)
    valid=(not ended_while_running and pressure_exit==0 and pressure_summary.get("count",0)>=15
        and pressure_summary.get("write_errors",1)==0)
    print("KTERM_RC2O_PRESSURE_CUSTODY="+("PASS" if valid else "FAIL_CLOSED"))
    print("KTERM_RC2O_FULL_REGRESSION=NOT_RUN_NOT_WAIVED")
    print("KTERM_RC2O_PRODUCTION_RELEASE=BLOCKED")
    if not valid:raise RuntimeError("FILESYSTEM_PRESSURE_VALIDITY_FAILED")
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as exc:
        print("KTERM_RC2O=FAIL_CLOSED:"+type(exc).__name__,flush=True)
        sys.exit(2)
