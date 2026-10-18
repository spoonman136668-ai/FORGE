"""F124-R evidence: authentic F124-O/Q parents, fresh FIT-only independent
learning and genuinely disjoint nonprotected DEV, complete original controls.

Previous Q FIT/DEV source was already consumed. It is not used by R training
or R evidence admission. Protected confirmation is unavailable and unused.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import f124o_native_learners as original
import f124p_frozen_variants as frozen_ablations
import f124q_independent_binding as previous_q
import f124n_development_evidence as original_adapter
import f124h_train_receipt as original_fixed
import f124r_fresh_source as source
import f124r_causal_learners as learner

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"reference/research-intake/f124r-calibrated-causal-evidence-freeze.json"
CONTRACT_BLOB="a4db651492631ad1be141ab2a0a6e1c86dad60ea"
BASE_SHA="025c97abc8eb69079d7d7d0f59bfdb81235b9ad9ab83e230f32b542d2cfbdb5d"
Q_SHA="c4c6155d75349730d31d0b304b2e2f6597a6abf91ee47ff96d7d4df671161117"
BASE_BLOB="a7ee347b736939bfdd0f7f56eca4d52a0fe0f0fd"
Q_BLOB="ebad38ff22ef6b151fd5ff7f25da41a20d9fcf65"
P_BLOB="6232d4ce49d182814dc5ab6f6b1c1c14fd762aaa"
SCHEMA="forge.research.f124r.fresh-continuous-causal-development-v1"


def need(ok,code):
    source.need(ok,"RECEIPT_"+code)


def blob(mod):
    return source.git_blob(Path(mod.__file__).read_bytes().replace(b"\r\n",b"\n"))


def authentic_freeze():
    raw=CONTRACT.read_bytes().replace(b"\r\n",b"\n")
    need(source.git_blob(raw)==CONTRACT_BLOB,"PREIMPLEMENTATION_BLOB_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124r.freeze.calibrated-causal-evidence-v1"
         and p["stage"]=="FROZEN_BEFORE_SOURCE_OR_MODEL_IMPLEMENTATION"
         and p["parent"]["commit_sha"]=="a3ef79b3dc10dcc4d544f808e35897e72ed4a154"
         and p["parent"]["original_f124o_model_git_blob"]==BASE_BLOB
         and p["parent"]["original_f124o_train_receipt_sha256"]==BASE_SHA
         and p["parent"]["f124q_development_sha256"]==Q_SHA
         and p["parent"]["f124q_model_git_blob"]==Q_BLOB
         and p["parent"]["previous_f124p_baseline_git_blob"]==P_BLOB
         and p["optimizer"]["steps"]==72
         and p["optimizer"]["epochs"]==learner.EPOCHS
         and p["optimizer"]["batch_pairs"]==learner.BATCH
         and p["optimizer"]["perturbation"]==learner.PERTURB
         and p["optimizer"]["learning_rate"]==learner.LR
         and p["optimizer"]["no_DEV_gradient_or_selection"] is True
         and p["optimizer"]["no_post_DEV_parameter_modification"] is True
         and p["models"]["Wingless"]["trainable_coefficients"]==2
         and p["models"]["Yggdrasil"]["trainable_coefficients"]==2
         and p["models"]["Yggdrasil"]["active_cell_limit"]==7
         and p["models"]["Yggdrasil"]["retained_cell_limit"]==9
         and all(x is False for x in p["authority"].values()),
         "PREIMPLEMENTATION_PROTOCOL_DRIFT")
    need(blob(original)==BASE_BLOB and blob(previous_q)==Q_BLOB
         and blob(frozen_ablations)==P_BLOB,
         "UNMODIFIED_ORIGINAL_MECHANISMS")
    source.frozen()
    return p


def auth_json(path,digest):
    raw=Path(path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==digest,
         "ORIGINAL_AUTHENTIC_EVIDENCE_SHA")
    return json.loads(raw)


def authenticated_weights(prior, prior_q):
    p=auth_json(prior,BASE_SHA)
    q=auth_json(prior_q,Q_SHA)
    need(p["schema"]=="forge.research.f124o.two-native-trained-development-outcomes.v1"
         and p["training_phase"]=="FIT_ONLY" and len(p["lanes"])==2
         and p["scientific_acceptances"]==0
         and q["schema"]=="forge.research.f124q.fresh-two-native-causal-binding-development.v1"
         and q["qualified_parent_head"]==
             "497ef36d0a2d17c6ff474db97ba554a2f55536a4"
         and q["authenticated_parent_receipt_sha256"]==BASE_SHA
         and q["source_protocol_git_blob"]==
             "82e2b26f8454231ac88af5a9169850cf997c0c71"
         and q["training_gate_negatives"]==1
         and q["two_lane_scientific_training_qualified"] is False
         and q["protected_source_generated"]==0
         and q["scientific_acceptances"]==0,"SOURCE_AUTHORITY_ORIGINAL_DRIFT")
    weights={}
    for row in p["lanes"]:
        lane=row["lane"]
        train=row["training"]
        w=train["trained_weights"]
        need(lane in source.COHORTS and lane not in weights
             and train["train_phase"]=="FIT_ONLY"
             and train["dev_seen_during_training"] is False
             and len(w)==7 and original.sha(w)==train["trained_weight_sha256"],
             "F124O_ORIGINAL_WEIGHT_AUTHENTICITY")
        weights[lane]=tuple(w)
    need(set(weights)=={"Wingless","Yggdrasil"}
         and q["lanes"][0]["lane"]=="Wingless"
         and q["lanes"][0]["training_status"]=="GENUINE_FIT_PASS"
         and q["lanes"][0]["training"]["fit_only"] is True
         and previous_q.digest(q["lanes"][0]["training"]["delta"])==
             q["lanes"][0]["training"]["delta_sha256"]
         and q["lanes"][1]["lane"]=="Yggdrasil"
         and q["lanes"][1]["training_status"]=="FIT_GATE_BLOCKED"
         and q["lanes"][1]["dev_scored"] is False,
         "Q_HISTORY_NO_FALSE_YGGDRASIL_LEARNER")
    return weights,tuple(q["lanes"][0]["training"]["delta"])


def prediction(lane,arm,g,base,delta,old_q_delta,fixed):
    if arm=="fixed_public":
        result,cost=fixed(g)
        return bool(result),{
            "public_edge_scans":cost["public_edge_scans"],
            "raw_bit_ops":cost["bit_comparisons"],
            "max_active":0,"max_retained":0,"causal_key_comparisons":0}
    if arm=="original_F124O":
        logit,cost=original.forward(lane,g,list(base))
    elif arm=="ablation_uniform_or_no_retention":
        logit,cost=frozen_ablations.variant_forward(
            lane,"ablate_compression" if lane=="Wingless"
            else "ablate_secondary",g,list(base))
    elif arm=="previous_Q_Wingless":
        need(lane=="Wingless","PREVIOUS_Q_YGGDRASIL_NOT_QUALIFIED")
        logit,cost=previous_q.forward(lane,g,list(base),list(old_q_delta))
    elif arm=="new_R_continuous":
        logit,cost=learner.forward(lane,g,list(base),list(delta))
    else:
        raise source.Quarantined("F124R_UNKNOWN_ARM")
    need(math.isfinite(logit),"NONFINITE_MODEL_LOGIT")
    return bool(original.sigmoid(logit)>=.5),cost


def phase_score(lane,phase,base,delta,old_q_delta,fixed):
    arms=["original_F124O","ablation_uniform_or_no_retention",
          "new_R_continuous","fixed_public"]
    if lane=="Wingless":
        arms.insert(2,"previous_Q_Wingless")
    results={name:{"pairs":0,"paired":0,"positive_correct":0,
                   "negative_correct":0,"false_positive":0,"false_negative":0,
                   "public_edge_scans":0,"raw_bit_ops":0,
                   "causal_key_comparisons":0,"max_active":0,"max_retained":0,
                   "execution_errors":0,
                   "per_depth":{str(d):{"pairs":0,"paired":0,
                                       "false_positives":0,
                                       "false_negatives":0} for d in (7,8,9)},
                   "case_sha256":[]}
             for name in arms}
    exact=role_only=0
    for vector in source.VECTORS:
        for seed in source.COHORTS[lane][phase]:
            pos,neg=source.build(lane,seed,vector,phase)
            need(source.public_routes(pos)==1 and
                 source.public_routes(neg)==0,"SYMBOLIC_CAUSAL_ADMISSION")
            exact+=1
            role_only+=int(source.public_routes(pos,True)>0
                           and source.public_routes(neg,True)==0)
            for name in arms:
                row=results[name]
                predictions=[]
                for graph in (pos,neg):
                    pred,cost=prediction(lane,name,graph,base,delta,
                                         old_q_delta,fixed)
                    predictions.append(pred)
                    row["public_edge_scans"]+=cost["public_edge_scans"]
                    row["raw_bit_ops"]+=cost["raw_bit_ops"]
                    row["causal_key_comparisons"]+=cost.get(
                        "causal_key_comparisons",0)
                    row["max_active"]=max(row["max_active"],
                                          cost.get("max_active",0))
                    row["max_retained"]=max(row["max_retained"],
                                            cost.get("max_retained",0))
                correct=bool(predictions[0] and not predictions[1])
                depth=str(len(pos["roles"]))
                row["pairs"]+=1
                row["paired"]+=int(correct)
                row["positive_correct"]+=int(predictions[0])
                row["negative_correct"]+=int(not predictions[1])
                row["false_positive"]+=int(predictions[1])
                row["false_negative"]+=int(not predictions[0])
                d=row["per_depth"][depth]
                d["pairs"]+=1;d["paired"]+=int(correct)
                d["false_positives"]+=int(predictions[1])
                d["false_negatives"]+=int(not predictions[0])
                row["case_sha256"].append(learner.digest({
                    "lane":lane,"phase":phase,"seed":seed,
                    "vector":vector,"depth":int(depth),"arm":name,
                    "pos":predictions[0],"neg":predictions[1]}))
    need(exact==48 and role_only==0,"PUBLIC_CAUSAL_PAIR_DENOMINATOR")
    for name,row in results.items():
        need(row["pairs"]==48 and len(row["case_sha256"])==48
             and all(v["pairs"]==16 for v in row["per_depth"].values())
             and row["execution_errors"]==0 and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192),
             "EXACT_SOURCE_OR_COGNITION_MEMORY_CAPACITY")
    return {"phase":phase,"pairs":48,"exact_symbolic_paired":exact,
            "role_only_paired":role_only,"arms":results}


def collect(prior_path,prior_q_path):
    proto=authentic_freeze()
    weights,old_q_delta=authenticated_weights(prior_path,prior_q_path)
    fixed=original_adapter.clone_single_validator(
        original_fixed.fixed_comparator,"graph")
    # Train both models without ever building a fresh DEV example.
    fitted={}
    for lane in ("Wingless","Yggdrasil"):
        print("F124R_FIT_BEGIN="+lane,flush=True)
        fitted[lane]=learner.train(lane,weights[lane])
        print("F124R_FIT_PASS="+lane+":UPDATE_L2="+
              str(fitted[lane]["weight_update_l2"]),flush=True)
    need(fitted["Wingless"]["delta_sha256"]!=
         fitted["Yggdrasil"]["delta_sha256"],"INDEPENDENT_LEARNED_STATE")
    out={"schema":SCHEMA,"qualified_f124q_parent_sha":
         "a3ef79b3dc10dcc4d544f808e35897e72ed4a154",
         "freeze_git_blob":CONTRACT_BLOB,
         "original_f124o_receipt_sha256":BASE_SHA,
         "original_f124q_receipt_sha256":Q_SHA,
         "source_birth_domain":"forge/F124R/new-structure/v1/",
         "study_status":"NONPROTECTED_DEVELOPMENT_ONLY",
         "protected_generated":0,"protected_first_use":False,
         "independent_original_science":False,"scientific_acceptances":0,
         "accepted_ref_mutations":0,"optimizer_promotions":0,
         "new_schedulers":0,"codex_calls":0,"paid_api_calls":0,
         "matched_compute_superiority_proven":False,
         "cross_lane_parameter_sharing":False,"lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        fit=phase_score(lane,"FIT",weights[lane],fitted[lane]["delta"],
                        old_q_delta,fixed)
        dev=phase_score(lane,"DEV",weights[lane],fitted[lane]["delta"],
                        old_q_delta,fixed)
        r=dev["arms"]
        out["lanes"].append({
            "lane":lane,"mechanism":proto["models"][lane]["name"],
            "frozen_original_F124O_sha256":original.sha(list(weights[lane])),
            "training":fitted[lane],"fit":fit,"dev":dev,
            "dev_verdict":"ABOVE_FIXED_ON_DEVELOPMENT_ONLY"
            if r["new_R_continuous"]["paired"]>r["fixed_public"]["paired"]
            else "NOT_ABOVE_FIXED_ON_DEVELOPMENT"})
    need(len(out["lanes"])==2 and
         all(l["training"]["dev_access_during_training"]==0 and
             l["training"]["protected_access_during_training"]==0
             for l in out["lanes"]),"FROZEN_BOUNDED_FIT_ONLY_TRAINING")
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--f124o-original",required=True)
    p.add_argument("--f124q-original",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    out=Path(a.output)
    need(out.parent.is_dir() and not out.exists(),"IMMUTABLE_RECEIPT")
    r=collect(a.f124o_original,a.f124q_original)
    data=(json.dumps(r,sort_keys=True,indent=2)+"\n").encode()
    with out.open("xb") as f:f.write(data)
    print("F124R_DEVELOPMENT_RECEIPT_SHA256="+hashlib.sha256(data).hexdigest())
    for row in r["lanes"]:
        d=row["dev"]["arms"]
        print("F124R_DEV:"+row["lane"]+
              ":learned="+str(d["new_R_continuous"]["paired"])+
              "/48:original="+str(d["original_F124O"]["paired"])+
              "/48:ablation="+str(d["ablation_uniform_or_no_retention"]["paired"])+
              "/48:fixed="+str(d["fixed_public"]["paired"])+"/48")


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as e:
        print("F124R_QUARANTINED:"+str(e),file=sys.stderr)
        sys.exit(1)
