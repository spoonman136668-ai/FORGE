"""AC-16: unchanged current Ygg local NCA, trained on real DTR PUBLIC FIT.

This is an external supervised outcome adapter, not a native DTR agent or
LocalTaskRuntime, scientific first-use, Wingless change or Ygg production loop.
No new upstream source calls: reuse authenticated AC-15 FIT and DEV artifacts.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
import time

import torch
from torch.nn import functional as F
import ac10_upstream_contract as ac10
import ac15_native_public_adapter as ac15

SCHEMA="forge.ac16.actual-ygg-local-nca-public-development.v1"
ACTIVE_YGG_SHA="92c421a5475a27015a390efb88c373eb5f15379d"
NCA_PATH="src/yggdrasil/nca.py"
TRAINING_PATH="src/yggdrasil/training.py"
NCA_BLOB="7b15017b7f5c6f9b507bcf43f4545a3c972f40d1"
TRAINING_BLOB="af610c4334d2dd16415b39dd344ae2ed82ddd931"
SEED=20261028
EPOCHS=64
LR=0.02
STEPS=2
STATE_CHANNELS=8
GRID=5
HIDDEN=16

def digest(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def verify_current_native(root:Path):
    root=root.resolve(strict=True)
    if ac10.git(root,"rev-parse","HEAD")!=ACTIVE_YGG_SHA:
        raise RuntimeError("AC16_CURRENT_YGG_BRANCH_SHA_DRIFT")
    for path,blob in ((NCA_PATH,NCA_BLOB),(TRAINING_PATH,TRAINING_BLOB)):
        f=root/path
        if not f.is_file() or f.is_symlink() or not f.resolve().is_relative_to(root):
            raise RuntimeError("AC16_CURRENT_NATIVE_FILE_UNSAFE:"+path)
        if ac10.git(root,"hash-object","--",path)!=blob:
            raise RuntimeError("AC16_CURRENT_NATIVE_BLOB_DRIFT:"+path)
    if ac10.git(root,"status","--porcelain","--untracked-files=no"):
        raise RuntimeError("AC16_NATIVE_WORKTREE_DIRTY")
    sys.path.insert(0,str(root/"src"))
    from yggdrasil.nca import NCAConfig,NeuralCellularAutomaton
    if (NeuralCellularAutomaton.__module__!="yggdrasil.nca" or
        not all(hasattr(NeuralCellularAutomaton,x) for x in
                ("perceive","alive_mask","step","run","parameter_count"))):
        raise RuntimeError("AC16_ORIGINAL_NCA_INTERFACE_DRIFT")
    return NCAConfig,NeuralCellularAutomaton

def validate_parent(parent:dict):
    if (parent.get("schema")!=ac15.SCHEMA or
        parent.get("scope")!="AUTHENTIC_PUBLIC_DEVELOPMENT_LEARNER_CONTROL_ONLY" or
        parent.get("upstream_sha")!=ac10.SOURCE_COMMIT or
        parent.get("upstream_tree_sha")!=ac10.SOURCE_TREE or
        parent.get("existing_ygg_commit")!=ac15.YGG_COMMIT or
        parent.get("existing_ygg_git_blob")!=ac15.YGG_BLOB or
        parent.get("fit_observed_action_outcome_updates")!=16 or
        parent.get("retained_checkpoint_bytes")!=164 or
        parent.get("dev_updates")!=0 or
        parent.get("cold_restore_identical") is not True or
        parent.get("fully_fitted_tabular_control_parity") is not True or
        parent.get("scientific_first_use") is not False or
        parent.get("protected_science_family_used") is not False):
        raise RuntimeError("AC16_PARENT_REAL_SOURCE_AND_DEV_FIT_INVALID")
    fit=parent.get("source_fit");dev=parent.get("source_dev")
    ac15.validate_source(fit,"FIT")
    ac15.validate_source(dev,"DEV")
    return fit,dev

def sample_rows(source:dict):
    rows=[]
    for episode in source["episodes"]:
        for event in episode["events"]:
            if set(event)!=ac15.FIELDS:
                raise RuntimeError("AC16_SOURCE_PUBLIC_WHITELIST_DRIFT")
            y=ac15.outcome(event)
            if type(y) is not int or y not in (0,1):
                raise RuntimeError("AC16_SOURCE_TARGET_NOT_BINARY")
            rows.append((int(event["stage"]),int(event["observation"]),int(event["action"]),y))
    return rows

def spatial_encode(rows,device="cpu"):
    """Strictly spatial, no global/privileged source or action-value readout."""
    x=torch.zeros((len(rows),STATE_CHANNELS,GRID,GRID),dtype=torch.float32,device=device)
    x[:,3,:,:]=1.0  # keep every cell alive; 3x3 local Sobel sees all features
    for i,(stage,observation,action,outcome) in enumerate(rows):
        if any(type(z) is not int or z not in (0,1) for z in (stage,observation,action,outcome)):
            raise RuntimeError("AC16_INVALID_PUBLIC_EVENT_BIT")
        x[i,0,2,1]=float(stage)
        x[i,1,2,2]=float(observation)
        x[i,2,2,3]=float(action)
    return x

def logits(model,x):
    result=model.run(x,steps=STEPS)
    return result[:,4,2,2]

def fresh(NCAConfig,Model):
    return Model(NCAConfig(state_channels=STATE_CHANNELS,
                           hidden_channels=HIDDEN,fire_rate=1.0,
                           alive_channel=3,max_steps=4))

def model_hash(model):
    return digest(b"".join(
        key.encode()+b"\0"+value.detach().cpu().contiguous().numpy().tobytes()
        for key,value in sorted(model.state_dict().items())))

def fit_model(NCAConfig,Model,fit,targets,epochs=EPOCHS):
    torch.manual_seed(SEED)
    m=fresh(NCAConfig,Model)
    m.train()
    input=spatial_encode(fit)
    t=torch.tensor(targets,dtype=torch.float32)
    before=model_hash(m)
    original=float(F.binary_cross_entropy_with_logits(logits(m,input),t).detach())
    opt=torch.optim.Adam(m.parameters(),lr=LR)
    start=time.perf_counter_ns()
    for _ in range(epochs):
        opt.zero_grad(set_to_none=True)
        loss=F.binary_cross_entropy_with_logits(logits(m,input),t)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(),1.0)
        opt.step()
    elapsed=time.perf_counter_ns()-start
    after=model_hash(m)
    with torch.no_grad():
        last=float(F.binary_cross_entropy_with_logits(logits(m,input),t))
    if before==after:
        raise RuntimeError("AC16_NATIVE_UPDATE_PARAMETERS_UNCHANGED")
    if not all(math.isfinite(q) for q in (original,last)):
        raise RuntimeError("AC16_NATIVE_TRAINING_NONFINITE")
    return m,{"initial_fit_logloss":original,"final_fit_logloss":last,
              "train_wall_ns":elapsed,"initial_parameter_sha256":before,
              "trained_parameter_sha256":after,
              "epochs":epochs,"fit_outcome_examples":len(fit)}

def dev_probs(model,rows):
    model.eval()
    with torch.no_grad():
        result=torch.sigmoid(logits(model,spatial_encode(rows))).tolist()
    if any(not math.isfinite(x) or x<0.0 or x>1.0 for x in result):
        raise RuntimeError("AC16_NONFINITE_MODEL_PUBLIC_PREDICTION")
    return result

def tabular_probs(fit,dev):
    counts=defaultdict(lambda:[0,0])
    for stage,obs,arm,y in fit:
        counts[(stage,obs,arm)][y]+=1
    results=[]
    missing=0
    for stage,obs,arm,_ in dev:
        c=counts[(stage,obs,arm)]
        missing+=sum(c)==0
        results.append((1.0+c[1])/(2.0+sum(c)))
    return results,missing

def metrics(probabilities,rows):
    targets=[r[3] for r in rows]
    correct=sum((p>=0.5)==bool(y) for p,y in zip(probabilities,targets))
    return {"binary_accuracy":correct/len(targets),
            "correct_examples":correct,"examples":len(targets),
            "brier":sum((p-y)**2 for p,y in zip(probabilities,targets))/len(targets)}

def run(ygg:Path,parent_path:Path,out:Path):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    Config,Model=verify_current_native(ygg)
    parent=json.loads(parent_path.read_text(encoding="utf-8"))
    fit_doc,dev_doc=validate_parent(parent)
    fit=sample_rows(fit_doc)
    dev=sample_rows(dev_doc)
    if len(fit)!=16 or len(dev)!=8:
        raise RuntimeError("AC16_SOURCE_FIT_DEV_EVENT_COUNTS_INVALID")
    model,training=fit_model(Config,Model,fit,[r[3] for r in fit])
    if model.parameter_count()<=0:
        raise RuntimeError("AC16_NATIVE_HAS_NO_TRAINABLE_PARAMS")
    buff=io.BytesIO()
    torch.save(model.state_dict(),buff)
    blob=buff.getvalue()
    identity=digest(blob)
    cold=fresh(Config,Model)
    cold.load_state_dict(torch.load(io.BytesIO(blob),map_location="cpu",weights_only=True))
    if model_hash(cold)!=model_hash(model):
        raise RuntimeError("AC16_NATIVE_COLD_RESTORE_WEIGHTS_CHANGED")
    before_dev=model_hash(model)
    p=dev_probs(model,dev)
    cold_p=dev_probs(cold,dev)
    if any(abs(a-b)>1e-7 for a,b in zip(p,cold_p)):
        raise RuntimeError("AC16_NATIVE_RESTART_PREDICTION_DRIFT")
    if before_dev!=model_hash(model):
        raise RuntimeError("AC16_DEV_EXPOSED_TO_NATIVE_TRAINER")
    ref,unseen=tabular_probs(fit,dev)
    global_p=(1+sum(r[3] for r in fit))/(2+len(fit))
    pooled=[global_p]*len(dev)
    rotated=[fit[(i+1)%len(fit)][3] for i in range(len(fit))]
    neg,negtraining=fit_model(Config,Model,fit,rotated)
    neg_p=dev_probs(neg,dev)
    if before_dev!=model_hash(model):
        raise RuntimeError("AC16_NEGATIVE_CONTROL_MUTATED_FITTED_MODEL")
    post_native=verify_current_native(ygg)
    assert post_native[1].__name__=="NeuralCellularAutomaton"
    outcome={
        "schema":SCHEMA,
        "scope":"EXTERNAL_SUPERVISED_ADAPTER_ON_UNCHANGED_NATIVE_NCA",
        "current_ygg_native_source_commit":ACTIVE_YGG_SHA,
        "current_ygg_nca_blob":NCA_BLOB,"current_ygg_training_blob":TRAINING_BLOB,
        "original_source_commit":parent["upstream_sha"],
        "actual_source_fit_episodes":fit_doc["source_owned_episodes"],
        "actual_source_dev_episodes":dev_doc["source_owned_episodes"],
        "actual_source_owned_new_episodes":0,
        "fit_public_outcome_examples":len(fit),
        "dev_public_outcome_examples":len(dev),
        "public_observations_only":True,
        "grid":[GRID,GRID],"state_channels":STATE_CHANNELS,
        "hidden_channels":HIDDEN,"local_nca_steps":STEPS,
        "native_trainable_parameter_count":model.parameter_count(),
        "model_training":training,
        "checkpoint_serialized_bytes":len(blob),
        "checkpoint_sha256":identity,
        "native_weight_sha256_before_dev":before_dev,
        "native_weight_sha256_after_dev":model_hash(model),
        "native_checkpoint_cold_restored":True,
        "dev_model_probabilities":[round(float(v),8) for v in p],
        "dev_public_labels":[int(v[3]) for v in dev],
        "dev_fitted_tabular_probabilities":ref,
        "dev_unseen_tabular_context_action_count":unseen,
        "dev_pooled_fitted_prior_probability":global_p,
        "native_dev_prediction_metrics":metrics(p,dev),
        "fitted_tabular_dev_prediction_metrics":metrics(ref,dev),
        "pooled_fitted_dev_prediction_metrics":metrics(pooled,dev),
        "rotated_fit_label_negative_training":negtraining,
        "rotated_fit_label_negative_dev_metrics":metrics(neg_p,dev),
        "trained_on_dev":False,
        "same_observations_and_fit_budget_for_conventional_controls":True,
        "native_model_training_objective_is_original_ygg_morphology_objective":False,
        "actual_distributed_action_policy_executed":False,
        "action_policy_return_measured":False,
        "unfamiliar_family_transfer_measured":False,
        "causal_credit_assignment_established":False,
        "native_repo_code_modified":False,
        "original_source_code_modified":False,
        "scientific_first_use":False,
        "scientific_admission":False,
        "controller_or_queue_modified":False
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(outcome,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return outcome

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--ygg",type=Path,required=True)
    parser.add_argument("--ac15-report",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args()
    r=run(a.ygg,a.ac15_report,a.out)
    print("AC16_REAL_NATIVE_LOCAL_UPDATE_TRAINED=TRUE")
    print("AC16_PUBLIC_FIT="+str(r["fit_public_outcome_examples"]))
    print("AC16_PUBLIC_DEV="+str(r["dev_public_outcome_examples"]))
    print("AC16_NATIVE_BRIER="+str(r["native_dev_prediction_metrics"]["brier"]))
    print("AC16_FITTED_TABULAR_BRIER="+str(r["fitted_tabular_dev_prediction_metrics"]["brier"]))
    print("AC16_SCIENTIFIC_ADMISSION=NO")
