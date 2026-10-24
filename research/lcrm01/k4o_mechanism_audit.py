#!/usr/bin/env python3
"""K4O source-only diagnostic of consumed K4N public FIT/DEV evidence.

Strictly retrospective: never samples environments, trains candidates, or
uses a hindsight repair to claim scientific advancement.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from k4m_mechanism_audit import selected, choice, squared

FROZEN=Path(__file__).with_name("k4o_frozen_mechanism_audit.json")
SCHEMA="mass.lcrm01.k4o.retrospective-information-and-capacity-diagnostic.v1"
METHODS=("full_12","fit_fidelity_4","coverage_4","outcome_aware_4","uniform_4")


def digest(b):
    return hashlib.sha256(b).hexdigest()


def original(zip_path):
    config=json.loads(FROZEN.read_text(encoding="utf-8"))
    expected=config["original_source"]
    if digest(zip_path.read_bytes()) != expected["zip_sha256"]:
        raise ValueError("K4O_ORIGINAL_ZIP_HASH_MISMATCH")
    payload={}
    with zipfile.ZipFile(zip_path) as arc:
        for name,pin in expected["members_sha256"].items():
            data=arc.read(name)
            if digest(data)!=pin:
                raise ValueError("K4O_ORIGINAL_MEMBER_HASH_DRIFT:"+name)
            payload[name]=json.loads(data)
    cmp=payload["comparison.json"]
    if (cmp.get("source_and_scientific_records_identical") is not True or
        cmp.get("result")!="NO_REPLICATED_DECISION_CORESET_ADVANCEMENT"):
        raise ValueError("K4O_ORIGINAL_COMPARISON_NOT_NO_GO")
    for fname in ("process-a.json","process-b.json"):
        r=payload[fname]
        if (r.get("schema")!="mass.lcrm01.k4n.original-fit-decision-fidelity-development.v1"
            or r.get("source_commit")!=expected["source_pin_CausalWorld"]
            or r.get("quality_cost_decision",{}).get("result")!=expected["K4N_outcome"]
            or r.get("scientific_accepted") is not False or
            r.get("scientific_first_use") is not False or
            r.get("original_K4L_negative_preserved") is not True or
            r.get("original_K4M_diagnostic_preserved") is not True or
            (r.get("FIT_exposures"),r.get("CHECK_exposures"),r.get("DEV_exposures"))!=(96,16,64)
            or (len(r.get("FIT_rows",[])),len(r.get("DEV_rows",[])))!=(96,64)):
            raise ValueError("K4O_ORIGINAL_SCIENTIFIC_PROVENANCE_DRIFT:"+fname)
    return config,payload


def model_pools(record,family):
    fit=record["FIT_rows"]
    audit=record["FIT_only_selection_audit"][family]["selected_FIT_variants_by_arm"]
    pools={}
    for arm in range(4):
        examples=sorted((r for r in fit if r["family"]==family and r["arm"]==arm),
                        key=lambda x:x["variant"])
        if [r["variant"] for r in examples]!=list(range(12)):
            raise ValueError("K4O_INCOMPLETE_ORIGINAL_FIT")
        pools[arm]={mode:selected(examples,mode) for mode in METHODS if mode!="fit_fidelity_4"}
        chosen={int(v) for v in audit[str(arm)]}
        if len(chosen)!=4:
            raise ValueError("K4O_FIT_DECISION_CORESET_CAPACITY_DRIFT")
        pools[arm]["fit_fidelity_4"]=[r for r in examples if r["variant"] in chosen]
    return pools


def trace(record):
    findings=[]
    for family in ("reaching","pushing"):
        pools=model_pools(record,family)
        dev=record["DEV_rows"]
        checks=[]
        fit=record["FIT_rows"]
        for variant in range(14,22):
            source=[r for r in dev if r["family"]==family and r["variant"]==variant]
            plan=next((p for p in record["DEV_plan"] if
                      p["family"]==family and p["variant"]==variant),None)
            if (plan is None or [r["arm"] for r in source]!=[0,1,2,3] or
                len({r["initial_observation_sha256"] for r in source})!=1 or
                source[0]["initial_observation_sha256"]!=plan["public_observation_sha256"]):
                raise ValueError("K4O_ORIGINAL_DEV_PUBLIC_RESET_MISMATCH")
            x=source[0]["features"]
            real={str(r["arm"]):r["reward"] for r in source}
            predictions={}
            for method in METHODS:
                result=choice({a:pools[a][method] for a in range(4)},x)
                if result["selected_arm"]!=plan["choices"][method]:
                    raise ValueError("K4O_RECOMPUTED_POLICY_DISAGREES_WITH_ORIGINAL:"+
                                     family+":"+str(variant)+":"+method)
                predictions[method]=result
            oracle=max(range(4),key=lambda a:(real[str(a)],-a))
            findings.append({"family":family,"DEV_variant":variant,
                "original_public_observation_sha256":source[0]["initial_observation_sha256"],
                "actual_public_reward_by_arm":real,
                "hindsight_actual_best_action":oracle,
                "predictions":predictions})
        fit_contexts={r["initial_observation_sha256"] for r in fit if
                      r["family"]==family and r["arm"]==0}
        dev_contexts={r["original_public_observation_sha256"] for r in findings
                      if r["family"]==family}
        checks.append({"family":family,"FIT_distinct_observable_contexts":len(fit_contexts),
             "DEV_distinct_observable_contexts":len(dev_contexts),
             "DEV_source_disjoint_from_FIT":not bool(dev_contexts&fit_contexts)})
    return findings,checks


def diagnostic(config,record,findings):
    fam=config["diagnostics"]["families"][0]
    fid=config["diagnostics"]["case_ids"]
    pools=model_pools(record,fam)
    dev_map={r["variant"]:r for r in record["DEV_rows"] if r["family"]==fam and r["arm"]==0}
    contrasts=[]
    for v in fid:
        f=next(z for z in findings if z["family"]==fam and z["DEV_variant"]==v)
        x=dev_map[v]["features"]
        full=f["predictions"]["full_12"]
        mini=f["predictions"]["fit_fidelity_4"]
        rewards=f["actual_public_reward_by_arm"]
        ablations={}
        if v==19:
            baseline={a:list(pools[a]["full_12"]) for a in range(4)}
            for removed in ([7],[8],[7,8]):
                variant={a:list(baseline[a]) for a in range(4)}
                variant[3]=[r for r in variant[3] if r["variant"] not in removed]
                ablations["full_minus_FIT_"+",".join(map(str,removed))]=choice(variant,x)["selected_arm"]
            compact={a:list(pools[a]["fit_fidelity_4"]) for a in range(4)}
            for restored in (7,8):
                original=next(r for r in pools[3]["full_12"] if r["variant"]==restored)
                extra={a:list(compact[a]) for a in range(4)}
                extra[3].append(original)
                ablations["small_plus_fifth_FIT_"+str(restored)]=choice(extra,x)["selected_arm"]
                # Matched four-item counterfactual is still hindsight, not first use.
                replace={a:list(compact[a]) for a in range(4)}
                replace[3]=replace[3][1:]+[original]
                ablations["small_replace_lowest_FIT_with_"+str(restored)]=choice(replace,x)["selected_arm"]
        contrasts.append({"DEV_variant":v,
            "original_full_arm":full["selected_arm"],
            "original_compressed_arm":mini["selected_arm"],
            "hindsight_actual_best_arm":f["hindsight_actual_best_action"],
            "full_nearest_FIT_arm3":full["arm_predictions"]["3"]["FIT_variant"],
            "compressed_nearest_FIT_arm3":mini["arm_predictions"]["3"]["FIT_variant"],
            "full_predicted_arm3_return":full["arm_predictions"]["3"]["predicted_return"],
            "compressed_predicted_arm3_return":mini["arm_predictions"]["3"]["predicted_return"],
            "arm3_minus_arm1_actual_reward":rewards["3"]-rewards["1"],
            "ablation_actions":ablations})
    source_loss=record["FIT_only_selection_audit"]["reaching"]
    return {"contrasts":contrasts,
        "fit_only_optimization":{"initial_loss":source_loss["initial_FIT_loss"],
          "final_loss":source_loss["final_FIT_loss"],
          "FIT_swaps":len(source_loss["strict_improving_swaps"])},
        "one_record_strict_capacity_lower_bound_proven":False,
        "new_unseen_transfer_success_proven":False}


def examine(path):
    config,originals=original(path)
    reports=[]
    for name in ("process-a.json","process-b.json"):
        rows,checks=trace(originals[name])
        analysis=diagnostic(config,originals[name],rows)
        reports.append({"context_custody":checks,"traces":rows,"diagnostic":analysis})
    if reports[0]!=reports[1]:
        raise ValueError("K4O_DIAGNOSTIC_DIFFERENCE_BETWEEN_ORIGINAL_PROCESSES")
    data=reports[0]
    assert len(data["traces"])==16
    t={z["DEV_variant"]:z for z in data["diagnostic"]["contrasts"]}
    # K4N case19: two adjacent high-return FIT records are absent in small,
    # and full itself misses case17. This is bounded diagnosis, NOT proof of
    # representation insufficiency or a lower bound on 4-example capacity.
    if not (t[19]["original_full_arm"]==3 and t[19]["original_compressed_arm"]==1
       and t[17]["original_full_arm"]==1 and t[17]["hindsight_actual_best_arm"]==3):
        raise ValueError("K4O_FROZEN_FAILURE_CASE_NOT_REPRODUCED")
    return {"schema":SCHEMA,"gate":"LCRM01-K4O",
        "result":"READ_ONLY_MECHANISM_BOUNDARIES_IDENTIFIED",
        "original_artifact_sha256":config["original_source"]["zip_sha256"],
        "original_no_go_preserved":True,"source_provenance_fail_closed":True,
        "original_reaching_pushing_DEV_choices_reconstructed_per_process":16,
        "two_original_process_diagnostics_agree":True,
        "source_context_checks":data["context_custody"],
        "retrospective_analysis":data["diagnostic"],
        "new_scientific_positive":False,"scientific_first_use":False,
        "scientific_accepted":False,"novel_cognitive_architecture_claim":False}


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--artifact-zip",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    x=a.parse_args()
    if x.output.exists() or not x.output.parent.is_dir():
        raise RuntimeError("K4O_DIAGNOSTIC_OUTPUT_MUST_BE_FRESH")
    r=examine(x.artifact_zip)
    x.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("K4O_DIAGNOSIS="+r["result"])
    for contrast in r["retrospective_analysis"]["contrasts"]:
        print("K4O_CONTRAST_"+str(contrast["DEV_variant"])+"="+json.dumps(contrast,sort_keys=True))
    print("K4O_SCIENCE_ACCEPTED=False")


if __name__=="__main__":
    main()
