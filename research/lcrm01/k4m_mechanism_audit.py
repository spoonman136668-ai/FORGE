#!/usr/bin/env python3
"""Mass K4M retrospective audit against original K4L action/reward evidence.

Never launches CausalWorld, refits, changes its rewards, or qualifies science.
The fixed reaching DEV diagnostic was already observed in K4L; all results
here are hindsight reconstruction of the *unchanged* K4I/K4K predictor.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

FROZEN=Path(__file__).with_name("k4m_frozen_mechanism_audit.json")
MODELS=("full_12","outcome_aware_4","coverage_4","uniform_4")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def squared(a,b):
    if len(a)!=128 or len(b)!=128:
        raise ValueError("UNEXPECTED_PUBLIC_FEATURE_DIMENSION")
    return sum((x-y)**2 for x,y in zip(a,b))

def selected(records,mode):
    if len(records)!=12 or [x["variant"] for x in records]!=list(range(12)):
        raise ValueError("FROZEN_TRAIN_EXAMPLES_NOT_12_CHRONOLOGICAL")
    if mode=="full_12":
        return list(records)
    if mode=="uniform_4":
        slots=[0,3,6,9]
    elif mode=="coverage_4":
        slots=[0]
    elif mode=="outcome_aware_4":
        low=min(range(12),key=lambda i:(records[i]["reward"],records[i]["variant"]))
        high=max(range(12),key=lambda i:(records[i]["reward"],-records[i]["variant"]))
        slots=[low]
        if high!=low:
            slots.append(high)
    else:
        raise ValueError("UNKNOWN_ORIGINAL_SELECTOR")
    while len(slots)<4:
        choices=[i for i in range(12) if i not in slots]
        if not choices:
            raise ValueError("NO_ORIGINAL_EXEMPLARS")
        add=max(choices,key=lambda i:(min(squared(
                records[i]["features"],records[j]["features"]) for j in slots),
                -records[i]["variant"]))
        slots.append(add)
    return [records[i] for i in sorted(slots)]

def predict(pool,x):
    if not pool:
        raise ValueError("EMPTY_FIT_POOL")
    nearest=min(pool,key=lambda r:(squared(r["features"],x),r["variant"]))
    return {"FIT_variant":nearest["variant"],"predicted_return":nearest["reward"],
            "distance_squared":squared(nearest["features"],x)}

def choice(pools,features):
    probes={str(a):predict(pools[a],features) for a in range(4)}
    selected_arm=max(range(4),key=lambda a:(probes[str(a)]["predicted_return"],-a))
    return {"selected_arm":selected_arm,"arm_predictions":probes}

def evidence(archive):
    pin=json.loads(FROZEN.read_text(encoding="utf-8"))
    fixed=pin["source"]
    if sha(archive.read_bytes())!=fixed["K4L_original_zip_sha256"]:
        raise ValueError("FROZEN_ORIGINAL_ZIP_SHA256_NOT_MATCHED")
    names={"process-a.json":fixed["K4L_original_process_a_sha256"],
           "process-b.json":fixed["K4L_original_process_b_sha256"],
           "comparison.json":fixed["K4L_original_comparison_sha256"]}
    with zipfile.ZipFile(archive) as z:
        if not all(name in z.namelist() for name in names):
            raise ValueError("MISSING_ORIGINAL_EVIDENCE_MEMBER")
        payloads={}
        for name,expected in names.items():
            raw=z.read(name)
            if sha(raw)!=expected:
                raise ValueError("ORIGINAL_MEMBER_SHA256_DRIFT:"+name)
            payloads[name]=json.loads(raw)
    cmp=payloads["comparison.json"]
    if (cmp.get("source_and_scientific_records_identical") is not True or
        cmp.get("result")!="NO_REPLICATED_UNIQUE_MEMORY_PARETO_ADVANCEMENT" or
        cmp.get("scientific_first_use") is not False or
        cmp.get("scientific_accepted") is not False):
        raise ValueError("UNVERIFIED_K4L_NEGATIVE_COMPARISON")
    for name in ("process-a.json","process-b.json"):
        p=payloads[name]
        if (p.get("schema")!="mass.lcrm01.k4l.frozen-multicontext-actual-outcome-v1" or
            p.get("source_commit")!=fixed["causalworld_commit"] or
            p.get("protocol_sha256")!=fixed["K4L_protocol_sha256"] or
            (p.get("FIT_exposures"),p.get("CHECK_exposures"),p.get("DEV_exposures"))!=(96,16,64) or
            len(p.get("FIT_rows",[]))!=96 or len(p.get("DEV_rows",[]))!=64 or
            p.get("quality_cost_decision",{}).get("result")!=
               "K4L_NOT_QUALIFIED_PRESERVE_FULL_NEGATIVE" or
            p.get("scientific_first_use") is not False or
            p.get("scientific_accepted") is not False or
            p.get("original_K4K_negative_preserved") is not True):
            raise ValueError("HISTORICAL_SCIENCE_CUSTODY_DRIFT:"+name)
    return pin,payloads

def trace(original):
    fit=original["FIT_rows"]
    dev=original["DEV_rows"]
    plans=original["DEV_plan"]
    cores={}
    for family in ("reaching","pushing"):
        cores[family]={}
        for arm in range(4):
            pool=sorted([r for r in fit if r["family"]==family and r["arm"]==arm],
                        key=lambda r:r["variant"])
            cores[family][arm]={mode:selected(pool,mode) for mode in MODELS}
    results=[]
    for family in ("reaching","pushing"):
        for variant in range(14,22):
            arm_rows=[r for r in dev if r["family"]==family and r["variant"]==variant]
            plan=next((p for p in plans if p["family"]==family and p["variant"]==variant),None)
            if plan is None or [r["arm"] for r in arm_rows]!=[0,1,2,3]:
                raise ValueError("MISSING_OR_UNORDERED_ORIGINAL_DEV_SOURCE")
            if len({r["initial_observation_sha256"] for r in arm_rows})!=1 or (
               plan["public_observation_sha256"]!=arm_rows[0]["initial_observation_sha256"]):
                raise ValueError("PUBLIC_RESET_NOT_IDENTICAL_ACROSS_ACTIONS")
            x=arm_rows[0]["features"]
            predictions={}
            for mode in MODELS:
                pools={a:cores[family][a][mode] for a in range(4)}
                inference=choice(pools,x)
                if inference["selected_arm"]!=plan["choices"][mode]:
                    raise ValueError("ORIGINAL_POLICY_CHOICE_NOT_REPRODUCIBLE:"
                        +family+":"+str(variant)+":"+mode)
                predictions[mode]=inference
            results.append({"family":family,"DEV_variant":variant,"prediction":predictions})
    return cores,results

def target_diagnostic(original,cores,trace_rows,pin):
    family=pin["reference"]["target_family"]
    variant=pin["reference"]["target_DEV_variant"]
    example=pin["reference"]["FIT_example_of_interest"]
    target=next(z for z in trace_rows if z["family"]==family and z["DEV_variant"]==variant)
    source=next(r for r in original["DEV_rows"] if r["family"]==family and r["variant"]==variant)
    feat=source["features"]
    required=("full_12","outcome_aware_4","coverage_4")
    fit_lists={str(arm):{
        mode:[r["variant"] for r in cores[family][arm][mode]]
        for mode in required} for arm in (1,3)}
    full=target["prediction"]["full_12"]
    compressed=target["prediction"]["outcome_aware_4"]
    coverage=target["prediction"]["coverage_4"]
    if not (full["selected_arm"]==3 and compressed["selected_arm"]==1 and
            coverage["selected_arm"]==1):
        raise ValueError("K4L_OBSERVED_ACTION_REVERSAL_ABSENT")
    for mode in ("outcome_aware_4","coverage_4"):
        if example in fit_lists["3"][mode]:
            raise ValueError("EXPECTED_EXEMPLAR_WAS_NOT_DROPPED")
    if full["arm_predictions"]["3"]["FIT_variant"]!=example:
        raise ValueError("FULL_MEMORY_NEAREST_IS_NOT_FROZEN_RECORD")
    # Deterministic influence ablation. This is NOT a prospective trained candidate.
    without={a:list(cores[family][a]["full_12"]) for a in range(4)}
    without[3]=[r for r in without[3] if r["variant"]!=example]
    removed=choice(without,feat)
    restored={}
    for mode in ("outcome_aware_4","coverage_4"):
        pool={a:list(cores[family][a][mode]) for a in range(4)}
        record=next(r for r in cores[family][3]["full_12"] if r["variant"]==example)
        pool[3].append(record)  # five examples: a pure hindsight diagnostic, not matched-capacity
        restored[mode]=choice(pool,feat)
    actual=source["reward"]  # original dev row arm0, replaced below with real arm-return table
    outcomes={str(a):next(r["reward"] for r in original["DEV_rows"]
               if r["family"]==family and r["variant"]==variant and r["arm"]==a)
              for a in range(4)}
    diagnosed=(removed["selected_arm"]==1 and
       all(v["selected_arm"]==3 for v in restored.values()))
    return {
      "case":{"family":family,"DEV_variant":variant,"target_FIT_variant":example},
      "original_predictions":{m:target["prediction"][m] for m in required},
      "retained_original_FIT_variants_by_action":fit_lists,
      "hindsight_full_minus_exemplar":removed,
      "hindsight_compressed_plus_fifth_exemplar":restored,
      "actual_original_real_rewards_by_action":outcomes,
      "actual_real_return_loss":outcomes["3"]-outcomes["1"],
      "deterministic_source_selection_loss_identified":diagnosed,
      "restoration_has_four_exemplars":False,
      "hindsight_not_prospective":True,
      "no_new_interactive_experiences":True}

def analyze(zip_path):
    pin,payloads=evidence(zip_path)
    tracks=[]
    for name in ("process-a.json","process-b.json"):
        core,dev=trace(payloads[name])
        diagnosed=target_diagnostic(payloads[name],core,dev,pin)
        tracks.append(diagnosed)
    if tracks[0]!=tracks[1]:
        raise ValueError("INDEPENDENT_OS_PROCESS_DIAGNOSTIC_DISAGREEMENT")
    successful=tracks[0]["deterministic_source_selection_loss_identified"]
    return {
      "schema":"mass.lcrm01.k4m.retrospective-original-mechanism-result.v1",
      "gate":"LCRM01-K4M",
      "classification":"DETERMINISTIC_FIT_EXEMPLAR_SELECTION_LOSS" if successful
            else "MECHANISM_NOT_IDENTIFIED",
      "verified_original_DEV_choices_per_process":16,
      "fresh_Python_OS_processes_reconciled":2,
      "source_pin_sha256":sha(FROZEN.read_bytes()),
      "original_zip_sha256":pin["source"]["K4L_original_zip_sha256"],
      "diagnostic":tracks[0],
      "unmodified_K4L_scientific_NO_GO":True,
      "new_scientific_positive":False,
      "scientific_first_use":False,
      "scientific_accepted":False,
      "new_Wingless_or_Yggdrasil_mechanism":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--artifact-zip",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("DIAGNOSTIC_FILE_NOT_FRESH")
    report=analyze(args.artifact_zip)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("K4M_DIAGNOSIS="+report["classification"])
    print("K4M_VERIFIED_ORIGINAL_DEV_CHOICES_PER_PROCESS="+str(
        report["verified_original_DEV_choices_per_process"]))
    print("K4M_FIT_REMOVAL_ACTION="+str(
        report["diagnostic"]["hindsight_full_minus_exemplar"]["selected_arm"]))
    print("K4M_HINDSIGHT_ONLY_NOT_NEW_SCIENCE=TRUE")
if __name__=="__main__":
    main()
