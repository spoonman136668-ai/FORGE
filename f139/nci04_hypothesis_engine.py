"""Source-grounded, preregistered compositional hypothesis engine for FORGE F139.

Moves beyond finite hardcoded DEV readouts by composing orthogonal local-cell
mechanisms (evidence estimators x support/balance gates x tie/exploration
policies), attaching a frozen scientific preregistration record BEFORE
execution, enforcing AST safety invariants, and selecting the next candidate
using evidence-conditioned, failure-guided ablation progression.

Design boundaries:
- Preserves distinct architectures (Yggdrasil, Wingless, TTT-Hybrid); never
  collapses them or introduces transformer/token or paid-API dependencies.
- Pure read-only proposal & ranking engine: no GitHub writes, no new
  controller/scheduler, no SQLite mutation, no automatic checkpoint promotion,
  and no scientific first-use authority (`scientific_first_use: False`).
- Retains all consumed and failed/negative trials; never deletes or replays.
"""
from __future__ import annotations

import ast
import base64
import json
from typing import Iterable

from f139.nci04_fresh_curriculum import PROPOSAL_SCHEMA
from f139.nci04_fresh_successor_producer import ANCHOR, git_blob
from f139.nci04_fresh_worker_protocol import SOURCE, TARGET, TARGET_TREE
from f139.nci04_fresh_yggdrasil_boundary import (
    ACCEPTED_NATIVE_BLOB, ACCEPTED_NATIVE_PATH,
)
from f139.nci04_native_contract import canonical, digest, parse_intent
from f139.nci04_owner_issue import KIND as ISSUE_KIND, SCHEMA as ISSUE_SCHEMA

SCHEMA = "forge.f139.source-grounded-hypothesis-engine.v1"
PREREG_SCHEMA = "forge.f139.scientific-preregistration.v1"

# Strictly separate research architectures (never collapsed into one model).
TARGET_ARCHITECTURES = frozenset({"Yggdrasil", "Wingless", "TTT-Hybrid"})

# Orthogonal local-cell scientific axes for Yggdrasil PublicCausalCells.
ESTIMATORS = (
    ("jeffreys", "Beta(1/2,1/2) minimax posterior mean over local arm counts"),
    ("asymmetric_loss", "Risk-averse utility penalizing local failures 2:1"),
    ("se_margin", "Exact integer 1-SE empirical variance gap abstention"),
    ("lcb_15", "Rational 1.5-SE lower-confidence-bound separation"),
)
SUPPORT_GATES = (
    ("min1", "Require >=1 observation on each arm"),
    ("min4", "Require >=4 observations on each arm"),
    ("min8", "Require >=8 observations on each arm"),
    ("balanced2x", "Require >=2 per arm and <=2x arm-count imbalance"),
)
TIE_POLICIES = (
    ("abstain", "Abstain strictly on tie or unresolved uncertainty"),
    ("least_observed", "Break unresolved ties toward the less-observed local arm"),
)

FROZEN_SEEDS = (13, 29, 53, 71, 97)
FORBIDDEN_IMPORTS = frozenset({
    "os", "sys", "subprocess", "socket", "urllib", "http", "requests",
    "random", "shutil", "pathlib", "ctypes", "importlib",
})


class HypothesisEngineDenied(ValueError):
    """Fail-closed denial for invalid source, preregistration, or AST drift."""


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise HypothesisEngineDenied("F139_HYPOTHESIS_" + reason)


def _support_guard_code(support_gate: str) -> str:
    if support_gate == "min1":
        return "        if not total0 or not total1:\n            return None\n"
    if support_gate == "min4":
        return "        if total0 < 4 or total1 < 4:\n            return None\n"
    if support_gate == "min8":
        return "        if total0 < 8 or total1 < 8:\n            return None\n"
    if support_gate == "balanced2x":
        return (
            "        if total0 < 2 or total1 < 2:\n"
            "            return None\n"
            "        if total0 > 2 * total1 or total1 > 2 * total0:\n"
            "            return None\n"
        )
    raise HypothesisEngineDenied("F139_HYPOTHESIS_UNKNOWN_SUPPORT_GATE")


def _tie_return_code(tie_policy: str) -> str:
    if tie_policy == "abstain":
        return "            return None\n"
    if tie_policy == "least_observed":
        return (
            "            if total0 == total1:\n"
            "                return None\n"
            "            return 0 if total0 < total1 else 1\n"
        )
    raise HypothesisEngineDenied("F139_HYPOTHESIS_UNKNOWN_TIE_POLICY")


def _estimator_code(estimator: str, tie_block: str) -> str:
    if estimator == "jeffreys":
        return (
            "        lhs = (2 * success0 + 1) * (2 * total1 + 2)\n"
            "        rhs = (2 * success1 + 1) * (2 * total0 + 2)\n"
            "        if lhs == rhs:\n"
            + tie_block +
            "        return 0 if lhs > rhs else 1\n"
        )
    if estimator == "asymmetric_loss":
        return (
            "        lhs = (success0 - 2 * fail0) * total1\n"
            "        rhs = (success1 - 2 * fail1) * total0\n"
            "        if lhs == rhs:\n"
            + tie_block +
            "        return 0 if lhs > rhs else 1\n"
        )
    if estimator == "se_margin":
        return (
            "        lhs = success0 * total1\n"
            "        rhs = success1 * total0\n"
            "        gap = lhs - rhs\n"
            "        var = (success0 * fail0 * total1 ** 3\n"
            "               + success1 * fail1 * total0 ** 3)\n"
            "        if gap == 0 or gap * gap * total0 * total1 <= var:\n"
            + tie_block +
            "        return 0 if gap > 0 else 1\n"
        )
    if estimator == "lcb_15":
        return (
            "        lhs = success0 * total1\n"
            "        rhs = success1 * total0\n"
            "        gap = lhs - rhs\n"
            "        var = (success0 * fail0 * total1 ** 3\n"
            "               + success1 * fail1 * total0 ** 3)\n"
            "        if gap == 0 or 4 * gap * gap * total0 * total1 <= 9 * var:\n"
            + tie_block +
            "        return 0 if gap > 0 else 1\n"
        )
    raise HypothesisEngineDenied("F139_HYPOTHESIS_UNKNOWN_ESTIMATOR")


def compose_yggdrasil_method(estimator: str, support_gate: str,
                             tie_policy: str) -> tuple[str, str]:
    """Synthesize one stateless, pure-integer local-cell method for Yggdrasil."""
    est_names = {k for k, _ in ESTIMATORS}
    sup_names = {k for k, _ in SUPPORT_GATES}
    tie_names = {k for k, _ in TIE_POLICIES}
    need(estimator in est_names and support_gate in sup_names
         and tie_policy in tie_names, "AXIS_VALUE_INVALID")
    method_name = f"choose_hyp_{estimator}_{support_gate}_{tie_policy}"
    tie_block = _tie_return_code(tie_policy)
    body = (
        f"    def {method_name}(self, address: int, *, retained: bool = False) -> int | None:\n"
        "        \"\"\"Preregistered local-cell hypothesis; leaves default choose and checkpoint intact.\"\"\"\n"
        "        cell = self._address(address, retained)\n"
        "        (fail0, success0), (fail1, success1) = self._counts[cell]\n"
        "        total0, total1 = fail0 + success0, fail1 + success1\n"
        + _support_guard_code(support_gate)
        + _estimator_code(estimator, tie_block)
        + "\n"
    )
    return method_name, body


def verify_candidate_ast_safety(source_text: str, method_name: str) -> None:
    """Fail-closed AST audit: pure local readout, zero mutations/imports."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError as exc:
        raise HypothesisEngineDenied("F139_HYPOTHESIS_AST_SYNTAX_INVALID") from exc
    classes = [n for n in tree.body
               if isinstance(n, ast.ClassDef) and n.name == "PublicCausalCells"]
    need(len(classes) == 1, "TARGET_CLASS_DRIFT")
    target_cls = classes[0]
    methods = [n for n in target_cls.body
               if isinstance(n, ast.FunctionDef) and n.name == method_name]
    need(len(methods) == 1, "GENERATED_METHOD_MISSING_OR_DUPLICATE")
    fn = methods[0]
    for node in ast.walk(fn):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise HypothesisEngineDenied("F139_HYPOTHESIS_FORBIDDEN_IMPORT_IN_METHOD")
        if isinstance(node, ast.Global) or isinstance(node, ast.Nonlocal):
            raise HypothesisEngineDenied("F139_HYPOTHESIS_NONLOCAL_STATE_FORBIDDEN")
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for tgt in targets:
                if isinstance(tgt, (ast.Attribute, ast.Subscript)):
                    raise HypothesisEngineDenied("F139_HYPOTHESIS_CELL_MUTATION_FORBIDDEN")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_IMPORTS:
            raise HypothesisEngineDenied("F139_HYPOTHESIS_FORBIDDEN_SYMBOL_REFERENCE")


def build_preregistration(*, architecture: str, estimator: str,
                          support_gate: str, tie_policy: str,
                          after_sha256: str, baseline_blob: str) -> dict:
    """Create a frozen, pre-observation scientific preregistration record."""
    need(architecture in TARGET_ARCHITECTURES, "UNKNOWN_TARGET_ARCHITECTURE")
    est_desc = dict(ESTIMATORS).get(estimator)
    sup_desc = dict(SUPPORT_GATES).get(support_gate)
    tie_desc = dict(TIE_POLICIES).get(tie_policy)
    need(est_desc is not None and sup_desc is not None and tie_desc is not None,
         "PREREG_MECHANISM_INVALID")
    hypothesis_id = f"ygg-{estimator}-{support_gate}-{tie_policy}-v1"
    record = {
        "schema": PREREG_SCHEMA,
        "hypothesis_id": hypothesis_id,
        "target_architecture": architecture,
        "axes": {
            "estimator": estimator,
            "support_gate": support_gate,
            "tie_policy": tie_policy,
        },
        "falsifiable_claim": (
            f"Composing {est_desc} with {sup_desc} and {tie_desc} improves "
            "out-of-sample decision accuracy or calibration on local causal "
            "cells relative to matched baselines without breaking 164-byte "
            "cold-restart retention."
        ),
        "matched_controls": ["PublicCausalCells.choose", "PublicCausalCells.choose_wilson"],
        "negative_controls": [
            "action_null_false_choice_rate",
            "sparse_deterministic_over_abstention",
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
        "baseline_blob": baseline_blob,
        "after_sha256": after_sha256,
    }
    record["preregistration_sha256"] = digest(canonical(record))
    return record


def generate_yggdrasil_hypothesis_pool(
    *, before: bytes, seed_intent: bytes,
    consumed_after: set[str], last_verified_after: str,
) -> list[dict]:
    """Generate the full 32-candidate compositional hypothesis pool for Yggdrasil.

    Skips already-consumed after_sha256 identities without deleting history.
    Every returned item includes:
      - `plan`: canonical issue payload compatible with single-owner publication
      - `selection`: selector metadata matching `PROPOSAL_SCHEMA`
      - `preregistration`: frozen scientific preregistration record
    """
    need(type(before) is bytes and 0 < len(before) <= 32768
         and git_blob(before) == ACCEPTED_NATIVE_BLOB
         and type(seed_intent) is bytes and 0 < len(seed_intent) <= 60000
         and type(consumed_after) is set and len(consumed_after) <= 10000
         and all(type(h) is str and len(h) == 64
                 and all(c in "0123456789abcdef" for c in h)
                 for h in consumed_after)
         and type(last_verified_after) is str
         and last_verified_after in consumed_after,
         "SOURCE_HISTORY_OR_TERMINAL_UNVERIFIED")
    try:
        original = before.decode("utf-8", "strict")
        seed = json.loads(seed_intent)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise HypothesisEngineDenied("F139_HYPOTHESIS_SEED_PARSE_FAILED") from exc
    initial = parse_intent(seed_intent, protected_main=SOURCE,
                           target_commit=TARGET, target_tree_sha=TARGET_TREE)
    need(type(seed) is dict and initial.path == ACCEPTED_NATIVE_PATH
         and initial.before_sha256 == digest(before)
         and seed.get("scientific_first_use") is False
         and seed.get("paid_api_calls") == 0
         and seed.get("accepted_ref_mutations") == 0
         and seed.get("optimizer_policy_mutations") == 0
         and seed.get("protected_holdouts_accessed") == 0
         and original.count(ANCHOR) == 1,
         "FROZEN_BASELINE_OR_INTENT_DRIFT")

    pool: list[dict] = []
    seen_hashes: set[str] = set()
    for estimator, _ in ESTIMATORS:
        for support_gate, _ in SUPPORT_GATES:
            for tie_policy, _ in TIE_POLICIES:
                method_name, method_src = compose_yggdrasil_method(
                    estimator, support_gate, tie_policy)
                need("def " + method_name + "(" not in original,
                     "METHOD_ALREADY_IN_BASELINE")
                after_text = original.replace(ANCHOR, method_src + ANCHOR)
                verify_candidate_ast_safety(after_text, method_name)
                raw_after = after_text.encode("utf-8")
                after_sha = digest(raw_after)
                need(0 < len(raw_after) <= 32768 and raw_after != before
                     and after_sha not in seen_hashes,
                     "CANDIDATE_DUPLICATE_OR_OVERSIZE")
                seen_hashes.add(after_sha)
                if after_sha in consumed_after:
                    continue
                intent = dict(seed)
                intent["after_base64"] = base64.b64encode(raw_after).decode("ascii")
                intent["after_sha256"] = after_sha
                raw_intent = canonical(intent)
                candidate = parse_intent(raw_intent, protected_main=SOURCE,
                                         target_commit=TARGET, target_tree_sha=TARGET_TREE)
                need(candidate.after_sha256 == after_sha
                     and candidate.path == ACCEPTED_NATIVE_PATH,
                     "GENERATED_CONTRACT_NOT_QUALIFIED")
                prereg = build_preregistration(
                    architecture="Yggdrasil",
                    estimator=estimator,
                    support_gate=support_gate,
                    tie_policy=tie_policy,
                    after_sha256=after_sha,
                    baseline_blob=ACCEPTED_NATIVE_BLOB,
                )
                issue = {
                    "schema": ISSUE_SCHEMA, "source_sha": SOURCE,
                    "lane": "Yggdrasil", "kind": ISSUE_KIND,
                    "intent_base64": base64.b64encode(raw_intent).decode("ascii"),
                    "scientific_first_use": False, "paid_model_calls": 0,
                }
                body = canonical(issue).decode("ascii")
                need(len(body) <= 60000, "ISSUE_BODY_TOO_LARGE")
                label = prereg["hypothesis_id"]
                mechanism = digest(canonical({
                    "schema": SCHEMA,
                    "preregistration_sha256": prereg["preregistration_sha256"],
                    "baseline_blob": ACCEPTED_NATIVE_BLOB,
                    "after_sha256": after_sha,
                }))
                checksum = digest(canonical({
                    "schema": SCHEMA, "mechanism_sha256": mechanism,
                    "intent_sha256": candidate.intent_sha256,
                    "qualification_key": candidate.qualification_key,
                    "target_tree_sha": TARGET_TREE,
                }))
                plan = {
                    "schema": SCHEMA, "recipe": label,
                    "title": "F139 auto-feed fresh Yggdrasil HYP: " + label,
                    "body": body, "body_sha256": digest(canonical(issue)),
                    "after_sha256": after_sha, "intent_sha256": candidate.intent_sha256,
                    "mechanism_sha256": mechanism,
                    "preregistration_sha256": prereg["preregistration_sha256"],
                    "scientific_first_use": False, "paid_model_calls": 0,
                }
                selection = {
                    "schema": PROPOSAL_SCHEMA, "source_sha": SOURCE,
                    "target_tree_sha": TARGET_TREE,
                    "after_sha256": after_sha, "intent_sha256": candidate.intent_sha256,
                    "mechanism_sha256": mechanism, "qualification_sha256": checksum,
                    "prerequisites": [last_verified_after], "exclusions": [],
                    "cost_units": 2,
                    "development_only": True, "scientific_first_use": False,
                    "paid_model_calls": 0, "accepted_ref_mutations": 0,
                }
                pool.append({
                    "plan": plan,
                    "selection": selection,
                    "preregistration": prereg,
                })
    return pool


def select_next_hypothesis(
    pool: list[dict], *,
    verified_axes: Iterable[dict] = (),
    failed_axes: Iterable[dict] = (),
) -> dict | None:
    """Evidence-conditioned, failure-guided ablation selector.

    - Penalizes axes associated with prior NEGATIVE/failed terminals so FORGE
      pivots to orthogonal mechanisms while retaining every failed record.
    - Rewards single-axis ablations (Hamming distance 1) of VERIFIED terminals
      so FORGE systematically isolates which mechanism component matters.
    - Deterministic tie-breaking by `after_sha256` (zero randomness).
    """
    need(type(pool) is list, "POOL_INVALID")
    if not pool:
        return None
    v_list = list(verified_axes)
    f_list = list(failed_axes)
    failed_est = {a.get("estimator") for a in f_list}
    failed_sup = {a.get("support_gate") for a in f_list}
    failed_tie = {a.get("tie_policy") for a in f_list}

    def score(item: dict) -> tuple[int, int, str]:
        axes = item["preregistration"]["axes"]
        # Failure penalty: count how many axes overlap with prior failed trials
        fail_overlap = (
            int(axes["estimator"] in failed_est)
            + int(axes["support_gate"] in failed_sup)
            + int(axes["tie_policy"] in failed_tie)
        )
        # Ablation priority: prefer exact 1-axis perturbation of a verified trial
        if v_list:
            min_dist = min(
                sum(axes[k] != v.get(k) for k in ("estimator", "support_gate", "tie_policy"))
                for v in v_list
            )
            ablation_rank = 0 if min_dist == 1 else (1 if min_dist == 2 else 2)
        else:
            ablation_rank = 0
        return (fail_overlap, ablation_rank, item["plan"]["after_sha256"])

    return min(pool, key=score)
