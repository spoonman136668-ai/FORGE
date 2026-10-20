#!/usr/bin/env python3
"""RC2-M2: retain exact failed test names from the 24-predecessor anomaly.

Frozen original and PR #73, Windows, single process, original Go ordering.
No application execution, synthetic fixtures only, no full regression.
Failure names are accepted only from the exact registered Go Test identifiers.
"""
import collections
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
NEW_TEST="TestHistoricalPnLFullAuditClockAndImmutableJournal"
TOP=re.compile(r"^Test[A-Za-z0-9_]+$")

def command(argv,cwd,env=None,timeout=180):
    return subprocess.run(argv,cwd=cwd,env=env,text=True,capture_output=True,
                          check=False,timeout=timeout)

def test_list(repo):
    p=command(["go","test","-p=1","-list",".","./pkg"],repo)
    if p.returncode:raise RuntimeError("GO_TEST_LIST_FAILED")
    l=[s.strip() for s in p.stdout.splitlines() if TOP.fullmatch(s.strip())]
    if len(l)!=len(set(l)) or TARGET not in l:raise RuntimeError("TEST_REGISTRY_INVALID")
    return l

def fixture_env(root):
    root.mkdir(mode=0o700,parents=False,exist_ok=False)
    e=dict(os.environ)
    e.update(GOTOOLCHAIN="local",GOTELEMETRY="off",GOMAXPROCS="2",
             GOFLAGS="-p=1",CGO_ENABLED="0",K_TERMINAL_EXECUTION_MODE="PAPER",
             K_TERMINAL_P5_LATENCY="0",K_TERMINAL_NATIVE_TIMING="0",
             K_TERMINAL_TEST_WORKSPACE=str(root))
    for k,s in (
        ("KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT","native-tail"),
        ("KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT","authenticated-post"),
        ("KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT","private-v2")
    ):
        d=root/s;d.mkdir(mode=0o700);e[k]=str(d)
    return e

def exercise(label,repo,group,dirpath,trial):
    env=fixture_env(dirpath)
    selector="^(?:"+"|".join(re.escape(n) for n in group)+")$"
    if len(selector)>5500:raise RuntimeError("SELECTOR_TOO_LONG")
    t=time.perf_counter()
    try:
        result=command(["go","test","-json","-count=1","-p=1","-parallel=1",
                        "-timeout=5m","-run",selector,"./pkg"],
                       repo,env=env,timeout=340)
        output=result.stdout
        code=result.returncode
    except subprocess.TimeoutExpired:
        return {"source":label,"trial":trial,"go_exit":124,
                "status":"FAIL_NOT_WAIVED","reasons":["RUN_TIMEOUT"]}
    elapsed=round(time.perf_counter()-t,3)
    ran=collections.Counter();passed=collections.Counter()
    failed=set();skipped=set()
    target_elapsed=None;bad=0
    for line in output.splitlines():
        try:e=json.loads(line)
        except ValueError:bad+=1;continue
        name=e.get("Test")
        act=e.get("Action")
        if not isinstance(name,str):continue
        if act=="run":ran[name]+=1
        if act=="pass":passed[name]+=1
        if act=="fail":failed.add(name)
        if act=="skip":skipped.add(name)
        if name==TARGET and act in ("pass","fail"):
            v=e.get("Elapsed")
            if isinstance(v,(int,float)):target_elapsed=round(v,6)
    success=(code==0 and bad==0 and not failed and not skipped and
             {n for n in ran if "/" not in n}==set(group) and
             {n for n in passed if "/" not in n}==set(group))
    leaf=sorted(x for x in failed if not any(
        y!=x and y.startswith(x+"/") for y in failed))
    # Only original compiler-reported test names are retained; no fixture data.
    eligible=lambda x: all(TOP.fullmatch(segment) or
        re.fullmatch(r"[A-Za-z0-9_.=-]+",segment) for segment in x.split("/"))
    return {
        "source":label,"trial":trial,"status":"PASS" if success else "FAIL_NOT_WAIVED",
        "go_exit":code,"elapsed_s":elapsed,"parse_errors":bad,
        "selected_top_level":len(group),
        "observed_top_level":len({n for n in ran if "/" not in n}),
        "failed_names":sorted(x for x in failed if eligible(x))[:20],
        "failed_leaf_names":list(filter(eligible,leaf))[:20],
        "skipped_names":sorted(x for x in skipped if eligible(x))[:12],
        "target_run":ran[TARGET],"target_pass":passed[TARGET],
        "target_fail":int(TARGET in failed),
        "target_elapsed_s":target_elapsed
    }

def main():
    if len(sys.argv)!=4:raise RuntimeError("EXPECTED_SOURCE_SOURCE_OUT")
    orig=pathlib.Path(sys.argv[1]).resolve(strict=True)
    cand=pathlib.Path(sys.argv[2]).resolve(strict=True)
    root=pathlib.Path(sys.argv[3]).resolve()
    if root.exists():raise RuntimeError("OUTPUT_ALREADY_EXISTS")
    root.mkdir(mode=0o700,parents=True)
    for src,sha in ((orig,BASE),(cand,CANDIDATE)):
        s=command(["git","-C",str(src),"rev-parse","HEAD"],src)
        d=command(["git","-C",str(src),"status","--porcelain"],src)
        if s.returncode or d.returncode or s.stdout.strip()!=sha or d.stdout.strip():
            raise RuntimeError("SOURCE_IDENTITY_DRIFT")
    original=test_list(orig)
    candidate=test_list(cand)
    if [n for n in candidate if n!=NEW_TEST]!=original or candidate.count(NEW_TEST)!=1:
        raise RuntimeError("GO_TEST_REGISTRATION_ORDER_DRIFT")
    i=original.index(TARGET)
    if i<24:raise RuntimeError("TOO_FEW_PREDECESSORS")
    selected=original[i-24:i+1]
    report={"schema":"kterminal.rc2m2.failed-predecessor-identities.v1",
            "original_sha":BASE,"candidate_sha":CANDIDATE,
            "target":TARGET,"registry_index":i,"selected_tests":selected,
            "tests_modified":False,"full_regression_executed":False,
            "runs":[],"solo_negative_replays":[]}
    # Alternate source order to keep compilation/load asymmetry visible.
    schedule=[("candidate",cand,1),("original",orig,1),
              ("candidate",cand,2),("original",orig,2),
              ("candidate",cand,3),("candidate",cand,4)]
    negatives=set()
    for label,repo,number in schedule:
        case=exercise(label,repo,selected,
                      root/(label+"-prior24-"+str(number)),number)
        report["runs"].append(case)
        if case["status"]!="PASS":negatives.update(case.get("failed_leaf_names",[]))
        print("KTERM_RC2M2_"+label.upper()+"_PRIOR24_TRIAL_"+str(number)+
              "="+case["status"]+"_TARGET_PASS_"+str(case.get("target_pass",0)))
        if case.get("failed_leaf_names"):
            print("KTERM_RC2M2_FAILING_LEAF_TESTS="+",".join(case["failed_leaf_names"]))
    # Narrow reproduction: only top-level registered tests, never select an
    # arbitrary subtest without its parent.
    suspects=sorted({name.split("/")[0] for name in negatives
                     if name.split("/")[0] in selected})[:4]
    for suspect in suspects:
        for label,repo in (("original",orig),("candidate",cand)):
            case=exercise(label,repo,[suspect],
                 root/(label+"-solo-"+suspect),1)
            report["solo_negative_replays"].append(case)
            print("KTERM_RC2M2_ISOLATED_"+label.upper()+"_"+suspect+"="+case["status"])
    dest=root/"rc2m2-redacted.json"
    dest.write_text(json.dumps(report,sort_keys=True,indent=2),encoding="utf-8")
    print("KTERM_RC2M2_NEGATIVE_GROUP_RUNS="+str(sum(
        row["status"]!="PASS" for row in report["runs"])))
    print("KTERM_RC2M2_TEST_NAMES_CUSTODY=CAPTURED_NOT_WAIVED")
    print("KTERM_RC2M2_FULL_REGRESSION=NOT_RUN")
    print("KTERM_RC2M2_RELEASE=BLOCKED")
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("KTERM_RC2M2_DIAGNOSTIC=FAIL_CLOSED:"+type(e).__name__)
        sys.exit(2)
