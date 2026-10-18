"""F124-U: authenticated, newly sourced FIT and DEV without training or extra cells.

The F124-T prior learned deltas remain byte-identical. Wingless calibrates
only one frozen FIT-selected logit bias; Yggdrasil uses the fixed preregistered
lookahead-to-cell-value intervention. Retain every control and cost.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import f124u_interventions as u
import f124s_development_evidence as previous
import f124q_independent_binding as q
import f124p_frozen_variants as p
import f124o_native_learners as original
import f124q_training_evidence as parent

T_SHA="a2f7b3641c2f84f684372918849170c97912c7a104fa4dbe264bcbd6d444c2d2"
O_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
SCHEMA="forge.research.f124u.authentic-fresh-fit-calibrated-cell-interventions.v1"
ARMS={
 "Wingless":("original_F124O","f124p_uniform","f124t_unchanged","new_fit_readout","strong_fixed"),
 "Yggdrasil":("original_F124O","f124p_no_retention","f124t_unchanged","f124t_neutral","new_cell_value","strong_fixed")
}


def need(ok,label):
    u.need(ok,"EVIDENCE_"+label)


def authenticated(o_path,t_path):
    raw_o=Path(o_path).read_bytes()
    raw_t=Path(t_path).read_bytes()
    need(hashlib.sha256(raw_o).hexdigest()==O_SHA,"ORIGINAL_RECEIPT_HASH")
    need(hashlib.sha256(raw_t).hexdigest()==T_SHA,"F124T_RECEIPT_HASH")
    originals=parent.original_weights(o_path)
    receipt=json.loads(raw_t)
    need(receipt["schema"]=="forge.research.f124t.new-fresh-absolute-causal-mass-development.v1"
         and receipt["freeze_git_blob"]=="60b985282d581d51cb9b121333fb40f1024f2310"
         and receipt["qg_immutable_diagnostic_sha256"]==
             "5496084491a8f78065891181a5676d348066578b83e46e77b2ca9bda7abae1c4"
         and receipt["known_f124s_negative_retained"]
         and receipt["scientific_acceptances"]==0
         and receipt["optimizer_promotions"]==0
         and receipt["protected_examples_generated"]==0
         and receipt["resource_matched_superiority_proven"] is False
         and len(receipt["lanes"])==2,"T_NEGATIVE_AND_AUTHORITY_PRESERVED")
    deltas={}
    for idx,lane in enumerate(("Wingless","Yggdrasil")):
        row=receipt["lanes"][idx]
        train=row["FIT_training"]
        need(row["lane"]==lane
             and train["lane"]==lane
             and train["steps"]==72
             and train["fit_pairs"]==48
             and train["genuine_fit_update"]
             and row["DEV"]["pairs"]==48
             and row["FIT"]["pairs"]==48
             and train["delta_sha256"]==q.digest(train["delta"])
             and len(train["delta"])==(4 if lane=="Wingless" else 2)
             and row["DEV"]["arms"]["new_F124S"]["paired"]==
                 (38 if lane=="Wingless" else 33)
             and row["DEV"]["arms"]["fixed_12of16"]["paired"]==
                 (46 if lane=="Wingless" else 43),"ORIGINAL_FROZEN_T_QUALIFICATION")
        deltas[lane]=list(train["delta"])
    return originals,deltas


def forward(lane,arm,graph,base,delta,bias,fixed):
    if arm=="strong_fixed":
        pred,w=fixed(graph)
        work={"public_edge_scans":w["public_edge_scans"],
              "raw_bit_ops":w["bit_comparisons"],
              "max_active":0,"max_retained":0}
        return bool(pred),work
    if arm=="original_F124O":
        score,work=original.forward(lane,graph,list(base))
    elif arm in ("f124p_uniform","f124p_no_retention"):
        scope=("ablate_compression" if lane=="Wingless" else "ablate_secondary")
        score,work=p.variant_forward(lane,scope,graph,list(base))
    elif arm=="f124t_unchanged":
        score,work=q.forward(lane,graph,list(base),list(delta))
    elif arm=="f124t_neutral":
        score,work=q.forward(lane,graph,list(base),[0.,0.])
    elif arm=="new_fit_readout":
        need(lane=="Wingless","READOUT_LANE")
        score,work=q.forward(lane,graph,list(base),list(delta))
        score+=bias
    elif arm=="new_cell_value":
        need(lane=="Yggdrasil","CELL_VALUE_LANE")
        score,work=u.yggdrasil_value_intervention(graph,base,delta)
    else:
        u.need(False,"UNKNOWN_ARM")
    return bool(score>=0),work


def score_cohort(lane,phase,base,delta,bias,fixed):
    names=ARMS[lane]
    stats={arm:{
       "pairs":0,"paired":0,"positive_false_negatives":0,
       "negative_false_positives":0,"public_edge_scans":0,"raw_bit_ops":0,
       "max_active":0,"max_retained":0,
       "depth":{str(j):{"pairs":0,"paired":0} for j in (7,8,9)},
       "case_sha256":[]} for arm in names}
    validator_exact=validator_role=0
    for seed,vector,pos,neg in u.pairs(lane,phase):
        validator_exact+=int(u.source.public_routes(pos)==1 and u.source.public_routes(neg)==0)
        validator_role+=int(u.source.public_routes(pos,True)>0 and u.source.public_routes(neg,True)==0)
        depth=str(len(pos["roles"]))
        for arm in names:
            yes,wy=forward(lane,arm,pos,base,delta,bias,fixed)
            no,wn=forward(lane,arm,neg,base,delta,bias,fixed)
            paired=bool(yes and not no)
            a=stats[arm]
            a["pairs"]+=1
            a["paired"]+=int(paired)
            a["positive_false_negatives"]+=int(not yes)
            a["negative_false_positives"]+=int(no)
            a["depth"][depth]["pairs"]+=1
            a["depth"][depth]["paired"]+=int(paired)
            a["public_edge_scans"]+=wy["public_edge_scans"]+wn["public_edge_scans"]
            a["raw_bit_ops"]+=wy["raw_bit_ops"]+wn["raw_bit_ops"]
            a["max_active"]=max(a["max_active"],wy.get("max_active",0),wn.get("max_active",0))
            a["max_retained"]=max(a["max_retained"],wy.get("max_retained",0),wn.get("max_retained",0))
            a["case_sha256"].append(q.digest({
               "lane":lane,"phase":phase,"seed":seed,"vector":vector,
               "arm":arm,"paired":paired,"positive":yes,"negative":no}))
    need(validator_exact==48 and validator_role==0,"EXACT_SYMBOLIC_ADMISSION")
    for a in stats.values():
        need(a["pairs"]==48 and len(a["case_sha256"])==48 and
             all(v["pairs"]==16 for v in a["depth"].values()) and
             a["max_retained"]<=9 and
             (a["max_active"]<=7 if lane=="Yggdrasil" else a["max_active"]<=192),
             "DENOMINATOR_OR_MEMORY_BUDGET")
    return {"phase":phase,"pairs":48,"exact_symbolic_ceiling":48,
            "role_only_negative":0,"arms":stats}


def run(o_path,t_path):
    protocol=u.frozen()
    bases,deltas=authenticated(o_path,t_path)
    fixed=parent.original_adapter.clone_single_validator(
        previous.old_control.fixed_comparator,"graph")
    selected={"Wingless":0.,"Yggdrasil":0.}
    # One FIT-only preregistered Wingless bias selection; NEVER access DEV here.
    wingfit=u.pairs("Wingless","FIT")
    best,grid=u.choose_fit_bias(wingfit,bases["Wingless"],deltas["Wingless"])
    selected["Wingless"]=best["bias"]
    # F124-T immutable trained coefficients; no alternative model training.
    out={"schema":SCHEMA,"frozen_protocol_git_blob":u.FREEZE_BLOB,
         "original_o_receipt_sha256":O_SHA,"original_t_receipt_sha256":T_SHA,
         "t_negative_untouched":True,"source_fresh_fit_and_dev":True,
         "wingless_fit_grid":grid,"wingless_selected_fit":best,
         "yggdrasil_fit_bias_selected":False,
         "models_retrained":False,"additional_yggdrasil_cells":0,
         "protected_cases_generated":0,"protected_first_use":False,
         "independent_scientific_acceptance":False,
         "optimizer_promotion":False,"accepted_ref_mutations":0,
         "paid_api_or_codex_calls":0,"matched_compute_superiority_proven":False,
         "lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        fit=score_cohort(lane,"FIT",bases[lane],deltas[lane],selected[lane],fixed)
        # First DEV readback; all candidate and baseline code frozen before this line.
        dev=score_cohort(lane,"DEV",bases[lane],deltas[lane],selected[lane],fixed)
        candidate="new_fit_readout" if lane=="Wingless" else "new_cell_value"
        out["lanes"].append({
            "lane":lane,"unchanged_trained_delta_sha256":q.digest(deltas[lane]),
            "readout_bias":selected[lane],
            "FIT":fit,"DEV":dev,
            "candidate":candidate,
            "candidate_frozen_before_DEV":True,
            "retained_cell_budget":{"active":7,"retained":9} if lane=="Yggdrasil" else None,
            "negative_or_unmatched_cost":
                "ABOVE_FIXED_UNMATCHED_COST_NOT_SCIENCE"
                if dev["arms"][candidate]["paired"]>dev["arms"]["strong_fixed"]["paired"]
                else "NO_ABOVE_FIXED_DEVELOPMENT_ADVANTAGE"
        })
    return out


def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--original-o-receipt",required=True)
    arg.add_argument("--original-t-receipt",required=True)
    arg.add_argument("--output",required=True)
    args=arg.parse_args()
    target=Path(args.output)
    need(target.parent.is_dir() and not target.exists(),"RECEIPT_IMMUTABILITY")
    report=run(args.original_o_receipt,args.original_t_receipt)
    data=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with target.open("xb") as handle:handle.write(data)
    print("F124U_RECEIPT_SHA256="+hashlib.sha256(data).hexdigest())
    for lane in report["lanes"]:
        a=lane["DEV"]["arms"]
        print("F124U_DEVELOPMENT="+lane["lane"]+
              ":candidate="+str(a[lane["candidate"]]["paired"])+
              "/48:unchanged="+str(a["f124t_unchanged"]["paired"])+
              "/48:fixed="+str(a["strong_fixed"]["paired"])+"/48")


if __name__=="__main__":
    try: main()
    except (ValueError,TypeError,KeyError,OSError,ArithmeticError) as e:
        print("F124U_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)
