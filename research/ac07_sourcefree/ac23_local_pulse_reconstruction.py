"""AC-23 local pulse-self-reconstruction in existing source-free AC-21 scaffold.

The candidate never reads a DEV episode and never imports/executes DTR.
Every local retention gate update depends solely on its own site pulse and
own current logit; terminal reward is used only for the cell-5 readout.
The original Yggdrasil implementation is NOT modified or incorporated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import tracemalloc

import ac21_local_temporal_memory as ac21
import ac22_fit_only_retention_diagnostics as ac22

SCHEMA="forge.ac23.fit-only-public-local-self-reconstruction.v1"
LOCAL_ETA=0.20
GATE_SITES=(3,4)
FIT_FOLDS=8
HEAD_UPDATES=7*ac21.PASSES

class LocalPulseReconstruction(ac22.CountingTemporal):
    def __init__(self):
        super().__init__()
        self.local_pulse_update_calls={3:0,4:0}
        self.local_nonzero_pulses={3:0,4:0}
        self._episode=None

    def local_self_reconstruct(self,site,pulse):
        """Reward-blind learning at exactly one original public source site."""
        if site not in GATE_SITES:
            raise ValueError("AC23_NONLOCAL_GATE_SITE")
        ac21.bit(pulse,"LOCAL_SITE_PULSE")
        current=self.gates[site]
        g=ac21.sig(current)
        # Descend 0.5*(pulse - pulse*g)**2 using only own pulse/logit.
        delta=LOCAL_ETA*pulse*pulse*g*(1.-g)*(1.-g)
        self.gates[site]=max(-5.,min(5.,current+delta))
        self.local_pulse_update_calls[site]+=1
        self.local_nonzero_pulses[site]+=int(pulse==1)
        return delta

    def begin_public_episode(self,s1,x1):
        """Only two stage0 public values reach their original source cells."""
        if self._episode is not None:
            raise RuntimeError("AC23_PUBLIC_EPISODE_ALREADY_STARTED")
        s1=ac21.bit(s1,"S1")
        x1=ac21.bit(x1,"X1")
        self._episode=ac21.LocalPublicEpisode(self.gates)
        # The episode stores the previously gated public pulses at sites 3/4
        # before the local, reward-blind self-reconstruction update; the new
        # retention gates affect later episodes, not retroactively this pulse.
        self._episode.stage0(s1,x1)
        self.local_self_reconstruct(3,s1)
        self.local_self_reconstruct(4,x1)

    def finish_public_episode(self,s2,x2,y):
        """Stage1 terminal head sees *only* two-hop delivered local packets."""
        if self._episode is None:
            raise RuntimeError("AC23_PUBLIC_STAGE1_BEFORE_STAGE0")
        ac21.bit(y,"TERMINAL_REWARD")
        msgs,work,s2,x2=self._episode.stage1(s2,x2,rounds=2)
        if set(msgs)!={"s1","x1"}:
            raise RuntimeError("AC23_NONLOCAL_HISTORY_NOT_DELIVERED")
        features=ac21.encode_features(msgs["s1"],msgs["x1"],s2,x2)
        p=ac21.sig(ac21.dot(self.weights,features))
        err=y-p
        self.weights=[max(-6.,min(6.,w+ac21.ETA*err*z))
                      for w,z in zip(self.weights,features)]
        self.messages_delivered+=work
        self.calls_to_two_hop_transport+=1
        self.last_transport_hops=work
        self._episode=None
        self.updates+=1

    def observe(self,h,y):
        if type(h) not in (list,tuple) or len(h)!=4:
            raise ValueError("AC23_PUBLIC_TWO_STAGE_HISTORY_INVALID")
        ac21.bit(y,"TERMINAL_REWARD")
        self.begin_public_episode(h[0],h[1])
        self.finish_public_episode(h[2],h[3],y)

def fit_only_diagnostic(rows):
    if type(rows) is not list or len(rows)!=FIT_FOLDS or (
            tuple(s for s,h,y in rows)!=ac22.FIT_SEEDS):
        raise RuntimeError("AC23_SOURCE_FIT_ROWS_NOT_FROZEN")
    preds=[]
    fold=[]
    message_total=0
    local_calls=0
    peak_bytes=0
    start=time.perf_counter_ns()
    tracemalloc.start()
    try:
        for k,(seed,h_test,y_test) in enumerate(rows):
            training=[(h,y) for j,(_seed,h,y) in enumerate(rows) if j!=k]
            model=ac21.fit(LocalPulseReconstruction(),training)
            if model.updates!=HEAD_UPDATES or any(
                    model.local_pulse_update_calls[site]!=HEAD_UPDATES for site in GATE_SITES):
                raise RuntimeError("AC23_FROZEN_FIT_BUDGET_MISMATCH")
            checkpoint=model.snapshot()
            restored=LocalPulseReconstruction.restore(checkpoint)
            if (checkpoint!=restored.snapshot() or
                model.predict(h_test)!=restored.predict(h_test)):
                raise RuntimeError("AC23_COLD_CHECKPOINT_RESTORE_DRIFT")
            prob=model.predict(h_test)
            if not math.isfinite(prob) or not 0<=prob<=1:
                raise RuntimeError("AC23_UNBOUNDED_FROZEN_FIT_PREDICTION")
            preds.append(prob)
            message_total+=model.messages_delivered
            local_calls+=sum(model.local_pulse_update_calls.values())
            fold.append({
                "original_fit_left_out_seed":seed,
                "true_fit_only_reward":y_test,
                "public_history":list(h_test),
                "prediction":prob,
                "fit_reward_head_updates":model.updates,
                "local_pulse_update_calls":dict(model.local_pulse_update_calls),
                "nonzero_local_pulses":dict(model.local_nonzero_pulses),
                "fit_gate_logits":[model.gates[3],model.gates[4]],
                "fit_gate_amplitudes":[ac21.sig(model.gates[3]),ac21.sig(model.gates[4])],
                "checkpoint_sha256":hashlib.sha256(checkpoint.encode("utf-8")).hexdigest(),
                "checkpoint_bytes":len(checkpoint.encode("utf-8")),
                "original_local_transport_message_deliveries":model.messages_delivered,
            })
        peak_bytes=tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    elapsed_ns=time.perf_counter_ns()-start
    scores=ac22.score(preds,[y for s,h,y in rows])
    if local_calls!=2*HEAD_UPDATES*FIT_FOLDS:
        raise RuntimeError("AC23_LOCAL_GATE_UPDATE_COUNT_DRIFT")
    return {
        "metric":scores,
        "folds":fold,
        "trained_parameter_count":10,
        "local_gate_training_rule":"site_local_pulse_self_reconstruction_reward_independent",
        "local_gate_learning_rate":LOCAL_ETA,
        "gate_initial_logits":[0.,0.],
        "head_learning_rate":ac21.ETA,
        "fit_passes_per_fold":ac21.PASSES,
        "fit_head_updates_per_fold":HEAD_UPDATES,
        "local_pulse_reconstruction_calls_total":local_calls,
        "two_hop_message_deliveries_total":message_total,
        "wall_ns":elapsed_ns,
        "tracemalloc_peak_bytes":peak_bytes,
    }

def run(ac15_path:Path,expected_sha:str,out:Path):
    # Parent AC-22's authenticated original-data reader accesses source FIT
    # only. This new gate does not read prior DEV or call the original DTR.
    b=ac15_path.read_bytes()
    if (expected_sha not in (
          "68508db981776033d403094f237c17dbbfbadf822ac9eca011feb05d50cba286",
          "071512caf92b82d8b3ed619d79d7741447be72bde29ae9b1b64fd42de2e39077")
        or hashlib.sha256(b).hexdigest()!=expected_sha):
        raise RuntimeError("AC23_AUTHENTIC_FIT_SOURCE_SHA_MISMATCH")
    parent=json.loads(b)
    rows=ac22.original_public_fit_only(parent)
    candidate=fit_only_diagnostic(rows)
    controls=ac22.diagnose_fit_only(rows)
    old=controls["fit_only_left_out_metrics"]["learned_local_gates"]["brier"]
    matched=controls["fit_only_left_out_metrics"]["matched_ten_coefficient_full_history_logistic"]["brier"]
    if abs(old-0.22548358626361042)>1e-11 or abs(matched-0.10130774806845362)>1e-11:
        raise RuntimeError("AC23_AC22_FIT_ONLY_PARENT_PARITY_DRIFT")
    results={
        "schema":SCHEMA,
        "scope":"PREREGISTERED_FIT_ONLY_MECHANISM_DIAGNOSIS_NOT_UNSEEN_DEV",
        "ac22_original_parent_sha":"60c33599de4bc2403ecf93dff6c1d8f61d180a24",
        "ac21_original_candidate_sha":"693a8c9e3c7df53a3ba9a48b9a3fce9478c5c1d6",
        "dtr_original_source_commit":ac22.ac15.ac10.SOURCE_COMMIT,
        "ac15_fit_receipt_sha256":hashlib.sha256(b).hexdigest(),
        "source_fit_episodes_reused":8,
        "original_fit_left_out_folds":8,
        "train_per_fold":7,
        "dev_records_read":0,
        "new_dtr_imports_calls_or_episodes":0,
        "all_input_fields_source_public":True,
        "local_gate_update_not_dependent_on_reward_or_distant_state":True,
        "site3_site4_local_self_reconstruction_objective":True,
        "head_stage1_receives_two_hop_locally_transported_public_history":True,
        "transport_signal_tags_remain_handcrafted":True,
        "local_candidate":candidate,
        "parent_fitted_controls":controls["fit_only_left_out_metrics"],
        "parent_control_predictions":controls["fit_only_fold_predictions"],
        "comparative_brier_delta_ac23_minus_ac22":candidate["metric"]["brier"]-old,
        "comparative_brier_delta_ac23_minus_best_ten_parameter_control":candidate["metric"]["brier"]-matched,
        "superior_to_fully_informed_ten_parameter_fit_only_control":candidate["metric"]["brier"]<matched,
        "no_dev_tuning_or_candidate_promotion":True,
        "native_original_or_active_ygg_code_modified":False,
        "wingless_source_modified":False,
        "forge_controller_queue_or_authority_modified":False,
        "source_first_use":False,
        "source_on_policy_actions_returns_measured":False,
        "unknown_family_transfer_tested":False,
        "scientific_admission":False,
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(results,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    return results

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--ac15-report",type=Path,required=True)
    p.add_argument("--sha256",required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    r=run(a.ac15_report,a.sha256,a.out)
    print("AC23_FIT_ONLY_LOCAL_GATE_RECONSTRUCTION=PASS")
    print("AC23_LOCAL_CANDIDATE_BRIER="+str(r["local_candidate"]["metric"]["brier"]))
    print("AC23_TEN_PARAMETER_CONVENTIONAL_BRIER="+str(r["parent_fitted_controls"]["matched_ten_coefficient_full_history_logistic"]["brier"]))
    print("AC23_NEW_SOURCE_EPISODES=ZERO")
    print("AC23_DEV_RECORDS_READ=ZERO")
    print("AC23_SCIENTIFIC_ADMISSION=NO_GO")
