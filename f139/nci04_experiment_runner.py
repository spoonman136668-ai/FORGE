"""FORGE Core Multi-Method Experiment & Training Runner (Gate 14).

Generalizes FORGE's bounded native execution model from unit-test-only checks
into a one-stop, fail-closed experimental research & training engine supporting
diverse theoretical method families (non-transformer AGI kernels, local-learning
cells, predictive causal state, TTT-Hybrid, experimental LLM, and GLM/world-model
tracks) under a single unified receipt contract.

Hard boundaries:
- Fixed allowlisted runner profiles only (untrusted specs cannot inject shell
  strings or arbitrary binaries).
- Isolated temporary execution workspace with strict wall-clock and output-byte
  caps; never mutates the live controller or original checkout.
- Cryptographically sealed `ExperimentReceipt` with optional checkpoint SHA-256
  digests (`auto_promote_checkpoint: False`, `scientific_first_use: False`,
  `paid_model_calls: 0`).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from f139.nci04_native_contract import canonical, digest

SPEC_SCHEMA = "forge.f139.experiment-spec.v1"
RECEIPT_SCHEMA = "forge.f139.experiment-receipt.v1"

MAX_CAPTURE_BYTES = 262_144
MAX_TIMEOUT_SECONDS = 600

SUPPORTED_METHOD_FAMILIES = frozenset({
    "Yggdrasil",
    "Wingless",
    "TTT-Hybrid",
    "LLM-Experimental",
    "GLM-WorldModel",
    "AGI-Kernel",
})

# Fixed allowlisted runner templates; experiment specs pick a profile key and
# relative module/entrypoint path inside the pinned workspace (no shell=True).
RUNNER_PROFILES: dict[str, tuple[str, ...]] = {
    "python_script": (sys.executable, "-B"),
    "python_unittest": (sys.executable, "-B", "-m", "unittest"),
    "go_test": ("go", "test", "-count=1"),
}

FORBIDDEN_ENV_PREFIXES = ("OPENAI_", "ANTHROPIC_", "GEMINI_API_", "GH_TOKEN", "GITHUB_TOKEN")


class ExperimentRunnerDenied(ValueError):
    """Fail-closed denial for invalid experiment specs or policy violations."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise ExperimentRunnerDenied("F139_EXP_RUNNER_" + reason)


def _safe_rel_path(rel: str) -> Path:
    need(type(rel) is str and 0 < len(rel) <= 256, "REL_PATH_INVALID")
    p = Path(rel)
    need(not p.is_absolute() and ".." not in p.parts, "PATH_TRAVERSAL_DENIED")
    return p


def build_experiment_spec(
    *,
    experiment_id: str,
    method_family: str,
    profile: str,
    entrypoint: str,
    seeds: tuple[int, ...] = (13, 29, 53),
    timeout_seconds: int = 60,
    primary_metric: str = "score",
    higher_is_better: bool = True,
    paid_model_calls: int = 0,
    auto_promote_checkpoint: bool = False,
    scientific_first_use: bool = False,
) -> dict:
    """Create and SHA-256-seal a validated ExperimentSpec."""
    need(type(experiment_id) is str and 3 <= len(experiment_id) <= 128, "EXPERIMENT_ID_INVALID")
    need(method_family in SUPPORTED_METHOD_FAMILIES, "UNSUPPORTED_METHOD_FAMILY")
    need(profile in RUNNER_PROFILES, "UNSUPPORTED_RUNNER_PROFILE")
    _safe_rel_path(entrypoint)
    need(type(seeds) is tuple and 1 <= len(seeds) <= 32
         and all(type(s) is int and s > 0 for s in seeds), "SEEDS_INVALID")
    need(type(timeout_seconds) is int and 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS,
         "TIMEOUT_OUT_OF_BOUNDS")
    need(type(primary_metric) is str and 1 <= len(primary_metric) <= 64, "METRIC_NAME_INVALID")
    need(type(higher_is_better) is bool, "DIRECTION_INVALID")
    need(paid_model_calls == 0, "PAID_MODEL_CALLS_FORBIDDEN")
    need(auto_promote_checkpoint is False, "AUTO_PROMOTE_CHECKPOINT_FORBIDDEN")
    need(scientific_first_use is False, "SCIENTIFIC_FIRST_USE_UNQUALIFIED")

    spec = {
        "schema": SPEC_SCHEMA,
        "experiment_id": experiment_id,
        "method_family": method_family,
        "profile": profile,
        "entrypoint": entrypoint,
        "seeds": list(seeds),
        "timeout_seconds": timeout_seconds,
        "primary_metric": primary_metric,
        "higher_is_better": higher_is_better,
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    spec["spec_sha256"] = digest(canonical(spec))
    return spec


def _verify_spec(spec: dict) -> None:
    need(type(spec) is dict and spec.get("schema") == SPEC_SCHEMA, "SPEC_SCHEMA_INVALID")
    need(spec.get("paid_model_calls") == 0
         and spec.get("auto_promote_checkpoint") is False
         and spec.get("scientific_first_use") is False,
         "SPEC_SAFETY_CONTRACT_VIOLATED")
    no_sig = {k: v for k, v in spec.items() if k != "spec_sha256"}
    need(digest(canonical(no_sig)) == spec.get("spec_sha256"), "SPEC_DIGEST_MISMATCH")
    need(spec.get("method_family") in SUPPORTED_METHOD_FAMILIES, "UNSUPPORTED_METHOD_FAMILY")
    need(spec.get("profile") in RUNNER_PROFILES, "UNSUPPORTED_RUNNER_PROFILE")
    _safe_rel_path(spec["entrypoint"])


def _sanitized_env(seeds: list[int], metrics_out: Path, checkpoint_dir: Path) -> dict[str, str]:
    env = {
        k: v for k, v in os.environ.items()
        if not any(k.upper().startswith(p) for p in FORBIDDEN_ENV_PREFIXES)
    }
    env["FORGE_EXPERIMENT_SEEDS"] = ",".join(str(s) for s in seeds)
    env["FORGE_METRICS_OUT"] = str(metrics_out)
    env["FORGE_CHECKPOINT_DIR"] = str(checkpoint_dir)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_bounded_experiment(
    spec: dict,
    *,
    source_root: Path,
    baseline_receipt: dict | None = None,
) -> dict:
    """Execute a sealed ExperimentSpec in an isolated temp workspace and emit a receipt."""
    _verify_spec(spec)
    source_root = Path(source_root).resolve(strict=True)
    need(source_root.is_dir(), "SOURCE_ROOT_MISSING")
    entry_rel = _safe_rel_path(spec["entrypoint"])
    need((source_root / entry_rel).exists(), "ENTRYPOINT_MISSING")

    with tempfile.TemporaryDirectory(prefix="forge_exp_") as td:
        td_path = Path(td)
        work_dir = td_path / "workspace"
        shutil.copytree(
            source_root,
            work_dir,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        metrics_out = td_path / "metrics.json"
        ckpt_dir = td_path / "checkpoints"
        ckpt_dir.mkdir()

        argv = [*RUNNER_PROFILES[spec["profile"]], str(entry_rel)]
        env = _sanitized_env(spec["seeds"], metrics_out, ckpt_dir)

        t0 = time.monotonic()
        timed_out = False
        try:
            proc = subprocess.run(
                argv,
                cwd=str(work_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                timeout=spec["timeout_seconds"],
                check=False,
            )
            returncode = proc.returncode
            stdout_raw = proc.stdout[:MAX_CAPTURE_BYTES]
            stderr_raw = proc.stderr[:MAX_CAPTURE_BYTES]
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = -1
            stdout_raw = (exc.stdout or b"")[:MAX_CAPTURE_BYTES]
            stderr_raw = (exc.stderr or b"")[:MAX_CAPTURE_BYTES]
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        metrics: dict = {}
        metrics_valid = False
        if metrics_out.is_file():
            raw_m = metrics_out.read_bytes()
            if 0 < len(raw_m) <= 65536:
                parsed = json.loads(raw_m.decode("utf-8"))
                if type(parsed) is dict:
                    metrics = parsed
                    metrics_valid = spec["primary_metric"] in metrics

        checkpoints: dict[str, str] = {}
        for f in sorted(ckpt_dir.rglob("*")):
            if f.is_file():
                rel_name = f.relative_to(ckpt_dir).as_posix()
                checkpoints[rel_name] = digest(f.read_bytes())

    status = "VERIFIED" if (not timed_out and returncode == 0 and metrics_valid) else "NEGATIVE"
    delta_vs_baseline = None
    beats_baseline = None
    if (
        status == "VERIFIED"
        and type(baseline_receipt) is dict
        and baseline_receipt.get("status") == "VERIFIED"
        and spec["primary_metric"] in baseline_receipt.get("metrics", {})
    ):
        cand_val = float(metrics[spec["primary_metric"]])
        base_val = float(baseline_receipt["metrics"][spec["primary_metric"]])
        delta_vs_baseline = round(cand_val - base_val, 6)
        beats_baseline = (
            (delta_vs_baseline > 0.0) if spec["higher_is_better"] else (delta_vs_baseline < 0.0)
        )

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "experiment_id": spec["experiment_id"],
        "spec_sha256": spec["spec_sha256"],
        "method_family": spec["method_family"],
        "status": status,
        "returncode": returncode,
        "timed_out": timed_out,
        "elapsed_ms": elapsed_ms,
        "stdout_sha256": digest(stdout_raw),
        "stderr_sha256": digest(stderr_raw),
        "metrics": metrics,
        "primary_metric": spec["primary_metric"],
        "delta_vs_baseline": delta_vs_baseline,
        "beats_baseline": beats_baseline,
        "checkpoint_digests": checkpoints,
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    receipt["receipt_sha256"] = digest(canonical(receipt))
    return receipt
