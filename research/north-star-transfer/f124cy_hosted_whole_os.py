"""F124-CY source-free whole Linux process comparison with audit.

Every one of the frozen 2 family×4 seed×3 arm cells is a separate full
OS process. Observations retain all natural no-admissions and sourcefree
heldout diagnostics. Nothing is selected/replayed from prior originals.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FAMILIES=("ungated_shared_linear_GF2","event_bit_gated_GF2")
ARMS=("shared","edge_control","gated_recurrent")
SEEDS=(0,1,2,3)
KEYS=tuple((family,seed,arm) for family in FAMILIES for seed in SEEDS for arm in ARMS)

def need(ok,why):
    if not ok:raise RuntimeError("F124CY_EVIDENCE_"+why)

def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def execute(family,seed,arm):
    need(sys.platform=="linux","REAL_LINUX_WAIT4_REQUIRED")
    env=dict(os.environ);env["OPENBLAS_NUM_THREADS"]="1";env["OMP_NUM_THREADS"]="1"
    env.pop("PYTHONPATH",None)
    with tempfile.TemporaryFile(mode="w+t") as out,tempfile.TemporaryFile(mode="w+t") as err:
        cmd=[sys.executable,"-B",str(HERE/"f124cy_sourcefree_trial.py"),
             "--regime",family,"--seed",str(seed),"--arm",arm]
        proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=out,stderr=err,text=True)
        pid,status,usage=os.wait4(proc.pid,0)
        need(pid==proc.pid,"ORIGINAL_OS_PROCESS_IDENTITY")
        code=os.waitstatus_to_exitcode(status)
        out.seek(0);err.seek(0)
        data=out.read();error=err.read()
        need(code==0,"CHILD_FAILED_"+error[-1300:])
    row=json.loads(data)
    need((row["regime"],row["seed"],row["arm"])==(family,seed,arm),
         "EXACT_FIXED_CELL_ID")
    row["full_OS_process_CPU_ns"]=int(round((usage.ru_utime+usage.ru_stime)*1e9))
    row["full_OS_peak_RSS_bytes"]=int(usage.ru_maxrss*1024)
    row["full_process_includes_Python_start_fit_CHECK_and_heldout"]=True
    need(row["full_OS_process_CPU_ns"]>0 and row["full_OS_peak_RSS_bytes"]>0,
         "COMPLETE_PROCESS_COST")
    return row

def validate(allrows):
    need(len(allrows)==24 and
         {(x["regime"],x["seed"],x["arm"]) for x in allrows}==set(KEYS),
         "ALL_24_PREREGISTERED_COMPLETE_OS_CELLS")
    bykey={(x["regime"],x["seed"],x["arm"]):x for x in allrows}
    for family in FAMILIES:
        for seed in SEEDS:
            group=[bykey[family,seed,a] for a in ARMS]
            for field in ("same_public_FIT_sha256","same_public_CHECK_sha256",
                          "same_public_HELDOUT_sha256"):
                need(len({row[field] for row in group})==1,
                     "THREE_INDEPENDENT_TRAINED_ARMS_SAME_PUBLIC_DATA_"+field)
            for row in group:
                need(row["schema"]=="mass.f124cy.sourcefree-compositional-role-comparison.v1"
                     and row["FIT_episodes"]==24 and row["CHECK_veto_only_episodes"]==8
                     and row["heldout_episodes"]==8
                     and row["full_rollout_no_early_exit"]
                     and row["full_process_includes_Python_start_fit_CHECK_and_heldout"]
                     and row["full_OS_process_CPU_ns"]>0
                     and row["full_OS_peak_RSS_bytes"]>0
                     and row["prospective_scientific_case_consumed"] is False
                     and row["original_source_ids_924_to_937_read"] is False
                     and row["privileged_hypothesis_class_declared"] is True
                     and not row["science_accepted"],"FULL_NATIVE_AND_SCIENTIFIC_BOUNDARY")
    return bykey

def aggregate(rows):
    d=validate(rows)
    summaries=[]
    for family in FAMILIES:
        for arm in ARMS:
            items=[d[family,seed,arm] for seed in SEEDS]
            summaries.append({
              "regime":family,"arm":arm,"case_count":4,
              "natural_CHECK_admissions":sum(x["natural_CHECK_trajectory_admission"] for x in items),
              "natural_CHECK_correct_full_episodes_out_of_32":sum(x["natural_CHECK_full_trajectories_correct"] for x in items),
              "diagnostic_heldout_exact_positives_out_of_32":sum(x["diagnostic_heldout_positive_exact_of_8"] for x in items),
              "diagnostic_false_positive_hard_negatives_out_of_32":sum(x["diagnostic_heldout_hard_false_positives_of_8"] for x in items),
              "mean_heldout_bit_errors_per_8episode_case":sum(x["diagnostic_heldout_bit_errors"] for x in items)/4,
              "mean_complete_OS_CPU_ns":sum(x["full_OS_process_CPU_ns"] for x in items)/4,
              "mean_complete_OS_peak_RSS_bytes":sum(x["full_OS_peak_RSS_bytes"] for x in items)/4,
              "independent_shard_cases":4})
    return summaries

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    x=p.parse_args()
    need(not x.out.exists(),"IMMUTABLE_FIRST_SOURCEFREE_MEASUREMENT")
    rows=[execute(*k) for k in KEYS]
    summaries=aggregate(rows)
    report={"schema":"mass.f124cy.sourcefree-compositional-24-process-study.v1",
      "original_protocol_commit_before_fixture":"f8b117c782280e1963fd02fa0f79577c1607d42f",
      "all_24_whole_linux_processes":rows,
      "all_six_aggregated_arm_family_rows":summaries,
      "known_bit_parity_inductive_bias_shared_with_BOTH_GF2_models":True,
      "three_model_training_on_same_public_sequences":True,
      "original_scientific_firstuse_consumed":0,
      "protected_science_opened":False,"resource_nonregression_claimed":False,
      "scientific_acceptance":False}
    x.out.mkdir(parents=True)
    (x.out/"full-sourcefree-evidence.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    safe={"schema":"mass.f124cy.sourcefree-compositional-safe-summary.v1",
          "complete_evidence_sha256":digest(report),
          "summaries":summaries,"whole_OS_child_processes":24,
          "firstuse_science":False,"science_accepted":False}
    (x.out/"summary.json").write_text(json.dumps(safe,sort_keys=True,indent=2)+"\n")
    print("F124CY_FULL_NATIVE_SOURCEFREE_PROCESS_COUNT=24")
    for row in summaries:
        print("F124CY_FAMILY_ARM="+json.dumps(row,sort_keys=True))
    print("F124CY_SCIENCE_FIRSTUSE_CONSUMED=0")
    print("F124CY_SCIENTIFIC_ACCEPTANCE=FALSE")

if __name__=="__main__":main()
