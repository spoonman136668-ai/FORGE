"""RAR-G126 development-only Windows Go full-package A/B/B/A, same runner.
All existing mandatory F139, Go vet/build and Linux race tests are unchanged.
The only intervention is Go's build/package -p concurrency for go test.
"""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
BASE="35278695e44b6d9efd6a3889e55d02506b2fe2da"
BRANCH="engineering/rar-g126-windows-go-test-parallelism-20261108"
ORDER=("p2","p4","p4","p2")
MAX_ARM=165
MEM_CAP=4*1024**3
REL_CAP=1.50
GAIN_MIN=1.10
PAIR_MIN=1.02

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,timeout=75,text=True).strip()

def stable(sha):
    if git("rev-parse","HEAD")!=sha or git("status","--porcelain","--untracked-files=all"):
        raise ValueError("G126_SOURCE_DRIFT")

class JobTreeMemory:
    """Windows Job Object highwater of committed bytes across workers AND descendants."""
    class Basic(ctypes.Structure):
        _fields_=[("PerProcessUserTimeLimit",ctypes.c_longlong),
                  ("PerJobUserTimeLimit",ctypes.c_longlong),
                  ("LimitFlags",wintypes.DWORD),
                  ("MinimumWorkingSetSize",ctypes.c_size_t),
                  ("MaximumWorkingSetSize",ctypes.c_size_t),
                  ("ActiveProcessLimit",wintypes.DWORD),
                  ("Affinity",ctypes.c_size_t),
                  ("PriorityClass",wintypes.DWORD),
                  ("SchedulingClass",wintypes.DWORD)]
    class IO(ctypes.Structure):
        _fields_=[(x,ctypes.c_ulonglong) for x in
                  ("ReadOperationCount","WriteOperationCount","OtherOperationCount",
                   "ReadTransferCount","WriteTransferCount","OtherTransferCount")]
    class Extended(ctypes.Structure):
        pass
    Extended._fields_=[("BasicLimitInformation",Basic),("IoInfo",IO),
                       ("ProcessMemoryLimit",ctypes.c_size_t),
                       ("JobMemoryLimit",ctypes.c_size_t),
                       ("PeakProcessMemoryUsed",ctypes.c_size_t),
                       ("PeakJobMemoryUsed",ctypes.c_size_t)]
    def __init__(self):
        self.api=ctypes.WinDLL("kernel32",use_last_error=True)
        self.api.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype=wintypes.HANDLE
        self.api.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
        self.api.AssignProcessToJobObject.restype=wintypes.BOOL
        self.api.QueryInformationJobObject.argtypes=[
            wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD)]
        self.api.QueryInformationJobObject.restype=wintypes.BOOL
        self.api.CloseHandle.argtypes=[wintypes.HANDLE]
        self.api.CloseHandle.restype=wintypes.BOOL
        self.handle=self.api.CreateJobObjectW(None,None)
        if not self.handle: raise ValueError("G126_CREATE_JOB_FAILED")
        self.high=0
    def assign(self,p):
        if not self.api.AssignProcessToJobObject(self.handle,p._handle):
            raise ValueError("G126_JOB_ASSIGNMENT_FAILED_"+str(ctypes.get_last_error()))
    def peak(self):
        info=self.Extended()
        returned=wintypes.DWORD()
        if not self.api.QueryInformationJobObject(self.handle,9,ctypes.byref(info),
                ctypes.sizeof(info),ctypes.byref(returned)):
            raise ValueError("G126_JOB_TREE_MEMORY_UNREADABLE")
        if returned.value < ctypes.sizeof(info):
            raise ValueError("G126_JOB_TREE_MEMORY_SHORT_READ")
        self.high=max(self.high,int(info.PeakJobMemoryUsed))
        return self.high
    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle=None


def child(args):
    gate=Path(os.environ["FORGE_G126_GATE"])
    stop=time.monotonic()+30
    while not gate.is_file():
        if time.monotonic()>stop:raise ValueError("G126_ASSIGNMENT_TIMEOUT")
        time.sleep(0.02)
    env={**os.environ,"GOFLAGS":"-p=4" if args.mode=="p4" else "-p=2",
         "GOMAXPROCS":"2","GOMEMLIMIT":"1536MiB"}
    started=time.perf_counter()
    try:
        done=subprocess.run(["go","test","-count=1","./..."],cwd=ROOT,env=env,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,
            errors="replace",timeout=MAX_ARM,check=False)
        states={}
        for line in done.stdout.splitlines():
            terms=line.strip().split()
            if len(terms)>1 and terms[0] in ("ok","?"):
                if terms[1] in states:raise ValueError("G126_DUPLICATE_PACKAGE")
                states[terms[1]]="PASS" if terms[0]=="ok" else "NO_TEST_FILES"
        if done.returncode:
            raise ValueError("G126_REAL_GO_TEST_FAILED:"+done.stdout[-1200:])
        result=dict(mode=args.mode,seconds=round(time.perf_counter()-started,6),
                    packages=states,go_returncode=done.returncode,
                    test_count_cache_disabled=True,successful=True)
        args.output.write_text(json.dumps(result,sort_keys=True),encoding="utf-8")
        return 0
    except BaseException as err:
        args.output.write_text(json.dumps(dict(mode=args.mode,successful=False,
            error=type(err).__name__+":"+str(err)[-1200:]),sort_keys=True),encoding="utf-8")
        raise

def arm(mode,expected):
    with tempfile.TemporaryDirectory(prefix="g126-windows-",dir=os.environ["RUNNER_TEMP"]) as d:
        home=Path(d);gate=home/"assigned";output=home/"result.json"
        log=(home/"child.log").open("w",encoding="utf-8")
        meter=JobTreeMemory()
        proc=None;high=0
        started=time.perf_counter()
        try:
            private=home/"tmp";private.mkdir()
            env={**os.environ,"FORGE_G126_GATE":str(gate),
                 "TEMP":str(private),"TMP":str(private),"TMPDIR":str(private),
                 "PYTHONDONTWRITEBYTECODE":"1"}
            proc=subprocess.Popen([sys.executable,"-B",str(Path(__file__)),
                    "--worker","--mode",mode,"--output",str(output)],
                    cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            meter.assign(proc)
            gate.write_text("ok\n",encoding="utf-8")
            while proc.poll() is None:
                high=max(high,meter.peak())
                if high>MEM_CAP:raise ValueError("G126_TREE_COMMIT_CAP_EXCEEDED")
                if time.perf_counter()-started>MAX_ARM:
                    raise ValueError("G126_ARM_TIMEOUT")
                time.sleep(0.18)
            high=max(high,meter.peak())
            if proc.wait(timeout=10)!=0:
                raise ValueError("G126_ARM_FAILED:"+str(output.read_text(encoding="utf-8")[-900:]
                                  if output.is_file() else "UNRECORDED"))
            result=json.loads(output.read_text(encoding="utf-8"))
            if (not result["successful"] or (expected is not None and result["packages"]!=expected) or
                    not 0<high<=MEM_CAP):
                raise ValueError("G126_FULL_PACKAGE_PARITY_OR_MEMORY_FAILED")
            result["tree_peak_commit_bytes"]=high
            result["tree_scope"]="WIN_JOB_OBJECT_PYTHON_GO_AND_DESCENDANTS"
            return result
        except BaseException:
            if proc and proc.poll() is None:
                proc.kill();proc.wait(timeout=15)
            raise
        finally:
            log.close();meter.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--worker",action="store_true")
    ap.add_argument("--mode",choices=("p2","p4"))
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    if args.worker:
        if not args.mode or not args.output:raise ValueError("G126_WORKER_INVALID")
        return child(args)
    if (os.name!="nt" or os.environ.get("GITHUB_ACTIONS")!="true"
            or os.environ.get("GITHUB_REPOSITORY")!="spoonman136668-ai/FORGE"
            or os.environ.get("GITHUB_EVENT_NAME")!="pull_request"
            or os.environ.get("GITHUB_HEAD_REF")!=BRANCH
            or not os.environ.get("RUNNER_TEMP")):
        raise ValueError("G126_WINDOWS_PR_ONLY")
    sha=git("rev-parse","HEAD")
    if sha!=os.environ.get("FORGE_G126_HEAD") or git("merge-base",BASE,sha)!=BASE:
        raise ValueError("G126_SHA_ANCHOR_INVALID")
    if set(git("diff","--name-only",BASE,sha).splitlines())!={
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g126_windows_go_test_abba.py"}:
        raise ValueError("G126_UNAUTHORIZED_DIFF")
    stable(sha)
    env={**os.environ,"GOFLAGS":"-p=2","GOMAXPROCS":"2","GOMEMLIMIT":"1536MiB"}
    names=subprocess.check_output(["go","list","./..."],cwd=ROOT,
            env=env,text=True,timeout=100).splitlines()
    if not names or len(set(names))!=len(names):
        raise ValueError("G126_INVALID_GO_PACKAGE_INVENTORY")
    out=Path(os.environ["RUNNER_TEMP"])/"rar-g126-windows-go-abba.json"
    report=dict(schema="forge.rar.g126.windows-full-go-test-abba.dev.v1",
        head_sha=sha,tree=git("rev-parse","HEAD^{tree}"),base_main=BASE,
        run_id=os.environ.get("GITHUB_RUN_ID"),
        runner_name=os.environ.get("RUNNER_NAME"),processor_model=platform.processor(),
        runner_image=os.environ.get("ImageOS"),image_version=os.environ.get("ImageVersion"),
        logical_cpus=os.cpu_count(),
        go_version=subprocess.check_output(["go","version"],text=True).strip(),
        package_count=len(names),package_ids_sha256=hashlib.sha256(
            "\n".join(sorted(names)).encode()).hexdigest(),
        comparison_order=list(ORDER),goprocs=2,go_memlimit="1536MiB",
        original_go_test_vet_build_mandatory=True,
        unchanged_linux_race=True,no_default_ci_change=True,
        first_cold_and_hosted_total_unproven=True,science_proof=False,
        fixed_thresholds=dict(gain=GAIN_MIN,pair=PAIR_MIN,memory_ratio=REL_CAP,
                              absolute_memory_bytes=MEM_CAP),
        verdict="INVALID_UNVERIFIED",arms=[])
    try:
        baseline=None
        for i,mode in enumerate(ORDER,1):
            stable(sha)
            result=arm(mode,baseline)
            if sorted(result["packages"])!=sorted(names):
                raise ValueError("G126_ORIGINAL_GO_PACKAGE_SELECTION_DRIFT")
            if baseline is None:baseline=result["packages"]
            result["index"]=i
            report["arms"].append(result)
            out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        a,b,c,d=report["arms"]
        secs=[x["seconds"] for x in report["arms"]]
        pairs=[secs[0]/secs[1],secs[3]/secs[2]]
        gain=(secs[0]+secs[3])/(secs[1]+secs[2])
        mem=[b["tree_peak_commit_bytes"]/a["tree_peak_commit_bytes"],
             c["tree_peak_commit_bytes"]/d["tree_peak_commit_bytes"]]
        report.update(aggregate_gain=round(gain,6),
                      opposite_order_pair_gains=[round(x,6) for x in pairs],
                      memory_peak_ratios=[round(x,6) for x in mem])
        report["verdict"]=("PASS_DEV_ONLY" if gain>=GAIN_MIN and
            min(pairs)>=PAIR_MIN and max(mem)<=REL_CAP
            else "NO_GO_DEV")
        return 0
    except BaseException as error:
        report["failure"]=type(error).__name__+":"+str(error)[-600:]
        raise
    finally:
        out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("FORGE_RAR_G126="+report["verdict"],flush=True)

if __name__=="__main__":
    sys.exit(main())
