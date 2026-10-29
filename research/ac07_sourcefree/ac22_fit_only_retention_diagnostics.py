"""AC-22 source-bound FIT-only mechanics, with NO original DTR environment calls.

Only AC-15 previously frozen public FIT may supply examples; source-dev records
are deliberately never read. All trials are fixed eight-way leave-one-out
mechanism diagnostics, not untouched holdout science or candidate selection.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import tracemalloc

import ac15_native_public_adapter as ac15
import ac21_local_temporal_memory as ac21

SCHEMA="forge.ac22.original-public-fit-only-retention-diagnostics.v1"
PASS_COUNT=ac21.PASSES
FIT_SEEDS=tuple(ac15.FIT)
PARAM_COUNTS={
    "learned_local_gates":10,
    "fixed_half_local_gates":8,
    "fixed_near_unit_local_gates":8,
    "direct_full_history_logistic":8,
    "matched_ten_coefficient_full_history_logistic":10,
}

class CountingTemporal(ac21.TemporalRingDev):
    def __init__(self):
        super().__init__()
        self.messages_delivered=0
        self.calls_to_two_hop_transport=0

    def transport(self,h,rounds=2):
        messages,work=super().transport(h,rounds)
        self.messages_delivered+=work
        self.calls_to_two_hop_transport+=int(rounds==2)
        return messages,work

class FrozenGateTemporal(CountingTemporal):
    def __init__(self,logit):
        super().__init__()
        if type(logit) not in (int,float) or logit not in (0.,5.):
            raise ValueError("AC22_UNPREREGISTERED_GATE_INTERVENTION")
        self.initial_gate_logit=float(logit)
        self.gates={3:float(logit),4:float(logit)}
    def observe(self,h,y):
        before=dict(self.gates)
        super().observe(h,y)
        self.gates=before
        if self.gates!=before:
            raise RuntimeError("AC22_FROZEN_GATE_CHANGED")

class TenCoefficientFullHistoryLogistic:
    """Genuinely trained ten-feature fully informed conventional logistic."""
    def __init__(self):
        self.weights=list(ac21.W0)+[0.,0.]
        self.updates=0
    def features(self,h):
        for name,value in zip(("S1","X1","S2","X2"),h):
            ac21.bit(value,name)
        return ac21.encode_features(float(h[0]),float(h[1]),h[2],h[3])+(float(h[0]*h[2]),float(h[1]*h[2]))
    def predict(self,h):
        return ac21.sig(ac21.dot(self.weights,self.features(h)))
    def observe(self,h,y):
        ac21.bit(y,"REWARD")
        x=self.features(h)
        d=y-self.predict(h)
        self.weights=[max(-6.,min(6.,w+ac21.ETA*d*f))
                      for w,f in zip(self.weights,x)]
        self.updates+=1

def make_models():
    return {
        "learned_local_gates":CountingTemporal(),
        "fixed_half_local_gates":FrozenGateTemporal(0.),
        "fixed_near_unit_local_gates":FrozenGateTemporal(5.),
        "direct_full_history_logistic":ac21.FullHistoryLogisticControl(),
        "matched_ten_coefficient_full_history_logistic":TenCoefficientFullHistoryLogistic(),
    }

def original_public_fit_only(report):
    # No access to source_dev is allowed here. Even provenance verification
    # uses only the parent header and original source-owned FIT records.
    if (type(report) is not dict or
        report.get("schema")!=ac15.SCHEMA or
        report.get("upstream_sha")!=ac15.ac10.SOURCE_COMMIT or
        report.get("upstream_tree_sha")!=ac15.ac10.SOURCE_TREE or
        report.get("existing_ygg_commit")!=ac15.YGG_COMMIT or
        report.get("fit_observed_action_outcome_updates")!=16 or
        report.get("dev_updates")!=0 or
        report.get("scientific_first_use") is not False or
        report.get("protected_science_family_used") is not False or
        report.get("native_wingless_or_yggdrasil_source_modified") is not False):
        raise RuntimeError("AC22_AUTHENTIC_PARENT_SOURCE_CUSTODY_NOT_ESTABLISHED")
    source_fit=report.get("source_fit")
    ac15.validate_source(source_fit,"FIT")
    # TRAINING inputs: first and second *public* observations + actions only.
    episodes=source_fit["episodes"]
    if len(episodes)!=8 or tuple(e["seed"] for e in episodes)!=FIT_SEEDS:
        raise RuntimeError("AC22_FIT_SOURCE_IDENTITY_CHANGED")
    return [(episode["seed"],)+ac21.history(episode) for episode in episodes]

def score(predictions,labels):
    if len(predictions)!=8 or len(labels)!=8 or any(
        not math.isfinite(p) or not 0<=p<=1 for p in predictions):
        raise RuntimeError("AC22_INVALID_FIT_LEFT_OUT_PREDICTIONS")
    return {"n":len(labels),
            "brier":sum((p-y)**2 for p,y in zip(predictions,labels))/len(labels),
            "correct_at_half":sum((p>=.5)==bool(y) for p,y in zip(predictions,labels)),
            "mean_prediction":sum(predictions)/len(predictions)}

def diagnose_fit_only(rows):
    if (type(rows) is not list or len(rows)!=8 or
        tuple(row[0] for row in rows)!=FIT_SEEDS):
        raise RuntimeError("AC22_FIT_ONLY_ROWS_INVALID")
    predictions={key:[] for key in PARAM_COUNTS}
    reports={key:[] for key in PARAM_COUNTS}
    labels=[y for seed,h,y in rows]
    total_messages={key:0 for key in PARAM_COUNTS}
    time_ns={key:0 for key in PARAM_COUNTS}
    peak_bytes={}
    tracemalloc.start()
    try:
        for left_out in range(8):
            train=[(h,y) for i,(_seed,h,y) in enumerate(rows) if i!=left_out]
            if len(train)!=7:
                raise RuntimeError("AC22_FIT_FOLD_SIZE_DRIFT")
            _seed,h_test,label=rows[left_out]
            for key,model in make_models().items():
                start=time.perf_counter_ns()
                ac21.fit(model,train)
                if model.updates!=PASS_COUNT*7:
                    raise RuntimeError("AC22_TRAINING_UPDATE_BUDGET_CHANGED")
                if key.startswith("fixed_") and model.gates!={3:model.initial_gate_logit,4:model.initial_gate_logit}:
                    raise RuntimeError("AC22_FIXED_INTERVENTION_NOT_FROZEN")
                if key=="learned_local_gates":
                    checkpoint=model.snapshot()
                    cold=ac21.TemporalRingDev.restore(checkpoint)
                    if cold.snapshot()!=checkpoint or cold.predict(h_test)!=model.predict(h_test):
                        raise RuntimeError("AC22_ORIGINAL_AC21_COLD_RESTORE_CHANGED")
                else:
                    checkpoint=None
                if hasattr(model,"transport"):
                    # Explicitly compare the packet-delivered features with
                    # the same public bits mathematically held by local cells:
                    # this is an identity check, not a parallel learner.
                    f=model.local_features(h_test)
                    exact=ac21.encode_features(h_test[0]*ac21.sig(model.gates[3]),
                        h_test[1]*ac21.sig(model.gates[4]),h_test[2],h_test[3])
                    if f!=exact:
                        raise RuntimeError("AC22_TEMPORAL_TRANSPORT_INFORMATION_LOST")
                prediction=model.predict(h_test)
                if not math.isfinite(prediction):
                    raise RuntimeError("AC22_PREDICTION_NOT_FINITE")
                work=getattr(model,"messages_delivered",0)
                total_messages[key]+=work
                elapsed=time.perf_counter_ns()-start
                time_ns[key]+=elapsed
                predictions[key].append(prediction)
                r={"seed":_seed,"p":prediction,"true_fit_only_reward":label,
                   "trained_updates":model.updates,
                   "trained_parameter_count":PARAM_COUNTS[key],
                   "message_deliveries_fold":work}
                if key=="learned_local_gates":
                    g=[model.gates[3],model.gates[4]]
                    r.update({"gate_logits_after_fit":g,
                              "gate_probabilities_after_fit":[ac21.sig(z) for z in g],
                              "gate_logits_initial":[0.,0.],
                              "checkpoint_sha256":hashlib.sha256(checkpoint.encode()).hexdigest(),
                              "checkpoint_bytes":len(checkpoint.encode())})
                reports[key].append(r)
        peak=tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    metrics={key:score(value,labels) for key,value in predictions.items()}
    return {
        "schema":SCHEMA,
        "scope":"FIT_ONLY_DIAGNOSTIC_NOT_NEW_DEV_OR_FIRST_USE",
        "original_source_commit":ac15.ac10.SOURCE_COMMIT,
        "original_ygg_causal_cells_commit":ac15.YGG_COMMIT,
        "ac21_parent_qualified_sha":"693a8c9e3c7df53a3ba9a48b9a3fce9478c5c1d6",
        "fit_seeds":list(FIT_SEEDS),
        "fit_examples_only":8,"leave_one_out_fit_folds":8,
        "train_examples_each_fold":7,
        "fit_passes_each_fold":PASS_COUNT,
        "updates_each_model_each_fold":PASS_COUNT*7,
        "original_dtr_source_imports_or_episodes":0,
        "previous_dev_episodes_read":0,
        "new_source_episodes":0,
        "local_public_packet_tagging_is_fixed":True,
        "native_ygg_source_modified":False,
        "active_forge_queue_controller_modified":False,
        "model_directed_actions_or_returns":False,
        "cross_family_transfer_tested":False,
        "scientific_first_use":False,"scientific_admission":False,
        "candidate_eligibility_decision":"NO_GO_PREVIOUS_DEV_ALREADY_USED",
        "model_parameter_counts":PARAM_COUNTS,
        "fit_only_left_out_metrics":metrics,
        "fit_only_fold_predictions":reports,
        "total_local_packet_deliveries_by_model":total_messages,
        "fit_only_fold_benchmark_wall_ns_by_model":time_ns,
        "fit_only_python_peak_allocated_bytes":peak,
    }

def run(ac15_path:Path,expected_digest:str,out:Path):
    raw=ac15_path.read_bytes()
    actual=hashlib.sha256(raw).hexdigest()
    if expected_digest not in (
      "68508db981776033d403094f237c17dbbfbadf822ac9eca011feb05d50cba286",
      "071512caf92b82d8b3ed619d79d7741447be72bde29ae9b1b64fd42de2e39077"
    ) or actual!=expected_digest:
        raise RuntimeError("AC22_FROZEN_SOURCE_EVIDENCE_HASH_DRIFT")
    parent=json.loads(raw)
    rows=original_public_fit_only(parent)
    result=diagnose_fit_only(rows)
    result["original_fit_receipt_sha256"]=actual
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--ac15-report",type=Path,required=True)
    a.add_argument("--sha256",required=True)
    a.add_argument("--out",type=Path,required=True)
    p=a.parse_args()
    r=run(p.ac15_report,p.sha256,p.out)
    print("AC22_AUTHENTIC_PUBLIC_FIT_ONLY_DIAGNOSIS=PASS")
    for key,metric in r["fit_only_left_out_metrics"].items():
        print("AC22_FIT_ONLY_BRIER_"+key.upper()+"="+str(metric["brier"]))
    print("AC22_DEV_RECORDS_READ=ZERO")
    print("AC22_NEW_SOURCE_EPISODES=ZERO")
    print("AC22_SCIENTIFIC_ADMISSION=NO_GO")
