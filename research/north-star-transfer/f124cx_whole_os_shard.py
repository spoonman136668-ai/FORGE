"""F124-CX run an exact 16-cell SOURCE-FREE original factorial shard.

All rows are measured in separate whole Linux child processes with wait4
CPU (user + sys) and peak RSS. The model, independent trained recurrent
control, source-free synthetic regimes and test budgets were frozen before
execution. No scientific firstuse or original source tasks.
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
ARMS=("attentive","gated")

def need(ok,reason):
    if not ok:raise RuntimeError("F124CX_SHARD_"+reason)

def observe(regime,seed,hidden,epochs,arm):
    need(sys.platform=="linux","WHOLE_NATIVE_WAIT4_LINUX_REQUIRED")
    import resource
    argv=[sys.executable,"-B",str(HERE/"f124cx_factorial_cell.py"),
          "--regime",regime,"--seed",str(seed),"--hidden",str(hidden),
          "--epochs",str(epochs),"--arm",arm]
    env=dict(os.environ)
    env["OPENBLAS_NUM_THREADS"]="1"
    env["OMP_NUM_THREADS"]="1"
    env.pop("PYTHONPATH",None)
    for key in tuple(env):
        if key.startswith("F124CU_PRIVATE_") or key.startswith("F124CR_PRIVATE_"):
            del env[key]
    with tempfile.TemporaryFile(mode="w+t") as o,tempfile.TemporaryFile(mode="w+t") as e:
        proc=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=o,stderr=e,text=True)
        pid,status,usage=os.wait4(proc.pid,0)
        need(pid==proc.pid,"SINGLE_PROCESS_PID")
        ret=os.waitstatus_to_exitcode(status)
        o.seek(0);e.seek(0)
        payload=o.read();errors=e.read()
        need(ret==0,"FROZEN_CHILD_CELL_FAILED_"+errors[-2200:])
    row=json.loads(payload)
    need(row["regime"]==regime and row["seed"]==seed and
         row["hidden"]==hidden and row["epochs"]==epochs and row["arm"]==arm,
         "EXACT_ORIGINAL_FACTORIAL_CELL_ID")
    row["complete_OS_process_CPU_ns"]=round((usage.ru_utime+usage.ru_stime)*1e9)
    row["complete_OS_process_peak_RSS_bytes"]=usage.ru_maxrss*1024
    row["full_python_numpy_BPTT_and_heldout_observed"]=True
    need(row["complete_OS_process_CPU_ns"]>0 and
         row["complete_OS_process_peak_RSS_bytes"]>0,
         "NONZERO_COMPLETE_PROCESS_OS_COST")
    return row

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--regime",choices=("dense","sparse"),required=True)
    a.add_argument("--first-seed",type=int,required=True)
    a.add_argument("--out",type=Path,required=True)
    x=a.parse_args()
    need(x.first_seed in (0,2) and not x.out.exists(),
         "FROZEN_SEED_PAIR_ONE_ORIGINAL_SHARD")
    x.out.mkdir(parents=True)
    rows=[]
    for seed in (x.first_seed,x.first_seed+1):
        for h in (8,16):
            for epochs in (45,135):
                for arm in ARMS:
                    row=observe(x.regime,seed,h,epochs,arm)
                    rows.append(row)
    need(len(rows)==16 and len({(o["regime"],o["seed"],o["hidden"],
            o["epochs"],o["arm"]) for o in rows})==16,
         "COMPLETE_SHARD_NOT_SELECTED_BY_RESULTS")
    record={"schema":"mass.f124cx.sourcefree-original-16cells-shard.v1",
       "regime":x.regime,"first_seed":x.first_seed,"cells":rows,
       "native_linux_wait4_whole_os_samples":16,
       "no_scientific_source_read":True,
       "sourcefree_diagnostic_only":True,"scientific_acceptance":False}
    filename=x.out/("shard-"+x.regime+"-"+str(x.first_seed)+".json")
    with filename.open("x") as f:
        json.dump(record,f,sort_keys=True,indent=2);f.write("\n")
    print("F124CX_SOURCEFREE_FACTORIAL_SHARD_PASS="+x.regime+"/"+str(x.first_seed))
    print("F124CX_FACTORIAL_MEASURED_CELLS=16")
    print("F124CX_FIRSTUSE_SCIENTIFIC_SOURCES_USED=0")
    print("F124CX_SCIENTIFIC_ACCEPTANCE=FALSE")

if __name__=="__main__":main()
