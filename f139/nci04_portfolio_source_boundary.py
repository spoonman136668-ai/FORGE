"""Source-only, non-executing boundary for portfolio-generated F139 proposals.

This module does not call optimizers, dispatch, publish, or grant authority.
A historical optimizer identity is NOT a candidate source. The original owner
must separately authenticate source bytes and publication session.
"""
from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass

FAMILIES = frozenset({"dream_rsi", "shinka_pareto", "theta_evolve",
                      "promptbreeder", "dgm_genenv"})
MAX_BYTES = 256_000


class PortfolioSourceRejected(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _ast_identity(raw: bytes) -> str:
    try:
        tree = ast.parse(raw.decode("utf-8", "strict"))
    except (SyntaxError, UnicodeError) as exc:
        raise PortfolioSourceRejected("SOURCE_NOT_PARSEABLE") from exc
    return _sha(ast.dump(tree, include_attributes=False).encode("utf-8"))


@dataclass(frozen=True)
class SourceCandidate:
    generator: str
    lane: str
    path: str
    parent_sha: str
    before_sha256: str
    after_sha256: str
    mechanism_sha256: str
    question: str
    hypothesis: str
    after: bytes


def validate_source_candidate(candidate: SourceCandidate, *, lane: str,
                              path: str, parent_sha: str, before: bytes,
                              historical_sha256: frozenset[str],
                              historical_ast_sha256: frozenset[str]) -> str:
    """Return the new AST identity only after strict source/novelty checks.

    No optimistic inference from a policy score, proposal lineage, or
    historical selection. Historical hashes must include negative attempts.
    """
    if type(candidate) is not SourceCandidate:
        raise PortfolioSourceRejected("UNRECOGNIZED_PROPOSAL")
    if candidate.generator not in FAMILIES or candidate.lane != lane or lane not in ("Wingless", "Yggdrasil"):
        raise PortfolioSourceRejected("GENERATOR_OR_LANE")
    if candidate.path != path or candidate.parent_sha != parent_sha or len(parent_sha) != 40:
        raise PortfolioSourceRejected("PINNED_PARENT_OR_PATH")
    if not all(c in "0123456789abcdef" for c in parent_sha):
        raise PortfolioSourceRejected("PARENT_SHA")
    if type(before) is not bytes or type(candidate.after) is not bytes:
        raise PortfolioSourceRejected("SOURCE_BYTES_REQUIRED")
    if not (0 < len(before) <= MAX_BYTES and 0 < len(candidate.after) <= MAX_BYTES):
        raise PortfolioSourceRejected("SOURCE_SIZE")
    if candidate.before_sha256 != _sha(before) or candidate.after_sha256 != _sha(candidate.after):
        raise PortfolioSourceRejected("SOURCE_DIGEST_DRIFT")
    if len(candidate.mechanism_sha256) != 64 or any(c not in "0123456789abcdef" for c in candidate.mechanism_sha256):
        raise PortfolioSourceRejected("MECHANISM_IDENTITY")
    if not (0 < len(candidate.question.strip()) <= 512 and
            0 < len(candidate.hypothesis.strip()) <= 2048):
        raise PortfolioSourceRejected("HYPOTHESIS_MISSING")
    old_ast = _ast_identity(before)
    new_ast = _ast_identity(candidate.after)
    if candidate.after_sha256 in historical_sha256 or new_ast in historical_ast_sha256:
        raise PortfolioSourceRejected("HISTORICAL_REPLAY")
    if old_ast == new_ast:
        raise PortfolioSourceRejected("NO_SEMANTIC_CHANGE")
    return new_ast


def validate_generation_batch(candidates, *, generator: str, mechanism: bytes,
                              mechanism_sha256: str, lane: str, path: str,
                              parent_sha: str, before: bytes,
                              historical_sha256: frozenset[str],
                              historical_ast_sha256: frozenset[str]):
    """Validate actual compiler outputs, never coerce advisory optimizer JSON.

    The caller supplies an independently pinned mechanism artifact. This is a
    non-executing adapter: it neither invents edits from policy weights nor
    invokes candidate Python. The original owner still authenticates custody.
    A whole bounded batch is checked before any candidate is returned.
    """
    if generator not in FAMILIES or type(mechanism) is not bytes or not mechanism:
        raise PortfolioSourceRejected("MECHANISM_ARTIFACT_REQUIRED")
    if _sha(mechanism) != mechanism_sha256:
        raise PortfolioSourceRejected("MECHANISM_ARTIFACT_DRIFT")
    if type(candidates) is not tuple or not 1 <= len(candidates) <= 16:
        raise PortfolioSourceRejected("BOUNDED_SOURCE_BATCH_REQUIRED")
    raw_seen = set(historical_sha256)
    ast_seen = set(historical_ast_sha256)
    receipts = []
    for candidate in candidates:
        if type(candidate) is not SourceCandidate:
            raise PortfolioSourceRejected("UNRECOGNIZED_PROPOSAL")
        if candidate.generator != generator or candidate.mechanism_sha256 != mechanism_sha256:
            raise PortfolioSourceRejected("MECHANISM_OUTPUT_MISMATCH")
        ast_id = validate_source_candidate(
            candidate, lane=lane, path=path, parent_sha=parent_sha, before=before,
            historical_sha256=frozenset(raw_seen),
            historical_ast_sha256=frozenset(ast_seen))
        raw_seen.add(candidate.after_sha256)
        ast_seen.add(ast_id)
        receipts.append((candidate, ast_id))
    return tuple(receipts)
