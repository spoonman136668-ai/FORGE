"""Wingless Real Go-Target Adapter for FORGE Experiment Runner (Gate 17).

Bridges FORGE's pinned `Wingless` research lane (`spoonman136668-ai/Wingless`,
commit `9a92fcae40c811c724b4214da03fff34126f6b4f`, tree
`4d4e92af583aa66f71aa62b1cba4969dacf39453`, `ice/relationships.go`) directly
into `f139/nci04_experiment_runner.py`'s `go_test` profile.

Enforces fail-closed lane isolation, exact commit/tree pinning, zero paid calls,
`auto_promote_checkpoint: False`, and `scientific_first_use: False`.
"""
from __future__ import annotations

from f139.nci04_experiment_runner import build_experiment_spec
from f139.nci04_multi_lane_targets import get_lane_contract, validate_lane_isolation
from f139.nci04_native_contract import canonical, digest

SCHEMA = "forge.f139.wingless-go-target-adapter.v1"
ALLOWED_GO_PACKAGES = frozenset({"./ice", "./cognition", "./..."})


class WinglessGoAdapterDenied(ValueError):
    """Fail-closed denial for unpinned or out-of-scope Wingless Go targets."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise WinglessGoAdapterDenied("F139_WINGLESS_GO_" + reason)


def build_wingless_go_experiment_spec(
    *,
    experiment_id: str,
    go_package: str = "./ice",
    candidate_summary: str = "wingless predictive causal state go test",
    timeout_seconds: int = 120,
) -> dict:
    """Build a sealed `ExperimentSpec` pinned to verified Wingless protected main."""
    need(go_package in ALLOWED_GO_PACKAGES, "GO_PACKAGE_NOT_ALLOWLISTED")
    contract = get_lane_contract("Wingless")
    validate_lane_isolation(
        lane="Wingless",
        candidate_text=candidate_summary,
        target_repo=contract["active_target_repo"],
        paid_model_calls=0,
        scientific_first_use=False,
    )
    spec = build_experiment_spec(
        experiment_id=experiment_id,
        method_family="Wingless",
        profile="go_test",
        entrypoint=go_package,
        timeout_seconds=timeout_seconds,
        primary_metric="go_test_pass",
        higher_is_better=True,
        paid_model_calls=0,
        auto_promote_checkpoint=False,
        scientific_first_use=False,
    )
    adapter_record = {
        "schema": SCHEMA,
        "lane": "Wingless",
        "target_repo": contract["active_target_repo"],
        "target_commit": contract["active_target_commit"],
        "target_tree": contract["active_target_tree"],
        "target_path": contract["active_target_path"],
        "go_package": go_package,
        "experiment_spec": spec,
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    adapter_record["adapter_sha256"] = digest(canonical(adapter_record))
    return adapter_record
