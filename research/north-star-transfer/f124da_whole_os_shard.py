"""F124-DA complete Linux OS evidence for source-free operator induction.

Each observed process includes startup, model import, full 24 FIT episodes,
CHECK, heldout positive & matched negatives. Five independent processes per
new sourcefree regime/seed/arm; only deterministic original predeclared cases.
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
FAMILIES=("unseen_boolean_operator_lexicon","fourbit_carry_outside_lexicon")
SEEDS=(51,52,53,54)
ARMS=("learned_lexicon","independent_equal_lexicon","edge_lexicon",
      "frozen_quadratic","frozen_gated_recurrent")
REPS=5

def need(ok,why):
    if not ok:raise RuntimeError("F124DA_OS_"+why)

def measure(family,seed,arm):
    need(sys.platform=="linux","ORIGINAL_FULL_PROCESS_LINUX_WAIT4")
    env=dict(os.environ)
    env["OPENBLAS_NUM_THREADS"]="1";env["OMP_NUM_THREADS"]="1"
    env.pop("PYTHONPATH",None)
    for name in tuple(env):
        if name.startswith(("F124CO_PRIVATE_","F124CU_PRIVATE_","F124CZ_PRIVATE_")):
            env.pop(name,None)
    cmd=[sys.executable,"-B",str(HERE/"f124da_operator_trial.py"),
         "--regime",family,"--seed",str(seed),"--arm",arm]
    with tempfile.TemporaryFile(mode="w+t") as out,tempfile.TemporaryFile(mode="w+t") as err:
        p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=out,stderr=err,text=True)
        pid,wait,usage=os.wait4(p.pid,0)
        need(pid==p.pid,"OS_PID_MATCH")
        code=os.waitstatus_to_exitcode(wait)
        out.seek(0);err.seek(0)
        payload=out.read();error=err.read()
        need(code==0,"FAIL_CLOSED_ORIGINAL_PROCESS_"+error[-1500:])
    row=json.loads(payload)
    need((row["regime"],row["seed"],row["arm"])==(family,seed,arm),
         "IMMUTABLE_MODEL_AND_SOURCE_ROSTER")
    row["whole_OS_user_sys_CPU_ns"]=round((usage.ru_utime+usage.ru_stime)*1e9)
    row["whole_OS_max_RSS_bytes"]=usage.ru_maxrss*1024
    row["OS_includes_import_FIT_CHECK_heldout"]=True
    need(row["whole_OS_user_sys_CPU_ns"]>0 and
         row["whole_OS_max_RSS_bytes"]>0,"OS_RESOURCE_NOT_MEASURED")
    return row

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",required=True,choices=FAMILIES)
    p.add_argument("--first-seed",required=True,type=int)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    need(a.first_seed in (51,53) and not a.out.exists(),
         "ORIGINAL_SHARD_ROSTER_AND_NO_OVERWRITE")
    a.out.mkdir(parents=True)
    results=[]
    for seed in (a.first_seed,a.first_seed+1):
        for arm in ARMS:
            for rep in range(REPS):
                results.append({"rep":rep,"row":measure(a.family,seed,arm)})
    need(len(results)==50,"ORIGINAL_FIFTY_INDEPENDENT_PROCESS_SAMPLES")
    record={"schema":"mass.f124da.sourcefree-one-original-shard.v1",
        "family":a.family,"first_seed":a.first_seed,
        "cases_and_arms":results,"OS_process_count":50,
        "sourcefree_only":True,"science_accepted":False,"new_firstuse":False}
    file=a.out/("shard-"+a.family+"-"+str(a.first_seed)+".json")
    with file.open("x") as out:
        json.dump(record,out,sort_keys=True,indent=2);out.write("\n")
    print("F124DA_FIFTY_COMPLETE_OS_SAMPLES=PASS")
    print("F124DA_ORIGINAL_SHARD="+a.family+"/"+str(a.first_seed))
    print("F124DA_NEW_SCIENTIFIC_FIRSTUSE=0")

if __name__=="__main__":main()
