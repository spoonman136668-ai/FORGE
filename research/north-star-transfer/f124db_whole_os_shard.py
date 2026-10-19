"""F124-DB five full Linux OS native repetitions of every fixed arm/case."""
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
FAMILIES=("nested-additive-new-graph","nested-xor-new-graph")
SEEDS=(61,62,63,64)
ARMS=("meta_constructor","equal_meta_peer","frozen_quadratic","frozen_gated_recurrent")
REPETITIONS=5

def need(ok,why):
    if not ok:raise RuntimeError("F124DB_NATIVE_"+why)

def observe(family,seed,arm):
    need(sys.platform=="linux","REAL_LINUX_WHOLE_PROCESS_WAIT4_REQUIRED")
    env=dict(os.environ)
    env["OPENBLAS_NUM_THREADS"]="1";env["OMP_NUM_THREADS"]="1"
    env.pop("PYTHONPATH",None)
    for n in tuple(env):
        if n.startswith(("F124CO_PRIVATE_","F124CU_PRIVATE_","F124CR_PRIVATE_")):
            env.pop(n,None)
    cmd=[sys.executable,"-B",str(HERE/"f124db_structural_trial.py"),
        "--family",family,"--seed",str(seed),"--arm",arm]
    with tempfile.TemporaryFile(mode="w+t") as stdout,tempfile.TemporaryFile(mode="w+t") as stderr:
        p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,text=True)
        pid,status,usage=os.wait4(p.pid,0)
        need(pid==p.pid,"REAL_CHILD_PROCESS_IDENTITY")
        result=os.waitstatus_to_exitcode(status)
        stdout.seek(0);stderr.seek(0)
        out=stdout.read();error=stderr.read()
        need(result==0,"ORIGINAL_PROCESS_FAILED_"+error[-1800:])
    row=json.loads(out)
    need((row["family"],row["seed"],row["arm"])==(family,seed,arm),
         "EXACT_FROZEN_PROCESS_IDENTITY")
    row["whole_OS_user_plus_sys_CPU_ns"]=round((usage.ru_utime+usage.ru_stime)*1e9)
    row["whole_OS_peak_RSS_bytes"]=usage.ru_maxrss*1024
    row["whole_OS_includes_Python_import_meta_FIT_CHECK_and_heldout"]=True
    need(row["whole_OS_user_plus_sys_CPU_ns"]>0 and
         row["whole_OS_peak_RSS_bytes"]>0,"MISSING_REAL_CPU_OR_RSS")
    return row

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--family",required=True,choices=FAMILIES)
    ap.add_argument("--first-seed",required=True,type=int)
    ap.add_argument("--out",required=True,type=Path)
    x=ap.parse_args()
    need(x.first_seed in (61,63) and not x.out.exists(),
         "FOUR_FROZEN_SHARDS_NO_OVERWRITE")
    x.out.mkdir(parents=True)
    results=[]
    for seed in (x.first_seed,x.first_seed+1):
        for arm in ARMS:
            for rep in range(REPETITIONS):
                results.append({"rep":rep,"measurement":observe(x.family,seed,arm)})
    need(len(results)==40,"EXACT_FORTY_FULL_PROCESS_SAMPLES")
    report={"schema":"mass.f124db.sourcefree-40-native-receipts.v1",
            "family":x.family,"first_seed":x.first_seed,
            "samples":results,"whole_OS_processes":40,
            "scientific_source_firstuse_consumed":0,
            "scientific_acceptance":False}
    name=x.out/("shard-"+x.family+"-"+str(x.first_seed)+".json")
    with name.open("x") as out:
        json.dump(report,out,sort_keys=True,indent=2);out.write("\n")
    print("F124DB_REAL_FORTY_FULL_OS_PROCESS_SHARD=PASS")
    print("F124DB_ORIGINAL_SOURCEFREE_SHARD="+x.family+"/"+str(x.first_seed))
    print("F124DB_NEW_FIRSTUSE=0")

if __name__=="__main__":main()
