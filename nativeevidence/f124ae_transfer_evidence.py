"""F124-AE source-distinct F124-AD fixed-coefficient transfer and strong controls.

Models are UNMODIFIED F124-AD forward functions with FIT-trained original
O/U receipts; combined gamma=.1 penalty=1.0 is from the prior sealed
development choice, never FIT/DEV reselected here. Positive route is computed
only after every blinded model and deterministic-control output.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from types import FunctionType,SimpleNamespace

import f124ae_source as source
import f124ad_intermediate_credit as AD
import f124v_yggdrasil_causal_trace as V
import f124h_train_receipt as H

SCHEMA="forge.research.f124ae.four-family-blind-transfer.v1"
ARMS=("O_original","O_combined","U_original","U_combined")
FAMILIES=source.FAMILIES
COEFFICIENTS={"gamma":0.1,"penalty":1.0}

def strong_fixed_12of16():
    """Preserve the original F124-H comparator Python bytecode EXACTLY.

    Only its public graph validator global changes to admit independently
    registered 10–12-hop public graphs; the original 128 frontier bound
    remains, and any overflow is explicitly recorded as CONTROL_BLOCKED.
    """
    orig=H.fixed_comparator
    g=dict(orig.__globals__)
    g["graph"]=SimpleNamespace(validate=source.validate_public)
    fn=FunctionType(orig.__code__,g,orig.__name__,orig.__defaults__,orig.__closure__)
    source.need(fn.__code__ is orig.__code__, "H_FIXED_CONTROL_BYTECODE_DRIFT")
    return fn

def fixed_predict(control,g):
    try:
        prediction,counts=control(g)
        return {"prediction":bool(prediction),"status":"COMPLETE",
                "edge_scans":counts.get("public_edge_scans"),
                "bit_comparisons":counts.get("bit_comparisons")}
    except Exception as e:
        # A fixed comparison that exceeds its original width does not get
        # misrepresented as a bad classification or comparable runtime.
        if "CONTROL_TRAVERSAL_BUDGET" not in str(e):raise
        return {"prediction":None,"status":"FRONTIER_BOUND_INAPPLICABLE",
                "reason":str(e)}

def cohort(phase,family):
    cases=[]
    lane="AE_"+family
    for vector in source.VECTORS:
        for seed in source.COHORTS[lane][phase]:
            pos,neg=source.transfer_pair(seed,vector,phase,family)
            source.paired_admit(pos,neg)
            cases.append((seed,list(vector),pos,neg))
    source.need(len(cases)==48,"EXACT_FAMILY_COHORT_48")
    return cases

def compute(weights,phase):
    control=strong_fixed_12of16()
    result={}
    for family in FAMILIES:
        x={arm:{"correct":0,"false_positives":0,"false_negatives":0,
                 "path_losses":0,"by_depth":{str(d):{"pairs":0,"correct":0,
                     "false_positive":0,"false_negative":0} for d in (10,11,12)},
                 "cases":[]} for arm in ARMS}
        fixed={"pairs":0,"correct":0,"blocked_pairs":0,
               "false_positives":0,"false_negatives":0,"cases":[]}
        exact={"pairs":0,"correct":0,"cases":[]}
        for seed,vector,pos,neg in cohort(phase,family):
            blind={}
            for arm in ARMS:
                who,version=arm.split("_",1)
                kw={} if version=="original" else dict(COEFFICIENTS)
                pp=AD.forward(who,pos,weights,**kw)
                nn=AD.forward(who,neg,weights,**kw)
                blind[arm]=(pp,nn)
            fp=fixed_predict(control,pos);fn=fixed_predict(control,neg)
            ev_pos=source.public_routes(pos)==1
            ev_neg=source.public_routes(neg)==1
            exact["pairs"]+=1; exact["correct"]+=int(ev_pos and not ev_neg)
            exact["cases"].append({"seed":seed,"vector":vector,
                                    "correct":bool(ev_pos and not ev_neg)})
            fixed["pairs"]+=1
            blocked=fp["status"]!="COMPLETE" or fn["status"]!="COMPLETE"
            fixed["blocked_pairs"]+=int(blocked)
            if not blocked:
                fixed["correct"]+=int(fp["prediction"] and not fn["prediction"])
                fixed["false_positives"]+=int(fn["prediction"])
                fixed["false_negatives"]+=int(not fp["prediction"])
            fixed["cases"].append({"seed":seed,"vector":vector,
                                  "positive":fp,"negative":fn,
                                  "paired_correct":bool(fp["prediction"] and
                                         not fn["prediction"]) if not blocked else None})
            # Evaluator-only source-derived causal true path AFTER blind scores.
            route=AD.exact_positive_prefix(pos)
            for arm,(pp,nn) in blind.items():
                who,version=arm.split("_",1)
                kw={} if version=="original" else dict(COEFFICIENTS)
                observed=AD.forward(who,pos,weights,positive_prefix=route,**kw)
                source.need(observed["logit_hex"]==pp["logit_hex"],
                            "EVALUATOR_ORACLE_AFFECTED_PREDICTION")
                loss=next((h["hop"] for h in observed["hops"]
                           if h["stage"] in ("pruned","not_generated")),None)
                yp=pp["prediction"];yn=nn["prediction"]
                correct=yp and not yn
                z=x[arm];z["correct"]+=int(correct)
                z["false_positives"]+=int(yn);z["false_negatives"]+=int(not yp)
                z["path_losses"]+=int(loss is not None)
                depth=str(len(pos["roles"]))
                d=z["by_depth"][depth]
                d["pairs"]+=1;d["correct"]+=int(correct)
                d["false_positive"]+=int(yn);d["false_negative"]+=int(not yp)
                z["cases"].append({"seed":seed,"vector":vector,
                   "depth":int(depth),"positive_prediction":yp,
                   "negative_prediction":yn,"paired_correct":bool(correct),
                   "false_positive":bool(yn),"false_negative":bool(not yp),
                   "first_true_path_loss":loss,"positive_logit_hex":pp["logit_hex"],
                   "negative_logit_hex":nn["logit_hex"],
                   "positive_terminal_cells":pp["terminal_target_cell_count"],
                   "negative_terminal_cells":nn["terminal_target_cell_count"],
                   "positive_causal_hop_evidence":observed["hops"],
                   "active_cells":pp["final_active"],
                   "retained_cells":pp["final_retained"]})
                source.need(pp["final_active"]<=7 and pp["final_retained"]<=9
                         and pp["final_active"]+pp["final_retained"]<=16
                         and nn["final_active"]<=7 and nn["final_retained"]<=9,
                            "ORIGINAL_CAPACITY_EXCEEDED")
        for arm,z in x.items():
            source.need(len(z["cases"])==48
                and all(v["pairs"]==16 for v in z["by_depth"].values()),
                "48_PAIR_DENOMINATOR_AND_DEPTH")
            z["pairs"]=48
            z["case_sha256"]=hashlib.sha256(json.dumps(z["cases"],
                sort_keys=True,separators=(",",":")).encode()).hexdigest()
        source.need(fixed["pairs"]==48 and exact["pairs"]==48,
                     "FIXED_AND_EXACT_DENOMINATOR")
        result[family]={"models":x,"strong_fixed_12of16":fixed,
                        "exact_16of16_public_verifier_reference":exact,
                        "family_DEV_success_by_model":{
                          who:(x[who+"_combined"]["correct"]>
                               x[who+"_original"]["correct"] and
                               x[who+"_combined"]["false_positives"]==0)
                          for who in ("O","U")}}
    return result

def main():
    ap=argparse.ArgumentParser()
    for name in ("o","r","s","u"):ap.add_argument("--original-"+name,required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    source.frozen()
    weights=V.original_weights(a.original_o,a.original_r,
                               a.original_s,a.original_u)
    fit=compute(weights,"FIT")
    dev=compute(weights,"DEV")
    report={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
      "parameters_locked_from_f124ad":COEFFICIENTS,
      "prior_original_FIT_trained_model_weights":True,
      "original_public_destination_diversity_unchanged":True,
      "original_persistent_cells":{"active":7,"retained":9,"total":16},
      "all_families_per_phase_pairs":48,"DEV_never_selected":True,
      "FIT":fit,"DEV":dev,
      "protected_first_use":False,"independent_science_accepted":False,
      "accepted_refs_changed":False,"optimizer_promoted":False}
    output=Path(a.output)
    source.need(output.parent.is_dir() and not output.exists(),"EXCLUSIVE_OUTPUT")
    raw=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
    with output.open("xb") as f:f.write(raw)
    print("F124AE_TRANSFER_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for family in FAMILIES:
        z=dev[family]
        for arm in ARMS:
            v=z["models"][arm]
            print("F124AE_DEV_"+family+"_"+arm+
                  ":correct="+str(v["correct"])+"/48:FP="+
                  str(v["false_positives"])+":FN="+str(v["false_negatives"])+
                  ":lost="+str(v["path_losses"]),flush=True)
        ctrl=z["strong_fixed_12of16"]
        print("F124AE_FIXED_"+family+":completed="+str(48-ctrl["blocked_pairs"])+
              "/48:correct="+str(ctrl["correct"])+
              ":blocked="+str(ctrl["blocked_pairs"]),flush=True)
        for who,yes in z["family_DEV_success_by_model"].items():
            print("F124AE_VERDICT_"+family+"_"+who+"="+
                  ("DEVELOPMENT_TRANSFER_PASS" if yes else "DEVELOPMENT_NEGATIVE"),
                  flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,TypeError,KeyError,ArithmeticError) as e:
        print("F124AE_TRANSFER_QUARANTINED="+str(e),file=sys.stderr)
        sys.exit(1)
