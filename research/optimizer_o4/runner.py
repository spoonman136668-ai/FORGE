"""O4 frozen prospective PUBLIC development, no scientific admission or promotion."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import tracemalloc

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from models import ARMS, fit_select, score, sha_checkpoint
from public_source import FAMILIES, ROLES, COUNTS, canonical, dataset, digest

FROZEN_PROTOCOL = HERE / "O4_FROZEN_PROTOCOL.json"


def verify_protocol():
    p = json.loads(FROZEN_PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"] == "forge.optimizer.o4.training-vs-latent-prereg.v1"
    assert p["role_namespace"] == "o4-public-20261023-v1"
    assert tuple(p["role_names"]) == ROLES
    assert p["role_episodes_per_family"] == COUNTS
    assert p["transitions_per_episode"] == 24
    assert tuple(p["arms"]) == ARMS
    return p


def peak_rss_bytes():
    if os.name == "posix":
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform == "darwin" else 1024*value)
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
        obj = PM()
        obj.cb = ctypes.sizeof(obj)
        process = ctypes.windll.kernel32.GetCurrentProcess()
        result = ctypes.windll.psapi.GetProcessMemoryInfo(
            process, ctypes.byref(obj), obj.cb)
        return int(obj.PeakWorkingSetSize) if result else None
    return None


def run():
    verify_protocol()
    start_total = time.process_time()
    tracemalloc.start()
    families = {}
    for family in FAMILIES:
        before = time.process_time()
        train, select, dev = [dataset(role, family) for role in ROLES]
        role_digests = {role: digest(rows) for role, rows in
                        zip(ROLES, (train, select, dev))}
        assert len(set(role_digests.values())) == len(ROLES)
        generator_cpu = time.process_time() - before
        arms = {}
        # All models see the identical public training/validation/dev episodes.
        for arm in ARMS:
            begin_fit = time.process_time()
            model, selection = fit_select(arm, train, select)
            fit_and_selection_cpu = time.process_time() - begin_fit
            checkpoint = model.checkpoint()
            start_dev = time.process_time()
            result = score(model, dev)
            inference_cpu = time.process_time() - start_dev
            assert checkpoint == model.checkpoint(), "O4_DEV_MODEL_MUTATED"
            arms[arm] = {
                "public_dev_nll": result,
                "select_nll": selection["selection_nll"],
                "selected_seed": selection["selected_seed"],
                "select_restarts": selection["selection_restarts"],
                "fit_selection_cpu_seconds": fit_and_selection_cpu,
                "public_dev_inference_cpu_seconds": inference_cpu,
                "checkpoint_sha256": sha_checkpoint(model),
                "serialized_state_bytes": len(checkpoint),
                "trained_updates": model.updates,
            }
        best_control = min(arms[x]["public_dev_nll"]
                           for x in ("PUBLIC_LAG_COUNTS", "PUBLIC_CURRENT_COUNTS"))
        families[family] = {
            "public_role_sha256": role_digests,
            "public_role_counts": {r: len(e) for r, e in
                                   zip(ROLES, (train, select, dev))},
            "generator_cpu_seconds": generator_cpu,
            "strongest_counts_dev_nll": best_control,
            "adam_vs_same_epoch_sgd_nll_gain": (
                arms["RNN_TANH_SGD_16E"]["public_dev_nll"] -
                arms["RNN_TANH_ADAM_16E"]["public_dev_nll"]),
            "hmm_vs_best_counts_nll_gain": (
                best_control - arms["HMM_2STATE_ACTION_EM"]["public_dev_nll"]),
            "arms": arms,
        }
    _, allocated_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema": "forge.optimizer.o4.public-dev.v1",
        "source_only": True,
        "development_only": True,
        "fsa_grant": None,
        "protected_scientific_roles": 0,
        "scientific_success": "NOT_EVALUATED",
        "no_hidden_training_labels": True,
        "source_mutation": False,
        "whole_process_cpu_seconds": time.process_time()-start_total,
        "peak_traced_allocations_bytes": allocated_peak,
        "whole_process_peak_rss_bytes": peak_rss_bytes(),
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "families": families,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True, allow_nan=False))
