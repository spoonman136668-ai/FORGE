"""Generation-2 Yggdrasil compositional hypothesis engine driven by Gate 10 feedback.

Refines the winning Generation-1 axes (`se_margin` z=1.0 and `lcb_15` z=1.5)
using exact-integer rational confidence levels (`z_5_4` = 1.25 SE, `z_7_4` = 1.75 SE,
`agresti_coull_1` = Laplace-shrunk 1-SE) composed with refined sampling-balance
gates (`min2`, `balanced_3_2`, `balanced_3_1`) and tie policies (`abstain`,
`least_observed`) — 18 new AST-verified, 164-byte-checkpoint-invariant hypotheses.

Pure read-only proposal engine: zero GitHub writes, zero paid calls,
`scientific_first_use: False`, `auto_promote_checkpoint: False`.
"""
from __future__ import annotations

import base64
import json

from f139.nci04_fresh_curriculum import PROPOSAL_SCHEMA
from f139.nci04_fresh_successor_producer import ANCHOR, git_blob
from f139.nci04_fresh_worker_protocol import SOURCE, TARGET, TARGET_TREE
from f139.nci04_fresh_yggdrasil_boundary import (
    ACCEPTED_NATIVE_BLOB, ACCEPTED_NATIVE_PATH,
)
from f139.nci04_hypothesis_engine import (
    FROZEN_SEEDS, PREREG_SCHEMA, HypothesisEngineDenied,
    verify_candidate_ast_safety,
)
from f139.nci04_native_contract import canonical, digest, parse_intent
from f139.nci04_owner_issue import KIND as ISSUE_KIND, SCHEMA as ISSUE_SCHEMA

SCHEMA = "forge.f139.source-grounded-hypothesis-engine.gen2.v1"

GEN2_ESTIMATORS = (
    ("z_5_4", "Exact integer 1.25-SE empirical variance gap gate (16*gap^2*t0*t1 > 25*var)"),
    ("z_7_4", "Exact integer 1.75-SE empirical variance gap gate (16*gap^2*t0*t1 > 49*var)"),
    ("agresti_coull_1", "Unit-pseudocount shrunk 1-SE empirical variance gap gate"),
)
GEN2_SUPPORT_GATES = (
    ("min2", "Require >=2 observations on each arm"),
    ("balanced_3_2", "Require >=2 per arm and <=3:2 arm-count imbalance"),
    ("balanced_3_1", "Require >=2 per arm and <=3:1 arm-count imbalance"),
)
GEN2_TIE_POLICIES = (
    ("abstain", "Abstain strictly on tie or unresolved uncertainty"),
    ("least_observed", "Break unresolved ties toward the less-observed local arm"),
)


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise HypothesisEngineDenied("F139_HYPOTHESIS_GEN2_" + reason)


def _support_code(gate: str) -> str:
    if gate == "min2":
        return "        if total0 < 2 or total1 < 2:\n            return None\n"
    if gate == "balanced_3_2":
        return (
            "        if total0 < 2 or total1 < 2:\n"
            "            return None\n"
            "        if 2 * total0 > 3 * total1 or 2 * total1 > 3 * total0:\n"
            "            return None\n"
        )
    if gate == "balanced_3_1":
        return (
            "        if total0 < 2 or total1 < 2:\n"
            "            return None\n"
            "        if total0 > 3 * total1 or total1 > 3 * total0:\n"
            "            return None\n"
        )
    raise HypothesisEngineDenied("F139_HYPOTHESIS_GEN2_UNKNOWN_GATE")


def _tie_code(tie: str) -> str:
    if tie == "abstain":
        return "            return None\n"
    if tie == "least_observed":
        return (
            "            if total0 == total1:\n"
            "                return None\n"
            "            return 0 if total0 < total1 else 1\n"
        )
    raise HypothesisEngineDenied("F139_HYPOTHESIS_GEN2_UNKNOWN_TIE")


def _estimator_code(est: str, tie_block: str) -> str:
    if est == "z_5_4":
        return (
            "        lhs = success0 * total1\n"
            "        rhs = success1 * total0\n"
            "        gap = lhs - rhs\n"
            "        var = (success0 * fail0 * total1 ** 3\n"
            "               + success1 * fail1 * total0 ** 3)\n"
            "        if gap == 0 or 16 * gap * gap * total0 * total1 <= 25 * var:\n"
            + tie_block +
            "        return 0 if gap > 0 else 1\n"
        )
    if est == "z_7_4":
        return (
            "        lhs = success0 * total1\n"
            "        rhs = success1 * total0\n"
            "        gap = lhs - rhs\n"
            "        var = (success0 * fail0 * total1 ** 3\n"
            "               + success1 * fail1 * total0 ** 3)\n"
            "        if gap == 0 or 16 * gap * gap * total0 * total1 <= 49 * var:\n"
            + tie_block +
            "        return 0 if gap > 0 else 1\n"
        )
    if est == "agresti_coull_1":
        return (
            "        s0, f0, t0 = success0 + 1, fail0 + 1, total0 + 2\n"
            "        s1, f1, t1 = success1 + 1, fail1 + 1, total1 + 2\n"
            "        gap = s0 * t1 - s1 * t0\n"
            "        var = s0 * f0 * t1 ** 3 + s1 * f1 * t0 ** 3\n"
            "        if gap == 0 or gap * gap * t0 * t1 <= var:\n"
            + tie_block +
            "        return 0 if gap > 0 else 1\n"
        )
    raise HypothesisEngineDenied("F139_HYPOTHESIS_GEN2_UNKNOWN_ESTIMATOR")


def compose_gen2_method(estimator: str, support_gate: str,
                        tie_policy: str) -> tuple[str, str]:
    _need(estimator in {k for k, _ in GEN2_ESTIMATORS}
          and support_gate in {k for k, _ in GEN2_SUPPORT_GATES}
          and tie_policy in {k for k, _ in GEN2_TIE_POLICIES},
          "AXIS_INVALID")
    name = f"choose_hyp_{estimator}_{support_gate}_{tie_policy}"
    body = (
        f"    def {name}(self, address: int, *, retained: bool = False) -> int | None:\n"
        "        \"\"\"Gen-2 preregistered local-cell hypothesis; leaves choose & 164B checkpoint intact.\"\"\"\n"
        "        cell = self._address(address, retained)\n"
        "        (fail0, success0), (fail1, success1) = self._counts[cell]\n"
        "        total0, total1 = fail0 + success0, fail1 + success1\n"
        + _support_code(support_gate)
        + _estimator_code(estimator, _tie_code(tie_policy))
        + "\n"
    )
    return name, body


def generate_gen2_yggdrasil_pool(
    *, before: bytes, seed_intent: bytes,
    consumed_after: set[str], last_verified_after: str,
) -> list[dict]:
    """Generate 18 Gen-2 preregistered Yggdrasil hypotheses skipping spent hashes."""
    _need(type(before) is bytes and 0 < len(before) <= 32768
          and git_blob(before) == ACCEPTED_NATIVE_BLOB
          and type(seed_intent) is bytes and 0 < len(seed_intent) <= 60000
          and type(consumed_after) is set and last_verified_after in consumed_after,
          "INPUT_INVALID")
    original = before.decode("utf-8", "strict")
    seed = json.loads(seed_intent)
    initial = parse_intent(seed_intent, protected_main=SOURCE,
                           target_commit=TARGET, target_tree_sha=TARGET_TREE)
    _need(initial.path == ACCEPTED_NATIVE_PATH and initial.before_sha256 == digest(before)
          and original.count(ANCHOR) == 1, "BASELINE_DRIFT")

    est_map = dict(GEN2_ESTIMATORS)
    sup_map = dict(GEN2_SUPPORT_GATES)
    tie_map = dict(GEN2_TIE_POLICIES)

    pool: list[dict] = []
    seen: set[str] = set()
    for est, _ in GEN2_ESTIMATORS:
        for sup, _ in GEN2_SUPPORT_GATES:
            for tie, _ in GEN2_TIE_POLICIES:
                mname, msrc = compose_gen2_method(est, sup, tie)
                after_text = original.replace(ANCHOR, msrc + ANCHOR)
                verify_candidate_ast_safety(after_text, mname)
                raw_after = after_text.encode("utf-8")
                after_sha = digest(raw_after)
                _need(0 < len(raw_after) <= 32768 and after_sha not in seen, "DUPLICATE")
                seen.add(after_sha)
                if after_sha in consumed_after:
                    continue
                intent = dict(seed)
                intent["after_base64"] = base64.b64encode(raw_after).decode("ascii")
                intent["after_sha256"] = after_sha
                raw_intent = canonical(intent)
                cand = parse_intent(raw_intent, protected_main=SOURCE,
                                    target_commit=TARGET, target_tree_sha=TARGET_TREE)
                hid = f"ygg-gen2-{est}-{sup}-{tie}-v1"
                prereg = {
                    "schema": PREREG_SCHEMA,
                    "hypothesis_id": hid,
                    "target_architecture": "Yggdrasil",
                    "axes": {"estimator": est, "support_gate": sup, "tie_policy": tie},
                    "falsifiable_claim": (
                        f"Gen-2 refinement composing {est_map[est]} with {sup_map[sup]} "
                        f"and {tie_map[tie]} improves risk-adjusted decision utility over "
                        "matched controls without breaking 164-byte cold-restart invariance."
                    ),
                    "matched_controls": [
                        "PublicCausalCells.choose", "PublicCausalCells.choose_wilson",
                    ],
                    "negative_controls": [
                        "action_null_false_choice_rate",
                        "imbalanced_arm_spurious_preference",
                        "checkpoint_164_byte_invariance",
                    ],
                    "frozen_protocol": {
                        "seeds": list(FROZEN_SEEDS),
                        "compute_budget_units": 2,
                        "stopping_condition": "single_bounded_qualification_pass_or_fail_closed",
                        "acceptance_criterion": "strictly_beats_strongest_matched_control_and_reproduces",
                        "scientific_first_use": False,
                        "paid_model_calls": 0,
                        "auto_promote_checkpoint": False,
                    },
                    "baseline_blob": ACCEPTED_NATIVE_BLOB,
                    "after_sha256": after_sha,
                }
                prereg["preregistration_sha256"] = digest(canonical(prereg))
                issue = {
                    "schema": ISSUE_SCHEMA, "source_sha": SOURCE,
                    "lane": "Yggdrasil", "kind": ISSUE_KIND,
                    "intent_base64": base64.b64encode(raw_intent).decode("ascii"),
                    "scientific_first_use": False, "paid_model_calls": 0,
                }
                body = canonical(issue).decode("ascii")
                mechanism = digest(canonical({
                    "schema": SCHEMA,
                    "preregistration_sha256": prereg["preregistration_sha256"],
                    "baseline_blob": ACCEPTED_NATIVE_BLOB,
                    "after_sha256": after_sha,
                }))
                checksum = digest(canonical({
                    "schema": SCHEMA, "mechanism_sha256": mechanism,
                    "intent_sha256": cand.intent_sha256,
                    "qualification_key": cand.qualification_key,
                    "target_tree_sha": TARGET_TREE,
                }))
                pool.append({
                    "plan": {
                        "schema": SCHEMA, "recipe": hid,
                        "title": "F139 auto-feed fresh Yggdrasil GEN2: " + hid,
                        "body": body, "body_sha256": digest(canonical(issue)),
                        "after_sha256": after_sha, "intent_sha256": cand.intent_sha256,
                        "mechanism_sha256": mechanism,
                        "preregistration_sha256": prereg["preregistration_sha256"],
                        "scientific_first_use": False, "paid_model_calls": 0,
                    },
                    "selection": {
                        "schema": PROPOSAL_SCHEMA, "source_sha": SOURCE,
                        "target_tree_sha": TARGET_TREE,
                        "after_sha256": after_sha, "intent_sha256": cand.intent_sha256,
                        "mechanism_sha256": mechanism, "qualification_sha256": checksum,
                        "prerequisites": [last_verified_after], "exclusions": [],
                        "cost_units": 2,
                        "development_only": True, "scientific_first_use": False,
                        "paid_model_calls": 0, "accepted_ref_mutations": 0,
                    },
                    "preregistration": prereg,
                })
    return pool
