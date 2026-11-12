"""O10 source-only prospective TRAIN/SELECT/DEV, nine frozen models.

A learned two-state public transition operator is trained from query-only
loss without hidden labels or hand-coded action semantics. Conventional
learned baselines and a separately labeled mechanism-oracle diagnostic are
trained on identical role TRAIN observations. No original science or FSA.
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
from public_source import FAMILIES,ROLES,COUNTS,STEPS,role_episodes,role_sha,query_info
from learned_operator import PublicLearnedOperator,SEEDS,EPOCHS,RATE,nll
from conventional import FittedPublicCounts,PublicHistoryLogistic
from o9_gru_original import TrainedMemory

FROZEN=HERE/"O10_FROZEN_PROTOCOL.json"
ARMS=(
    "LEARNED_MARKOV_OPERATOR","ACTION_TIED_OPERATOR",
    "ERASED_MARKOV_OPERATOR","O9_GRU_2",
    "FITTED_PUBLIC_HISTORY_COUNTS","PUBLIC_HISTORY_LOGISTIC",
    "CURRENT_QUERY_COUNTS","ENGINEERED_PUBLIC_PROGRAM_WITNESS",
    "UNIFORM_05_DIAGNOSTIC",
)


def protocol():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o10.learned-causal-memory-operators.public-dev.v1"
    assert p["stage"]=="FROZEN_BEFORE_ANY_O10_SOURCE_OR_MODEL_IMPLEMENTATION"
    assert tuple(p["public_roles"])==ROLES
    assert p["episodes_by_role"]==COUNTS and p["episode_length"]==STEPS
    assert tuple(p["arms"])==ARMS
    assert tuple(p["train"]["seeds"])==SEEDS
    assert p["train"]["operator_epochs"]==EPOCHS
    assert p["train"]["operator_adam_rate"]==RATE
    return p


def query_loss(model,episodes,erase=False):
    total=0.0
    for ep in episodes:
        pred=(model.predict(ep,erased_query=True)
              if erase else model.predict(ep))
        if not math.isfinite(pred) or not 0<=pred<=1:
            raise ValueError("O10_BAD_PUBLIC_QUERY_PROB")
        total+=nll(query_info(ep)["target"],pred)
    return total/len(episodes)


def select_model(arm,train,select):
    candidates=[]
    for seed in SEEDS:
        if arm=="LEARNED_MARKOV_OPERATOR":
            model=PublicLearnedOperator(seed)
        elif arm=="ACTION_TIED_OPERATOR":
            model=PublicLearnedOperator(seed,action_tied=True)
        elif arm=="O9_GRU_2":
            model=TrainedMemory("GRU_2",seed)
        else:
            raise ValueError("O10_MODEL_NOT_DECLARED")
        model.fit(train)
        candidates.append((query_loss(model,select),seed,model))
    candidates.sort(key=lambda x:(x[0],x[1]))
    return candidates[0][2],{
        "public_select_nll":candidates[0][0],
        "selected_seed":candidates[0][1],
        "public_select_all_starts":{str(s):v for v,s,_ in candidates},
    }


def current_rss_peak():
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
        obj=PM()
        obj.cb=ctypes.sizeof(obj)
        try:
            good=ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(),
                ctypes.byref(obj),obj.cb)
            return int(obj.PeakWorkingSetSize) if good else None
        except (OSError,AttributeError):
            return None
    return None


def run():
    protocol()
    before=time.process_time()
    tracemalloc.start()
    outcomes={}
    for family in FAMILIES:
        t=time.process_time()
        batches={role:role_episodes(role,family) for role in ROLES}
        generation_cpu=time.process_time()-t
        digests={role:role_sha(eps) for role,eps in batches.items()}
        if len(set(digests.values()))!=len(ROLES):
            raise ValueError("O10_COLLIDED_ROLES")
        train,select,dev=(batches[role] for role in ROLES)
        arms={}
        fitted={}
        for arm in ("LEARNED_MARKOV_OPERATOR","ACTION_TIED_OPERATOR","O9_GRU_2"):
            t=time.process_time()
            model,sel=select_model(arm,train,select)
            fit_cpu=time.process_time()-t
            checkpoint=model.checkpoint()
            t=time.process_time()
            dev_loss=query_loss(model,dev)
            eval_cpu=time.process_time()-t
            if checkpoint!=model.checkpoint():
                raise ValueError("O10_DEV_CHECKPOINT_MUTATION")
            param_count=(model.parameters() if isinstance(model,PublicLearnedOperator)
                         else model.parameter_count())
            arms[arm]={
                "public_dev_query_nll":dev_loss,
                "fit_and_selection_cpu_seconds":fit_cpu,
                "public_dev_inference_cpu_seconds":eval_cpu,
                "checkpoint_bytes":len(checkpoint),
                "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
                "trained_parameters":param_count,
                "training_updates":model.updates,
                **sel,
            }
            fitted[arm]=model
        learned=fitted["LEARNED_MARKOV_OPERATOR"]
        checkpoint=learned.checkpoint()
        t=time.process_time()
        erased=query_loss(learned,dev,erase=True)
        erased_cpu=time.process_time()-t
        assert learned.checkpoint()==checkpoint
        arms["ERASED_MARKOV_OPERATOR"]={
            "public_dev_query_nll":erased,
            "fit_and_selection_cpu_seconds":0.0,
            "public_dev_inference_cpu_seconds":erased_cpu,
            "checkpoint_bytes":len(checkpoint),
            "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
            "trained_parameters":learned.parameters(),
            "same_fitted_checkpoint":"LEARNED_MARKOV_OPERATOR",
        }
        controls=(
            ("FITTED_PUBLIC_HISTORY_COUNTS",
             lambda:FittedPublicCounts("PUBLIC_HISTORY")),
            ("PUBLIC_HISTORY_LOGISTIC",PublicHistoryLogistic),
            ("CURRENT_QUERY_COUNTS",lambda:FittedPublicCounts("CURRENT")),
            ("ENGINEERED_PUBLIC_PROGRAM_WITNESS",
             lambda:FittedPublicCounts("ENGINEERED_WITNESS",family)),
        )
        for arm,constructor in controls:
            t=time.process_time()
            model=constructor()
            model.fit(train)
            fit_cpu=time.process_time()-t
            checkpoint=model.checkpoint()
            t=time.process_time()
            dev_loss=query_loss(model,dev)
            infer_cpu=time.process_time()-t
            if checkpoint!=model.checkpoint():
                raise ValueError("O10_CONVENTIONAL_DEV_CHANGED")
            arms[arm]={
                "public_dev_query_nll":dev_loss,
                "fit_and_selection_cpu_seconds":fit_cpu,
                "public_dev_inference_cpu_seconds":infer_cpu,
                "checkpoint_bytes":len(checkpoint),
                "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
                "training_updates":model.updates,
                "mechanism_privileged_oracle":arm=="ENGINEERED_PUBLIC_PROGRAM_WITNESS",
            }
        arms["UNIFORM_05_DIAGNOSTIC"]={
            "public_dev_query_nll":nll(0,0.5),
            "fit_and_selection_cpu_seconds":0.0,
            "public_dev_inference_cpu_seconds":0.0,
            "checkpoint_bytes":0,
            "checkpoint_sha256":hashlib.sha256(b"").hexdigest(),
            "training_updates":0,
        }
        if set(arms)!=set(ARMS):
            raise ValueError("O10_FROZEN_ARM_DRIFT")
        best=min(arms[key]["public_dev_query_nll"] for key in (
            "ACTION_TIED_OPERATOR","O9_GRU_2","FITTED_PUBLIC_HISTORY_COUNTS",
            "PUBLIC_HISTORY_LOGISTIC","CURRENT_QUERY_COUNTS"))
        v=arms["LEARNED_MARKOV_OPERATOR"]["public_dev_query_nll"]
        outcomes[family]={
            "source_role_sha256":digests,
            "episode_counts":{r:len(batch) for r,batch in batches.items()},
            "generation_cpu_seconds":generation_cpu,
            "candidate_minus_best_trained_nonoracle_nll_gain":best-v,
            "action_specific_training_ablation_gain":(
                arms["ACTION_TIED_OPERATOR"]["public_dev_query_nll"]-v),
            "state_erasure_loss_increase":erased-v,
            "candidate_vs_fitted_gru2_gain":arms["O9_GRU_2"]["public_dev_query_nll"]-v,
            "arms":arms,
        }
    _,allocation=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.o10.public-development-receipt.v1",
        "development_only":True,
        "protected_scientific_first_use":False,
        "fsa_grant":"NONE",
        "native_architecture_integration":"NONE",
        "source_selection_from_DEV":False,
        "whole_process_cpu_seconds":time.process_time()-before,
        "whole_process_peak_tracemalloc_bytes":allocation,
        "whole_process_peak_rss_bytes":current_rss_peak(),
        "platform":platform.platform(),
        "python":sys.version.split()[0],
        "families":outcomes,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True,allow_nan=False))
