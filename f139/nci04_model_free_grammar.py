"""Inert two-recipe source generator for model-free F139 development research.

This is a source-only, finite grammar proof: a caller must independently
authenticate the frozen source, complete original ledger history and qualified
split/controls. It does not call the existing owner, GitHub, model or science.
No ranked improvement claim, PR creation, source transition or dispatch.
"""
from __future__ import annotations

import ast
import hashlib
import re

from f139.nci04_model_free_frontier import (
    FrontierDenied, choose_frontier, digest, verify_proposal,
)

SCHEMA = "forge.f139.model-free-source-grammar.v1"
TARGET_PATH = "yggdrasil/public_causal_cells.py"
ANCHOR = "    def snapshot(self) -> bytes:\n"
RECIPES = (("posterior_public_cost_prior_1", 1),
           ("posterior_public_cost_prior_2", 2))
METADATA = frozenset({
    "dependency_sha256", "qualification_harness_sha256",
    "suite_identity_sha256", "training_config_sha256", "frozen_split_sha256",
})
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class GrammarDenied(ValueError):
    pass


def require(ok: bool, code: str) -> None:
    if not ok:
        raise GrammarDenied("F139_GRAMMAR_" + code)


def method_for(prior: int) -> str:
    """Transparent deterministic hypothesis family, not discovered science."""
    require(type(prior) is int and prior in (1, 2),
            "PRIOR_OUTSIDE_PREDECLARED_GRAMMAR")
    return f'''    def choose_posterior_public_cost_p{prior}(self, address: int,
                                             cost0: int, cost1: int, *,
                                             reward_value: int = 1,
                                             retained: bool = False) -> int | None:
        """Opt-in posterior-smoothed empirical public-cost control.

        Symmetric Beta({prior},{prior}) pseudo-counts; no hidden outcomes,
        intervention oracle, new learned bytes or checkpoint modifications.
        Independent observed outcomes are required for both actions.
        """
        if (type(cost0) is not int or type(cost1) is not int
                or not 0 <= cost0 <= 65535 or not 0 <= cost1 <= 65535):
            raise ValueError("PUBLIC_CAUSAL_COST_INVALID")
        if type(reward_value) is not int or not 1 <= reward_value <= 65535:
            raise ValueError("PUBLIC_CAUSAL_REWARD_VALUE_INVALID")
        cell = self._address(address, retained)
        (fail0, success0), (fail1, success1) = self._counts[cell]
        n0, n1 = fail0 + success0, fail1 + success1
        if not n0 or not n1:
            return None
        d0, d1 = n0 + {2 * prior}, n1 + {2 * prior}
        lhs = ((success0 + {prior}) * reward_value - cost0 * d0) * d1
        rhs = ((success1 + {prior}) * reward_value - cost1 * d1) * d0
        if lhs == rhs:
            return None
        return 0 if lhs > rhs else 1

'''


def generate(*, controller_source_sha: str, target_commit: str,
             target_tree_sha: str, frozen_source_sha256: str, original: bytes,
             metadata: dict, complete_history: list[dict]) -> dict:
    """Generate at most two finite candidate sources, then consume/abstain.

    The exact source/tree, metadata, historical ledger events and independent
    public-cost provenance MUST be verified by the existing original owner,
    not by this function. The output is inert and cannot authorize a PR.
    """
    require(isinstance(controller_source_sha, str)
            and SHA40.fullmatch(controller_source_sha) is not None
            and isinstance(target_commit, str)
            and SHA40.fullmatch(target_commit) is not None
            and isinstance(target_tree_sha, str)
            and SHA40.fullmatch(target_tree_sha) is not None
            and isinstance(frozen_source_sha256, str)
            and SHA64.fullmatch(frozen_source_sha256) is not None,
            "SOURCE_OR_TREE_IDENTITY_INVALID")
    require(type(original) is bytes and 100 <= len(original) <= 32768
            and hashlib.sha256(original).hexdigest() == frozen_source_sha256,
            "SOURCE_BYTES_NOT_PINNED")
    require(type(metadata) is dict and set(metadata) == METADATA
            and all(isinstance(v, str) and SHA64.fullmatch(v) is not None
                    for v in metadata.values()),
            "SEMANTIC_QUALIFICATION_IDENTITIES_INVALID")
    try:
        before = original.decode("utf-8", "strict")
        tree = ast.parse(before, TARGET_PATH)
    except (UnicodeError, SyntaxError) as exc:
        raise GrammarDenied("F139_GRAMMAR_ORIGINAL_NOT_PYTHON") from exc
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)
               and n.name == "PublicCausalCells"]
    require(len(classes) == 1 and before.count(ANCHOR) == 1
            and len({n.name for n in classes[0].body
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))})
                    == sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                           for n in classes[0].body)
            and any(isinstance(n, ast.FunctionDef) and n.name == "choose"
                    for n in classes[0].body)
            and any(isinstance(n, ast.FunctionDef) and n.name == "snapshot"
                    for n in classes[0].body),
            "EXACT_NATIVE_METHOD_ANCHOR_INVALID")
    candidates, source_by_id = [], {}
    for recipe, prior in RECIPES:
        method = f"choose_posterior_public_cost_p{prior}"
        require(not any(isinstance(n, ast.FunctionDef) and n.name == method
                        for n in classes[0].body),
                "PROPOSED_METHOD_ALREADY_PRESENT")
        source = before.replace(ANCHOR, method_for(prior) + ANCHOR, 1)
        try:
            changed = ast.parse(source, TARGET_PATH)
        except SyntaxError as exc:
            raise GrammarDenied("F139_GRAMMAR_GENERATED_SOURCE_INVALID") from exc
        after = source.encode("utf-8")
        require(after != original and len(after) <= 32768
                and sum(isinstance(n, ast.FunctionDef) and n.name == method
                        for n in next(n for n in changed.body
                                      if isinstance(n, ast.ClassDef)
                                      and n.name == "PublicCausalCells").body) == 1,
                "CANDIDATE_BOUNDARY_INVALID")
        row = {
            "lane": "Yggdrasil",
            "controller_source_sha": controller_source_sha,
            "target_commit": target_commit, "target_tree_sha": target_tree_sha,
            "path": TARGET_PATH,
            "before_sha256": frozen_source_sha256,
            "after_sha256": hashlib.sha256(after).hexdigest(),
            "mechanism_sha256": digest({
                "schema": SCHEMA, "recipe": recipe, "prior": prior,
                "method_sha256": hashlib.sha256(method_for(prior).encode()).hexdigest(),
            }),
            "toolchain_identity": "python3.11.11",
            "scientific_first_use": False,
            "paid_model_calls": 0, "protected_holdouts_accessed": 0,
            "accepted_ref_mutations": 0, "optimizer_policy_mutations": 0,
            **metadata,
        }
        identity = verify_proposal(row, controller_source_sha)["candidate_identity"]
        require(identity not in source_by_id, "DUPLICATE_SOURCE_ID")
        source_by_id[identity] = after
        candidates.append(row)
    try:
        selected = choose_frontier(
            source_sha=controller_source_sha,
            catalog=candidates, history=complete_history)
    except FrontierDenied as exc:
        raise GrammarDenied("F139_GRAMMAR_HISTORY_OR_FRONTIER_INVALID") from exc
    return {
        "schema": SCHEMA, "candidate_catalog_sha256": selected["catalog_sha256"],
        "history_sha256": selected["history_sha256"],
        "generated_recipe_count": len(candidates),
        "selected": selected["selected"], "abstentions": selected["abstentions"],
        "source_by_candidate_id": {
            row["candidate_identity"]: source_by_id[row["candidate_identity"]]
            for row in selected["selected"]
        },
        "source_authentication": "EXTERNAL_OWNER_REQUIRED",
        "history_authentication": "COMPLETE_ORIGINAL_LEDGER_REQUIRED",
        "cost_provenance": "INDEPENDENT_PUBLIC_ENVIRONMENT_REQUIRED",
        "qualification": "NOT_RUN_NOT_ACCEPTED",
        "development_only": True, "publication_authorized": False,
        "dispatch_authorized": False, "scientific_first_use": False,
        "new_controller": False, "new_scheduler": False, "new_queue": False,
        "paid_model_calls": 0,
    }
