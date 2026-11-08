"""RAR-G120: matched conditioned first-full serial and two-worker Windows F139 suites.

Existing mandatory CI remains completely serial and unchanged. No test is
removed or skipped by the shard selector, no source-under-test is modified.
A shadow comparison cannot authorize deployment or controller/science actions.
"""
from __future__ import annotations
import argparse
from collections import Counter
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
BASE="ca1cf30ceb651817ce6e9e1581c4ba1d3dcc7f63"
BRANCH="engineering/rar-g120-matched-firstfull-20261107"
PROFILE_SHA256="bebc42823ae0a002bd174d8a710a16ec8bc136d7c4e9509fedb1ef7c1188225f"
MIN_GAIN=1.15
MIN_PAIR=1.05
MAX_ARM=420
MAX_MEMORY=4*1024**3
MAX_REL_MEMORY=2.50
# Historical Windows profile, source pinned to run #42417473730, 1435 cases.
# Frozen weights affect module assignment only, NEVER case selection.
WEIGHTS={
"test_nci04_v30_source_transition":19.38287,
"test_nci04_original_owner_mutex":13.08060,
"test_nci04_v5_sealed_negative_succession":7.64936,
"test_nci04_g38_owner_terminal":6.91878,
"f139.test_nci04_g32_owner_custody":6.62197,
"test_nci04_g32_owner_custody":6.54054,
"test_nci04_v4_provider_recovery":6.20860,
"test_audit_d2k_custody":5.94560,
"test_nci04_prompt_program":5.36114,
"test_nci04_native_worker":4.96455,
"test_nci04_two_negative_transition":4.76948,
"test_nci04_v32_source_transition":3.64975,
"test_nci04_parent_feedback":3.35448,
"test_nci04_split_negative_owner_store":3.12513,
"test_nci04_g36_owner_integration":2.95824,
"test_reconcile_original":2.89374,
"test_nci04_g37_original_dispatch":2.87240,
"test_nci04_g52_canonical_runtime":2.86921,
"test_nci04_g47_canonical_owner_handle":2.21449,
"test_rsi_r3_disposable_tree":1.89690,
"test_local_controller":1.80746,
"test_nci04_v19_original_transition_engine":1.72470,
"test_nci04_genenv_owner_backend":1.58564,
"test_nci04_v37_source_transition":1.53369,
"test_nci04_v36_source_transition":1.52633,
"test_nci04_worker_entry":1.36113,
"test_nci04_v34_source_transition":1.30652,
"test_nci04_continuous_cadence":1.23086,
"test_nci04_worker_v3":1.17795,
"test_nci04_v19_original_owner_nowrite_probe":1.14740,
"test_nci04_v33_source_transition":1.03381,
"test_nci04_v28_source_transition":1.02948,
"test_nci04_v19_original_proposal_validation_custody":1.02008,
"test_nci04_v19_original_publication_preflight_no_write":0.97942,
"test_nci04_split_negative_owner_cli":0.97475,
}

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True,timeout=75).strip()

def stable(sha):
    if git("rev-parse","HEAD")!=sha or git("status","--porcelain","--untracked-files=all"):
        raise ValueError("G118_SOURCE_DRIFT_OR_DIRTY")

def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

def discover():
    sys.path.insert(0,str(ROOT))
    sys.path.insert(0,str(ROOT/"f139"))
    cases=list(flatten(unittest.defaultTestLoader.discover("f139",pattern="test_*.py")))
    if any(isinstance(t,unittest.loader._FailedTest) for t in cases):
        raise ValueError("G118_IMPORT_FAILURE")
    ids=[t.id() for t in cases]
    if not ids or len(ids)!=len(set(ids)):
        raise ValueError("G118_DUPLICATE_OR_EMPTY_IDS")
    return cases,ids

def partition(cases):
    counts=Counter(type(t).__module__ for t in cases)
    weights={m:WEIGHTS.get(m,max(0.08,n*0.09)) for m,n in counts.items()}
    bins=[set(),set()]
    totals=[0.0,0.0]
    for module in sorted(weights,key=lambda m:(-weights[m],m)):
        i=0 if totals[0]<=totals[1] else 1
        bins[i].add(module)
        totals[i]+=weights[module]
    if not bins[0] or not bins[1] or bins[0]&bins[1]:
        raise ValueError("G118_SHARD_PARTITION_INVALID")
    if Counter(t.id() for t in cases if type(t).__module__ in bins[0]|bins[1])!=Counter(t.id() for t in cases):
        raise ValueError("G118_DROPPED_CASE_NEGATIVE_CONTROL")
    return bins,totals

class RecordedResult(unittest.TextTestResult):
    def __init__(self,*a,**k):
        super().__init__(*a,**k)
        self.executed=[]
    def startTest(self,test):
        self.executed.append(test.id())
        super().startTest(test)

def child(mode,shard,output):
    # Workers cannot execute a test or spawn descendants before parent Job assignment.
    gate=Path(os.environ["FORGE_G120_GO"])
    deadline=time.monotonic()+30
    while not gate.is_file():
        if time.monotonic()>deadline: raise ValueError("G120_JOB_ASSIGNMENT_BARRIER_TIMEOUT")
        time.sleep(0.02)
    cases,_=discover()
    if mode=="serial" and shard!="all":
        raise ValueError("G118_SERIAL_PARTITION_INVALID")
    if mode=="parallel":
        bins,_=partition(cases)
        selected=[t for t in cases if type(t).__module__ in bins[int(shard)]]
    else:
        selected=cases
    if not selected: raise ValueError("G118_EMPTY_SHARD")
    log=io.StringIO()
    started=time.perf_counter()
    result=unittest.TextTestRunner(stream=log,verbosity=1,resultclass=RecordedResult).run(
        unittest.TestSuite(selected))
    data=dict(mode=mode,shard=shard,seconds=round(time.perf_counter()-started,6),
        selected_ids=[t.id() for t in selected],executed_ids=result.executed,
        skipped_ids=[t.id() for t,_ in result.skipped],
        expected_failures=[t.id() for t,_ in result.expectedFailures],
        unexpected_successes=[t.id() for t in result.unexpectedSuccesses],
        errors=[t.id() for t,_ in result.errors],
        failures=[t.id() for t,_ in result.failures],
        successful=result.wasSuccessful(),tests_run=result.testsRun)
    output.write_text(json.dumps(data,sort_keys=True),encoding="utf-8")
    print("FORGE_G118_CHILD="+json.dumps({k:data[k] for k in
          ("mode","shard","seconds","tests_run","successful")}),flush=True)
    if not result.wasSuccessful():
        print(log.getvalue()[-1500:],file=sys.stderr)
    return int(not result.wasSuccessful())

class WorkerMemory:
    """PSAPI read-only per-worker peak working set, NOT complete descendant RSS."""
    def __init__(self,procs):
        class Memory(ctypes.Structure):
            _fields_=[
                ("cb",wintypes.DWORD),("page_faults",wintypes.DWORD),
                ("peak_working_set",ctypes.c_size_t),("working_set",ctypes.c_size_t),
                ("peak_paged_pool",ctypes.c_size_t),("paged_pool",ctypes.c_size_t),
                ("peak_nonpaged_pool",ctypes.c_size_t),("nonpaged_pool",ctypes.c_size_t),
                ("pagefile",ctypes.c_size_t),("peak_pagefile",ctypes.c_size_t)]
        self.struct=Memory
        self.api=ctypes.WinDLL("kernel32",use_last_error=True)
        self.memapi=ctypes.WinDLL("psapi",use_last_error=True)
        self.api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        self.api.OpenProcess.restype=wintypes.HANDLE
        self.api.CloseHandle.argtypes=[wintypes.HANDLE]
        self.api.CloseHandle.restype=wintypes.BOOL
        self.memapi.GetProcessMemoryInfo.argtypes=[
            wintypes.HANDLE,ctypes.POINTER(Memory),wintypes.DWORD]
        self.memapi.GetProcessMemoryInfo.restype=wintypes.BOOL
        self.procs=procs
        self.handles=[]
        self.peaks=[0]*len(procs)
        self.high=0
        try:
            for p in procs:
                h=self.api.OpenProcess(0x0410,False,p.pid)
                if not h:raise ValueError("G118_UNREADABLE_WORKER_MEMORY")
                self.handles.append(h)
        except BaseException:
            self.close()
            raise
    def sample(self):
        total=0
        for i,(p,h) in enumerate(zip(self.procs,self.handles)):
            if p.poll() is None:
                value=self.struct()
                value.cb=ctypes.sizeof(value)
                if self.memapi.GetProcessMemoryInfo(h,ctypes.byref(value),value.cb):
                    self.peaks[i]=max(self.peaks[i],int(value.peak_working_set))
                elif p.poll() is None:
                    raise ValueError("G118_WORKER_MEMORY_COUNTER_FAILED")
            total+=self.peaks[i]
        self.high=max(self.high,total)
        return self.high
    def close(self):
        for h in self.handles:self.api.CloseHandle(h)
        self.handles=[]


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
        if not self.handle: raise ValueError("G120_CREATE_JOB_FAILED")
        self.high=0
    def assign(self,p):
        if not self.api.AssignProcessToJobObject(self.handle,p._handle):
            raise ValueError("G120_JOB_ASSIGNMENT_FAILED_"+str(ctypes.get_last_error()))
    def peak(self):
        info=self.Extended()
        returned=wintypes.DWORD()
        if not self.api.QueryInformationJobObject(self.handle,9,ctypes.byref(info),
                ctypes.sizeof(info),ctypes.byref(returned)):
            raise ValueError("G120_JOB_TREE_MEMORY_UNREADABLE")
        if returned.value < ctypes.sizeof(info):
            raise ValueError("G120_JOB_TREE_MEMORY_SHORT_READ")
        self.high=max(self.high,int(info.PeakJobMemoryUsed))
        return self.high
    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle=None

def arm(mode,ids,bins):
    shards=["all"] if mode=="serial" else ["0","1"]
    with tempfile.TemporaryDirectory(prefix="g120-",dir=os.environ["RUNNER_TEMP"]) as temp:
        root=Path(temp)
        gate=root/"assigned"
        processes=[]
        files=[]
        job=JobTreeMemory()
        started=time.perf_counter()
        direct_peak=0
        tree_peak=0
        try:
            for name in shards:
                private=root/("tmp"+name)
                private.mkdir()
                report=root/("report"+name+".json")
                log=(root/("log"+name+".txt")).open("w",encoding="utf-8")
                files.append(log)
                env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1",
                    "FORGE_G120_GO":str(gate),
                    "TEMP":str(private),"TMP":str(private),"TMPDIR":str(private)}
                p=subprocess.Popen([sys.executable,"-B",str(Path(__file__)),
                    "--worker","--mode",mode,"--shard",name,"--output",str(report)],
                    cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
                processes.append(p)
                job.assign(p)
            # Every subprocess starts test discovery only after all Job assignments.
            gate.write_text("assigned\n",encoding="utf-8")
            meter=WorkerMemory(processes)
            try:
                while any(p.poll() is None for p in processes):
                    direct_peak=meter.sample()
                    tree_peak=job.peak()
                    if tree_peak>MAX_MEMORY: raise ValueError("G120_JOB_TREE_MEMORY_CAP")
                    if time.perf_counter()-started>MAX_ARM:
                        raise ValueError("G120_ARM_TIMEOUT")
                    time.sleep(0.2)
                direct_peak=max(direct_peak,meter.sample())
                tree_peak=job.peak()
            finally:
                meter.close()
            for p in processes:
                if p.wait(timeout=15)!=0:
                    raise ValueError("G120_ORIGINAL_TESTS_FAILED")
            if direct_peak<=0 or tree_peak<=0:
                raise ValueError("G120_MEMORY_UNMEASURED")
            reports=[json.loads((root/("report"+name+".json")).read_text()) for name in shards]
            executed=[t for rep in reports for t in rep["executed_ids"]]
            if Counter(executed)!=Counter(ids) or any(
                    rep["selected_ids"]!=rep["executed_ids"] or not rep["successful"]
                    for rep in reports):
                raise ValueError("G120_CASE_PARITY_OR_ASSERTIONS_FAILED")
            return dict(mode=mode,seconds=round(time.perf_counter()-started,6),
                direct_worker_peak_workingset_bytes=direct_peak,
                process_tree_peak_commit_bytes=tree_peak,
                process_tree_memory_scope="WINDOWS_JOB_OBJECT_WITH_WORKER_BARRIER",
                test_count=len(executed),
                skipped_ids=sorted(t for rep in reports for t in rep["skipped_ids"]),
                expected_failures=sorted(t for rep in reports for t in rep["expected_failures"]),
                unexpected_successes=sorted(t for rep in reports for t in rep["unexpected_successes"]),
                errors=sorted(t for rep in reports for t in rep["errors"]),
                failures=sorted(t for rep in reports for t in rep["failures"]),
                shards=[dict(name=rep["shard"],test_count=rep["tests_run"],
                    seconds=rep["seconds"]) for rep in reports])
        except BaseException:
            for p in processes:
                if p.poll() is None:p.kill()
            for p in processes:p.wait(timeout=20)
            raise
        finally:
            for f in files:f.close()
            job.close()

EXPECTED_CASES=1443
EXPECTED_TEST_IDS_SHA256="b3fcf34229cb3a2a0eb03cfea735804cf474646a830c41875fa58b30ad4cec3b"
EXPECTED_SKIP_IDS_SHA256="2454be52b27ce0c78314b658efa2d9b5298fca718458486943462bd0ad8f111a"
# Frozen from G118 artifact 13594973914 on same F139 source.
# The original separate full serial CI suite is mandatory and runs AFTER this
# early cold-first sharded arm. No matched cold performance control claimed.

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--worker",action="store_true")
    parser.add_argument("--mode",choices=("serial","parallel"))
    parser.add_argument("--arm",choices=("serial","parallel"))
    parser.add_argument("--shard",choices=("all","0","1"))
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if args.worker:
        if not args.mode or not args.output or (
                args.mode=="serial" and args.shard!="all") or (
                args.mode=="parallel" and args.shard not in ("0","1")):
            raise ValueError("G120_WORKER_ARGUMENTS_INVALID")
        return child(args.mode,args.shard,args.output)
    if (os.name!="nt" or os.environ.get("GITHUB_ACTIONS")!="true"
            or os.environ.get("GITHUB_REPOSITORY")!="spoonman136668-ai/FORGE"
            or os.environ.get("GITHUB_EVENT_NAME")!="pull_request"
            or os.environ.get("GITHUB_HEAD_REF")!=BRANCH
            or not os.environ.get("RUNNER_TEMP") or not args.arm):
        raise ValueError("G120_WINDOWS_PR_ONLY")
    sha=git("rev-parse","HEAD")
    if sha!=os.environ.get("FORGE_G120_HEAD") or git("merge-base",BASE,sha)!=BASE:
        raise ValueError("G120_SOURCE_CUSTODY_OR_ANCESTRY_DRIFT")
    changed=set(git("diff","--name-only",BASE,sha).splitlines())
    if changed!={".github/workflows/qualify.yml",
                 "scripts/check_rar_g120_first_full.py"}:
        raise ValueError("G120_UNQUALIFIED_SOURCE_DIFF")
    tree=git("rev-parse","HEAD^{tree}")
    stable(sha)
    # Conditioned first complete F139 suite after unchanged isolation/transport preflights.
    # Two arms run on independently allocated GitHub Windows runners. They are NOT
    # equivalent to same-machine matched A/B and cannot prove default CI speedup.
    result=dict(schema="forge.rar.g120.conditioned-first-full.dev.v1",
        source_sha=sha,source_tree=tree,base_main=BASE,
        arm=args.arm,run_id=os.environ.get("GITHUB_RUN_ID"),
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
        runner_image=os.environ.get("ImageOS"),runner_image_version=os.environ.get("ImageVersion"),
        runner_arch=os.environ.get("RUNNER_ARCH"),
        processor_model=platform.processor(),
        logical_cpus=os.cpu_count(),platform=platform.platform(),
        python=sys.version,conditioned_preflights=True,
        pristine_runner_cold=False,same_machine_comparator=False,
        original_linux_and_windows_full_regression_retained=True,
        default_activation=False,whole_ci_speedup_proven=False,
        global_test_order_independent_unverified=True,
        development_verdict="INVALID_UNVERIFIED",expected_tests=EXPECTED_CASES)
    output=Path(os.environ["RUNNER_TEMP"])/("rar-g120-first-full-"+args.arm+".json")
    try:
        cases,ids=discover()
        digest=hashlib.sha256("\n".join(ids).encode()).hexdigest()
        if len(ids)!=EXPECTED_CASES or digest!=EXPECTED_TEST_IDS_SHA256:
            raise ValueError("G120_FROZEN_INVENTORY_DRIFT")
        bins,weights=partition(cases)
        result["case_ids_sha256"]=digest
        result["module_counts"]=[len(x) for x in bins]
        result["historical_partition_weights"]=weights
        measured=arm(args.arm,ids,bins)
        stable(sha)
        skip_digest=hashlib.sha256("\n".join(measured["skipped_ids"]).encode()).hexdigest()
        result["measurement"]=measured
        result["skip_ids_sha256"]=skip_digest
        if (measured["test_count"]!=EXPECTED_CASES
                or len(measured["skipped_ids"])!=7
                or skip_digest!=EXPECTED_SKIP_IDS_SHA256
                or measured["expected_failures"] or measured["unexpected_successes"]
                or measured["errors"] or measured["failures"]
                or measured["process_tree_peak_commit_bytes"]<=0
                or measured["process_tree_peak_commit_bytes"]>MAX_MEMORY):
            raise ValueError("G120_PARITY_OR_TREE_MEMORY_FAILED")
        result["development_verdict"]="PASS_CONDITIONED_FIRST_FULL_ONLY"
        return 0
    except BaseException as err:
        result["failure"]=type(err).__name__+":"+str(err)[:300]
        raise
    finally:
        output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                          encoding="utf-8")
        print("FORGE_RAR_G120_ARM="+args.arm,flush=True)
        print("FORGE_RAR_G120_VERDICT="+result["development_verdict"],flush=True)

if __name__=="__main__":
    sys.exit(main())
