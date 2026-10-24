"""O10 real fresh public fit/selection/dev: phase composition vs prior routing.

No PROTECTED first-use. Independent public role digests and all negative
results logged. DEV NEVER performs training, selection, or parameter update.
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

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from public_source import (FAMILIES,ROLES,ROLE_COUNTS,STEPS,
                           public_episodes,digest,query_info)
from phase import (PublicPhaseComposer,VARIANTS,SEEDS,nll)
from controls import PublicCountControl
from o9_frozen_routing import LearnedEpisodicRouting

PROTOCOL=ROOT/"O10_FROZEN_PROTOCOL.json"
ARMS=("TRAINED_PHASE_MEMORY","FROZEN_PHASE_TRAINED_HEAD",
      "LINEAR_COUNT_MEMORY","ERASE_PHASE_ABLATION",
      "O9_LEARNED_WRITE_READ_FROZEN_CODE","PUBLIC_ENGINEERED_EPISODIC",
      "CURRENT_ONLY_COUNTS","UNIFORM_05_DIAGNOSTIC")


def guard():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o10.learned-composable-phase-public-dev.v1"
    assert p["stage"]=="PROSPECTIVELY_FROZEN_BEFORE_SOURCE_MODEL_OR_DEV_GENERATION"
    assert tuple(p["roles"])==ROLES and p["count_per_role"]==ROLE_COUNTS
    assert p["episode_steps"]==STEPS and p["namespace"]=="o10-20261023-public-compose-v1"
    assert tuple(p["arms"])==ARMS
    assert p["frozen_training"]["random_starts"]==list(SEEDS)
    assert p["frozen_training"]["train_epochs"]==40
    return p


def score(model,episodes,erased=False):
    losses=[]
    for ep in episodes:
        p=model.predict(ep,erased=erased) if erased else model.predict(ep)
        if not math.isfinite(p) or not 0<p<1:
            raise ValueError("O10_NONFINITE_PREDICTION")
        losses.append(nll(query_info(ep)["target"],p))
    return sum(losses)/len(losses)


def select(arm,train,validation):
    if arm not in VARIANTS and arm!="O9_LEARNED_WRITE_READ_FROZEN_CODE":
        raise ValueError("O10_UNREGISTERED_MODEL")
    choices=[]
    for seed in SEEDS:
        model=(LearnedEpisodicRouting("LEARNED_WRITE_READ",seed)
               if arm=="O9_LEARNED_WRITE_READ_FROZEN_CODE" else
               PublicPhaseComposer(arm,seed))
        model.fit(train)
        choices.append((score(model,validation),seed,model))
    choices.sort(key=lambda x:(x[0],x[1]))
    return choices[0][2],{
        "selected_start":choices[0][1],
        "public_select_nll":choices[0][0],
        "select_nll_by_seed":{str(s):n for n,s,_ in choices},
    }


def peak_rss():
    if os.name=="posix":
        import resource
        r=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(r if sys.platform=="darwin" else r*1024)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class PM(ctypes.Structure):
            _fields_=[
                ("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                ("PeakWorkingSetSize",ctypes.c_size_t),
                ("WorkingSetSize",ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                ("PagefileUsage",ctypes.c_size_t),
                ("PeakPagefileUsage",ctypes.c_size_t),
            ]
        pm=PM()
        pm.cb=ctypes.sizeof(pm)
        ok=ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(pm),pm.cb)
        return int(pm.PeakWorkingSetSize) if ok else None
    return None


def record(model,dev,fit_cpu,select_meta=None,erased=False):
    checkpoint=model.checkpoint()
    t=time.process_time()
    loss=score(model,dev,erased=erased)
    dev_cpu=time.process_time()-t
    if checkpoint!=model.checkpoint():
        raise ValueError("O10_DEV_CHECKPOINT_MUTATION")
    r={
        "public_dev_query_nll":loss,
        "fit_select_cpu_s":fit_cpu,
        "dev_query_cpu_s":dev_cpu,
        "checkpoint_bytes":len(checkpoint),
        "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
    }
    if select_meta:
        r.update(select_meta)
    if isinstance(model,PublicPhaseComposer):
        r.update({
            "trainable_parameter_count":6 if model.variant=="FROZEN_PHASE_TRAINED_HEAD" else 8,
            "inference_public_state_scalars":5,
            "retained_full_history_events":0,
            "training_updates":model.updates,
        })
    elif isinstance(model,LearnedEpisodicRouting):
        r.update({"trainable_parameter_count":24,
                  "inference_stored_public_events_max":19,
                  "training_updates":model.updates})
    else:
        r.update({"training_updates":model.updates,
                  "hand_engineered_features":model.variant=="PUBLIC_ENGINEERED_EPISODIC"})
    return r


def main():
    guard()
    tracemalloc.start()
    begin=time.process_time()
    output={}
    for family in FAMILIES:
        start=time.process_time()
        data={r:public_episodes(r,family) for r in ROLES}
        src_cpu=time.process_time()-start
        shas={r:digest(data[r]) for r in ROLES}
        if len(set(shas.values()))!=3:
            raise ValueError("O10_PUBLIC_ROLE_HASH_COLLISION")
        train,select_role,dev=(data[x] for x in ROLES)
        arms={}
        models={}
        for name in ("TRAINED_PHASE_MEMORY","FROZEN_PHASE_TRAINED_HEAD",
                     "LINEAR_COUNT_MEMORY","O9_LEARNED_WRITE_READ_FROZEN_CODE"):
            t=time.process_time()
            m,meta=select(name,train,select_role)
            cost=time.process_time()-t
            arms[name]=record(m,dev,cost,meta)
            models[name]=m
        m=models["TRAINED_PHASE_MEMORY"]
        arms["ERASE_PHASE_ABLATION"]=record(
            m,dev,0,{"uses_selected_checkpoint":"TRAINED_PHASE_MEMORY"},erased=True)
        for name in ("PUBLIC_ENGINEERED_EPISODIC","CURRENT_ONLY_COUNTS"):
            t=time.process_time()
            m=PublicCountControl(name)
            m.fit(train)
            cost=time.process_time()-t
            arms[name]=record(m,dev,cost)
        arms["UNIFORM_05_DIAGNOSTIC"]={
            "public_dev_query_nll":nll(0,.5),
            "fit_select_cpu_s":0,"dev_query_cpu_s":0,
            "checkpoint_bytes":0,
            "checkpoint_sha256":hashlib.sha256(b"").hexdigest(),
            "training_updates":0,
        }
        learned=arms["TRAINED_PHASE_MEMORY"]["public_dev_query_nll"]
        output[family]={
            "source_role_sha256":shas,
            "source_episode_counts":{r:len(data[r]) for r in ROLES},
            "source_cpu_seconds":src_cpu,
            "learned_minus_frozen_phase_gain":(
                arms["FROZEN_PHASE_TRAINED_HEAD"]["public_dev_query_nll"]-learned),
            "learned_minus_linear_counts_gain":(
                arms["LINEAR_COUNT_MEMORY"]["public_dev_query_nll"]-learned),
            "erased_phase_minus_learned_gain":(
                arms["ERASE_PHASE_ABLATION"]["public_dev_query_nll"]-learned),
            "best_fitted_control_minus_learned_gain":min(
                arms[x]["public_dev_query_nll"] for x in (
                    "O9_LEARNED_WRITE_READ_FROZEN_CODE",
                    "PUBLIC_ENGINEERED_EPISODIC","CURRENT_ONLY_COUNTS",
                    "UNIFORM_05_DIAGNOSTIC"))-learned,
            "arms":arms,
        }
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.o10.public-dev-receipt.v1",
        "science_protected_first_use":False,
        "native_wingless_yggdrasil_integration":False,
        "CKB_FORGE_dispatch_mutation":False,
        "full_process_cpu_s":time.process_time()-begin,
        "tracemalloc_peak_bytes":peak,
        "process_rss_peak_bytes":peak_rss(),
        "platform":platform.platform(),
        "python":sys.version.split()[0],
        "families":output,
    }


if __name__=="__main__":
    print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
