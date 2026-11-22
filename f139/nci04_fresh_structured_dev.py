"""Bounded grammar for *new* Yggdrasil DEV proposals after the fixed two.

A pure patch author and contract parser, not a research learner or live owner.
The caller must independently authenticate the frozen target commit/tree and
original terminal/consumed history before supplying its inputs. Candidate
receipt hashes in this module are *local checksums*, not approval signatures.
No IO, GitHub POST, imports from candidates, source promotion or first-use.
"""
from __future__ import annotations

import ast
import base64
import json

from f139.nci04_fresh_curriculum import PROPOSAL_SCHEMA
from f139.nci04_fresh_successor_producer import (
    ANCHOR, FreshProposalDenied, git_blob, need,
)
from f139.nci04_fresh_yggdrasil_boundary import (
    ACCEPTED_NATIVE_BLOB, ACCEPTED_NATIVE_PATH,
)
from f139.nci04_fresh_worker_protocol import SOURCE, TARGET, TARGET_TREE
from f139.nci04_native_contract import canonical, digest, parse_intent
from f139.nci04_owner_issue import KIND as ISSUE_KIND, SCHEMA as ISSUE_SCHEMA

SCHEMA = "forge.f139.fresh-structured-dev-grammar.v1"
FAMILIES = ("support", "symmetric-prior")
PARAMETERS = (2, 4, 8, 16)


def method_for(family: str, parameter: int) -> tuple[str, str]:
    """Generate one stateless public-counts method from constrained integers."""
    need(family in FAMILIES and type(parameter) is int
         and parameter in PARAMETERS, "GRAMMAR_PARAMETER_INVALID")
    if family == "support":
        name = "choose_support_floor_" + str(parameter)
        compare = (
            f"        if total0 < {parameter} or total1 < {parameter}:\n"
            "            return None\n"
            "        lhs = success0 * total1\n"
            "        rhs = success1 * total0\n"
        )
    else:
        name = "choose_symmetric_prior_" + str(parameter)
        compare = (
            "        if not total0 or not total1:\n"
            "            return None\n"
            f"        lhs = (success0 + {parameter}) * (total1 + {2 * parameter})\n"
            f"        rhs = (success1 + {parameter}) * (total0 + {2 * parameter})\n"
        )
    method = (
        f"    def {name}(self, address: int, *, retained: bool = False) -> int | None:\n"
        "        \"\"\"Optional public-counts DEV control; no default change.\"\"\"\n"
        "        cell = self._address(address, retained)\n"
        "        (fail0, success0), (fail1, success1) = self._counts[cell]\n"
        "        total0, total1 = fail0 + success0, fail1 + success1\n"
        + compare +
        "        if lhs == rhs:\n"
        "            return None\n"
        "        return 0 if lhs > rhs else 1\n\n"
    )
    return name, method


def generate_dev_pool(*, before: bytes, seed_intent: bytes,
                      consumed_after: set[str],
                      last_verified_after: str) -> list[dict]:
    """Generate eight structural alternatives, skipping already spent bytes.

    Every output is a canonical issue plan AND separate selector-only metadata.
    No dynamic source from an external text or developer model is executed.
    The verified-prerequisite hash is a caller-supplied input, not proof by
    itself; use the existing owner ledger audit to establish provenance.
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
        parsed = ast.parse(original)
        seed = json.loads(seed_intent)
    except (UnicodeError, ValueError, SyntaxError, TypeError) as exc:
        raise FreshProposalDenied("F139_FRESH_PROPOSAL_GRAMMAR_PARSE_FAILED") from exc
    initial = parse_intent(seed_intent, protected_main=SOURCE,
                           target_commit=TARGET, target_tree_sha=TARGET_TREE)
    need(type(seed) is dict and initial.path == ACCEPTED_NATIVE_PATH
         and initial.before_sha256 == digest(before)
         and seed.get("scientific_first_use") is False
         and seed.get("paid_api_calls") == 0
         and seed.get("accepted_ref_mutations") == 0
         and seed.get("optimizer_policy_mutations") == 0
         and seed.get("protected_holdouts_accessed") == 0
         and original.count(ANCHOR) == 1
         and sum(isinstance(n, ast.ClassDef) and n.name == "PublicCausalCells"
                 for n in parsed.body) == 1,
         "FROZEN_BASELINE_OR_INTENT_DRIFT")
    result: list[dict] = []
    output_hashes: set[str] = set()
    for family in FAMILIES:
        for parameter in PARAMETERS:
            name, method = method_for(family, parameter)
            need("def " + name + "(" not in original,
                 "METHOD_ALREADY_IN_FROZEN_BASELINE")
            after = original.replace(ANCHOR, method + ANCHOR)
            try:
                checked = ast.parse(after)
            except SyntaxError as exc:
                raise FreshProposalDenied("F139_FRESH_PROPOSAL_GRAMMAR_AST_INVALID") from exc
            need(sum(isinstance(n, ast.ClassDef) and n.name == "PublicCausalCells"
                     for n in checked.body) == 1,
                 "GRAMMAR_CLASS_DRIFT")
            raw_after = after.encode("utf-8")
            after_sha = digest(raw_after)
            need(0 < len(raw_after) <= 32768 and after_sha not in output_hashes
                 and raw_after != before,
                 "GRAMMAR_DUPLICATE_OR_OVERSIZE")
            output_hashes.add(after_sha)
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
                 "GRAMMAR_CONTRACT_NOT_QUALIFIED")
            label = family + "-" + str(parameter) + "-v2"
            issue = {
                "schema": ISSUE_SCHEMA, "source_sha": SOURCE,
                "lane": "Yggdrasil", "kind": ISSUE_KIND,
                "intent_base64": base64.b64encode(raw_intent).decode("ascii"),
                "scientific_first_use": False, "paid_model_calls": 0,
            }
            body = canonical(issue).decode("ascii")
            need(len(body) <= 60000, "GRAMMAR_ISSUE_TOO_LARGE")
            mechanism = digest(canonical({
                "schema": SCHEMA, "family": family, "parameter": parameter,
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
                "title": "F139 auto-feed fresh Yggdrasil DEV: " + label,
                "body": body, "body_sha256": digest(canonical(issue)),
                "after_sha256": after_sha, "intent_sha256": candidate.intent_sha256,
                "mechanism_sha256": mechanism,
                "scientific_first_use": False, "paid_model_calls": 0,
            }
            selector = {
                "schema": PROPOSAL_SCHEMA, "source_sha": SOURCE,
                "target_tree_sha": TARGET_TREE,
                "after_sha256": after_sha, "intent_sha256": candidate.intent_sha256,
                "mechanism_sha256": mechanism, "qualification_sha256": checksum,
                "prerequisites": [last_verified_after], "exclusions": [],
                "cost_units": 2,
                "development_only": True, "scientific_first_use": False,
                "paid_model_calls": 0, "accepted_ref_mutations": 0,
            }
            result.append({"plan": plan, "selection": selector})
    return result


def matching_plan(pool: list[dict], selection: dict) -> dict:
    """Bind a selected identity back to the *exact* generated issue bytes."""
    need(type(pool) is list and 0 < len(pool) <= len(FAMILIES) * len(PARAMETERS)
         and type(selection) is dict and set(selection) == set(
             pool[0].get("selection", {})),
         "GRAMMAR_SELECTION_SHAPE_INVALID")
    same = [item for item in pool if item["selection"] == selection]
    need(len(same) == 1 and type(same[0].get("plan")) is dict,
         "GRAMMAR_SELECTED_PLAN_AMBIGUOUS")
    return dict(same[0]["plan"])
