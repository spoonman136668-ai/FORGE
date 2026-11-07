"""RAR-G118: bounded development-only Windows 2-worker F139 full-suite A/B/B/A.

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
BASE="b2ee4d4f1e7d105b01c7f82b12e76353a8b43dd0"
BRANCH="engineering/rar-g118-windows-shards-dev-20261107"
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

def arm(mode,index,ids,bins):
    shards=["all"] if mode=="serial" else ["0","1"]
    with tempfile.TemporaryDirectory(prefix="g118-",dir=os.environ["RUNNER_TEMP"]) as temp:
        root=Path(temp)
        processes=[]
        files=[]
        start=time.perf_counter()
        for name in shards:
            private=root/("tmp"+name)
            private.mkdir()
            report=root/("report"+name+".json")
            log=(root/("log"+name+".txt")).open("w",encoding="utf-8")
            files.append(log)
            env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1",
                 "TEMP":str(private),"TMP":str(private),"TMPDIR":str(private)}
            p=subprocess.Popen([sys.executable,"-B",str(Path(__file__)),
                "--worker","--mode",mode,"--shard",name,"--output",str(report)],
                cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            processes.append(p)
        peak=0
        try:
            meter=WorkerMemory(processes)
            try:
                while any(p.poll() is None for p in processes):
                    peak=meter.sample()
                    if peak>MAX_MEMORY:raise ValueError("G118_WORKER_MEMORY_CAP")
                    if time.perf_counter()-start>MAX_ARM:
                        raise ValueError("G118_ARM_TIMEOUT")
                    time.sleep(0.2)
            finally:
                meter.close()
            for p in processes:
                if p.wait(timeout=15)!=0:
                    raise ValueError("G118_CHILD_SUITE_FAILED")
        except BaseException:
            for p in processes:
                if p.poll() is None:p.kill()
            for p in processes:p.wait(timeout=20)
            raise
        finally:
            for f in files:f.close()
        if peak<=0:raise ValueError("G118_MEMORY_UNMEASURED")
        reports=[json.loads((root/("report"+name+".json")).read_text()) for name in shards]
        executed=[v for rep in reports for v in rep["executed_ids"]]
        if Counter(executed)!=Counter(ids) or any(
                rep["selected_ids"]!=rep["executed_ids"] or not rep["successful"]
                for rep in reports):
            raise ValueError("G118_MISSING_REORDERED_OR_FAILED_TEST")
        if mode=="parallel" and len(bins[0]|bins[1])==0:
            raise ValueError("G118_MODULES_MISSING")
        return dict(index=index,mode=mode,seconds=round(time.perf_counter()-start,6),
            peak_worker_workingset_bytes=peak,test_count=len(executed),
            skipped_ids=sorted(x for rep in reports for x in rep["skipped_ids"]),
            expected_failures=sorted(x for rep in reports for x in rep["expected_failures"]),
            unexpected_successes=sorted(x for rep in reports for x in rep["unexpected_successes"]),
            shards=[dict(name=rep["shard"],test_count=rep["tests_run"],
                         seconds=rep["seconds"]) for rep in reports])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--worker",action="store_true")
    ap.add_argument("--mode",choices=("serial","parallel"))
    ap.add_argument("--shard",choices=("all","0","1"))
    ap.add_argument("--output",type=Path)
    opts=ap.parse_args()
    if opts.worker:
        if not opts.mode or not opts.shard or not opts.output:
            raise ValueError("G118_MISSING_CHILD_PARAMETERS")
        return child(opts.mode,opts.shard,opts.output)
    if (os.name!="nt" or os.environ.get("GITHUB_ACTIONS")!="true"
            or os.environ.get("GITHUB_REPOSITORY")!="spoonman136668-ai/FORGE"
            or os.environ.get("GITHUB_EVENT_NAME")!="pull_request"
            or os.environ.get("GITHUB_HEAD_REF")!=BRANCH):
        raise ValueError("G118_WINDOWS_DEV_CI_ONLY")
    sha=git("rev-parse","HEAD")
    if sha!=os.environ.get("FORGE_G118_HEAD") or git("merge-base",BASE,sha)!=BASE:
        raise ValueError("G118_EXACT_SOURCE_OR_ANCESTRY_DRIFT")
    changed=set(git("diff","--name-only",BASE,sha).splitlines())
    if changed!={".github/workflows/qualify.yml",
                 "scripts/check_rar_g118_shard_dev.py"}:
        raise ValueError("G118_TEST_SOURCE_OR_SCOPE_DRIFT")
    tree=git("rev-parse","HEAD^{tree}")
    stable(sha)
    cases,ids=discover()
    bins,weights=partition(cases)
    report=dict(schema="forge.rar.g118.windows-two-shard.abba.dev.v1",
        source_sha=sha,source_tree=tree,base_main=BASE,profile_zip_sha256=PROFILE_SHA256,
        platform=platform.platform(),python=sys.version,
        run_id=os.environ.get("GITHUB_RUN_ID"),run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
        tests_expected=len(ids),test_ids_sha256=hashlib.sha256("\n".join(ids).encode()).hexdigest(),
        shard_module_counts=[len(x) for x in bins],historical_shard_weights_seconds=weights,
        full_serial_ci_retained=True,sharded_global_order_changed=True,
        original_test_selection_reduced=False,
        limits=dict(min_aggregate=MIN_GAIN,min_pair=MIN_PAIR,
                    max_memory=MAX_MEMORY,max_memory_pair_ratio=MAX_REL_MEMORY),
        memory_scope="DIRECT_WORKER_PEAK_WORKING_SET_NOT_DESCENDANT_RSS",
        science_pass=False,whole_ci_speedup_proven=False,default_ci_activation=False,
        development_verdict="UNVERIFIED_INVALID",arms=[])
    dest=Path(os.environ["RUNNER_TEMP"])/"rar-g118-abba.json"
    try:
        for index,mode in enumerate(("serial","parallel","parallel","serial"),1):
            stable(sha)
            report["arms"].append(arm(mode,index,ids,bins))
        stable(sha)
        if (len({tuple(a["skipped_ids"]) for a in report["arms"]})!=1
                or len({tuple(a["expected_failures"]) for a in report["arms"]})!=1
                or any(a["unexpected_successes"] for a in report["arms"])):
            raise ValueError("G118_NEGATIVE_CONTROL_OUTCOME_DRIFT")
        a,b,c,d=report["arms"]
        pairs=[a["seconds"]/b["seconds"],d["seconds"]/c["seconds"]]
        agg=(a["seconds"]+d["seconds"])/(b["seconds"]+c["seconds"])
        mr=[b["peak_worker_workingset_bytes"]/a["peak_worker_workingset_bytes"],
            c["peak_worker_workingset_bytes"]/d["peak_worker_workingset_bytes"]]
        report["pair_speedups"]=[round(x,6) for x in pairs]
        report["aggregate_speedup"]=round(agg,6)
        report["memory_ratios"]=[round(x,6) for x in mr]
        report["development_verdict"]=(
            "PASS_DEV_ONLY" if agg>=MIN_GAIN and min(pairs)>=MIN_PAIR
            and max(mr)<=MAX_REL_MEMORY else "NO_GO")
    except BaseException as e:
        report["failure_code"]=str(e)[:300]
        raise
    finally:
        dest.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("FORGE_RAR_G118="+report["development_verdict"],flush=True)
        if "aggregate_speedup" in report:
            print("FORGE_RAR_G118_GAIN="+str(report["aggregate_speedup"]),flush=True)
    return 0

if __name__=="__main__":
    sys.exit(main())
