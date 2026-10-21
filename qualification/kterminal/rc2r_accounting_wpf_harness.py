#!/usr/bin/env python3
"""RC2-R frozen original-vs-candidate post-order accounting and UI evidence.

Tests real Go confirmed-event reducers, observed idempotence and snapshot
publication, plus the existing Windows WPF-control acceptance on original
PowerShell source. Never launch executable, change source under Git, use a
broker, treat a fabricated fill as an actual paper fill, or claim pixel paint.
"""
import collections,json,os,pathlib,re,subprocess,sys,time,hashlib

PINS={"original":"eb5d225ae73b698a59c68d840daf1ec678e1a0ec",
      "candidate":"b8c2052d530cdff93462dfccc21b28f3824e5531"}
NAME="TestRC2RConfirmedOrderAccountingAndDashboardPublication"
CONTROLS=("TestConfirmedOrderPartialUpdatesAndDelayedFeesDoNotDoubleCount",
          "TestDashboardDiagnosticsFailureRepeatRecoveryPreservesFinancialValues")
KEYS=("account_event_us","position_snapshot_us","duplicate_event_us",
      "order_observe_us","model_build_us","atomic_publish_us",
      "published_file_read_us","total_direct_us","order_rows")
METRIC=re.compile(r"([a-z_]+)=([0-9]+)")

def call(args,where,env=None,timeout=210):
    return subprocess.run(args,cwd=where,env=env,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        timeout=timeout,check=False)

def custody(repo,sha,overlay=False):
    r=call(["git","-C",str(repo),"rev-parse","HEAD"],repo)
    c=call(["git","-C",str(repo),"status","--porcelain"],repo)
    v=c.stdout.strip().replace("\\","/")
    if r.returncode or c.returncode or r.stdout.strip()!=sha or (
        v and (not overlay or v!="?? pkg/rc2r_transient_accounting_test.go")):
        raise RuntimeError("FROZEN_SOURCE_CUSTODY_FAIL")

def env(root):
    root.mkdir(mode=0o700,parents=False,exist_ok=False)
    e=dict(os.environ)
    e.update(GOTOOLCHAIN="local",GOTELEMETRY="off",GOFLAGS="-p=1",
        GOMAXPROCS="2",CGO_ENABLED="0",K_TERMINAL_EXECUTION_MODE="PAPER",
        K_TERMINAL_NATIVE_TIMING="0",K_TERMINAL_P5_LATENCY="0",
        K_TERMINAL_TEST_WORKSPACE=str(root))
    for key,sub in (
       ("KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT","tail"),
       ("KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT","post"),
       ("KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT","v2")):
        p=root/sub;p.mkdir(mode=0o700);e[key]=str(p)
    return e

def go_case(label,repo,root):
    e=env(root/(label+"-go"))
    expr="^(?:"+"|".join([NAME,*CONTROLS])+")$"
    try:
        r=call(["go","test","-json","-count=3","-p=1","-parallel=1",
            "-timeout=6m","-run",expr,"./pkg"],repo,e,timeout=430)
    except subprocess.TimeoutExpired:
        return {"result":"FAIL_NOT_WAIVED","cause":"TIMEOUT","samples":[]}
    counter=collections.Counter();metrics=[];parse_errors=0
    for line in r.stdout.splitlines():
        try:z=json.loads(line)
        except ValueError:parse_errors+=1;continue
        if z.get("Package")!="k-terminal/pkg":continue
        test=z.get("Test");action=z.get("Action")
        if test and action in ("pass","fail","run","skip"):
            counter[(test,action)]+=1
        if action=="output" and test==NAME and "RC2R_PHASE " in z.get("Output",""):
            fields={k:int(v) for k,v in METRIC.findall(z["Output"].split("RC2R_PHASE ",1)[1])}
            if set(fields)==set(KEYS):metrics.append(fields)
    success=(r.returncode==0 and parse_errors==0 and len(metrics)==3 and
        all(counter[(k,"pass")]==3 and counter[(k,"fail")]==0 and
            counter[(k,"run")]==3 and counter[(k,"skip")]==0
            for k in (NAME,*CONTROLS)))
    return {"result":"PASS" if success else "FAIL_NOT_WAIVED",
        "go_exit":r.returncode,"samples":metrics,
        "parse_errors":parse_errors,
        "exact_expected_cases":9,
        "observed_cases":sum(counter[(k,"pass")] for k in (NAME,*CONTROLS))}

def static_desktop(label,repo):
    go=(repo/"pkg/terminal-dashboard.go").read_text(encoding="utf-8")
    ps=(repo/"dashboard-ui.ps1").read_text(encoding="utf-8-sig")
    valid=(
        bool(re.search(r"defaultDashboardRefreshSeconds\s*=\s*5\b",go)) and
        bool(re.search(r"\$timer\.Interval\s*=\s*\[TimeSpan\]::FromMilliseconds\(50\)",ps)) and
        "Update-Dashboard $readResult.Value" in ps and
        "Read-KTerminalJsonSnapshot -Path $snapshotPath" in ps and
        "Refresh-EventStream" in ps and
        "AddMilliseconds(200)" in ps)
    return {"source":label,"result":"PASS" if valid else "FAIL_NOT_WAIVED",
        "backend_default_snapshot_ticker_ms":5000 if valid else None,
        "wpf_dispatcher_poll_ms":50 if valid else None,
        "event_tail_read_cadence_ms":200 if valid else None,
        "pixel_paint_captured":False}

def wpf_control_test(label,repo):
    script=repo/"verification/test-dashboard-presentation.ps1"
    started=time.monotonic()
    try:
        p=call(["powershell.exe","-NoLogo","-NoProfile","-NonInteractive",
             "-Sta","-ExecutionPolicy","Bypass","-File",str(script),
             "-Root",str(repo)],repo,timeout=190)
        passed=p.returncode==0 and "PASS: strict-mode" in p.stdout
        return {"source":label,"result":"PASS" if passed else "FAIL_NOT_WAIVED",
            "total_verification_wall_ms":round((time.monotonic()-started)*1000,2),
            "wpf_controls_instantiated":passed,
            "rendered_frame_measured":False}
    except subprocess.TimeoutExpired:
        return {"source":label,"result":"FAIL_NOT_WAIVED",
            "cause":"WINDOWS_WPF_CONTROL_TEST_TIMEOUT"}

def main():
    if len(sys.argv)!=5:raise RuntimeError("ORIG_CAND_TEST_OUTPUT_REQUIRED")
    orig=pathlib.Path(sys.argv[1]).resolve(strict=True)
    cand=pathlib.Path(sys.argv[2]).resolve(strict=True)
    probe=pathlib.Path(sys.argv[3]).resolve(strict=True)
    out=pathlib.Path(sys.argv[4]).resolve()
    if out.exists():raise RuntimeError("EVIDENCE_ROOT_ALREADY_EXISTS")
    out.mkdir(mode=0o700,parents=True)
    body=probe.read_bytes()
    if b"TestRC2RConfirmedOrderAccountingAndDashboardPublication" not in body:
        raise RuntimeError("UNEXPECTED_SOURCE_PROBE")
    repos=[("original",orig),("candidate",cand)]
    for label,repo in repos:custody(repo,PINS[label])
    data={"schema":"kterminal.rc2r.accounting-dashboard-window-control.v1",
        "source_sha":PINS,"temporary_test_sha256":hashlib.sha256(body).hexdigest(),
        "real_broker_used":False,"real_paper_fill_claimed":False,
        "original_order_source_modified":False,"wpf_pixel_paint_measured":False,
        "end_to_end_7s_cause_proven":False,"full_regression_run":False,
        "results":[]}
    temporary=[]
    try:
        for label,repo in repos:
            dest=repo/"pkg/rc2r_transient_accounting_test.go"
            if dest.exists():raise RuntimeError("TEMPORARY_TEST_ALREADY_PRESENT")
            dest.write_bytes(body)
            temporary.append(dest)
            custody(repo,PINS[label],overlay=True)
        for label,repo in repos:
            go=go_case(label,repo,out)
            view=static_desktop(label,repo)
            wpf=wpf_control_test(label,repo)
            data["results"].append({"source":label,"go":go,"desktop_source":view,"wpf_control_fixture":wpf})
            print("KTERM_RC2R_"+label.upper()+"_ACCOUNTING="+go["result"],flush=True)
            print("KTERM_RC2R_"+label.upper()+"_WPF_CONTROLS="+wpf["result"],flush=True)
            print("KTERM_RC2R_"+label.upper()+"_UI_SOURCE="+view["result"],flush=True)
    finally:
        for file in temporary:file.unlink(missing_ok=True)
        for label,repo in repos:custody(repo,PINS[label])
    data["all_focused_checks_pass"]=all(
        all(row[key]["result"]=="PASS" for key in ("go","desktop_source","wpf_control_fixture"))
        for row in data["results"])
    (out/"rc2r-redacted-evidence.json").write_text(
        json.dumps(data,indent=2,sort_keys=True),encoding="utf-8")
    print("KTERM_RC2R_FOCUSED="+("PASS" if data["all_focused_checks_pass"] else "FAIL_NOT_WAIVED"),flush=True)
    print("KTERM_RC2R_REAL_PROCESS_WPF_PAINT=NOT_MEASURED",flush=True)
    print("KTERM_RC2R_ACTUAL_PAPER_FILL=NOT_TESTED",flush=True)
    print("KTERM_RC2R_UNMODIFIED_CHECKOUTS=PASS",flush=True)
    print("KTERM_RC2R_FULL_WINDOWS_REGRESSION=NOT_RUN",flush=True)
    print("KTERM_RC2R_RELEASE=BLOCKED",flush=True)
    return 0 if data["all_focused_checks_pass"] else 2
if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("KTERM_RC2R_SETUP=FAIL_CLOSED:"+type(e).__name__,flush=True)
        sys.exit(2)
