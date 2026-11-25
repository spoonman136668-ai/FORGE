"""Read-Only FORGE Self-Improvement Proposal CLI (Gate 17).

Runs a bounded, fail-closed `run_self_improvement_cycle` against an allowlisted
FORGE research module in isolated temporary sandboxes and prints a sealed JSON
`SelfImprovementBundle` ready for PR/CI review.

Never mutates the live repo, never touches protected kernel/controller files,
never auto-merges, and never promotes checkpoints.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from f139.nci04_self_improvement_loop import run_self_improvement_cycle


def run_default_wingless_calibration_proposal(forge_root: Path) -> dict:
    """Run a bounded read-only self-improvement proposal sweep on Wingless Gen-2."""
    target = "f139/nci04_wingless_gen2.py"
    orig = (forge_root / target).read_text(encoding="utf-8")
    candidates = [
        {
            "candidate_id": f"wingless-z-{z.replace('.', '_')}",
            "source": orig.replace(
                "diff < 1.00 * math.sqrt(tot)",
                f"diff < {z} * math.sqrt(tot)",
                1,
            ),
        }
        for z in ("0.85", "0.90", "1.05")
    ]
    meta_script = (
        "from f139.nci04_wingless_gen2 import qualify_wingless_gen2_heldout\n"
        "res = qualify_wingless_gen2_heldout()\n"
        "print(res['evaluations'][0]['total_delta_vs_baseline'])\n"
    )
    return run_self_improvement_cycle(
        cycle_id="forge-cli-wingless-calibration-v1",
        forge_root=forge_root,
        target_rel_path=target,
        candidates=candidates,
        regression_test_modules=("f139/test_nci04_gate13_multi_lane_qualification.py",),
        meta_benchmark_script=meta_script,
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    forge_root = Path(args[0]).resolve() if args else Path(__file__).resolve().parent.parent
    bundle = run_default_wingless_calibration_proposal(forge_root)
    summary = {
        "schema": bundle["schema"],
        "cycle_id": bundle["cycle_id"],
        "target_rel_path": bundle["target_rel_path"],
        "qualified_count": bundle["qualified_count"],
        "rejected_count": bundle["rejected_count"],
        "denied_count": bundle["denied_count"],
        "selected_candidate_id": bundle["selected_candidate_id"],
        "selected_meta_delta": bundle["selected_meta_delta"],
        "selected_after_sha256": bundle["selected_after_sha256"],
        "live_controller_mutated": bundle["live_controller_mutated"],
        "requires_human_or_ci_merge": bundle["requires_human_or_ci_merge"],
        "bundle_sha256": bundle["bundle_sha256"],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
