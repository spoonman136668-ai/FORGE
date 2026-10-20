"""F124-DG 18 full native processes per fixed sourcefree seed-pair shard.

Each of 3 arms × 3 prespecified query budgets × 2 seeds executes once in
a fresh Linux Python child. Source secrets stay in synthetic local oracle,
never imported by learners. No old original scientific artifacts touched.
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
FAMILIES=("sparse_degree4_GF2_unknown","dense_degree4_GF2_unknown")
ARMS=("meta_rank","independent_meta_rank","lex_exact_rank")
BUDGETS=(0,16,48)

def require(ok,msg):
    if not ok:raise RuntimeError("F124DG_OS_"+msg)

def measure(family,seed,arm,budget):
    require(sys.platform=="linux","NATIVE_LINUX_OS_WAIT4_REQUIRED")
    cmd=[sys.executable,"-B",str(HERE/"f124dg_budgeted_active_trial.py"),
         "--family",family,"--seed",str(seed),"--arm",arm,
         "--budget",str(budget)]
    env=dict(os.environ);env["OPENBLAS_NUM_THREADS"]="1";env["OMP_NUM_THREADS"]="1"
    env.pop("PYTHONPATH",None)
    with tempfile.TemporaryFile(mode="w+t") as out,tempfile.TemporaryFile(mode="w+t") as err:
        process=subprocess.Popen(cmd,cwd=ROOT,env=env,
                                 stdout=out,stderr=err,text=True)
        pid,status,usage=os.wait4(process.pid,0)
        require(pid==process.pid,"WHOLE_PROCESS_PID")
        code=os.waitstatus_to_exitcode(status)
        out.seek(0);err.seek(0)
        content=out.read();problem=err.read()
        require(code==0,"CHILD_FAIL_"+problem[-1700:])
    row=json.loads(content)
    require((row["family"],row["seed"],row["arm"],row["extra_oracle_budget"])
            ==(family,seed,arm,budget),"EXACT_FIXED_QUERY_ALLOCATION")
    row["full_python_OS_user_sys_CPU_ns"]=round((usage.ru_utime+usage.ru_stime)*1e9)
    row["full_python_OS_peak_RSS_bytes"]=usage.ru_maxrss*1024
    row["whole_process_includes_import_FIT_extra_oracle_CHECK_HELDOUT"]=True
    require(row["full_python_OS_user_sys_CPU_ns"]>0 and
            row["full_python_OS_peak_RSS_bytes"]>0,"COMPLETE_PROCESS_COST")
    return row

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--family",required=True,choices=FAMILIES)
    parser.add_argument("--first-seed",required=True,type=int)
    parser.add_argument("--out",required=True,type=Path)
    v=parser.parse_args()
    require(v.first_seed in (201,203) and not v.out.exists(),
            "EXACT_FOUR_INDEPENDENT_NONOVERLAPPING_SHARDS")
    v.out.mkdir(parents=True)
    cases=[measure(v.family,seed,arm,budget)
           for seed in (v.first_seed,v.first_seed+1)
           for arm in ARMS for budget in BUDGETS]
    require(len(cases)==18 and len({(r["family"],r["seed"],r["arm"],
             r["extra_oracle_budget"]) for r in cases})==18,
             "ALL_FIXED_FACTORIAL_CELLS")
    record={"schema":"mass.f124dg.original-sourcefree-active-18-os-process-shard.v1",
            "family":v.family,"first_seed":v.first_seed,"measurements":cases,
            "whole_OS_processes":18,
            "original_scientific_firstuse_consumed":0,
            "science_accepted":False}
    (v.out/("shard-"+v.family+"-"+str(v.first_seed)+".json")).write_text(
          json.dumps(record,sort_keys=True,indent=2)+"\n")
    print("F124DG_SOURCEFREE_COMPLETE_PROCESS_SHARD=PASS")
    print("F124DG_COMPLETE_OS_CHILD_PROCESSES=18")
    print("F124DG_SCIENTIFIC_FIRSTUSE_CONSUMED=0")

if __name__=="__main__":main()
