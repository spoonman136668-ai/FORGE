"""AC-21 development-only 8-cell temporal memory on prior authentic public DTR FIT/DEV.

This module NEVER imports DTR, creates source episodes, calls a source oracle
or changes historical/current Yggdrasil. It is a new FORGE-side candidate,
not the original Yggdrasil runtime. Tags in local messages are fixed
public-signal transport scaffolding, not learned representations.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import tracemalloc
import ac18_original_ring_dtr as ac18

SCHEMA="forge.ac21.authentic-public-development-local-temporal-memory.v1"
CHECKPOINT_SCHEMA="forge.ac21.local-temporal-checkpoint.v1"
N=8
PASSES=24
ETA=0.06
ETA_GATE=0.04
W0=(0.05,0.08,-0.03,0.04,-0.04,0.02,0.03,-0.02)
NEIGHBORS=tuple(((i-1)%N,(i+1)%N) for i in range(N))

def bit(v,name):
    if type(v) is not int or v not in (0,1):
        raise ValueError("AC21_INVALID_PUBLIC_"+name)
    return v

def history(episode):
    if type(episode) is not dict or type(episode.get("events")) is not list or len(episode["events"])!=2:
        raise ValueError("AC21_INVALID_PUBLIC_EPISODE")
    a,b=episode["events"]
    if (a["stage"]!=0 or b["stage"]!=1 or a["next_observation"]!=b["observation"] or
        a["terminated"] is not False or b["terminated"] is not True or
        b["next_observation"] is not None or a["reward"]!=0 or
        a["valid_actions"]!=[0,1] or b["valid_actions"]!=[0,1] or
        a["truncated"] is not False or b["truncated"] is not False):
        raise ValueError("AC21_SOURCE_PUBLIC_STAGE_CHAIN_INVALID")
    h=(bit(a["observation"],"S1"),bit(a["action"],"X1"),
       bit(b["observation"],"S2"),bit(b["action"],"X2"))
    return h,bit(b["reward"],"TERMINAL_REWARD")

def sig(x):
    return 1/(1+math.exp(-max(-30.,min(30.,x))))

def encode_features(a,b,s2,x2):
    return (1.,a,b,float(s2),float(x2),a*b,a*x2,b*x2)

def dot(weights,features):
    return sum(w*x for w,x in zip(weights,features))

class TemporalRingDev:
    """Two learnable source-cell retention gates and local terminal readout.

    No unrestricted raw-history readout: source-labelled packets start at
    sites 3 (s1) and 4 (x1), travel solely along ring edges for two rounds,
    then site 5 combines delivered packets with current public s2/x2.
    """
    def __init__(self):
        self.weights=list(W0)
        self.gates={3:0.,4:0.}
        self.updates=0
        self.last_transport_hops=0

    def transport(self,h,rounds=2):
        s1,x1,s2,x2=h
        for name,v in zip(("S1","X1","S2","X2"),h):bit(v,name)
        if type(rounds) is not int or rounds not in (0,1,2):
            raise ValueError("AC21_UNAUTHORIZED_TRANSPORT_DEPTH")
        # Only two source cells retain public bits between source stages.
        packets=[{} for _ in range(N)]
        packets[3]["s1"]=s1*sig(self.gates[3])
        packets[4]["x1"]=x1*sig(self.gates[4])
        deliveries=0
        for _ in range(rounds):
            old=packets
            new=[dict(v) for v in old]
            for i in range(N):
                for n in NEIGHBORS[i]:
                    for name,value in old[i].items():
                        if name in new[n] and new[n][name]!=value:
                            raise RuntimeError("AC21_CONFLICTING_PUBLIC_LOCAL_SIGNAL")
                        new[n][name]=value
                        deliveries+=1
            packets=new
        return packets[5].copy(),deliveries

    def local_features(self,h):
        msgs,work=self.transport(h,2)
        if set(msgs)!={"s1","x1"}:
            raise RuntimeError("AC21_TWO_HOP_LOCAL_PUBLIC_HISTORY_MISSING")
        self.last_transport_hops=work
        return encode_features(msgs["s1"],msgs["x1"],h[2],h[3])

    def predict(self,h):
        return sig(dot(self.weights,self.local_features(h)))

    def observe(self,h,y):
        bit(y,"REWARD")
        f=self.local_features(h)
        p=sig(dot(self.weights,f))
        delta=y-p
        old=list(self.weights)
        a,b=f[1],f[2]
        # Site 5 emits a bounded reward-error credit: one hop to cell4;
        # only then a second neighboring hop reaches original cell3.
        credit_route=(5,4,3)
        if not all(b in NEIGHBORS[a] for a,b in zip(credit_route,credit_route[1:])):
            raise RuntimeError("AC21_NONLOCAL_REWARD_CREDIT")
        g3=sig(self.gates[3]); g4=sig(self.gates[4])
        # Analytic local eligibility: only publicly emitted stored signals
        # and the terminal source-owned reward are used for updates.
        d3=(old[1]+old[5]*b+old[6]*h[3])*h[0]*g3*(1-g3)
        d4=(old[2]+old[5]*a+old[7]*h[3])*h[1]*g4*(1-g4)
        self.weights=[max(-6.,min(6.,w+ETA*delta*z))
                      for w,z in zip(self.weights,f)]
        self.gates[3]=max(-5.,min(5.,self.gates[3]+ETA_GATE*delta*d3))
        self.gates[4]=max(-5.,min(5.,self.gates[4]+ETA_GATE*delta*d4))
        self.updates+=1

    def snapshot(self):
        return json.dumps({
            "schema":CHECKPOINT_SCHEMA,"weights":self.weights,
            "gates":[self.gates[3],self.gates[4]],"updates":self.updates,
            "cells":N,"neighbors":NEIGHBORS},
            sort_keys=True,separators=(",",":"),allow_nan=False)

    @classmethod
    def restore(cls,raw):
        if type(raw) is not str or len(raw)>8192:
            raise ValueError("AC21_INVALID_CHECKPOINT_LENGTH")
        x=json.loads(raw)
        if (type(x) is not dict or set(x)!={"schema","weights","gates","updates","cells","neighbors"} or
            x["schema"]!=CHECKPOINT_SCHEMA or x["cells"]!=N or
            x["neighbors"]!=[list(a) for a in NEIGHBORS] or
            type(x["weights"]) is not list or len(x["weights"])!=len(W0) or
            type(x["gates"]) is not list or len(x["gates"])!=2 or
            any(type(z) not in (int,float) or not math.isfinite(z) for z in x["weights"]+x["gates"]) or
            type(x["updates"]) is not int or not 0<=x["updates"]<=1_000_000):
            raise ValueError("AC21_INVALID_CHECKPOINT_SCHEMA")
        m=cls()
        m.weights=list(x["weights"])
        m.gates={3:x["gates"][0],4:x["gates"][1]}
        m.updates=x["updates"]
        if any(abs(w)>6 for w in m.weights) or any(abs(g)>5 for g in m.gates.values()):
            raise ValueError("AC21_CHECKPOINT_PARAMETER_BOUNDS")
        return m

class FullHistoryLogisticControl:
    """Conventional directly-observed full-history logistic, same FIT passes."""
    def __init__(self):
        self.weights=list(W0)
        self.updates=0

    def features(self,h):
        for name,v in zip(("S1","X1","S2","X2"),h):bit(v,name)
        return encode_features(float(h[0]),float(h[1]),h[2],h[3])

    def predict(self,h):
        return sig(dot(self.weights,self.features(h)))

    def observe(self,h,y):
        bit(y,"REWARD")
        f=self.features(h)
        d=y-self.predict(h)
        self.weights=[max(-6.,min(6.,w+ETA*d*x)) for w,x in zip(self.weights,f)]
        self.updates+=1

def fit(model,rows,mask=None):
    if mask not in (None,"s1","x1"):
        raise ValueError("AC21_INVALID_ABLATION")
    for _ in range(PASSES):
        for h,y in rows:
            mh=((0 if mask=="s1" else h[0]),
                (0 if mask=="x1" else h[1]),h[2],h[3])
            model.observe(mh,y)
    if model.updates!=PASSES*len(rows):
        raise RuntimeError("AC21_FIT_BUDGET_UNEXPECTED")
    return model

def predictions(model,rows,mask=None):
    return [model.predict(((0 if mask=="s1" else h[0]),
                           (0 if mask=="x1" else h[1]),h[2],h[3]))
            for h,_ in rows]

def measures(scores,rows):
    if not scores or len(scores)!=len(rows) or any(not math.isfinite(v) or not 0<=v<=1 for v in scores):
        raise RuntimeError("AC21_INVALID_FROZEN_PREDICTIONS")
    return {"n":len(rows),
            "accuracy":sum((s>=.5)==bool(y) for s,(_,y) in zip(scores,rows))/len(rows),
            "brier":sum((s-y)**2 for s,(_,y) in zip(scores,rows))/len(rows)}

def classical_controls(fit_rows,dev_rows):
    prior=sum(y for _,y in fit_rows)/len(fit_rows)
    tab={}
    ema={}
    for h,y in fit_rows:
        yes,n=tab.get(h,(0,0))
        tab[h]=(yes+y,n+1)
        ema[h]=ac18.EMA_ALPHA*y+(1-ac18.EMA_ALPHA)*ema.get(h,prior)
    pooled=[prior for h,y in dev_rows]
    table=[(tab[h][0]+1)/(tab[h][1]+2) if h in tab else prior for h,y in dev_rows]
    keyed=[ema.get(h,prior) for h,y in dev_rows]
    return {"full_history_laplace":measures(table,dev_rows),
            "full_history_acting_ema":measures(keyed,dev_rows),
            "pooled_prior":measures(pooled,dev_rows)}

def run(ac15_path:Path,ac18_path:Path,out:Path):
    parent15=json.loads(ac15_path.read_text(encoding="utf-8"))
    parent18=json.loads(ac18_path.read_text(encoding="utf-8"))
    fit_source,dev_source=ac18.exact_source(parent15)
    if (parent18.get("schema")!=ac18.SCHEMA or
        parent18.get("new_source_owned_episodes")!=0 or
        parent18.get("original_fit_reward_updates")!=16 or
        parent18.get("scientific_first_use") is not False or
        parent18.get("scientific_admission") is not False or
        parent18.get("full_native_task_bridge_admission",{}).get("full_native_runtime_admission")!="NO_GO_PUBLIC_TYPE_MISMATCH"):
        raise RuntimeError("AC21_PARENT_SOURCE_NATIVE_EVIDENCE_INVALID")
    fit_rows=[history(e) for e in fit_source["episodes"]]
    dev_rows=[history(e) for e in dev_source["episodes"]]
    if len(fit_rows)!=8 or len(dev_rows)!=4 or len(set(e["seed"] for e in fit_source["episodes"]+dev_source["episodes"]))!=12:
        raise RuntimeError("AC21_AUTHENTIC_FIT_DEV_COHORT_MISMATCH")
    tracemalloc.start()
    t0=time.perf_counter_ns()
    native=fit(TemporalRingDev(),fit_rows)
    baseline=fit(FullHistoryLogisticControl(),fit_rows)
    no_s1=fit(TemporalRingDev(),fit_rows,mask="s1")
    no_x1=fit(TemporalRingDev(),fit_rows,mask="x1")
    fit_ns=time.perf_counter_ns()-t0
    peak=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    checkpoint=native.snapshot()
    cold=TemporalRingDev.restore(checkpoint)
    before=checkpoint
    models={"native_temporal":measures(predictions(native,dev_rows),dev_rows),
            "matched_full_history_logistic":measures(predictions(baseline,dev_rows),dev_rows),
            "ablation_without_earlier_observation":measures(predictions(no_s1,dev_rows,"s1"),dev_rows),
            "ablation_without_earlier_action":measures(predictions(no_x1,dev_rows,"x1"),dev_rows)}
    models.update(classical_controls(fit_rows,dev_rows))
    if (native.snapshot()!=before or cold.snapshot()!=before or
        predictions(cold,dev_rows)!=predictions(native,dev_rows) or
        any(x.updates!=192 for x in (native,baseline,no_s1,no_x1))):
        raise RuntimeError("AC21_FROZEN_NATIVE_COLD_RESTORE_OR_FIT_BUDGET_FAILED")
    before_one,_=native.transport((1,1,0,1),1)
    after_two,_=native.transport((1,1,0,1),2)
    if "s1" in before_one or set(after_two)!={"s1","x1"}:
        raise RuntimeError("AC21_NONLOCAL_HISTORY_ACCESS")
    changed_gates=sum(abs(native.gates[i])>1e-12 for i in (3,4))
    if not changed_gates or native.weights==list(W0):
        raise RuntimeError("AC21_NO_ACTUAL_LOCAL_LEARNING")
    score=models["native_temporal"]["brier"]
    control_best=min(v["brier"] for k,v in models.items() if k not in
        ("native_temporal","ablation_without_earlier_observation","ablation_without_earlier_action"))
    doc={
        "schema":SCHEMA,
        "scope":"NEW_FORGE_SIDE_LOCAL_TEMPORAL_DEVELOPMENT_CANDIDATE_NOT_ORIGINAL_YGG_MODEL",
        "source_original_commit":parent15["upstream_sha"],
        "original_ygg_historical_source_modified":False,
        "source_fit_episodes_reused":8,"source_dev_episodes_reused":4,
        "new_source_episodes_executed":0,
        "source_private_info_exposed":False,
        "public_reward_train_examples":len(fit_rows),
        "fit_passes":PASSES,"training_updates_per_gradient_model":native.updates,
        "total_candidate_and_ablation_updates":native.updates+no_s1.updates+no_x1.updates,
        "full_history_conventional_logistic_updates":baseline.updates,
        "eight_cells":N,"neighbor_radius":1,"transport_rounds":2,
        "one_round_site5_has_earlier_s1":False,
        "two_round_site5_has_earlier_s1_and_x1":True,
        "fixed_tagged_transport_not_learned_representation":True,
        "local_retention_gates_trained":changed_gates,
        "local_retention_gate_logit_values":[native.gates[3],native.gates[4]],
        "native_temporal_head_coefficients":list(native.weights),
        "trained_parameter_count":10,
        "fit_wall_ns_four_models":fit_ns,
        "fit_peak_allocated_python_bytes_four_models":peak,
        "checkpoint_bytes":len(checkpoint.encode("utf-8")),
        "checkpoint_sha256":hashlib.sha256(checkpoint.encode("utf-8")).hexdigest(),
        "checkpoint_cold_restored_identically_same_platform":True,
        "dev_updates":0,"dev_episodes_scored":4,
        "frozen_dev_results":models,
        "beats_all_fully_informed_controls_on_tiny_dev":score<control_best,
        "realized_model_action_return_measured":False,
        "original_native_task_runtime_modified":False,
        "native_production_integration":False,
        "scientific_first_use":False,"scientific_admission":False,
        "controller_or_queue_modified":False
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(doc,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return doc

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--ac15-report",type=Path,required=True)
    p.add_argument("--ac18-report",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=run(a.ac15_report,a.ac18_report,a.out)
    print("AC21_PUBLIC_TEMPORAL_RETENTION_TRAINED=PASS")
    print("AC21_ACTUAL_AUTHENTIC_PUBLIC_FIT_EXAMPLES=8")
    print("AC21_FROZEN_DEV_BRIER="+str(result["frozen_dev_results"]["native_temporal"]["brier"]))
    print("AC21_MATCHED_LOGISTIC_BRIER="+str(result["frozen_dev_results"]["matched_full_history_logistic"]["brier"]))
    print("AC21_NEW_SOURCE_CALLS=ZERO")
    print("AC21_SCIENTIFIC_ADMISSION=NO")
