"""F124-O immutable-development scientific evidence collector.

Reads *previously verified* F124-N development evidence by SHA-256.
Fits two fully separate trainable programs to FIT only. DEV evaluation is
performed once with frozen fitted parameters, compared to the same original
public fixed comparator and exact causal admission ceiling.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import f124n_novel_structure_source as source
import f124n_development_evidence as previous
import f124o_native_learners as learners

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT/"reference/research-intake/f124o-dual-native-learned-binding-freeze.json"
FREEZE_BLOB = "30b2d1f5097f6bd781d2dcc7ca84123100959dfe"
F124N_SHA = "1c03362fcfa44dea72208867cf374b0c196b8bb3c79e6e430ffdb6685ee12739"
SCHEMA = "forge.research.f124o.two-native-trained-development-outcomes.v1"


def need(ok,reason):
    source.need(ok,"RECEIPT_"+reason)


def read_freeze():
    b=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(source.git_blob(b)==FREEZE_BLOB,"SOURCE_FREEZE_DRIFT")
    p=json.loads(b)
    need(p["schema"]=="forge.research.f124o.two-independent-learned-structural-mechanisms.v1"
         and p["stage"]=="FROZEN_BEFORE_IMPLEMENTATION"
         and p["parent"]["f124n_source_commit"]=="59cef2e3e877d8b76e7ac971acca69e5d1ed172b"
         and p["parent"]["f124n_development_evidence_sha256"]==F124N_SHA
         and p["optimizer"]["epochs"]==learners.EPOCHS
         and p["optimizer"]["batch_pairs"]==learners.BATCH
         and p["optimizer"]["learning_rate"]==learners.RATE
         and p["optimizer"]["perturbation"]==learners.PERTURB
         and p["arms"]["Wingless"]["initial_weights"]==learners.WINGLESS_INIT
         and p["arms"]["Yggdrasil"]["initial_weights"]==learners.YGGDRASIL_INIT
         and all(v is False for v in p["boundaries"].values()),
         "FROZEN_PROTOCOL_MISMATCH")
    return p


def authentic_previous(path):
    raw=Path(path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==F124N_SHA,"F124N_AUTHENTIC_PRIOR_RECEIPT")
    p=json.loads(raw)
    need(p["schema"]==previous.SCHEMA and
         p["freeze_git_blob"]==source.PROTOCOL_BLOB and
         p["original_train_receipt_sha256"]==previous.TRAIN_SHA and
         p["protected_examples_generated"]==0 and
         p["protected_examples_scored"]==0 and
         p["scientific_acceptances"]==0 and
         p["optimizer_promotions"]==0 and
         len(p["lanes"])==2, "ORIGINAL_DEVELOPMENT_AUTHORITY")
    return p


def evaluate(lane,phase,w,public_fixed):
    summary={"pairs":0,"learned_paired":0,"learned_positive_correct":0,
             "learned_negative_correct":0,"fixed_paired":0,"exact_paired":0,
             "role_only_paired":0,"learned_edge_scans":0,"learned_raw_bit_ops":0,
             "fixed_edge_scans":0,"fixed_bit_ops":0,"max_active":0,
             "max_retained":0,"evictions":0,"execution_failures":0,
             "per_depth":{str(i):{"pairs":0,"learned_paired":0,
                                  "fixed_paired":0} for i in (7,8,9)},
             "case_sha256":[]}
    for vector in source.VECTORS:
        for seed in source.COHORTS[lane][phase]:
            pos,neg=source.build(lane,seed,vector,phase)
            outcomes=[]
            for g in (pos,neg):
                logit,work=learners.forward(lane,g,w)
                fixed,control_work=public_fixed(g)
                outcomes.append((learners.sigmoid(logit)>=.5,bool(fixed),
                                 logit,work,control_work))
            (ap,af,al,aw,ac),(bp,bf,bl,bw,bc)=outcomes
            learned=bool(ap and not bp)
            fixed=bool(af and not bf)
            depth=str(len(pos["roles"]))
            summary["pairs"]+=1
            summary["learned_paired"]+=int(learned)
            summary["learned_positive_correct"]+=int(ap)
            summary["learned_negative_correct"]+=int(not bp)
            summary["fixed_paired"]+=int(fixed)
            summary["exact_paired"]+=int(source.public_routes(pos)==1
                                       and source.public_routes(neg)==0)
            summary["role_only_paired"]+=int(source.public_routes(pos,True)>0
                                           and source.public_routes(neg,True)==0)
            depthstats=summary["per_depth"][depth]
            depthstats["pairs"]+=1
            depthstats["learned_paired"]+=int(learned)
            depthstats["fixed_paired"]+=int(fixed)
            for work,control in ((aw,ac),(bw,bc)):
                summary["learned_edge_scans"]+=work["public_edge_scans"]
                summary["learned_raw_bit_ops"]+=work["raw_bit_ops"]
                summary["fixed_edge_scans"]+=control["public_edge_scans"]
                summary["fixed_bit_ops"]+=control["bit_comparisons"]
                summary["max_active"]=max(summary["max_active"],
                                          work.get("max_active",0))
                summary["max_retained"]=max(summary["max_retained"],
                                            work.get("max_retained",0))
                summary["evictions"]+=work["evictions"]
            summary["case_sha256"].append(learners.sha({
                "lane":lane,"phase":phase,"seed":seed,"vector":vector,
                "depth":int(depth),"learned_pair":learned,"fixed_pair":fixed,
                "pos_logit":round(al,8),"neg_logit":round(bl,8)}))
    need(summary["pairs"]==48 and summary["exact_paired"]==48 and
         summary["role_only_paired"]==0 and
         len(summary["case_sha256"])==48 and
         all(v["pairs"]==16 for v in summary["per_depth"].values()),
         "COMPLETE_STRATIFIED_DENOMINATOR")
    need(summary["max_retained"]<=9 and
         (summary["max_active"]<=7 if lane=="Yggdrasil"
          else summary["max_active"]<=192), "RESOURCE_LIMIT")
    return summary


def collect(prior_path):
    freeze=read_freeze()
    prior=authentic_previous(prior_path)
    fixed=previous.clone_single_validator(previous.old_control.fixed_comparator,"graph")
    output={"schema":SCHEMA,"development_source_git_blob":source.git_blob(
                Path(source.__file__).read_bytes().replace(b"\r\n",b"\n")),
            "preimplementation_freeze_git_blob":FREEZE_BLOB,
            "parent_f124n_receipt_sha256":F124N_SHA,
            "frozen_training_configuration_sha256":learners.sha(freeze["optimizer"]),
            "architectural_independence":True,
            "training_phase":"FIT_ONLY","independent_model_arms":2,"lanes":[],
            "protected_examples_generated":0,"protected_examples_scored":0,
            "independent_first_use":False,"scientific_acceptances":0,
            "accepted_ref_mutations":0,"optimizer_promotions":0,
            "new_schedulers":0,"codex_calls":0,"paid_api_calls":0,
            "resource_matched_superiority_proven":False}
    need(output["development_source_git_blob"]==
         source.git_blob(Path(source.__file__).read_bytes().replace(b"\r\n",b"\n")),
         "SOURCE_IDENTITY")
    for i,lane in enumerate(("Wingless","Yggdrasil")):
        previous_lane=prior["lanes"][i]
        need(previous_lane["lane"]==lane and
             previous_lane["dev"]["pairs"]==48, "SOURCE_LANE_ORDER")
        fitted=learners.train(lane)
        frozen_w=list(fitted["trained_weights"])
        weightsha=fitted["trained_weight_sha256"]
        fit=evaluate(lane,"FIT",frozen_w,fixed)
        dev=evaluate(lane,"DEV",frozen_w,fixed)
        need(learners.sha(frozen_w)==weightsha and
             dev["fixed_paired"]==previous_lane["dev"]["fixed_paired"] and
             fit["fixed_paired"]==previous_lane["fit"]["fixed_paired"] and
             dev["exact_paired"]==48 and
             fitted["dev_seen_during_training"] is False,
             "FROZEN_DEV_OR_ORIGINAL_CONTROL_DRIFT")
        output["lanes"].append({
            "lane":lane,
            "distinct_mechanism":freeze["arms"][lane]["name"],
            "training":fitted,
            "fit":fit,"dev":dev,
            "prior_f124n_original_B_dev_paired":previous_lane["dev"]["B_paired"],
            "prior_f124n_fixed_dev_paired":previous_lane["dev"]["fixed_paired"],
            "dev_verdict":"LEARNED_ABOVE_FIXED_DEVELOPMENT_ONLY" if
                dev["learned_paired"]>dev["fixed_paired"]
                else "LEARNED_NOT_ABOVE_FIXED_DEVELOPMENT_NEGATIVE_OR_TIE"})
    need(len(set(row["training"]["trained_weight_sha256"] for row in
                 output["lanes"]))==2, "INDEPENDENT_TRAINED_STATE")
    return output


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--f124n-receipt",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    target=Path(args.output)
    need(target.parent.is_dir() and not target.exists(),"OUTPUT_ALREADY_EXISTS")
    receipt=collect(args.f124n_receipt)
    raw=(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode()
    with target.open("xb") as f:
        f.write(raw)
    print("F124O_DEVELOPMENT_RECEIPT_SHA256="+hashlib.sha256(raw).hexdigest())
    for row in receipt["lanes"]:
        r=row["dev"]
        print("F124O_DEV="+row["lane"]+":learned="+str(r["learned_paired"])+
              "/48:fixed="+str(r["fixed_paired"])+
              "/48:prior_B="+str(row["prior_f124n_original_B_dev_paired"])+
              "/48:train_l2="+str(row["training"]["weight_update_l2"]))


if __name__=="__main__":
    try: main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as e:
        print("F124O_QUARANTINED:"+str(e),file=sys.stderr)
        sys.exit(1)
