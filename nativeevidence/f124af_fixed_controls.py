"""F124-AF untouched source-frozen F124-AD O/U versus two executable controls.

Historical O/U learner Python bytecode is reused without editing by rebinding
ONLY its original source validation module to new public graph admission.
Original F124H 12/16 comparator Python bytecode is also preserved.
A bounded fixed exact16 comparator enforces original 7 active+9 retained
three-field cells and same public role/edge passes. Never use path oracle
in model predictions. It is not assumed compute identical without cost data.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from types import FunctionType,SimpleNamespace
import f124af_sparse_source as source
import f124ad_intermediate_credit as AD
import f124h_train_receipt as H
import f124v_yggdrasil_causal_trace as V
import f124o_native_learners as O

SCHEMA="forge.research.f124af.sparse-automata-evidence.v1"
FAMILIES=source.FAMILIES
ARMS=("O_original","O_combined","U_original","U_combined")
GAMMA=.1;PENALTY=1.

def prior_model():
    orig=AD.forward
    globals_=dict(orig.__globals__)
    globals_["source"]=source
    fn=FunctionType(orig.__code__,globals_,orig.__name__,
                    orig.__defaults__,orig.__closure__)
    source.need(fn.__code__ is orig.__code__ and
                globals_["source"] is source,"ORIGINAL_BYTECODE_CHANGED")
    return fn

def historical_H12():
    orig=H.fixed_comparator
    globals_=dict(orig.__globals__)
    globals_["graph"]=SimpleNamespace(validate=source.validate_public)
    fn=FunctionType(orig.__code__,globals_,orig.__name__,
                    orig.__defaults__,orig.__closure__)
    source.need(fn.__code__ is orig.__code__,"H12_CONTROL_BYTECODE_CHANGED")
    return fn

def bounded_exact16(g):
    """Source-independent fixed exact public continuation, no hidden truth.

    Same three fields per persistent cell as original (node,raw16,score),
    at most seven active plus nine retained. Uses exact 16 comparisons on
    each matched candidate and scans the original edge inventory in the
    same outer loop; if capacity becomes insufficient, report ordinary
    misses, NOT an oracle-guided recovery.
    """
    source.validate_public(g)
    edges=O.sorted_edges(g)
    active=[(g["start"],None,0.)];retained=[]
    scans=bits=0
    max_cells=1
    for role in g["roles"]:
        candidates=[]
        for node,carried,score in active+retained:
            for e in edges:
                scans+=1
                if e["from"]!=node or e["role"]!=role:continue
                if carried is not None:
                    bits+=16
                    exact=sum(x==y for x,y in zip(carried,e["src_bits"]))==16
                    if not exact:continue
                candidates.append((e["to"],tuple(e["dst_bits"]),score+1.))
        candidates.sort(key=lambda c:(-c[2],c[0],c[1]))
        winners=[];seen=set()
        for candidate in candidates:
            if candidate[0] not in seen:
                seen.add(candidate[0]);winners.append(candidate)
                if len(winners)==7:break
        selected={id(x) for x in winners}
        for candidate in candidates:
            if len(winners)==7:break
            if id(candidate) not in selected:winners.append(candidate)
        selected={id(x) for x in winners}
        active=winners[:7]
        retained=[x for x in candidates if id(x) not in selected][:9]
        max_cells=max(max_cells,len(active)+len(retained))
        source.need(len(active)<=7 and len(retained)<=9
             and max_cells<=16,"FIXED_CONTROL_CAPACITY")
    return {"prediction":any(x[0]==g["target"] for x in active+retained),
      "actual_cell_peak":max_cells,"edge_scans":scans,
      "raw_bit_comparisons":bits,"blocked":False}

def H12(g,fn):
    try:
        pred,counts=fn(g)
        return {"prediction":bool(pred),"blocked":False,
                "edge_scans":counts["public_edge_scans"],
                "raw_bit_comparisons":counts["bit_comparisons"]}
    except Exception as exc:
        if "CONTROL_TRAVERSAL_BUDGET" in str(exc):
            return {"prediction":None,"blocked":True,"reason":str(exc)}
        raise

def model_output(fn,arm,g,weights):
    who,kind=arm.split("_",1)
    kw={} if kind=="original" else dict(gamma=GAMMA,penalty=PENALTY)
    return fn(who,g,weights,**kw)

def cases(phase,family):
    got=[(seed,vector,*source.build(family,seed,vector,phase))
         for vector in source.VECTORS for seed in source.COHORTS[family][phase]]
    source.need(len(got)==48,"EXACT_48_SOURCE_CASES")
    return got

def evaluate(phase,weights):
    predict=prior_model();H=historical_H12()
    out={}
    for family in FAMILIES:
        arms={name:{"correct":0,"false_positive":0,"false_negative":0,
                    "by_depth":{str(d):{"pairs":0,"correct":0,"FP":0,"FN":0}
                                for d in (10,11,12)},"cases":[]} for name in ARMS}
        fixeds={name:{"correct":0,"false_positive":0,"false_negative":0,
                  "blocked":0,"cells_peak_max":0,"edge_scans":0,"bit_comparisons":0,
                  "cases":[]} for name in ("H12","bounded_exact16")}
        for seed,vector,p,n in cases(phase,family):
            blind={name:(model_output(predict,name,p,weights),
                         model_output(predict,name,n,weights))
                   for name in ARMS}
            controls={"H12":(H12(p,H),H12(n,H)),
                      "bounded_exact16":(bounded_exact16(p),bounded_exact16(n))}
            # Only now evaluate original source-derived true path.
            source.need(source.routes(p)==1 and source.routes(n)==0,
                        "SOURCE_TRUTH_INVALID")
            for name,(positive,negative) in blind.items():
                predpos=positive["prediction"];predneg=negative["prediction"]
                correct=bool(predpos and not predneg)
                rec=arms[name]
                rec["correct"]+=int(correct)
                rec["false_positive"]+=int(predneg)
                rec["false_negative"]+=int(not predpos)
                d=rec["by_depth"][str(len(p["roles"]))]
                d["pairs"]+=1;d["correct"]+=int(correct)
                d["FP"]+=int(predneg);d["FN"]+=int(not predpos)
                source.need(positive["final_active"]<=7
                      and positive["final_retained"]<=9
                      and negative["final_active"]<=7
                      and negative["final_retained"]<=9,
                      "MODEL_PERSISTENT_BUDGET_EXCEEDED")
                rec["cases"].append({"seed":seed,"vector":list(vector),
                   "depth":len(p["roles"]),"correct":correct,
                   "positive":bool(predpos),"negative":bool(predneg),
                   "positive_logit_hex":positive["logit_hex"],
                   "negative_logit_hex":negative["logit_hex"],
                   "positive_terminal_cells":positive["terminal_target_cell_count"],
                   "negative_terminal_cells":negative["terminal_target_cell_count"],
                   "positive_active":positive["final_active"],
                   "positive_retained":positive["final_retained"]})
            for name,(positive,negative) in controls.items():
                rec=fixeds[name]
                blocked=positive["blocked"] or negative["blocked"]
                rec["blocked"]+=int(blocked)
                if not blocked:
                    ok=positive["prediction"] and not negative["prediction"]
                    rec["correct"]+=int(ok)
                    rec["false_positive"]+=int(negative["prediction"])
                    rec["false_negative"]+=int(not positive["prediction"])
                    rec["edge_scans"]+=positive["edge_scans"]+negative["edge_scans"]
                    rec["bit_comparisons"]+=(
                        positive["raw_bit_comparisons"]+
                        negative["raw_bit_comparisons"])
                    rec["cells_peak_max"]=max(rec["cells_peak_max"],
                       positive.get("actual_cell_peak",0),
                       negative.get("actual_cell_peak",0))
                rec["cases"].append({"seed":seed,"vector":list(vector),
                    "positive":positive,"negative":negative,
                    "correct":(bool(positive["prediction"] and not negative["prediction"])
                               if not blocked else None)})
        for name,rec in arms.items():
            source.need(len(rec["cases"])==48 and all(
                v["pairs"]==16 for v in rec["by_depth"].values()),
                "PER_MODEL_CASES_48_BALANCED")
            rec["pairs"]=48
            rec["source_case_sha256"]=hashlib.sha256(json.dumps(
                rec["cases"],sort_keys=True,separators=(",",":")).encode()).hexdigest()
        for name,rec in fixeds.items():
            rec["pairs"]=48
            source.need(len(rec["cases"])==48,"FIXED_CONTROL_CASES")
        # If historical comparator fails to complete >= 95%, explicitly
        # mark its fairness admission blocked; never count as a loss.
        h=fixeds["H12"]
        h["completion_admitted"]=(48-h["blocked"]>=46)
        out[family]={"arms":arms,"controls":fixeds,
              "matched_strong_H12_comparison_qualified":h["completion_admitted"],
              "frozen_combined_beats_both_controls":{
                who:(arms[who+"_combined"]["correct"]>
                         arms[who+"_original"]["correct"]
                     and arms[who+"_combined"]["correct"]>
                         fixeds["bounded_exact16"]["correct"]
                     and h["completion_admitted"]
                     and arms[who+"_combined"]["correct"]>
                         h["correct"]
                     and arms[who+"_combined"]["false_positive"]==0)
                for who in ("O","U")}}
    return out

def main():
    ap=argparse.ArgumentParser()
    for name in ("o","r","s","u"):ap.add_argument("--original-"+name,required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    source.frozen()
    weights=V.original_weights(args.original_o,args.original_r,
                               args.original_s,args.original_u)
    result={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
       "frozen_combined_coefficients":{"gamma":GAMMA,"penalty":PENALTY},
       "original_O_U_weights_unchanged":True,"DEV_never_selected":True,
       "original_16_persistent_cells_unchanged":True,
       "FIT":evaluate("FIT",weights),"DEV":evaluate("DEV",weights),
       "protected_first_use":False,"science_accepted":False,
       "optimizer_promoted":False}
    dest=Path(args.output)
    source.need(dest.parent.is_dir() and not dest.exists(),"EXCLUSIVE_EVIDENCE_FILE")
    data=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with dest.open("xb") as f:f.write(data)
    print("F124AF_TRANSFER_SHA256="+hashlib.sha256(data).hexdigest(),flush=True)
    for family,z in result["DEV"].items():
        for arm,x in z["arms"].items():
            print("F124AF_DEV_"+family+"_"+arm+
               ":paired="+str(x["correct"])+"/48:FP="+
               str(x["false_positive"])+":FN="+str(x["false_negative"]),flush=True)
        for control,x in z["controls"].items():
            print("F124AF_FIXED_"+family+"_"+control+
              ":paired="+str(x["correct"])+"/48:blocked="+
              str(x["blocked"])+":maxcells="+str(x["cells_peak_max"]),flush=True)
        print("F124AF_H12_ADMITTED_"+family+"="+str(
               z["matched_strong_H12_comparison_qualified"]),flush=True)
        for model,verdict in z["frozen_combined_beats_both_controls"].items():
            print("F124AF_STRONG_VERDICT_"+family+"_"+model+"="+
                  ("BEATS_BOTH" if verdict else "NOT_SUPERIOR_OR_UNQUALIFIED"),
                  flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,TypeError,KeyError,ArithmeticError,OSError) as e:
        print("F124AF_QUARANTINE="+str(e),file=sys.stderr);sys.exit(1)
