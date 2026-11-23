"""Finite, deterministic, source-pinned native candidate construction.

This is a *development-only* model-free code candidate producer, not a
research authority, optimizer acceptance, GitHub writer, queue, scheduler or
scientific first-use. Its one currently qualified recipe tests whether public
outcome experience from *other visible contexts within the same memory tier*
can supply a missing arm on a new Yggdrasil context. Such transfer might
instead be confounding/negative, which is an essential controlled outcome.

The output is source bytes to be independently committed as an owner-authored
one-file/one-parent draft PR and reauthenticated by the original F139 feeder.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re

from f139.nci04_autonomy_feed import candidate_identity
from f139.nci04_native_contract import canonical, digest

SCHEMA = "forge.f139.native-source-candidate.v1"
MECHANISM = "tier-local-partial-pooling-when-unobserved-v1"
LANE = "Yggdrasil"
PATH = "yggdrasil/public_causal_cells.py"
GENERATOR = "dream_rsi"
_SHA40 = re.compile(r"[a-f0-9]{40}\Z")
_SHA64 = re.compile(r"[a-f0-9]{64}\Z")

# Replacing this exact existing behavior makes one structural policy choice:
# transfer empirical outcome evidence to an otherwise-unobserved arm from
# other PUBLIC addresses in the same active or retained tier. It uses no
# hidden outcomes, extra memory, cross-tier leakage, or new API dependency.
# Only independent unfamiliar-family evaluations can tell if it generalizes.
_ANCHOR = (
    "        if not trials0 or not trials1:\n"
    "            return None\n"
)
_REPLACEMENT = (
    "        if not trials0 or not trials1:\n"
    "            # Experimental partial pooling: borrow only public outcomes\n"
    "            # from other addresses in this SAME active/retained tier.\n"
    "            # Confounding across contexts may make this worse than abstention.\n"
    "            start = self.ACTIVE_SLOTS if retained else 0\n"
    "            limit = self.RETAINED_SLOTS if retained else self.ACTIVE_SLOTS\n"
    "            pooled0 = pooled1 = 0\n"
    "            for other in range(start, start + limit):\n"
    "                if other == cell:\n"
    "                    continue\n"
    "                (n00, n01), (n10, n11) = self._counts[other]\n"
    "                if not trials0:\n"
    "                    pooled0 += n00\n"
    "                    one0 += n01\n"
    "                if not trials1:\n"
    "                    pooled1 += n10\n"
    "                    one1 += n11\n"
    "            if not trials0:\n"
    "                trials0 = pooled0 + one0\n"
    "            if not trials1:\n"
    "                trials1 = pooled1 + one1\n"
    "            if not trials0 or not trials1:\n"
    "                return None\n"
)


class CandidateProducerDenied(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise CandidateProducerDenied("F139_CANDIDATE_PRODUCER_" + reason)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def candidate_mechanism_identity() -> str:
    return digest(canonical({
        "schema": SCHEMA,
        "lane": LANE,
        "generator": GENERATOR,
        "recipe": MECHANISM,
        "source_path": PATH,
        "replace_sha256": sha256(_REPLACEMENT.encode("utf-8")),
    }))


def produce(*, lane: str, path: str, parent_commit: str,
            before_bytes: bytes, pinned_before_sha256: str,
            history_sha256: str, consumed_mechanism_sha256: set[str],
            scientific_first_use: bool = False) -> dict:
    """Emit source bytes + non-authorizing, deduplicable candidate identity.

    The parent SHA and before bytes must be authenticated independently via
    GitHub GET by the caller, not trusted merely because they were supplied.
    This function only validates their equality to the supplied hash.
    """
    require(lane == LANE and path == PATH
            and isinstance(parent_commit, str)
            and _SHA40.fullmatch(parent_commit) is not None
            and type(before_bytes) is bytes and 100 <= len(before_bytes) <= 32768
            and isinstance(pinned_before_sha256, str)
            and _SHA64.fullmatch(pinned_before_sha256) is not None
            and sha256(before_bytes) == pinned_before_sha256
            and isinstance(history_sha256, str)
            and _SHA64.fullmatch(history_sha256) is not None
            and isinstance(consumed_mechanism_sha256, set)
            and len(consumed_mechanism_sha256) <= 10000
            and all(isinstance(s, str) and _SHA64.fullmatch(s)
                    for s in consumed_mechanism_sha256)
            and scientific_first_use is False,
            "INPUT_OR_AUTHORITY_DRIFT")
    mechanism = candidate_mechanism_identity()
    require(mechanism not in consumed_mechanism_sha256,
            "HISTORICAL_MECHANISM_ALREADY_CONSUMED")
    try:
        before = before_bytes.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise CandidateProducerDenied(
            "F139_CANDIDATE_PRODUCER_INPUT_ENCODING") from exc
    require(before.count(_ANCHOR) == 1
            and "class PublicCausalCells:" in before
            and "def choose(self, address:" in before
            and "RETAINED_SLOTS = 9" in before
            and "ACTIVE_SLOTS = 7" in before,
            "NATIVE_CONTEXT_NOT_FROZEN")
    try:
        tree = ast.parse(before, filename=PATH)
        require(any(isinstance(node, ast.ClassDef)
                    and node.name == "PublicCausalCells" for node in tree.body),
                "ORIGINAL_AST_IDENTITY_DRIFT")
    except (SyntaxError, ValueError, TypeError) as exc:
        raise CandidateProducerDenied(
            "F139_CANDIDATE_PRODUCER_ORIGINAL_AST_INVALID") from exc
    after = before.replace(_ANCHOR, _REPLACEMENT, 1)
    try:
        ast.parse(after, filename=PATH)
    except (SyntaxError, ValueError, TypeError) as exc:
        raise CandidateProducerDenied(
            "F139_CANDIDATE_PRODUCER_GENERATED_AST_INVALID") from exc
    output = after.encode("utf-8")
    require(output != before_bytes and 100 <= len(output) <= 32768,
            "OUTPUT_NOT_BOUNDED_NEW_SOURCE")
    after_sha256 = sha256(output)
    identity = candidate_identity(lane, parent_commit, path, after_sha256)
    record = {
        "schema": SCHEMA, "lane": lane, "path": path,
        "parent_commit": parent_commit, "before_sha256": pinned_before_sha256,
        "after_sha256": after_sha256, "candidate_identity": identity,
        "generator": GENERATOR, "mechanism": MECHANISM,
        "mechanism_sha256": mechanism, "history_sha256": history_sha256,
        "hypothesis": (
            "Tier-local partial pooling supplies unseen public action-outcome "
            "evidence for unfamiliar contexts; falsify with adversarial "
            "context-confounding and unseen-family transfer controls"),
        "estimates_only": True, "historical_negatives_preserved": True,
        "independent_scientific_acceptance": False,
        "scientific_first_use": False, "dispatch_authorized": False,
        "policy_promotion_authorized": False, "paid_model_calls": 0,
        "new_controller": False, "new_scheduler": False,
    }
    return {
        "source": output, "record": record,
        "record_sha256": digest(canonical(record)),
        "candidate_identity": identity,
        "pr_title": "F139 autonomy DEV: tier-local public causal partial pooling",
        "requires_independent_source_authentication": True,
        "requires_unchanged_existing_f139_intake": True,
    }
