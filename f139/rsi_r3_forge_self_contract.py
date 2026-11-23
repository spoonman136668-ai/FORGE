"""Source-only, deny-by-default FORGE-self engineering candidate contract.

This is NOT a modification of the F139 native worker/owner intake, policy,
research lanes, accepted source, or deployment. Only one fully reviewed source
rewrite of one original maintained FORGE module is representable here.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
import re

SCHEMA = "forge.f139.rsi-r3.forge-self-source-candidate.v1"
FROZEN_PARENT_COMMIT = "e48693e41347942c2b581c2fa2793406020b7b67"
FROZEN_PARENT_TREE = "7047c3ec1b6ef92064044c7020cf10155f6bbda5"
TARGET = "f139/nci04_portfolio_source_boundary.py"
TARGET_BLOB = "8bb13f14f6039032cde4aca623a38713ea47b4e9"
MAX_SOURCE_BYTES = 32_768
OPERATOR = "reuse-unchanged-ast-identity"
# Existing scripts and platform CI own these commands. No user-selected argv.
REQUIRED_QUALIFICATION = (
    ("python", "-B", "-m", "unittest", "f139.test_nci04_portfolio_source_boundary", "-v"),
    ("python", "-B", "-m", "unittest", "discover", "-s", "f139", "-p", "test_*.py"),
    ("go", "test", "./..."),
    ("go", "vet", "./..."),
    ("go", "build", "./..."),
)
# These exact, existing source lines locate the original operational
# implementation. This is a source generation rule, not an arbitrary diff API.
ANCHOR = (
    "    old_ast = _ast_identity(before)\n"
    "    new_ast = _ast_identity(candidate.after)\n"
)
REPLACEMENT = (
    "    old_ast = _ast_identity(before)\n"
    "    # Reuse the known identity when the unchanged source is rejected.\n"
    "    new_ast = (old_ast if candidate.after == before\n"
    "               else _ast_identity(candidate.after))\n"
)


class SelfContractDenied(ValueError):
    pass


def need(value: bool, reason: str) -> None:
    if not value:
        raise SelfContractDenied("F139_RSI_SELF_" + reason)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _original(before: bytes) -> str:
    need(type(before) is bytes and 0 < len(before) < MAX_SOURCE_BYTES,
         "SOURCE_BYTES_OR_LIMIT")
    need(git_blob(before) == TARGET_BLOB, "PINNED_PREIMAGE_DRIFT")
    try:
        old = before.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise SelfContractDenied("F139_RSI_SELF_UTF8_INVALID") from exc
    need(old.count(ANCHOR) == 1 and "\r" not in old, "ANCHOR_OR_EOL_DRIFT")
    return old


def rewrite(before: bytes, operator: str) -> bytes:
    """Emit one bounded actual-source candidate without executing any input."""
    need(type(operator) is str and operator == OPERATOR,
         "OPERATOR_NOT_AUTHORIZED")
    old = _original(before)
    after = old.replace(ANCHOR, REPLACEMENT, 1).encode("utf-8")
    need(after != before and len(after) <= MAX_SOURCE_BYTES,
         "NO_BOUNDED_SOURCE_EDIT")
    try:
        original_ast = ast.parse(old, filename=TARGET)
        after_ast = ast.parse(after.decode("utf-8"), filename=TARGET)
    except SyntaxError as exc:
        raise SelfContractDenied("F139_RSI_SELF_SOURCE_UNPARSEABLE") from exc
    need(ast.dump(original_ast, include_attributes=False) !=
         ast.dump(after_ast, include_attributes=False),
         "UNCHANGED_AST")
    # Only the AST of the original named function may change. The original
    # imports, all other function definitions and module-level code are fixed.
    def without_target(tree: ast.Module) -> str:
        bodies = [node for node in tree.body
                  if not (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                          and node.name == "validate_source_candidate")]
        return ast.dump(ast.Module(body=bodies, type_ignores=[]),
                        include_attributes=False)
    need(without_target(original_ast) == without_target(after_ast),
         "UNRELATED_AST_DRIFT")
    return after


@dataclass(frozen=True)
class SelfProposal:
    schema: str
    origin_commit: str
    origin_tree: str
    path: str
    operator: str
    before_blob: str
    before_sha256: str
    after_sha256: str
    after: bytes
    provenance_sha256: str
    qualification_commands: tuple[tuple[str, ...], ...]
    eligible_for_owner: bool = False
    scientific_first_use: bool = False
    deployment_authorized: bool = False
    rsi_proven: bool = False


def canonical_receipt(*, before_hash: str, after_hash: str) -> str:
    payload = {"schema": SCHEMA, "origin_commit": FROZEN_PARENT_COMMIT,
               "origin_tree": FROZEN_PARENT_TREE, "path": TARGET,
               "operator": OPERATOR, "before_blob": TARGET_BLOB,
               "before_sha256": before_hash, "after_sha256": after_hash,
               "qualification_commands": REQUIRED_QUALIFICATION,
               "eligible_for_owner": False, "scientific_first_use": False,
               "deployment_authorized": False, "rsi_proven": False}
    return digest(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())


def propose(*, original_source: bytes, pinned_commit: str, pinned_tree: str,
            path: str, operator: str = OPERATOR,
            consumed_source_hashes: frozenset[str]) -> SelfProposal:
    """Pure-source boundary; caller must separately authenticate Git originals.

    `consumed_source_hashes` is a caller-provided development filter, not a
    verified complete owner ledger. This function cannot confer admission.
    """
    need(pinned_commit == FROZEN_PARENT_COMMIT and
         pinned_tree == FROZEN_PARENT_TREE and path == TARGET,
         "FROZEN_COMMIT_TREE_OR_PATH_DRIFT")
    need(type(consumed_source_hashes) is frozenset and
         all(type(x) is str and re.fullmatch(r"[0-9a-f]{64}", x)
             for x in consumed_source_hashes), "CONSUMED_IDENTITIES_UNTRUSTED")
    emitted = rewrite(original_source, operator)
    new_hash = digest(emitted)
    need(new_hash not in consumed_source_hashes, "CONSUMED_SOURCE_NO_REPLAY")
    old_hash = digest(original_source)
    return SelfProposal(SCHEMA, pinned_commit, pinned_tree, path, operator,
                        TARGET_BLOB, old_hash, new_hash, emitted,
                        canonical_receipt(before_hash=old_hash,
                                          after_hash=new_hash),
                        REQUIRED_QUALIFICATION)


def verify(proposal: SelfProposal, original_source: bytes,
           consumed_source_hashes: frozenset[str]) -> bool:
    need(type(proposal) is SelfProposal, "RECEIPT_TYPE_INVALID")
    recreated = propose(original_source=original_source,
                         pinned_commit=proposal.origin_commit,
                         pinned_tree=proposal.origin_tree,
                         path=proposal.path, operator=proposal.operator,
                         consumed_source_hashes=consumed_source_hashes)
    need(recreated == proposal, "CANDIDATE_OR_PROVENANCE_DRIFT")
    return True
