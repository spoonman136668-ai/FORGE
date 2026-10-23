"""O14 frozen public zero-shot structural transfer vs original fitted controls.

Training/restart selection uses FIT_A/B *only*. Entire evaluation of ternary,
paired-bit and null worlds is strict one-time public zero-shot: never fit,
checkpoint-select, tune, retrain, reset a learned parameter, or present family
identity to predictors. Source is synthetic PUBLIC, not independently
sourced protected heldout scientific first use.
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
from public_source import (
    FIT_FAMILIES,TRANSFER_FAMILIES,FAMILIES,ROLES,ROLE_COUNTS,
    STEPS,episodes,role_digest,interleaved_fit,canonical,
)
from o13_original_belief import LearnedPublicBelief
from o4_original_controls import (
    PublicRecurrent,PublicActionHMM,PublicHistoryCounts,score,loss,
)

PROTOCOL=HERE/"O14_FROZEN_PROTOCOL.json"
ARMS=(
    "O13_FULL_CREDIT_FROZEN_SOURCE",
    "O13_STOP_CREDIT_FROZEN_SOURCE",
    "O4_RNN_ADAM_16E",
    "O4_ACTION_HMM_EM12",
    "O4_FITTED_LAGGED_COUNTS",
    "O4_FITTED_CURRENT_COUNTS",
    "O13_ERASE_FULL_STATE",
    "UNIFORM_NULL",
)
FIT_ARMS=ARMS[:6]
SEEDS=(17,31)


def assert_prereg():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.o14.zero-shot-structural-transfer-public-dev.v1"
    assert p["frozen_stage"]=="PROSPECTIVE_PROTOCOL_FIRST_COMMIT_BEFORE_ANY_SOURCE_OR_MODEL_IMPLEMENTATION"
    assert p["source_namespace"]=="o14-20261023-structural-transfer-v1"
    assert tuple(p["roles"])==ROLES and tuple(p["families"])==FAMILIES
    assert p["role_family_matrix"]==ROLE_COUNTS and p["steps_per_episode"]==STEPS
    assert tuple(p["arms"])==ARMS
    assert p["selection_policy"].startswith("No selection")
    return p


def nll(model,ep_batch,erased=False):
    if not ep_batch:
        raise ValueError("O14_EMPTY_EVAL")
    if not erased:
        return score(model,ep_batch)
    total=0.
    count=0
    for ep in ep_batch:
        predictions=model.predict(ep,erased=True)
        for row,p in zip(ep,predictions):
            if not math.isfinite(p):
                raise ValueError("O14_NONFINITE_PREDICTION")
            total+=loss(row[2],p)
            count+=1
    return total/count


def fitted_model(arm,train,select):
    if arm=="O4_FITTED_LAGGED_COUNTS":
        m=PublicHistoryCounts(True)
        m.fit(train)
        return m,{"chosen_start":None,"select_nll":nll(m,select)}
    if arm=="O4_FITTED_CURRENT_COUNTS":
        m=PublicHistoryCounts(False)
        m.fit(train)
        return m,{"chosen_start":None,"select_nll":nll(m,select)}
    candidates=[]
    for seed in SEEDS:
        if arm in ARMS[:2]:
            original_name=("FULL_CREDIT_BELIEF" if arm==ARMS[0]
                           else "STOP_CREDIT_BELIEF")
            m=LearnedPublicBelief(original_name,seed)
            m.fit(train)
        elif arm=="O4_RNN_ADAM_16E":
            m=PublicRecurrent("RNN_TANH_ADAM_16E",seed)
            m.fit(train)
        elif arm=="O4_ACTION_HMM_EM12":
            m=PublicActionHMM(seed)
            m.fit(train,iterations=12)
        else:
            raise ValueError("O14_UNREGISTERED_FIT_MODEL")
        candidates.append((nll(m,select),seed,m))
    candidates.sort(key=lambda row:(row[0],row[1]))
    return candidates[0][2],{
        "chosen_start":candidates[0][1],
        "select_nll":candidates[0][0],
        "select_by_start":{str(s):v for v,s,_ in candidates},
    }


def rss_bytes():
    if os.name=="posix":
        import resource
        high=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(high if sys.platform=="darwin" else high*1024)
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
        x=PM()
        x.cb=ctypes.sizeof(x)
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(x),x.cb
        ):
            return int(x.PeakWorkingSetSize)
    return None


def run():
    assert_prereg()
    tracemalloc.start()
    start=time.process_time()
    source_t=time.process_time()
    # The only two roles that may enter ANY fitting/selection call.
    train=interleaved_fit("O14_FIT_TRAIN")
    selection=interleaved_fit("O14_FIT_SELECT")
    train_digest=hashlib.sha256(canonical(train)).hexdigest()
    selection_digest=hashlib.sha256(canonical(selection)).hexdigest()
    assert len(train)==48 and len(selection)==16
    role_families={}
    for role,allowed in ROLE_COUNTS.items():
        for family,count in allowed.items():
            batch=episodes(role,family)
            assert len(batch)==count
            role_families[(family,role)]={"sha256":role_digest(batch),
                                        "episode_count":count}
    generation_cpu=time.process_time()-source_t
    # Allocate and freeze ALL fitted original comparators before evaluation.
    models={}
    fit_receipts={}
    for arm in FIT_ARMS:
        t=time.process_time()
        model,selection_meta=fitted_model(arm,train,selection)
        fit_cpu=time.process_time()-t
        cp=model.checkpoint()
        models[arm]=model
        fit_receipts[arm]={
            "fit_select_cpu_seconds":fit_cpu,
            "training_experience_episodes":len(train),
            "public_select_episodes":len(selection),
            "optimizer_updates":model.updates,
            "checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
            "checkpoint_with_optimizer_bytes":len(cp),
            "dynamic_belief_state_scalars":(
                1 if arm in ARMS[:2] else
                2 if arm in ("O4_RNN_ADAM_16E","O4_ACTION_HMM_EM12")
                else None),
            **selection_meta,
        }
    # Exact state-erasure same already selected and trained FULL model.
    model=models[ARMS[0]]
    cp=model.checkpoint()
    fit_receipts["O13_ERASE_FULL_STATE"]={
        **fit_receipts[ARMS[0]],
        "shared_selected_checkpoint":"O13_FULL_CREDIT_FROZEN_SOURCE",
        "additional_training_cpu_seconds":0.0,
    }
    fit_receipts["UNIFORM_NULL"]={
        "fit_select_cpu_seconds":0.0,"optimizer_updates":0,
        "checkpoint_with_optimizer_bytes":0,
        "checkpoint_sha256":hashlib.sha256(b"").hexdigest(),
        "training_experience_episodes":0,
        "public_select_episodes":0,
        "dynamic_belief_state_scalars":0,
    }
    all_scores={}
    for family in FAMILIES:
        role=("O14_INDOMAIN_DEV" if family in FIT_FAMILIES
              else "O14_ZERO_SHOT_TRANSFER")
        dataset=episodes(role,family)
        scores={}
        for arm in ARMS:
            t=time.process_time()
            if arm=="UNIFORM_NULL":
                score_value=math.log(2)
            elif arm=="O13_ERASE_FULL_STATE":
                score_value=nll(models[ARMS[0]],dataset,erased=True)
            else:
                score_value=nll(models[arm],dataset)
            cpu=time.process_time()-t
            if not math.isfinite(score_value):
                raise ValueError("O14_NONFINITE_DEV_NLL")
            scores[arm]={"nextbit_nll":score_value,
                         "inference_cpu_seconds":cpu}
        original_controls=(ARMS[2],ARMS[3],ARMS[4],ARMS[5])
        learned=scores[ARMS[0]]["nextbit_nll"]
        all_scores[family]={
            "evaluation_role":role,
            "source_sha256":role_families[(family,role)]["sha256"],
            "full_vs_best_trained_conventional_gain":min(
                scores[a]["nextbit_nll"] for a in original_controls)-learned,
            "full_vs_truncated_credit_gain":scores[ARMS[1]]["nextbit_nll"]-learned,
            "erased_full_state_effect":scores["O13_ERASE_FULL_STATE"]["nextbit_nll"]-learned,
            "arms":scores,
        }
    if cp!=models[ARMS[0]].checkpoint():
        raise ValueError("O14_TRANSFER_DID_NOT_FREEZE_LEARNER")
    for arm in FIT_ARMS:
        current=models[arm].checkpoint()
        if fit_receipts[arm]["checkpoint_sha256"]!=hashlib.sha256(current).hexdigest():
            raise ValueError("O14_EVALUATION_MUTATED_MODEL")
    _,allocated=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    public_train_raw_bytes=len(canonical(train))
    public_selection_raw_bytes=len(canonical(selection))
    return {
        "schema":"forge.optimizer.o14.public-structural-zero-shot-receipt.v1",
        "source_namespace":"o14-20261023-structural-transfer-v1",
        "external_independent_scientific_custody":False,
        "FSA_protected_roles_consumed":0,
        "previous_O1_O13_dev_roles_consumed":0,
        "public_fit_family_whitelist":list(FIT_FAMILIES),
        "public_transfer_family_blacklist_during_fit":list(TRANSFER_FAMILIES),
        "source_role_sha256":{
            f"{family}:{role}":info["sha256"]
            for (family,role),info in role_families.items()},
        "interleaved_fit_sha256":train_digest,
        "interleaved_select_sha256":selection_digest,
        "fit_episodes":len(train),
        "select_episodes":len(selection),
        "fit_public_episode_bytes":public_train_raw_bytes,
        "select_public_episode_bytes":public_selection_raw_bytes,
        "source_generation_cpu_seconds":generation_cpu,
        "fit_model_evidence":fit_receipts,
        "evaluations":all_scores,
        "total_process_cpu_seconds":time.process_time()-start,
        "process_rss_highwater_bytes":rss_bytes(),
        "tracemalloc_peak_bytes":allocated,
        "scientific_candidate_promoted":False,
    }


if __name__=="__main__":
    print(json.dumps(run(),sort_keys=True,indent=2,allow_nan=False))
