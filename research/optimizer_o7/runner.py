"""O7 public TRAIN/SELECT/DEV screen, no protected or native-model science.

Supervised predictive partition complexity chosen ONLY on SELECT. Strong
recurrent/HMM comparators trained on the SAME public trajectories. New DEV
never updates or selects learners. Preserve every adverse result.
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
from public_source import FAMILIES,ROLES,ROLE_COUNTS,STEPS,episodes,digest,public_examples
from predictive_partition import (
    CAPACITIES,PredictivePartition,FixedPublicCounts,PublicLogistic,
    public_score,nll,
)
from o4_original_controls import PublicRecurrent,PublicActionHMM

PROTOCOL=HERE/"O7_FROZEN_PROTOCOL.json"
ARMS=(
    "LEARNED_PREDICTIVE_PARTITION","RANDOM_SPLIT_PARTITION",
    "FIXED_FIRST3_PARTITION","FULL_SIX_FEATURE_COUNTS",
    "CURRENT_ONLY_COUNTS","FITTED_LOGISTIC",
    "TWO_STATE_RNN_ADAM","TWO_STATE_HMM_EM",
)


def frozen_protocol():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o7.public-predictive-partitions.v1"
    assert p["frozen_stage"]=="PREREGISTERED_BEFORE_GENERATOR_AND_TRAINING_CODE"
    assert tuple(p["roles"])==ROLES
    assert p["episodes_per_family"]==ROLE_COUNTS
    assert p["steps_per_episode"]==STEPS
    assert tuple(p["models"])==ARMS
    assert p["models"]["LEARNED_PREDICTIVE_PARTITION"].startswith("Greedy supervised")
    return p


def fit_select(name,training,selection):
    examples=public_examples(training)
    if name in ARMS[:2]:
        choices=[]
        for cap in CAPACITIES:
            model=PredictivePartition(cap,randomized=name=="RANDOM_SPLIT_PARTITION")
            model.fit(examples)
            choices.append((public_score(model,selection),cap,model))
        choices.sort(key=lambda z:(z[0],z[1]))
        return choices[0][2],{
            "selection_nll":choices[0][0],
            "selected_leaf_budget":choices[0][1],
            "actual_leaf_count":len(choices[0][2].nodes),
            "capacity_trials":{str(c):nll for nll,c,_ in choices},
        }
    if name in ARMS[2:5]:
        if name=="FIXED_FIRST3_PARTITION":
            feature=(0,1,2)
        elif name=="FULL_SIX_FEATURE_COUNTS":
            feature=(0,1,2,3,4,5)
        else:
            feature=(0,1)
        model=FixedPublicCounts(feature,name)
        model.fit(examples)
        return model,{"selection_nll":public_score(model,selection),
                      "selected_leaf_budget":None,
                      "actual_leaf_count":len(model.table)}
    if name=="FITTED_LOGISTIC":
        model=PublicLogistic()
        model.fit(examples)
        return model,{"selection_nll":public_score(model,selection),
                      "selected_leaf_budget":None,
                      "actual_leaf_count":None}
    if name in ARMS[6:]:
        options=[]
        for seed in (17,31):
            model=(PublicRecurrent("RNN_TANH_ADAM_16E",seed)
                   if name=="TWO_STATE_RNN_ADAM" else PublicActionHMM(seed))
            if name=="TWO_STATE_HMM_EM":
                model.fit(training,iterations=12)
            else:
                model.fit(training)
            options.append((public_score(model,selection),seed,model))
        options.sort(key=lambda z:(z[0],z[1]))
        return options[0][2],{
            "selection_nll":options[0][0],
            "selected_seed":options[0][1],
            "selection_restarts":{str(seed):val for val,seed,_ in options},
        }
    raise ValueError("O7_MODEL_NOT_FROZEN")


def rss_bytes():
    if os.name=="posix":
        import resource
        raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(raw if sys.platform=="darwin" else raw*1024)
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
    frozen_protocol()
    tracemalloc.start()
    start=time.process_time()
    families={}
    for family in FAMILIES:
        t=time.process_time()
        dataset={role:episodes(role,family) for role in ROLES}
        source_time=time.process_time()-t
        source_digests={role:digest(dataset[role]) for role in ROLES}
        assert len(set(source_digests.values()))==len(ROLES)
        results={}
        for arm in ARMS:
            t=time.process_time()
            model,selection=fit_select(arm,dataset["O7_TRAIN"],
                                        dataset["O7_SELECT"])
            training_cpu=time.process_time()-t
            check=model.checkpoint()
            t=time.process_time()
            dev_nll=public_score(model,dataset["O7_DEV"])
            dev_cpu=time.process_time()-t
            assert check==model.checkpoint(),"O7_MODEL_CHANGED_DURING_DEV"
            assert math.isfinite(dev_nll)
            results[arm]={
                "dev_nll":dev_nll,
                "fit_and_select_cpu_seconds":training_cpu,
                "dev_inference_cpu_seconds":dev_cpu,
                "checkpoint_bytes":len(check),
                "checkpoint_sha256":hashlib.sha256(check).hexdigest(),
                "train_updates":model.updates,
                **selection,
            }
        learned=results["LEARNED_PREDICTIVE_PARTITION"]["dev_nll"]
        conventional=[x for x in ARMS if x not in
                      ("LEARNED_PREDICTIVE_PARTITION","RANDOM_SPLIT_PARTITION")]
        best=min(results[x]["dev_nll"] for x in conventional)
        uniform_nll=sum(nll(row[2],0.5)
                        for ep in dataset["O7_DEV"] for row in ep)/(
                            len(dataset["O7_DEV"])*STEPS)
        families[family]={
            "sha256_of_roles":source_digests,
            "episodes_by_role":{r:len(dataset[r]) for r in ROLES},
            "source_cpu_seconds":source_time,
            "learned_minus_best_conventional_gain":best-learned,
            "learned_minus_random_partition_gain":(
                results["RANDOM_SPLIT_PARTITION"]["dev_nll"]-learned),
            "learned_vs_erased_uniform_state_nll_gain":uniform_nll-learned,
            "erased_uniform_state_nll":uniform_nll,
            "models":results,
        }
    _,peak_alloc=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.o7.public-development.v1",
        "source_only":True,
        "source_namespace":"o7-new-public-v1",
        "scientific_first_use":False,
        "fsa_admission":"NONE",
        "native_architecture_integration":"NONE",
        "scientific_go":"NOT_EVALUATED",
        "cpu_full_process_seconds":time.process_time()-start,
        "peak_tracemalloc_bytes":peak_alloc,
        "process_rss_highwater_bytes":rss_bytes(),
        "platform":platform.platform(),
        "python":sys.version.split()[0],
        "families":families,
    }


if __name__=="__main__":
    print(json.dumps(run(),sort_keys=True,indent=2,allow_nan=False))
