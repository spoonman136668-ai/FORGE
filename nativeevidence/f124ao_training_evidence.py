"""F124-AO authenticated TRAIN-only candidate selection, NEVER touches DEV.

Source truth is available to the evaluator for identity checks only, after
candidate TRAIN predictions. Immutable parent O/T and AN scientific receipts
are authenticated by exact raw bytes, schema, lineage and original weights.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import f124ao_frozen_source as source
import f124ao_public_relation_learner as y
import f124ao_packed_ambiguity as w
import f124u_development_evidence as historical
import f124q_independent_binding as provenance

SCHEMA="forge.research.f124ao.authentic-train-only-frozen-selection.v1"
AN_SHA="7226e267ac02090069690ebb40e92696a2cba1bd56a567d838fc6e48880cff9c"

def need(ok,tag):source.need(ok,"TRAIN_"+tag)

def identity(original_o,original_t,an_path):
    base,delta=historical.authenticated(original_o,original_t)
    raw=Path(an_path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==AN_SHA,
         "ORIGINAL_AN_RAW_EVIDENCE")
    prior=json.loads(raw)
    need(prior["schema"]==
         "forge.research.f124an.authentic-robust-uncertainty-and-one-packed-isolation.v1"
         and prior["freeze_blob"]=="d3ad91612d2aefc4be13f94515badb6d2b4347cb"
         and prior["parent_AM_raw_sha256"]==
             "fcb5bb9825a4b95860461c55abd3953c518adaf0cfa7052a9d200397ee87a88f"
         and prior["authentic_TRAIN_before_first_DEV"]
         and prior["no_DEV_selection_or_tuning"]
         and not prior["protected_first_use"]
         and not prior["independent_science_acceptance"]
         and not prior["optimizer_promotion"]
         and not prior["production_activation"]
         and len(prior["lanes"])==2,
         "ORIGINAL_AN_FULL_PROVENANCE")
    previous={x["lane"]:x for x in prior["lanes"]}
    need(set(previous)=={"Wingless","Yggdrasil"},"AN_BOTH_LANES")
    for lane in previous:
        need(previous[lane]["original_weights_digest"]==
             provenance.digest(base[lane]) and
             previous[lane]["DEV"]["pairs"]==48,
             "ORIGINAL_FROZEN_WEIGHTS_AND_DENOMINATOR")
    return base,delta,previous

def graph_checks(cases):
    diagnostics={"positives":0,"negatives":0,"old_literal_positive":0,
                 "three_corruptions":0,
                 "by_family":{family:0 for family in source.FAMILIES},
                 "affine":0,"feistel":0,
                 "support_equal_in_pairs":True}
    truth=source.parent.am.old.prior.parent.original.parent.prior.parent.routes15
    for seed,vec,fam,op,nonce,p,n in cases:
        restored_p=source.plain(p,op,nonce)
        restored_n=source.plain(n,op,nonce)
        relax=fam=="rotate4_tolerant"
        diagnostics["positives"]+=int(truth(restored_p,relaxed=relax)==1)
        diagnostics["negatives"]+=int(truth(restored_n,relaxed=relax)==0)
        diagnostics["old_literal_positive"]+=int(
            truth({k:p[k] for k in ("start","target","roles","edges")},
                  relaxed=True)>0)
        diagnostics["three_corruptions"]+=int(
            sum(source.relation(d["input_bits"],op)!=d["output_bits"]
                for d in p["demos"])==3)
        diagnostics["by_family"][fam]+=1
        diagnostics["affine" if op.startswith("affine_") else "feistel"]+=1
        diagnostics["support_equal_in_pairs"]&=p["demos"]==n["demos"]
    need(len(cases)==48 and diagnostics["positives"]==48 and
         diagnostics["negatives"]==48 and
         diagnostics["three_corruptions"]==48 and
         diagnostics["old_literal_positive"]==0 and
         diagnostics["affine"]==24 and diagnostics["feistel"]==24 and
         all(v==12 for v in diagnostics["by_family"].values()) and
         diagnostics["support_equal_in_pairs"],
         "TRAIN_PAIRS_AND_FOUR_FAMILIES")
    return diagnostics

def train(original_o,original_t,an_path):
    doc=source.frozen()
    base,delta,prior=identity(original_o,original_t,an_path)
    yc=source.pairs("Yggdrasil","TRAIN")
    wc=source.pairs("Wingless","TRAIN")
    ydiag=graph_checks(yc)
    wdiag=graph_checks(wc)
    yselected,ygrid=y.select(yc,base["Yggdrasil"],delta["Yggdrasil"])
    # Source-only normalized graph supplied to Wingless arms equally.
    normalized=[]
    for seed,vec,fam,op,nonce,p,n in wc:
        normalized.append((provenance.digest([seed,list(vec),fam]),fam,
                           source.plain(p,op,nonce),source.plain(n,op,nonce)))
    wselected,wgrid=w.select(normalized,base["Wingless"],delta["Wingless"])
    need(len(ygrid)==24 and len(wgrid)==7 and
         yselected in ygrid and wselected in wgrid and
         wselected["strict_train_preservation"],
         "TRAIN_PRESELECTED_CANDIDATE_GRIDS")
    need(all(row["FP"]>=0 and row["FN"]>=0 and row["paired"]<=48
             for row in ygrid+wgrid),
         "TRAIN_PAIRED_OUTCOME_BOUNDS")
    return {"schema":SCHEMA,"source_blob":source.FREEZE_BLOB,
            "lineage_parent_AN_sha256":AN_SHA,
            "qualified_parent_source_head":
                "ca46eba41179a1c6d9cd0bfa74119782c6d11d88",
            "original_foundations":{
                lane:{"base_sha256":provenance.digest(base[lane]),
                      "delta_sha256":provenance.digest(delta[lane]),
                      "parent_AN_DEV_paired":(
                          prior[lane]["DEV"]["models"][
                              "new_calibrated_affine" if lane=="Yggdrasil"
                              else "terminal_gamma_selected"]["paired"])}
                for lane in ("Yggdrasil","Wingless")},
            "source":{"Yggdrasil_TRAIN":ydiag,"Wingless_TRAIN":wdiag},
            "selected":{"Yggdrasil":yselected,"Wingless":wselected},
            "grid":{"Yggdrasil":ygrid,"Wingless":wgrid},
            "only_train_sources_evaluated":True,
            "dev_cases_generated":0,"dev_selection_or_retuning":False,
            "source_oracle_never_model_input":True,
            "wingless_source_evaluator_normalized":True,
            "original_Ygg_7_plus_9":True,"original_Wing_12_bit_one_state":True,
            "protected_first_use":False,
            "independent_science_acceptance":False,
            "optimizer_promotion":False,"production_activation":False}

def main():
    ap=argparse.ArgumentParser()
    for key in ("o","t","an","output"):ap.add_argument("--"+key,required=True)
    args=ap.parse_args()
    output=Path(args.output)
    need(output.parent.is_dir() and not output.exists(),"IMMUTABLE_TRAIN_ONLY_OUTFILE")
    data=train(args.o,args.t,args.an)
    raw=json.dumps(data,sort_keys=True,indent=2).encode()+b"\n"
    with output.open("xb") as f:f.write(raw)
    print("F124AO_TRAIN_SELECTION_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in ("Yggdrasil","Wingless"):
        print("F124AO_TRAIN_"+lane+"="+json.dumps(data["selected"][lane],sort_keys=True))
    print("F124AO_DEV_CASES_GENERATED=0")
    print("F124AO_AUTHORITY_ACCEPTANCE=FALSE")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print("F124AO_TRAIN_FAIL_CLOSED:"+str(exc),file=sys.stderr)
        sys.exit(1)
