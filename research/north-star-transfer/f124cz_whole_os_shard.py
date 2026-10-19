"""F124-CZ five complete Linux OS processes for each fixed model/case.

Four independent GitHub-hosted shards, each 2 sourcefree cases x 5 arms
x 5 whole OS repetitions. All natural FIT/CHECK abstentions preserved.
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
REGIMES=("nonlinear_cross_role_quadratic","modular_carry_composition")
SEEDS=(41,42,43,44)
ARMS=("frozen_affine","shared_quadratic","independent_pooled",
      "edge_quadratic","frozen_gated_recurrent")
REPS=5

def need(ok,reason):
    if not ok:raise RuntimeError("F124CZ_WHOLE_OS_"+reason)

def observe(realm,seed,arm):
    need(sys.platform=="linux","WHOLE_PROCESS_LINUX_WAIT4_REQUIRED")
    cmd=[sys.executable,"-B",str(HERE/"f124cz_outofclass_trial.py"),
         "--realm",realm,"--seed",str(seed),"--arm",arm]
    env=dict(os.environ)
    env["OPENBLAS_NUM_THREADS"]="1";env["OMP_NUM_THREADS"]="1"
    env.pop("PYTHONPATH",None)
    for name in tuple(env):
        if name.startswith(("F124CU_PRIVATE_","F124CR_PRIVATE_","F124CO_PRIVATE_")):
            env.pop(name,None)
    with tempfile.TemporaryFile(mode="w+t") as stdout,tempfile.TemporaryFile(mode="w+t") as stderr:
        process=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,text=True)
        pid,status,usage=os.wait4(process.pid,0)
        need(pid==process.pid,"EXACT_PROCESS_ID")
        code=os.waitstatus_to_exitcode(status)
        stdout.seek(0);stderr.seek(0)
        output=stdout.read();error=stderr.read()
        need(code==0,"FAIL_CLOSED_FITTED_SOURCEFREE_PROCESS_"+error[-1800:])
    row=json.loads(output)
    need((row["realm"],row["seed"],row["arm"])==(realm,seed,arm),
         "EXACT_FIXED_SOURCEFREE_CELL")
    row["whole_OS_CPU_user_sys_ns"]=round((usage.ru_utime+usage.ru_stime)*1e9)
    row["whole_OS_peak_RSS_bytes"]=usage.ru_maxrss*1024
    row["complete_python_import_fit_veto_positive_and_negative_process"]=True
    need(row["whole_OS_CPU_user_sys_ns"]>0 and row["whole_OS_peak_RSS_bytes"]>0,
         "NO_ZERO_OS_CPU_OR_RSS")
    return row

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--regime",required=True,choices=REGIMES)
    ap.add_argument("--first-seed",type=int,required=True)
    ap.add_argument("--out",required=True,type=Path)
    z=ap.parse_args()
    need(z.first_seed in (41,43) and not z.out.exists(),
         "ONLY_FOUR_FIXED_ORIGINAL_SHARDS")
    z.out.mkdir(parents=True)
    data=[]
    for seed in (z.first_seed,z.first_seed+1):
        for arm in ARMS:
            for rep in range(REPS):
                row=observe(z.regime,seed,arm)
                data.append({"repetition":rep,"original_process":row})
    need(len(data)==50,"EXACT_2_CASE_5_ARM_5_REP_ROSTER")
    shard={"schema":"mass.f124cz.sourcefree-outofclass-original-shard.v1",
          "regime":z.regime,"first_seed":z.first_seed,"processes":data,
          "full_linux_process_count":50,"scientific_originals_consumed":0,
          "private_source_oracle_in_model":False,"scientific_acceptance":False}
    filename=z.out/("shard-"+z.regime+"-"+str(z.first_seed)+".json")
    with filename.open("x") as out:
        json.dump(shard,out,sort_keys=True,indent=2);out.write("\n")
    print("F124CZ_FIVE_OS_REPEATS_PER_FROZEN_ARM_AND_CASE=PASS")
    print("F124CZ_SOURCEFREE_SHARD_50_PROCESS_RECEIPTS=PASS")
    print("F124CZ_SHARD="+z.regime+"/"+str(z.first_seed))
    print("F124CZ_SCIENTIFIC_FIRSTUSE=FALSE")

if __name__=="__main__":main()
