"""F124-P authentic F124-O frozen-weight ablations and cross-source development.

No training, no protected source access, no accepted science/policy promotion.
F124-N DEV already observed: only diagnostic replay. F124-K QUALIFICATION_FIXTURE:
independent-source development stress, previously used for other models.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import f124h_train_receipt as original_control
import f124n_development_evidence as original_adapter
import f124n_novel_structure_source as source_n
import f124k_extended_source as source_k
import f124o_native_learners as original
import f124p_frozen_variants as variants

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f124p-structural-ablation-freeze.json"
FREEZE_BLOB="f0b0be02fd0ee6baef77f17ed66fd9cd1ca045ae"
ORIGINAL_RECEIPT_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
ORIGINAL_MODEL_BLOB="a7ee347b736939bfdd0f7f56eca4d52a0fe0f0fd"
ORIGINAL_N_SOURCE_BLOB="b4ff0e72f8a2fee5976189049b3b7fc74fc45b9d"
ORIGINAL_K_SOURCE_BLOB="b7c665e20c0fcff6655dba969a7e3de2c525ffab"
SCHEMA="forge.research.f124p.frozen-development-cross-source-ablations.v1"
ARMS=("original","ablate_compression","ablate_secondary","candidate")


def need(ok,code):
    source_n.need(ok,"F124P_EVIDENCE_"+code)


def module_blob(mod):
    return source_n.git_blob(Path(mod.__file__).read_bytes().replace(b"\r\n",b"\n"))


def read_freeze():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(source_n.git_blob(raw)==FREEZE_BLOB,"FREEZE_BLOB_IDENTITY")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124p.frozen-architectural-ablation-and-cross-source.v1"
         and p["stage"]=="PREIMPLEMENTATION_FROZEN"
         and p["source_parent"]["qualified_f124o_head"]=="5b52da1e38d5ff5671c582676790daf0462dd18d"
         and p["source_parent"]["f124o_receipt_sha256"]==ORIGINAL_RECEIPT_SHA
         and p["source_parent"]["f124k_public_fixture_source_blob"]==ORIGINAL_K_SOURCE_BLOB
         and p["study"]["additional_training_steps"]==0
         and p["study"]["original_f124o_models_and_weights_immutable"] is True
         and p["study"]["sources"][0]["name"]=="F124N_DEV_PREVIOUSLY_OBSERVED_DIAGNOSTIC"
         and p["study"]["sources"][1]["name"]=="F124K_NONRESERVED_FIXTURE_CROSS_SOURCE"
         and p["study"]["sources"][1]["never_protected"] is True
         and all(v is False for v in p["authority"].values()),
         "FROZEN_STUDY_DRIFT")
    need(module_blob(original)==ORIGINAL_MODEL_BLOB
         and module_blob(source_n)==ORIGINAL_N_SOURCE_BLOB
         and module_blob(source_k)==ORIGINAL_K_SOURCE_BLOB,
         "IMMUTABLE_MODEL_SOURCE_PROVENANCE")
    source_n.frozen()
    source_k.frozen()
    return p


def authenticate_f124o(path):
    raw=Path(path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==ORIGINAL_RECEIPT_SHA,
         "UNAUTHENTIC_ORIGINAL_TRAINED_WEIGHT_RECEIPT")
    r=json.loads(raw)
    need(r["schema"]=="forge.research.f124o.two-native-trained-development-outcomes.v1"
         and r["preimplementation_freeze_git_blob"]=="30b2d1f5097f6bd781d2dcc7ca84123100959dfe"
         and r["parent_f124n_receipt_sha256"]==
             "1c03362fcfa44dea72208867cf374b0c196b8bb3c79e6e430ffdb6685ee12739"
         and r["training_phase"]=="FIT_ONLY"
         and r["architectural_independence"] is True
         and r["protected_examples_generated"]==0
         and r["protected_examples_scored"]==0
         and r["scientific_acceptances"]==0
         and r["optimizer_promotions"]==0
         and len(r["lanes"])==2,"F124O_AUTHORITY_OR_SCHEMA")
    frozen={}
    for row in r["lanes"]:
        lane=row["lane"]
        train=row["training"]
        w=train["trained_weights"]
        need(lane in ("Wingless","Yggdrasil") and lane not in frozen and
             train["train_phase"]=="FIT_ONLY" and
             train["epochs"]==12 and train["training_steps"]==72 and
             train["dev_seen_during_training"] is False and
             len(w)==7 and original.sha(w)==train["trained_weight_sha256"],
             "FIT_TRAINED_WEIGHT_OR_LANE_IDENTITY")
        frozen[lane]=tuple(w)
    need(set(frozen)=={"Wingless","Yggdrasil"},"BOTH_LANES")
    return frozen,r


def case_generator(lane,kind):
    if kind=="F124N_PREVIOUS_DEV":
        for vec in source_n.VECTORS:
            for seed in source_n.COHORTS[lane]["DEV"]:
                yield seed,tuple(vec),source_n.build(lane,seed,vec,"DEV")
    elif kind=="F124K_CROSS_SOURCE":
        for vec in ((1,1,2),(3,2,0)):
            for seed in source_k.FIXTURES[lane]:
                yield seed,tuple(vec),source_k.build_fixture(
                    seed,list(vec),lane,"QUALIFICATION_FIXTURE")
    else:
        raise source_n.Quarantined("F124P_UNKNOWN_COHORT")


def classify_pair(pos,neg,pp,pn):
    # 'Positive' and 'negative' are known only to this downstream evaluator.
    return ("PAIRED_CORRECT" if pp and not pn else
            "FALSE_POSITIVE_AND_FALSE_NEGATIVE" if not pp and pn else
            "FALSE_NEGATIVE" if not pp and not pn else
            "FALSE_POSITIVE")


def evaluate(lane,kind,weights,public_fixed):
    scores={}
    for arm in ARMS:
        scores[arm]={
            "paired":0,"true_positives":0,"true_negatives":0,
            "false_positives":0,"false_negatives":0,
            "both_wrong":0,"model_only_failures_vs_fixed":0,
            "fixed_only_failures_vs_model":0,"execution_errors":0,
            "public_edge_scans":0,"raw_bit_ops":0,
            "diversity_comparisons":0,"max_active":0,"max_retained":0,
            "per_depth":{str(d):{"pairs":0,"paired":0,
                                 "false_positive":0,"false_negative":0}
                         for d in (7,8,9)}, "case_hashes":[]}
    fixed_score={"paired":0,"public_edge_scans":0,"bit_comparisons":0}
    role_only_score=0
    exact_score=0
    pairs=0
    for seed,vec,(pos,neg) in case_generator(lane,kind):
        pairs+=1
        validate=source_n if kind=="F124N_PREVIOUS_DEV" else source_k
        need(validate.public_routes(pos)==1 and
             validate.public_routes(neg)==0 if kind=="F124N_PREVIOUS_DEV" else
             validate.symbolic_routes(pos)==1 and
             validate.symbolic_routes(neg)==0,
             "EXACT_ORACLE_SOURCE_DRIFT")
        exact_score+=1
        pp=(validate.public_routes(pos,True) if kind=="F124N_PREVIOUS_DEV"
            else validate.symbolic_routes(pos,True))
        pn=(validate.public_routes(neg,True) if kind=="F124N_PREVIOUS_DEV"
            else validate.symbolic_routes(neg,True))
        role_only_score+=int(pp>0 and pn==0)
        fc=[]
        for g in (pos,neg):
            pred,work=public_fixed(g)
            fc.append(bool(pred))
            fixed_score["public_edge_scans"]+=work["public_edge_scans"]
            fixed_score["bit_comparisons"]+=work["bit_comparisons"]
        fixedcorrect=bool(fc[0] and not fc[1])
        fixed_score["paired"]+=int(fixedcorrect)
        for arm in ARMS:
            a=scores[arm]
            predictions=[]
            errored=False
            for g in (pos,neg):
                try:
                    logit,work=variants.variant_forward(lane,arm,g,list(weights))
                    need(math.isfinite(logit),"NONFINITE_LOGIT")
                    predictions.append(original.sigmoid(logit)>=.5)
                    a["public_edge_scans"]+=work["public_edge_scans"]
                    a["raw_bit_ops"]+=work["raw_bit_ops"]
                    a["diversity_comparisons"]+=work.get("diversity_comparisons",0)
                    a["max_active"]=max(a["max_active"],work.get("max_active",0))
                    a["max_retained"]=max(a["max_retained"],work.get("max_retained",0))
                except (source_n.Quarantined,source_k.Invalid,
                        OverflowError,ArithmeticError,ValueError):
                    errored=True
                    predictions.append(False)
            correct=bool(not errored and predictions[0] and not predictions[1])
            classification=classify_pair(pos,neg,*predictions)
            a["paired"]+=int(correct)
            a["true_positives"]+=int(not errored and predictions[0])
            a["true_negatives"]+=int(not errored and not predictions[1])
            a["false_positives"]+=int(errored or predictions[1])
            a["false_negatives"]+=int(errored or not predictions[0])
            a["both_wrong"]+=int(classification=="FALSE_POSITIVE_AND_FALSE_NEGATIVE")
            a["model_only_failures_vs_fixed"]+=int(not correct and fixedcorrect)
            a["fixed_only_failures_vs_model"]+=int(correct and not fixedcorrect)
            a["execution_errors"]+=int(errored)
            depth=str(len(pos["roles"]))
            d=a["per_depth"][depth]
            d["pairs"]+=1
            d["paired"]+=int(correct)
            d["false_positive"]+=int(errored or predictions[1])
            d["false_negative"]+=int(errored or not predictions[0])
            a["case_hashes"].append(original.sha({
                "lane":lane,"source":kind,"seed":seed,"vector":vec,
                "depth":depth,"arm":arm,"paired":correct,
                "classification":classification,"fixed_paired":fixedcorrect,
                "errored":errored}))
    need(pairs==48 and exact_score==48 and role_only_score==0,
         "COMPLETE_PUBLIC_SOURCE_DENOMINATOR")
    for arm,a in scores.items():
        need(len(a["case_hashes"])==48 and
             all(d["pairs"]==16 for d in a["per_depth"].values()),
             "COMPLETE_BALANCED_COHORT")
        need(a["max_retained"]<=9 and
             (a["max_active"]<=7 if lane=="Yggdrasil"
              else a["max_active"]<=192),
             "NO_SILENT_MEMORY_CAPACITY_EXPANSION")
    return {"source":kind,"pairs":pairs,"exact_reference_paired":exact_score,
            "role_only_paired":role_only_score,"fixed_public_12of16":fixed_score,
            "arms":scores}


def collect(path):
    frozen=read_freeze()
    weights,previous=authenticate_f124o(path)
    comparator=original_adapter.clone_single_validator(
        original_control.fixed_comparator,"graph")
    out={"schema":SCHEMA,"parent_qualified_head":
         "5b52da1e38d5ff5671c582676790daf0462dd18d",
         "frozen_contract_git_blob":FREEZE_BLOB,
         "original_f124o_receipt_sha256":ORIGINAL_RECEIPT_SHA,
         "weight_updates":0,"new_training_steps":0,
         "independent_first_use":False,"scientific_acceptances":0,
         "accepted_ref_mutations":0,"optimizer_promotions":0,
         "protected_examples_generated":0,"paid_model_calls":0,
         "resource_matched_superiority_proven":False,
         "lanes":[]}
    for index,lane in enumerate(("Wingless","Yggdrasil")):
        prior=previous["lanes"][index]
        need(prior["lane"]==lane,"ORIGINAL_LANE_ORDER")
        n=evaluate(lane,"F124N_PREVIOUS_DEV",weights[lane],comparator)
        k=evaluate(lane,"F124K_CROSS_SOURCE",weights[lane],comparator)
        need(n["arms"]["original"]["paired"]==prior["dev"]["learned_paired"]
             and n["fixed_public_12of16"]["paired"]==
                 prior["dev"]["fixed_paired"]
             and n["arms"]["original"]["execution_errors"]==0,
             "ORIGINAL_F124O_DEV_REPLAY_DRIFT")
        # Historical F124-L K public fixed results are source-identity matched.
        expected=37 if lane=="Wingless" else 36
        need(k["fixed_public_12of16"]["paired"]==expected,
             "F124L_PUBLIC_CONTROL_DRIFT")
        out["lanes"].append({"lane":lane,
            "original_f124o_frozen_weight_sha256":original.sha(list(weights[lane])),
            "diagnostic_consumed_f124n_dev":n,
            "cross_source_nonreserved_f124k_fixture":k,
            "candidate_verdict":"BEATS_BOTH_ORIGINAL_AND_FIXED_PUBLIC_ON_K"
            if (k["arms"]["candidate"]["paired"]>k["arms"]["original"]["paired"]
                and k["arms"]["candidate"]["paired"]>
                    k["fixed_public_12of16"]["paired"])
            else "NO_CROSS_SOURCE_FIXED_BASELINE_BREAKTHROUGH"})
    return out


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--f124o-receipt",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    dest=Path(args.output)
    need(dest.parent.is_dir() and not dest.exists(),"IMMUTABLE_OUTPUT_REQUIRED")
    result=collect(args.f124o_receipt)
    b=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(b)
    print("F124P_DEVELOPMENT_RECEIPT_SHA256="+hashlib.sha256(b).hexdigest())
    for row in result["lanes"]:
        for cohort in ("diagnostic_consumed_f124n_dev","cross_source_nonreserved_f124k_fixture"):
            r=row[cohort]
            print("F124P_RESULT:"+row["lane"]+":"+r["source"]+
                  ":original="+str(r["arms"]["original"]["paired"])+
                  "/48:candidate="+str(r["arms"]["candidate"]["paired"])+
                  "/48:fixed="+str(r["fixed_public_12of16"]["paired"])+
                  "/48:ablate_compression="+
                  str(r["arms"]["ablate_compression"]["paired"])+
                  "/48:ablate_secondary="+
                  str(r["arms"]["ablate_secondary"]["paired"])+"/48")


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as e:
        print("F124P_QUARANTINED:"+str(e),file=sys.stderr)
        sys.exit(1)
