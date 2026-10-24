"""L3 source-disjoint PUBLIC learned neural controls and original L2 parallel baseline.

No language-science GO: aligned synthetic grammar, same public FIT/SELECT
information, not matched parameter/FLOP budgets or real unaligned text.
DEV and NULL are never used for fitting, restarts or architecture tuning.
All measured outcomes and negative arms are retained in native receipts.
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
from public_source import ROLES,COUNTS,SLOTS,dataset,sha,canonical,surface
from neural import ARMS as NEURAL_ARMS,SEEDS,NeuralChunkModel
from l2_original_categorical import PublicChunkLearner

PROTO=HERE/"L3_FROZEN_PROTOCOL.json"
ARMS=("NAR_H13","RNN_H12","SSM_DIAGONAL_H14",
      "PARALLEL_CATEGORICAL_4","UNCONDITIONAL")


def guard():
    p=json.loads(PROTO.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.language.l3.frozen-neural-control-evaluation-v1"
    assert p["stage"]=="PROTOCOL_ALONE_COMMITTED_BEFORE_SOURCE_AND_LEARNERS"
    assert p["namespace"]=="l3-20261023-new-semantic-surface-v1"
    assert p["roles"]==COUNTS and tuple(p["arms"])==ARMS
    assert p["train"]["numpy"]=="2.1.3"
    assert p["governance"]["mode"]=="ADDITIVE_PUBLIC_DEVELOPMENT_ONLY"
    return p


def rss_bytes():
    if os.name=="posix":
        import resource
        x=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(x if sys.platform=="darwin" else x*1024)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class MEM(ctypes.Structure):
            _fields_=[
                ("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                ("PeakWorkingSetSize",ctypes.c_size_t),
                ("WorkingSetSize",ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                ("PagefileUsage",ctypes.c_size_t),
                ("PeakPagefileUsage",ctypes.c_size_t)]
        m=MEM()
        m.cb=ctypes.sizeof(m)
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(m),m.cb):
            return int(m.PeakWorkingSetSize)
    return None


def fit_arm(name,train,selection):
    t=time.process_time()
    if name in NEURAL_ARMS:
        vocab=sorted({s for row in train for s in row["slots"]})
        candidates=[]
        for seed in SEEDS:
            model=NeuralChunkModel(name,seed,vocab).fit(train)
            selected=model.teacher_forced_nll(selection)
            candidates.append((selected,seed,model))
        candidates.sort(key=lambda x:(x[0],x[1]))
        value,chosen,model=candidates[0]
        meta={
            "selected_seed":chosen,
            "select_teacher_forced_mean_chunk_nll":value,
            "all_seeds_SELECT_NLL":{str(seed):nll for nll,seed,_ in candidates},
            "trainable_parameter_count":model.params_count(),
            "optimizer_update_count_each_start":model.updates,
            "trained_seed_count":len(candidates),
        }
    else:
        capacity=4 if name=="PARALLEL_CATEGORICAL_4" else 0
        model=PublicChunkLearner(capacity,False).fit(train,selection)
        meta={
            "selected_seed":None,
            "selection_field_subsets":[list(k) for k in model.subsets],
            "fitted_table_contexts":model.context_entries(),
            "trained_seed_count":1,
            "trainable_parameter_count":None,
        }
    meta["fit_and_SELECT_cpu_seconds"]=time.process_time()-t
    checkpoint=model.checkpoint()
    meta["checkpoint_bytes_including_optimizer"]=len(checkpoint)
    meta["checkpoint_sha256"]=hashlib.sha256(checkpoint).hexdigest()
    meta["serial_dependency_stages"]=8 if name in (
        "RNN_H12","SSM_DIAGONAL_H14") else 1
    meta["actual_parallel_execution"]=False
    meta["training_examples"]=len(train)
    meta["selection_examples"]=len(selection)
    meta["inference_work_unit"]="analytical_matmul_MAC_proxy" if name in NEURAL_ARMS else "categorical_lookup_proxy"
    return model,meta


def evaluate(model,examples,role):
    exact=slots=0
    corrupt_matches=0
    verb=actor=0
    operation_proxy=0
    wall0=time.perf_counter()
    cpu0=time.process_time()
    for row in examples:
        result,work=model.generate(row["meaning"])
        expected=(surface(tuple(row["meaning"])) if role=="L3_NULL_CORRUPT"
                  else tuple(row["slots"]))
        result=tuple(result)
        if len(result)!=len(SLOTS):
            raise ValueError("L3_INCOMPLETE_SENTENCE")
        exact+=(result==expected)
        actor+=(result[0]==expected[0])
        verb+=(result[3]==expected[3])
        slots+=sum(a==b for a,b in zip(result,expected))
        operation_proxy+=work
        if role=="L3_NULL_CORRUPT":
            corrupt_matches+=(result==tuple(row["slots"]))
    wall=time.perf_counter()-wall0
    cpu=time.process_time()-cpu0
    return {
        "records":len(examples),
        "exact_semantic_utterance":exact/len(examples),
        "mean_chunk_accuracy":slots/(len(SLOTS)*len(examples)),
        "actor_accuracy":actor/len(examples),
        "verb_inflection_accuracy":verb/len(examples),
        "corrupted_target_false_exact_rate":(
            corrupt_matches/len(examples) if role=="L3_NULL_CORRUPT" else None),
        "inference_CPU_seconds":cpu,
        "measured_serial_wall_us_per_utterance":wall/len(examples)*1e6,
        "analytical_MAC_or_lookup_proxy_not_measured_FLOPs":operation_proxy
    }


def run():
    guard()
    import numpy as np
    if np.__version__!="2.1.3":
        raise ValueError("L3_PINNED_NUMPY_VERSION_DRIFT")
    tracemalloc.start()
    start=time.process_time()
    source0=time.process_time()
    rows={role:dataset(role) for role in ROLES}
    hashes={role:sha(role) for role in ROLES}
    groups={role:{tuple(x["meaning"]) for x in batch}
            for role,batch in rows.items()}
    for i,role in enumerate(ROLES):
        if len(groups[role])!=COUNTS[role]:
            raise ValueError("L3_ROLE_DUPLICATE")
        for previous in ROLES[:i]:
            if groups[role]&groups[previous]:
                raise ValueError("L3_CROSS_ROLE_EXACT_TUPLE_LEAKAGE")
    src_cpu=time.process_time()-source0
    train,select=rows["L3_TRAIN"],rows["L3_SELECT"]
    fitted={}
    meta={}
    for arm in ARMS:
        model,receipt=fit_arm(arm,train,select)
        fitted[arm]=model
        meta[arm]=receipt
    frozen={arm:meta[arm]["checkpoint_sha256"] for arm in ARMS}
    results={}
    for role in ROLES:
        results[role]={}
        for arm in ARMS:
            results[role][arm]=evaluate(fitted[arm],rows[role],role)
            if hashlib.sha256(fitted[arm].checkpoint()).hexdigest()!=frozen[arm]:
                raise ValueError("L3_FROZEN_EVALUATION_MUTATED_TRAINED_MODEL")
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.language.l3.native-neural-comparison.v1",
        "scope":"SYNTHETIC_PUBLIC_DEV_ONLY",
        "science_promotion":False,
        "prior_L1_L2_dev_roles_consumed":0,
        "Q21_FSA_protected_first_use":False,
        "unchanged_active_native_research":True,
        "external_unaligned_natural_language_source":False,
        "fully_resource_matched_trained_transformer_baseline":False,
        "actual_parallel_execution":False,
        "energy_joules":"NOT_MEASURED",
        "real_hardware_FLOPs":"NOT_MEASURED",
        "coding_reasoning_math_multilingual":"NOT_EVALUATED",
        "numpy_version":np.__version__,
        "source_sha256":hashes,
        "source_role_counts":COUNTS,
        "train_corpus_serialized_bytes":len(canonical(train)),
        "selection_corpus_serialized_bytes":len(canonical(select)),
        "source_generation_cpu_seconds":src_cpu,
        "models":meta,
        "evaluations":results,
        "whole_process_cpu_seconds":time.process_time()-start,
        "peak_python_tracemalloc_bytes":peak,
        "peak_process_rss_bytes":rss_bytes(),
        "platform":platform.platform(),
    }


if __name__=="__main__":
    print(json.dumps(run(),sort_keys=True,indent=2,allow_nan=False))
