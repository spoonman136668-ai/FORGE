#!/usr/bin/env python3
"""RC2-R4 unchanged WPF snapshot-consumer and real layout exercises.

Uses frozen original and PR73 PowerShell tests on Windows STA; safe fixture
files only, no app startup and no external order transport. Captures timings
and PASS receipts, not source, test output or rendered images.
"""
import json,pathlib,subprocess,sys,time
PINS={"original":"eb5d225ae73b698a59c68d840daf1ec678e1a0ec",
      "candidate":"b8c2052d530cdff93462dfccc21b28f3824e5531"}
CASES=(
  ("snapshot_gap","verification/test-dashboard-snapshot-gap.ps1",False,
     "PASS: deterministic snapshot replacement gap"),
  ("actual_wpf_layout","verification/test-dashboard-resize.ps1",True,
     "PASS: real WPF splitter"),
)
def command(args,cwd,limit=120):
    return subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,
         stderr=subprocess.PIPE,text=True,timeout=limit,check=False)
def main():
    if len(sys.argv)!=4:raise RuntimeError("EXPECTED_ORIGINAL_CAND_OUTPUT")
    original=pathlib.Path(sys.argv[1]).resolve(strict=True)
    candidate=pathlib.Path(sys.argv[2]).resolve(strict=True)
    root=pathlib.Path(sys.argv[3]).resolve()
    if root.exists():raise RuntimeError("OUTPUT_ALREADY_PRESENT")
    root.mkdir(mode=0o700,parents=True)
    result={"schema":"kterminal.rc2r4.wpf-current-consumer-and-layout.v1",
        "frozen_source_pins":PINS,"source_edited":False,
        "app_started":False,"broker_contact":False,
        "actual_window_content_layout_tested":True,
        "shipping_exe_pixel_latency_measured":False,
        "full_regression_approved":False,"results":[]}
    for label,repo in (("original",original),("candidate",candidate)):
        sha=command(["git","rev-parse","HEAD"],repo)
        st=command(["git","status","--porcelain"],repo)
        if sha.stdout.strip()!=PINS[label] or st.stdout.strip() or sha.returncode or st.returncode:
            raise RuntimeError("SOURCE_IDENTITY_DRIFT")
        for name,relative,creates_images,marker in CASES:
            argv=["powershell.exe","-NoProfile","-NonInteractive","-NoLogo",
                "-Sta","-ExecutionPolicy","Bypass","-File",str(repo/relative),
                "-Root",str(repo)]
            if creates_images:
                destination=root/(label+"-"+name)
                destination.mkdir(mode=0o700)
                argv+=["-OutputDirectory",str(destination)]
            start=time.monotonic()
            try:
                p=command(argv,repo,limit=145)
                e=p.returncode
                passed=e==0 and marker in p.stdout
            except subprocess.TimeoutExpired:
                e=124;passed=False
            elapsed=round((time.monotonic()-start)*1000,2)
            row={"source":label,"case":name,
                "status":"PASS" if passed else "FAIL_NOT_WAIVED",
                "exit":e,"wall_ms":elapsed,
                "actual_layout_bitmap_rendered":creates_images and passed,
                "saved_bitmaps_not_published":True,
                "genuine_full_desktop_application_tested":False}
            result["results"].append(row)
            print("KTERM_RC2R4_"+label.upper()+"_"+name.upper()+"="+row["status"],flush=True)
            if creates_images:
                # Preserve only basename-level existence evidence. Source
                # images remain inside the private runner and expire.
                row["private_raster_output_count"]=len(list(destination.glob("*.png")))
    (root/"rc2r4-redacted-wpf.json").write_text(
       json.dumps(result,sort_keys=True,indent=2),encoding="utf-8")
    print("KTERM_RC2R4_ORIGINAL_STALE_PRESENTATION_TEST=RETAINED_FAILED")
    print("KTERM_RC2R4_SOURCE_MODIFICATION=NONE")
    print("KTERM_RC2R4_COMPLETE_DESKTOP_LATENCY=NOT_MEASURED")
    print("KTERM_RC2R4_RELEASE=BLOCKED")
    return 0 if all(x["status"]=="PASS" for x in result["results"]) else 2
if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("KTERM_RC2R4_SETUP=FAIL_CLOSED:"+type(e).__name__,flush=True)
        sys.exit(2)
