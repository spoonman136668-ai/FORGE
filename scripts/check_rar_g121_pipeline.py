"""RAR-G121: same-Windows-runner ABBA post-preflight Python and native pipeline.

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
BRANCH="engineering/rar-g121-samehost-fullpipeline-20261107"
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
    gate=Path(os.environ["FORGE_G121_GO"])
    deadline=time.monotonic()+30
    while not gate.is_file():
        if time.monotonic()>deadline: raise ValueError("G121_JOB_ASSIGNMENT_BARRIER_TIMEOUT")
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
        if not self.handle: raise ValueError("G121_CREATE_JOB_FAILED")
        self.high=0
    def assign(self,p):
        if not self.api.AssignProcessToJobObject(self.handle,p._handle):
            raise ValueError("G121_JOB_ASSIGNMENT_FAILED_"+str(ctypes.get_last_error()))
    def peak(self):
        info=self.Extended()
        returned=wintypes.DWORD()
        if not self.api.QueryInformationJobObject(self.handle,9,ctypes.byref(info),
                ctypes.sizeof(info),ctypes.byref(returned)):
            raise ValueError("G121_JOB_TREE_MEMORY_UNREADABLE")
        if returned.value < ctypes.sizeof(info):
            raise ValueError("G121_JOB_TREE_MEMORY_SHORT_READ")
        self.high=max(self.high,int(info.PeakJobMemoryUsed))
        return self.high
    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle=None

def arm(mode,ids,bins):
    shards=["all"] if mode=="serial" else ["0","1"]
    with tempfile.TemporaryDirectory(prefix="g121-",dir=os.environ["RUNNER_TEMP"]) as temp:
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
                    "FORGE_G121_GO":str(gate),
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
                    if tree_peak>MAX_MEMORY: raise ValueError("G121_JOB_TREE_MEMORY_CAP")
                    if time.perf_counter()-started>MAX_ARM:
                        raise ValueError("G121_ARM_TIMEOUT")
                    time.sleep(0.2)
                direct_peak=max(direct_peak,meter.sample())
                tree_peak=job.peak()
            finally:
                meter.close()
            for p in processes:
                if p.wait(timeout=15)!=0:
                    raise ValueError("G121_ORIGINAL_TESTS_FAILED")
            if direct_peak<=0 or tree_peak<=0:
                raise ValueError("G121_MEMORY_UNMEASURED")
            reports=[json.loads((root/("report"+name+".json")).read_text()) for name in shards]
            executed=[t for rep in reports for t in rep["executed_ids"]]
            if Counter(executed)!=Counter(ids) or any(
                    rep["selected_ids"]!=rep["executed_ids"] or not rep["successful"]
                    for rep in reports):
                raise ValueError("G121_CASE_PARITY_OR_ASSERTIONS_FAILED")
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


ORDER=("serial","parallel","parallel","serial")
MAX_TOTAL_SECONDS=1800

def command_run(args,env=None,timeout=420):
    started=time.perf_counter()
    completed=subprocess.run(args,cwd=ROOT,env=env,stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,encoding="utf-8",
                             errors="replace",timeout=timeout)
    if completed.returncode!=0:
        raise ValueError("G121_ORIGINAL_COMMAND_FAILED:"+repr(args)+
                         ":"+str(completed.returncode)+":"+completed.stdout[-700:])
    return round(time.perf_counter()-started,6)

def native_pipeline(index):
    with tempfile.TemporaryDirectory(prefix="g121-original-",dir=os.environ["RUNNER_TEMP"]) as d:
        t=Path(d)
        request=t/"request.json"; result=t/"result.json"; previous=t/"previous.json"
        env={**os.environ,"CGO_ENABLED":"0","GOTOOLCHAIN":"local",
             "GOFLAGS":"-p=2","GOMAXPROCS":"2","GOMEMLIMIT":"1536MiB"}
        # Exact existing Windows GenEnv + Promptbreeder and typed-program tests.
        script="set -euo pipefail\npython3 -B -m f139.check_genenv_source_integration --request > \""+str(request)+"\"\ngo run ./cmd/f139-genenv-source < \""+str(request)+"\" > \""+str(result)+"\"\npython3 -B -m f139.check_genenv_source_integration --result \""+str(result)+"\"\npython3 -B -m f139.check_prompt_source_integration --request > \""+str(request)+"\"\ngo run ./cmd/f139-genenv-source < \""+str(request)+"\" > \""+str(result)+"\"\npython3 -B -m f139.check_prompt_source_integration --result \""+str(result)+"\"\npython3 -B -m f139.check_prompt_program_integration --request > \""+str(request)+"\"\ngo run ./cmd/f139-genenv-source < \""+str(request)+"\" > \""+str(previous)+"\"\npython3 -B -m f139.check_prompt_program_integration --result \""+str(previous)+"\"\npython3 -B -m f139.check_prompt_program_integration --request --previous \""+str(previous)+"\" > \""+str(request)+"\"\ngo run ./cmd/f139-genenv-source < \""+str(request)+"\" > \""+str(result)+"\"\npython3 -B -m f139.check_prompt_program_integration --result \""+str(result)+"\" --previous \""+str(previous)+"\""
        first=command_run(["bash","-c",script],env=env,timeout=420)
        native_env={**os.environ,"GOFLAGS":"-p=2","GOMAXPROCS":"2",
                    "GOMEMLIMIT":"1536MiB"}
        t_test=command_run(["go","test","-count=1","./..."],env=native_env,timeout=420)
        t_vet=command_run(["go","vet","./..."],env=native_env,timeout=420)
        t_build=command_run(["go","build","./..."],env=native_env,timeout=420)
        return dict(genenv_original_seconds=first,go_test_seconds=t_test,
                    go_vet_seconds=t_vet,go_build_seconds=t_build)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--worker",action="store_true")
    parser.add_argument("--mode",choices=("serial","parallel"))
    parser.add_argument("--shard",choices=("all","0","1"))
    parser.add_argument("--output",type=Path)
    a=parser.parse_args()
    if a.worker:
        if not a.mode or not a.output or (a.mode=="serial" and a.shard!="all") or (
                a.mode=="parallel" and a.shard not in ("0","1")):
            raise ValueError("G121_WORKER_ARGUMENTS_INVALID")
        return child(a.mode,a.shard,a.output)
    if (os.name!="nt" or os.getenv("GITHUB_ACTIONS")!="true"
            or os.getenv("GITHUB_REPOSITORY")!="spoonman136668-ai/FORGE"
            or os.getenv("GITHUB_EVENT_NAME")!="pull_request"
            or os.getenv("GITHUB_HEAD_REF")!=BRANCH
            or not os.getenv("RUNNER_TEMP")):
        raise ValueError("G121_WINDOWS_PR_ONLY")
    sha=git("rev-parse","HEAD")
    if sha!=os.getenv("FORGE_G121_HEAD") or git("merge-base",BASE,sha)!=BASE:
        raise ValueError("G121_SHA_OR_ANCESTRY_DRIFT")
    if set(git("diff","--name-only",BASE,sha).splitlines())!={
            ".github/workflows/qualify.yml","scripts/check_rar_g121_pipeline.py"}:
        raise ValueError("G121_UNQUALIFIED_SOURCE_DIFF")
    stable(sha)
    stamp=time.perf_counter()
    report=dict(schema="forge.rar.g121.same-runner-postpreflight-abba.dev.v1",
        source_sha=sha,source_tree=git("rev-parse","HEAD^{tree}"),base_main=BASE,
        run_id=os.getenv("GITHUB_RUN_ID"),run_attempt=os.getenv("GITHUB_RUN_ATTEMPT"),
        runner_name=os.getenv("RUNNER_NAME"),
        runner_image=os.getenv("ImageOS"),image_version=os.getenv("ImageVersion"),
        processor_model=platform.processor(),logical_cpus=os.cpu_count(),
        python=sys.version,go=subprocess.check_output(["go","version"],text=True).strip(),
        order=list(ORDER),conditional_development=True,preflights_conditioned=True,
        host_fixed_for_all_arms=True,first_full_cold_claim=False,
        whole_GitHub_workflow_queue_checkout_setup_measured=False,
        Python_test_tree_peak_commit_measured=True,
        native_go_tree_memory_measured=False,
        main_ci_parallel_default_changed=False,required_original_CI_preserved=True,
        min_pipeline_aggregate_gain=1.15,min_bracket_gain=1.05,
        max_python_tree_memory_ratio=2.5,
        experiment_budget_seconds=MAX_TOTAL_SECONDS,
        verdict="UNVERIFIED_INVALID",arms=[])
    dest=Path(os.environ["RUNNER_TEMP"])/"rar-g121-samehost-abba.json"
    try:
        cases,ids=discover()
        ids_hash=hashlib.sha256("\n".join(ids).encode()).hexdigest()
        if len(ids)!=EXPECTED_CASES or ids_hash!=EXPECTED_TEST_IDS_SHA256:
            raise ValueError("G121_FROZEN_INVENTORY_DRIFT")
        bins,weights=partition(cases)
        report["case_ids_sha256"]=ids_hash
        report["module_counts"]=[len(b) for b in bins]
        report["historical_partition_weights"]=weights
        for idx,mode in enumerate(ORDER,1):
            if time.perf_counter()-stamp>MAX_TOTAL_SECONDS:
                raise ValueError("G121_EXPERIMENT_TIMEOUT")
            stable(sha)
            begin=time.perf_counter()
            measured=arm(mode,ids,bins)
            skip_hash=hashlib.sha256("\n".join(measured["skipped_ids"]).encode()).hexdigest()
            if (measured["test_count"]!=EXPECTED_CASES
                    or len(measured["skipped_ids"])!=7
                    or skip_hash!=EXPECTED_SKIP_IDS_SHA256
                    or measured["expected_failures"] or measured["unexpected_successes"]
                    or measured["errors"] or measured["failures"]
                    or not (0<measured["process_tree_peak_commit_bytes"]<=MAX_MEMORY)):
                raise ValueError("G121_TEST_PARITY_OR_TREE_MEMORY_FAILED")
            native=native_pipeline(idx)
            stable(sha)
            report["arms"].append(dict(index=idx,mode=mode,python=measured,
                native=native,pipeline_seconds=round(time.perf_counter()-begin,6)))
            dest.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        first,b,c,last=report["arms"]
        py=[a["python"]["seconds"] for a in report["arms"]]
        sec=[a["pipeline_seconds"] for a in report["arms"]]
        pair=[sec[0]/sec[1],sec[3]/sec[2]]
        gain=(sec[0]+sec[3])/(sec[1]+sec[2])
        memory=[b["python"]["process_tree_peak_commit_bytes"]/
                first["python"]["process_tree_peak_commit_bytes"],
                c["python"]["process_tree_peak_commit_bytes"]/
                last["python"]["process_tree_peak_commit_bytes"]]
        report["pipeline_pair_gain"]=[round(x,6) for x in pair]
        report["pipeline_aggregate_gain"]=round(gain,6)
        report["python_aggregate_gain"]=round((py[0]+py[3])/(py[1]+py[2]),6)
        report["python_tree_memory_ratios"]=[round(x,6) for x in memory]
        report["total_experiment_seconds"]=round(time.perf_counter()-stamp,6)
        report["verdict"]=("PASS_DEV_ONLY_POSTPREFLIGHT"
            if gain>=1.15 and min(pair)>=1.05 and max(memory)<=2.5
            else "NO_GO_DEV_POSTPREFLIGHT")
        return 0
    except BaseException as exc:
        report["failure"]=type(exc).__name__+":"+str(exc)[:500]
        raise
    finally:
        dest.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("FORGE_RAR_G121="+report["verdict"],flush=True)
        if "pipeline_aggregate_gain" in report:
            print("FORGE_RAR_G121_GAIN="+str(report["pipeline_aggregate_gain"]),flush=True)

if __name__=="__main__":
    sys.exit(main())
