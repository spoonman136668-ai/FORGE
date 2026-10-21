#!/usr/bin/env python3
"""RC2-R2 read-only WPF fixture failure attribution.

Runs existing original/candidate presentation verification without modifying
the original scripts. Publishes only allowlisted error classes, exit values,
and whether the known PASS receipt was present. No WPF source/log dumps.
"""
import json,pathlib,re,subprocess,sys,time
PINS={"original":"eb5d225ae73b698a59c68d840daf1ec678e1a0ec",
      "candidate":"b8c2052d530cdff93462dfccc21b28f3824e5531"}
PATTERNS={
 "WINDOWS_PRESENTATION_FRAMEWORK_MISSING":r"Could not load file or assembly.*PresentationFramework|Cannot find path.*PresentationFramework",
 "XAML_OR_PS_PARSE_FAILURE":r"ParserError|ParseException|The string is missing the terminator",
 "COMMAND_NOT_FOUND":r"CommandNotFoundException|The term.*is not recognized",
 "MISSING_MOCK_CONTROL":r"Cannot index into a null array|Cannot find an overload|You cannot call a method on a null",
 "STRICT_MODE_PROPERTY_OR_VARIABLE":r"PropertyNotFoundException|VariableIsUndefined|The property .* cannot be found",
 "WPF_STA_CONSTRAINT":r"apartment|Single-Threaded Apartment|STA",
 "WPF_TYPE_INIT_FAILURE":r"TypeInitializationException|Cannot find type|Unable to find type",
 "INHERITED_PRESENTATION_ASSERTION":r"Presentation churn|Financial tones missing|Incomplete flat execution display|Render receipt did not reflect|Refresh diagnostics were not bounded",
 "BOUNDARY_OR_RETURN_CONTRACT":r"Failed to bind|Cannot convert|ParameterBindingException|ParameterArgumentValidationError",
}
def call(args,at,seconds=70):
    return subprocess.run(args,cwd=at,capture_output=True,
          text=True,check=False,timeout=seconds)
def main():
    if len(sys.argv)!=4:raise RuntimeError("EXPECTED_ORIGINAL_CANDIDATE_OUTPUT")
    orig=pathlib.Path(sys.argv[1]).resolve(strict=True)
    cand=pathlib.Path(sys.argv[2]).resolve(strict=True)
    out=pathlib.Path(sys.argv[3]).resolve()
    if out.exists():raise RuntimeError("EXISTING_OUTPUT")
    out.mkdir(mode=0o700,parents=True)
    results=[]
    for label,repo in (("original",orig),("candidate",cand)):
        sha=call(["git","rev-parse","HEAD"],repo)
        status=call(["git","status","--porcelain"],repo)
        if sha.stdout.strip()!=PINS[label] or sha.returncode or status.stdout.strip() or status.returncode:
            raise RuntimeError("SOURCE_IDENTITY_OR_CLEANLINESS_FAILED")
        script=repo/"verification/test-dashboard-presentation.ps1"
        before=time.monotonic()
        try:
            p=call(["powershell.exe","-NoLogo","-NoProfile",
               "-NonInteractive","-Sta","-ExecutionPolicy","Bypass",
               "-File",str(script),"-Root",str(repo)],repo)
            exit=p.returncode
            combined=p.stdout+"\n"+p.stderr
            receipt="PASS: strict-mode" in p.stdout
        except subprocess.TimeoutExpired:
            exit=124
            combined=""
            receipt=False
        failure_classes=sorted(k for k,pattern in PATTERNS.items()
            if re.search(pattern,combined,re.IGNORECASE))
        # Windows PowerShell normally prints a FullyQualifiedErrorId; its
        # opaque value is restricted to a bounded safe identifier.
        fqids=sorted(set(re.findall(
            r"FullyQualifiedErrorId\s*:\s*([A-Za-z_][A-Za-z0-9_,.-]{0,80})",combined)))[:4]
        result={"source":label,"exit":exit,
            "pass_marker":receipt,"elapsed_s":round(time.monotonic()-before,3),
            "failure_classes":failure_classes,
            "powershell_error_identifiers":fqids,
            "status":"PASS" if exit==0 and receipt else "FAIL_NOT_WAIVED"}
        results.append(result)
        print("KTERM_RC2R2_"+label.upper()+"_WPF_CONTROL="+result["status"],flush=True)
        print("KTERM_RC2R2_"+label.upper()+"_CAUSE="+
          ",".join(failure_classes or (["NO_ALLOWLIST_MATCH"] if exit else ["NO_PASS_MARKER"])),flush=True)
        print("KTERM_RC2R2_"+label.upper()+"_EXIT="+str(exit),flush=True)
    (out/"rc2r2-redacted-wpf-identity.json").write_text(json.dumps(
        {"schema":"kterminal.rc2r2.wpf-fixture-control-attribution.v1",
         "source_sha":PINS,"source_modified":False,"results":results,
         "original_desktop_paint_measured":False,
         "full_regression_run":False,"release_approved":False},
          indent=2,sort_keys=True),encoding="utf-8")
    print("KTERM_RC2R2_WPF_FAILURES_RETAINED=TRUE")
    print("KTERM_RC2R2_RELEASE=BLOCKED")
    return 0
if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("KTERM_RC2R2_SETUP=FAIL_CLOSED:"+type(e).__name__,flush=True)
        sys.exit(2)
