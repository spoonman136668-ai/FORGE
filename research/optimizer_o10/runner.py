"""O10 public-only paired causal interventions and trained memory comparisons.

Every learner trains ONLY on the base (unmodified) O10_TRAIN and selects
its restart ONLY on base O10_SELECT. Both base and controlled causal
counterfactual O10_DEV are scored after model weights are frozen. Test
paired sensitivity independently of fit success and strong conventional
benchmarks; no protected original first-use or scientific admission.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import tracemalloc

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from public_source import FAMILIES,ROLES,COUNTS,STEPS,pairs_for_role,query_info,role_digest
from trainable_memory import TrainedMemory,KINDS,STARTS
from recurrent_memory import PublicRecurrentMemory,nll
from public_controls import PublicQueryCounts,PublicMemoryLogistic

PROTO=HERE/"O10_FROZEN_PROTOCOL.json"
ARMS=(
    "LEARNED_WRITE_READ_2","GRU_2","GRU_4","O8_GATED_4",
    "PUBLIC_EXPLICIT_EPISODIC","PUBLIC_MEMORY_LOGISTIC",
    "CURRENT_QUERY_COUNTS","ERASED_LEARNED_WRITE_READ_2",
    "UNIFORM_05_DIAGNOSTIC",
)


def protocol_guard():
    p=json.loads(PROTO.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o10.causal-memory-interventions.public-development.v1"
    assert p["stage"]=="SOURCE_ONLY_PROTOCOL_FROZEN_BEFORE_ANY_O10_GENERATOR_OR_RUN"
    assert tuple(p["source"]["roles"])==ROLES
    assert p["source"]["episode_counts"]==COUNTS
    assert p["source"]["episode_steps"]==STEPS
    assert p["source"]["intervention_action_time"]==4
    assert tuple(p["arms"])==ARMS
    assert tuple(STARTS)==(17,31)
    return p


def fit_selected(name,training,selection):
    opts=[]
    for seed in STARTS:
        if name=="LEARNED_WRITE_READ_2":
            model=TrainedMemory("LEARNED_EXTERNAL_WRITE_READ_2",seed)
        elif name in ("GRU_2","GRU_4"):
            model=TrainedMemory(name,seed)
        elif name=="O8_GATED_4":
            model=PublicRecurrentMemory("GATED_4",seed)
        else:
            raise ValueError("O10_UNREGISTERED_FIT_ARM")
        model.fit(training)
        select_loss=sum(nll(query_info(ep)["target"],model.predict(ep))
                        for ep in selection)/len(selection)
        opts.append((select_loss,seed,model))
    opts.sort(key=lambda z:(z[0],z[1]))
    return opts[0][2],{
        "selected_seed":opts[0][1],
        "selection_query_nll":opts[0][0],
        "selection_loss_by_seed":{str(seed):loss for loss,seed,_ in opts},
    }


def score_pair(model,pairs,erased=False):
    base_losses=[]
    twin_losses=[]
    causal_alignment=[]
    abs_input_sensitivity=[]
    for base,twin in pairs:
        b=model.predict(base,erased_query=True) if erased else model.predict(base)
        t=model.predict(twin,erased_query=True) if erased else model.predict(twin)
        if not all(0<z<1 and math.isfinite(z) for z in (b,t)):
            raise ValueError("O10_MODEL_PROBABILITY_NOT_FINITE")
        yb=query_info(base)["target"]
        yt=query_info(twin)["target"]
        base_losses.append(nll(yb,b))
        twin_losses.append(nll(yt,t))
        causal_alignment.append((t-b)*(yt-yb))
        abs_input_sensitivity.append(abs(t-b))
    return {
        "base_dev_query_nll":sum(base_losses)/len(base_losses),
        "intervened_dev_query_nll":sum(twin_losses)/len(twin_losses),
        "paired_dev_query_nll":(sum(base_losses)+sum(twin_losses))/
                               (len(base_losses)+len(twin_losses)),
        "signed_causal_alignment":sum(causal_alignment)/len(causal_alignment),
        "mean_absolute_probability_sensitivity":
            sum(abs_input_sensitivity)/len(abs_input_sensitivity),
    }


class Uniform:
    updates=0
    def predict(self,episode):
        query_info(episode)
        return 0.5
    def checkpoint(self):
        return b""


def rss_bytes():
    if os.name=="posix":
        import resource
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(peak if sys.platform=="darwin" else peak*1024)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class PM(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                      ("PeakWorkingSetSize",ctypes.c_size_t),
                      ("WorkingSetSize",ctypes.c_size_t),
                      ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                      ("QuotaPagedPoolUsage",ctypes.c_size_t),
                      ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                      ("PagefileUsage",ctypes.c_size_t),
                      ("PeakPagefileUsage",ctypes.c_size_t)]
        pm=PM()
        pm.cb=ctypes.sizeof(pm)
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(pm),pm.cb):
            return int(pm.PeakWorkingSetSize)
    return None


def run():
    protocol_guard()
    start=time.process_time()
    tracemalloc.start()
    result={}
    for family in FAMILIES:
        t=time.process_time()
        datasets={role:pairs_for_role(role,family) for role in ROLES}
        generation_cpu=time.process_time()-t
        hashes={role:role_digest(p) for role,p in datasets.items()}
        if len(set(hashes.values()))!=3:
            raise ValueError("O10_SOURCE_ROLE_ID_COLLISION")
        train=tuple(pair[0] for pair in datasets["O10_TRAIN"])
        select=tuple(pair[0] for pair in datasets["O10_SELECT"])
        dev=datasets["O10_DEV"]
        scored={}
        selected={}
        for arm in ARMS[:4]:
            t=time.process_time()
            model,meta=fit_selected(arm,train,select)
            fit_cpu=time.process_time()-t
            state=model.checkpoint()
            t=time.process_time()
            measures=score_pair(model,dev)
            inf_cpu=time.process_time()-t
            if model.checkpoint()!=state:
                raise ValueError("O10_DEV_CHECKPOINT_MUTATION")
            scored[arm]={
                **measures,**meta,
                "fit_and_select_cpu_seconds":fit_cpu,
                "dev_pair_inference_cpu_seconds":inf_cpu,
                "checkpoint_bytes":len(state),
                "checkpoint_sha256":hashlib.sha256(state).hexdigest(),
                "trainable_parameters":model.parameter_count(),
                "training_updates":model.updates,
            }
            selected[arm]=model
        for arm,ctor in (
            ("PUBLIC_EXPLICIT_EPISODIC",
             lambda:PublicQueryCounts("FULL_PUBLIC_EPISODIC")),
            ("PUBLIC_MEMORY_LOGISTIC",PublicMemoryLogistic),
            ("CURRENT_QUERY_COUNTS",
             lambda:PublicQueryCounts("CURRENT_QUERY")),
        ):
            t=time.process_time()
            model=ctor()
            model.fit(train)
            fit_cpu=time.process_time()-t
            state=model.checkpoint()
            t=time.process_time()
            measures=score_pair(model,dev)
            inf_cpu=time.process_time()-t
            assert state==model.checkpoint()
            scored[arm]={
                **measures,
                "fit_and_select_cpu_seconds":fit_cpu,
                "dev_pair_inference_cpu_seconds":inf_cpu,
                "checkpoint_bytes":len(state),
                "checkpoint_sha256":hashlib.sha256(state).hexdigest(),
                "training_updates":model.updates,
                "hand_engineered_history":arm!="CURRENT_QUERY_COUNTS",
            }
        model=selected["LEARNED_WRITE_READ_2"]
        state=model.checkpoint()
        t=time.process_time()
        erased=score_pair(model,dev,erased=True)
        erased_cpu=time.process_time()-t
        assert state==model.checkpoint()
        scored["ERASED_LEARNED_WRITE_READ_2"]={
            **erased,
            "fit_and_select_cpu_seconds":0.0,
            "dev_pair_inference_cpu_seconds":erased_cpu,
            "checkpoint_bytes":len(state),
            "checkpoint_sha256":hashlib.sha256(state).hexdigest(),
            "trained_weight_reference":"LEARNED_WRITE_READ_2",
            "trained_parameters_shared":model.parameter_count(),
        }
        uniform=Uniform()
        scored["UNIFORM_05_DIAGNOSTIC"]={
            **score_pair(uniform,dev),
            "fit_and_select_cpu_seconds":0.0,
            "dev_pair_inference_cpu_seconds":0.0,
            "checkpoint_bytes":0,
            "checkpoint_sha256":hashlib.sha256(b"").hexdigest(),
            "training_updates":0,
        }
        if set(scored)!=set(ARMS):
            raise ValueError("O10_MODEL_INVENTORY_CHANGED")
        strong_controls=("GRU_2","GRU_4","O8_GATED_4",
                         "PUBLIC_EXPLICIT_EPISODIC",
                         "PUBLIC_MEMORY_LOGISTIC","CURRENT_QUERY_COUNTS")
        best=min(scored[arm]["paired_dev_query_nll"] for arm in strong_controls)
        learned=scored["LEARNED_WRITE_READ_2"]
        erased=scored["ERASED_LEARNED_WRITE_READ_2"]
        result[family]={
            "paired_role_source_sha256":hashes,
            "role_episode_pairs":{role:len(v) for role,v in datasets.items()},
            "source_generation_cpu_seconds":generation_cpu,
            "signed_nll_gain_vs_best_fitted_control":
                best-learned["paired_dev_query_nll"],
            "signed_retained_state_nll_gain":
                erased["paired_dev_query_nll"]-learned["paired_dev_query_nll"],
            "causal_alignment_gain_from_retained_memory":
                learned["signed_causal_alignment"]-
                erased["signed_causal_alignment"],
            "arms":scored,
        }
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.o10.public-causal-intervention-receipt.v1",
        "protected_science_first_use":False,
        "scientific_admission":"NONE",
        "native_architecture_promotion":"NONE",
        "training_used_intervention_twins":False,
        "public_dev_weights_frozen":True,
        "complete_process_cpu_seconds":time.process_time()-start,
        "python_traced_peak_bytes":peak,
        "process_rss_peak_bytes":rss_bytes(),
        "platform":platform.platform(),
        "python_version":sys.version.split()[0],
        "families":result,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True,allow_nan=False))
