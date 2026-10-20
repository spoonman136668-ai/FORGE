"""F124-DI development-only single original full OS run per arm/case.

Original source-free development cases are consumed at this gate and must
not be reused as new unconsumed prospective science. CPU/RSS timing of one
whole process is exploratory; it is NOT a matched FLOP/resource proof.
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
FAMILIES=("two_register_add_carry","two_register_rotate_and_add",
          "non_arithmetic_bitwise_boolean","three_register_outside_model")
ARMS=("learned_CV_causal_prior","independent_equal_CV_peer","frozen_degree4_reference")
SEEDS=(701,702,703,704)
def require(ok,why):
    if not ok:raise RuntimeError("F124DI_DEV_OS_"+why)
def measure(family,seed,arm):
    require(sys.platform=="linux","REAL_FULL_PROCESS_LINUX_WAIT4")
    env=dict(os.environ);env.pop("PYTHONPATH",None)
    env["OPENBLAS_NUM_THREADS"]="1";env["OMP_NUM_THREADS"]="1"
    cmd=[sys.executable,"-B",str(HERE/"f124di_zero_oracle_trial.py"),
         "--family",family,"--seed",str(seed),"--arm",arm]
    with tempfile.TemporaryFile(mode="w+t") as output,tempfile.TemporaryFile(mode="w+t") as error:
        p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=output,stderr=error,text=True)
        pid,status,cost=os.wait4(p.pid,0)
        require(pid==p.pid,"CHILD_PROCESS_IDENTITY")
        ret=os.waitstatus_to_exitcode(status)
        output.seek(0);error.seek(0)
        stdout=output.read();stderr=error.read()
        require(ret==0,"DEV_PROCESS_DID_NOT_PASS_"+stderr[-1300:])
    row=json.loads(stdout)
    require((row["family"],row["seed"],row["arm"])==(family,seed,arm),
            "DEV_CASE_WRONG_IDENTITY")
    row["complete_OS_CPU_user_sys_ns"]=round((cost.ru_utime+cost.ru_stime)*1e9)
    row["complete_OS_peak_RSS_bytes"]=cost.ru_maxrss*1024
    row["complete_OS_includes_python_import_FIT_prior_CHECK_heldout"]=True
    return row
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=FAMILIES,required=True)
    p.add_argument("--out",type=Path,required=True)
    z=p.parse_args()
    require(not z.out.exists(),"ORIGINAL_ENGINEERING_DEV_NO_OVERWRITE")
    z.out.mkdir(parents=True)
    observations=[measure(z.family,seed,arm) for seed in SEEDS for arm in ARMS]
    require(len(observations)==12,"ALL_TWELVE_DEVELOPMENT_PROCESSES")
    artifact={"schema":"mass.f124di.zero-oracle-dev-12-full-OS.v1",
       "family":z.family,"development_samples":observations,
       "full_OS_process_count":12,
       "no_extra_oracle_queries":True,
       "new_scientific_firstuse_consumed":0,
       "external_source_birth":False,
       "scientific_acceptance":False}
    with (z.out/("dev-"+z.family+".json")).open("x") as file:
        json.dump(artifact,file,indent=2,sort_keys=True);file.write("\n")
    print("F124DI_SOURCEFREE_TWELVE_DEV_OS_PROCESS=PASS")
if __name__=="__main__":main()
