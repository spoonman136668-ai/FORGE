"""F124-Q source-qualified dual-lane FIT-only training and fresh DEV evidence.

Original F124-O 7 coefficients are read ONLY from the authentic prior evidence.
Two independent learned deltas, prior ablations, fixed threshold and symbolic
ceiling run on the SAME newly salted public cohort. Not independent science.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import f124o_native_learners as original
import f124p_frozen_variants as previous_ablations
import f124n_development_evidence as original_adapter
import f124h_train_receipt as original_control
import f124q_fresh_source as source
import f124q_independent_binding as learner

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f124q-fresh-causal-binding-freeze.json"
FREEZE_BLOB="82e2b26f8454231ac88af5a9169850cf997c0c71"
ORIGINAL_RECEIPT_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
ORIGINAL_MODEL_BLOB="a7ee347b736939bfdd0f7f56eca4d52a0fe0f0fd"
SCHEMA="forge.research.f124q.fresh-two-native-causal-binding-development.v1"


def need(ok,code):
    source.need(ok,"RECEIPT_"+code)


def git_blob(mod):
    return source.git_blob(Path(mod.__file__).read_bytes().replace(b"\r\n",b"\n"))


def validate_freeze():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(source.git_blob(raw)==FREEZE_BLOB,"FREEZE_GIT_BLOB_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124q.fresh-frozen-independent-binding-v1"
         and p["state"]=="PREIMPLEMENTATION_SOURCE_AND_HYPOTHESIS_FREEZE"
         and p["qualified_parent"]["sha"]=="497ef36d0a2d17c6ff474db97ba554a2f55536a4"
         and p["qualified_parent"]["authentic_trained_f124o_receipt_sha256"]==ORIGINAL_RECEIPT_SHA
         and p["qualified_parent"]["original_model_blob"]==ORIGINAL_MODEL_BLOB
         and p["training"]["steps"]==72 and p["training"]["epochs"]==12
         and p["training"]["batch_pairs"]==8
         and p["training"]["FIT_only"] is True
         and p["training"]["fresh_DEV_not_generated_during_fit"] is True
         and p["training"]["not_tune_after_DEV"] is True
         and p["outcomes"]["paired_dev_denominator"]==48
         and p["mechanisms"]["Wingless"]["trainable_parameters"]==4
         and p["mechanisms"]["Yggdrasil"]["trainable_parameters"]==2
         and all(v is False for v in p["authority"].values())
         and git_blob(original)==ORIGINAL_MODEL_BLOB,
         "FROZEN_IMPLEMENTATION_IDENTITY_DRIFT")
    source.frozen()
    return p


def original_weights(path):
    raw=Path(path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==ORIGINAL_RECEIPT_SHA,
         "F124O_ORIGINAL_WEIGHT_RECEIPT_UNAUTHENTIC")
    r=json.loads(raw)
    need(r["schema"]=="forge.research.f124o.two-native-trained-development-outcomes.v1"
         and r["parent_f124n_receipt_sha256"]==
           "1c03362fcfa44dea72208867cf374b0c196b8bb3c79e6e430ffdb6685ee12739"
         and r["training_phase"]=="FIT_ONLY" and r["scientific_acceptances"]==0
         and r["protected_examples_generated"]==0
         and r["optimizer_promotions"]==0 and len(r["lanes"])==2,
         "HISTORICAL_DEVELOPMENT_AUTHORITY")
    out={}
    for row in r["lanes"]:
        lane=row["lane"]
        w=row["training"]["trained_weights"]
        need(lane in source.COHORTS and lane not in out
             and len(w)==7
             and original.sha(w)==row["training"]["trained_weight_sha256"]
             and row["training"]["dev_seen_during_training"] is False,
             "ORIGINAL_LANE_WEIGHTS")
        out[lane]=tuple(w)
    need(set(out)=={"Wingless","Yggdrasil"},"BOTH_HISTORICAL_LANES")
    return out


def mechanism(lane,arm,g,base,delta,fixed):
    if arm=="strong_fixed":
        pred,work=fixed(g)
        return bool(pred),{"public_edge_scans":work["public_edge_scans"],
                           "raw_bit_ops":work["bit_comparisons"],
                           "max_active":0,"max_retained":0,"evictions":0}
    if arm=="original_F124O":
        logit,work=original.forward(lane,g,list(base))
    elif arm=="prior_frozen_ablation":
        logit,work=previous_ablations.variant_forward(lane,
           "ablate_compression" if lane=="Wingless" else "ablate_secondary",
           g,list(base))
    elif arm=="new_fit_only_learned":
        logit,work=learner.forward(lane,g,list(base),list(delta))
    else:
        raise source.Quarantined("F124Q_UNKNOWN_MECHANISM")
    need(math.isfinite(logit),"FINITE_MODEL_OUTPUT")
    return bool(original.sigmoid(logit)>=.5),work


def score_phase(lane,phase,base,delta,fixed):
    arms=("original_F124O","prior_frozen_ablation",
          "new_fit_only_learned","strong_fixed")
    stats={k:{"pairs":0,"paired":0,"pos_correct":0,"neg_correct":0,
              "false_positive":0,"false_negative":0,"execution_errors":0,
              "public_edge_scans":0,"raw_bit_ops":0,
              "max_active":0,"max_retained":0,"evictions":0,
              "depth":{str(n):{"pairs":0,"paired":0,"false_positive":0,
                                 "false_negative":0} for n in (7,8,9)},
              "case_sha256":[]}
           for k in arms}
    exact=role_only=0
    for vector in source.VECTORS:
        for seed in source.COHORTS[lane][phase]:
            pos,neg=source.build(lane,seed,vector,phase)
            need(source.public_routes(pos)==1 and
                 source.public_routes(neg)==0,"EXACT_PUBLIC_SOURCE")
            exact+=1
            role_only+=int(source.public_routes(pos,True)>0 and
                           source.public_routes(neg,True)==0)
            for arm in arms:
                x=stats[arm]
                preds=[]
                for graph in (pos,neg):
                    truth,work=mechanism(lane,arm,graph,base,delta,fixed)
                    preds.append(truth)
                    x["public_edge_scans"]+=work["public_edge_scans"]
                    x["raw_bit_ops"]+=work["raw_bit_ops"]
                    x["evictions"]+=work.get("evictions",0)
                    x["max_active"]=max(x["max_active"],work.get("max_active",0))
                    x["max_retained"]=max(x["max_retained"],work.get("max_retained",0))
                paired=bool(preds[0] and not preds[1])
                depth=str(len(pos["roles"]))
                x["pairs"]+=1
                x["paired"]+=int(paired)
                x["pos_correct"]+=int(preds[0])
                x["neg_correct"]+=int(not preds[1])
                x["false_positive"]+=int(preds[1])
                x["false_negative"]+=int(not preds[0])
                y=x["depth"][depth]
                y["pairs"]+=1
                y["paired"]+=int(paired)
                y["false_positive"]+=int(preds[1])
                y["false_negative"]+=int(not preds[0])
                x["case_sha256"].append(learner.digest({
                    "lane":lane,"phase":phase,"seed":seed,"vector":vector,
                    "depth":int(depth),"arm":arm,
                    "positive_prediction":preds[0],
                    "negative_prediction":preds[1]}))
    need(exact==48 and role_only==0,"FIXTURE_ORACLE_DENOMINATOR")
    for name,x in stats.items():
        need(x["pairs"]==48 and len(x["case_sha256"])==48
             and all(d["pairs"]==16 for d in x["depth"].values())
             and x["execution_errors"]==0 and
             x["max_retained"]<=9 and
             (x["max_active"]<=7 if lane=="Yggdrasil" else x["max_active"]<=192),
             "EXACT_COMPLETE_PAIR_COUNTS_OR_RESOURCE_BOUND")
    return {"phase":phase,"pairs":48,"exact_symbolic_paired":exact,
            "role_only_paired":role_only,"arms":stats}


def run(authenticated_prior_path):
    spec=validate_freeze()
    prior=original_weights(authenticated_prior_path)
    # Public comparators preserve original bytecode; only graph shape validator
    # rebound to F124-N public validator. All actual graphs from guarded Q source.
    fixed=original_adapter.clone_single_validator(
        original_control.fixed_comparator,"graph")
    trained={}
    # Critical anti-leak order: train both separately before any Q DEV build.
    for lane in ("Wingless","Yggdrasil"):
        print("F124Q_FIT_ATTEMPT="+lane,flush=True)
        trained[lane]=learner.train(lane,prior[lane])
        print("F124Q_FIT_PASS="+lane+":UPDATE_L2="+str(trained[lane]["weight_update_l2"]),flush=True)
    out={"schema":SCHEMA,
         "source_protocol_git_blob":source.PROTOCOL_BLOB,
         "frozen_preimplementation_git_blob":FREEZE_BLOB,
         "authenticated_parent_receipt_sha256":ORIGINAL_RECEIPT_SHA,
         "qualified_parent_head":"497ef36d0a2d17c6ff474db97ba554a2f55536a4",
         "training_method":"INDEPENDENT_NEW_FIT_ONLY_SPSA",
         "source_born_accepted_original":False,
         "protected_source_generated":0,"protected_first_use":False,
         "scientific_acceptances":0,"accepted_refs_changed":0,
         "optimizer_promotions":0,"paid_api_calls":0,"codex_calls":0,
         "cross_lane_parameter_sharing":False,
         "matched_compute_superiority_proven":False,"lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        fit=score_phase(lane,"FIT",prior[lane],trained[lane]["delta"],fixed)
        dev=score_phase(lane,"DEV",prior[lane],trained[lane]["delta"],fixed)
        out["lanes"].append({
            "lane":lane,
            "new_trainable_mechanism":spec["mechanisms"][lane]["model"],
            "training":trained[lane],"fit":fit,"dev":dev,
            "development_verdict":"LEARNED_ABOVE_STRONG_FIXED_IN_FRESH_DEV_ONLY"
            if dev["arms"]["new_fit_only_learned"]["paired"]>
               dev["arms"]["strong_fixed"]["paired"]
            else "LEARNED_NOT_ABOVE_STRONG_FIXED_IN_FRESH_DEV"})
    need(len(out["lanes"])==2 and
         trained["Wingless"]["delta_sha256"]!=
         trained["Yggdrasil"]["delta_sha256"] and
         all(x["training"]["dev_access_during_training"]==0
             for x in out["lanes"]),"LANE_ISOLATION_AND_NO_DEV_TRAIN")
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--f124o-receipt",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    dest=Path(args.output)
    need(dest.parent.is_dir() and not dest.exists(),"NO_OUTPUT_REPLACEMENT")
    result=run(args.f124o_receipt)
    data=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(data)
    print("F124Q_DEVELOPMENT_SHA256="+hashlib.sha256(data).hexdigest())
    for row in result["lanes"]:
        d=row["dev"]["arms"]
        print("F124Q_DEV:"+row["lane"]+":learned="+
              str(d["new_fit_only_learned"]["paired"])+
              "/48:prior="+str(d["original_F124O"]["paired"])+
              "/48:ablation="+str(d["prior_frozen_ablation"]["paired"])+
              "/48:fixed="+str(d["strong_fixed"]["paired"])+"/48")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as e:
        print("F124Q_QUARANTINED:"+str(e),file=sys.stderr)
        sys.exit(1)
