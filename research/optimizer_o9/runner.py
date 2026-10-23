"""O9 prospective native PUBLIC delayed-memory training, selection, ablation.

Authentically fitted recurrent/GRU/episodic controls get identical public
trajectories; only O9_PUBLIC_SELECT chooses initialization. O9_PUBLIC_DEV
never trains. Scientific original, hidden-state labels and old DEV forbidden.
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
from public_source import FAMILIES,ROLES,COUNTS,STEPS,all_public,role_digest,query_info
from trainable_memory import KINDS,STARTS,TrainedMemory,EPOCHS,RATE
from recurrent_memory import PublicRecurrentMemory,nll
from public_controls import PublicQueryCounts,PublicMemoryLogistic

PROTOCOL=HERE/"O9_FROZEN_PROTOCOL.json"
ARMS=(
    "LEARNED_EXTERNAL_WRITE_READ_1",
    "LEARNED_EXTERNAL_WRITE_READ_2",
    "ERASED_EXTERNAL_WRITE_READ_2",
    "GRU_2","GRU_4","O8_GATED_4",
    "PUBLIC_EXPLICIT_EPISODIC","PUBLIC_MEMORY_LOGISTIC",
    "CURRENT_QUERY_COUNTS","UNIFORM_05_DIAGNOSTIC",
)


def check_protocol():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o9.learned-write-read.public-development.v1"
    assert p["state"]=="PROSPECTIVELY_FROZEN_BEFORE_ANY_O9_GENERATOR_MODEL_OR_DEV_RUN"
    assert p["fresh_public_source"]["namespace"]=="o9-public-v1"
    assert tuple(p["fresh_public_source"]["roles"])==ROLES
    assert p["fresh_public_source"]["counts"]==COUNTS
    assert p["fresh_public_source"]["length"]==STEPS
    assert p["training"]["epochs"]==EPOCHS
    assert p["training"]["adam_learning_rate"]==RATE
    assert tuple(p["training"]["initialization_seeds"])==STARTS
    assert tuple(p["models"])==ARMS
    return p


def eval_model(model,eps,erased=False):
    scores=[]
    for ep in eps:
        p=model.predict(ep,erased_query=True) if erased else model.predict(ep)
        scores.append(nll(query_info(ep)["target"],p))
    return sum(scores)/len(scores)


def fit_select(kind,train,selection):
    if kind not in KINDS and kind!="O8_GATED_4":
        raise ValueError("O9_BAD_RECURRENT_NAME")
    candidates=[]
    for seed in STARTS:
        model=(PublicRecurrentMemory("GATED_4",seed)
               if kind=="O8_GATED_4" else TrainedMemory(kind,seed))
        model.fit(train)
        candidates.append((eval_model(model,selection),seed,model))
    candidates.sort(key=lambda x:(x[0],x[1]))
    return candidates[0][2],{
        "public_select_nll":candidates[0][0],
        "selected_seed":candidates[0][1],
        "public_select_all_starts":{str(seed):v for v,seed,_ in candidates},
    }


def rss_bytes():
    if os.name=="posix":
        import resource
        mem=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(mem if sys.platform=="darwin" else 1024*mem)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class PMC(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                      ("PeakWorkingSetSize",ctypes.c_size_t),
                      ("WorkingSetSize",ctypes.c_size_t),
                      ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                      ("QuotaPagedPoolUsage",ctypes.c_size_t),
                      ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                      ("PagefileUsage",ctypes.c_size_t),
                      ("PeakPagefileUsage",ctypes.c_size_t)]
        c=PMC()
        c.cb=ctypes.sizeof(c)
        try:
            ok=ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(c),c.cb)
            return int(c.PeakWorkingSetSize) if ok else None
        except (AttributeError,OSError):
            return None
    return None


def execute():
    check_protocol()
    start=time.process_time()
    tracemalloc.start()
    outcomes={}
    for family in FAMILIES:
        t=time.process_time()
        datasets={role:all_public(role,family) for role in ROLES}
        source_cpu=time.process_time()-t
        sha={role:role_digest(eps) for role,eps in datasets.items()}
        if len(set(sha.values()))!=3:
            raise ValueError("O9_ROLE_ID_COLLISION")
        tr,select,dev=(datasets[k] for k in ROLES)
        fitted={}
        models={}
        for kind in ("LEARNED_EXTERNAL_WRITE_READ_1",
                     "LEARNED_EXTERNAL_WRITE_READ_2",
                     "GRU_2","GRU_4","O8_GATED_4"):
            t=time.process_time()
            model,meta=fit_select(kind,tr,select)
            cpu=time.process_time()-t
            cp=model.checkpoint()
            t=time.process_time()
            loss=eval_model(model,dev)
            infer_cpu=time.process_time()-t
            if cp!=model.checkpoint():
                raise ValueError("O9_DEV_ADAPTED_MODEL")
            fitted[kind]={
                "public_dev_query_nll":loss,
                "fit_select_cpu_seconds":cpu,
                "dev_inference_cpu_seconds":infer_cpu,
                "checkpoint_bytes":len(cp),
                "checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
                "trainable_parameters":model.parameter_count(),
                "learned_state_cells":model.dim,
                "training_updates":model.updates,
                **meta,
            }
            models[kind]=model
        target=models["LEARNED_EXTERNAL_WRITE_READ_2"]
        cp=target.checkpoint()
        t=time.process_time()
        erased=eval_model(target,dev,erased=True)
        infer_cpu=time.process_time()-t
        assert target.checkpoint()==cp
        fitted["ERASED_EXTERNAL_WRITE_READ_2"]={
            "public_dev_query_nll":erased,
            "fit_select_cpu_seconds":0.0,
            "dev_inference_cpu_seconds":infer_cpu,
            "checkpoint_bytes":len(cp),
            "checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
            "trainable_parameters":target.parameter_count(),
            "learned_state_cells":0,
            "trained_weight_reference":"LEARNED_EXTERNAL_WRITE_READ_2",
        }
        for kind,constructor in (
            ("PUBLIC_EXPLICIT_EPISODIC",
             lambda:PublicQueryCounts("FULL_PUBLIC_EPISODIC")),
            ("PUBLIC_MEMORY_LOGISTIC",PublicMemoryLogistic),
            ("CURRENT_QUERY_COUNTS",lambda:PublicQueryCounts("CURRENT_QUERY")),
        ):
            t=time.process_time()
            model=constructor()
            model.fit(tr)
            cpu=time.process_time()-t
            cp=model.checkpoint()
            t=time.process_time()
            loss=eval_model(model,dev)
            infer_cpu=time.process_time()-t
            assert model.checkpoint()==cp
            fitted[kind]={
                "public_dev_query_nll":loss,
                "fit_select_cpu_seconds":cpu,
                "dev_inference_cpu_seconds":infer_cpu,
                "checkpoint_bytes":len(cp),
                "checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
                "training_updates":model.updates,
                "public_history_features_prespecified":(
                    kind!="CURRENT_QUERY_COUNTS"),
            }
        fitted["UNIFORM_05_DIAGNOSTIC"]={
            "public_dev_query_nll":nll(0,0.5),
            "fit_select_cpu_seconds":0.0,
            "dev_inference_cpu_seconds":0.0,
            "checkpoint_bytes":0,
            "checkpoint_sha256":hashlib.sha256(b"").hexdigest(),
            "training_updates":0,
        }
        if set(fitted)!=set(ARMS):
            raise ValueError("O9_ARM_INVENTORY_DRIFT")
        best=min(fitted[name]["public_dev_query_nll"] for name in (
            "GRU_2","GRU_4","O8_GATED_4","PUBLIC_EXPLICIT_EPISODIC",
            "PUBLIC_MEMORY_LOGISTIC","CURRENT_QUERY_COUNTS"))
        candidate=fitted["LEARNED_EXTERNAL_WRITE_READ_2"]["public_dev_query_nll"]
        outcomes[family]={
            "role_sha256":sha,
            "source_counts":{role:len(eps) for role,eps in datasets.items()},
            "source_generation_cpu_seconds":source_cpu,
            "candidate_minus_best_trained_control_nll_gain":best-candidate,
            "candidate_memory_retention_gain":(
                fitted["ERASED_EXTERNAL_WRITE_READ_2"]["public_dev_query_nll"]
                -candidate),
            "candidate_vs_two_cell_gru_gain":(
                fitted["GRU_2"]["public_dev_query_nll"]-candidate),
            "arms":fitted,
        }
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.o9.public-memory-study-receipt.v1",
        "development_only":True,
        "protected_first_use":False,
        "fsa_science_admission":"NONE",
        "native_wingless_yggdrasil_integration":"NONE",
        "accepted_candidate":"NONE",
        "full_process_cpu_seconds":time.process_time()-start,
        "peak_tracemalloc_bytes":peak,
        "process_peak_rss_bytes":rss_bytes(),
        "platform":platform.platform(),
        "python":sys.version.split()[0],
        "families":outcomes,
    }


if __name__=="__main__":
    print(json.dumps(execute(),indent=2,sort_keys=True,allow_nan=False))
