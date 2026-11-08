"""G133 DEV: real full F139 regression A/B/B/A with and without exact-byte AST memoization.

Original all-case unittest suite each arm; normal tests stay mandatory on Linux
and Windows. A=original uncached normalization, B=exact-byte cache; separate
Python processes on the same Windows runner, identical source SHA/tree and
full package/test inventory, bounded process-tree memory. No science execution.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
BASE="8cf1ecc115707e186f666f7aad12de8dbdc2a88c"
BRANCH="engineering/rar-g133-exact-byte-ast-cache-20261108"
ORDER=("A1","B1","B2","A2")
MAX_ARM=360
MEM_CAP=4*1024**3
REL_CAP=1.50
GAIN_MIN=1.03
PAIR_MIN=1.005

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,timeout=80,text=True).strip()

def stable(sha):
    if git("rev-parse","HEAD")!=sha or git("status","--porcelain","--untracked-files=all"):
        raise ValueError("G133_SOURCE_DRIFT")

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
        if not self.handle: raise ValueError("G133_CREATE_JOB_FAILED")
        self.high=0
    def assign(self,p):
        if not self.api.AssignProcessToJobObject(self.handle,p._handle):
            raise ValueError("G133_JOB_ASSIGNMENT_FAILED_"+str(ctypes.get_last_error()))
    def peak(self):
        info=self.Extended()
        returned=wintypes.DWORD()
        if not self.api.QueryInformationJobObject(self.handle,9,ctypes.byref(info),
                ctypes.sizeof(info),ctypes.byref(returned)):
            raise ValueError("G133_JOB_TREE_MEMORY_UNREADABLE")
        if returned.value < ctypes.sizeof(info):
            raise ValueError("G133_JOB_TREE_MEMORY_SHORT_READ")
        self.high=max(self.high,int(info.PeakJobMemoryUsed))
        return self.high
    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle=None



def case_ids(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from case_ids(test)
        else:
            yield test.id()


def worker(args):
    gate=Path(os.environ["G133_GATE"])
    deadline=time.monotonic()+30
    while not gate.is_file():
        if time.monotonic()>deadline:
            raise ValueError("G133_JOB_ASSIGN_TIMEOUT")
        time.sleep(0.02)
    out=dict(mode=args.mode,successful=False)
    try:
        os.chdir(ROOT)
        from f139 import nci04_model_free_search as search
        # Replace ONLY the pure normalization function for original-control arms,
        # before importing the unchanged test modules and their callers.
        if args.mode=="A":
            search.normalized=search._normalized_uncached
        else:
            search._normalized_exact_bytes.cache_clear()
        start=time.perf_counter()
        loader=unittest.TestLoader()
        suite=loader.discover(start_dir="f139",pattern="test_*.py")
        ids=sorted(case_ids(suite))
        expected_cases=len(ids)
        if expected_cases<1443 or expected_cases!=len(set(ids)):
            raise ValueError("G133_TEST_INVENTORY_INVALID")
        stream=io.StringIO()
        outcome=unittest.TextTestRunner(stream=stream,verbosity=1).run(suite)
        duration=time.perf_counter()-start
        text=stream.getvalue()
        out.update(test_count=outcome.testsRun,
                   expected_count=expected_cases,
                   test_identity_sha256=hashlib.sha256("\n".join(ids).encode()).hexdigest(),
                   full_suite_wall_seconds=round(duration,6),
                   failures_count=len(outcome.failures),
                   errors_count=len(outcome.errors),
                   unexpected_success_count=len(outcome.unexpectedSuccesses),
                   skipped_count=len(outcome.skipped),
                   test_log_sha256=hashlib.sha256(text.encode()).hexdigest(),
                   cache_stats=(search._normalized_exact_bytes.cache_info()._asdict()
                                if args.mode=="B" else None),
                   successful=outcome.wasSuccessful() and outcome.testsRun==expected_cases)
        if not out["successful"]:
            out["tail"]=text[-1800:]
            raise ValueError("G133_FULL_UNITTEST_FAILED")
        return 0
    except BaseException as e:
        out["error"]=type(e).__name__+":"+str(e)[-1100:]
        raise
    finally:
        args.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n",
                               encoding="utf-8")


def run_arm(label,sha,prior):
    with tempfile.TemporaryDirectory(prefix="g133-python-arm-",dir=os.environ["RUNNER_TEMP"]) as d:
        home=Path(d)
        gate=home/"assigned"
        output=home/"worker.json"
        log=(home/"log.txt").open("w",encoding="utf-8")
        meter=JobTreeMemory()
        proc=None
        peak=0
        start=time.perf_counter()
        mode=label[0]
        try:
            tmp=home/"scratch"
            tmp.mkdir()
            env={**os.environ,"G133_GATE":str(gate),
                 "TEMP":str(tmp),"TMP":str(tmp),"TMPDIR":str(tmp),
                 "PYTHONDONTWRITEBYTECODE":"1"}
            proc=subprocess.Popen([sys.executable,"-B",str(Path(__file__)),
                "--worker","--mode",mode,"--output",str(output)],
                cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            meter.assign(proc)
            gate.write_text("ok\n",encoding="utf-8")
            while proc.poll() is None:
                peak=max(peak,meter.peak())
                if peak>MEM_CAP:
                    raise ValueError("G133_PROCESS_TREE_MEMORY_LIMIT")
                if time.perf_counter()-start>MAX_ARM:
                    raise ValueError("G133_FULL_SUITE_TIMEOUT")
                time.sleep(0.20)
            peak=max(peak,meter.peak())
            if proc.wait(timeout=10):
                raise ValueError("G133_WORKER_FAILED:"+
                    (output.read_text(encoding="utf-8")[-1500:]
                        if output.is_file() else "MISSING_RECEIPT"))
            report=json.loads(output.read_text(encoding="utf-8"))
            if not report["successful"]:
                raise ValueError("G133_FAILED_SUITE")
            if prior and (report["test_identity_sha256"]!=prior["test_identity_sha256"]
                          or report["test_count"]!=prior["test_count"]
                          or report["skipped_count"]!=prior["skipped_count"]):
                raise ValueError("G133_FULL_SUITE_IDENTITY_PARITY_FAILED")
            if not 0<peak<=MEM_CAP:
                raise ValueError("G133_PROCESS_TREE_MEMORY_NOT_MEASURED")
            report.update(index=ORDER.index(label)+1,label=label,
                process_tree_peak_commit_bytes=peak,
                process_tree_scope="WINDOWS_JOB_OBJECT_FULL_PYTHON_TEST_SUITE_AND_DESCENDANTS",
                measured_wall_seconds=round(time.perf_counter()-start,6))
            stable(sha)
            return report
        except BaseException:
            if proc and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=15)
            raise
        finally:
            log.close()
            meter.close()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--mode",choices=("A","B"))
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    if args.worker:
        if not args.mode or not args.output:
            raise ValueError("G133_WORKER_PARAMETERS_INVALID")
        return worker(args)
    if (os.name!="nt" or os.environ.get("GITHUB_ACTIONS")!="true"
            or os.environ.get("GITHUB_REPOSITORY")!="spoonman136668-ai/FORGE"
            or os.environ.get("GITHUB_EVENT_NAME")!="pull_request"
            or os.environ.get("GITHUB_HEAD_REF")!=BRANCH
            or not os.environ.get("RUNNER_TEMP")):
        raise ValueError("G133_RUNNER_BOUNDARY_INVALID")
    sha=git("rev-parse","HEAD")
    if sha!=os.environ.get("FORGE_G133_HEAD") or git("merge-base",BASE,sha)!=BASE:
        raise ValueError("G133_SHA_ANCHOR_INVALID")
    changed=set(git("diff","--name-only",BASE,sha).splitlines())
    if changed!={".github/workflows/qualify.yml",
                "f139/nci04_model_free_search.py",
                "f139/test_nci04_normalized_cache.py",
                "scripts/check_rar_g133_f139_suite_abba.py"}:
        raise ValueError("G133_UNAUTHORIZED_DIFF")
    stable(sha)
    report_path=Path(os.environ["RUNNER_TEMP"])/"rar-g133-f139-suite-abba.json"
    report=dict(schema="forge.rar-g133.full-f139-regression-abba.v1",
        source_sha=sha,tree_sha=git("rev-parse","HEAD^{tree}"),baseline_sha=BASE,
        runner_image=os.environ.get("ImageOS"),image_version=os.environ.get("ImageVersion"),
        runner_name=os.environ.get("RUNNER_NAME"),
        runner_os=os.environ.get("RUNNER_OS"),
        processor_model=platform.processor(),cpus=os.cpu_count(),
        python_version=platform.python_version(),python_executable=sys.executable,
        order=list(ORDER),treatment="in-process exact raw bytes lru64 only",
        control="original _normalized_uncached pure AST normalizer",
        original_full_suite_each_arm=True,negative_controls_preserved=True,
        cache_limit_entries=64,source_bytes_limit=256000,
        fixed_thresholds=dict(aggregate_gain=GAIN_MIN,pair_gain=PAIR_MIN,
            relative_peak_memory=REL_CAP,absolute_peak_bytes=MEM_CAP),
        original_mandatory_linux_and_windows_tests_unchanged=True,
        whole_CI_workflow_speedup_proven=False,
        performance_verdict="UNVERIFIED",arms=[])
    try:
        expected=None
        for label in ORDER:
            stable(sha)
            arm=run_arm(label,sha,expected)
            if expected is None:
                expected=arm
            report["arms"].append(arm)
            report_path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                                   encoding="utf-8")
            print("G133_ARM="+label+" suite_cases="+str(arm["test_count"])+
                  " seconds="+str(arm["measured_wall_seconds"])+
                  " peak_commit="+str(arm["process_tree_peak_commit_bytes"]),flush=True)
        a,b,c,d=report["arms"]
        time1=a["measured_wall_seconds"]/b["measured_wall_seconds"]
        time2=d["measured_wall_seconds"]/c["measured_wall_seconds"]
        aggregate=(a["measured_wall_seconds"]+d["measured_wall_seconds"])/(
                    b["measured_wall_seconds"]+c["measured_wall_seconds"])
        mem1=b["process_tree_peak_commit_bytes"]/a["process_tree_peak_commit_bytes"]
        mem2=c["process_tree_peak_commit_bytes"]/d["process_tree_peak_commit_bytes"]
        report.update(aggregate_gain=round(aggregate,6),
            paired_gains=[round(time1,6),round(time2,6)],
            paired_memory_ratios=[round(mem1,6),round(mem2,6)],
            gross_seconds_saved_per_suite=round(
                (a["measured_wall_seconds"]+d["measured_wall_seconds"]
                 -b["measured_wall_seconds"]-c["measured_wall_seconds"])/2,6))
        report["performance_verdict"]=(
            "PASS_FULL_F139_DEV_ONLY"
            if aggregate>=GAIN_MIN and min(time1,time2)>=PAIR_MIN
            and max(mem1,mem2)<=REL_CAP
            else "NO_GO_DEV")
        return 0
    except BaseException as e:
        report["performance_verdict"]="INVALID"
        report["failure"]=type(e).__name__+":"+str(e)[-900:]
        raise
    finally:
        stable(sha)
        report_path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                               encoding="utf-8")
        print("FORGE_RAR_G133="+report["performance_verdict"],flush=True)


if __name__=="__main__":
    sys.exit(main())
