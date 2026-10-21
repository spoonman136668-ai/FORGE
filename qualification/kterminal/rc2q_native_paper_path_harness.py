#!/usr/bin/env python3
"""RC2-Q initial PAPER submission/replay/presentation trace, exact-source Windows.

No live transport and no installed files. Never exports test logs or source.
Go test overlay is removed before tool returns; original source is checked clean.
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

PINS={"original":"eb5d225ae73b698a59c68d840daf1ec678e1a0ec",
      "candidate":"b8c2052d530cdff93462dfccc21b28f3824e5531"}
NAME="TestRC2QNativePaperOneOrderReceiptAndDashboardPublication"
CONTROLS=["TestOneClickPlayPaperUsesNoPrivateChecks",
          "TestDashboardOrderEvidenceDeduplicatesAndNeverResurrectsFills"]
FIELDS={
 "admission_to_ready_us","ready_to_result_us","result_to_return_us",
 "total_submission_us","receipt_sync_us","tranche_sync_us",
 "evidence_sync_us","duplicate_us","ui_model_us","ui_publish_atomic_us",
 "injected_display_fill_us","network_calls","paper_reservations",
 "requests","receipts"
}
METRIC=re.compile(r"([a-z_]+)=(-?[0-9]+)")

def cmd(argv,cwd,env=None,timeout=240):
    return subprocess.run(argv,cwd=cwd,env=env,capture_output=True,
                          text=True,check=False,timeout=timeout)
def sha_and_status(repo,expected,overlay=False):
    p=cmd(["git","-C",str(repo),"rev-parse","HEAD"],repo)
    q=cmd(["git","-C",str(repo),"status","--porcelain"],repo)
    if p.returncode or q.returncode or p.stdout.strip()!=expected:
        raise RuntimeError("SOURCE_IDENTITY_FAIL")
    actual=q.stdout.strip().replace("\\","/")
    if actual and (not overlay or actual!="?? pkg/rc2q_transient_paper_order_test.go"):
        raise RuntimeError("SOURCE_DIRTY_FAIL")
def env_for(root):
    root.mkdir(mode=0o700,parents=True,exist_ok=False)
    result=dict(os.environ)
    result.update(GOTOOLCHAIN="local",GOTELEMETRY="off",GOFLAGS="-p=1",
        CGO_ENABLED="0",GOMAXPROCS="2",K_TERMINAL_EXECUTION_MODE="PAPER",
        K_TERMINAL_P5_LATENCY="0",K_TERMINAL_NATIVE_TIMING="0",
        K_TERMINAL_TEST_WORKSPACE=str(root))
    for key,suffix in (("KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT","tail"),
                       ("KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT","post"),
                       ("KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT","v2")):
        p=root/suffix;p.mkdir(mode=0o700);result[key]=str(p)
    return result
def parse(stdout):
    metrics=[]
    counts=collections.Counter()
    rejects=set()
    malformed=0
    for line in stdout.splitlines():
        try:e=json.loads(line)
        except ValueError:malformed+=1;continue
        if e.get("Package")!="k-terminal/pkg":continue
        action=e.get("Action")
        name=e.get("Test")
        if name and action in ("run","pass","fail"):
            counts[(name,action)]+=1
        if action=="output" and name==NAME and "RC2Q_BOUNDARY " in e.get("Output",""):
            fields={k:int(v) for k,v in METRIC.findall(e["Output"].split("RC2Q_BOUNDARY ",1)[1])}
            if set(fields)==FIELDS:metrics.append(fields)
            else:rejects.add("BAD_METRIC_INVENTORY")
        if action=="fail" and name==NAME:rejects.add("PAPER_TEST_FAILURE")
        if action=="fail" and not name:rejects.add("PACKAGE_FAILED")
    return metrics,counts,malformed,rejects

def run_probe(label,repo,output):
    path=output/(label+"-data")
    env=env_for(path)
    names=[NAME]+CONTROLS
    expression="^(?:"+"|".join(names)+")$"
    started=time.monotonic()
    try:
        proc=cmd(["go","test","-json","-count=2","-p=1","-parallel=1",
                  "-timeout=6m","-run",expression,"./pkg"],
                repo,env,timeout=420)
        exit_code=proc.returncode
        metrics,counts,malformed,rejects=parse(proc.stdout)
    except subprocess.TimeoutExpired:
        exit_code=124;metrics=[];counts=collections.Counter()
        malformed=0;rejects={"GO_TIMEOUT"}
    complete=(exit_code==0 and not rejects and malformed==0 and len(metrics)==2 and
        all(counts[(test,"run")]==2 and counts[(test,"pass")]==2 and
            counts[(test,"fail")]==0 for test in names) and
        all(s["requests"]==1 and s["network_calls"]==0 and s["paper_reservations"]==0
            and s["receipts"]==1 for s in metrics))
    if not complete:rejects.add("INCOMPLETE_OR_FAILED_ACCOUNTING_PRESENTATION_ACCEPTANCE")
    return {"source":label,"result":"PASS" if complete else "FAIL_NOT_WAIVED",
        "go_exit":exit_code,"source_sha":PINS[label],
        "total_test_cases":len(names),"iterations":2,"collected_timings":len(metrics),
        "reason_classes":sorted(rejects),"parse_errors":malformed,
        "command_wall_s":round(time.monotonic()-started,3),
        "metrics":metrics,"no_real_paper_fill":True,
        "display_fill_event_injected_only":True,
        "wpf_screen_render_not_measured":True,
        "original_paper_submission_path_measured":True}
def main():
    if len(sys.argv)!=5:
        raise RuntimeError("ARGS:original candidate transient-go-file temp-output")
    original=pathlib.Path(sys.argv[1]).resolve(strict=True)
    candidate=pathlib.Path(sys.argv[2]).resolve(strict=True)
    probe=pathlib.Path(sys.argv[3]).resolve(strict=True)
    output=pathlib.Path(sys.argv[4]).resolve()
    if output.exists():raise RuntimeError("EXISTING_OUTPUT")
    output.mkdir(mode=0o700,parents=True)
    for label,source in (("original",original),("candidate",candidate)):
        sha_and_status(source,PINS[label])
    content=probe.read_bytes()
    if b"TestRC2QNativePaperOneOrderReceiptAndDashboardPublication" not in content or len(content)<4000:
        raise RuntimeError("TEST_PROBE_UNKNOWN")
    rows=[]
    overlays=[]
    try:
        for label,source in (("original",original),("candidate",candidate)):
            target=source/"pkg"/"rc2q_transient_paper_order_test.go"
            if target.exists():raise RuntimeError("TEMP_FILE_COLLISION")
            target.write_bytes(content)
            overlays.append(target)
            sha_and_status(source,PINS[label],overlay=True)
        for label,source in (("original",original),("candidate",candidate)):
            row=run_probe(label,source,output)
            rows.append(row)
            print("KTERM_RC2Q_"+label.upper()+"="+row["result"],flush=True)
    finally:
        for path in overlays:path.unlink(missing_ok=True)
        for label,source in (("original",original),("candidate",candidate)):
            sha_and_status(source,PINS[label])
    evidence={"schema":"kterminal.rc2q.native-paper-path-v1",
        "source_sha":PINS,
        "probe_sha256":hashlib.sha256(content).hexdigest(),
        "source_restored":True,"live_broker_traffic":False,
        "actual_paper_fill_accounting_proven":False,
        "wpf_render_proven":False,
        "full_regression_run":False,"results":rows}
    (output/"rc2q-redacted-metrics.json").write_text(
        json.dumps(evidence,sort_keys=True,indent=2),encoding="utf-8")
    print("KTERM_RC2Q_SOURCE_RESTORED=PASS")
    print("KTERM_RC2Q_FINANCIAL_PAPER_FILL=NOT_PROVEN")
    print("KTERM_RC2Q_WPF_RENDER=NOT_MEASURED")
    print("KTERM_RC2Q_FULL_REGRESSION=NOT_RUN_NOT_WAIVED")
    print("KTERM_RC2Q_RELEASE=BLOCKED")
    return 0 if all(x["result"]=="PASS" for x in rows) else 2
if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("KTERM_RC2Q_SETUP=FAIL_CLOSED:"+type(e).__name__,flush=True)
        sys.exit(2)
