"""L4 bounded public real-text gap completion and full resource receipts.

The entire data path is pinned to one external Git blob; no external model
API, no downloaded pretrained weights or protected research data. Trained
word-count arms have identical 1,200 source examples; model capacities and
fit algorithms differ, thus NO resource-matched neural/LM Pareto conclusion.
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
from source import ROLES,COUNTS,EXPECTED_GIT_SHA1,load_file,canonical,digest
from models import CategoricalCounts,SelectiveRepair

PROTOCOL=HERE/"L4_FROZEN_PROTOCOL.json"
ARMS=("P_SLOT_INDEPENDENT","SEQ_CONDITIONAL","JOINT_SPAN_COUNT",
      "P_WITH_SELECT_REPAIR","FIT_PRIOR")


def protocol_guard():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.language.l4.realtext-span-development.v1"
    assert p["stage"]=="FROZEN_PROTOCOL_ONLY_COMMIT_BEFORE_RETRIEVAL_CODE_OR_DATA_FIRST_USE"
    assert p["external_corpus"]["source_git_blob_sha1"]==EXPECTED_GIT_SHA1
    assert p["task"]["counts"]==COUNTS
    assert tuple(p["task"]["roles"])==ROLES
    assert tuple(p["models"])==ARMS
    assert p["governance"]["scope"]=="ADDITIVE_PUBLIC_REALTEXT_DEVELOPMENT_ONLY"
    return p


def fit(train,select):
    fitted={}
    evidence={}
    for name,kind in (
        ("P_SLOT_INDEPENDENT","parallel"),
        ("SEQ_CONDITIONAL","sequential"),
        ("JOINT_SPAN_COUNT","joint"),
        ("FIT_PRIOR","prior"),
    ):
        start=time.process_time()
        fitted[name]=CategoricalCounts(kind).fit(train)
        cpu=time.process_time()-start
        evidence[name]={"train_and_SELECT_CPU_seconds":cpu,
                        "fitted_train_records":len(train),
                        "select_records_available_no_model_selection":len(select),
                        "conceptual_dependency_stages":2 if kind=="sequential" else 1,
                        "actual_parallel_execution":False}
    t=time.process_time()
    repair=SelectiveRepair(
        fitted["P_SLOT_INDEPENDENT"],fitted["SEQ_CONDITIONAL"]).select(select)
    selection_cpu=time.process_time()-t
    fitted["P_WITH_SELECT_REPAIR"]=repair
    evidence["P_WITH_SELECT_REPAIR"]={
        "train_and_SELECT_CPU_seconds":(
            evidence["P_SLOT_INDEPENDENT"]["train_and_SELECT_CPU_seconds"]+
            evidence["SEQ_CONDITIONAL"]["train_and_SELECT_CPU_seconds"]+
            selection_cpu),
        "fitted_train_records":len(train),
        "repair_threshold_SELECTED_only":repair.margin,
        "conceptual_dependency_stages":3,
        "actual_parallel_execution":False,
        "both_trained_checkpoints_counted":True,
    }
    for arm in ARMS:
        frozen=fitted[arm].checkpoint()
        evidence[arm].update({
            "checkpoint_bytes_including_underlying_models":len(frozen),
            "checkpoint_sha256":hashlib.sha256(frozen).hexdigest(),
        })
    return fitted,evidence


def rss_bytes():
    if os.name=="posix":
        import resource
        z=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(z if sys.platform=="darwin" else z*1024)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class MEM(ctypes.Structure):
            _fields_=[
                ("cb",wintypes.DWORD),
                ("PageFaultCount",wintypes.DWORD),
                ("PeakWorkingSetSize",ctypes.c_size_t),
                ("WorkingSetSize",ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                ("PagefileUsage",ctypes.c_size_t),
                ("PeakPagefileUsage",ctypes.c_size_t)
            ]
        m=MEM()
        m.cb=ctypes.sizeof(m)
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(m),m.cb):
            return int(m.PeakWorkingSetSize)
    return None


def evaluate(model,batch,train_vocab):
    exact=0
    first=second=0
    no_vocabulary=0
    repairs=0
    operations=0
    predictions_hash=hashlib.sha256()
    start_wall=time.perf_counter()
    start_cpu=time.process_time()
    for row in batch:
        output=model.generate(row)
        if len(output)==3:
            guess,work,repaired=output
            repairs+=repaired
        else:
            guess,work=output
        truth=tuple(row["gold"])
        guess=tuple(guess)
        if len(guess)!=2:
            raise ValueError("L4_INCOMPLETE_GAP")
        exact+=(guess==truth)
        first+=(guess[0]==truth[0])
        second+=(guess[1]==truth[1])
        no_vocabulary+=(truth[0] not in train_vocab or truth[1] not in train_vocab)
        operations+=work
        predictions_hash.update(canonical(guess)+b"\n")
    cpu=time.process_time()-start_cpu
    wall=time.perf_counter()-start_wall
    return {
        "evaluated_rows":len(batch),
        "two_word_exact_match":exact/len(batch),
        "first_word_accuracy":first/len(batch),
        "second_word_accuracy":second/len(batch),
        "gap_has_train_out_of_vocabulary":no_vocabulary/len(batch),
        "predicted_gaps_sha256":predictions_hash.hexdigest(),
        "repair_changes":repairs,
        "categorical_lookup_proxy_not_FLOPs":operations,
        "actual_serial_inference_cpu_s":cpu,
        "actual_serial_wall_us_per_gap":wall/len(batch)*1e6,
    }


def run(path):
    protocol_guard()
    tracemalloc.start()
    started=time.process_time()
    source_cpu0=time.process_time()
    raw_sha,roles=load_file(path)
    generation_cpu=time.process_time()-source_cpu0
    for role in ROLES:
        if len(roles[role])!=COUNTS[role]:
            raise ValueError("L4_SOURCE_ROLE_QUOTA_NOT_MATCHED")
    source_hashes={role:digest(roles[role]) for role in ROLES}
    ordered_physical={role:{r["physical_line"] for r in data}
                      for role,data in roles.items()}
    example_tuples={role:{canonical((r["left"],r["gold"],r["right"]))
                          for r in data} for role,data in roles.items()}
    for i,role in enumerate(ROLES):
        if len(example_tuples[role])!=COUNTS[role]:
            raise ValueError("L4_SOURCE_DUPLICATE")
        for prev in ROLES[:i]:
            if example_tuples[role]&example_tuples[prev] or \
                    ordered_physical[role]&ordered_physical[prev]:
                raise ValueError("L4_SOURCE_CHRONOLOGICAL_LEAKAGE")
    tr,se,de=(roles[role] for role in ROLES)
    train_vocab={word for x in tr for word in x["gold"]}
    fitted,models=fit(tr,se)
    frozen={arm:models[arm]["checkpoint_sha256"] for arm in ARMS}
    evaluations={}
    for role,episodes in roles.items():
        evaluations[role]={}
        for arm in ARMS:
            evaluations[role][arm]=evaluate(fitted[arm],episodes,train_vocab)
            if hashlib.sha256(fitted[arm].checkpoint()).hexdigest()!=frozen[arm]:
                raise ValueError("L4_EVALUATION_MUTATED_FITTED_MODEL")
    _,python_peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.language.l4.realtext-public-gap-receipt.v1",
        "source_git_blob_sha1":EXPECTED_GIT_SHA1,
        "source_raw_sha256":raw_sha,
        "previous_L1_L3_dev_reuse":0,
        "protected_Q21_FSA_scientific_first_use":False,
        "Q21_and_active_research_unchanged":True,
        "externally_blinded_science":False,
        "model_scientific_go":False,
        "fully_resource_matched_conventional_LM":False,
        "natural_text_gap_not_semantic_language_realization":True,
        "energy_joules":"NOT_MEASURED",
        "measured_hardware_FLOPs":"NOT_MEASURED",
        "actual_parallel_execution":False,
        "source_role_sha256":source_hashes,
        "source_role_counts":COUNTS,
        "train_gap_source_bytes":len(canonical(tr)),
        "select_gap_source_bytes":len(canonical(se)),
        "fit_target_vocabulary_word_count":len(train_vocab),
        "source_generation_cpu_s":generation_cpu,
        "models":models,
        "evaluations":evaluations,
        "total_process_CPU_s":time.process_time()-started,
        "peak_tracemalloc_bytes":python_peak,
        "process_peak_rss_bytes":rss_bytes(),
        "platform":platform.platform(),
    }


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: runner.py /path/external-original.txt")
    print(json.dumps(run(sys.argv[1]),sort_keys=True,
                     allow_nan=False,indent=2))
