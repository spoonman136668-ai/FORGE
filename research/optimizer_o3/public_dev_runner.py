"""Prospective O3 PUBLIC development only: fit, select, evaluate without DEV tuning.

Never emits scientific GO, first-use or research authority, and does not write
a model artifact, queue action, or update any frozen predecessor protocol.
"""
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
from learners import fit_models, model_receipt, score
from public_source import FAMILIES, ROLES, role_digest, role_episodes

PROTOCOL = HERE / "O3_FROZEN_PUBLIC_PROTOCOL.json"


def protocol_guard():
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert p["schema"] == "forge.optimizer.o3.public-predictive-state-prereg.v1"
    assert p["protocol_state"] == "FROZEN_BEFORE_IMPLEMENTATION_AND_PUBLIC_DEV"
    assert p["roles"] == list(ROLES)
    assert p["episodes_per_family"] == {"PUBLIC_TRAIN": 48,
                                       "PUBLIC_SELECT": 16,
                                       "PUBLIC_DEV": 20}
    assert p["transitions_per_episode"] == 24
    assert p["training"]["epochs"] == 5
    assert p["training"]["initializations"] == [17, 31]
    assert p["training"]["learning_rate"] == 0.035
    assert p["training"]["gradient_clipping"] == 2.0
    return p


def process_peak_rss_bytes():
    if os.name == "posix":
        try:
            import resource
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return int(peak) if sys.platform == "darwin" else int(peak * 1024)
        except (ImportError, OSError):
            return None
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            class PMC(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]
            val = PMC()
            val.cb = ctypes.sizeof(val)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(val), val.cb)
            return int(val.PeakWorkingSetSize) if ok else None
        except (AttributeError, OSError, ValueError):
            return None
    return None


def measure_full_screen():
    protocol_guard()
    tracemalloc.start()
    beginning = time.process_time()
    report = {}
    for family in FAMILIES:
        start_gen = time.process_time()
        datasets = {role: role_episodes(role, family) for role in ROLES}
        digests = {role: role_digest(role, family, datasets[role])
                   for role in ROLES}
        assert len(set(digests.values())) == len(ROLES), "ROLE_DIGEST_COLLISION"
        generator_cpu = time.process_time() - start_gen
        start_fit = time.process_time()
        fitted = fit_models(datasets["PUBLIC_TRAIN"], datasets["PUBLIC_SELECT"])
        fit_select_cpu = time.process_time() - start_fit
        start_dev = time.process_time()
        evaluations = {}
        for name, (model, metadata) in sorted(fitted.items()):
            frozen = model.checkpoint()
            val = score(model, datasets["PUBLIC_DEV"])
            assert frozen == model.checkpoint(), "PUBLIC_DEV_MUTATED_MODEL"
            evaluations[name] = {
                "public_dev_next_bit_nll": val,
                **model_receipt(model, metadata),
            }
        inference_cpu = time.process_time() - start_dev
        best_conventional = min(evaluations[n]["public_dev_next_bit_nll"]
                                for n in ("TWO_STATE_TANH_RTRL",
                                          "FOUR_LAG_BAYES_COUNTS",
                                          "EXACT_CONTEXT_EPISODIC",
                                          "CURRENT_ONLY_COUNTS"))
        candidate = evaluations["ONE_BELIEF_SIGMOID_RTRL"]["public_dev_next_bit_nll"]
        report[family] = {
            "role_source_digests": digests,
            "episode_counts": {r: len(datasets[r]) for r in ROLES},
            "public_generator_cpu_seconds": generator_cpu,
            "full_fit_and_selection_cpu_seconds": fit_select_cpu,
            "public_dev_inference_cpu_seconds": inference_cpu,
            "best_trained_conventional_public_dev_nll": best_conventional,
            "candidate_vs_best_conventional_nll_gain": best_conventional-candidate,
            "models": evaluations,
        }
    _, peak_alloc = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema": "forge.optimizer.o3.public-trained-dev-receipt.v1",
        "status": "DEVELOPMENT_ONLY_NOT_SCIENTIFIC_ADMISSION",
        "fully_fit_from_public_experience": True,
        "candidate_policy": "ONE_BELIEF_SIGMOID_RTRL",
        "control_capacity_disclosed": True,
        "protected_first_use": False,
        "fsa_admission": "NONE",
        "scientific_go": "NOT_EVALUATED",
        "source_role_birth": "ONLY_PUBLIC_DEV_DEMONSTRATION",
        "full_process_cpu_seconds": time.process_time() - beginning,
        "tracemalloc_peak_bytes": peak_alloc,
        "process_peak_rss_bytes": process_peak_rss_bytes(),
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "families": report,
    }


if __name__ == "__main__":
    print(json.dumps(measure_full_screen(), indent=2, sort_keys=True,
                     allow_nan=False))
