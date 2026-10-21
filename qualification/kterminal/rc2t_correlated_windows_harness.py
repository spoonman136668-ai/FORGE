#!/usr/bin/env python3
"""RC2-T Go reducer -> production dashboard publisher -> WPF snapshot AST.

Windows-only local synthetic fixture. Does NOT run original shipping executable,
connect a broker, prove an actual paper fill, or measure a physical desktop
compositor. The source-native 5s ticker cadence is reproduced as an isolated
model; the entire TerminalDashboard.Start loop is not started. Both positive
and negative observations are retained. Sensitive source, financial fixture
values, private file paths, Go and PowerShell logs never leave runner.
"""
import collections
import json
import os
import pathlib
import re
import subprocess
import sys
import time

PINS={"original":"eb5d225ae73b698a59c68d840daf1ec678e1a0ec",
      "candidate":"b8c2052d530cdff93462dfccc21b28f3824e5531"}
GO_TEST="TestRC2TCorrelatedSyntheticConfirmedEventAndDashboardPublication"
GO_CTRL=("TestConfirmedOrderPartialUpdatesAndDelayedFeesDoNotDoubleCount",
         "TestDashboardOrderEvidenceDeduplicatesAndNeverResurrectsFills")
SAFE_ISSUES=("RC2T_ACCOUNTING_INTEGRITY_FAILURE",
             "RC2T_BACKEND_TICKER_MODEL_TIMEOUT",
             "RC2T_REAL_PUBLISHER_DID_NOT_WRITE",
             "RC2T_DASHBOARD_WIRE_MODEL_INVALID",
             "RC2T_CORRELATED_WPF_OBSERVATIONS_INCOMPLETE",
             "RC2T_FINANCIAL_DISPLAY_INCOHERENT",
             "RC2T_ORIGINAL_SNAPSHOT_CONSUMER_NOT_FOUND",
             "RC2T_PRODUCTION_DASHBOARD_FUNCTION_MISSING",
             "RC2T_NATIVE_REDUCER_AND_PRODUCTION_UI_PUBLISHER=PASS",
             "RC2T_WPF_CONSUMER=PASS")

def run(args,cwd,env=None,timeout=190):
    return subprocess.run(args,cwd=cwd,env=env,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,check=False,text=True,
                          timeout=timeout)

def source_clean(root,sha,overlay=False):
    ident=run(["git","-C",str(root),"rev-parse","HEAD"],root)
    status=run(["git","-C",str(root),"status","--porcelain"],root)
    allowed="?? pkg/rc2t_correlated_transient_test.go"
    actual=status.stdout.strip().replace("\\","/")
    if ident.returncode or status.returncode or ident.stdout.strip()!=sha or (
       actual and (not overlay or actual!=allowed)):
        raise RuntimeError("EXACT_IDENTITY_OR_WORKTREE_FAIL_CLOSED")

def source_env(synthetic_root):
    e=dict(os.environ)
    e.update(GOTOOLCHAIN="local",GOFLAGS="-p=1",CGO_ENABLED="0",
       GOMAXPROCS="2",GOTELEMETRY="off",K_TERMINAL_EXECUTION_MODE="PAPER",
       K_TERMINAL_GUI_MODE="0",K_TERMINAL_NATIVE_TIMING="0",
       K_TERMINAL_P5_LATENCY="0",KTERM_RC2T_ROOT=str(synthetic_root))
    for n,leaf in (
       ("KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT","tail"),
       ("KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT","post"),
       ("KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT","v2")):
       sub=synthetic_root/leaf
       sub.mkdir(mode=0o700)
       e[n]=str(sub)
    return e

def parse_go(stdout):
    counts=collections.Counter()
    reports=[]
    fail=[]
    for line in stdout.splitlines():
        try:z=json.loads(line)
        except ValueError:continue
        if z.get("Package")!="k-terminal/pkg":continue
        name=z.get("Test")
        action=z.get("Action")
        if name in (GO_TEST,*GO_CTRL) and action in ("run","pass","fail","skip"):
            counts[(name,action)]+=1
        if name==GO_TEST and action=="output":
            msg=z.get("Output","")
            for p in SAFE_ISSUES:
                if p in msg and p not in reports:reports.append(p)
            if "RC2T_PHASE " in msg:
                sample=dict((k,int(v)) for k,v in re.findall(
                    r"([a-z_]+)=([0-9]+)",msg.split("RC2T_PHASE ",1)[1]))
                if set(sample)!={"index","accounting_us","wait_before_publish_us","publish_us"}:
                    fail.append("MALFORMED_NATIVE_PHASE_OUTPUT")
    valid=all(counts[(n,"run")]==1 and counts[(n,"pass")]==1 and
              counts[(n,"fail")]==0 for n in (GO_TEST,*GO_CTRL))
    return valid,reports,fail

def bounded_issues(output):
    return sorted(x for x in SAFE_ISSUES if x in output)

def phased(label,repo,test_ps,output_root):
    sandbox=output_root/(label+"-sandbox")
    sandbox.mkdir(mode=0o700,parents=False,exist_ok=False)
    (sandbox/"data").mkdir(mode=0o700)
    env=source_env(sandbox)
    wpf_result=sandbox/"wpf-consumer.json"
    wpf_cmd=["powershell.exe","-NoProfile","-NoLogo","-NonInteractive",
          "-Sta","-ExecutionPolicy","Bypass","-File",str(test_ps),
          "-Root",str(repo),"-OutputPath",str(wpf_result),"-SandboxRoot",str(sandbox)]
    # Independent PowerShell WPF process starts first; the producer is not
    # executed until a real STA Dispatcher loop has signaled readiness.
    wpf=subprocess.Popen(wpf_cmd,cwd=repo,env=env,stdout=subprocess.PIPE,
         stderr=subprocess.PIPE,text=True)
    try:
        ready=sandbox/"receiver-ready.flag"
        deadline=time.monotonic()+22
        while time.monotonic()<deadline and not ready.exists():
            if wpf.poll() is not None:break
            time.sleep(.10)
        if not ready.exists():raise RuntimeError("WPF_CONSUMER_UNAVAILABLE")
        pattern="^(?:"+"|".join((GO_TEST,*GO_CTRL))+")$"
        started=time.monotonic()
        try:
            go=run(["go","test","-json","-count=1","-parallel=1","-p=1",
                 "-timeout=5m","-run",pattern,"./pkg"],
                 repo,env,timeout=245)
        except subprocess.TimeoutExpired:
            raise RuntimeError("GO_PROCESS_TIMEOUT")
        go_elapsed=round(time.monotonic()-started,3)
        try:
            stdout,stderr=wpf.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            raise RuntimeError("WPF_CONSUMER_TIMEOUT")
        actual_go=go.returncode
        actual_wpf=wpf.returncode
        go_ok,go_issues,parse_issues=parse_go(go.stdout)
        completed=(actual_go==0 and go_ok and
                   "RC2T_NATIVE_REDUCER_AND_PRODUCTION_UI_PUBLISHER=PASS" in go_issues)
        tracefile=sandbox/"producer-trace.json"
        native=json.loads(tracefile.read_text(encoding="utf-8")) if tracefile.exists() else []
        ui=json.loads(wpf_result.read_text(encoding="utf-8")) if wpf_result.exists() else {}
        output=stdout+"\n"+stderr
        consumer_ok=(actual_wpf==0 and ui.get("result")=="PASS" and
                     "RC2T_WPF_CONSUMER=PASS" in output and
                     len(ui.get("samples",[]))==2)
        pairs=[]
        if len(native)==2 and len(ui.get("samples",[]))==2:
            for go_entry in native:
                matches=[obs for obs in ui["samples"]
                         if obs.get("model_updated_at")==go_entry.get("model_updated_at")]
                if len(matches)!=1:continue
                obs=matches[0]
                completion_ms=go_entry["accounting_completed_ns"]/1000000
                publish_ms=go_entry["published_ns"]/1000000
                update_ms=obs["wpf_update_begin_unix_ms"]
                render_ms=obs["wpf_render_end_unix_ms"]
                phase={
                 "phase":go_entry["phase"],
                 "producer_accounting_ms":round(
                    (go_entry["accounting_completed_ns"]-
                     go_entry["accounting_started_ns"])/1e6,3),
                 "event_completion_to_publish_ms":round(publish_ms-completion_ms,3),
                 "publisher_elapsed_ms":round(
                    (go_entry["published_ns"]-
                     go_entry["snapshot_prepared_ns"])/1e6,3),
                 "publish_to_consumer_callback_ms":round(update_ms-publish_ms,3),
                 "consumer_callback_to_render_ms":round(render_ms-update_ms,3),
                 "event_to_offscreen_render_ms":round(render_ms-completion_ms,3),
                 "source_native_five_second_ticker_modeled":go_entry["source_ticker_simulated"],
                 "offscreen_render_not_physical_screen":True,
                }
                phase["monotonic_causal_order"]=(
                  phase["event_completion_to_publish_ms"]>=0 and
                  phase["publish_to_consumer_callback_ms"]>=-2 and
                  phase["consumer_callback_to_render_ms"]>=0)
                pairs.append(phase)
        valid=(completed and consumer_ok and len(pairs)==2 and
               all(x["monotonic_causal_order"] for x in pairs))
        return {"source":label,"result":"PASS" if valid else "FAIL_NOT_WAIVED",
            "go_exit":actual_go,"wpf_exit":actual_wpf,
            "go_elapsed_s":go_elapsed,
            "original_controls_pass":go_ok,
            "failure_classes":sorted(set(
                  parse_issues+bounded_issues(output)+bounded_issues(go.stdout))),
            "correlated_phases":pairs,
            "correlated_samples":len(pairs),
            "shipping_display_frame_measured":False,
            "actual_paper_engine_fill_measured":False,
            "full_dashboard_Start_loop_measured":False}
    finally:
        if wpf.poll() is None:
            wpf.terminate()
            try:wpf.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                wpf.kill()
                wpf.communicate(timeout=5)

def main():
    if len(sys.argv)!=6:raise RuntimeError("NEED_SOURCE_SOURCE_GO_PS_TEMP")
    original=pathlib.Path(sys.argv[1]).resolve(strict=True)
    candidate=pathlib.Path(sys.argv[2]).resolve(strict=True)
    go=pathlib.Path(sys.argv[3]).resolve(strict=True)
    ps=pathlib.Path(sys.argv[4]).resolve(strict=True)
    out=pathlib.Path(sys.argv[5]).resolve()
    if out.exists():raise RuntimeError("PREEXISTING_EVIDENCE_DIRECTORY")
    out.mkdir(mode=0o700,parents=True)
    if go.name!="rc2t_correlated_event_publisher_test.go" or        ps.name!="rc2t_correlated_wpf_consumer.ps1":
        raise RuntimeError("WRONG_TRANSIENT_TEST_ID")
    rows=[]
    sources=[("original",original),("candidate",candidate)]
    for name,root in sources:source_clean(root,PINS[name])
    staged=[]
    try:
        for name,root in sources:
            path=root/"pkg"/"rc2t_correlated_transient_test.go"
            if path.exists():raise RuntimeError("TRANSIENT_PROBE_COLLISION")
            path.write_bytes(go.read_bytes())
            staged.append(path)
            source_clean(root,PINS[name],overlay=True)
        for name,root in sources:
            result=phased(name,root,ps,out)
            rows.append(result)
            print("KTERM_RC2T_"+name.upper()+"="+result["result"],flush=True)
            for phase in result["correlated_phases"]:
                print("KTERM_RC2T_"+name.upper()+"_"+
                  phase["phase"].upper()+"_EVENT_TO_OFFSCREEN_MS="+
                  str(phase["event_to_offscreen_render_ms"]),flush=True)
    finally:
        for path in staged:path.unlink(missing_ok=True)
        for name,root in sources:source_clean(root,PINS[name])
    report={"schema":"kterminal.rc2t.correlated-native-publish-wpf-consumer.v1",
      "source_sha":PINS,"source_unmodified":True,"live_broker_used":False,
      "real_paper_order_fill_proven":False,
      "full_shipping_executable_visible_screen_latency_proven":False,
      "independent_5s_cadence_model_not_production_scheduler":True,
      "original_cadence_ms":5000,
      "full_regression":False,"pr_merges":False,
      "release_gate":"BLOCKED","results":rows}
    (out/"rc2t-correlated-redacted.json").write_text(
        json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    print("KTERM_RC2T_SOURCE_RESTORED=PASS",flush=True)
    print("KTERM_RC2T_SHIPPING_PIXEL_LATENCY=NOT_PROVEN",flush=True)
    print("KTERM_RC2T_FULL_WINDOWS_REGRESSION=NOT_RUN_NOT_WAIVED",flush=True)
    print("KTERM_RC2T_RELEASE=BLOCKED",flush=True)
    return 0 if len(rows)==2 and all(x["result"]=="PASS" for x in rows) else 2

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as exc:
        print("KTERM_RC2T_SETUP=FAIL_CLOSED:"+type(exc).__name__,flush=True)
        sys.exit(2)
