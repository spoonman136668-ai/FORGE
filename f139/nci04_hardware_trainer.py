"""Hardware-Aware Bounded Local Training Runner for FORGE F139 (Gate 19).

Auto-detects local compute capabilities (CPU cores, optional PyTorch + CUDA GPU
availability) without requiring PyTorch in stdlib-only CI, enforces strict
resource budgets (`HardwareBudget`), and executes real bounded training jobs
through `f139/nci04_experiment_runner.py` with optional persistence into
`f139/nci04_evidence_store.py`.

Hard boundaries:
- Zero paid model/API calls (`paid_model_calls: 0`).
- Never auto-promotes trained checkpoints (`auto_promote_checkpoint: False`).
- `scientific_first_use: False`.
"""
from __future__ import annotations

import os
from pathlib import Path
import platform

from f139.nci04_evidence_store import append_evidence_record
from f139.nci04_experiment_runner import build_experiment_spec, run_bounded_experiment
from f139.nci04_native_contract import canonical, digest

PROFILE_SCHEMA = "forge.f139.hardware-profile.v1"
BUDGET_SCHEMA = "forge.f139.hardware-training-budget.v1"


class HardwareTrainerDenied(ValueError):
    """Fail-closed denial for invalid hardware training budget or inputs."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise HardwareTrainerDenied("F139_HW_TRAINER_" + reason)


def detect_hardware_profile() -> dict:
    """Detect local CPU and optional PyTorch/CUDA capabilities safely (read-only)."""
    cpu_count = os.cpu_count() or 1
    torch_available = False
    torch_version = None
    cuda_available = False
    gpu_name = None
    gpu_vram_mb = 0

    try:
        import torch  # type: ignore
        torch_available = True
        torch_version = getattr(torch, "__version__", "unknown")
        if torch.cuda.is_available():
            cuda_available = True
            props = torch.cuda.get_device_properties(0)
            gpu_name = str(props.name)
            gpu_vram_mb = int(props.total_memory // (1024 * 1024))
    except Exception:
        pass

    profile = {
        "schema": PROFILE_SCHEMA,
        "platform": platform.system(),
        "machine": platform.machine(),
        "cpu_count": cpu_count,
        "torch_available": torch_available,
        "torch_version": torch_version,
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
        "gpu_vram_mb": gpu_vram_mb,
        "recommended_backend": (
            "torch_cuda" if cuda_available else ("torch_cpu" if torch_available else "stdlib_cpu")
        ),
    }
    profile["profile_sha256"] = digest(canonical(profile))
    return profile


def build_hardware_budget(
    *,
    max_wall_seconds: int = 120,
    max_threads: int = 4,
    max_ram_mb: int = 4096,
    max_vram_mb: int = 0,
    allow_gpu: bool = False,
) -> dict:
    """Create a validated, bounded resource budget for local FORGE training runs."""
    need(type(max_wall_seconds) is int and 5 <= max_wall_seconds <= 600, "WALL_SECONDS_INVALID")
    need(type(max_threads) is int and 1 <= max_threads <= 64, "THREADS_INVALID")
    need(type(max_ram_mb) is int and 256 <= max_ram_mb <= 65536, "RAM_MB_INVALID")
    need(type(max_vram_mb) is int and 0 <= max_vram_mb <= 49152, "VRAM_MB_INVALID")
    need(type(allow_gpu) is bool, "ALLOW_GPU_INVALID")
    hw = detect_hardware_profile()
    effective_threads = min(max_threads, hw["cpu_count"])
    use_gpu = bool(allow_gpu and hw["cuda_available"] and max_vram_mb > 0)

    budget = {
        "schema": BUDGET_SCHEMA,
        "max_wall_seconds": max_wall_seconds,
        "effective_threads": effective_threads,
        "max_ram_mb": max_ram_mb,
        "max_vram_mb": max_vram_mb if use_gpu else 0,
        "device": "cuda:0" if use_gpu else "cpu",
        "backend": hw["recommended_backend"] if (use_gpu or hw["torch_available"]) else "stdlib_cpu",
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    budget["budget_sha256"] = digest(canonical(budget))
    return budget


def run_hardware_bounded_training(
    *,
    experiment_id: str,
    method_family: str,
    entrypoint: str,
    source_root: Path,
    budget: dict,
    primary_metric: str = "val_loss",
    higher_is_better: bool = False,
    seeds: tuple[int, ...] = (13, 29, 53),
    baseline_receipt: dict | None = None,
    evidence_store_path: Path | None = None,
) -> dict:
    """Run a hardware-bounded training experiment and optionally log to evidence store."""
    need(type(budget) is dict and budget.get("schema") == BUDGET_SCHEMA, "BUDGET_INVALID")
    need(budget.get("paid_model_calls") == 0
         and budget.get("auto_promote_checkpoint") is False
         and budget.get("scientific_first_use") is False,
         "BUDGET_SAFETY_VIOLATION")

    spec = build_experiment_spec(
        experiment_id=experiment_id,
        method_family=method_family,
        profile="python_script",
        entrypoint=entrypoint,
        seeds=seeds,
        timeout_seconds=budget["max_wall_seconds"],
        primary_metric=primary_metric,
        higher_is_better=higher_is_better,
        paid_model_calls=0,
        auto_promote_checkpoint=False,
        scientific_first_use=False,
    )
    # Propagate deterministic thread & device hints via env for child process
    old_omp = os.environ.get("OMP_NUM_THREADS")
    old_dev = os.environ.get("FORGE_TRAINING_DEVICE")
    os.environ["OMP_NUM_THREADS"] = str(budget["effective_threads"])
    os.environ["FORGE_TRAINING_DEVICE"] = budget["device"]
    try:
        receipt = run_bounded_experiment(
            spec, source_root=source_root, baseline_receipt=baseline_receipt
        )
    finally:
        if old_omp is None:
            os.environ.pop("OMP_NUM_THREADS", None)
        else:
            os.environ["OMP_NUM_THREADS"] = old_omp
        if old_dev is None:
            os.environ.pop("FORGE_TRAINING_DEVICE", None)
        else:
            os.environ["FORGE_TRAINING_DEVICE"] = old_dev

    receipt["hardware_device"] = budget["device"]
    receipt["hardware_backend"] = budget["backend"]

    if evidence_store_path is not None:
        val = receipt["metrics"].get(primary_metric) if receipt["status"] == "VERIFIED" else None
        append_evidence_record(
            evidence_store_path,
            kind="experiment_receipt",
            method_family=method_family,
            status=receipt["status"],
            payload=receipt,
            primary_metric=primary_metric,
            primary_value=float(val) if type(val) in (int, float) else None,
            higher_is_better=higher_is_better,
        )
    return receipt
