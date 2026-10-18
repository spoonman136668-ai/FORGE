"""F124-U source-authenticated independent research evidence.

Qualify merged F124-S/T source before this preregistration. No protected
first use; compare a bounded scratch/microindex implementation and train a
new Yggdrasil ranking-only causal surrogate solely on new FIT data.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import f124u_fresh_source as source
import f124u_microindex_causal_rank as model
import f124s_native_mechanisms as S
import f124t_variants as T
import f124o_native_learners as O
import f124r_causal_learners as R
import f124n_development_evidence as adapter
import f124h_train_receipt as original_ctrl

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f124u-microindex-causal-rank-freeze.json"
FREEZE_BLOB="3f7150378a3b7e86006534843d4f1f41f6e783ef"
O_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
R_SHA="8ac2d22d10c91e453e33ca7d6deba44a75d92849b106d6f49cc9f19b123f2525"
S_SHA="fb28a06ca4e0bfde9b4053734d61f2e3d1e760a8a3dda29e834780abe2339f25"
T_SHA="6aeab10ff49a98819e2e7614140d6304a0079cc8caebca7dd20b08b8ff73fab3"
S_BLOB="69398a9e090cb19f207816ffcd5f8060bb4bbafb"
T_BLOB="a7c204d5082c3c542cff2892dfdf77b21f93effd"
SCHEMA="forge.research.f124u.bounded-index-and-fresh-causal-rank-development.v1"


def need(x,msg):
    source.need(x,"RECEIPT_"+msg)


def sha(x):
    return model.sha(x)


def blob(mod):
    return source.git_blob(Path(mod.__file__).read_bytes().replace(b"\r\n",b"\n"))


def preregistration():
    b=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(source.git_blob(b)==FREEZE_BLOB,"PREREGISTERED_BLOB_DRIFT")
    p=json.loads(b)
    need(p["schema"]=="forge.research.f124u.frozen-microindex-causal-rank-v1"
         and p["stage"]=="PREIMPLEMENTATION_FROZEN"
         and p["qualified_parent"]["head"]=="becf7829c7a5521b234a1c25b659b614570f1af7"
         and p["qualified_parent"]["run_id"]==39083960650
         and p["qualified_parent"]["t_original_mechanism_sha"]==T_BLOB
         and p["qualified_parent"]["s_original_mechanism_sha"]==S_BLOB
         and p["qualified_parent"]["s_receipt_sha256"]==S_SHA
         and p["qualified_parent"]["t_receipt_sha256"]==T_SHA
         and p["arms"]["Wingless"]["microindex_max_edge_entries"]==8
         and p["arms"]["Wingless"]["microindex_max_candidate_keys"]==4
         and p["arms"]["Wingless"]["key_cache_max_entries"]==8
         and p["arms"]["Yggdrasil"]["train_steps"]==72
         and p["arms"]["Yggdrasil"]["no_accumulated_value_credit"] is True
         and p["arms"]["Yggdrasil"]["fit_failure_blocks_DEV"] is True
         and all(v is False for v in p["authority"].values())
         and blob(S)==S_BLOB and blob(T)==T_BLOB,
         "UNMODIFIED_PREVIOUS_SCIENCE")
    source.frozen()
    return p


def authenticate(path,digest):
    raw=Path(path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==digest,"AUTHENTIC_ORIGINAL_RECEIPT")
    return json.loads(raw)


def originals(o_path,r_path,s_path,t_path):
    o=authenticate(o_path,O_SHA)
    r=authenticate(r_path,R_SHA)
    s=authenticate(s_path,S_SHA)
    t=authenticate(t_path,T_SHA)
    need(o["schema"]=="forge.research.f124o.two-native-trained-development-outcomes.v1"
         and r["schema"]=="forge.research.f124r.fresh-continuous-causal-development-v1"
         and s["schema"]=="forge.research.f124s.fresh-packed-key-cell-credit-development.v1"
         and t["schema"]=="forge.research.f124t.indexed-key-and-cell-credit-diagnostic-v1"
         and t["qualified_parent_sha"]=="bc59de4f118b37d9a501dd8a944e210540222a27"
         and s["both_models_trained"] is True
         and t["training_steps"]==0
         and t["scientific_acceptances"]==0
         and s["scientific_acceptances"]==0 and len(t["lanes"])==2,
         "PARENT_S_T_SCIENCE_STATE")
    out={}
    for lane in ("Wingless","Yggdrasil"):
        orig=next(x for x in o["lanes"] if x["lane"]==lane)
        oldR=next(x for x in r["lanes"] if x["lane"]==lane)
        oldS=next(x for x in s["lanes"] if x["lane"]==lane)
        oldT=next(x for x in t["lanes"] if x["lane"]==lane)
        base=orig["training"]["trained_weights"]
        rd=oldR["training"]["delta"]
        sd=oldS["training"]["delta"]
        need(O.sha(base)==orig["training"]["trained_weight_sha256"]
             and R.digest(rd)==oldR["training"]["delta_sha256"]
             and S.digest(sd)==oldS["training"]["delta_sha256"]
             and oldS["training"]["fit_only"] is True
             and oldT["unchanged_original_S_parameter_sha256"]==
                 oldS["training"]["delta_sha256"]
             and oldT["dev"]["pairs"]==48
             and oldS["dev"]["pairs"]==48,
             "ORIGINAL_FIT_WEIGHT_HISTORY")
        out[lane]={"base":tuple(base),"r":tuple(rd),"s":tuple(sd)}
    return out


def arm(lane,name,g,prior,new_delta,fixed):
    base=list(prior["base"])
    if name=="fixed":
        a,w=fixed(g)
        return bool(a),{"public_edge_scans":w["public_edge_scans"],
                        "raw_bit_ops":w["bit_comparisons"],
                        "max_active":0,"max_retained":0},None
    if name=="original_O":
        z,w=O.forward(lane,g,base)
    elif name=="original_R":
        z,w=R.forward(lane,g,base,list(prior["r"]))
    elif name=="original_S":
        z,w=S.forward(lane,g,base,list(prior["s"]))
    elif name=="T_index" and lane=="Wingless":
        z,w=T.wingless_indexed(g,base,list(prior["s"]))
    elif name=="U_microindex" and lane=="Wingless":
        z,w=model.wingless_microindex(g,base,list(prior["s"]))
    elif name=="T_rank_only" and lane=="Yggdrasil":
        z,w=T.yggdrasil_credit_ablation(
            g,base,list(prior["s"]),value_credit=False,rank_credit=True)
    elif name=="U_fresh_rank" and lane=="Yggdrasil":
        z,w=model.ygg_rank(g,base,new_delta)
    else:
        raise source.Quarantined("F124U_ARM_INVALID")
    need(math.isfinite(z),"NONFINITE_SCORE")
    return bool(O.sigmoid(z)>=.5),w,z


def score(lane,phase,prior,new_delta,fixed):
    arms=["original_O","original_R","original_S","fixed"]
    if lane=="Wingless":
        arms.extend(["T_index","U_microindex"])
    else:
        arms.extend(["T_rank_only","U_fresh_rank"])
    out={k:{"paired":0,"pairs":0,"positive_correct":0,"negative_correct":0,
            "false_positive":0,"false_negative":0,
            "public_edge_scans":0,"raw_bit_ops":0,
            "index_entries_max":0,"key_cache_entries_max":0,
            "index_lookups":0,"fallback_scans":0,
            "max_active":0,"max_retained":0,"evictions":0,
            "depth":{str(i):{"pairs":0,"paired":0} for i in (7,8,9)},
            "case_hashes":[]}
         for k in arms}
    exact=role_only=0
    for v in source.VECTORS:
        for seed in source.COHORTS[lane][phase]:
            p,n=source.build(lane,seed,v,phase)
            need(source.public_routes(p)==1 and source.public_routes(n)==0,
                 "PUBLIC_SOURCE_EXACT_ADMISSION")
            exact+=1
            role_only+=int(source.public_routes(p,True)>0
                           and source.public_routes(n,True)==0)
            pred={}
            for graph_ix,g in enumerate((p,n)):
                data={name:arm(lane,name,g,prior,new_delta,fixed)
                      for name in arms}
                if lane=="Wingless":
                    z0=data["original_S"][2]
                    need(z0.hex()==data["T_index"][2].hex()==
                         data["U_microindex"][2].hex()
                         and data["original_S"][0]==data["T_index"][0]==
                         data["U_microindex"][0],
                         "WINGLESS_INDEX_BITEXACT_OR_PREDICTION_DRIFT")
                    wc=data["U_microindex"][1]
                    need(wc["index_entries"]<=8 and
                         wc["max_key_cache_entries"]<=8 and
                         wc["index_candidate_keys"]<=4 and
                         wc["serialized_state_payload_bytes"]==10,
                         "FROZEN_MICROINDEX_LIMIT")
                else:
                    wc=data["U_fresh_rank"][1]
                    need(wc["max_active"]<=7 and wc["max_retained"]<=9,
                         "YGG_FIXED_7_9_BUDGET")
                for name,(vote,work,z) in data.items():
                    pred[(name,graph_ix)]=vote
                    row=out[name]
                    row["public_edge_scans"]+=work["public_edge_scans"]
                    row["raw_bit_ops"]+=work.get("raw_bit_ops",
                                              work.get("bit_comparisons",0))
                    row["index_entries_max"]=max(row["index_entries_max"],
                                                work.get("index_entries",0))
                    row["key_cache_entries_max"]=max(row["key_cache_entries_max"],
                                               work.get("max_key_cache_entries",0))
                    row["index_lookups"]+=work.get("index_lookups",
                                                  work.get("index_lookup_count",0))
                    row["fallback_scans"]+=work.get("fallback_scans",0)
                    row["max_active"]=max(row["max_active"],
                                          work.get("max_active",0))
                    row["max_retained"]=max(row["max_retained"],
                                            work.get("max_retained",0))
                    row["evictions"]+=work.get("evictions",0)
            depth=str(len(p["roles"]))
            for name in arms:
                a=pred[(name,0)]
                b=pred[(name,1)]
                row=out[name]
                row["pairs"]+=1
                row["paired"]+=int(a and not b)
                row["positive_correct"]+=int(a)
                row["negative_correct"]+=int(not b)
                row["false_positive"]+=int(b)
                row["false_negative"]+=int(not a)
                row["depth"][depth]["pairs"]+=1
                row["depth"][depth]["paired"]+=int(a and not b)
                row["case_hashes"].append(model.sha({
                    "phase":phase,"lane":lane,"seed":seed,"vector":v,
                    "arm":name,"depth":depth,"positive":a,"negative":b}))
    need(exact==48 and role_only==0,"CAUSAL_DENOMINATOR")
    for name,row in out.items():
        need(row["pairs"]==48 and len(row["case_hashes"])==48 and
             all(d["pairs"]==16 for d in row["depth"].values()) and
             row["max_retained"]<=9 and
             (row["max_active"]<=7 if lane=="Yggdrasil"
              else row["max_active"]<=192),"COMPLETE_48_AND_MEMORY_BOUND")
    perf={}
    if lane=="Wingless":
        base=out["original_S"];full=out["T_index"];micro=out["U_microindex"]
        perf={"same_bitexact_logits_confirmed":True,
              "state_serialized_bytes":10,
              "microindex_edges_limit":8,"microindex_key_cache_limit":8,
              "microindex_extra_scratch_present":True,
              "S_edge_scans":base["public_edge_scans"],
              "T_full_edge_scans":full["public_edge_scans"],
              "U_bounded_edge_scans":micro["public_edge_scans"],
              "S_raw_bit_ops":base["raw_bit_ops"],
              "T_full_raw_bit_ops":full["raw_bit_ops"],
              "U_bounded_raw_bit_ops":micro["raw_bit_ops"],
              "U_fallback_scans":micro["fallback_scans"],
              "U_index_peak_entries":micro["index_entries_max"],
              "U_cache_peak_entries":micro["key_cache_entries_max"],
              "wallclock_equal_comparison_proven":False,
              "total_ram_equal_comparison_proven":False,
              "information_equal_comparison_proven":False,
              "matched_compute_superiority_proven":False}
    else:
        perf={"7_active_9_retained":True,"zero_accumulated_value_credit":True,
              "new_parameters_trained_on_FIT_only":True,
              "no_scientific_policy_advancement":True}
    return {"cohort":phase,"pairs":48,"exact_symbolic_pairs":exact,
            "role_only_pairs":role_only,"arms":out,"cost_census":perf}


def collect(o_path,r_path,s_path,t_path):
    p=preregistration()
    prior=originals(o_path,r_path,s_path,t_path)
    fixed=adapter.clone_single_validator(original_ctrl.fixed_comparator,"graph")
    print("F124U_YGGDRASIL_FIT_BEGIN",flush=True)
    ygg=model.train_ygg(list(prior["Yggdrasil"]["base"]))
    print("F124U_YGGDRASIL_FIT_UPDATE="+
          str(ygg["update_l2"]),flush=True)
    result={"schema":SCHEMA,
            "source_parent_qualified_head":"becf7829c7a5521b234a1c25b659b614570f1af7",
            "preimplementation_freeze_blob":FREEZE_BLOB,
            "original_S_receipt_sha256":S_SHA,
            "original_T_receipt_sha256":T_SHA,
            "original_O_receipt_sha256":O_SHA,
            "original_R_receipt_sha256":R_SHA,
            "wingless_original_S_weights_unchanged":True,
            "wingless_new_trained_parameters":0,
            "Yggdrasil_training":ygg,
            "protected_examples_generated":0,
            "protected_first_use":False,
            "scientific_acceptances":0,"optimizer_promotions":0,
            "accepted_ref_mutations":0,"new_schedulers":0,
            "cloudflare_mind_palace_mutations":0,
            "codex_paid_api_calls":0,
            "matched_compute_superiority_proven":False,"lanes":[]}
    # Only after FIT completion do we construct fresh DEV examples.
    for lane in ("Wingless","Yggdrasil"):
        d=ygg["learned_delta"] if lane=="Yggdrasil" else None
        fit=score(lane,"FIT",prior[lane],d,fixed)
        dev=score(lane,"DEV",prior[lane],d,fixed)
        result["lanes"].append({"lane":lane,"fit":fit,"dev":dev,
            "verdict":"DEVELOPMENT_ONLY_NO_PROTECTED_SCIENTIFIC_ACCEPTANCE"})
    return result


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--original-o",required=True)
    a.add_argument("--original-r",required=True)
    a.add_argument("--original-s",required=True)
    a.add_argument("--original-t",required=True)
    a.add_argument("--output",required=True)
    args=a.parse_args()
    target=Path(args.output)
    need(target.parent.is_dir() and not target.exists(),"IMMUTABLE_OUTPUT")
    value=collect(args.original_o,args.original_r,args.original_s,args.original_t)
    raw=(json.dumps(value,sort_keys=True,indent=2)+"\n").encode()
    with target.open("xb") as f:f.write(raw)
    print("F124U_EVIDENCE_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in value["lanes"]:
        d=lane["dev"]["arms"]
        if lane["lane"]=="Wingless":
            print("F124U_DEV_Wingless:S="+str(d["original_S"]["paired"])+
                  "/48:T="+str(d["T_index"]["paired"])+
                  "/48:U="+str(d["U_microindex"]["paired"])+
                  "/48:fixed="+str(d["fixed"]["paired"])+
                  "/48:edge_scans_U="+str(d["U_microindex"]["public_edge_scans"]))
        else:
            print("F124U_DEV_Yggdrasil:new="+str(d["U_fresh_rank"]["paired"])+
                  "/48:frozen_rank="+str(d["T_rank_only"]["paired"])+
                  "/48:oldR="+str(d["original_R"]["paired"])+
                  "/48:fixed="+str(d["fixed"]["paired"]))


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
        print("F124U_QUARANTINED:"+str(exc),file=sys.stderr)
        sys.exit(1)
