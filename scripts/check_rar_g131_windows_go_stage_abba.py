"""Development-only G131 full original Windows native Go stage A/B/B/A.
Same runner, same source and toolchain, cold/warm/warm/cold Go compilation cache.
Do not treat native-stage gain as whole CI acceleration or cache transfer proof.
Windows Job Objects bound worker and descendant committed memory.
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
BASE="8cf1ecc115707e186f666f7aad12de8dbdc2a88c"
BRANCH="engineering/rar-g131-windows-real-go-stage-abba-20261108"
ORDER=("A1","B1","B2","A2")
MAX_ARM=240
MEM_CAP=4*1024**3
REL_CAP=1.50
GAIN_MIN=1.10
PAIR_MIN=1.02

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,timeout=75,text=True).strip()

def stable(sha):
    if git("rev-parse","HEAD")!=sha or git("status","--porcelain","--untracked-files=all"):
        raise ValueError("G131_SOURCE_DRIFT")

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
        if not self.handle: raise ValueError("G131_CREATE_JOB_FAILED")
        self.high=0
    def assign(self,p):
        if not self.api.AssignProcessToJobObject(self.handle,p._handle):
            raise ValueError("G131_JOB_ASSIGNMENT_FAILED_"+str(ctypes.get_last_error()))
    def peak(self):
        info=self.Extended()
        returned=wintypes.DWORD()
        if not self.api.QueryInformationJobObject(self.handle,9,ctypes.byref(info),
                ctypes.sizeof(info),ctypes.byref(returned)):
            raise ValueError("G131_JOB_TREE_MEMORY_UNREADABLE")
        if returned.value < ctypes.sizeof(info):
            raise ValueError("G131_JOB_TREE_MEMORY_SHORT_READ")
        self.high=max(self.high,int(info.PeakJobMemoryUsed))
        return self.high
    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle=None



def worker(args):
    gate=Path(os.environ["FORGE_G131_GATE"])
    deadline=time.monotonic()+30
    while not gate.is_file():
        if time.monotonic()>=deadline:
            raise ValueError("G131_JOB_ASSIGN_TIMEOUT")
        time.sleep(0.02)
    output=dict(label=args.label,success=False,stages={},packages={})
    try:
        for stage,cmd in (("test",["go","test","-count=1","./..."]),
                          ("vet",["go","vet","./..."]),
                          ("build",["go","build","./..."])):
            started=time.perf_counter()
            done=subprocess.run(cmd,cwd=ROOT,env=os.environ.copy(),
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                text=True,errors="replace",timeout=MAX_ARM,check=False)
            seconds=time.perf_counter()-started
            output["stages"][stage]=dict(seconds=round(seconds,6),exit_code=done.returncode,
                 log_sha256=hashlib.sha256(done.stdout.encode()).hexdigest())
            if stage=="test":
                seen={}
                for line in done.stdout.splitlines():
                    terms=line.strip().split()
                    if len(terms)>=2 and terms[0] in ("ok","?"):
                        if terms[1] in seen:
                            raise ValueError("G131_DUPLICATE_GO_PACKAGE")
                        seen[terms[1]]="PASS" if terms[0]=="ok" else "NO_TEST_FILES"
                output["packages"]=seen
            if done.returncode:
                raise ValueError("G131_"+stage.upper()+"_FAILED:"+done.stdout[-800:])
        output["success"]=True
        output["stage_sum_seconds"]=round(sum(x["seconds"] for x in output["stages"].values()),6)
        return 0
    except BaseException as e:
        output["error"]=type(e).__name__+":"+str(e)[-800:]
        raise
    finally:
        args.output.write_text(json.dumps(output,sort_keys=True,indent=2)+"\n",encoding="utf-8")

def one_arm(label,cache,expected):
    with tempfile.TemporaryDirectory(prefix="g131-arm-",dir=os.environ["RUNNER_TEMP"]) as d:
        home=Path(d)
        gate=home/"assigned"
        output=home/"worker.json"
        meter=JobTreeMemory()
        log=(home/"worker.log").open("w",encoding="utf-8")
        proc=None
        peak=0
        start=time.perf_counter()
        try:
            private=home/"temp"
            private.mkdir()
            env={**os.environ,"GOCACHE":str(cache),"FORGE_G131_GATE":str(gate),
                 "TMP":str(private),"TEMP":str(private),"TMPDIR":str(private),
                 "PYTHONDONTWRITEBYTECODE":"1"}
            proc=subprocess.Popen([sys.executable,"-B",str(Path(__file__)),
                "--worker","--label",label,"--output",str(output)],
                cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            meter.assign(proc)
            gate.write_text("ok\n",encoding="utf-8")
            while proc.poll() is None:
                peak=max(peak,meter.peak())
                if peak>MEM_CAP:
                    raise ValueError("G131_JOB_TREE_MEMORY_CAP_EXCEEDED")
                if time.perf_counter()-start>MAX_ARM:
                    raise ValueError("G131_ARM_TIMED_OUT")
                time.sleep(0.18)
            peak=max(peak,meter.peak())
            if proc.wait(timeout=10)!=0:
                raise ValueError("G131_WORKER_FAILURE:"+
                    (output.read_text(encoding="utf-8")[-1000:]
                        if output.is_file() else "MISSING_WORKER_RECEIPT"))
            result=json.loads(output.read_text(encoding="utf-8"))
            if not result["success"] or (expected is not None and result["packages"]!=expected):
                raise ValueError("G131_GO_PACKAGE_PARITY_FAILURE")
            if not 0<peak<=MEM_CAP:
                raise ValueError("G131_JOB_OBJECT_PEAK_INVALID")
            result["job_tree_peak_commit_bytes"]=peak
            result["job_tree_scope"]="WINDOWS_JOB_OBJECT_WORKER_GO_CHILDREN"
            result["wall_seconds"]=round(time.perf_counter()-start,6)
            return result
        finally:
            if proc and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=15)
            log.close()
            meter.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--worker",action="store_true")
    ap.add_argument("--label",choices=ORDER)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    if args.worker:
        if not args.label or not args.output:
            raise ValueError("G131_WORKER_ARGS_INVALID")
        return worker(args)
    if (os.name!="nt" or os.environ.get("GITHUB_ACTIONS")!="true"
            or os.environ.get("GITHUB_REPOSITORY")!="spoonman136668-ai/FORGE"
            or os.environ.get("GITHUB_EVENT_NAME")!="pull_request"
            or os.environ.get("GITHUB_HEAD_REF")!=BRANCH
            or not os.environ.get("RUNNER_TEMP")):
        raise ValueError("G131_UNAUTHORIZED_EXECUTION_SURFACE")
    sha=git("rev-parse","HEAD")
    if sha!=os.environ.get("FORGE_G131_HEAD") or git("merge-base",BASE,sha)!=BASE:
        raise ValueError("G131_SOURCE_IDENTITY_DRIFT")
    changed=set(git("diff","--name-only",BASE,sha).splitlines())
    if changed!={".github/workflows/qualify.yml","scripts/check_rar_g131_windows_go_stage_abba.py"}:
        raise ValueError("G131_UNEXPECTED_SOURCE_DIFF")
    stable(sha)
    env={**os.environ,"GOFLAGS":"-p=2","GOMAXPROCS":"2","GOMEMLIMIT":"1536MiB"}
    if any(os.environ.get(k)!=v for k,v in
           (("GOFLAGS","-p=2"),("GOMAXPROCS","2"),("GOMEMLIMIT","1536MiB"))):
        raise ValueError("G131_ORIGINAL_GO_SETTINGS_CHANGED")
    names=subprocess.check_output(["go","list","./..."],cwd=ROOT,env=env,
        text=True,timeout=100).splitlines()
    if not names or len(names)!=len(set(names)):
        raise ValueError("G131_PACKAGE_INVENTORY_INVALID")
    package_digest=hashlib.sha256("\n".join(sorted(names)).encode()).hexdigest()
    receipt_path=Path(os.environ["RUNNER_TEMP"])/"rar-g131-windows-go-stage-abba.json"
    result=dict(schema="forge.rar-g131.windows-real-go-stage-abba.v1",
        candidate_sha=sha,tree_sha=git("rev-parse","HEAD^{tree}"),base_sha=BASE,
        go_version=subprocess.check_output(["go","version"],text=True).strip(),
        goflags=" -p=2" .strip(),gomaxprocs=2,gomemlimit="1536MiB",
        runner_name=os.environ.get("RUNNER_NAME"),
        runner_image=os.environ.get("ImageOS"),
        image_version=os.environ.get("ImageVersion"),
        processor_model=platform.processor(),cpu_count=os.cpu_count(),
        package_count=len(names),package_digest=package_digest,
        compare_order=list(ORDER),
        resource_limits=dict(memory_cap=MEM_CAP,relative_max=REL_CAP,
            aggregate_gain_min=GAIN_MIN,bracket_gain_min=PAIR_MIN),
        original_mandatory_ci_unchanged=True,full_cases_rerun_for_controlled_abba=True,
        cross_job_cache_transfer_cost_included=False,whole_job_gain_established=False,
        arms=[],verdict="UNVERIFIED")
    first=Path(os.environ["RUNNER_TEMP"])/"rar-g131-go-cache-1"
    second=Path(os.environ["RUNNER_TEMP"])/"rar-g131-go-cache-2"
    try:
        if first.exists() or second.exists():
            raise ValueError("G131_GO_CACHES_NOT_FRESH")
        expected=None
        for label in ORDER:
            stable(sha)
            target=first if label!="A2" else second
            outcome=one_arm(label,target,expected)
            if expected is None:
                expected=outcome["packages"]
            if sorted(outcome["packages"])!=sorted(names):
                raise ValueError("G131_ORIGINAL_PACKAGE_SELECTION_CHANGED")
            result["arms"].append(outcome)
            receipt_path.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
            print("G131_ARM="+label+" seconds="+str(outcome["wall_seconds"])+
                  " peak="+str(outcome["job_tree_peak_commit_bytes"]),flush=True)
        a,b,c,d=result["arms"]
        ratio1=a["wall_seconds"]/b["wall_seconds"]
        ratio2=d["wall_seconds"]/c["wall_seconds"]
        gain=(a["wall_seconds"]+d["wall_seconds"])/(b["wall_seconds"]+c["wall_seconds"])
        memory1=b["job_tree_peak_commit_bytes"]/a["job_tree_peak_commit_bytes"]
        memory2=c["job_tree_peak_commit_bytes"]/d["job_tree_peak_commit_bytes"]
        result.update(aggregate_gain=round(gain,6),
            bracket_gains=[round(ratio1,6),round(ratio2,6)],
            memory_peak_ratios=[round(memory1,6),round(memory2,6)])
        result["verdict"]=("PASS_NATIVE_STAGE_DEV_ONLY"
            if gain>=GAIN_MIN and min(ratio1,ratio2)>=PAIR_MIN
            and max(memory1,memory2)<=REL_CAP else "NO_GO_DEV")
        return 0
    except BaseException as e:
        result["verdict"]="INVALID"
        result["failure"]=type(e).__name__+":"+str(e)[-700:]
        raise
    finally:
        stable(sha)
        receipt_path.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("FORGE_RAR_G131="+result["verdict"],flush=True)

if __name__=="__main__":
    sys.exit(main())
