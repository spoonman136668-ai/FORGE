"""F124-T signed-parent development evidence: no training, no first use.

Strict exact predictor replay required for indexed Wingless and full Yggdrasil
ablation. Work counters expose auxiliary indexing/cache resources; they are
proxies, not wall-clock or information-matched claims.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import f124t_fresh_source as src
import f124t_variants as var
import f124s_native_mechanisms as s_model
import f124o_native_learners as o_model
import f124r_causal_learners as r_model
import f124n_development_evidence as original_validator
import f124h_train_receipt as original_fixed
import f124p_frozen_variants as p_ablations

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"reference/research-intake/f124t-indexed-key-credit-ablation-freeze.json"
CONTRACT_BLOB="61810e6d77e924310c10e84bc7cdbde726adac17"
S_SHA="fb28a06ca4e0bfde9b4053734d61f2e3d1e760a8a3dda29e834780abe2339f25"
R_SHA="8ac2d22d10c91e453e33ca7d6deba44a75d92849b106d6f49cc9f19b123f2525"
O_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
S_MODEL_BLOB="69398a9e090cb19f207816ffcd5f8060bb4bbafb"
S_SOURCE_BLOB="2a426c6974b8375bc762884380e3dfb6e60bad34"
SCHEMA="forge.research.f124t.indexed-key-and-cell-credit-diagnostic-v1"


def need(ok,msg):
    src.need(ok,"RECEIPT_"+msg)


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,
        separators=(",",":")).encode()).hexdigest()


def blob(mod):
    return src.git_blob(Path(mod.__file__).read_bytes().replace(b"\r\n",b"\n"))


def contract():
    raw=CONTRACT.read_bytes().replace(b"\r\n",b"\n")
    need(src.git_blob(raw)==CONTRACT_BLOB,"PREREGISTRATION_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124t.frozen-indexed-key-credit-ablation.v1"
         and p["stage"]=="PREIMPLEMENTATION_FROZEN"
         and p["parent"]["qualified_head"]=="bc59de4f118b37d9a501dd8a944e210540222a27"
         and p["parent"]["s_model_blob"]==S_MODEL_BLOB
         and p["parent"]["s_source_blob"]==S_SOURCE_BLOB
         and p["parent"]["signed_s_development_sha256"]==S_SHA
         and p["protocol"]["no_new_learning_or_new_parameters"] is True
         and p["protocol"]["no_post_dev_tuning"] is True
         and p["new_public_source"]["pairs_per_lane_per_cohort"]==48
         and p["protocol"]["Yggdrasil"]["active_limit"]==7
         and p["protocol"]["Yggdrasil"]["retained_limit"]==9
         and all(x is False for x in p["authority"].values())
         and blob(s_model)==S_MODEL_BLOB,
         "FROZEN_SOURCE_BOUNDARY")
    src.frozen()
    return p


def read_source(path,expected):
    raw=Path(path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==expected,
         "AUTHENTIC_PREVIOUS_EVIDENCE_SHA")
    return json.loads(raw)


def authentic_models(o_path,r_path,s_path):
    o=read_source(o_path,O_SHA)
    r=read_source(r_path,R_SHA)
    s=read_source(s_path,S_SHA)
    need(o["schema"]=="forge.research.f124o.two-native-trained-development-outcomes.v1"
         and r["schema"]=="forge.research.f124r.fresh-continuous-causal-development-v1"
         and s["schema"]=="forge.research.f124s.fresh-packed-key-cell-credit-development.v1"
         and s["exact_qualified_parent"]=="522601491c10ebfeb36e7dca2627ff5366b51abb"
         and s["preimplementation_git_blob"]=="33b299417fb284982aa162684b467b4593a6d828"
         and s["both_models_trained"] is True
         and s["training_gate_negatives"]==0
         and s["scientific_acceptances"]==0
         and s["protected_cases_generated"]==0
         and len(s["lanes"])==2
         and len(o["lanes"])==2 and len(r["lanes"])==2,
         "PARENT_AUTHORITIES")
    output={}
    for lane in ("Wingless","Yggdrasil"):
        a=next(x for x in o["lanes"] if x["lane"]==lane)
        b=next(x for x in r["lanes"] if x["lane"]==lane)
        c=next(x for x in s["lanes"] if x["lane"]==lane)
        base=a["training"]["trained_weights"]
        rdelta=b["training"]["delta"]
        sdelta=c["training"]["delta"]
        need(len(base)==7 and len(rdelta)==2 and len(sdelta)==2
             and o_model.sha(base)==a["training"]["trained_weight_sha256"]
             and r_model.digest(rdelta)==b["training"]["delta_sha256"]
             and s_model.digest(sdelta)==c["training"]["delta_sha256"]
             and c["training"]["fit_only"] is True
             and c["training"]["training_steps"]==72
             and c["training"]["DEV_access_during_train"]==0
             and c["dev"]["arms"]["new_F124S"]["pairs"]==48
             and c["dev"]["resource_comparison"]
                 ["scientific_resource_matched_superiority_proven"] is False,
             "AUTHENTIC_ORIGINAL_WEIGHTS")
        output[lane]={"base":tuple(base),"rd":tuple(rdelta),"sd":tuple(sdelta),
                      "s_original_sha":c["training"]["delta_sha256"]}
    return output


def score_arm(lane,arm,g,params,fixed):
    base=list(params["base"]);rd=list(params["rd"]);sd=list(params["sd"])
    if arm=="fixed":
        pred,work=fixed(g)
        return int(bool(pred)),work,None
    if arm=="o":
        z,work=o_model.forward(lane,g,base)
    elif arm=="r":
        z,work=r_model.forward(lane,g,base,rd)
    elif arm=="s":
        z,work=s_model.forward(lane,g,base,sd)
    elif arm=="indexed":
        need(lane=="Wingless","INDEX_ONLY_WING")
        z,work=var.wingless_indexed(g,base,sd)
    elif arm=="value_only":
        need(lane=="Yggdrasil","ABLATION_ONLY_YGG")
        z,work=var.yggdrasil_credit_ablation(g,base,sd,
                                              value_credit=True,rank_credit=False)
    elif arm=="rank_only":
        need(lane=="Yggdrasil","ABLATION_ONLY_YGG")
        z,work=var.yggdrasil_credit_ablation(g,base,sd,
                                              value_credit=False,rank_credit=True)
    elif arm=="p_zero":
        need(lane=="Yggdrasil","ABLATION_ONLY_YGG")
        z,work=p_ablations.variant_forward(lane,"ablate_secondary",g,base)
    else:
        raise src.Quarantined("F124T_INVALID_ARM")
    need(math.isfinite(z),"FINITE_DEVELOPMENT_LOGIT")
    return int(o_model.sigmoid(z)>=.5),work,z


def evaluate(lane,phase,params,fixed):
    arms=("o","r","s","indexed","fixed") if lane=="Wingless" else (
        "o","r","s","value_only","rank_only","p_zero","fixed")
    results={name:{"paired":0,"pairs":0,"pos_correct":0,"neg_correct":0,
                   "false_positive":0,"false_negative":0,
                   "public_edge_scans":0,"raw_bit_ops":0,
                   "index_lookup_count":0,"cache_hits":0,
                   "peak_extra_index_entries":0,
                   "peak_extra_cache_entries":0,
                   "max_active":0,"max_retained":0,"evictions":0,
                   "depth":{str(d):{"pairs":0,"paired":0} for d in (7,8,9)},
                   "cases":[]}
             for name in arms}
    exact=noncausal=0
    for v in src.VECTORS:
        for seed in src.COHORTS[lane][phase]:
            pos,neg=src.build(lane,seed,v,phase)
            need(src.public_routes(pos)==1 and src.public_routes(neg)==0,
                 "EXACT_PUBLIC_CAUSAL_ADMISSION")
            exact+=1
            noncausal+=int(src.public_routes(pos,True)>0
                           and src.public_routes(neg,True)==0)
            samples=[{},{}]
            for index,g in enumerate((pos,neg)):
                for arm in arms:
                    samples[index][arm]=score_arm(lane,arm,g,params,fixed)
                if lane=="Wingless":
                    # Exact equality includes score, predictions and per-case
                    # logged evidence: optimization does not change mechanism.
                    need(samples[index]["indexed"][2].hex()==
                         samples[index]["s"][2].hex() and
                         samples[index]["indexed"][0]==
                         samples[index]["s"][0],"WING_OPTIMIZATION_PREDICTION_DRIFT")
                else:
                    z,work=var.yggdrasil_credit_ablation(
                        g,list(params["base"]),list(params["sd"]),
                        value_credit=True,rank_credit=True)
                    need(z.hex()==samples[index]["s"][2].hex() and
                         work["max_active"]<=7 and work["max_retained"]<=9,
                         "YGG_ABLATION_ORIGINAL_IDENTICAL")
            depth=str(len(pos["roles"]))
            for arm in arms:
                rec=results[arm]
                a,wa,za=samples[0][arm]
                b,wb,zb=samples[1][arm]
                paired=int(bool(a and not b))
                rec["pairs"]+=1;rec["paired"]+=paired
                rec["pos_correct"]+=a;rec["neg_correct"]+=1-b
                rec["false_positive"]+=b;rec["false_negative"]+=1-a
                rec["depth"][depth]["pairs"]+=1
                rec["depth"][depth]["paired"]+=paired
                for cost in (wa,wb):
                    rec["public_edge_scans"]+=cost["public_edge_scans"]
                    rec["raw_bit_ops"]+=cost.get("raw_bit_ops",
                                                    cost.get("bit_comparisons",0))
                    rec["index_lookup_count"]+=cost.get("index_lookup_count",0)
                    rec["cache_hits"]+=cost.get("cache_hits",0)
                    rec["max_active"]=max(rec["max_active"],
                                          cost.get("max_active",0))
                    rec["max_retained"]=max(rec["max_retained"],
                                            cost.get("max_retained",0))
                    rec["evictions"]+=cost.get("evictions",0)
                    rec["peak_extra_index_entries"]=max(
                        rec["peak_extra_index_entries"],
                        cost.get("index_entries",0))
                    rec["peak_extra_cache_entries"]=max(
                        rec["peak_extra_cache_entries"],
                        cost.get("max_key_cache_entries",0))
                rec["cases"].append(digest({
                    "lane":lane,"phase":phase,"vector":v,"seed":seed,
                    "depth":int(depth),"arm":arm,"pos":a,"neg":b}))
    need(exact==48 and noncausal==0,"SOURCE_48_PAIR_POS_NEG_DENOMINATOR")
    for arm,x in results.items():
        need(x["pairs"]==48 and len(x["cases"])==48
             and all(y["pairs"]==16 for y in x["depth"].values())
             and x["max_retained"]<=9 and
             (x["max_active"]<=7 if lane=="Yggdrasil"
              else x["max_active"]<=192),
             "FULL_FIXED_CAPACITY_AND_DEPTH")
    if lane=="Wingless":
        before=results["s"];after=results["indexed"];fixed_result=results["fixed"]
        need(before["paired"]==after["paired"]
             and before["cases"]!=after["cases"]  # arm ID intentionally differs
             and after["peak_extra_index_entries"]>0,
             "INDEX_SOURCE_AND_SAME_OUTCOMES")
        extras={"persistent_serialized_state_bytes":10,
                "persistent_model_old_o_logical_state_bytes":40,
                "extra_transient_index_entries":after["peak_extra_index_entries"],
                "extra_transient_token_cache_entries":after["peak_extra_cache_entries"],
                "index_lookups":after["index_lookup_count"],
                "cache_hits":after["cache_hits"],
                "old_s_edge_scans":before["public_edge_scans"],
                "indexed_edge_scans":after["public_edge_scans"],
                "fixed_edge_scans":fixed_result["public_edge_scans"],
                "old_s_raw_bit_ops":before["raw_bit_ops"],
                "indexed_raw_bit_ops":after["raw_bit_ops"],
                "fixed_raw_bit_ops":fixed_result["raw_bit_ops"],
                "improved_edge_scan_proxy":after["public_edge_scans"]<
                                             before["public_edge_scans"],
                "improved_raw_bit_proxy":after["raw_bit_ops"]<
                                            before["raw_bit_ops"],
                "full_runtime_or_information_capacity_matched":False}
    else:
        extras={"original_S_score_replay_verified":True,
                "no_parameter_updates":True,
                "active_limit":7,"retained_limit":9}
    return {"phase":phase,"pairs":48,"exact_paired":exact,
            "role_only_paired":noncausal,"arms":results,"resource_census":extras}


def collect(o_path,r_path,s_path):
    protocol=contract()
    params=authentic_models(o_path,r_path,s_path)
    fixed=original_validator.clone_single_validator(
        original_fixed.fixed_comparator,"graph")
    result={"schema":SCHEMA,"freeze_blob":CONTRACT_BLOB,
            "qualified_parent_sha":"bc59de4f118b37d9a501dd8a944e210540222a27",
            "authenticated_original_S_receipt_sha256":S_SHA,
            "authenticated_original_R_receipt_sha256":R_SHA,
            "authenticated_original_O_receipt_sha256":O_SHA,
            "training_steps":0,"new_trained_parameters":0,
            "development_only":True,"source_born_protected_first_use":False,
            "independent_science_accepted":False,"scientific_acceptances":0,
            "optimizer_promotions":0,"accepted_ref_mutations":0,
            "new_schedulers":0,"paid_api_or_codex_calls":0,
            "matched_compute_superiority_proven":False,"lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        fit=evaluate(lane,"FIT",params[lane],fixed)
        dev=evaluate(lane,"DEV",params[lane],fixed)
        result["lanes"].append({"lane":lane,
            "unchanged_original_S_parameter_sha256":params[lane]["s_original_sha"],
            "fit":fit,"dev":dev,
            "verdict":("NO_NEW_SCIENTIFIC_ACCEPTANCE" if lane=="Wingless"
                else "ABLATION_ONLY_NO_POSTHOC_MODEL_SELECTION")})
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-o",required=True)
    p.add_argument("--original-r",required=True)
    p.add_argument("--original-s",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    path=Path(a.output)
    need(path.parent.is_dir() and not path.exists(),"OUTPUT_MUST_BE_NEW")
    result=collect(a.original_o,a.original_r,a.original_s)
    raw=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with path.open("xb") as stream:stream.write(raw)
    print("F124T_EVIDENCE_SHA256="+hashlib.sha256(raw).hexdigest())
    for row in result["lanes"]:
        d=row["dev"];arms=d["arms"]
        if row["lane"]=="Wingless":
            print("F124T_DEV_WINGLESS:oldS="+str(arms["s"]["paired"])+
                  "/48:indexed="+str(arms["indexed"]["paired"])+
                  "/48:fixed="+str(arms["fixed"]["paired"])+"/48"+
                  ":edge_scans_old="+str(arms["s"]["public_edge_scans"])+
                  ":edge_scans_new="+str(arms["indexed"]["public_edge_scans"])+
                  ":extra_index_entries="+str(d["resource_census"]["extra_transient_index_entries"]))
        else:
            print("F124T_DEV_YGGDRASIL:fullS="+str(arms["s"]["paired"])+
                  "/48:valueOnly="+str(arms["value_only"]["paired"])+
                  "/48:rankOnly="+str(arms["rank_only"]["paired"])+
                  "/48:oldR="+str(arms["r"]["paired"])+
                  "/48:fixed="+str(arms["fixed"]["paired"])+"/48")


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
        print("F124T_QUARANTINED:"+str(exc),file=sys.stderr)
        sys.exit(1)
