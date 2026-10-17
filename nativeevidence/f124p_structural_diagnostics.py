"""F124-P: immutable model ablations and cross-source structural diagnostics.

Only original F124-O trained weights, pinned source-only GitHub receipt,
nonreserved F124-N DEV and F124-K fixture source; no training, no first use.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import f124k_extended_source as fixture
import f124n_novel_structure_source as nsource
import f124n_development_evidence as old_fixed
import f124o_native_learners as original
import f124p_frozen_variants as variants

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f124p-structural-ablation-freeze.json"
FREEZE_BLOB="f0b0be02fd0ee6baef77f17ed66fd9cd1ca045ae"
O_SOURCE_BLOB="a7ee347b736939bfdd0f7f56eca4d52a0fe0f0fd"
K_SOURCE_BLOB="b7c665e20c0fcff6655dba969a7e3de2c525ffab"
O_RECEIPT_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
N_RECEIPT_SHA="1c03362fcfa44dea72208867cf374b0c196b8bb3c79e6e430ffdb6685ee12739"
SCHEMA="forge.research.f124p.source-qualified-frozen-structural-ablation.v1"
ARMS=("original","ablate_compression","ablate_secondary","candidate")
SOURCES=("F124N_DEV_PREVIOUSLY_OBSERVED_DIAGNOSTIC","F124K_NONRESERVED_FIXTURE_CROSS_SOURCE")


def need(ok, label):
    nsource.need(ok,"F124P_"+label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(x):
    return (json.dumps(x,sort_keys=True,separators=(",",":"))+"\n").encode()


def blob(file):
    return nsource.git_blob(Path(file).read_bytes().replace(b"\r\n",b"\n"))


def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(nsource.git_blob(raw)==FREEZE_BLOB,"FREEZE_BLOB_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124p.frozen-architectural-ablation-and-cross-source.v1"
         and p["stage"]=="PREIMPLEMENTATION_FROZEN"
         and p["source_parent"]["qualified_f124o_head"]==
             "5b52da1e38d5ff5671c582676790daf0462dd18d"
         and p["source_parent"]["f124o_receipt_sha256"]==O_RECEIPT_SHA
         and p["source_parent"]["f124n_development_sha256"]==N_RECEIPT_SHA
         and p["source_parent"]["f124k_public_fixture_source_blob"]==K_SOURCE_BLOB
         and p["study"]["additional_training_steps"]==0
         and p["study"]["original_f124o_models_and_weights_immutable"]
         and p["study"]["sources"][0]["name"]==SOURCES[0]
         and p["study"]["sources"][1]["name"]==SOURCES[1]
         and all(v is False for v in p["authority"].values())
         and all(p["qualification"].values()),
         "PREIMPLEMENTATION_METHOD_CHANGED")
    need(blob(original.__file__)==O_SOURCE_BLOB, "ORIGINAL_LEARNER_CODE_DRIFT")
    need(blob(fixture.__file__)==K_SOURCE_BLOB, "PUBLIC_K_GENERATOR_DRIFT")
    original_source=nsource.frozen()
    fixture.frozen()
    return p,original_source


def authenticated_weights(path):
    raw=Path(path).read_bytes()
    need(sha(raw)==O_RECEIPT_SHA,"ORIGINAL_F124O_RECEIPT_DRIFT")
    result=json.loads(raw)
    need(result["schema"]==
         "forge.research.f124o.two-native-trained-development-outcomes.v1"
         and result["preimplementation_freeze_git_blob"]==
             "30b2d1f5097f6bd781d2dcc7ca84123100959dfe"
         and result["parent_f124n_receipt_sha256"]==N_RECEIPT_SHA
         and result["training_phase"]=="FIT_ONLY"
         and result["independent_model_arms"]==2
         and result["architectural_independence"]
         and result["protected_examples_generated"]==0
         and result["protected_examples_scored"]==0
         and result["scientific_acceptances"]==0
         and result["optimizer_promotions"]==0
         and result["accepted_ref_mutations"]==0
         and len(result["lanes"])==2,"PARENT_RECEIPT_CONTRACT")
    ret={}
    for idx,lane in enumerate(("Wingless","Yggdrasil")):
        row=result["lanes"][idx]
        weights=row["training"]["trained_weights"]
        expect=33 if lane=="Wingless" else 40
        fixed=43 if lane=="Wingless" else 45
        need(row["lane"]==lane and row["dev"]["learned_paired"]==expect
             and row["dev"]["fixed_paired"]==fixed
             and row["training"]["dev_seen_during_training"] is False
             and row["training"]["protected_cases_seen"]==0
             and row["training"]["training_steps"]==72
             and row["training"]["trained_weight_sha256"]==original.sha(weights)
             and len(weights)==7
             and all(isinstance(v,(float,int)) and math.isfinite(v) for v in weights),
             "UNMODIFIED_TRAINED_WEIGHT_OR_PRIOR_NEGATIVE")
        ret[lane]=list(weights)
    need(set(ret)=={"Wingless","Yggdrasil"},"TWO_LANES")
    return ret


def graphs(lane,source_name):
    need(lane in ("Wingless","Yggdrasil") and source_name in SOURCES,
         "UNAUTHORIZED_LANE_OR_SOURCE")
    if source_name==SOURCES[0]:
        for vector in nsource.VECTORS:
            for seed in nsource.COHORTS[lane]["DEV"]:
                pos,neg=nsource.build(lane,seed,vector,"DEV")
                need(nsource.paired_admit(pos,neg),"N_SOURCE_INVARIANT")
                yield seed,tuple(vector),pos,neg
    else:
        for vector in ((1,1,2),(3,2,0)):
            for seed in fixture.FIXTURES[lane]:
                pos,neg=fixture.build_fixture(seed,list(vector),lane)
                need(fixture.paired_admit(pos,neg),"K_SOURCE_INVARIANT")
                yield seed,tuple(vector),pos,neg


def evaluate(lane,source_name,weights):
    fixed=old_fixed.clone_single_validator(
        old_fixed.old_control.fixed_comparator,"graph")
    result={"source":source_name,"pairs":0,"exact_paired":0,
            "role_only_paired":0,
            "depth":{str(k):{"pairs":0} for k in (7,8,9)},
            "arms":{a:{"paired":0,"positive_false_negative":0,
                       "negative_false_positive":0,"both_incorrect":0,
                       "model_only_failures_vs_fixed":0,
                       "fixed_only_failures_vs_model":0,
                       "public_edge_scans":0,"raw_bit_ops":0,
                       "max_active":0,"max_retained":0,
                       "case_sha256":[],"depth":{str(k):{"pairs":0,"paired":0}
                                         for k in (7,8,9)}}
                    for a in ARMS},
            "fixed":{"paired":0,"public_edge_scans":0,"raw_bit_ops":0}}
    for seed,vec,pos,neg in graphs(lane,source_name):
        depth=str(len(pos["roles"]))
        result["pairs"]+=1
        result["depth"][depth]["pairs"]+=1
        reference=nsource.public_routes if source_name==SOURCES[0] else fixture.symbolic_routes
        result["exact_paired"]+=int(reference(pos)==1 and reference(neg)==0)
        result["role_only_paired"]+=int(
            reference(pos,True)>0 and reference(neg,True)==0)
        fresults=[fixed(g) for g in (pos,neg)]
        fixed_pair=bool(fresults[0][0] and not fresults[1][0])
        result["fixed"]["paired"]+=int(fixed_pair)
        result["fixed"]["public_edge_scans"]+=sum(
            r[1]["public_edge_scans"] for r in fresults)
        result["fixed"]["raw_bit_ops"]+=sum(
            r[1]["bit_comparisons"] for r in fresults)
        for arm in ARMS:
            (a,wa),(b,wb)=(variants.variant_forward(lane,arm,g,weights)
                           for g in (pos,neg))
            assert type(a) in (int,float) and type(b) in (int,float)
            yes,no=a>=0,b<0
            good=bool(yes and no)
            record=result["arms"][arm]
            record["paired"]+=int(good)
            record["positive_false_negative"]+=int(not yes)
            record["negative_false_positive"]+=int(not no)
            record["both_incorrect"]+=int(not yes and not no)
            record["model_only_failures_vs_fixed"]+=int(not good and fixed_pair)
            record["fixed_only_failures_vs_model"]+=int(good and not fixed_pair)
            record["depth"][depth]["pairs"]+=1
            record["depth"][depth]["paired"]+=int(good)
            record["public_edge_scans"]+=wa["public_edge_scans"]+wb["public_edge_scans"]
            record["raw_bit_ops"]+=wa["raw_bit_ops"]+wb["raw_bit_ops"]
            record["max_active"]=max(record["max_active"],
                                     wa["max_active"],wb["max_active"])
            record["max_retained"]=max(record["max_retained"],
                                       wa.get("max_retained",0),wb.get("max_retained",0))
            record["case_sha256"].append(sha(encoded({
                "lane":lane,"source":source_name,"seed":seed,"vector":vec,
                "arm":arm,"positive_logit":round(a,10),
                "negative_logit":round(b,10),"paired":good
            })))
    need(result["pairs"]==48 and result["exact_paired"]==48
         and result["role_only_paired"]==0
         and all(v["pairs"]==16 for v in result["depth"].values()),
         "COMPLETE_SOURCE_DENOMINATOR")
    for arm,record in result["arms"].items():
        need(len(record["case_sha256"])==48
             and all(row["pairs"]==16 for row in record["depth"].values())
             and record["positive_false_negative"]<=48
             and record["negative_false_positive"]<=48
             and (record["max_active"]<=7 and record["max_retained"]<=9
                  if lane=="Yggdrasil" else record["max_active"]<=192),
             "COMPLETE_COMPARISON_ARM")
    return result


def produce(path):
    proto,_=frozen()
    weights=authenticated_weights(path)
    out={"schema":SCHEMA,
         "parent_f124o_receipt_sha256":O_RECEIPT_SHA,
         "preimplementation_freeze_git_blob":FREEZE_BLOB,
         "unaltered_original_learners_git_blob":O_SOURCE_BLOB,
         "model_training_steps":0,"lanes":[],
         "protected_first_use":False,"scientific_acceptances":0,
         "optimizer_promotions":0,"accepted_ref_mutations":0,
         "codex_calls":0,"paid_api_calls":0,
         "resource_matched_superiority_proven":False,
         "original_protected_examples_generated":0}
    for lane in ("Wingless","Yggdrasil"):
        cases=[evaluate(lane,source_name,weights[lane]) for source_name in SOURCES]
        n=cases[0]
        expect=(33,43) if lane=="Wingless" else (40,45)
        need((n["arms"]["original"]["paired"],n["fixed"]["paired"])==expect,
             "F124O_ORIGINAL_DEV_BASELINE_DRIFT")
        out["lanes"].append({"lane":lane,
            "original_trained_weights_sha256":original.sha(weights[lane]),
            "studies":cases,
            "candidate_declared_before_scoring":True,
            "development_only":True})
    need(len(out["lanes"])==2,"LANE_DENOMINATOR")
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--f124o-receipt",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    out=Path(a.output)
    need(out.parent.is_dir() and not out.exists(),"IMMUTABLE_OUTPUT")
    report=produce(a.f124o_receipt)
    raw=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with out.open("xb") as f:
        f.write(raw)
    print("F124P_REPORT_SHA256="+sha(raw))
    for lane in report["lanes"]:
        for row in lane["studies"]:
            print("F124P_DEVELOPMENT="+lane["lane"]+
                  ":"+row["source"]+":original="+
                  str(row["arms"]["original"]["paired"])+
                  "/48:candidate="+str(row["arms"]["candidate"]["paired"])+
                  "/48:fixed="+str(row["fixed"]["paired"])+"/48")


if __name__=="__main__":
    try:
        main()
    except (ValueError,TypeError,KeyError,OSError,ArithmeticError,fixture.Invalid) as e:
        print("F124P_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)
