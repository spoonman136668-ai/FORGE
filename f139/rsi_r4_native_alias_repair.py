"""Agent-free source repair of one verified SQLite-import-alias defect class.

Extends the already-qualified R16 AST resource-repair compiler without
modifying it. Returns proposed source only; no file, Git, owner, runner, API,
science-first-use or scheduler mutation, and no RSI success claim.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import re

from f139.r16_semantic_repair import (
    FAILURE_CLASS, UnsafeRepair, _repair_python,
)

SCHEMA = "forge.f139.rsi-r4.native-sqlite-alias-repair.v1"
MAX_BYTES = 24_999
PATH = re.compile(r"f139/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+\.py\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_CONNECTIONS = 6


class AliasRepairDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise AliasRepairDenied("RSI_R4_ALIAS_" + reason)


def digest(source: bytes) -> str:
    need(type(source) is bytes, "SOURCE_BYTES_REQUIRED")
    return hashlib.sha256(source).hexdigest()


@dataclass(frozen=True)
class SourcePatch:
    schema: str
    path: str
    original_sha256: str
    proposed_sha256: str
    rule: str
    repaired_connections: int
    proposed_source: bytes
    # Immutable *provenance*, not repair acceptance or owner authorization.
    original_owner_activated: bool = False
    independently_qualified: bool = False
    scientific_first_use: bool = False
    rsi_proven: bool = False


def _alias_to_direct_import(script: str) -> tuple[str, str]:
    """Use AST-bound spans; reject every sqlite alias use outside a simple with.

    The trusted R16 source generator recognizes exactly sqlite3.connect, so
    normalize the one import and its with-bound references before R16 runs.
    No arbitrary source payload is executed or interpolated into a program.
    """
    tree = ast.parse(script)
    imports = [(node, item) for node in tree.body
               if isinstance(node, ast.Import)
               for item in node.names if item.name == "sqlite3"]
    need(len(imports) == 1, "EXACT_IMPORT_REQUIRED")
    imp, imported = imports[0]
    if imported.asname is None:
        return script, "r16-direct"
    alias = imported.asname
    need(alias != "sqlite3" and alias.isidentifier() and alias.isascii(),
         "ALIAS_INVALID")
    need(imp.lineno == imp.end_lineno, "MULTILINE_IMPORT_DENIED")

    # A canonical name already in use (or a rebinding of the alias) makes
    # lexical normalization unsafe, even if the resulting file parses.
    for node in ast.walk(tree):
        need(not (isinstance(node, ast.Name) and node.id == "sqlite3"),
             "CANONICAL_NAME_COLLISION")
        need(not (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                    ast.ClassDef)) and node.name in (alias, "sqlite3")),
             "NAME_REBINDING")
        need(not (isinstance(node, ast.arg)
                  and node.arg in (alias, "sqlite3")), "PARAMETER_SHADOW")
        need(not (isinstance(node, ast.ExceptHandler)
                  and node.name in (alias, "sqlite3")), "EXCEPT_SHADOW")
        need(not (isinstance(node, (ast.Global, ast.Nonlocal))
                  and (alias in node.names or "sqlite3" in node.names)),
             "SCOPE_REBINDING")
        need(not (isinstance(node, ast.ImportFrom) and
                  any(x.name == "sqlite3" or x.asname in (alias, "sqlite3")
                      for x in node.names)), "SECOND_IMPORT")
        if isinstance(node, ast.Import):
            for x in node.names:
                if x is not imported:
                    need(x.asname not in (alias, "sqlite3") and
                         x.name != "sqlite3", "IMPORT_NAME_COLLISION")

    allowed = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                call = item.context_expr
                if (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and isinstance(call.func.value, ast.Name)
                        and call.func.value.id == alias):
                    # Mirror R16's finite safe context grammar.
                    need(isinstance(node, ast.With) and len(node.items) == 1
                         and call.func.attr == "connect"
                         and isinstance(item.optional_vars, ast.Name),
                         "ALIAS_CONTEXT_COMPLEX")
                    allowed.append(call.func.value)
    refs = [n for n in ast.walk(tree)
            if isinstance(n, ast.Name) and n.id == alias]
    need(0 < len(allowed) <= MAX_CONNECTIONS and
         {id(n) for n in allowed} == {id(n) for n in refs} and
         len(allowed) == len(refs), "ALIAS_REFERENCE_OUTSIDE_WITH")
    # Additional bindings that AST represents as plain strings.
    for node in ast.walk(tree):
        need(not (isinstance(node, (ast.MatchAs, ast.MatchStar))
                  and node.name in (alias, "sqlite3")), "MATCH_BINDING")

    lines = script.splitlines(keepends=True)
    fragment = ast.get_source_segment(script, imp)
    need(isinstance(fragment, str) and "\n" not in fragment
         and fragment == lines[imp.lineno - 1][imp.col_offset:imp.end_col_offset],
         "IMPORT_SOURCE_DRIFT")
    pattern = r"(?<![A-Za-z0-9_])sqlite3[ \t]+as[ \t]+" + re.escape(alias) + r"(?![A-Za-z0-9_])"
    replaced, count = re.subn(pattern, "sqlite3", fragment)
    need(count == 1, "IMPORT_ALIAS_DRIFT")
    edits = [(imp.lineno - 1, imp.col_offset, imp.end_col_offset, fragment, replaced)]
    for ref in refs:
        need(ref.lineno == ref.end_lineno, "ALIAS_REF_MULTILINE")
        edits.append((ref.lineno - 1, ref.col_offset, ref.end_col_offset,
                      alias, "sqlite3"))
    for row, start, end, original, replacement in sorted(edits, reverse=True):
        need(0 <= row < len(lines) and
             lines[row][start:end] == original, "ALIAS_SPAN_DRIFT")
        lines[row] = lines[row][:start] + replacement + lines[row][end:]
    normalized = "".join(lines)
    need(normalized != script, "ALIAS_UNCHANGED")
    ast.parse(normalized)
    return normalized, "r16-ast-alias-normalization"


def propose(*, original_source: bytes, expected_sha256: str,
            path: str, failure_class: str) -> SourcePatch:
    """Generate at most one compileable repair from a caller-pinned source.

    The caller must authenticate the source and failure independently. Digest
    equality to a caller-provided value alone is NOT source-owner evidence.
    """
    need(type(path) is str and PATH.fullmatch(path) is not None,
         "TARGET_PATH_NOT_ALLOWED")
    need(type(failure_class) is str and failure_class == FAILURE_CLASS,
         "FAILURE_CLASS_NOT_ALLOWED")
    need(type(expected_sha256) is str
         and SHA256.fullmatch(expected_sha256) is not None,
         "EXPECTED_DIGEST_INVALID")
    need(type(original_source) is bytes and
         0 < len(original_source) <= MAX_BYTES and
         b"\r" not in original_source, "SOURCE_TYPE_SIZE_OR_EOL")
    need(digest(original_source) == expected_sha256,
         "PINNED_SOURCE_DRIFT")
    try:
        source = original_source.decode("ascii", "strict")
    except UnicodeError as exc:
        raise AliasRepairDenied("RSI_R4_ALIAS_ASCII_ONLY") from exc
    try:
        normalized, rule = _alias_to_direct_import(source)
    except (SyntaxError, ValueError) as exc:
        if isinstance(exc, AliasRepairDenied):
            raise
        raise AliasRepairDenied("RSI_R4_ALIAS_SOURCE_INVALID") from exc
    # Reuse R16's original bounded transaction/closing proof, not a new
    # shortcut that could silently roll back database updates.
    repaired, count = _repair_python(normalized)
    candidate = repaired.encode("ascii")
    need(0 < len(candidate) <= MAX_BYTES and candidate != original_source
         and 1 <= count <= MAX_CONNECTIONS, "CANDIDATE_NOT_BOUNDED")
    compile(candidate, path, "exec")
    return SourcePatch(SCHEMA, path, expected_sha256, digest(candidate),
                       rule, count, candidate)
