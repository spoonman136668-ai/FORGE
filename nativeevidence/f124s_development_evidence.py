"""F124-S immutable source-qualified experiment and honest resource census.

Loads original F124-O and qualified F124-R signed-by-SHA artifacts without
touching source. All new training is independently FIT-only; fresh DEV is
constructed only after both new FIT attempts. On a frozen FIT negative, skip
that lane's DEV and preserve its failure, rather than tuning the model.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import f124o_native_learners as original
import f124p_frozen_variants as p_controls
import f124r_causal_learners as r_model
import f124n_development_evidence as old_validator
import f124h_train_receipt as old_fixed
import f124s_fresh_source as source
import f124s_native_mechanisms as new

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f124s-packed-key-causal-credit-freeze.json"
FREEZE_BLOB="33b299417fb284982aa162684b467b4593a6d828"
O_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
R_SHA="8ac2d22d10c91e453e33ca7d6deba44a75d92849b106d6f49cc9f19b123f2525"
O_BLOB="a7ee347b736939bfdd0f7f56eca4d52a0fe0f0fd"
R_BLOB="9c295483f680532d8ee8db86ae6e02a125743a08"
SCHEMA="forge.research.f124s.fresh-packed-key-cell-credit-development.v1"


def need(ok,code):
    source.need(ok,"RECEIPT_"+code)


def blob(mod):
    return source.git_blob(Path(mod.__file__).read_bytes().replace(b"\r\n",b"\n"))


def protocol():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(source.git_blob(raw)==FREEZE_BLOB,"FROZEN_SCIENTIFIC_CONTRACT")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124s.fixed-memory-credit-freeze.v1"
         and p["stage"]=="PREIMPLEMENTATION_FROZEN"
         and p["parent"]["exact_head"]=="522601491c10ebfeb36e7dca2627ff5366b51abb"
         and p["parent"]["f124r_authenticated_evidence_sha256"]==R_SHA
         and p["parent"]["f124o_authenticated_evidence_sha256"]==O_SHA
         and p["parent"]["f124r_model_blob"]==R_BLOB
         and p["parent"]["f124o_model_blob"]==O_BLOB
         and p["models"]["Wingless"]["candidate_serialized_state_bytes"]==10
         and p["models"]["Wingless"]["reference_serialized_state_bytes"]==40
         and p["models"]["Yggdrasil"]["active_limit"]==7
         and p["models"]["Yggdrasil"]["retained_limit"]==9
         and p["training"]["epochs"]==new.EPOCHS
         and p["training"]["batch_pairs"]==new.BATCH
         and p["training"]["steps"]==72
         and p["training"]["delta"]==new.PERTURB
         and p["training"]["lr"]==new.LR
         and p["training"]["no_post_DEV_changes"] is True
         and all(x is False for x in p["authority"].values())
         and blob(original)==O_BLOB and blob(r_model)==R_BLOB,
         "PREIMPLEMENTATION_DRIFT")
    source.frozen()
    return p


def authentic(path,digest):
    raw=Path(path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==digest,
         "AUTHENTIC_ORIGINAL_RECEIPT")
    return json.loads(raw)


def parents(o_path,r_path):
    o=authentic(o_path,O_SHA)
    r=authentic(r_path,R_SHA)
    need(o["schema"]=="forge.research.f124o.two-native-trained-development-outcomes.v1"
         and o["training_phase"]=="FIT_ONLY"
         and o["scientific_acceptances"]==0
         and len(o["lanes"])==2
         and r["schema"]=="forge.research.f124r.fresh-continuous-causal-development-v1"
         and r["qualified_f124q_parent_sha"]==
             "a3ef79b3dc10dcc4d544f808e35897e72ed4a154"
         and r["freeze_git_blob"]=="a4db651492631ad1be141ab2a0a6e1c86dad60ea"
         and r["protected_generated"]==0 and
         r["scientific_acceptances"]==0
         and len(r["lanes"])==2,"PARENT_PROVENANCE_OR_AUTHORITY")
    result={}
    for name in ("Wingless","Yggdrasil"):
        a=next((x for x in o["lanes"] if x["lane"]==name),None)
        b=next((x for x in r["lanes"] if x["lane"]==name),None)
        need(a is not None and b is not None,"MISSING_PAIRED_ORIGINAL_LANE")
        bw=a["training"]["trained_weights"]
        delta=b["training"]["delta"]
        need(a["training"]["train_phase"]=="FIT_ONLY"
             and not a["training"]["dev_seen_during_training"]
             and original.sha(bw)==a["training"]["trained_weight_sha256"]
             and b["training"]["fit_only"] is True
             and b["training"]["training_steps"]==72
             and r_model.digest(delta)==b["training"]["delta_sha256"],
             "TRAINED_STATE_IDENTITY")
        result[name]={"base":tuple(bw),"old_r_delta":tuple(delta)}
    return result


def predict(lane,arm,g,base,old_r_delta,delta,fixed):
    if arm=="strong_fixed":
        result,work=fixed(g)
        return bool(result),{
            "public_edge_scans":work["public_edge_scans"],
            "raw_bit_ops":work["bit_comparisons"],
            "max_active":0,"max_retained":0,"causal_key_comparisons":0}
    if arm=="old_F124O":
        z,c=original.forward(lane,g,list(base))
    elif arm=="old_F124R":
        z,c=r_model.forward(lane,g,list(base),list(old_r_delta))
    elif arm=="frozen_ablation":
        z,c=p_controls.variant_forward(lane,
           "ablate_compression" if lane=="Wingless" else "ablate_secondary",
           g,list(base))
    elif arm=="new_F124S":
        z,c=new.forward(lane,g,list(base),list(delta))
    else:
        raise source.Quarantined("F124S_UNKNOWN_ARM")
    need(math.isfinite(z),"FINITE_MODEL_LOGIT")
    return bool(original.sigmoid(z)>=.5),c


def evaluate(lane,phase,base,old_r_delta,delta,fixed):
    arms=("old_F124O","old_F124R","frozen_ablation",
          "new_F124S","strong_fixed")
    report={name:{
        "paired":0,"pairs":0,"positive_correct":0,"negative_correct":0,
        "false_positive":0,"false_negative":0,
        "public_edge_scans":0,"raw_bit_ops":0,"causal_key_comparisons":0,
        "max_active":0,"max_retained":0,"execution_errors":0,
        "state_logical_bytes_per_slot":(
          40 if name in ("old_F124O","frozen_ablation") and lane=="Wingless"
          else 42 if name=="old_F124R" and lane=="Wingless"
          else 10 if name=="new_F124S" and lane=="Wingless" else None),
        "depth":{str(d):{"pairs":0,"paired":0} for d in (7,8,9)},
        "cases":[]}
            for name in arms}
    exact=role_only=0
    for vec in source.VECTORS:
        for seed in source.COHORTS[lane][phase]:
            p,n=source.build(lane,seed,vec,phase)
            need(source.public_routes(p)==1 and
                 source.public_routes(n)==0,"ORACLE_ADMISSION")
            exact+=1
            role_only+=int(source.public_routes(p,True)>0
                           and source.public_routes(n,True)==0)
            for name in arms:
                row=report[name]
                outcomes=[]
                for graph in (p,n):
                    predicted,work=predict(lane,name,graph,base,
                                           old_r_delta,delta,fixed)
                    outcomes.append(predicted)
                    row["public_edge_scans"]+=work["public_edge_scans"]
                    row["raw_bit_ops"]+=work["raw_bit_ops"]
                    row["causal_key_comparisons"]+=work.get("causal_key_comparisons",0)
                    row["max_active"]=max(row["max_active"],
                                          work.get("max_active",0))
                    row["max_retained"]=max(row["max_retained"],
                                            work.get("max_retained",0))
                    if name=="new_F124S" and lane=="Wingless":
                        need(work["serialized_state_payload_bytes"]==10 and
                             work["reference_serialized_state_payload_bytes"]==40
                             and work["state_limit"]==3,
                             "PACKED_STATE_BUDGET_DRIFT")
                correct=bool(outcomes[0] and not outcomes[1])
                depth=str(len(p["roles"]))
                row["pairs"]+=1
                row["paired"]+=int(correct)
                row["positive_correct"]+=int(outcomes[0])
                row["negative_correct"]+=int(not outcomes[1])
                row["false_positive"]+=int(outcomes[1])
                row["false_negative"]+=int(not outcomes[0])
                row["depth"][depth]["pairs"]+=1
                row["depth"][depth]["paired"]+=int(correct)
                row["cases"].append(new.digest({
                    "lane":lane,"phase":phase,"seed":seed,"vector":vec,
                    "arm":name,"pos":outcomes[0],"neg":outcomes[1],
                    "depth":int(depth)}))
    need(exact==48 and role_only==0,"FULL_POSITIVE_NEGATIVE_DENOMINATOR")
    for name,row in report.items():
        need(row["pairs"]==48 and len(row["cases"])==48
             and row["execution_errors"]==0
             and all(r["pairs"]==16 for r in row["depth"].values())
             and row["max_retained"]<=9 and
             (row["max_active"]<=7 if lane=="Yggdrasil"
              else row["max_active"]<=192),
             "COMPLETE_MODEL_PAIR_AND_MEMORY_BOUNDS")
    fixed_work=report["strong_fixed"]
    candidate=report["new_F124S"]
    compare={
       "serialized_candidate_bytes_per_Wingless_state":
         (10 if lane=="Wingless" else None),
       "serialized_reference_bytes_per_Wingless_state":
         (40 if lane=="Wingless" else None),
       "only_logical_serialized_payload_not_heap_bytes":True,
       "candidate_edge_scans":candidate["public_edge_scans"],
       "fixed_edge_scans":fixed_work["public_edge_scans"],
       "candidate_raw_bit_ops":candidate["raw_bit_ops"],
       "fixed_raw_bit_ops":fixed_work["raw_bit_ops"],
       "operation_proxy_matched":(
          candidate["public_edge_scans"]<=fixed_work["public_edge_scans"]
          and candidate["raw_bit_ops"]<=fixed_work["raw_bit_ops"]),
       "candidate_accuracy_above_fixed":candidate["paired"]>fixed_work["paired"],
       "equal_information_capacity_proven":False,
       "wall_clock_matched_proven":False,
       "scientific_resource_matched_superiority_proven":False}
    return {"phase":phase,"pairs":48,"exact_symbolic_paired":exact,
            "role_only_paired":role_only,"arms":report,
            "resource_comparison":compare}


def collect(o_path,r_path):
    p=protocol()
    weights=parents(o_path,r_path)
    fixed=old_validator.clone_single_validator(
        old_fixed.fixed_comparator,"graph")
    fitted={}
    failures={}
    for lane in ("Wingless","Yggdrasil"):
        print("F124S_FIT_BEGIN="+lane,flush=True)
        try:
            fitted[lane]=new.train(lane,weights[lane]["base"])
            print("F124S_FIT_PASS="+lane+":L2="+
                  str(fitted[lane]["weight_update_l2"]),flush=True)
        except source.Quarantined as exc:
            if str(exc)!="F124S_LEARNER_GENUINE_FIT_UPDATE_GATE":
                raise
            failures[lane]=str(exc)
            print("F124S_FIT_NEGATIVE="+lane+":"+str(exc),flush=True)
    need(len(failures)<2,"BOTH_FIT_MODELS_BLOCKED__RETAIN_RUN_FAILURE")
    out={"schema":SCHEMA,
        "exact_qualified_parent":"522601491c10ebfeb36e7dca2627ff5366b51abb",
        "preimplementation_git_blob":FREEZE_BLOB,
        "authenticated_f124o_sha256":O_SHA,
        "authenticated_f124r_sha256":R_SHA,
        "source_birth_domain":"forge/F124S/new-structure/v1/",
        "study":"NONPROTECTED_DEVELOPMENT_ONLY",
        "training_gate_negatives":len(failures),
        "both_models_trained":not bool(failures),
        "protected_cases_generated":0,"protected_first_use":False,
        "independent_accepted_science":False,
        "scientific_acceptances":0,"accepted_ref_mutations":0,
        "optimizer_promotions":0,"codex_calls":0,"paid_api_calls":0,
        "new_schedulers":0,"resource_matched_superiority_proven":False,
        "lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        if lane in failures:
            out["lanes"].append({
                "lane":lane,"training_status":"FROZEN_FIT_NEGATIVE",
                "negative":failures[lane],"training":None,
                "fit":None,"dev":None,
                "new_dev_scored":False})
            continue
        old=weights[lane]
        fit=evaluate(lane,"FIT",old["base"],
                     old["old_r_delta"],fitted[lane]["delta"],fixed)
        dev=evaluate(lane,"DEV",old["base"],
                     old["old_r_delta"],fitted[lane]["delta"],fixed)
        c=dev["arms"]
        out["lanes"].append({
            "lane":lane,"training_status":"GENUINE_FIT_PASS",
            "training":fitted[lane],"fit":fit,"dev":dev,
            "new_dev_scored":True,
            "development_verdict":(
                "ACCURACY_ABOVE_FIXED_BUT_RESOURCE_SUPERIORITY_NOT_ESTABLISHED"
                if c["new_F124S"]["paired"]>c["strong_fixed"]["paired"]
                else "LEARNED_NOT_ABOVE_STRONG_FIXED")})
    need(all(x["training"] is None or
             x["training"]["DEV_access_during_train"]==0
             for x in out["lanes"]),"DEV_TRAINING_LEAK")
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-o",required=True)
    p.add_argument("--original-r",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    target=Path(args.output)
    need(target.parent.is_dir() and not target.exists(),"IMMUTABLE_OUTPUT")
    res=collect(args.original_o,args.original_r)
    data=(json.dumps(res,sort_keys=True,indent=2)+"\n").encode()
    with target.open("xb") as f:f.write(data)
    print("F124S_DEVELOPMENT_EVIDENCE_SHA256="+hashlib.sha256(data).hexdigest())
    for lane in res["lanes"]:
        if lane["dev"] is None:
            print("F124S_DEV_NOT_SCORED="+lane["lane"])
            continue
        arms=lane["dev"]["arms"]
        print("F124S_DEV:"+lane["lane"]+
              ":new="+str(arms["new_F124S"]["paired"])+"/48"+
              ":prior_R="+str(arms["old_F124R"]["paired"])+"/48"+
              ":fixed="+str(arms["strong_fixed"]["paired"])+"/48"+
              ":work_matched="+str(lane["dev"]["resource_comparison"]
                                   ["operation_proxy_matched"]))


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
        print("F124S_QUARANTINED:"+str(exc),file=sys.stderr)
        sys.exit(1)
