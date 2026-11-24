"""FORGE Autonomous Self-Improvement Loop (`FORGE-on-FORGE`, Gate 15).

Orchestrates a bounded, fail-closed self-improvement cycle over FORGE's own
allowlisted research-intelligence modules:
  1. Accepts a finite list of candidate module patches targeting an allowlisted
     FORGE module (`SELF_IMPROVABLE_MODULES`).
  2. Evaluates each candidate in an isolated temporary FORGE checkout via
     `evaluate_self_improvement_proposal`:
     - Enforces protected-kernel, AST, import, and safety-flag boundaries.
     - Runs FORGE's regression test suite in an isolated subprocess.
     - Runs a deterministic downstream meta-benchmark comparing baseline FORGE
       vs. candidate FORGE.
  3. Retains all evaluated candidates (qualified and rejected/failed), ranks
     strictly qualifying candidates by downstream `meta_delta`, and emits a
     SHA-256-sealed `SelfImprovementBundle`.
  4. Never mutates the live controller, never self-merges, and always requires
     CI/human review before landing on protected `main`.
"""
from __future__ import annotations

from pathlib import Path

from f139.nci04_native_contract import canonical, digest
from f139.nci04_self_improvement import (
    SelfImprovementDenied,
    evaluate_self_improvement_proposal,
)

BUNDLE_SCHEMA = "forge.f139.self-improvement-bundle.v1"
MAX_SELF_CANDIDATES = 12


class SelfImprovementLoopDenied(ValueError):
    """Fail-closed denial for invalid self-improvement cycle inputs."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise SelfImprovementLoopDenied("F139_SELF_LOOP_" + reason)


def run_self_improvement_cycle(
    *,
    cycle_id: str,
    forge_root: Path,
    target_rel_path: str,
    candidates: list[dict],
    regression_test_modules: tuple[str, ...],
    meta_benchmark_script: str,
    timeout_seconds: int = 90,
) -> dict:
    """Run a bounded self-improvement meta-qualification cycle on one FORGE module.

    Each item in `candidates` must be `{"candidate_id": str, "source": str}`.
    Safety/syntax/kernel violations are recorded cleanly as denied entries rather
    than crashing the audit trail, while never executing denied code.
    """
    need(type(cycle_id) is str and 3 <= len(cycle_id) <= 128, "CYCLE_ID_INVALID")
    need(type(candidates) is list and 1 <= len(candidates) <= MAX_SELF_CANDIDATES,
         "CANDIDATES_INVALID")
    need(type(meta_benchmark_script) is str and len(meta_benchmark_script.strip()) > 0,
         "META_BENCHMARK_REQUIRED")

    seen_ids: set[str] = set()
    evaluations: list[dict] = []

    for item in candidates:
        need(type(item) is dict and type(item.get("candidate_id")) is str
             and type(item.get("source")) is str, "CANDIDATE_ENTRY_INVALID")
        cid = item["candidate_id"]
        need(cid not in seen_ids, "DUPLICATE_CANDIDATE_ID")
        seen_ids.add(cid)

        try:
            prop = evaluate_self_improvement_proposal(
                forge_root=forge_root,
                target_rel_path=target_rel_path,
                candidate_source=item["source"],
                regression_test_modules=regression_test_modules,
                meta_benchmark_script=meta_benchmark_script,
                timeout_seconds=timeout_seconds,
            )
            evaluations.append({
                "candidate_id": cid,
                "status": "QUALIFIED" if prop["self_improvement_qualified"] else "REJECTED",
                "denied_reason": None,
                "proposal": prop,
            })
        except SelfImprovementDenied as exc:
            evaluations.append({
                "candidate_id": cid,
                "status": "DENIED",
                "denied_reason": str(exc),
                "proposal": None,
            })

    qualified = [e for e in evaluations if e["status"] == "QUALIFIED"]
    qualified.sort(
        key=lambda e: (
            -float(e["proposal"]["meta_delta"]),
            e["candidate_id"],
        )
    )

    best = qualified[0] if qualified else None
    bundle = {
        "schema": BUNDLE_SCHEMA,
        "cycle_id": cycle_id,
        "target_rel_path": target_rel_path,
        "total_candidates": len(evaluations),
        "qualified_count": len(qualified),
        "rejected_count": sum(1 for e in evaluations if e["status"] == "REJECTED"),
        "denied_count": sum(1 for e in evaluations if e["status"] == "DENIED"),
        "retained_all_attempts": True,
        "selected_candidate_id": best["candidate_id"] if best else None,
        "selected_meta_delta": best["proposal"]["meta_delta"] if best else None,
        "selected_after_sha256": best["proposal"]["after_sha256"] if best else None,
        "evaluations": evaluations,
        "live_controller_mutated": False,
        "requires_human_or_ci_merge": True,
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    bundle["bundle_sha256"] = digest(canonical(bundle))
    return bundle
