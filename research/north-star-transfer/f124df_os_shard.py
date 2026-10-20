"""F124-DF original 96 full-Linux-process fresh sourcefree forensic trials.

Each subprocess includes Python startup, frozen FIT trained model, CHECK
veto, untouched heldout, exact 163-monomial fit rank and explicit FIT
nullspace. Source-only oracle exposed AFTER all public-model scoring.
Original scientific first-use remains zero, no owner workstation.
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
FAMILIES=("rotated-modular-add-unfamiliar","rotated-modular-add-role-switch",
          "plain-modular-add-control","three-register-arithmetic-out-of-class")
ARMS=("frozen_sparse_crossbit","frozen_equal_full_ANF")
REPS=3
def need(ok,why):
    if not ok:raise RuntimeError("F124DF_OS_"+why)
def run(family,seed,arm):
    need(sys.platform=="linux","TRUE_LINUX_WAIT4_REQUIRED")
    env=dict(os.environ)
    env.pop("PYTHONPATH",None)
    env["OPENBLAS_NUM_THREADS"]="1"
    env["OMP_NUM_THREADS"]="1"
    for k in tuple(env):
        if k.startswith(("F124CR_PRIVATE_","F124CU_PRIVATE_","F124CO_PRIVATE_")):env.pop(k,None)
    cmd=[sys.executable,"-B",str(HERE/"f124df_rotation_trial.py"),
         "--family",family,"--seed",str(seed),"--arm",arm]
    with tempfile.TemporaryFile(mode="w+t") as stdout,tempfile.TemporaryFile(mode="w+t") as stderr:
        p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,text=True)
        pid,status,usage=os.wait4(p.pid,0)
        need(pid==p.pid,"EXACT_CHILD_SOURCE_IDENTITY")
        code=os.waitstatus_to_exitcode(status)
        stdout.seek(0);stderr.seek(0)
        content=stdout.read();error=stderr.read()
        need(code==0,"FROZEN_FULL_SOURCEFREE_PROCESS_FAILED_"+error[-1500:])
    record=json.loads(content)
    need((record["family"],record["seed"],record["arm"])==(family,seed,arm),
         "FROZEN_SOURCEFREE_PROCESS_ROSTER_CHANGED")
    record["OS_complete_CPU_user_system_ns"]=round((usage.ru_utime+usage.ru_stime)*1e9)
    record["OS_peak_RSS_bytes"]=usage.ru_maxrss*1024
    record["OS_includes_python_fit_check_holdout_and_postfit_identifiability"]=True
    need(record["OS_complete_CPU_user_system_ns"]>0 and record["OS_peak_RSS_bytes"]>0,
         "MISSING_COMPLETE_CPU_OR_RSS")
    return record
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=FAMILIES,required=True)
    p.add_argument("--first-seed",type=int,required=True)
    p.add_argument("--out",type=Path,required=True)
    z=p.parse_args()
    need(z.first_seed in (101,103) and not z.out.exists(),
         "ORIGINAL_EIGHT_SOURCEFREE_SHARDS_NO_OVERWRITE")
    z.out.mkdir(parents=True)
    samples=[{"repeat":rep,"measurement":run(z.family,seed,arm)}
             for seed in (z.first_seed,z.first_seed+1)
             for arm in ARMS for rep in range(REPS)]
    need(len(samples)==12,"TWELVE_EXACT_WHOLE_PROCESS_MEASUREMENTS")
    receipt={"schema":"mass.f124df.original-sourcefree-12-process-forensic-shard.v1",
       "family":z.family,"first_seed":z.first_seed,"original_samples":samples,
       "complete_hosted_OS_processes":12,
       "independent_external_sources":False,"authentic_scientific_firstuse":0,
       "scientific_acceptance":False}
    path=z.out/("shard-"+z.family+"-"+str(z.first_seed)+".json")
    with path.open("x") as output:
        json.dump(receipt,output,sort_keys=True,indent=2);output.write("\n")
    print("F124DF_TWELVE_COMPLETE_OS_SAMPLES=PASS")
    print("F124DF_ORIGINAL_SOURCEFREE_SHARD="+z.family+"/"+str(z.first_seed))
if __name__=="__main__":main()
