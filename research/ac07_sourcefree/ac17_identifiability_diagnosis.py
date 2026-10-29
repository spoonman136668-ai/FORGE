"""AC-17: direct diagnosis of current native Ygg NCA on real public DTR.

No new DTR calls. Only authentic AC-15/16 source-owned public FIT/DEV data
with original current native Ygg source. No scientific or controller authority.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import time

import torch
import ac10_upstream_contract as ac10
import ac15_native_public_adapter as ac15
import ac16_current_ygg_nca as ac16

SCHEMA="forge.ac17.original-public-identifiability-locality.v1"
N_FOLDS=8
TOTAL_FOLD_GRADIENT_STEPS=8*ac16.EPOCHS

def fidelity(ac15_record:dict,ac16_record:dict):
    fit,dev=ac16.validate_parent(ac15_record)
    if (ac16_record.get("schema")!=ac16.SCHEMA or
        ac16_record.get("scope")!="EXTERNAL_SUPERVISED_ADAPTER_ON_UNCHANGED_NATIVE_NCA" or
        ac16_record.get("current_ygg_native_source_commit")!=ac16.ACTIVE_YGG_SHA or
        ac16_record.get("original_source_commit")!=ac10.SOURCE_COMMIT or
        ac16_record.get("fit_public_outcome_examples")!=16 or
        ac16_record.get("dev_public_outcome_examples")!=8 or
        ac16_record.get("actual_source_owned_new_episodes")!=0 or
        ac16_record.get("model_training",{}).get("epochs")!=64 or
        ac16_record.get("trained_on_dev") is not False or
        ac16_record.get("scientific_first_use") is not False or
        ac16_record.get("scientific_admission") is not False or
        ac16_record.get("native_repo_code_modified") is not False or
        ac16_record.get("actual_distributed_action_policy_executed") is not False):
        raise RuntimeError("AC17_AUTHENTIC_AC16_DEV_PARENT_FAILED")
    if ac16_record["dev_public_labels"]!=[r[3] for r in ac16.sample_rows(dev)]:
        raise RuntimeError("AC17_DEV_LABELS_INCONSISTENT_WITH_SOURCE")
    if len(ac16_record["dev_model_probabilities"])!=8:
        raise RuntimeError("AC17_PREVIOUS_FROZEN_DEV_PREDICTIONS_DRIFT")
    return fit,dev

def public_context_evidence(fit_rows:list[tuple],dev_rows:list[tuple]):
    counter=defaultdict(lambda:[0,0])
    for stage,obs,arm,y in fit_rows:
        counter[(stage,obs,arm)][y]+=1
    conflict={str(key):{"zero":counts[0],"one":counts[1],
                        "minority_mistakes":min(counts)}
              for key,counts in sorted(counter.items())
              if counts[0]>0 and counts[1]>0}
    n=sum(sum(v) for v in counter.values())
    if n!=len(fit_rows):
        raise RuntimeError("AC17_CONTEXT_SAMPLE_MISMATCH")
    ambiguity=sum(min(v) for v in counter.values())
    conditional_entropy_bits=0.0
    for values in counter.values():
        total=sum(values)
        for c in values:
            if c:
                p=c/total
                conditional_entropy_bits-=total/n*p*math.log2(p)
    missing=[{"stage":st,"observation":o,"action":a}
             for st,o,a,_ in dev_rows if (st,o,a) not in counter]
    return {"train_unique_public_context_action":len(counter),
            "train_possible_binary_context_action":8,
            "train_context_outcome_counts":[
                {"stage":st,"observation":ob,"action":arm,
                 "negative":v[0],"positive":v[1]}
                for (st,ob,arm),v in sorted(counter.items())],
            "train_contexts_with_both_outcomes":len(conflict),
            "train_conflicts":conflict,
            "in_sample_minority_count_lower_bound_for_deterministic_public_lookup":ambiguity,
            "in_sample_public_lookup_minimum_error_rate":ambiguity/n,
            "conditional_empirical_entropy_bits":conditional_entropy_bits,
            "dev_unseen_context_action_count":len(missing),
            "dev_unseen_context_action_keys":missing,
            "does_not_prove_unobservable_source_u":True}

def episode_cv(fit_doc,Config,Model):
    source=fit_doc["episodes"]
    if len(source)!=N_FOLDS:
        raise RuntimeError("AC17_FIT_FOLD_COUNT_INVALID")
    fold_rows=[]
    pred=[]
    label=[]
    baseline_tab=[]
    baseline_pool=[]
    total_wall=0
    for excluded_index in range(N_FOLDS):
        kept=[ev for i,episode in enumerate(source) if i!=excluded_index
              for ev in episode["events"]]
        held=[ev for ev in source[excluded_index]["events"]]
        training=[(e["stage"],e["observation"],e["action"],ac15.outcome(e)) for e in kept]
        test=[(e["stage"],e["observation"],e["action"],ac15.outcome(e)) for e in held]
        if len(training)!=14 or len(test)!=2:
            raise RuntimeError("AC17_LOO_TRAIN_TEST_SAMPLE_COUNT")
        trained,stats=ac16.fit_model(Config,Model,training,[r[3] for r in training])
        p=ac16.dev_probs(trained,test)
        t,unseen=ac16.tabular_probs(training,test)
        pool=(1+sum(r[3] for r in training))/(2+len(training))
        pred.extend(p)
        baseline_tab.extend(t)
        baseline_pool.extend([pool]*len(test))
        label.extend([r[3] for r in test])
        total_wall+=stats["train_wall_ns"]
        fold_rows.append({
            "heldout_fit_seed":source[excluded_index]["seed"],
            "remaining_fit_episodes":7,
            "train_public_outcomes":14,
            "heldout_public_outcomes":2,
            "heldout_context_action_unseen_count":unseen,
            "native_fold_brier":ac16.metrics(p,test)["brier"],
            "tabular_fold_brier":ac16.metrics(t,test)["brier"],
            "pooled_fold_brier":ac16.metrics([pool]*len(test),test)["brier"],
            "native_changed_parameters":stats["initial_parameter_sha256"]!=stats["trained_parameter_sha256"]
        })
    rows=[(0,0,0,int(y)) for y in label]
    return {
        "method":"FIT_ONLY_8_LEAVE_ONE_EPISODE_OUT_FOLDS",
        "fixed_fit_episodes":N_FOLDS,
        "each_training_examples":14,
        "each_heldout_examples":2,
        "total_native_gradient_steps":TOTAL_FOLD_GRADIENT_STEPS,
        "total_native_train_wall_ns":total_wall,
        "folds":fold_rows,
        "native_brier_and_accuracy":ac16.metrics(pred,rows),
        "contextual_tabular_brier_and_accuracy":ac16.metrics(baseline_tab,rows),
        "pooled_brier_and_accuracy":ac16.metrics(baseline_pool,rows),
        "source_owned_episodes_executed":0,
        "dev_seen_in_cv":False}

def sensitivities(model,dev):
    # Exact same trained model: flipping one public input bit is a *model*
    # sensitivity test, not authentic causal environment intervention.
    original=ac16.dev_probs(model,dev)
    result={}
    for bit,name in enumerate(("stage","observation","action")):
        alt=[]
        for row in dev:
            a=list(row)
            a[bit]=1-a[bit]
            alt.append(tuple(a))
        p=ac16.dev_probs(model,alt)
        changes=[abs(a-b) for a,b in zip(original,p)]
        result[name]={
            "mean_absolute_probability_change":sum(changes)/len(changes),
            "max_absolute_probability_change":max(changes),
            "unchanged_to_1e_minus_6":sum(d<=1e-6 for d in changes),
            "individual_absolute_changes":[round(v,8) for v in changes]}
    return result

def run(ygg:Path,ac15_report:Path,ac16_report:Path,out:Path):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    Config,Model=ac16.verify_current_native(ygg)
    parent15=json.loads(ac15_report.read_text(encoding="utf-8"))
    parent16=json.loads(ac16_report.read_text(encoding="utf-8"))
    fit_doc,dev_doc=fidelity(parent15,parent16)
    train=ac16.sample_rows(fit_doc);dev=ac16.sample_rows(dev_doc)
    coverage=public_context_evidence(train,dev)
    folds=episode_cv(fit_doc,Config,Model)
    model,fitstats=ac16.fit_model(Config,Model,train,[r[3] for r in train])
    pre=ac16.model_hash(model)
    sensitivity=sensitivities(model,dev)
    post=ac16.model_hash(model)
    if pre!=post:
        raise RuntimeError("AC17_FROZEN_PUBLIC_SENSITIVITY_MUTATED_MODEL")
    if fitstats["epochs"]!=ac16.EPOCHS or len(train)!=16:
        raise RuntimeError("AC17_FIT_ONLY_RULE_DRIFT")
    ac16.verify_current_native(ygg)
    result={
        "schema":SCHEMA,"scope":"DIAGNOSE_EXISTING_NATIVE_NEGATIVE_PUBLIC_ONLY",
        "original_dtr_source_commit":ac10.SOURCE_COMMIT,
        "current_ygg_source_commit":ac16.ACTIVE_YGG_SHA,
        "current_ygg_nca_blob":ac16.NCA_BLOB,
        "current_ygg_training_blob":ac16.TRAINING_BLOB,
        "parent_ac15_report_sha256":ac16.digest(ac15_report.read_bytes()),
        "parent_ac16_report_sha256":ac16.digest(ac16_report.read_bytes()),
        "source_fit_episodes_reused":8,"source_dev_episodes_reused":4,
        "new_source_episodes_executed":0,
        "fit_public_outcomes":len(train),"dev_public_outcomes":len(dev),
        "fit_public_context_identifiability":coverage,
        "leave_one_fit_episode_out_native_vs_controls":folds,
        "retrained_full_fit_native_update":fitstats,
        "frozen_model_sha256_before_sensitivity":pre,
        "frozen_model_sha256_after_sensitivity":post,
        "model_public_feature_flip_sensitivity":sensitivity,
        "original_ac16_dev_native_metrics":parent16["native_dev_prediction_metrics"],
        "original_ac16_dev_fitted_tabular_metrics":parent16["fitted_tabular_dev_prediction_metrics"],
        "original_ac16_dev_pooled_prior_metrics":parent16["pooled_fitted_dev_prediction_metrics"],
        "original_ac16_dev_rotated_negative_metrics":parent16["rotated_fit_label_negative_dev_metrics"],
        "original_nca_training_objective_replaced":False,
        "external_supervised_adapter_only":True,
        "native_dtr_action_reward_api_exists":False,
        "true_environment_action_counterfactual_performed":False,
        "causal_identifiability_proved":False,
        "learned_local_role_specialization_proved":False,
        "unfamiliar_family_transfer_tested":False,
        "dev_gradient_updates":0,
        "research_owner_manifest_modified":False,
        "native_source_repos_modified":False,
        "scientific_first_use":False,
        "scientific_admission":False,
        "controller_or_queue_modified":False
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--ygg",type=Path,required=True)
    p.add_argument("--ac15-report",type=Path,required=True)
    p.add_argument("--ac16-report",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    report=run(a.ygg,a.ac15_report,a.ac16_report,a.out)
    c=report["fit_public_context_identifiability"]
    loo=report["leave_one_fit_episode_out_native_vs_controls"]
    print("AC17_IDENTICAL_PUBLIC_INPUT_MIXED_OUTCOME_CONTEXTS="+str(c["train_contexts_with_both_outcomes"]))
    print("AC17_FIT_PUBLIC_IRREDUCIBLE_LOOKUP_ERRORS="+str(c["in_sample_minority_count_lower_bound_for_deterministic_public_lookup"]))
    print("AC17_DEV_UNSEEN_PUBLIC_CONTEXTS="+str(c["dev_unseen_context_action_count"]))
    print("AC17_EIGHT_FOLD_NATIVE_BRIER="+str(loo["native_brier_and_accuracy"]["brier"]))
    print("AC17_EIGHT_FOLD_TABULAR_BRIER="+str(loo["contextual_tabular_brier_and_accuracy"]["brier"]))
    print("AC17_PROTECTED_FIRST_USE=FALSE")
