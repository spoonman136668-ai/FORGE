"""F124-DD 240 full Linux OS process receipts for new sourcefree cohorts.

Each process includes Python boot/import, 12 task public meta training,
24 FIT, compiler construction, CHECK and all heldout positive/negative
rollouts. All conditions fixed preregistration before this measurement.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FAMILIES=("fresh-ternary-compiler-sanity","four-input-parity-conjunction",
          "four-input-selector-with-interaction","nibble-addition-carry-out-of-bitwise")
SEEDS=(81,82,83,84)
ARMS=("compact_meta_NAND","independent_compact_meta_ANF","slow_meta_NAND_DAG")
REPS=5

def need(ok,why):
    if not ok:raise RuntimeError("F124DD_OS_"+why)

def measure(family,seed,arm):
    need(sys.platform=="linux","REAL_LINUX_WAIT4_FULL_PROCESS_ONLY")
    cmd=[sys.executable,"-B",str(HERE/"f124dd_compact_trial.py"),
         "--family",family,"--seed",str(seed),"--arm",arm]
    env=dict(os.environ)
    env["OPENBLAS_NUM_THREADS"]="1";env["OMP_NUM_THREADS"]="1"
    env.pop("PYTHONPATH",None)
    for k in tuple(env):
        if k.startswith(("F124CR_PRIVATE_","F124CU_PRIVATE_","F124CO_PRIVATE_","F124DC_PRIVATE_")):
            env.pop(k,None)
    with tempfile.TemporaryFile(mode="w+t") as stdout,tempfile.TemporaryFile(mode="w+t") as stderr:
        p=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,cwd=ROOT,env=env,text=True)
        pid,status,osr=os.wait4(p.pid,0)
        need(pid==p.pid,"OS_PROCESS_IDENTITY")
        code=os.waitstatus_to_exitcode(status)
        stdout.seek(0);stderr.seek(0)
        payload=stdout.read();error=stderr.read()
        need(code==0,"ORIGINAL_WHOLE_PROCESS_"+error[-2000:])
    row=json.loads(payload)
    need((row["family"],row["seed"],row["arm"])==(family,seed,arm),
         "FROZEN_SOURCEFREE_CONDITION")
    row["whole_OS_CPU_user_system_ns"]=int(round((osr.ru_utime+osr.ru_stime)*1e9))
    row["whole_OS_peak_RSS_bytes"]=int(osr.ru_maxrss*1024)
    row["OS_measurement_includes_import_meta_fit_compilation_CHECK_and_heldout"]=True
    need(row["whole_OS_CPU_user_system_ns"]>0 and row["whole_OS_peak_RSS_bytes"]>0,
         "REAL_CPU_AND_RSS_REQUIRED")
    return row

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=FAMILIES,required=True)
    p.add_argument("--first-seed",type=int,required=True)
    p.add_argument("--out",type=Path,required=True)
    x=p.parse_args()
    need(x.first_seed in (81,83) and not x.out.exists(),
         "EIGHT_SOURCEFREE_SHARDS_NO_OVERWRITE")
    x.out.mkdir(parents=True)
    data=[]
    for seed in (x.first_seed,x.first_seed+1):
        for arm in ARMS:
            for repeat in range(REPS):
                data.append({"repeat":repeat,"original_process":measure(x.family,seed,arm)})
    need(len(data)==30,"ALL_THIRTY_NATIVE_PROCESSES")
    report={"schema":"mass.f124dd.sourcefree-original-30-process-shard.v1",
            "family":x.family,"first_seed":x.first_seed,
            "original_measurements":data,"full_OS_processes":30,
            "authentic_scientific_firstuse_consumed":0,
            "external_independent_source_origin":False,"scientific_success":False}
    name=x.out/("shard-"+x.family+"-"+str(x.first_seed)+".json")
    with name.open("x") as f:
        json.dump(report,f,sort_keys=True,indent=2);f.write("\n")
    print("F124DD_ORIGINAL_THIRTY_FULL_OS_SOURCEFREE_PROCESSES=PASS")
    print("F124DD_OS_SHARD="+x.family+"/"+str(x.first_seed))
    print("F124DD_ORIGINAL_SCIENTIFIC_FIRSTUSE=0")

if __name__=="__main__":main()
