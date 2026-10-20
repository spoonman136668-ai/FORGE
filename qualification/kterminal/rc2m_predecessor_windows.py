#!/usr/bin/env python3
"""RC2-M: bounded exact-order predecessor regression comparison, no full suite.

This intentionally invokes the original source's Go top-level test registry
(go test -list), then runs only exact immediate predecessors and the failing
test together in ONE Go process, matching Go's registration order. No order
randomization, skipped assertions, broker access, or two-second window edits.
"""
import collections
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ORIGINAL="eb5d225ae73b698a59c68d840daf1ec678e1a0ec"
CANDIDATE="b8c2052d530cdff93462dfccc21b28f3824e5531"
ADDITION="TestHistoricalPnLFullAuditClockAndImmutableJournal"
TARGET="TestCanceledBuyRetryActualAllNineMakerAttemptsWithinOriginalWindow"
TOP=re.compile(r"^Test[A-Za-z0-9_]+$")
CATEGORIZE={
    "TWO_SECOND_WINDOW_OR_ATTEMPT_COUNT":"full original native maker budget failed",
    "MAKER_ATTEMPTS_TRUNCATED":"authorized maker budget truncated",
    "CLIENT_ID_POLICY_OR_QUANTITY":"attempt identity/policy/quantity changed",
    "DUPLICATE_RETRY":"duplicate terminal proof resubmitted",
    "RESERVATION_INTEGRITY":"logical event acquired duplicate reservations",
    "TEST_TIMED_OUT":"panic: test timed out",
}

def command(argv,cwd,env=None,timeout=140):
    return subprocess.run(argv,cwd=cwd,env=env,capture_output=True,
                          text=True,timeout=timeout,check=False)

def exact_order(repo):
    output=command(["go","test","-p=1","-list",".","./pkg"],repo,timeout=200)
    if output.returncode:
        raise RuntimeError("ORIGINAL_GO_TEST_LIST_FAILED")
    names=[]
    for line in output.stdout.splitlines():
        item=line.strip()
        if TOP.fullmatch(item):names.append(item)
    if len(names)!=len(set(names)) or TARGET not in names or len(names)<70:
        raise RuntimeError("ORIGINAL_TEST_REGISTRY_INVALID")
    return names

def test_env(parent):
    parent.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ)
    env["K_TERMINAL_TEST_WORKSPACE"]=str(parent)
    env.update(GOTOOLCHAIN="local",GOTELEMETRY="off",GOFLAGS="-p=1",GOMAXPROCS="2",
               CGO_ENABLED="0",K_TERMINAL_EXECUTION_MODE="PAPER",
               K_TERMINAL_P5_LATENCY="0",K_TERMINAL_NATIVE_TIMING="0")
    for key,name in (
        ("KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT","native-tail"),
        ("KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT","authenticated-post"),
        ("KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT","private-v2")
    ):
        root=parent/name
        root.mkdir(mode=0o700)
        env[key]=str(root)
    return env

def compare_case(repo,chosen,source_label,predecessor_count,work):
    env=test_env(work)
    expr="^(?:"+"|".join(re.escape(n) for n in chosen)+")$"
    if len(expr.encode("utf-8"))>=5000:
        raise RuntimeError("SELECTOR_TOO_LONG")
    cmd=["go","test","-json","-count=1","-p=1","-parallel=1",
         "-timeout=7m","-run",expr,"./pkg"]
    now=time.perf_counter()
    try:
        proc=command(cmd,repo,env=env,timeout=445)
        code=proc.returncode
        stdout=proc.stdout
    except subprocess.TimeoutExpired:
        return {"source":source_label,"predecessors":predecessor_count,
            "status":"FAIL_NOT_WAIVED","exit":124,"reason_classes":["RUN_TIMEOUT"],
            "test_count_expected":len(chosen),"test_count_seen":0,
            "target_run":0,"target_pass":0,"target_fail":0,
            "elapsed_s":445}
    elapsed=round(time.perf_counter()-now,3)
    events=collections.Counter()
    failed={}
    durations={}
    reason_classes=set()
    package_pass=False
    errors=0
    for line in stdout.splitlines():
        try:e=json.loads(line)
        except (TypeError,ValueError):errors+=1;continue
        action=e.get("Action")
        name=e.get("Test")
        if name and action in ("run","pass","fail","skip"):
            events[(name,action)]+=1
            if action in ("fail","skip") and name in chosen:
                failed[name]=action
            if action in ("pass","fail") and name==TARGET and isinstance(e.get("Elapsed"),(int,float)):
                durations[name]=round(e["Elapsed"],6)
        if not name and action=="pass" and e.get("Package")=="k-terminal/pkg":
            package_pass=True
        if action=="output" and (name==TARGET or name is None):
            msg=e.get("Output","")
            for code_name,phrase in CATEGORIZE.items():
                if phrase in msg:reason_classes.add(code_name)
    seen={n for (n,act),count in events.items() if act=="run" and "/" not in n}
    completed={n for (n,act),count in events.items() if act=="pass" and "/" not in n}
    failures={n for (n,act),count in events.items() if act=="fail"}
    skipped={n for (n,act),count in events.items() if act=="skip"}
    complete=(code==0 and errors==0 and package_pass and
              seen==set(chosen) and completed==set(chosen) and
              not failures and not skipped and
              events[(TARGET,"run")]==1 and events[(TARGET,"pass")]==1)
    if not complete and not reason_classes:
        reason_classes.add("UNCLASSIFIED_GO_TEST_FAILURE")
    return {
        "source":source_label,"predecessors":predecessor_count,
        "status":"PASS" if complete else "FAIL_NOT_WAIVED",
        "exit":code,"elapsed_s":elapsed,
        "test_count_expected":len(chosen),
        "test_count_seen":len(seen),
        "target_run":events[(TARGET,"run")],
        "target_pass":events[(TARGET,"pass")],
        "target_fail":events[(TARGET,"fail")],
        "target_elapsed_s":durations.get(TARGET),
        "other_failed_test_count":len(failures-{TARGET}),
        "other_skipped_test_count":len(skipped),
        "reason_classes":sorted(reason_classes),
        "parser_error_count":errors,
    }

def main():
    if len(sys.argv)!=4:raise RuntimeError("EXPECTED_ORIGINAL_CANDIDATE_TEMP")
    original=pathlib.Path(sys.argv[1]).resolve(strict=True)
    candidate=pathlib.Path(sys.argv[2]).resolve(strict=True)
    temp=pathlib.Path(sys.argv[3]).resolve()
    if temp.exists():raise RuntimeError("WORKSPACE_ALREADY_EXISTS")
    temp.mkdir(mode=0o700,parents=True)
    for path,sha in ((original,ORIGINAL),(candidate,CANDIDATE)):
        p=command(["git","-C",str(path),"rev-parse","HEAD"],path)
        d=command(["git","-C",str(path),"status","--porcelain"],path)
        if p.returncode or p.stdout.strip()!=sha or d.returncode or d.stdout.strip():
            raise RuntimeError("FROZEN_SOURCE_IDENTITY_DRIFT")
    old=exact_order(original)
    new=exact_order(candidate)
    if [x for x in new if x!=ADDITION]!=old or new.count(ADDITION)!=1:
        raise RuntimeError("ORIGINAL_GO_TEST_ORDER_DRIFT")
    at=old.index(TARGET)
    if at<48:raise RuntimeError("TOO_FEW_PREDECESSORS")
    original_predecessors=old[:at]
    windows=(8,24,48)
    report={
        "schema":"kterminal.rc2m.original-go-order-predecessor-control.v1",
        "original_sha":ORIGINAL,"candidate_sha":CANDIDATE,
        "target":TARGET,
        "registry_top_level_original":len(old),
        "registry_top_level_candidate":len(new),
        "target_registry_index":at,
        "original_order_preserved_with_single_expected_addition":True,
        "immediately_preceding_24":original_predecessors[-24:],
        "predecessor_windows":list(windows),"runs":[],
        "full_suite_executed":False,"runtime_logic_modified":False,
        "full_regression_gate":"BLOCKED",
    }
    print("KTERM_RC2M_ORIGINAL_TARGET_GO_REGISTRY_INDEX="+str(at))
    print("KTERM_RC2M_DIRECT_PREDECESSOR="+old[at-1])
    print("KTERM_RC2M_DIRECT_PREDECESSORS_8="+",".join(old[at-8:at]))
    print("KTERM_RC2M_ORIGINAL_REGISTRY_EQUIVALENCE=PASS")
    budget_start=time.monotonic()
    for n in windows:
        chosen=old[at-n:at]+[TARGET]
        # Alternating exact-source order avoids a single-source compilation advantage.
        for label,repo in (("original",original),("candidate",candidate)):
            if time.monotonic()-budget_start>1000:
                raise RuntimeError("BOUND_EXHAUSTED_BEFORE_ALL_PREDECESSOR_WINDOWS")
            row=compare_case(repo,chosen,label,n,temp/(label+"-preceding-"+str(n)))
            report["runs"].append(row)
            print("KTERM_RC2M_"+label.upper()+"_PRIOR_"+str(n)+"="+row["status"]+
                "_TARGET_PASS_"+str(row["target_pass"])+
                "_TARGET_FAIL_"+str(row["target_fail"]))
            if row["reason_classes"]:
                print("KTERM_RC2M_REASON="+",".join(row["reason_classes"]))
    out=temp/"rc2m-redacted.json"
    out.write_text(json.dumps(report,sort_keys=True,indent=2),encoding="utf-8")
    bad=[row for row in report["runs"] if row["status"]!="PASS"]
    if bad:
        print("KTERM_RC2M_PREDECESSOR_GROUPS=NEGATIVES_RETAINED")
    else:
        print("KTERM_RC2M_PREDECESSOR_GROUPS=NO_REPRODUCTION_IN_BOUNDED_WINDOWS")
    print("KTERM_RC2M_FULL_WINDOWS_REGRESSION=NOT_RUN_NOT_WAIVED")
    print("KTERM_RC2M_RELEASE=BLOCKED")
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("KTERM_RC2M_DIAGNOSTIC=FAIL_CLOSED:"+type(e).__name__+
              ":"+str(e).split(":")[0])
        sys.exit(2)
