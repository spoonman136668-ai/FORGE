"""O9 fresh public TRAIN/SELECT/DEV with all frozen routings and ability witnesses."""
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
from public_source import (FAMILIES,ROLES,COUNTS,STEPS,public_roles,digest,query_info)
from routing import (LearnedEpisodicRouting,VARIANTS,SEEDS,PARAMS,nll)
from controls import PublicCounts
from o8_frozen_recurrent import PublicRecurrentMemory

PROTOCOL=ROOT/"O9_FROZEN_PROTOCOL.json"
ARMS=("LEARNED_WRITE_READ","LEARNED_READ_FIXED_WRITE","FROZEN_RANDOM_ROUTE",
      "ERASED_LEARNED_HISTORY","O8_GATED4_FROZEN_CODE",
      "PUBLIC_EPISODIC_TABLE","CURRENT_QUERY_COUNTS","UNIFORM_NULL")


def frozen_protocol():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o9.learned-write-read-public-development.v1"
    assert p["frozen_stage"]=="FREEZE_PRECEDES_SOURCE_CREATION_MODEL_IMPLEMENTATION_AND_DEV_FIRST_USE"
    assert p["namespace"]=="o9-20261023-memory-routing-v1"
    assert tuple(p["roles"])==ROLES and p["episodes_by_role"]==COUNTS
    assert p["steps_per_episode"]==STEPS
    assert tuple(p["models"])==ARMS
    assert p["frozen_hyperparams"]["learned_epochs"]==40
    assert p["frozen_hyperparams"]["learned_adam_lr"]==.03
    assert p["frozen_hyperparams"]["starts"]==list(SEEDS)
    return p


def score(model, batch, erased=False):
    loss=0.
    for ep in batch:
        prediction=(model.predict(ep,erased=erased) if erased
                    else model.predict(ep))
        if not math.isfinite(prediction) or not 0 < prediction < 1:
            raise ValueError("O9_NONFINITE_PUBLIC_PREDICTION")
        loss+=nll(query_info(ep)["target"],prediction)
    return loss/len(batch)


def selected(kind,train,select):
    options=[]
    for seed in SEEDS:
        if kind=="O8_GATED4_FROZEN_CODE":
            model=PublicRecurrentMemory("GATED_4",seed)
        else:
            model=LearnedEpisodicRouting(kind,seed)
        model.fit(train)
        options.append((score(model,select),seed,model))
    options.sort(key=lambda r:(r[0],r[1]))
    return options[0][2],{
        "public_select_nll":options[0][0],
        "public_select_by_start":{str(seed):loss for loss,seed,_ in options},
        "selected_start":options[0][1],
    }


def peak_rss_bytes():
    if os.name=="posix":
        import resource
        x=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(x if sys.platform=="darwin" else x*1024)
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


def main():
    frozen_protocol()
    tracemalloc.start()
    start=time.process_time()
    families={}
    for family in FAMILIES:
        source_t=time.process_time()
        born={role:public_roles(role,family) for role in ROLES}
        digests={role:digest(batch) for role,batch in born.items()}
        if len(set(digests.values()))!=3:
            raise ValueError("O9_SOURCE_ROLE_COLLISION")
        source_cpu=time.process_time()-source_t
        train,select,dev=[born[role] for role in ROLES]
        results={}
        trained={}
        for arm in ("LEARNED_WRITE_READ","LEARNED_READ_FIXED_WRITE",
                    "FROZEN_RANDOM_ROUTE","O8_GATED4_FROZEN_CODE"):
            t=time.process_time()
            model,meta=selected(arm,train,select)
            fit_cpu=time.process_time()-t
            checkpoint=model.checkpoint()
            t=time.process_time()
            value=score(model,dev)
            eval_cpu=time.process_time()-t
            if checkpoint!=model.checkpoint():
                raise ValueError("O9_DEV_LEARNER_MUTATED")
            results[arm]={
                "public_dev_query_nll":value,
                "fit_select_cpu_s":fit_cpu,
                "dev_query_cpu_s":eval_cpu,
                "checkpoint_bytes":len(checkpoint),
                "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
                "total_parameters":(
                    model.parameter_count() if arm=="O8_GATED4_FROZEN_CODE"
                    else PARAMS),
                "trainable_parameters":(
                    model.parameter_count() if arm=="O8_GATED4_FROZEN_CODE"
                    else 24 if arm=="LEARNED_WRITE_READ"
                    else 17 if arm=="LEARNED_READ_FIXED_WRITE" else 3),
                "fit_updates":model.updates,
                **meta,
            }
            trained[arm]=model
        model=trained["LEARNED_WRITE_READ"]
        checkpoint=model.checkpoint()
        t=time.process_time()
        erased_value=score(model,dev,erased=True)
        erased_cpu=time.process_time()-t
        if checkpoint!=model.checkpoint():
            raise ValueError("O9_STATE_ERASURE_MUTATED_TRAINED_MODEL")
        results["ERASED_LEARNED_HISTORY"]={
            "public_dev_query_nll":erased_value,
            "fit_select_cpu_s":0,
            "dev_query_cpu_s":erased_cpu,
            "checkpoint_bytes":len(checkpoint),
            "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
            "training_shared_with":"LEARNED_WRITE_READ",
        }
        for arm in ("PUBLIC_EPISODIC_TABLE","CURRENT_QUERY_COUNTS"):
            t=time.process_time()
            model=PublicCounts(arm,family)
            model.fit(train)
            fit_cpu=time.process_time()-t
            checkpoint=model.checkpoint()
            t=time.process_time()
            value=score(model,dev)
            dev_cpu=time.process_time()-t
            if checkpoint!=model.checkpoint():
                raise ValueError("O9_DEV_CONTROL_MUTATED")
            results[arm]={
                "public_dev_query_nll":value,
                "fit_select_cpu_s":fit_cpu,
                "dev_query_cpu_s":dev_cpu,
                "checkpoint_bytes":len(checkpoint),
                "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
                "training_updates":model.updates,
                "source_aware_engineered_public_features":arm=="PUBLIC_EPISODIC_TABLE",
            }
        results["UNIFORM_NULL"]={
            "public_dev_query_nll":nll(0,.5),
            "fit_select_cpu_s":0.,"dev_query_cpu_s":0.,
            "checkpoint_bytes":0,
            "checkpoint_sha256":hashlib.sha256(b"").hexdigest(),
        }
        learned=results["LEARNED_WRITE_READ"]["public_dev_query_nll"]
        families[family]={
            "source_role_sha256":digests,
            "source_role_sizes":{k:len(v) for k,v in born.items()},
            "source_generation_cpu_s":source_cpu,
            "learned_minus_frozen_route_gain":(
                results["FROZEN_RANDOM_ROUTE"]["public_dev_query_nll"]-learned),
            "learned_minus_fixed_write_gain":(
                results["LEARNED_READ_FIXED_WRITE"]["public_dev_query_nll"]-learned),
            "erased_history_minus_learned_gain":erased_value-learned,
            "best_conventional_minus_learned_gain":min(
                results[name]["public_dev_query_nll"] for name in (
                    "O8_GATED4_FROZEN_CODE","PUBLIC_EPISODIC_TABLE",
                    "CURRENT_QUERY_COUNTS","UNIFORM_NULL"))-learned,
            "arms":results,
        }
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.o9.public-development-only.v1",
        "candidate_admitted_for_scientific_first_use":False,
        "Q21_frozen_roles_consumed":0,
        "native_integration":"NONE",
        "controller_changes":"NONE",
        "whole_process_cpu_seconds":time.process_time()-start,
        "python_peak_tracemalloc_bytes":peak,
        "process_peak_rss_bytes":peak_rss_bytes(),
        "platform":platform.platform(),
        "python_version":sys.version.split()[0],
        "families":families,
    }


if __name__=="__main__":
    print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
