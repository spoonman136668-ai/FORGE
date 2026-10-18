"""F124-S original-evidence-authenticated fresh FIT/DEV and cost census.

Scores Wingless and Yggdrasil independently. The historical QG negative is
required and remains negative; the original frozen model and strong fixed
comparator are evaluated unchanged. All claims DEVELOPMENT ONLY.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import f124s_anchored_surrogate as method
import f124q_independent_binding as qmodel
import f124q_training_evidence as qprior
import f124q_fresh_source as qsource
import f124o_native_learners as original
import f124p_frozen_variants as prior_ablations
import f124h_train_receipt as old_control

SCHEMA="forge.research.f124s.authenticated-fresh-source-compute-census.v1"
O_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
QG_SHA="5496084491a8f78065891181a5676d348066578b83e46e77b2ca9bda7abae1c4"
ARMS=("original_F124O","prior_ablation","new_F124S","fixed_12of16")


def need(ok,why):
    method.need(ok,"REPORT_"+why)


def authenticated_o(path):
    data=Path(path).read_bytes()
    need(hashlib.sha256(data).hexdigest()==O_SHA,"ORIGINAL_RECEIPT_SHA")
    return qprior.original_weights(path)


def authenticated_qg(path):
    data=Path(path).read_bytes()
    need(hashlib.sha256(data).hexdigest()==QG_SHA,"ORIGINAL_QG_NEGATIVE_SHA")
    qg=json.loads(data)
    need(qg["schema"]=="forge.research.f124qg.frozen-fit-spsa-zero-gradient-diagnostic.v1"
         and qg["frozen_diagnostic_git_blob"]==
             "495565b44b20a6a8e0b8b0ab9566612f61d2b0f6"
         and qg["dev_cases_generated"]==0
         and qg["scientific_acceptances"]==0
         and qg["optimizer_promotions"]==0
         and qg["lanes"][0]["lane"]=="Wingless"
         and qg["lanes"][0]["nonzero_loss_difference_steps"]==65
         and qg["lanes"][1]["lane"]=="Yggdrasil"
         and qg["lanes"][1]["nonzero_loss_difference_steps"]==0
         and qg["lanes"][1]["update_l2"]==0,
         "NEGATIVE_MUST_REMAIN_IMMUTABLE")
    return qg


def predict(lane,arm,g,base,delta,public_fixed):
    if arm=="original_F124O":
        logit,work=original.forward(lane,g,list(base))
    elif arm=="prior_ablation":
        logit,work=prior_ablations.variant_forward(
            lane,"ablate_compression" if lane=="Wingless" else "ablate_secondary",
            g,list(base))
    elif arm=="new_F124S":
        logit,work=qmodel.forward(lane,g,list(base),list(delta))
    elif arm=="fixed_12of16":
        pred,orig_work=public_fixed(g)
        return bool(pred),{"public_edge_scans":orig_work["public_edge_scans"],
                           "raw_bit_ops":orig_work["bit_comparisons"],
                           "max_active":0,"max_retained":0}
    else:
        raise qsource.Quarantined("F124S_UNKNOWN_COMPARATOR")
    return bool(original.sigmoid(logit)>=0.5),work


def scoring(lane,phase,base,delta,fixed):
    stats={arm:{"pairs":0,"paired":0,"false_positives":0,"false_negatives":0,
                "public_edge_scans":0,"raw_bit_ops":0,"max_active":0,
                "max_retained":0,
                "depth":{str(d):{"pairs":0,"paired":0} for d in (7,8,9)},
                "case_sha256":[]} for arm in ARMS}
    exact=role_only=0
    for vector in method.VECTORS:
        for seed in method.COHORTS[lane][phase]:
            positive,negative=method.build(lane,seed,vector,phase)
            exact+=int(qsource.public_routes(positive)==1 and
                       qsource.public_routes(negative)==0)
            role_only+=int(qsource.public_routes(positive,True)>0 and
                           qsource.public_routes(negative,True)==0)
            depth=str(len(positive["roles"]))
            for arm in ARMS:
                x=stats[arm]
                p,wp=predict(lane,arm,positive,base,delta,fixed)
                n,wn=predict(lane,arm,negative,base,delta,fixed)
                pair=bool(p and not n)
                x["paired"]+=int(pair)
                x["pairs"]+=1
                x["false_positives"]+=int(n)
                x["false_negatives"]+=int(not p)
                x["depth"][depth]["pairs"]+=1
                x["depth"][depth]["paired"]+=int(pair)
                x["public_edge_scans"]+=wp["public_edge_scans"]+wn["public_edge_scans"]
                x["raw_bit_ops"]+=wp["raw_bit_ops"]+wn["raw_bit_ops"]
                x["max_active"]=max(x["max_active"],
                                    wp.get("max_active",0),wn.get("max_active",0))
                x["max_retained"]=max(x["max_retained"],
                                      wp.get("max_retained",0),wn.get("max_retained",0))
                x["case_sha256"].append(qmodel.digest({
                    "lane":lane,"phase":phase,"seed":seed,"vector":vector,
                    "arm":arm,"paired":pair,"positive_prediction":p,
                    "negative_prediction":n}))
    need(exact==48 and role_only==0,"ORIGINAL_CAUSAL_SOURCE")
    for arm,row in stats.items():
        need(row["pairs"]==48 and len(row["case_sha256"])==48
             and all(x["pairs"]==16 for x in row["depth"].values())
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192),
             "FROZEN_DENOMINATOR_OR_MEMORY")
    return {"phase":phase,"pairs":48,"exact_symbolic_ceiling":48,
            "role_only_negative":0,"arms":stats}


def run(path_o,path_qg):
    spec=method.frozen()
    originals=authenticated_o(path_o)
    authenticated_qg(path_qg)
    fixed=qprior.original_adapter.clone_single_validator(
        old_control.fixed_comparator,"graph")
    # Separate independent Q+fresh FIT. Generate DEV only after both trained.
    trained={}
    for lane in ("Wingless","Yggdrasil"):
        print("F124S_FIT_ATTEMPT="+lane,flush=True)
        trained[lane]=method.train(lane,originals[lane])
        print("F124S_FIT_UPDATE="+lane+":"+str(trained[lane]["update_l2"]),flush=True)
    need(all(t["genuine_fit_update"] and t["steps"]==72 and
             not t["DEV_generated_during_fit"] for t in trained.values()),
         "FIT_UPDATE_FAILED_NO_DEV_PERMITTED")
    out={"schema":SCHEMA,"freeze_git_blob":method.FREEZE_BLOB,
         "qg_immutable_diagnostic_sha256":QG_SHA,
         "original_trained_model_sha256":O_SHA,
         "original_model_unchanged":True,"source_family":"F124Q_ORIGINAL_BYTECODE_NEW_DISJOINT_SEEDS",
         "independent_model_lanes":2,"new_DEV_scored_only_after_both_fit":True,
         "protected_examples_generated":0,"original_scientific_first_use":False,
         "scientific_acceptances":0,"optimizer_promotions":0,
         "accepted_ref_mutations":0,"paid_model_calls":0,"codex_calls":0,
         "resource_matched_superiority_proven":False,"lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        train=trained[lane]
        fit=scoring(lane,"FIT",originals[lane],train["delta"],fixed)
        dev=scoring(lane,"DEV",originals[lane],train["delta"],fixed)
        # Report costs in separate units, not made-up equivalent runtime.
        costs={arm:{"public_edge_scans":dev["arms"][arm]["public_edge_scans"],
                    "raw_bit_ops":dev["arms"][arm]["raw_bit_ops"]}
               for arm in ARMS}
        out["lanes"].append({"lane":lane,"FIT_training":train,"FIT":fit,"DEV":dev,
                             "development_cost_census":costs,
                             "inference_capacity_increase":False,
                             "matched_compute_superiority_proven":False,
                             "development_verdict":
                                 "NEW_ABOVE_FIXED_UNMATCHED_COST_NOT_SCIENCE"
                                 if dev["arms"]["new_F124S"]["paired"]>
                                    dev["arms"]["fixed_12of16"]["paired"]
                                 else "NEW_NOT_ABOVE_FIXED_DEVELOPMENT_NEGATIVE_OR_TIE"})
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--original-o-receipt",required=True)
    ap.add_argument("--qg-negative-receipt",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    target=Path(args.output)
    need(target.parent.is_dir() and not target.exists(),"OUTPUT_OVERWRITE")
    report=run(args.original_o_receipt,args.qg_negative_receipt)
    data=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with target.open("xb") as stream:
        stream.write(data)
    print("F124S_REPORT_SHA256="+hashlib.sha256(data).hexdigest())
    for item in report["lanes"]:
        x=item["DEV"]["arms"]
        print("F124S_DEV="+item["lane"]+":learned="+
              str(x["new_F124S"]["paired"])+"/48:original="+
              str(x["original_F124O"]["paired"])+"/48:ablation="+
              str(x["prior_ablation"]["paired"])+"/48:fixed="+
              str(x["fixed_12of16"]["paired"])+"/48")


if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
        print("F124S_QUARANTINED:"+str(exc),file=sys.stderr)
        sys.exit(1)
