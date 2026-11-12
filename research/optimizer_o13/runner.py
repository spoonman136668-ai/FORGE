"""O13 prospective fresh public next-bit state and temporal credit comparison.

All arms see the SAME TRAIN/SELECT/DEV public episodes. Hidden source
generator latent is never imported or revealed. No prior O1-O12 source
role, protected original or FSA scientific admission is consumed.
"""
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
from public_source import FAMILIES,ROLES,COUNTS,STEPS,public_episodes,digest
from learned_belief import ARMS as LEARNED_ARMS,SEEDS,LearnedPublicBelief,loss
from o4_frozen_controls import PublicActionHMM,PublicHistoryCounts,score

PROTOCOL=HERE/"O13_FROZEN_PROTOCOL.json"
ARMS=(
    "FULL_CREDIT_BELIEF","STOP_CREDIT_BELIEF",
    "FROZEN_TRANSITION_BELIEF",
    "O4_BATCH_ACTION_HMM_EM","O4_PUBLIC_LAGGED_COUNTS",
    "O4_PUBLIC_CURRENT_COUNTS","ERASE_FULL_BELIEF_STATE"
)


def verify_protocol():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o13.public-predictive-credit-v1"
    assert p["stage"]=="PRECOMMITTED_BEFORE_GENERATOR_LEARNER_OR_PUBLIC_DEV_FIRST_USE"
    assert p["source_namespace"]=="o13-new-public-credit-v1"
    assert tuple(p["roles"])==ROLES and tuple(p["families"])==FAMILIES
    assert p["roles_per_family"]==COUNTS and p["steps_per_episode"]==STEPS
    assert tuple(p["learners"])==ARMS
    assert p["frozen_training"]["epochs"]==24
    assert p["frozen_training"]["finite_difference_eps"]==.0001
    assert p["frozen_training"]["seeds"]==list(SEEDS)
    return p


def eval_loss(model,ep_batch,erased=False):
    if not erased:
        return score(model,ep_batch)
    total=0.0
    n=0
    for ep in ep_batch:
        predictions=model.predict(ep,erased=True)
        for row,p in zip(ep,predictions):
            total+=loss(row[2],p)
            n+=1
    return total/n


def choose(arm,train,selection):
    if arm in ("O4_PUBLIC_LAGGED_COUNTS","O4_PUBLIC_CURRENT_COUNTS"):
        m=PublicHistoryCounts(lagged=(arm=="O4_PUBLIC_LAGGED_COUNTS"))
        m.fit(train)
        val=eval_loss(m,selection)
        return m,{"public_select_nll":val,"selected_seed":None}
    candidates=[]
    for seed in SEEDS:
        m=(PublicActionHMM(seed) if arm=="O4_BATCH_ACTION_HMM_EM"
           else LearnedPublicBelief(arm,seed))
        if arm=="O4_BATCH_ACTION_HMM_EM":
            m.fit(train,iterations=12)
        else:
            m.fit(train)
        candidates.append((eval_loss(m,selection),seed,m))
    candidates.sort(key=lambda row:(row[0],row[1]))
    return candidates[0][2],{
        "public_select_nll":candidates[0][0],
        "selected_seed":candidates[0][1],
        "public_select_by_seed":{str(s):val for val,s,_ in candidates},
    }


def peak_rss_bytes():
    if os.name=="posix":
        import resource
        z=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(z if sys.platform=="darwin" else z*1024)
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
        p=PM()
        p.cb=ctypes.sizeof(p)
        ok=ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(p),p.cb)
        return int(p.PeakWorkingSetSize) if ok else None
    return None


def report():
    verify_protocol()
    start=time.process_time()
    tracemalloc.start()
    families={}
    for family in FAMILIES:
        source_t=time.process_time()
        data={role:public_episodes(role,family) for role in ROLES}
        source_cpu=time.process_time()-source_t
        role_sha={role:digest(batch) for role,batch in data.items()}
        assert len(set(role_sha.values()))==3
        train,select,dev=(data[role] for role in ROLES)
        models={}
        results={}
        for arm in ARMS[:-1]:
            begin=time.process_time()
            m,meta=choose(arm,train,select)
            fit_cpu=time.process_time()-begin
            frozen=m.checkpoint()
            t=time.process_time()
            nll=eval_loss(m,dev)
            dev_cpu=time.process_time()-t
            if frozen!=m.checkpoint():
                raise ValueError("O13_DEV_MODEL_MUTATION")
            results[arm]={
                "public_dev_nextbit_nll":nll,
                "training_and_selection_cpu_s":fit_cpu,
                "dev_inference_cpu_s":dev_cpu,
                "checkpoint_bytes":len(frozen),
                "checkpoint_sha256":hashlib.sha256(frozen).hexdigest(),
                "training_updates":m.updates,
                "model_state_scalars":1 if arm in LEARNED_ARMS else None,
                "learned_parameter_count":(
                    3 if arm=="FROZEN_TRANSITION_BELIEF" else
                    5 if arm in LEARNED_ARMS else None),
                **meta,
            }
            models[arm]=m
        m=models["FULL_CREDIT_BELIEF"]
        cp=m.checkpoint()
        t=time.process_time()
        erased=eval_loss(m,dev,erased=True)
        dev_cpu=time.process_time()-t
        assert cp==m.checkpoint()
        results["ERASE_FULL_BELIEF_STATE"]={
            "public_dev_nextbit_nll":erased,
            "training_and_selection_cpu_s":0.,
            "dev_inference_cpu_s":dev_cpu,
            "checkpoint_bytes":len(cp),
            "checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
            "shares_selected_trained_checkpoint":"FULL_CREDIT_BELIEF",
        }
        full=results["FULL_CREDIT_BELIEF"]["public_dev_nextbit_nll"]
        controls=("O4_BATCH_ACTION_HMM_EM","O4_PUBLIC_LAGGED_COUNTS",
                  "O4_PUBLIC_CURRENT_COUNTS")
        families[family]={
            "source_role_sha256":role_sha,
            "source_episode_counts":{k:len(v) for k,v in data.items()},
            "source_cpu_s":source_cpu,
            "full_minus_one_step_credit_gain":(
                results["STOP_CREDIT_BELIEF"]["public_dev_nextbit_nll"]-full),
            "full_minus_frozen_transition_gain":(
                results["FROZEN_TRANSITION_BELIEF"]["public_dev_nextbit_nll"]-full),
            "full_state_erasure_effect":erased-full,
            "full_minus_strongest_original_control_gain":min(
                results[k]["public_dev_nextbit_nll"] for k in controls)-full,
            "arms":results,
        }
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.o13.public-predictive-credit-receipt.v1",
        "scientific_first_use":False,
        "FSA_Q21_PROTECTED_ROLES_CONSUMED":0,
        "old_O1_O12_DEVELOPMENT_ROLES_CONSUMED":0,
        "promoted_native_candidate":None,
        "whole_process_cpu_s":time.process_time()-start,
        "peak_tracemalloc_bytes":peak,
        "peak_process_rss_bytes":peak_rss_bytes(),
        "platform":platform.platform(),
        "python":sys.version.split()[0],
        "families":families,
    }


if __name__=="__main__":
    print(json.dumps(report(),sort_keys=True,indent=2,allow_nan=False))
