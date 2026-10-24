"""O6 actual fitted public train/select/DEV, frozen no-DEV-adaptation.

Fresh O6 source only. No hidden labels, O5/O4 historical cohorts, external
authorities or protected first use. All candidates share identical public
observations. Results can be negative and do not authorize integration.
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
from public_source import FAMILIES, ROLES, ROLE_COUNTS, role_episodes, source_digest
from innovation_gated import InnovationGatedBelief
from o5_frozen_online import OnlineLocalBelief
from o4_frozen_controls import PublicActionHMM, PublicHistoryCounts, score

PROTOCOL = HERE / "O6_FROZEN_PROTOCOL.json"
ARMS = (
    "INNOVATION_GATED_ONLINE", "GATED_FIXED_TRANSITION_ABLATION",
    "O5_UNGATED_LOCAL", "O4_BATCH_HMM",
    "CURRENT_ONLY_FITTED_COUNTS", "LAGGED_FITTED_COUNTS",
)
SEEDS = (17, 31)


def validate_protocol():
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"] == "forge.optimizer.o6.innovation-gated-local.public-development.v1"
    assert p["design_state"] == "FROZEN_BEFORE_IMPLEMENTATION_AND_ANY_ROLE_GENERATION"
    assert tuple(p["roles"]) == ROLES
    assert p["episodes_per_family"] == ROLE_COUNTS
    assert p["steps_per_episode"] == 24
    assert tuple(p["arms"]) == ARMS
    assert p["arms"]["O5_UNGATED_LOCAL"]["source_blob"] == (
        "26b3077b9b7f0fec30fa2bc4cfa55cd7b142f6f0")
    assert p["arms"]["O4_BATCH_HMM"]["source_blob"] == (
        "3ab09e0b9b27a3404ddaf81fdc3c26cc87ba7a4c")
    return p


def peak_rss_bytes():
    if os.name == "posix":
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(peak if sys.platform == "darwin" else peak*1024)
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
        result = PM()
        result.cb = ctypes.sizeof(result)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(result), result.cb)
        return int(result.PeakWorkingSetSize) if ok else None
    return None


def fitted(arm, training, selection):
    if arm not in ARMS:
        raise ValueError("O6_NOT_FROZEN_ARM")
    if arm == "CURRENT_ONLY_FITTED_COUNTS" or arm == "LAGGED_FITTED_COUNTS":
        model = PublicHistoryCounts(lagged=(arm == "LAGGED_FITTED_COUNTS"))
        model.fit(training)
        loss = score(model, selection)
        return model, {"selected_seed": None,
                       "public_select_nll": loss,
                       "public_select_by_seed": {"nonrandom": loss}}
    options = []
    for seed in SEEDS:
        if arm == "INNOVATION_GATED_ONLINE":
            model = InnovationGatedBelief(seed)
        elif arm == "GATED_FIXED_TRANSITION_ABLATION":
            model = InnovationGatedBelief(seed, train_transition=False)
        elif arm == "O5_UNGATED_LOCAL":
            model = OnlineLocalBelief(seed)
        else:
            model = PublicActionHMM(seed)
        if arm == "O4_BATCH_HMM":
            model.fit(training, iterations=12)
        else:
            model.fit(training)
        options.append((score(model, selection), seed, model))
    options.sort(key=lambda item: (item[0], item[1]))
    return options[0][2], {
        "selected_seed": options[0][1],
        "public_select_nll": options[0][0],
        "public_select_by_seed": {str(seed): val for val, seed, _ in options},
    }


def main():
    validate_protocol()
    start = time.process_time()
    tracemalloc.start()
    results = {}
    for family in FAMILIES:
        t = time.process_time()
        datasets = {role: role_episodes(role, family) for role in ROLES}
        source_cpu = time.process_time()-t
        hashes = {role: source_digest(datasets[role]) for role in ROLES}
        assert len(set(hashes.values())) == len(ROLES)
        arm_results = {}
        for arm in ARMS:
            t = time.process_time()
            model, select = fitted(arm, datasets["O6_PUBLIC_TRAIN"],
                                   datasets["O6_PUBLIC_SELECT"])
            fit_cpu = time.process_time()-t
            frozen_state = model.checkpoint()
            t = time.process_time()
            dev_nll = score(model, datasets["O6_PUBLIC_DEV"])
            dev_cpu = time.process_time()-t
            assert math.isfinite(dev_nll) and dev_nll >= 0
            assert frozen_state == model.checkpoint(), "O6_DEV_MUTATED_CHECKPOINT"
            arm_results[arm] = {
                "public_dev_nll": dev_nll,
                "fit_and_select_cpu_s": fit_cpu,
                "public_dev_inference_cpu_s": dev_cpu,
                "state_bytes": len(frozen_state),
                "state_sha256": hashlib.sha256(frozen_state).hexdigest(),
                "updates_from_public_train": model.updates,
                **select,
            }
        learner = arm_results["INNOVATION_GATED_ONLINE"]
        all_controls = ["O5_UNGATED_LOCAL", "O4_BATCH_HMM",
                        "CURRENT_ONLY_FITTED_COUNTS", "LAGGED_FITTED_COUNTS"]
        best_control = min(arm_results[arm]["public_dev_nll"]
                           for arm in all_controls)
        results[family] = {
            "source_role_sha256": hashes,
            "source_role_counts": {role: len(datasets[role]) for role in ROLES},
            "source_generation_cpu_s": source_cpu,
            "candidate_minus_best_control_gain_nll": (
                best_control-learner["public_dev_nll"]),
            "candidate_vs_o5_fixed_rate_gain_nll": (
                arm_results["O5_UNGATED_LOCAL"]["public_dev_nll"] -
                learner["public_dev_nll"]),
            "candidate_vs_frozen_transition_gain_nll": (
                arm_results["GATED_FIXED_TRANSITION_ABLATION"]["public_dev_nll"] -
                learner["public_dev_nll"]),
            "candidate_lower_fit_select_cpu_than_o4_batch": (
                learner["fit_and_select_cpu_s"] <
                arm_results["O4_BATCH_HMM"]["fit_and_select_cpu_s"]),
            "arms": arm_results,
        }
    _, peak_alloc = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema": "forge.optimizer.o6.development-only-result.v1",
        "result_status": "DEVELOPMENT_ONLY_NOT_PROTECTED_SCIENCE",
        "protected_first_use": 0,
        "fsa_admission": None,
        "old_o5_role_episodes_consumed": 0,
        "scientific_go": "NOT_EVALUATED",
        "native_integration": "NONE",
        "whole_process_cpu_s": time.process_time()-start,
        "peak_tracemalloc_bytes": peak_alloc,
        "peak_process_rss_bytes": peak_rss_bytes(),
        "operating_system": platform.platform(),
        "python_version": sys.version.split()[0],
        "families": results,
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True, allow_nan=False))
