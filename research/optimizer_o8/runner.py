"""O8 public-only trained delayed-query memory and state-erasure qualification.

Fresh source roles have no relation to FSA scientific originals. All learners
receive identical O8_PUBLIC_TRAIN histories and SELECT opportunities;
O8_PUBLIC_DEV never fits, tunes or chooses a learner. Source controls use
only public episode observations/actions; explicit parity is hand-engineered.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from public_source import FAMILIES,ROLES,COUNTS,STEPS,all_public,role_digest,query_info
from recurrent_memory import KINDS,SEEDS,PublicRecurrentMemory,nll
from public_controls import PublicQueryCounts,PublicMemoryLogistic

PROTOCOL = HERE/"O8_FROZEN_PROTOCOL.json"
ARMS = ("GATED_2","GATED_4","VANILLA_4","ERASED_GATED_2",
        "PUBLIC_QUERY_COUNTS","PUBLIC_EPISODIC_TABLE",
        "PUBLIC_LOGISTIC_MEMORY","UNIFORM_05_DIAGNOSTIC")


def protocol_guard():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o8.learned-multistep-predictive-memory.v1"
    assert p["stage"]=="PROSPECTIVELY_FROZEN_BEFORE_ANY_SOURCE_OR_MODEL_CODE"
    assert p["role_namespace"]=="o8-public-20261023-v1"
    assert tuple(p["roles"])==ROLES
    assert p["episodes_by_role"]==COUNTS and p["episode_steps"]==STEPS
    assert p["frozen_training"]["recurrent_epochs"]==12
    assert p["frozen_training"]["adam_rate"]==0.01
    assert p["frozen_training"]["random_initializations"]==list(SEEDS)
    assert len(ARMS)==8
    return p


def eval_query(model, episodes, erased=False):
    loss=0.0
    for ep in episodes:
        p=model.predict(ep,erased_query=True) if erased else model.predict(ep)
        loss+=nll(query_info(ep)["target"],p)
    return loss/len(episodes)


def fit_select(kind, train, selection):
    options=[]
    for seed in SEEDS:
        model=PublicRecurrentMemory(kind,seed)
        model.fit(train)
        options.append((eval_query(model,selection),seed,model))
    options.sort(key=lambda row:(row[0],row[1]))
    return options[0][2],{
        "public_select_nll":options[0][0],
        "selected_seed":options[0][1],
        "public_selection_by_start":{str(seed):val for val,seed,_ in options},
    }


def rss_bytes():
    if os.name=="posix":
        import resource
        value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform=="darwin" else 1024*value)
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
        inst=PM()
        inst.cb=ctypes.sizeof(inst)
        ok=ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(inst),inst.cb)
        return int(inst.PeakWorkingSetSize) if ok else None
    return None


def run():
    protocol_guard()
    beginning=time.process_time()
    tracemalloc.start()
    result={}
    for family in FAMILIES:
        t=time.process_time()
        roles={role:all_public(role,family) for role in ROLES}
        role_sha={role:role_digest(data) for role,data in roles.items()}
        if len(set(role_sha.values()))!=len(ROLES):
            raise ValueError("O8_SOURCE_ROLE_COLLISION")
        generated=time.process_time()-t
        train,select,dev=(roles[role] for role in ROLES)
        arms={}
        trained={}
        for kind in KINDS:
            t=time.process_time()
            model,meta=fit_select(kind,train,select)
            fit_cpu=time.process_time()-t
            cp=model.checkpoint()
            t=time.process_time()
            val=eval_query(model,dev)
            eval_cpu=time.process_time()-t
            assert cp==model.checkpoint(), "O8_DEV_MODEL_MUTATION"
            arms[kind]={
                "dev_query_nll":val,"fit_select_cpu_seconds":fit_cpu,
                "dev_inference_cpu_seconds":eval_cpu,
                "checkpoint_bytes":len(cp),
                "checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
                "learned_state_dimension":model.dim,
                "parameters":model.parameter_count(),
                "training_updates":model.updates,
                **meta,
            }
            trained[kind]=model
        model=trained["GATED_2"]
        cp=model.checkpoint()
        t=time.process_time()
        erased_loss=eval_query(model,dev,erased=True)
        erased_cpu=time.process_time()-t
        assert cp==model.checkpoint()
        arms["ERASED_GATED_2"]={
            "dev_query_nll":erased_loss,
            "fit_select_cpu_seconds":0.0,
            "dev_inference_cpu_seconds":erased_cpu,
            "checkpoint_bytes":len(cp),
            "checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
            "learned_state_dimension":0,
            "parameters":model.parameter_count(),
            "shared_training_with":"GATED_2",
        }
        for name,klass in (
            ("PUBLIC_QUERY_COUNTS",lambda:PublicQueryCounts("CURRENT_QUERY")),
            ("PUBLIC_EPISODIC_TABLE",lambda:PublicQueryCounts("FULL_PUBLIC_EPISODIC")),
            ("PUBLIC_LOGISTIC_MEMORY",PublicMemoryLogistic),
        ):
            t=time.process_time()
            baseline=klass()
            baseline.fit(train)
            fit_cpu=time.process_time()-t
            cp=baseline.checkpoint()
            t=time.process_time()
            val=eval_query(baseline,dev)
            eval_cpu=time.process_time()-t
            assert cp==baseline.checkpoint()
            arms[name]={
                "dev_query_nll":val,"fit_select_cpu_seconds":fit_cpu,
                "dev_inference_cpu_seconds":eval_cpu,
                "checkpoint_bytes":len(cp),
                "checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
                "trained_update_count":baseline.updates,
                "hand_engineered_public_history":name!="PUBLIC_QUERY_COUNTS",
            }
        arms["UNIFORM_05_DIAGNOSTIC"]={
            "dev_query_nll":nll(0,0.5),
            "fit_select_cpu_seconds":0.0,
            "dev_inference_cpu_seconds":0.0,
            "checkpoint_bytes":0,
            "checkpoint_sha256":hashlib.sha256(b"").hexdigest(),
            "training_updates":0,
        }
        conventional=["PUBLIC_QUERY_COUNTS","PUBLIC_EPISODIC_TABLE",
                      "PUBLIC_LOGISTIC_MEMORY"]
        best=min(arms[a]["dev_query_nll"] for a in conventional)
        result[family]={
            "public_source_role_sha256":role_sha,
            "public_role_episode_counts":{k:len(v) for k,v in roles.items()},
            "public_source_generation_cpu_seconds":generated,
            "gated2_vs_best_fitted_control_nll_gain":(
                best-arms["GATED_2"]["dev_query_nll"]),
            "gated2_memory_ablation_gain":(
                arms["ERASED_GATED_2"]["dev_query_nll"]-
                arms["GATED_2"]["dev_query_nll"]),
            "gated4_vs_vanilla4_gain":(
                arms["VANILLA_4"]["dev_query_nll"]-
                arms["GATED_4"]["dev_query_nll"]),
            "arms":arms,
        }
    _,alloc=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.o8.public-delayed-memory-receipt.v1",
        "stage":"PUBLIC_DEV_ONLY_UNADMITTED_SCIENCE",
        "protected_source_first_use":False,
        "FSA_admission":None,
        "accepted_native_candidate":None,
        "model_selection_on_public_DEV":False,
        "whole_process_cpu_seconds":time.process_time()-beginning,
        "whole_process_tracemalloc_peak_bytes":alloc,
        "whole_process_peak_rss_bytes":rss_bytes(),
        "operating_system":platform.platform(),
        "python":sys.version.split()[0],
        "families":result,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True,allow_nan=False))
