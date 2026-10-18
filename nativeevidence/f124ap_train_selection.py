"""F124-AP source-authenticated TRAIN-only candidate selection.

All source-of-truth checks happen in evaluator code; hidden transformation,
operator family and graph label are NEVER passed to the model. DEV creation
explicitly disallowed by source adapter and has no path from this module.
Original AO scientific negative is checked, not retuned.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import f124ap_frozen_train_source as source
import f124ap_dual_kernel_learner as y
import f124ap_one_packed_hop_evidence as w
import f124ao_training_evidence as previous
import f124q_independent_binding as q

SCHEMA="forge.research.f124ap.authentic-train-only-kernel-and-hop-selection.v1"
PARENT_AO_RAW="37d61d2130fc73f28fd96d32b85d018dee231c5319dd515b2024132f7855cb52"
PARENT_AO_FREEZE="e30c39911fe9aee5af48c1d94233c5a5402b99bc"

def need(ok,name):source.need(ok,"TRAIN_"+name)

def foundation(o,t,an,ao):
    base,delta,an_previous=previous.identity(o,t,an)
    raw=Path(ao).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==PARENT_AO_RAW,
         "QUALIFIED_AO_RAW_BYTES")
    r=json.loads(raw)
    need(r["schema"]=="forge.research.f124ao.frozen-first-dev-source-backed-outcome.v1"
         and r["mode"]=="dev" and r["period"]=="DEV"
         and r["frozen_selection_blob"]==PARENT_AO_FREEZE
         and r["original_train_raw_sha256"]==
              "40d21628aa38ebad9e26f1ebcb4ee918bd60aba58b19fe065eb54bc0062f6217"
         and r["no_DEV_selection_or_retuning"]
         and not r["protected_first_use"] and
         not r["independent_science_acceptance"] and
         not r["optimizer_promotion"] and not r["production_activation"]
         and len(r["lanes"])==2,"ORIGINAL_AO_RETAINED_NO_PROMOTION")
    for lane in r["lanes"]:
        need(lane["pairs"]==48 and not lane["strict_scientific_win"],
             "ORIGINAL_AO_NEGATIVE_AND_DENOMINATOR")
    return base,delta,r

def diagnostic(cases):
    correct_p=correct_n=corrupted=literal=0
    fam={k:0 for k in source.FAMILIES}
    truth=source.parent.parent.am.old.prior.parent.original.parent.prior.parent.routes15
    for seed,vec,family,operator,nonce,p,n in cases:
        a=source.plain(p,operator,nonce)
        b=source.plain(n,operator,nonce)
        relax=family=="rotate4_tolerant"
        correct_p+=int(truth(a,relaxed=relax)==1)
        correct_n+=int(truth(b,relaxed=relax)==0)
        corrupted+=int(sum(source.relation(d["input_bits"],operator)!=
                           d["output_bits"] for d in p["demos"])==3)
        literal+=int(truth(
            {k:p[k] for k in ("start","target","roles","edges")},
            relaxed=True)>0)
        fam[family]+=1
    need(len(cases)==48 and correct_p==48 and correct_n==48 and
         corrupted==48 and literal==0 and
         all(v==12 for v in fam.values()),"ORIGINAL_GRAPH_ORACLE_TRAIN_ONLY")
    return {"pairs":48,"positive_truths":correct_p,
            "negative_truths":correct_n,
            "three_corrupted_demos":corrupted,
            "old_literal_shortcuts":literal,"by_family":fam}

def train(o,t,an,ao):
    source.frozen()
    base,delta,parent=foundation(o,t,an,ao)
    ya=source.pairs("Yggdrasil","TRAIN")
    wi=source.pairs("Wingless","TRAIN")
    ydiag=diagnostic(ya)
    wdiag=diagnostic(wi)
    yy,yg=y.select(ya,base["Yggdrasil"],delta["Yggdrasil"])
    # Source-only inverse: all Wingless candidates get IDENTICAL restored graphs.
    certified=[(q.digest([seed,list(vec),family]),family,
                source.plain(p,op,nonce),source.plain(n,op,nonce))
               for seed,vec,family,op,nonce,p,n in wi]
    ww,wg=w.select(certified,base["Wingless"],delta["Wingless"])
    need(len(yg)==16 and len(wg)==7 and yy in yg and ww in wg and
         ww["strict_train_preservation"],"PRESELECTED_ALL_CANDIDATES")
    return {"schema":SCHEMA,
        "frozen_source_blob":source.FREEZE_BLOB,
        "parent_AO_original_raw_sha256":PARENT_AO_RAW,
        "source":{"Yggdrasil":ydiag,"Wingless":wdiag},
        "selected":{"Yggdrasil":yy,"Wingless":ww},
        "train_grid":{"Yggdrasil":yg,"Wingless":wg},
        "original_model_identity":{
            lane:{"base_sha256":q.digest(base[lane]),
                  "delta_sha256":q.digest(delta[lane])}
            for lane in ("Yggdrasil","Wingless")},
        "dev_cases_generated":0,"dev_source_touched":False,
        "selection_used_only_TRAIN_labels":True,
        "source_oracle_not_model_input":True,
        "wingless_true_normalization_evaluator_only":True,
        "ygg_original_seven_active_nine_retained":True,
        "wing_original_one_12bit_packed_state_per_node":True,
        "transient_kernel_memory_disclosed":True,
        "protected_first_use":False,
        "independent_science_acceptance":False,
        "optimizer_promotion":False,
        "production_activation":False,
        "accepted_ref_mutation":False}

def main():
    ap=argparse.ArgumentParser()
    for k in ("o","t","an","ao","output"):ap.add_argument("--"+k,required=True)
    a=ap.parse_args()
    dst=Path(a.output)
    need(dst.parent.is_dir() and not dst.exists(),
         "APPEND_ONLY_ORIGINAL_TRAIN_OUTPUT")
    report=train(a.o,a.t,a.an,a.ao)
    raw=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with dst.open("xb") as f:f.write(raw)
    print("F124AP_ORIGINAL_TRAIN_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in ("Yggdrasil","Wingless"):
        print("F124AP_TRAIN_"+lane+"="+json.dumps(report["selected"][lane],sort_keys=True))
    print("F124AP_DEV_CASES_GENERATED=0")
    print("F124AP_SCIENCE_ACCEPTED=false")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as error:
        print("F124AP_FAIL_CLOSED:"+str(error),file=sys.stderr)
        sys.exit(1)
