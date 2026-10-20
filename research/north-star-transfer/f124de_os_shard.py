"""F124-DE authentic whole-Linux-process CPU/RSS samples for new synthetic cases.

Eight sourcefree nonoverlapping shards x 18 whole Linux OS processes =144;
three OS repetitions per new family/seed/model, includes imports/FIT/CHECK
and heldout. No paid inference or protected original scientific source.
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
FAMILIES=("novel-carry-nibble-add","novel-rotate-after-add",
          "fresh-bitwise-crossrole-check","three-nibble-unseen-negative")
ARMS=("sparse_crossbit_compact","independent_equal_degree4_ANF","prior_optimized_bitwise_ANF")
REPS=3
def need(ok,reason):
    if not ok:raise RuntimeError("F124DE_WHOLE_OS_"+reason)
def one(family,seed,arm):
    need(sys.platform=="linux","REAL_WAIT4_LINUX_ONLY")
    env=dict(os.environ);env.pop("PYTHONPATH",None)
    env["OPENBLAS_NUM_THREADS"]="1";env["OMP_NUM_THREADS"]="1"
    for k in tuple(env):
        if k.startswith(("F124CR_PRIVATE_","F124CO_PRIVATE_","F124CU_PRIVATE_")):env.pop(k,None)
    cmd=[sys.executable,"-B",str(HERE/"f124de_original_trial.py"),
        "--family",family,"--seed",str(seed),"--arm",arm]
    with tempfile.TemporaryFile(mode="w+t") as output,tempfile.TemporaryFile(mode="w+t") as error:
        p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=output,stderr=error,text=True)
        pid,status,usage=os.wait4(p.pid,0)
        need(pid==p.pid,"EXACT_ORIGINAL_PROCESS_ID")
        code=os.waitstatus_to_exitcode(status)
        output.seek(0);error.seek(0)
        stdout=output.read();stderr=error.read()
        need(code==0,"SOURCEFREE_FIT_OR_NATIVE_PROCESS_FAILED_"+stderr[-1200:])
    row=json.loads(stdout)
    need((row["family"],row["seed"],row["arm"])==(family,seed,arm),
         "FROZEN_ORIGINAL_CONDITION_ID")
    row["full_OS_CPU_user_system_ns"]=round((usage.ru_utime+usage.ru_stime)*1e9)
    row["full_OS_peak_RSS_bytes"]=usage.ru_maxrss*1024
    row["OS_includes_python_import_meta_FIT_native_compilation_CHECK_heldout"]=True
    need(row["full_OS_CPU_user_system_ns"]>0 and row["full_OS_peak_RSS_bytes"]>0,
         "NOT_A_COMPLETE_NATIVE_OS_MEASUREMENT")
    return row

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=FAMILIES,required=True)
    p.add_argument("--first-seed",type=int,required=True)
    p.add_argument("--out",type=Path,required=True)
    z=p.parse_args()
    need(z.first_seed in (91,93) and not z.out.exists(),
         "SOURCEFREE_EIGHT_NONOVERLAPPING_SHARDS")
    z.out.mkdir(parents=True)
    rows=[{"rep":rep,"row":one(z.family,seed,arm)}
         for seed in (z.first_seed,z.first_seed+1)
         for arm in ARMS for rep in range(REPS)]
    need(len(rows)==18,"ALL_EIGHTEEN_COMPLETE_OS_PROCESS_MEASUREMENTS")
    shard={"schema":"mass.f124de.original-sourcefree-18-OS-measurements.v1",
      "family":z.family,"first_seed":z.first_seed,"whole_OS_samples":rows,
      "sourcefree_original_OS_processes":18,
      "independently_birthed_scientific_sources":False,
      "science_firstuse_consumed":0,"scientific_acceptance":False}
    path=z.out/("shard-"+z.family+"-"+str(z.first_seed)+".json")
    with path.open("x") as handle:
        json.dump(shard,handle,indent=2,sort_keys=True);handle.write("\n")
    print("F124DE_EIGHTEEN_COMPLETE_SOURCEFREE_OS_PROCESSES=PASS")
    print("F124DE_SOURCEFREE_SHARD="+z.family+"/"+str(z.first_seed))
    print("F124DE_NO_ORIGINAL_SCIENTIFIC_FIRSTUSE=TRUE")
if __name__=="__main__":main()
