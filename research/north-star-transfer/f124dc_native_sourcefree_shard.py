"""F124-DC native CPU/RSS for 24 genuine source-free whole-process trials/shard.

All OS children include Python startup/import, binary meta-task induction,
novel FIT, CHECK veto and untouched positive/negative full rollouts.
Three repeats per (family, seed, arm), no science original/holdout access.
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
FAMILIES=("ternary-majority-unseen","ternary-selector-unseen","quartic-fourway-unseen")
SEEDS=(71,72,73,74)
ARMS=("meta_NAND_constructor","equally_meta_trained_ANF_peer",
      "same_compute_no_meta_gate_ablation","prior_F124DA_two_input_lexicon")
REPS=3

def need(ok,msg):
    if not ok:raise RuntimeError("F124DC_OS_"+msg)

def observe(family,seed,arm):
    need(sys.platform=="linux","REQUIRE_GITHUB_LINUX_WAIT4")
    env=dict(os.environ);env["OPENBLAS_NUM_THREADS"]="1"
    env["OMP_NUM_THREADS"]="1";env.pop("PYTHONPATH",None)
    for key in tuple(env):
        if key.startswith(("F124CO_PRIVATE_","F124CU_PRIVATE_","F124CR_PRIVATE_","F124DA_PRIVATE_")):
            env.pop(key,None)
    cmd=[sys.executable,"-B",str(HERE/"f124dc_primitive_trial.py"),
         "--family",family,"--seed",str(seed),"--arm",arm]
    with tempfile.TemporaryFile(mode="w+t") as stdout,tempfile.TemporaryFile(mode="w+t") as stderr:
        proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,text=True)
        pid,status,usage=os.wait4(proc.pid,0)
        need(pid==proc.pid,"COMPLETE_PROCESS_ID")
        code=os.waitstatus_to_exitcode(status)
        stdout.seek(0);stderr.seek(0)
        out=stdout.read();error=stderr.read()
        need(code==0,"REAL_PROCESS_FAILED_"+error[-2200:])
    row=json.loads(out)
    need((row["family"],row["seed"],row["arm"])==(family,seed,arm),
         "FROZEN_CASE_AND_ARM_NOT_MATCHED")
    row["complete_OS_user_plus_system_CPU_ns"]=int(round((usage.ru_utime+usage.ru_stime)*1e9))
    row["complete_OS_peak_RSS_bytes"]=int(usage.ru_maxrss*1024)
    row["whole_python_import_meta_fit_veto_heldout_process"]=True
    need(row["complete_OS_user_plus_system_CPU_ns"]>0 and
         row["complete_OS_peak_RSS_bytes"]>0,"NATIVE_CPU_RSS_NOT_MEASURED")
    return row

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=FAMILIES,required=True)
    p.add_argument("--seed-start",type=int,required=True)
    p.add_argument("--out",type=Path,required=True)
    x=p.parse_args()
    need(x.seed_start in (71,73) and not x.out.exists(),
         "EXACT_SIX_NONOVERLAPPING_ORIGINAL_SHARDS")
    x.out.mkdir(parents=True)
    data=[]
    for seed in (x.seed_start,x.seed_start+1):
        for arm in ARMS:
            for rep in range(REPS):
                data.append({"rep":rep,"row":observe(x.family,seed,arm)})
    need(len(data)==24,"TWENTY_FOUR_WHOLE_NATIVE_PROCESSES")
    record={"schema":"mass.f124dc.sourcefree-original-24-process-shard.v1",
            "family":x.family,"seed_start":x.seed_start,"original_os_samples":data,
            "whole_linux_processes":24,
            "scientific_original_firstuse_consumed":0,"science_accepted":False}
    name=x.out/("shard-"+x.family+"-"+str(x.seed_start)+".json")
    with name.open("x") as f:
        json.dump(record,f,sort_keys=True,indent=2);f.write("\n")
    print("F124DC_ORIGINAL_SOURCEFREE_NATIVE_SHARD=PASS")
    print("F124DC_COMPLETE_PROCESS_COUNT=24")
    print("F124DC_SCIENTIFIC_FIRSTUSE=0")

if __name__=="__main__":main()
