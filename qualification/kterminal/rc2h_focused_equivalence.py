#!/usr/bin/env python3
"""RC2-H bounded isolated Windows control: serial vs 2-process focused tests.

This is NOT a replacement for the full source-exact Windows regression.
Works only against the frozen RC2 candidate. Each tested process gets its own
fresh git worktree, working directory, retention roots and temp directories.
Never writes to the user's installation, never invokes the application, and
fails on any test failure, missing test, or child/subtest identity drift.
"""
import collections
import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

CANDIDATE = "b8c2052d530cdff93462dfccc21b28f3824e5531"
TOP = re.compile(r"^Test[A-Za-z0-9_]+$")
FOCUSED = re.compile(
    r"^(?:TestHistoricalPnL|TestHistoricalOrderScope|TestHistoricalScope|"
    r"TestIncrementalRestart|TestNativeObservation|TestPerformanceDrawdown|"
    r"TestStage3NativeHistoricalHistoryCheckpointV2)"
)

def checked(command, cwd=None, env=None, timeout=160):
    proc = subprocess.run(command, cwd=cwd, env=env, check=False, capture_output=True,
                          text=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError("COMMAND_FAILED:" + command[0] + ":rc=" + str(proc.returncode))
    return proc.stdout

def inventory(source):
    out = checked(["go", "test", "-p=1", "-list", ".", "./pkg"], cwd=source)
    tests = []
    for line in out.splitlines():
        item=line.strip()
        if TOP.fullmatch(item) and FOCUSED.match(item):
            tests.append(item)
    if not tests or len(tests)!=len(set(tests)):
        raise RuntimeError("EMPTY_OR_DUPLICATE_FOCUSED_INVENTORY")
    required=("TestHistoricalPnLFullAuditClockAndImmutableJournal",
              "TestStage3NativeHistoricalHistoryCheckpointV2")
    if any(x not in tests for x in required):
        raise RuntimeError("FOCUSED_CORE_TEST_MISSING")
    return sorted(tests)

def new_workspace(source, temp, suffix):
    root=temp/suffix
    if root.exists(): raise RuntimeError("WORKSPACE_ALREADY_EXISTS")
    root.parent.mkdir(parents=True,exist_ok=True)
    checked(["git", "-C", str(source), "worktree", "add", "--detach",
             str(root), CANDIDATE],timeout=120)
    got=checked(["git", "-C", str(root), "rev-parse", "HEAD"]).strip()
    if got != CANDIDATE:raise RuntimeError("WORKTREE_IDENTITY_DRIFT")
    return root

def run_case(label, source, path, tests, temp):
    root=path
    fixture=temp/(label+"-fixture")
    fixture.mkdir(mode=0o700)
    env=dict(os.environ)
    env["K_TERMINAL_TEST_WORKSPACE"]=str(fixture)
    for name,rel in (
        ("KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT","native-tail"),
        ("KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT","authenticated-post"),
        ("KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT","private-v2")):
        location=fixture/rel
        location.mkdir(mode=0o700)
        env[name]=str(location)
    env["K_TERMINAL_EXECUTION_MODE"]="PAPER"
    env["GOTOOLCHAIN"]="local"
    env["GOTELEMETRY"]="off"
    env["GOFLAGS"]="-p=1"
    env["GOMAXPROCS"]="2"
    env["CGO_ENABLED"]="0"
    # Anchored exact top-level tests, each keeps all its subtests intact.
    run_regex="^("+"|".join(re.escape(x) for x in tests)+")$"
    if len(run_regex.encode("utf-8"))>5000:raise RuntimeError("FOCUSED_SELECTOR_TOO_LONG")
    output=temp/(label+"-results.jsonl")
    stderr=temp/(label+"-stderr.txt")
    start=time.monotonic()
    with output.open("wb") as stdout,stderr.open("wb") as errors:
        try:
            proc=subprocess.run(["go","test","-json","-count=1","-p=1",
                                 "-parallel=1","-timeout=14m",
                                 "-run",run_regex,"./pkg"],
                                cwd=root, env=env, stdout=stdout, stderr=errors,
                                timeout=890, check=False)
            code=proc.returncode
        except subprocess.TimeoutExpired:
            code=124
    elapsed=round(time.monotonic()-start,3)
    executed=collections.Counter()
    passes=collections.Counter()
    failures=collections.Counter()
    package_pass=False
    parse_errors=0
    with output.open(encoding="utf-8",errors="replace") as stream:
        for line in stream:
            try:ev=json.loads(line)
            except ValueError:parse_errors+=1;continue
            n=ev.get("Test")
            action=ev.get("Action")
            if action=="run" and n:executed[n]+=1
            if action=="pass" and n:passes[n]+=1
            if action=="fail" and n:failures[n]+=1
            if action=="pass" and not n and ev.get("Package")=="k-terminal/pkg":
                package_pass=True
    good=(code==0 and parse_errors==0 and not failures and package_pass and
          sorted(n for n in executed if "/" not in n)==sorted(tests) and
          executed==passes)
    # Do not emit raw logs, paths, fixtures or test data.
    return {"label":label, "ok":good, "exit":code, "elapsed_s":elapsed,
            "run_count":sum(executed.values()),"pass_count":sum(passes.values()),
            "fail_count":sum(failures.values()),
            "test_names":set(executed),"pass_names":set(passes),
            "top_level_count":len(tests),"parse_errors":parse_errors}

def main():
    if len(sys.argv)!=3:
        raise SystemExit("USAGE: rc2h_focused_equivalence.py <source-path> <temp-empty-path>")
    source=pathlib.Path(sys.argv[1]).resolve(strict=True)
    temp=pathlib.Path(sys.argv[2]).resolve()
    if temp.exists():raise SystemExit("FAIL_CLOSED:TEMP_ALREADY_EXISTS")
    temp.mkdir(parents=True,exist_ok=False)
    actual=checked(["git","-C",str(source),"rev-parse","HEAD"]).strip()
    if actual!=CANDIDATE:raise SystemExit("FAIL_CLOSED:IDENTITY_DRIFT")
    tests=inventory(source)
    groups=[[],[]]
    for n in tests:
        index=int(hashlib.sha256(n.encode("utf-8")).hexdigest()[:8],16)%2
        groups[index].append(n)
    if any(not g for g in groups) or sorted(groups[0]+groups[1])!=tests:
        raise SystemExit("FAIL_CLOSED:STATIC_SELECTION")
    # Git metadata maintenance is serialized; only test processes overlap.
    serial_root=new_workspace(source,temp,"serial")
    shard0_root=new_workspace(source,temp,"shard0")
    shard1_root=new_workspace(source,temp,"shard1")
    serial=run_case("serial",source,serial_root,tests,temp)
    print("KTERM_RC2H_FOCUSED_SERIAL="+("PASS" if serial["ok"] else "FAIL"))
    print("KTERM_RC2H_FOCUSED_SERIAL_SECONDS="+str(serial["elapsed_s"]))
    if not serial["ok"]:return 2
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f0=pool.submit(run_case,"shard0",source,shard0_root,groups[0],temp)
        f1=pool.submit(run_case,"shard1",source,shard1_root,groups[1],temp)
        p0,p1=f0.result(),f1.result()
    members=(p0,p1)
    combined=sorted(p0["test_names"] | p1["test_names"])
    intersects=p0["test_names"] & p1["test_names"]
    identical=(not intersects and set(combined)==serial["test_names"]
               and (p0["pass_names"] | p1["pass_names"])==serial["pass_names"]
               and p0["ok"] and p1["ok"])
    print("KTERM_RC2H_FOCUSED_TOP_LEVEL_TESTS="+str(len(tests)))
    print("KTERM_RC2H_TWO_SHARD_SELECTED="+str([len(x) for x in groups]))
    print("KTERM_RC2H_TWO_SHARD_WALL_SECONDS="+str(max(x["elapsed_s"] for x in members)))
    print("KTERM_RC2H_SHARD_TEST_NAME_INTERSECTION="+str(len(intersects)))
    print("KTERM_RC2H_PARALLEL_FOCUSED_EQUIVALENCE="+("PASS" if identical else "FAIL_NOT_WAIVED"))
    print("KTERM_RC2H_FULL_PARALLEL_EQUIVALENCE=NOT_YET_QUALIFIED")
    print("KTERM_RC2H_FULL_WINDOWS_REGRESSION=STILL_REQUIRED")
    return 0 if identical else 2

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("KTERM_RC2H_CONTROL=FAIL_CLOSED:"+type(e).__name__+":"+str(e).split(":")[0])
        sys.exit(2)
