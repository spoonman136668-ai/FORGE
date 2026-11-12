"""O5 public-source fit/selection/DEV evidence, no protected science or dispatch.

All arms see exactly the same fresh public histories; the HMM and counts are
the immutable O4 implementations copied verbatim for an auditable comparator.
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
sys.path.insert(0, str(HERE))
from public_source import FAMILIES, ROLES, ROLE_COUNTS, canonical, role_episodes, digest
from online_local import OnlineLocalBelief, SEEDS
from o4_frozen_controls import PublicActionHMM, PublicHistoryCounts, score

PROTO = HERE / "O5_FROZEN_PROTOCOL.json"
ARMS = (
    "ONLINE_LOCAL_BELIEF", "ONLINE_FROZEN_TRANSITION_ABLATION",
    "BATCH_HMM_EM_O4", "PUBLIC_CURRENT_COUNTS", "PUBLIC_LAG_COUNTS",
)


def frozen():
    v = json.loads(PROTO.read_text(encoding="utf-8"))
    assert v["schema"] == "forge.optimizer.o5.online-local-belief.public-development.v1"
    assert v["status"] == "FROZEN_BEFORE_PUBLIC_ROLE_BIRTH_OR_LEARNER_EXECUTION"
    assert v["new_seed_namespace"] == "o5-public-v1"
    assert tuple(v["roles"]) == ROLES and v["episodes_per_family"] == ROLE_COUNTS
    assert tuple(v["arms"]) == ARMS and v["episode_steps"] == 24
    assert v["arms"]["ONLINE_LOCAL_BELIEF"]["local_em_rate"] == 0.045
    assert v["arms"]["ONLINE_LOCAL_BELIEF"]["local_flip_rate"] == 0.045
    assert v["arms"]["BATCH_HMM_EM_O4"]["source_blob"] == (
        "3ab09e0b9b27a3404ddaf81fdc3c26cc87ba7a4c")
    return v


def rss_bytes():
    if os.name == "posix":
        import resource
        observed = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(observed if sys.platform == "darwin" else 1024*observed)
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class PM(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        pm = PM()
        pm.cb = ctypes.sizeof(pm)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(pm), pm.cb)
        return int(pm.PeakWorkingSetSize) if ok else None
    return None


def fit_arm(arm, train, select):
    if arm == "ONLINE_LOCAL_BELIEF" or arm == "ONLINE_FROZEN_TRANSITION_ABLATION":
        active = arm == "ONLINE_LOCAL_BELIEF"
        options = []
        for seed in SEEDS:
            model = OnlineLocalBelief(seed, train_transition=active)
            model.fit(train)
            options.append((score(model, select), seed, model))
        options.sort(key=lambda row: (row[0], row[1]))
        return options[0][2], {
            "selection_nll": options[0][0],
            "selected_initialization": options[0][1],
            "all_selection_nll": {str(s): nll for nll, s, _ in options},
        }
    if arm == "BATCH_HMM_EM_O4":
        options = []
        for seed in SEEDS:
            model = PublicActionHMM(seed)
            model.fit(train, iterations=12)
            options.append((score(model, select), seed, model))
        options.sort(key=lambda row: (row[0], row[1]))
        return options[0][2], {
            "selection_nll": options[0][0],
            "selected_initialization": options[0][1],
            "all_selection_nll": {str(s): nll for nll, s, _ in options},
        }
    if arm in ("PUBLIC_CURRENT_COUNTS", "PUBLIC_LAG_COUNTS"):
        model = PublicHistoryCounts(lagged=arm == "PUBLIC_LAG_COUNTS")
        model.fit(train)
        valid_score = score(model, select)
        return model, {"selection_nll": valid_score,
                       "selected_initialization": None,
                       "all_selection_nll": {"nonrandom": valid_score}}
    raise ValueError("O5_UNKNOWN_ARM")


def screen():
    frozen()
    total_start = time.process_time()
    tracemalloc.start()
    output = {}
    for family in FAMILIES:
        t = time.process_time()
        train, select, dev = [role_episodes(role, family) for role in ROLES]
        source_cpu = time.process_time()-t
        role_digests = {role: digest(rows) for role, rows in
                        zip(ROLES, (train, select, dev))}
        assert len(set(role_digests.values())) == len(ROLES)
        fitted = {}
        for arm in ARMS:
            t = time.process_time()
            model, selection = fit_arm(arm, train, select)
            fit_cpu = time.process_time()-t
            cp = model.checkpoint()
            t = time.process_time()
            eval_nll = score(model, dev)
            eval_cpu = time.process_time()-t
            assert cp == model.checkpoint(), "O5_DEV_TUNING_OR_MUTATION"
            assert math.isfinite(eval_nll)
            fitted[arm] = {
                "public_dev_nll": eval_nll,
                "fit_and_selection_cpu_s": fit_cpu,
                "public_dev_inference_cpu_s": eval_cpu,
                "model_bytes": len(cp),
                "model_sha256": hashlib.sha256(cp).hexdigest(),
                "trained_updates": model.updates,
                **selection,
            }
        benchmark = min(fitted[n]["public_dev_nll"] for n in
                        ("BATCH_HMM_EM_O4", "PUBLIC_CURRENT_COUNTS",
                         "PUBLIC_LAG_COUNTS"))
        online = fitted["ONLINE_LOCAL_BELIEF"]
        batch = fitted["BATCH_HMM_EM_O4"]
        output[family] = {
            "roles": {role: len(data) for role, data in
                      zip(ROLES, (train, select, dev))},
            "role_source_sha256": role_digests,
            "generation_cpu_s": source_cpu,
            "online_vs_best_control_nll_gain": benchmark - online["public_dev_nll"],
            "online_vs_fixed_transition_nll_gain": (
                fitted["ONLINE_FROZEN_TRANSITION_ABLATION"]["public_dev_nll"]
                - online["public_dev_nll"]),
            "online_cpu_less_than_batch": (
                online["fit_and_selection_cpu_s"] <
                batch["fit_and_selection_cpu_s"]),
            "models": fitted,
        }
    _, peak_allocation = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema": "forge.optimizer.o5.public-development-result.v1",
        "not_scientific_evidence": True,
        "fsa_grant": "NONE",
        "protected_first_use": 0,
        "separate_O4_roles_consumed": 0,
        "DEV_model_updates": 0,
        "accepted_learner": "NONE",
        "native_architecture_integration": "NONE",
        "cpu_whole_process_s": time.process_time()-total_start,
        "peak_tracemalloc_bytes": peak_allocation,
        "peak_process_rss_bytes": rss_bytes(),
        "operating_system": platform.platform(),
        "python_version": sys.version.split()[0],
        "families": output,
    }


if __name__ == "__main__":
    print(json.dumps(screen(), indent=2, sort_keys=True, allow_nan=False))
