"""F124-CX independent read-only full 64-cell factorial reconciliation.

Four GitHub-hosted Linux shards each produce exactly 16 separate child
processes. Aggregator never retrains, regenerates synthetic fixtures,
replays any consumed scientific source or changes frozen parameters.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics

ARMS=("attentive","gated")
REGIMES=("dense","sparse")
SEEDS=(0,1,2,3)
HIDDENS=(8,16)
EPOCHS=(45,135)
PRIMARY_METRICS=("diagnostic_heldout_bit_errors_even_when_vetoed",
                 "diagnostic_heldout_BCE_even_when_vetoed",
                 "diagnostic_heldout_exact_episodes_of_8")

def need(ok,reason):
    if not ok:raise RuntimeError("F124CX_REVIEW_"+reason)

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def validate_shards(root):
    expected={"shard-"+regime+"-"+str(seed)+".json"
              for regime in REGIMES for seed in (0,2)}
    found={p.name for p in root.glob("shard-*.json")}
    need(found==expected,"ALL_FOUR_UNDUPLICATED_ORIGINAL_SHARDS")
    rows=[]
    hashes=[]
    for path in sorted(root.glob("shard-*.json")):
        shard=json.loads(path.read_text())
        need(shard["schema"]=="mass.f124cx.sourcefree-original-16cells-shard.v1"
             and shard["native_linux_wait4_whole_os_samples"]==16
             and len(shard["cells"])==16
             and shard["no_scientific_source_read"]
             and shard["sourcefree_diagnostic_only"]
             and not shard["scientific_acceptance"],
             "TRUSTED_ORIGINAL_SHARD_AND_SCIENCE_BOUNDARY")
        hashes.append({"shard":path.name,"content_sha256":digest(shard)})
        rows+=shard["cells"]
    expected_keys={(regime,seed,h,epochs,arm) for regime in REGIMES
                   for seed in SEEDS for h in HIDDENS for epochs in EPOCHS
                   for arm in ARMS}
    real_keys=[(x["regime"],x["seed"],x["hidden"],x["epochs"],x["arm"])
               for x in rows]
    need(len(real_keys)==64 and set(real_keys)==expected_keys,
         "COMPLETE_PREDECLARED_2x2_BY_TWO_REGIMES_FOUR_SEEDS_AND_TWO_MODELS")
    keyed={k:row for k,row in zip(real_keys,rows)}
    for key,row in keyed.items():
        regime,seed,h,epochs,arm=key
        need(row["schema"]=="mass.f124cx.sourcefree-single-full-BPTT-cell.v1"
             and row["full_BPTT"] and row["fit_episodes"]==24
             and row["check_veto_episodes"]==8
             and row["heldout_full_episodes"]==8
             and row["steps_per_episode"]==8
             and row["sourcefree_synthetic_only"]
             and row["original_source_or_oracle_imported"] is False
             and row["scientific_firstuse_consumed"]==0
             and not row["scientific_acceptance"]
             and row["full_python_numpy_BPTT_and_heldout_observed"]
             and row["complete_OS_process_CPU_ns"]>0
             and row["complete_OS_process_peak_RSS_bytes"]>0
             and row["diagnostic_heldout_not_scientific_model_admission"]
             and row["trainable_parameters"]>0,
             "ORIGINAL_MODEL_RESOURCE_AND_NO_FIRSTUSE_BOUNDARY")
    # Every matched arm/capacity/epoch shares exact FIT CHECK and HELDOUT
    # inputs. A mismatch is identity drift, not a statistical difference.
    for regime in REGIMES:
        for seed in SEEDS:
            group=[keyed[(regime,seed,h,e,a)] for h in HIDDENS
                   for e in EPOCHS for a in ARMS]
            for field in ("public_training_FIT_SHA256",
                          "public_veto_CHECK_SHA256","public_heldout_SHA256"):
                need(len({r[field] for r in group})==1,
                     "ALL_FACTORIAL_CELLS_SAME_PUBLIC_SOURCE_"+field)
    return keyed,hashes

def summarize(keyed):
    rows=[]
    for regime in REGIMES:
        for arm in ARMS:
            observations=[]
            for h in HIDDENS:
                for epoch in EPOCHS:
                    samples=[keyed[(regime,seed,h,epoch,arm)] for seed in SEEDS]
                    rec={"hidden":h,"epochs":epoch,
                         "natural_admitted_of_four":sum(x["natural_CHECK_veto_admission"] for x in samples),
                         "mean_fit_BCE":statistics.mean(x["FIT_final_BCE"] for x in samples),
                         "mean_check_bit_errors":statistics.mean(x["CHECK_bit_errors"] for x in samples),
                         "mean_heldout_BCE":statistics.mean(x[PRIMARY_METRICS[1]] for x in samples),
                         "mean_heldout_bit_errors":statistics.mean(x[PRIMARY_METRICS[0]] for x in samples),
                         "mean_heldout_exact_episodes_of_eight":statistics.mean(x[PRIMARY_METRICS[2]] for x in samples),
                         "mean_full_OS_CPU_ns":statistics.mean(x["complete_OS_process_CPU_ns"] for x in samples),
                         "mean_full_OS_peak_RSS_bytes":statistics.mean(x["complete_OS_process_peak_RSS_bytes"] for x in samples),
                         "mean_trainable_parameters":statistics.mean(x["trainable_parameters"] for x in samples)}
                    observations.append(rec)
            differences=[]
            for metric in PRIMARY_METRICS:
                effects={}
                for epoch in EPOCHS:
                    effects["H16_minus_H8_at_E"+str(epoch)]=statistics.mean(
                        keyed[(regime,seed,16,epoch,arm)][metric]-
                        keyed[(regime,seed,8,epoch,arm)][metric]
                        for seed in SEEDS)
                for h in HIDDENS:
                    effects["E135_minus_E45_at_H"+str(h)]=statistics.mean(
                        keyed[(regime,seed,h,135,arm)][metric]-
                        keyed[(regime,seed,h,45,arm)][metric]
                        for seed in SEEDS)
                effects["capacity_by_epoch_interaction"]=statistics.mean(
                    (keyed[(regime,seed,16,135,arm)][metric]-
                     keyed[(regime,seed,8,135,arm)][metric])-
                    (keyed[(regime,seed,16,45,arm)][metric]-
                     keyed[(regime,seed,8,45,arm)][metric])
                    for seed in SEEDS)
                differences.append({"metric":metric,"paired_seed_effects":effects})
            rows.append({"regime":regime,"arm":arm,
                         "all_four_factorial_means":observations,
                         "paired_capability_effects":differences})
    peer=[]
    for regime in REGIMES:
        for h in HIDDENS:
            for epoch in EPOCHS:
                cost=[];error=[];exact=[]
                for seed in SEEDS:
                    a=keyed[regime,seed,h,epoch,"attentive"]
                    c=keyed[regime,seed,h,epoch,"gated"]
                    cost.append(a["complete_OS_process_CPU_ns"]-c["complete_OS_process_CPU_ns"])
                    error.append(a[PRIMARY_METRICS[0]]-c[PRIMARY_METRICS[0]])
                    exact.append(a[PRIMARY_METRICS[2]]-c[PRIMARY_METRICS[2]])
                peer.append({"regime":regime,"hidden":h,"epochs":epoch,
                    "attentive_minus_gated_heldout_bit_errors_mean":statistics.mean(error),
                    "attentive_minus_gated_heldout_exact_episodes_mean":statistics.mean(exact),
                    "attentive_minus_gated_whole_OS_CPU_ns_mean":statistics.mean(cost),
                    "comparable_input_and_training_schedule":True,
                    "equal_FLOP_or_byte_work_proven":False,
                    "resource_nonregression_passed":False})
    return rows,peer

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shards",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    x=p.parse_args()
    need(not x.out.exists(),"NO_EVIDENCE_OVERWRITE")
    keyed,hashes=validate_shards(x.shards)
    factorial,peer=summarize(keyed)
    report={
      "schema":"mass.f124cx.sourcefree-original-64-cell-factorial-report.v1",
      "factorial_cells":64,"fully_measured_linux_OS_child_processes":64,
      "factorial_hiddens":list(HIDDENS),"epochs":list(EPOCHS),
      "regimes":list(REGIMES),"seeds":list(SEEDS),"arms":list(ARMS),
      "original_sourcefree_shard_hashes":hashes,
      "paired_and_factorial_findings":factorial,
      "equal_public_case_strong_recurrent_comparator_findings":peer,
      "complete_original_64_cell_evidence":[keyed[k] for k in sorted(keyed)],
      "preregistered_synthetic_source_free_only":True,
      "no_scientific_originals_consumed":True,
      "no_private_source_read":True,
      "higher_epoch_and_larger_H_are_diagnostic_not_frozen_model_changes":True,
      "generalization_claim_for_heldout_real_causal_worlds":False,
      "full_work_equivalence_claim":False,
      "OS_resource_nonregression_accepted":False,
      "protected_firstuse":False,"scientific_acceptance":False}
    x.out.mkdir(parents=True)
    (x.out/"complete-frozen-factorial.json").write_text(
         json.dumps(report,sort_keys=True,indent=2)+"\n")
    digest_rec=digest(report)
    summary={"schema":"mass.f124cx.sourcefree-factorial-summary.v1",
      "sha256_complete_report":digest_rec,
      "factorial_cells":64,
      "factorial_findings":factorial,"comparator_findings":peer,
      "no_original_sci_firstuse":True,
      "real_prospective_transfer":False,"science_accepted":False}
    (x.out/"source-safe-summary.json").write_text(
         json.dumps(summary,sort_keys=True,indent=2)+"\n")
    print("F124CX_SOURCEFREE_FACTORIAL_OS_PROCESSES=64")
    print("F124CX_ALL_FROZEN_FACTORIAL_IDS=PASS")
    for row in factorial:
        print("F124CX_"+row["regime"].upper()+"_"+row["arm"].upper()+
             "_SUMMARY="+json.dumps([
                {"hidden":v["hidden"],"epochs":v["epochs"],
                 "CHECK_admitted":v["natural_admitted_of_four"],
                 "heldout_bit_errors":round(v["mean_heldout_bit_errors"],3),
                 "heldout_exact_episodes":round(v["mean_heldout_exact_episodes_of_eight"],3)}
                for v in row["all_four_factorial_means"]],sort_keys=True))
    print("F124CX_NEW_FIRSTUSE_SCIENCE_CONSUMED=0")
    print("F124CX_SCIENTIFIC_ACCEPTANCE=FALSE")

if __name__=="__main__":main()
