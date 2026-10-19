"""F124-CX SINGLE source-free capacity×epochs×learner full-process cell.

Each caller is an isolated fresh Python process; it measures one fixed
capacity (8 or 16), one fixed training duration (45 or 135), and one
independently implemented full-BPTT recurrent arm. No scientific originals.
Diagnostic heldout is computed EVEN IF CHECK VETOES admission; ineligible
model evaluation here is diagnostic only, not original-science acceptance.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import numpy as np
import f124ct_sequence_protocol as p
import f124cw_feasibility_audit as toy

ARMS=("attentive","gated")
HIDDENS=(8,16)
EPOCHS=(45,135)

def need(ok,reason):
    if not ok:raise RuntimeError("F124CX_CELL_"+reason)

def load_frozen(arm):
    path=HERE/("f124ct_attentive_causal_memory.py" if arm=="attentive"
             else "f124ct_gated_sequence_control.py")
    # ATTENTION_DIVISOR is initialized at import. Fresh module load AFTER
    # assigning HIDDEN guarantees the correct sqrt(H) for the larger model.
    spec=importlib.util.spec_from_file_location("f124cx_"+arm+"_capacity_isolated",path)
    need(spec is not None and spec.loader is not None,"FROZEN_MODULE_LOAD")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def fit_model(mod,train,check,epochs):
    P=mod.new()
    start,_=mod.evaluate(P,train)
    for epoch in range(epochs):
        for index in p.schedule(epoch):
            grad,_=mod.gradients(P,train[int(index)])
            p.clip_and_update(P,grad)
    final,fit_bit_errors=mod.evaluate(P,train)
    _,check_bit_errors=mod.evaluate(P,check)
    reduction=(start-final)/max(start,1e-9)
    admitted=bool(reduction>=p.MIN_FIT_LOSS_REDUCTION
       and check_bit_errors/(len(check)*p.STEPS_PER_EPISODE*4)
                      <=p.CHECK_ERROR_VETO_RATIO)
    return P,{
      "initial_FIT_BCE":float(start),"final_FIT_BCE":float(final),
      "FIT_bit_errors":int(fit_bit_errors),
      "CHECK_bit_errors":int(check_bit_errors),
      "FIT_loss_reduction":float(reduction),
      "natural_admitted_by_frozen_CHECK_veto":admitted
    }

def run_cell(regime,seed,hidden,epochs,arm):
    need(regime in toy.REGIMES and seed in toy.SEEDS and
         type(hidden) is int and hidden in HIDDENS and
         type(epochs) is int and epochs in EPOCHS and
         arm in ARMS,"ONE_PREREGISTERED_2x2_CELL")
    need(os.environ.get("OPENBLAS_NUM_THREADS")=="1"
         and os.environ.get("OMP_NUM_THREADS")=="1",
         "PINNED_SINGLE_THREAD_NATIVE_WORK")
    p.HIDDEN=hidden
    mod=load_frozen(arm)
    if arm=="attentive":
        need(abs(mod.ATTENTION_DIVISOR-hidden**0.5)<1e-9,
             "DIMENSION_SPECIFIC_ATTENTION_SCALE")
    keys,fit,check,heldout=toy.fixture(regime,seed)
    p.validate(fit,24);p.validate(check,8);p.validate(heldout,8)
    # Neither frozen learner sees the known grammar or keys. They are only
    # delivered whole episode data; no private original scientific sources.
    del keys
    train_start=time.process_time_ns()
    weights,receipt=fit_model(mod,fit,check,epochs)
    training_cpu_ns=time.process_time_ns()-train_start
    _,heldout_bce,heldout_bits=(None,*mod.evaluate(weights,heldout))
    exact=sum(mod.predict_sequence(weights,ep)==
        [x["observed"] for x in ep["events"]] for ep in heldout)
    fit_exact=sum(mod.predict_sequence(weights,ep)==
        [x["observed"] for x in ep["events"]] for ep in fit)
    need(0<=exact<=8 and 0<=fit_exact<=24 and
         int(heldout_bits)>=0 and training_cpu_ns>0,
         "FULL_SEQUENCE_DIAGNOSTIC_MEASUREMENTS")
    return {
      "schema":"mass.f124cx.sourcefree-single-full-BPTT-cell.v1",
      "regime":regime,"seed":seed,"hidden":hidden,"epochs":epochs,"arm":arm,
      "fit_episodes":len(fit),"check_veto_episodes":len(check),
      "heldout_full_episodes":len(heldout),"steps_per_episode":8,
      "trainable_parameters":sum(v.size for v in weights.values()),
      "optim":"original_clipped_SGD_with_original_schedule",
      "full_BPTT":True,
      "frozen_parameter_initializers_unmodified":True,
      "public_training_FIT_SHA256":p.digest(fit),
      "public_veto_CHECK_SHA256":p.digest(check),
      "public_heldout_SHA256":p.digest(heldout),
      "natural_CHECK_veto_admission":receipt["natural_admitted_by_frozen_CHECK_veto"],
      "FIT_initial_BCE":receipt["initial_FIT_BCE"],
      "FIT_final_BCE":receipt["final_FIT_BCE"],
      "FIT_relative_loss_reduction":receipt["FIT_loss_reduction"],
      "FIT_bit_errors":receipt["FIT_bit_errors"],
      "CHECK_bit_errors":receipt["CHECK_bit_errors"],
      "diagnostic_heldout_BCE_even_when_vetoed":float(heldout_bce),
      "diagnostic_heldout_bit_errors_even_when_vetoed":int(heldout_bits),
      "diagnostic_heldout_exact_episodes_of_8":exact,
      "diagnostic_FIT_exact_episodes_of_24":fit_exact,
      "training_process_CPU_ns_excluding_python_boot":training_cpu_ns,
      "diagnostic_heldout_not_scientific_model_admission":True,
      "original_source_or_oracle_imported":False,
      "sourcefree_synthetic_only":True,
      "scientific_firstuse_consumed":0,
      "scientific_acceptance":False
    }

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--regime",required=True,choices=toy.REGIMES)
    a.add_argument("--seed",required=True,type=int)
    a.add_argument("--hidden",required=True,type=int)
    a.add_argument("--epochs",required=True,type=int)
    a.add_argument("--arm",required=True,choices=ARMS)
    v=a.parse_args()
    print(json.dumps(run_cell(v.regime,v.seed,v.hidden,v.epochs,v.arm),
                     sort_keys=True))

if __name__=="__main__":main()
