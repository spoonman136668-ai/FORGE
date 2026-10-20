"""F124-DA five full Linux OS measurements per fixed causal program arm.

Each four-way hosted shard runs TWO preregistered cases x FOUR independently
trained arms x FIVE repetitions = 40 separate whole Python processes.
No scientifically consumed sources, no private program/oracle in learner.
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
FAMILIES=("heldout_two_stage_arithmetic_programs","out_of_primitive_class_multiplicative_carry")
ARMS=("shared_program","independent_pooled","edge_program","frozen_gated_recurrent")
REPS=5

def need(ok,msg):
    if not ok:raise RuntimeError("F124DA_OS_"+msg)

def measure(family,seed,arm):
    need(sys.platform=="linux","WHOLE_LINUX_WAIT4_ONLY")
    env=dict(os.environ);env["OPENBLAS_NUM_THREADS"]="1";env["OMP_NUM_THREADS"]="1"
    env.pop("PYTHONPATH",None)
    for key in list(env):
        if key.startswith(("F124CO_PRIVATE_","F124CU_PRIVATE_","F124CZ_PRIVATE_")):
            env.pop(key)
    command=[sys.executable,"-B",str(HERE/"f124da_program_trial.py"),
        "--family",family,"--seed",str(seed),"--arm",arm]
    with tempfile.TemporaryFile(mode="w+t") as out,tempfile.TemporaryFile(mode="w+t") as err:
        worker=subprocess.Popen(command,cwd=ROOT,env=env,stdout=out,stderr=err,text=True)
        pid,status,usage=os.wait4(worker.pid,0)
        need(pid==worker.pid,"EXACT_NATIVE_PID")
        code=os.waitstatus_to_exitcode(status)
        out.seek(0);err.seek(0)
        payload=out.read();errors=err.read()
        need(code==0,"CHILD_FAILED_"+errors[-1200:])
    result=json.loads(payload)
    need((result["family"],result["seed"],result["arm"])==(family,seed,arm),
         "FROZEN_CASE_ARM_IDENTITY")
    result["whole_OS_CPU_user_and_sys_ns"]=round((usage.ru_utime+usage.ru_stime)*1e9)
    result["whole_OS_peak_RSS_bytes"]=usage.ru_maxrss*1024
    result["full_process_includes_start_import_FIT_CHECK_HELDOUT"]=True
    need(result["whole_OS_CPU_user_and_sys_ns"]>0 and result["whole_OS_peak_RSS_bytes"]>0,
         "NONZERO_NATIVE_MEASUREMENT")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",required=True,choices=FAMILIES)
    p.add_argument("--first-seed",required=True,type=int)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    need(a.first_seed in (51,53) and not a.out.exists(),"FOUR_PREREGISTERED_NONSELECTIVE_SHARDS")
    a.out.mkdir(parents=True)
    sample=[]
    for seed in (a.first_seed,a.first_seed+1):
        for arm in ARMS:
            for repetition in range(REPS):
                row=measure(a.family,seed,arm)
                sample.append({"rep":repetition,"original_process":row})
    need(len(sample)==40,"EXACT_FOURTY_FULL_OS_PROCESSES")
    packet={"schema":"mass.f124da.original-sourcefree-40-process-shard.v1",
        "family":a.family,"first_seed":a.first_seed,
        "whole_OS_process_count":40,"samples":sample,
        "new_original_scientific_sources_consumed":0,
        "protected_source_opened":False,"scientific_acceptance":False}
    file=a.out/("shard-"+a.family+"-"+str(a.first_seed)+".json")
    with file.open("x") as f:json.dump(packet,f,sort_keys=True,indent=2);f.write("\n")
    print("F124DA_FROZEN_SHARD="+a.family+"/"+str(a.first_seed))
    print("F124DA_ORIGINAL_WHOLE_OS_RECEIPTS=40")
    print("F124DA_SCIENCE_FIRSTUSE_CONSUMED=0")

if __name__=="__main__":main()
