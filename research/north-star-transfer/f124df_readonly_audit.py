"""F124-DF independent no-model-rerun all-96 original OS evidence audit.

Read-only exact provider shard artifacts. Validate complete 4×4×2×3
frozen case roster, paired public identity, real wait4 CPU/RSS, stable
model output/diagnosis, and retained mathematical nullspace witnesses.
No private source generator or model imports inside this audit.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics

FAMILIES=("rotated-modular-add-unfamiliar","rotated-modular-add-role-switch",
          "plain-modular-add-control","three-register-arithmetic-out-of-class")
SEEDS=(101,102,103,104)
ARMS=("frozen_sparse_crossbit","frozen_equal_full_ANF")
REPS=3
def need(ok,why):
    if not ok:raise RuntimeError("F124DF_AUDIT_"+why)
def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def classify(z):
    f=z["post_learning_forensic_receipt"]
    if f.get("outside_two_register_hypothesis"):
        return "THREE_REGISTER_REPRESENTATION_BOUNDARY"
    if not f["source_model_class_representable"]:
        return "SOURCE_OPERATOR_NOT_REPRESENTABLE"
    if not z["natural_FIT"]:
        return "FITTING_FAILED_DESPITE_REPRESENTABILITY"
    ambiguity=f["true_pair_FIT_indeterminacy"]["witness_exists"]
    wrong=f["wrong_pair_selected"]
    if wrong and ambiguity:return "PAIR_SELECTION_AND_FIT_UNDERIDENTIFICATION"
    if wrong:return "PAIR_SELECTION_DIFFERENT_TRUE_CAUSAL_INPUT_PAIR"
    if ambiguity and not z["natural_CHECK_admission"]:
        return "TRUE_PAIR_FIT_UNDERDETERMINED_CHECK_FAILED"
    if ambiguity:return "TRUE_PAIR_FIT_UNDERDETERMINED_CHECK_PASSED"
    if not z["natural_CHECK_admission"]:return "FULL_RANK_FIT_BUT_CHECK_FAILED"
    return "UNIQUE_FIT_AND_CHECK_PASSED"
def audit(directory):
    files=list(directory.glob("shard-*.json"))
    expected={"shard-"+f+"-"+str(seed)+".json" for f in FAMILIES for seed in (101,103)}
    need(len(files)==8 and {f.name for f in files}==expected,
         "EIGHT_NONOVERLAPPING_ORIGINAL_SHARDS")
    samples={};hashes=[]
    for path in files:
        data=json.loads(path.read_text())
        need(data["schema"]=="mass.f124df.original-sourcefree-12-process-forensic-shard.v1"
             and data["complete_hosted_OS_processes"]==12
             and len(data["original_samples"])==12
             and data["authentic_scientific_firstuse"]==0
             and not data["independent_external_sources"]
             and not data["scientific_acceptance"],"ONLY_FRESH_SOURCEFREE_EVIDENCE")
        hashes.append({"shard":path.name,"SHA256":digest(data)})
        for obs in data["original_samples"]:
            z=obs["measurement"];key=z["family"],z["seed"],z["arm"]
            need(z["schema"]=="mass.f124df.new-sourcefree-rotation-diagnostic.v1"
                 and z["family"]==data["family"]
                 and z["seed"] in (data["first_seed"],data["first_seed"]+1)
                 and z["arm"] in ARMS and obs["repeat"] in range(REPS)
                 and z["FIT_episodes"]==24 and z["CHECK_veto_episodes"]==8
                 and z["heldout_positives"]==8 and z["matched_hard_negatives"]==8
                 and z["original_competitors_unchanged"]
                 and not z["source_wiring_disclosed_to_models"]
                 and z["private_oracle_used_only_after_complete_model_scoring"]
                 and z["previous_sourcefree_91_94_never_replayed"]
                 and z["consumed_sci_924_937_never_used"]
                 and z["sourcefree_synthetic_only"]
                 and z["scientific_firstuse_consumed"]==0
                 and not z["scientific_acceptance"]
                 and z["OS_includes_python_fit_check_holdout_and_postfit_identifiability"]
                 and z["OS_complete_CPU_user_system_ns"]>0
                 and z["OS_peak_RSS_bytes"]>0,
                 "EXACT_PROVIDER_CPU_RSS_MATH_AND_SOURCE_CUSTODY")
            if len(z["post_learning_forensic_receipt"]["post_model_source_wiring"])==2:
                q=z["post_learning_forensic_receipt"]
                need(q["source_model_class_representable"]
                     and q["true_pair_FIT_degree4_representable"]
                     and q["true_pair_FIT_indeterminacy"]["witness_exists"]
                     and q["true_pair_FIT_indeterminacy"]["nullity"]>0
                     and q["true_pair_FIT_indeterminacy"]["unobserved_witness_proves_nonidentification"]
                     and q["FIT_numerical_optimizer_cannot_be_blamed_if_exact"],
                     "SOURCEFREE_REPRESENTABILITY_AND_NULLSPACE_PROOF")
            samples.setdefault(key,{})
            need(obs["repeat"] not in samples[key],"DUPLICATE_WHOLE_OS_RECEIPT")
            samples[key][obs["repeat"]]=z
    keys={(f,seed,arm) for f in FAMILIES for seed in SEEDS for arm in ARMS}
    need(set(samples)==keys and all(set(z)==set(range(REPS))
         for z in samples.values()),"ALL_96_FROZEN_NEW_SOURCEFREE_SAMPLES")
    for family in FAMILIES:
        for seed in SEEDS:
            a,b=(samples[family,seed,arm][0] for arm in ARMS)
            for field in ("FIT_source_sha256","CHECK_source_sha256","HELDOUT_source_sha256"):
                need(a[field]==b[field],"UNEQUAL_PUBLIC_SOURCE_"+field)
            x=a["post_learning_forensic_receipt"]
            y=b["post_learning_forensic_receipt"]
            need(x["post_model_source_wiring"]==y["post_model_source_wiring"]
                 and x.get("true_pair_FIT_indeterminacy")==y.get("true_pair_FIT_indeterminacy"),
                 "INDEPENDENT_ARMS_SOURCE_OR_TRUE_RANK_CHANGED")
    for grp in samples.values():
        exemplar=grp[0]
        for z in grp.values():
            for field in ("natural_FIT","natural_CHECK_admission",
                          "CHECK_full_episodes_exact",
                          "diagnostic_heldout_positive_exact",
                          "diagnostic_hard_false_positives",
                          "CHECK_admitted_heldout_exact",
                          "CHECK_admitted_hard_false_positives",
                          "post_learning_forensic_receipt"):
                need(z[field]==exemplar[field],"REPEAT_DISAGREES_ON_FROZEN_SCIENCE_"+field)
    return samples,hashes
def summarise(samples):
    out=[]
    for family in FAMILIES:
        for arm in ARMS:
            cases=[samples[family,seed,arm][0] for seed in SEEDS]
            cost=[z for seed in SEEDS for z in samples[family,seed,arm].values()]
            classifications={key:sum(classify(case)==key for case in cases)
                             for key in sorted({classify(case) for case in cases})}
            post=[z["post_learning_forensic_receipt"] for z in cases]
            rank=[x["true_pair_FIT_indeterminacy"]["rank"] for x in post
                  if not x.get("outside_two_register_hypothesis")]
            out.append({
              "family":family,"arm":arm,
              "FIT_fitted_cases":sum(z["natural_FIT"] for z in cases),
              "CHECK_admitted_cases_of_4":sum(z["natural_CHECK_admission"] for z in cases),
              "CHECK_correct_full_episodes_of_32":sum(z["CHECK_full_episodes_exact"] for z in cases),
              "admitted_exact_positive_of_32":sum(z["CHECK_admitted_heldout_exact"] or 0 for z in cases),
              "admitted_hard_false_positive_of_32":sum(z["CHECK_admitted_hard_false_positives"] or 0 for z in cases),
              "post_learning_failure_classification":classifications,
              "true_pair_rank_by_frozen_seed":rank,
              "mean_true_pair_rank":sum(rank)/len(rank) if rank else None,
              "cases_selected_wrong_pair":sum(q.get("wrong_pair_selected") is True for q in post),
              "cases_true_polynomial_representable":sum(q.get("source_model_class_representable") is True for q in post),
              "cases_true_pair_FIT_underdetermined":sum(q.get("true_pair_FIT_indeterminacy",{}).get("witness_exists") is True for q in post),
              "complete_OS_repetitions":12,
              "median_complete_OS_CPU_ns":statistics.median(z["OS_complete_CPU_user_system_ns"] for z in cost),
              "median_complete_OS_peak_RSS_bytes":statistics.median(z["OS_peak_RSS_bytes"] for z in cost),
              "native_FLOPs_equal_certified":False,
              "scientific_acceptance":False})
    return out
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shards",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    z=p.parse_args()
    need(not z.out.exists(),"PRESERVE_ORIGINAL_CUSTODY_NO_OVERWRITE")
    samples,shards=audit(z.shards)
    findings=summarise(samples)
    report={"schema":"mass.f124df.original-independent-96-process-readonly.v1",
            "all_original_native_samples":[{"family":key[0],"seed":key[1],"arm":key[2],
                    "rep":rep,"row":record}
                for key,grp in sorted(samples.items()) for rep,record in sorted(grp.items())],
            "eight_original_sourcefree_shard_sha256s":shards,
            "per_family_model_findings":findings,
            "total_complete_original_CPU_RSS_receipts":96,
            "original_scientific_firstuse_consumed":0,
            "independent_scientific_source_birth":False,
            "scientific_acceptance":False}
    z.out.mkdir(parents=True)
    (z.out/"full-original-96-diagnostic-receipts.json").write_text(
         json.dumps(report,sort_keys=True,indent=2)+"\n")
    safe={"schema":"mass.f124df.safe-rotation-identifiability-findings.v1",
          "complete_96_original_receipts_sha256":digest(report),
          "sourcefree_per_family":findings,"original_complete_OS_processes":96,
          "science_accepted":False}
    (z.out/"safe-findings.json").write_text(json.dumps(safe,sort_keys=True,indent=2)+"\n")
    print("F124DF_INDEPENDENT_ALL_96_OS_RECEIPTS=PASS")
    for x in findings:print("F124DF_ROTATION_IDENTIFIABILITY_RESULT="+json.dumps(x,sort_keys=True))
    print("F124DF_ORIGINAL_SCIENTIFIC_FIRSTUSE=0")
    print("F124DF_SCIENTIFIC_ACCEPTANCE=FALSE")
if __name__=="__main__":main()
