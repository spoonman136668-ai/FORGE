#!/usr/bin/env python3
"""RC2-S source-pinned Windows WPF publish-to-consumer callback timing.

This is not a real shipping app frame time: it measures the genuine WPF
snapshot poll AST, JSON snapshot reader, and production Update-Dashboard
function against test-only WPF controls and an offscreen render. The full
5-second server ticker and physical desktop compositor remain unmeasured.

All financial and brokerage state stays isolated from production. No raw
PowerShell logs, source text, order data, screenshots, or file paths are
uploaded as public CI artifacts.
"""
import json,pathlib,re,subprocess,sys,time,statistics
PIN={"original":"eb5d225ae73b698a59c68d840daf1ec678e1a0ec",
     "candidate":"b8c2052d530cdff93462dfccc21b28f3824e5531"}
FAIL_CODES={
 "UNBOUND_FUNCTION_OR_PROPERTY":r"PropertyNotFoundStrict|CommandNotFoundException|The term .* is not recognized",
 "WPF_LAYOUT_OVERLAP":r"Horizontal overlap|Vertical overlap/clipping|Compact row overlaps|Metrics extend",
 "WPF_RESIZE_INVARIANT":r"Dashboard cannot compact|Reset failed to restore|XRP reserve precision changed|BTC reserve precision changed",
 "WPF_XAML_ERROR":r"XamlParseException|Cannot create unknown type|Cannot set unknown member",
 "WPF_SNAPSHOT_MISSING":r"RC2S_SNAPSHOT_NOT_CONSUMED",
 "WPF_SYNCHRONIZATION":r"RC2S_MISSED_OR_DUPLICATE|RC2S_PRESENTATION_LATENCY_EXCEEDED",
 "WPF_FINANCIAL_INCOHERENT":r"RC2S_FINANCIAL_DISPLAY_INCOHERENT",
 "PS_PARSER_ERROR":r"ParserError|ParseException|Unexpected token",
}
def proc(argv,cwd,seconds=120):
    return subprocess.run(argv,cwd=cwd,stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,text=True,check=False,timeout=seconds)
def custody(repo,expected):
    sha=proc(["git","-C",str(repo),"rev-parse","HEAD"],repo)
    dirty=proc(["git","-C",str(repo),"status","--porcelain"],repo)
    if sha.returncode or dirty.returncode or sha.stdout.strip()!=expected or dirty.stdout.strip():
        raise RuntimeError("SOURCE_SHA_OR_CLEANLINESS_MISMATCH")
def testcase(repo,source_label,ps,out):
    path=out/(source_label+"-wpf.json")
    invocation=["powershell.exe","-NoLogo","-NoProfile","-NonInteractive",
       "-Sta","-ExecutionPolicy","Bypass","-File",str(ps),
       "-Root",str(repo),"-OutputPath",str(path)]
    before=time.monotonic()
    try:
        p=proc(invocation,repo,145)
        rc=p.returncode
        output=p.stdout+"\n"+p.stderr
    except subprocess.TimeoutExpired:
        rc=124
        output=""
    markers=("KTERM_RC2S_SNAPSHOT_POLL=PASS" in output and
        "KTERM_RC2S_SHIPPING_PIXEL_PAINT=NOT_MEASURED" in output)
    data=json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    valid=bool(rc==0 and markers and data and data.get("result")=="PASS"
         and len(data.get("samples",[]))==6 and
         data.get("production_Update_Dashboard_callback") is True and
         data.get("shipping_window_pixel_paint_measured") is False)
    classifications=sorted(k for k,x in FAIL_CODES.items()
        if re.search(x,output,re.IGNORECASE))
    if not valid and not classifications:classifications=["UNCLASSIFIED_FAILURE"]
    result={
      "source":source_label,"result":"PASS" if valid else "FAIL_NOT_WAIVED",
      "exit_code":rc,"wall_s":round(time.monotonic()-before,3),
      "reason_classes":classifications,
      "sample_count":len(data["samples"]) if data else 0,
      "observations":data["samples"] if valid else [],
      "shipping_pixel_paint_tested":False}
    if valid:
        fields=("source_publish_to_update_ms","production_update_ms",
                "offscreen_layout_render_ms")
        result["stats_ms"]={
          k:{"median":round(statistics.median(x[k] for x in data["samples"]),3),
             "max":round(max(x[k] for x in data["samples"]),3)}
          for k in fields}
    print("KTERM_RC2S_"+source_label.upper()+"_SNAPSHOT_TO_WPF="+result["result"],flush=True)
    return result
def layout_attribution(repo,label,out):
    # Read-only original failing fixture. No source or assertion relaxation.
    start=time.monotonic()
    argv=["powershell.exe","-NoLogo","-NoProfile","-NonInteractive",
          "-Sta","-ExecutionPolicy","Bypass","-File",
          str(repo/"verification/test-dashboard-resize.ps1"),
          "-Root",str(repo)]
    try:
        p=proc(argv,repo,95);rc=p.returncode;output=p.stdout+"\n"+p.stderr
    except subprocess.TimeoutExpired:
        rc=124;output=""
    categories=sorted(k for k,r in FAIL_CODES.items()
        if re.search(r,output,re.IGNORECASE))
    if rc!=0 and not categories:categories=["UNCLASSIFIED_LAYOUT_FAILURE"]
    result={"source":label,"case":"unchanged_existing_WPF_resize",
        "result":"PASS" if rc==0 and "PASS: real WPF splitter" in output else "FAIL_NOT_WAIVED",
        "exit_code":rc,"reason_classes":categories,
        "elapsed_ms":round((time.monotonic()-start)*1000,2),
        "source_edited":False}
    print("KTERM_RC2S_"+label.upper()+"_UNCHANGED_WPF_RESIZE="+result["result"],flush=True)
    print("KTERM_RC2S_"+label.upper()+"_RESIZE_CAUSE="+",".join(result["reason_classes"]),flush=True)
    return result
def main():
    if len(sys.argv)!=5:raise RuntimeError("ORIGINAL_CAND_WPF_PROBE_OUTPUT_REQUIRED")
    root=pathlib.Path(__file__).resolve().parent
    orig=pathlib.Path(sys.argv[1]).resolve(strict=True)
    cand=pathlib.Path(sys.argv[2]).resolve(strict=True)
    ps=pathlib.Path(sys.argv[3]).resolve(strict=True)
    out=pathlib.Path(sys.argv[4]).resolve()
    if out.exists():raise RuntimeError("PREEXISTING_OUTPUT")
    out.mkdir(mode=0o700,parents=True)
    if ps!=root/"rc2s_wpf_snapshot_probe.ps1":
        raise RuntimeError("UNKNOWN_WPF_TEST_SOURCE")
    report={"schema":"kterminal.rc2s.wpf-consumer-attribution.v1",
       "pinned_source":PIN,
       "known_stale_original_presentation_fixture":"FAIL_RETAINED",
       "known_legacy_fixture_missing_function":"Update-KTerminalAlertHeader",
       "source_modified":False,"broker_calls":False,
       "real_wpf_shipping_window_tested":False,
       "backend_5_second_ticker_measured":False,
       "scope":"original_snapshot_poll_JSON_reader_UpdateDashboard_and_offscreen_WPF",
       "full_windows_regression":False,
       "release_approved":False,"results":[]}
    for label,repo in (("original",orig),("candidate",cand)):
        custody(repo,PIN[label])
        measured=testcase(repo,label,ps,out)
        resize=layout_attribution(repo,label,out)
        custody(repo,PIN[label])
        report["results"].append({"source":label,"consumer":measured,"resize_control":resize})
    output=out/"rc2s-redacted-wpf-timing.json"
    output.write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    print("KTERM_RC2S_ORIGINAL_CUSTODY=PASS",flush=True)
    print("KTERM_RC2S_RELEASE=BLOCKED",flush=True)
    print("KTERM_RC2S_TRUE_DESKTOP_7S_CAUSE=NOT_PROVEN",flush=True)
    return 0 if all(r["consumer"]["result"]=="PASS"
         and r["resize_control"]["result"]=="PASS" for r in report["results"]) else 2
if __name__=="__main__":
    try:sys.exit(main())
    except Exception as ex:
        print("KTERM_RC2S=FAIL_CLOSED:"+type(ex).__name__,flush=True)
        sys.exit(2)
