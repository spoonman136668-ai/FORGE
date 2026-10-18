"""F124-AG blinded frozen O/U against original exact, tolerant and noisy-consistency controls.

Historical learned original Python bytecode is preserved; only public source
validation global is rebound. The new fixed controls use ORIGINAL three-field
node/raw16/score cells and <=7 active +9 retained. Consistency control
encodes a 4-bit first mismatch INDEX in the pre-existing score scalar.
No control consults a label, source family, future truth, or evaluator oracle.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from types import FunctionType,SimpleNamespace
import f124ag_noisy_source as source
import f124af_fixed_controls as AF
import f124ad_intermediate_credit as AD
import f124h_train_receipt as H
import f124v_yggdrasil_causal_trace as V
import f124o_native_learners as O

SCHEMA="forge.research.f124ag.blind-noisy-consistency-evidence.v1"
FAMILIES=source.FAMILIES
ARMS=("O_original","O_combined","U_original","U_combined")
CONTROLS=("fixed_exact16","fixed_tolerant15","fixed_consistency16","H12")
GAMMA=.1
PENALTY=1.

def original_forward():
    original=AD.forward
    env=dict(original.__globals__)
    env["source"]=source
    out=FunctionType(original.__code__,env,original.__name__,
                     original.__defaults__,original.__closure__)
    source.need(out.__code__ is original.__code__,
                "FIT_MODEL_BYTECODE_IDENTITY")
    return out

def H12():
    original=H.fixed_comparator
    env=dict(original.__globals__)
    env["graph"]=SimpleNamespace(validate=source.validate_public)
    out=FunctionType(original.__code__,env,original.__name__,
                     original.__defaults__,original.__closure__)
    source.need(out.__code__ is original.__code__,
                "STRONG_HISTORICAL_BYTECODE_IDENTITY")
    return out

def exact_control():
    original=AF.bounded_exact16
    env=dict(original.__globals__)
    env["source"]=source
    out=FunctionType(original.__code__,env,original.__name__,
                     original.__defaults__,original.__closure__)
    source.need(out.__code__ is original.__code__,
                "PREDECESSOR_FIXED16_BYTECODE_IDENTITY")
    return out

def bounded_public_control(graph,rule):
    """Competing weak tolerance and strong two-error consistency policies.

    Role/edge scans remain identical. Maximum persistent state 16 original
    node/key/score records; no new metadata. Float score encodes first
    observed error bit 1..16 or completed double agreement as -1.
    """
    source.validate_public(graph)
    source.need(rule in ("tolerant15","consistency16"),"CONTROL_RULE")
    edges=O.sorted_edges(graph)
    active=[(graph["start"],None,0.)];retained=[]
    scans=bits=0
    max_cells=1
    for role in graph["roles"]:
        candidates=[]
        for node,carried,score in active+retained:
            for e in edges:
                scans+=1
                if e["from"]!=node or e["role"]!=role:continue
                differences=source.diff_bits(carried,e["src_bits"])
                if carried is not None:bits+=16
                if len(differences)>1:continue
                if rule=="tolerant15":
                    newscore=score+1.
                else:
                    if differences:
                        bit=differences[0]
                        if score==0.:
                            newscore=float(bit+1)
                        elif score>0. and bit==int(score)-1:
                            newscore=-1.
                        else:
                            continue
                    else:newscore=score
                candidates.append((e["to"],tuple(e["dst_bits"]),newscore))
        # Destination-diverse active quota, deterministic and public.
        # Prefer already-consistent proof when present; otherwise the first
        # public node/key in lexical ordering. This is FIXED, not trained.
        candidates.sort(key=lambda c:(0 if c[2]==-1. else 1,c[0],c[1],c[2]))
        winners=[];seen=set()
        for c in candidates:
            if c[0] in seen:continue
            seen.add(c[0]);winners.append(c)
            if len(winners)==7:break
        selected={id(x) for x in winners}
        for c in candidates:
            if len(winners)==7:break
            if id(c) not in selected:winners.append(c)
        selected={id(x) for x in winners}
        active=winners[:7]
        retained=[c for c in candidates if id(c) not in selected][:9]
        max_cells=max(max_cells,len(active)+len(retained))
        source.need(len(active)<=7 and len(retained)<=9
                    and max_cells<=16,"FIXED_CONTROL_EXCEEDED_7_PLUS_9")
    state=active+retained
    if rule=="consistency16":
        answer=any(n==graph["target"] and score==-1. for n,_,score in state)
    else:
        answer=any(n==graph["target"] for n,_,_ in state)
    return {"prediction":answer,"blocked":False,"actual_cell_peak":max_cells,
            "edge_scans":scans,"raw_bit_comparisons":bits}

def control_result(name,g):
    if name=="fixed_exact16":
        return exact_control()(g)
    if name=="fixed_tolerant15":
        return bounded_public_control(g,"tolerant15")
    if name=="fixed_consistency16":
        return bounded_public_control(g,"consistency16")
    if name=="H12":
        fn=H12()
        return AF.H12(g,fn)
    raise ValueError("NOT_ORIGINAL_FROZEN_CONTROL")

def model_result(arm,g,weights,fn=None):
    fn=fn or original_forward()
    model,variant=arm.split("_",1)
    kw={} if variant=="original" else {"gamma":GAMMA,"penalty":PENALTY}
    return fn(model,g,weights,**kw)

def cohort(family,phase):
    items=[(seed,list(v),*source.build(family,seed,v,phase))
        for v in source.VECTORS for seed in source.COHORTS[family][phase]]
    source.need(len(items)==48,"INDEPENDENT_SOURCE_48")
    return items

def collect(phase,weights):
    model=original_forward()
    data={}
    for family in FAMILIES:
        cases=cohort(family,phase)
        results={arm:{"correct":0,"FP":0,"FN":0,
               "by_depth":{str(d):{"pairs":0,"correct":0,"FP":0,"FN":0}
                           for d in (10,11,12)},"cases":[]} for arm in ARMS}
        controls={name:{"correct":0,"FP":0,"FN":0,"blocked_pairs":0,
                 "max_cells":0,"total_scans":0,"total_bit_compares":0,"cases":[]}
                  for name in CONTROLS}
        for seed,v,pos,neg in cases:
            # Blind score ALL competing algorithms before semantic route
            # verification. The source constructor's admission is disjoint.
            predictions={name:(model_result(name,pos,weights,model),
                               model_result(name,neg,weights,model)) for name in ARMS}
            fixed={name:(control_result(name,pos),control_result(name,neg))
                   for name in CONTROLS}
            semantic={"positive":source.routes(pos,"consistency"),
                      "negative":source.routes(neg,"consistency"),
                      "exact_pos":source.routes(pos,"exact16"),
                      "exact_neg":source.routes(neg,"exact16"),
                      "tolerant_pos":source.routes(pos,"tolerant15"),
                      "tolerant_neg":source.routes(neg,"tolerant15")}
            source.need(semantic=={"positive":1,"negative":0,
                          "exact_pos":0,"exact_neg":0,
                          "tolerant_pos":1,"tolerant_neg":1},
                        "LABEL_ADMISSION_AFTER_BLIND_PREDICTION")
            for name,(p,n) in predictions.items():
                truth=bool(p["prediction"] and not n["prediction"])
                rec=results[name]
                rec["correct"]+=int(truth)
                rec["FP"]+=int(n["prediction"])
                rec["FN"]+=int(not p["prediction"])
                depth=str(len(pos["roles"]))
                d=rec["by_depth"][depth]
                d["pairs"]+=1;d["correct"]+=int(truth)
                d["FP"]+=int(n["prediction"]);d["FN"]+=int(not p["prediction"])
                source.need(p["final_active"]<=7 and p["final_retained"]<=9
                      and n["final_active"]<=7 and n["final_retained"]<=9,
                      "ORIGINAL_MODEL_STATE_OVER_16")
                rec["cases"].append({"seed":seed,"vector":v,"depth":int(depth),
                    "paired_correct":truth,"positive_pred":bool(p["prediction"]),
                    "negative_pred":bool(n["prediction"]),
                    "positive_logit_hex":p["logit_hex"],
                    "negative_logit_hex":n["logit_hex"],
                    "positive_terminal_cells":p["terminal_target_cell_count"],
                    "negative_terminal_cells":n["terminal_target_cell_count"],
                    "positive_state_count":p["final_active"]+p["final_retained"],
                    "negative_state_count":n["final_active"]+n["final_retained"]})
            for name,(p,n) in fixed.items():
                rec=controls[name]
                blocked=bool(p["blocked"] or n["blocked"])
                rec["blocked_pairs"]+=int(blocked)
                if not blocked:
                    good=p["prediction"] and not n["prediction"]
                    rec["correct"]+=int(good)
                    rec["FP"]+=int(n["prediction"])
                    rec["FN"]+=int(not p["prediction"])
                    rec["total_scans"]+=(p["edge_scans"]+n["edge_scans"])
                    rec["total_bit_compares"]+=(
                        p["raw_bit_comparisons"]+n["raw_bit_comparisons"])
                    rec["max_cells"]=max(rec["max_cells"],
                        p.get("actual_cell_peak",0),n.get("actual_cell_peak",0))
                rec["cases"].append({"seed":seed,"vector":v,
                    "positive":p,"negative":n,
                    "paired_correct":bool(p["prediction"] and not n["prediction"])
                         if not blocked else None})
        for arm,rec in results.items():
            source.need(len(rec["cases"])==48 and
                 all(d["pairs"]==16 for d in rec["by_depth"].values()),
                 "DEVELOPMENT_DENOMINATORS")
            rec["pairs"]=48
        for name,rec in controls.items():
            rec["pairs"]=48
            source.need(len(rec["cases"])==48,"FIXED_CONTROL_DENOMINATOR")
        data[family]={"models":results,"controls":controls,
          "H12_qualified":controls["H12"]["blocked_pairs"]<=2,
          "bounded_exact_qualified":controls["fixed_exact16"]["blocked_pairs"]==0,
          "fixed_consistency_qualified":controls["fixed_consistency16"]["blocked_pairs"]==0,
          "learned_superiority":{
             model:(results[model+"_combined"]["correct"]>
                    results[model+"_original"]["correct"] and
                    results[model+"_combined"]["correct"]>
                    controls["fixed_consistency16"]["correct"] and
                    results[model+"_combined"]["FP"]==0)
             for model in ("O","U")}}
    return data

def main():
    ap=argparse.ArgumentParser()
    for n in ("o","r","s","u"):ap.add_argument("--original-"+n,required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    source.frozen()
    w=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    fit=collect("FIT",w)
    dev=collect("DEV",w)
    result={"schema":SCHEMA,"freeze_blob":source.PROTOCOL_BLOB,
      "f124ad_frozen_coefficients":{"gamma":GAMMA,"penalty":PENALTY},
      "old_O_U_fitted_weights_unchanged":True,
      "original_forward_bytecode_unchanged":True,
      "DEV_never_used_for_training":True,
      "original_seven_active_nine_retained":True,
      "FIT":fit,"DEV":dev,"protected_first_use":False,
      "independent_science_accepted":False,"optimizer_promoted":False}
    output=Path(a.output)
    source.need(output.parent.is_dir() and not output.exists(),"EXCLUSIVE_OUTPUT")
    raw=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with output.open("xb") as f:f.write(raw)
    print("F124AG_TRANSFER_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
    for family,rec in dev.items():
        for arm,v in rec["models"].items():
            print("F124AG_DEV_"+family+"_"+arm+":paired="+
                str(v["correct"])+"/48:FP="+str(v["FP"])+":FN="+str(v["FN"]),
                flush=True)
        for name,v in rec["controls"].items():
            print("F124AG_FIXED_"+family+"_"+name+":paired="+
                str(v["correct"])+"/48:FP="+str(v["FP"])+":FN="+
                str(v["FN"])+":blocked="+str(v["blocked_pairs"]),flush=True)
        for name,v in rec["learned_superiority"].items():
            print("F124AG_SUPERIOR_"+family+"_"+name+"="+str(v),flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,TypeError,KeyError,ArithmeticError) as e:
        print("F124AG_QUARANTINE="+str(e),file=sys.stderr);sys.exit(1)
