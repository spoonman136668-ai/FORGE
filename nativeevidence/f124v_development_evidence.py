"""F124-V: genuine original-receipt custody and fresh-development A/B measurements.

All comparator weights/deltas from authenticated original artifacts.
No modified F124-O/T/U, no training on FIT/DEV, no DEV selection/retune.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import f124v_collision_centered as v
import f124u_development_evidence as earlier
import f124u_interventions as u
import f124q_independent_binding as q
import f124p_frozen_variants as p
import f124o_native_learners as original
import f124q_fresh_source as source

SCHEMA="forge.research.f124v.fresh-equal-capacity-centered-evidence-dev.v1"
U_SHA="63a2a57973444752d4002bc4718ec63de88a26ed05142627305de3a94fa9fb41"
ARMS={
 "Wingless":("original_O","P_uniform","T_anchored","U_readout","new_collision","fixed_12of16"),
 "Yggdrasil":("original_O","P_no_retained","T_anchored","T_neutral","U_uncentered","new_centered","fixed_12of16")
}


def need(cond,code):
    v.need(cond,"REPORT_"+code)


def authenticate(o_path,t_path,u_path):
    base,deltas=earlier.authenticated(o_path,t_path)
    raw=Path(u_path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==U_SHA,"AUTHENTIC_F124U_RAW_RECEIPT")
    old=json.loads(raw)
    need(old["schema"]=="forge.research.f124u.authentic-fresh-fit-calibrated-cell-interventions.v1"
         and old["frozen_protocol_git_blob"]=="204b4dc051607aa9a30307875bcafb1d188426a2"
         and old["original_t_receipt_sha256"]==earlier.T_SHA
         and old["original_o_receipt_sha256"]==earlier.O_SHA
         and old["source_fresh_fit_and_dev"] and old["t_negative_untouched"]
         and old["models_retrained"] is False and old["protected_first_use"] is False
         and old["independent_scientific_acceptance"] is False
         and old["optimizer_promotion"] is False and old["accepted_ref_mutations"]==0
         and len(old["lanes"])==2,
         "PARENT_NEGATIVE_AND_CUSTODY")
    for lane,oldrow in zip(("Wingless","Yggdrasil"),old["lanes"]):
        name="new_fit_readout" if lane=="Wingless" else "new_cell_value"
        need(oldrow["lane"]==lane
             and oldrow["candidate"]==name
             and oldrow["DEV"]["arms"][name]["paired"]==
                 (38 if lane=="Wingless" else 0)
             and oldrow["DEV"]["arms"]["f124t_unchanged"]["paired"]==
                 (38 if lane=="Wingless" else 36)
             and oldrow["DEV"]["arms"]["strong_fixed"]["paired"]==
                 (40 if lane=="Wingless" else 43)
             and oldrow["unchanged_trained_delta_sha256"]==q.digest(deltas[lane]),
             "HISTORICAL_NEGATIVE_PRESERVED")
    return base,deltas


def predict(lane,arm,g,base,delta,fixed):
    if arm=="fixed_12of16":
        pred,w=fixed(g)
        return bool(pred),{"public_edge_scans":w["public_edge_scans"],
                           "raw_bit_ops":w["bit_comparisons"],
                           "max_active":0,"max_retained":0}
    if arm=="original_O":
        logit,work=original.forward(lane,g,list(base))
    elif arm in ("P_uniform","P_no_retained"):
        scope="ablate_compression" if lane=="Wingless" else "ablate_secondary"
        logit,work=p.variant_forward(lane,scope,g,list(base))
    elif arm in ("T_anchored","U_readout"):
        logit,work=q.forward(lane,g,list(base),list(delta))
        # Original authentic U FIT chose exactly zero Wingless readout bias.
    elif arm=="T_neutral":
        logit,work=q.forward(lane,g,list(base),[0.,0.])
    elif arm=="U_uncentered":
        logit,work=u.yggdrasil_value_intervention(g,list(base),list(delta))
    elif arm=="new_collision":
        need(lane=="Wingless","WINGLESS_ONLY")
        logit,work=v.wingless_collision_reassignment(g,base,delta)
    elif arm=="new_centered":
        need(lane=="Yggdrasil","YGGDRASIL_ONLY")
        logit,work=v.yggdrasil_centered_evidence(g,base,delta)
    else:
        v.need(False,"UNKNOWN_ARM")
    return bool(logit>=0),work


def score(lane,phase,base,delta,fixed):
    names=ARMS[lane]
    result={n:{"pairs":0,"paired":0,"false_negative":0,"false_positive":0,
               "public_edge_scans":0,"raw_bit_ops":0,"max_active":0,
               "max_retained":0,"evictions":0,
               "extra_centering_operations":0,
               "compression_levels":5 if n=="new_collision" else None,
               "depth":{str(d):{"pairs":0,"paired":0} for d in (7,8,9)},
               "case_sha256":[]} for n in names}
    exact=role=0
    for seed,vec,pos,neg in v.pairs(lane,phase):
        exact+=int(source.public_routes(pos)==1 and source.public_routes(neg)==0)
        role+=int(source.public_routes(pos,True)>0 and source.public_routes(neg,True)==0)
        depth=str(len(pos["roles"]))
        for name in names:
            yes,py=predict(lane,name,pos,base,delta,fixed)
            no,pn=predict(lane,name,neg,base,delta,fixed)
            row=result[name]
            pair=bool(yes and not no)
            row["pairs"]+=1
            row["paired"]+=int(pair)
            row["false_negative"]+=int(not yes)
            row["false_positive"]+=int(no)
            row["depth"][depth]["pairs"]+=1
            row["depth"][depth]["paired"]+=int(pair)
            for attr in ("public_edge_scans","raw_bit_ops","evictions"):
                row[attr]+=py.get(attr,0)+pn.get(attr,0)
            row["extra_centering_operations"]+=(
                py.get("centered_arithmetic",0)+pn.get("centered_arithmetic",0))
            row["max_active"]=max(row["max_active"],py.get("max_active",0),pn.get("max_active",0))
            row["max_retained"]=max(row["max_retained"],py.get("max_retained",0),pn.get("max_retained",0))
            row["case_sha256"].append(q.digest({
                "lane":lane,"phase":phase,"seed":seed,"vector":vec,"arm":name,
                "positive_predicted":yes,"negative_predicted":no,"paired":pair}))
    need(exact==48 and role==0,"SOURCE_EXACT_VS_ROLE_ONLY")
    for arm,row in result.items():
        need(row["pairs"]==48 and len(row["case_sha256"])==48
             and all(d["pairs"]==16 for d in row["depth"].values())
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil" else row["max_active"]<=192),
             "MEMORY_DENOMINATOR_AND_SOURCE")
    return {"phase":phase,"pairs":48,"reference_exact_paired":48,
            "role_only_paired":0,"arms":result}


def run(original_o,original_t,original_u):
    spec=v.frozen()
    base,deltas=authenticate(original_o,original_t,original_u)
    fixed=earlier.parent.original_adapter.clone_single_validator(
        earlier.previous.old_control.fixed_comparator,"graph")
    report={"schema":SCHEMA,"freeze_blob":v.FREEZE_BLOB,
            "qualified_parent_head":"6ba96aaaeff083a5e2f54020c70d2a717e431a10",
            "original_o_receipt_sha256":earlier.O_SHA,
            "original_t_receipt_sha256":earlier.T_SHA,
            "original_u_negative_sha256":U_SHA,
            "original_weights_and_prior_failures_unchanged":True,
            "DEV_evaluated_after_all_methods_frozen":True,
            "new_training_steps":0,"scientific_acceptance":False,
            "optimizer_promotion":False,"protected_cases_generated":0,
            "accepted_ref_mutations":0,"resource_matched_superiority_proven":False,
            "paid_api_or_codex_calls":0,
            "lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        fit=score(lane,"FIT",base[lane],deltas[lane],fixed)
        dev=score(lane,"DEV",base[lane],deltas[lane],fixed)
        name="new_collision" if lane=="Wingless" else "new_centered"
        verdict=("NEW_ABOVE_FIXED_UNMATCHED_COST_DEV_ONLY"
                 if dev["arms"][name]["paired"]>dev["arms"]["fixed_12of16"]["paired"]
                 else "NEGATIVE_OR_TIE_BELOW_FIXED")
        report["lanes"].append({
           "lane":lane,"source_born_unique":True,"no_extra_capacity":True,
           "unchanged_original_delta_sha256":q.digest(deltas[lane]),
           "fit":fit,"dev":dev,"new_arm":name,
           "frozen_mechanism_dev_verdict":verdict,
           "inference_budget":{"active":7,"retained":9}
               if lane=="Yggdrasil" else {"per_public_node":3,"total":192},
           "resource_matched_superiority_proven":False})
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--o",required=True)
    parser.add_argument("--t",required=True)
    parser.add_argument("--u",required=True)
    parser.add_argument("--output",required=True)
    a=parser.parse_args()
    destination=Path(a.output)
    need(destination.parent.is_dir() and not destination.exists(),"NONOVERWRITE_RECEIPT")
    report=run(a.o,a.t,a.u)
    b=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with destination.open("xb") as f:f.write(b)
    print("F124V_AUTHENTIC_RECEIPT_SHA256="+hashlib.sha256(b).hexdigest())
    for row in report["lanes"]:
        stats=row["dev"]["arms"]
        print("F124V_DEV="+row["lane"]+":new="+str(stats[row["new_arm"]]["paired"])+
              "/48:T="+str(stats["T_anchored"]["paired"])+
              "/48:fixed="+str(stats["fixed_12of16"]["paired"])+"/48")


if __name__=="__main__":
    try:main()
    except (OSError,TypeError,ValueError,KeyError,ArithmeticError) as ex:
        print("F124V_QUARANTINED:"+str(ex),file=sys.stderr)
        sys.exit(1)
