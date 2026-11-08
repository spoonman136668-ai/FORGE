"""RAR-G130 source-bound Windows Go cached-build verification.
Original F139, mandatory Go vet/build, original Go suite, and Linux race tests stay unchanged.
A separate branch-only job validates cross-runner restored build cache with unchanged -p=2.
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
BASE="7b4834e8255ce3dca1cf9bfea5470aa7b41f046c"
BRANCH="engineering/rar-g130-source-keyed-cache-restore-20261108"
MAX_ARM=360
MEM_CAP=4*1024**3

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,timeout=75,text=True).strip()

def stable(sha):
    if git("rev-parse","HEAD")!=sha or git("status","--porcelain","--untracked-files=all"):
        raise ValueError("G130_SOURCE_DRIFT")

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
        if not self.handle: raise ValueError("G130_CREATE_JOB_FAILED")
        self.high=0
    def assign(self,p):
        if not self.api.AssignProcessToJobObject(self.handle,p._handle):
            raise ValueError("G130_JOB_ASSIGNMENT_FAILED_"+str(ctypes.get_last_error()))
    def peak(self):
        info=self.Extended()
        returned=wintypes.DWORD()
        if not self.api.QueryInformationJobObject(self.handle,9,ctypes.byref(info),
                ctypes.sizeof(info),ctypes.byref(returned)):
            raise ValueError("G130_JOB_TREE_MEMORY_UNREADABLE")
        if returned.value < ctypes.sizeof(info):
            raise ValueError("G130_JOB_TREE_MEMORY_SHORT_READ")
        self.high=max(self.high,int(info.PeakJobMemoryUsed))
        return self.high
    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle=None



def worker(args):
    gate=Path(os.environ["FORGE_G130_GATE"])
    until=time.monotonic()+30
    while not gate.is_file():
        if time.monotonic() > until:
            raise ValueError("G130_ASSIGNMENT_TIMEOUT")
        time.sleep(0.02)
    result={"schema":"forge.rar-g130.windows-cached-go-native.v1",
            "stages":{},"packages":{},"successful":False}
    try:
        for stage,cmd in (
            ("test",["go","test","-count=1","./..."]),
            ("vet",["go","vet","./..."]),
            ("build",["go","build","./..."])):
            start=time.perf_counter()
            done=subprocess.run(cmd,cwd=ROOT,env=os.environ.copy(),
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                text=True,errors="replace",timeout=MAX_ARM,check=False)
            elapsed=time.perf_counter()-start
            result["stages"][stage]={"seconds":round(elapsed,6),"exit_code":done.returncode,
                "log_sha256":hashlib.sha256(done.stdout.encode("utf-8")).hexdigest()}
            if stage=="test":
                states={}
                for line in done.stdout.splitlines():
                    terms=line.strip().split()
                    if len(terms)>1 and terms[0] in ("ok","?"):
                        if terms[1] in states:
                            raise ValueError("G130_DUPLICATE_PACKAGE")
                        states[terms[1]]="PASS" if terms[0]=="ok" else "NO_TEST_FILES"
                result["packages"]=states
            if done.returncode:
                raise ValueError("G130_REAL_GO_"+stage.upper()+"_FAILED:"+done.stdout[-900:])
        result["successful"]=True
        return 0
    except BaseException as exc:
        result["error"]=type(exc).__name__+":"+str(exc)[-1200:]
        raise
    finally:
        args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")

def measured_run(expected):
    with tempfile.TemporaryDirectory(prefix="g130-windows-",dir=os.environ["RUNNER_TEMP"]) as d:
        home=Path(d)
        gate=home/"assigned"
        output=home/"worker.json"
        log=(home/"child.log").open("w",encoding="utf-8")
        meter=JobTreeMemory()
        proc=None
        high=0
        started=time.perf_counter()
        try:
            private=home/"tmp"
            private.mkdir()
            env={**os.environ,"FORGE_G130_GATE":str(gate),
                 "TEMP":str(private),"TMP":str(private),"TMPDIR":str(private),
                 "PYTHONDONTWRITEBYTECODE":"1"}
            proc=subprocess.Popen([sys.executable,"-B",str(Path(__file__)),
                    "--worker","--output",str(output)],cwd=ROOT,env=env,
                    stdout=log,stderr=subprocess.STDOUT)
            meter.assign(proc)
            gate.write_text("ok\n",encoding="utf-8")
            while proc.poll() is None:
                high=max(high,meter.peak())
                if high>MEM_CAP:
                    raise ValueError("G130_TREE_COMMIT_CAP_EXCEEDED")
                if time.perf_counter()-started>MAX_ARM:
                    raise ValueError("G130_ARM_TIMEOUT")
                time.sleep(0.20)
            high=max(high,meter.peak())
            if proc.wait(timeout=10):
                raise ValueError("G130_CHILD_FAILED:"+(
                    output.read_text(encoding="utf-8")[-900:]
                    if output.is_file() else "UNRECORDED"))
            result=json.loads(output.read_text(encoding="utf-8"))
            if not result["successful"] or (expected is not None and result["packages"]!=expected):
                raise ValueError("G130_REAL_FULL_PACKAGE_PARITY_FAILED")
            if not (0<high<=MEM_CAP):
                raise ValueError("G130_INVALID_JOB_TREE_PEAK")
            result["tree_peak_commit_bytes"]=high
            result["tree_scope"]="WIN_JOB_OBJECT_PYTHON_GO_AND_DESCENDANTS"
            result["total_seconds"]=round(time.perf_counter()-started,6)
            return result
        finally:
            if proc and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=15)
            log.close()
            meter.close()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--worker",action="store_true")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if args.worker:
        if args.output is None:
            raise ValueError("G130_WORKER_OUTPUT_REQUIRED")
        return worker(args)
    if (os.name!="nt" or os.environ.get("GITHUB_ACTIONS")!="true"
            or os.environ.get("GITHUB_REPOSITORY")!="spoonman136668-ai/FORGE"
            or os.environ.get("GITHUB_EVENT_NAME")!="pull_request"
            or os.environ.get("GITHUB_HEAD_REF")!=BRANCH
            or not os.environ.get("RUNNER_TEMP")
            or os.environ.get("G130_CACHE_HIT")!="true"):
        raise ValueError("G130_EXPECTED_WINDOWS_PR_EXACT_CACHE_HIT")
    sha=git("rev-parse","HEAD")
    if sha!=os.environ.get("G130_HEAD") or git("merge-base",BASE,sha)!=BASE:
        raise ValueError("G130_SHA_PIN_INVALID")
    diff=set(git("diff","--name-only",BASE,sha).splitlines())
    if diff!={".github/workflows/qualify.yml",
             "scripts/check_rar_g130_windows_cache.py"}:
        raise ValueError("G130_UNEXPECTED_SOURCE_DIFF")
    stable(sha)
    names=subprocess.check_output(["go","list","./..."],cwd=ROOT,
        env=os.environ.copy(),text=True,timeout=100).splitlines()
    if len(names)!=137 or len(set(names))!=len(names):
        raise ValueError("G130_PACKAGE_INVENTORY_CHANGED")
    identity=hashlib.sha256("\n".join(sorted(names)).encode()).hexdigest()
    if identity!="9f05d938ba62df0519abeb0c8bb5da8b0758435b84684f1a920690e2e81e12e9":
        raise ValueError("G130_PACKAGE_IDENTITY_CHANGED")
    output=Path(os.environ["RUNNER_TEMP"])/"rar-g130-windows-cache-verify.json"
    result=dict(schema="forge.rar-g130.windows-cache-verify.v1",
        source_sha=sha,source_tree=git("rev-parse","HEAD^{tree}"),base_main=BASE,
        cache_key=os.environ.get("G130_CACHE_KEY"),
        exact_cache_hit=True,source_clean=True,
        toolchain=subprocess.check_output(["go","version"],text=True).strip(),
        goflags=os.environ.get("GOFLAGS"),
        gomaxprocs=os.environ.get("GOMAXPROCS"),
        gomemlimit=os.environ.get("GOMEMLIMIT"),
        runner_os=os.environ.get("RUNNER_OS"),
        runner_arch=os.environ.get("RUNNER_ARCH"),
        runner_image=os.environ.get("ImageOS"),
        image_version=os.environ.get("ImageVersion"),
        processor_model=platform.processor(),
        cpu_count=os.cpu_count(),
        package_count=len(names),package_ids_sha256=identity,
        cache_cross_job=True,full_original_cases_executed=True,
        memory_cap_bytes=MEM_CAP,memory_relative_baseline_unverified=True,
        gain_vs_full_ci_unverified=True,
        verdict="UNVERIFIED")
    try:
        if (os.environ.get("GOMAXPROCS")!="2"
                or os.environ.get("GOFLAGS")!="-p=2"
                or os.environ.get("GOMEMLIMIT")!="1536MiB"
                or not result["cache_key"]):
            raise ValueError("G130_GO_ENVIRONMENT_DRIFT")
        # Real Go test output includes 'ok' for tested packages and '?' for packages
        # without tests. Preserve all expected package IDs; no test selection.
        run=measured_run(None)
        if sorted(run["packages"])!=sorted(names):
            raise ValueError("G130_REAL_PACKAGE_SELECTION_CHANGED")
        result["measurement"]=run
        stable(sha)
        result["verdict"]="PASS_CROSS_JOB_DEV_ONLY"
        return 0
    except BaseException as error:
        result["failure"]=type(error).__name__+":"+str(error)[-900:]
        result["verdict"]="NO_GO_DEV"
        raise
    finally:
        output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print("FORGE_RAR_G130="+result["verdict"],flush=True)

if __name__=="__main__":
    sys.exit(main())
