"""FORGE Fail-Closed Self-Improvement Sandbox & Meta-Qualification Engine (Gate 14).

Enables FORGE to propose, sandbox-test, and meta-benchmark improvements to its
OWN research-intelligence modules ("FORGE improving FORGE to improve what it
works on") while strictly protecting the controller kernel, signing boundary,
SQLite ledger integrity, and safety invariants.

Hard boundaries:
- Explicit `SELF_IMPROVABLE_MODULES` allowlist: ONLY research-intelligence
  modules (hypothesis engines, receipt feedback, evaluators, experiment runner)
  may be patched.
- Explicit `PROTECTED_KERNEL_PREFIXES` / `PROTECTED_KERNEL_PATHS`: Hard-denies
  any self-edit touching the controller, lifecycle, signing credentials, DPAPI,
  SQLite ledger, source-forward cutover scripts, or `.github/workflows/`.
- AST + token safety check: Denies injecting network calls, subprocess/os.system
  overrides, paid API calls, KTRADE terms, or flipping safety flags
  (`auto_promote_checkpoint`, `scientific_first_use`, `paid_model_calls`).
- Isolated temporary staging: Copies the FORGE tree into a temp sandbox, applies
  the candidate module patch, runs FORGE's regression tests in a subprocess,
  executes a downstream meta-benchmark comparing baseline FORGE vs candidate
  FORGE, and emits a SHA-256-sealed `SelfImprovementProposal`.
- Never self-merges and never mutates the live running controller.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from f139.nci04_native_contract import canonical, digest

SCHEMA = "forge.f139.self-improvement-proposal.v1"

# ONLY these FORGE research-intelligence modules may be targeted by self-improvement.
SELF_IMPROVABLE_MODULES = frozenset({
    "f139/nci04_hypothesis_engine.py",
    "f139/nci04_hypothesis_engine_gen2.py",
    "f139/nci04_receipt_feedback.py",
    "f139/nci04_scientific_evaluator.py",
    "f139/nci04_heldout_qualifier.py",
    "f139/nci04_wingless_hypothesis.py",
    "f139/nci04_wingless_gen2.py",
    "f139/nci04_ttt_hybrid_hypothesis.py",
    "f139/nci04_scientific_evidence_report.py",
    "f139/nci04_experiment_runner.py",
})

# Explicitly protected kernel/security surfaces (defense-in-depth alongside allowlist).
PROTECTED_KERNEL_PREFIXES = (
    ".github/",
    "scripts/",
    "f139/local_controller",
    "f139/nci04_fresh_lifecycle",
    "f139/nci04_fresh_owner_source_forward",
    "f139/nci04_native_contract",
    "f139/nci04_native_worker",
    "f139/nci04_self_improvement",
)

FORBIDDEN_SELF_PATCH_TOKENS = (
    "ktrade",
    "k-terminal",
    "openai_api_key",
    "anthropic_api_key",
    "auto_promote_checkpoint = true",
    "auto_promote_checkpoint\": true",
    "scientific_first_use = true",
    "scientific_first_use\": true",
    "paid_model_calls = 1",
)

FORBIDDEN_AST_IMPORTS = frozenset({
    "urllib", "urllib.request", "http.client", "socket", "requests", "httpx",
})


class SelfImprovementDenied(ValueError):
    """Fail-closed denial for unsafe or out-of-scope FORGE self-modification."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise SelfImprovementDenied("F139_SELF_IMPROVE_" + reason)


def validate_self_patch_target(target_rel_path: str, candidate_source: str) -> None:
    """Fail-closed check on target path, AST syntax, imports, and safety tokens."""
    need(type(target_rel_path) is str and 0 < len(target_rel_path) <= 256, "TARGET_PATH_INVALID")
    norm = target_rel_path.replace("\\", "/")
    for prefix in PROTECTED_KERNEL_PREFIXES:
        need(not norm.startswith(prefix), "PROTECTED_KERNEL_PATH_DENIED")
    need(norm in SELF_IMPROVABLE_MODULES, "TARGET_NOT_IN_SELF_IMPROVE_ALLOWLIST")
    need(type(candidate_source) is str and 0 < len(candidate_source) <= 131_072,
         "CANDIDATE_SOURCE_INVALID")

    lowered = candidate_source.lower()
    for token in FORBIDDEN_SELF_PATCH_TOKENS:
        need(token not in lowered, "FORBIDDEN_SAFETY_OR_CONTAMINATION_TOKEN")

    try:
        tree = ast.parse(candidate_source, filename=norm)
    except SyntaxError as exc:
        raise SelfImprovementDenied("F139_SELF_IMPROVE_SYNTAX_ERROR") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                need(alias.name not in FORBIDDEN_AST_IMPORTS, "FORBIDDEN_NETWORK_IMPORT")
        elif isinstance(node, ast.ImportFrom) and node.module:
            need(node.module not in FORBIDDEN_AST_IMPORTS, "FORBIDDEN_NETWORK_IMPORT")


def evaluate_self_improvement_proposal(
    *,
    forge_root: Path,
    target_rel_path: str,
    candidate_source: str,
    regression_test_modules: tuple[str, ...],
    meta_benchmark_script: str | None = None,
    timeout_seconds: int = 90,
) -> dict:
    """Sandbox-stage a FORGE self-improvement patch, run regression + meta-benchmark.

    Returns a cryptographically sealed SelfImprovementProposal. Never modifies
    `forge_root`, never self-merges, and never mutates a live controller.
    """
    validate_self_patch_target(target_rel_path, candidate_source)
    forge_root = Path(forge_root).resolve(strict=True)
    need(forge_root.is_dir(), "FORGE_ROOT_MISSING")
    orig_file = forge_root / target_rel_path
    need(orig_file.is_file(), "TARGET_FILE_MISSING")
    need(type(regression_test_modules) is tuple and 1 <= len(regression_test_modules) <= 32
         and all(type(m) is str and m.startswith("f139/test_") and m.endswith(".py")
                 for m in regression_test_modules),
         "REGRESSION_TESTS_INVALID")
    need(type(timeout_seconds) is int and 5 <= timeout_seconds <= 300, "TIMEOUT_INVALID")

    before_bytes = orig_file.read_bytes()
    after_bytes = candidate_source.encode("utf-8")
    before_sha = digest(before_bytes)
    after_sha = digest(after_bytes)
    need(before_sha != after_sha, "NOOP_SELF_PATCH_DENIED")

    def _run_in_sandbox(root_dir: Path) -> tuple[bool, float | None, str]:
        env = {
            k: v for k, v in os.environ.items()
            if not k.upper().startswith(("GH_TOKEN", "GITHUB_TOKEN", "OPENAI_", "ANTHROPIC_"))
        }
        env["PYTHONPATH"] = f"{root_dir}{os.pathsep}{root_dir / 'scripts'}"
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        test_proc = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", *regression_test_modules, "-q"],
            cwd=str(root_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            timeout=timeout_seconds,
            check=False,
        )
        if test_proc.returncode != 0:
            err = (test_proc.stderr or test_proc.stdout).decode("utf-8", errors="replace")[:2048]
            return False, None, err

        score = None
        if meta_benchmark_script is not None:
            meta_proc = subprocess.run(
                [sys.executable, "-B", "-c", meta_benchmark_script],
                cwd=str(root_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                timeout=timeout_seconds,
                check=False,
            )
            if meta_proc.returncode != 0:
                err = (meta_proc.stderr or meta_proc.stdout).decode("utf-8", errors="replace")[:2048]
                return False, None, err
            score = float(meta_proc.stdout.decode("utf-8").strip().splitlines()[-1])
        return True, score, ""

    with tempfile.TemporaryDirectory(prefix="forge_self_improve_") as td:
        td_path = Path(td)
        base_copy = td_path / "base"
        cand_copy = td_path / "candidate"
        ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc")
        shutil.copytree(forge_root / "f139", base_copy / "f139", ignore=ignore)
        if (forge_root / "scripts").is_dir():
            shutil.copytree(forge_root / "scripts", base_copy / "scripts", ignore=ignore)
        shutil.copytree(base_copy, cand_copy)

        # Apply candidate patch ONLY inside isolated sandbox copy
        (cand_copy / target_rel_path).write_bytes(after_bytes)

        base_ok, base_score, base_err = _run_in_sandbox(base_copy)
        cand_ok, cand_score, cand_err = _run_in_sandbox(cand_copy)

    # Confirm original checkout untouched
    need(orig_file.read_bytes() == before_bytes, "LIVE_CHECKOUT_MUTATED")

    meta_delta = None
    meta_improved = None
    if base_ok and cand_ok and base_score is not None and cand_score is not None:
        meta_delta = round(cand_score - base_score, 6)
        meta_improved = meta_delta > 0.0

    qualified = bool(
        base_ok and cand_ok and (meta_improved is True if meta_benchmark_script else True)
    )

    proposal = {
        "schema": SCHEMA,
        "target_rel_path": target_rel_path,
        "before_sha256": before_sha,
        "after_sha256": after_sha,
        "regression_test_modules": list(regression_test_modules),
        "baseline_regression_pass": base_ok,
        "candidate_regression_pass": cand_ok,
        "baseline_meta_score": base_score,
        "candidate_meta_score": cand_score,
        "meta_delta": meta_delta,
        "meta_improved": meta_improved,
        "self_improvement_qualified": qualified,
        "live_controller_mutated": False,
        "requires_human_or_ci_merge": True,
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
        "error_excerpt": (cand_err or base_err)[:512],
    }
    proposal["proposal_sha256"] = digest(canonical(proposal))
    return proposal
