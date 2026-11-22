"""Finite, model-free next-issue proposal for the EXISTING F139 fresh owner.

Only produces canonical issue data for the original lock-held Windows owner.
No GitHub writes, model calls, queue, scheduler or authority in this module.
The owner must commit a one-shot attempt BEFORE any remote POST, and must
independently authenticate the provider source and consumed history.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import json

from f139.nci04_native_contract import canonical, digest, parse_intent
from f139.nci04_owner_issue import SCHEMA as ISSUE_SCHEMA, KIND as ISSUE_KIND
from f139.nci04_fresh_worker_protocol import SOURCE, TARGET, TARGET_TREE
from f139.nci04_fresh_yggdrasil_boundary import (
    ACCEPTED_NATIVE_PATH, ACCEPTED_NATIVE_BLOB, _content,
)

SCHEMA = "forge.f139.fresh-owner-source-proposal.v1"
REPO = "spoonman136668-ai/Yggdrasil"
ANCHOR = "    def choose(self, address: int, *, retained: bool = False) -> int | None:\n"

# Conventional bounded DEV recipes, not scientific hypotheses being accepted.
# Both are opt-in and leave the default chooser and 164-byte checkpoint intact.
RECIPES = (
    ("least-observed-local-arm-v1", '''
    def propose_least_observed_action(self, address: int, *,
                                      retained: bool = False) -> int | None:
        """Suggest the less observed local arm, abstaining on equal evidence."""
        cell = self._address(address, retained)
        zero = sum(self._counts[cell][0])
        one = sum(self._counts[cell][1])
        if zero == one:
            return None
        return 0 if zero < one else 1

'''),
    ("laplace-local-evidence-v1", '''
    def choose_laplace(self, address: int, *,
                       retained: bool = False) -> int | None:
        """Rank observed local public outcomes with fixed unit pseudocounts."""
        cell = self._address(address, retained)
        (fail0, success0), (fail1, success1) = self._counts[cell]
        if not (fail0 + success0) or not (fail1 + success1):
            return None
        lhs = (success0 + 1) * (fail1 + success1 + 2)
        rhs = (success1 + 1) * (fail0 + success0 + 2)
        if lhs == rhs:
            return None
        return 0 if lhs > rhs else 1

'''),
)

class FreshProposalDenied(ValueError):
    pass


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise FreshProposalDenied("F139_FRESH_PROPOSAL_" + reason)


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii")
                        + b"\0" + raw).hexdigest()


def propose_one(*, before: bytes, seed_intent: bytes,
                consumed_after: set[str]) -> dict | None:
    """Pure bounded one-candidate selection from authenticated owner inputs.

    No re-creation after all recipes are consumed; the frozen history is
    supplied by the original owner and independently validated by its caller.
    """
    need(type(before) is bytes and 0 < len(before) <= 32768
         and git_blob(before) == ACCEPTED_NATIVE_BLOB
         and type(seed_intent) is bytes
         and type(consumed_after) is set
         and len(consumed_after) <= 10000
         and all(type(s) is str and len(s) == 64
                 and all(c in "0123456789abcdef" for c in s)
                 for s in consumed_after),
         "SOURCE_OR_HISTORY_INVALID")
    try:
        text = before.decode("utf-8", "strict")
        tree = ast.parse(text)
        seed = json.loads(seed_intent)
    except (UnicodeError, SyntaxError, ValueError, TypeError) as exc:
        raise FreshProposalDenied("F139_FRESH_PROPOSAL_SOURCE_PARSE_INVALID") from exc
    original = parse_intent(seed_intent, protected_main=SOURCE,
                            target_commit=TARGET, target_tree_sha=TARGET_TREE)
    need(type(seed) is dict
         and original.path == ACCEPTED_NATIVE_PATH
         and original.before_sha256 == digest(before)
         and seed.get("scientific_first_use") is False
         and seed.get("paid_api_calls") == 0
         and seed.get("protected_holdouts_accessed") == 0
         and text.count(ANCHOR) == 1
         and sum(isinstance(n, ast.ClassDef) and
                 n.name == "PublicCausalCells" for n in tree.body) == 1,
         "FROZEN_BASELINE_OR_INTENT_DRIFT")
    for recipe, method in RECIPES:
        name = method.split("def ", 1)[1].split("(", 1)[0]
        need("def " + name + "(" not in text, "RECIPE_ALREADY_IN_BASELINE")
        after = text.replace(ANCHOR, method + ANCHOR)
        try:
            ast.parse(after)
        except SyntaxError as exc:
            raise FreshProposalDenied("F139_FRESH_PROPOSAL_AST_INVALID") from exc
        output = after.encode("utf-8")
        need(0 < len(output) <= 32768 and output != before,
             "CANDIDATE_BYTES_INVALID")
        after_hash = digest(output)
        if after_hash in consumed_after:
            continue
        intent = dict(seed)
        intent["after_base64"] = base64.b64encode(output).decode("ascii")
        intent["after_sha256"] = after_hash
        raw_intent = canonical(intent)
        candidate = parse_intent(raw_intent, protected_main=SOURCE,
                                 target_commit=TARGET, target_tree_sha=TARGET_TREE)
        need(candidate.after_sha256 == after_hash
             and candidate.path == ACCEPTED_NATIVE_PATH,
             "GENERATED_INTENT_NOT_QUALIFIED")
        body = canonical({
            "schema": ISSUE_SCHEMA, "source_sha": SOURCE,
            "lane": "Yggdrasil", "kind": ISSUE_KIND,
            "intent_base64": base64.b64encode(raw_intent).decode("ascii"),
            "scientific_first_use": False, "paid_model_calls": 0,
        }).decode("ascii")
        mechanism = digest(canonical({
            "schema": SCHEMA, "recipe": recipe, "baseline_blob": ACCEPTED_NATIVE_BLOB,
            "after_sha256": after_hash,
        }))
        need(len(body.encode("utf-8")) <= 60000,
             "ISSUE_BODY_TOO_LARGE")
        return {
            "schema": SCHEMA, "recipe": recipe,
            "title": "F139 auto-feed fresh Yggdrasil DEV: " + recipe,
            "body": body, "body_sha256": digest(canonical(json.loads(body))),
            "after_sha256": after_hash,
            "intent_sha256": candidate.intent_sha256,
            "mechanism_sha256": mechanism,
            "scientific_first_use": False, "paid_model_calls": 0,
        }
    return None


def propose_from_original_owner(api, initial_record: dict,
                                consumed_after: set[str]) -> dict | None:
    """Verify the accepted provider tree before preparing issue-only data."""
    main = api.native_repo_get("repos/" + REPO + "/branches/main")
    commit = api.native_repo_get("repos/" + REPO + "/git/commits/" + TARGET)
    need(main.get("name") == "main" and main.get("protected") is True
         and main.get("commit", {}).get("sha") == TARGET
         and commit.get("sha") == TARGET
         and commit.get("tree", {}).get("sha") == TARGET_TREE,
         "PROTECTED_NATIVE_TARGET_DRIFT")
    before = _content(api.native_repo_get, ACCEPTED_NATIVE_PATH,
                      TARGET, ACCEPTED_NATIVE_BLOB)
    need(api.native_repo_get("repos/" + REPO + "/branches/main") == main,
         "NATIVE_MAIN_MOVED")
    need(type(initial_record) is dict
         and type(initial_record.get("native_intent_base64")) is str,
         "INITIAL_SEALED_INTENT_MISSING")
    try:
        initial = base64.b64decode(initial_record["native_intent_base64"],
                                   validate=True)
    except ValueError as exc:
        raise FreshProposalDenied("F139_FRESH_PROPOSAL_INITIAL_ENCODING") from exc
    return propose_one(before=before, seed_intent=initial,
                       consumed_after=consumed_after)
