"""Bounded AST repair synthesis for authenticated Windows SQLite leaks.

This code returns a proposed source string only. It never executes inputs,
writes files, changes the owner, or authorizes source promotion or science.
"""
from __future__ import annotations

import ast
import re

FAILURE_CLASS = "WINDOWS_SQLITE_OPEN_HANDLE_CLEANUP"


class UnsafeRepair(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise UnsafeRepair("R16_SQLITE_REPAIR_" + reason)


def _sqlite_connect(expr: ast.expr) -> bool:
    return (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Attribute)
        and expr.func.attr == "connect"
        and isinstance(expr.func.value, ast.Name)
        and expr.func.value.id == "sqlite3"
        and not any(keyword.arg is None for keyword in expr.keywords)
    )


def _repair_python(script: str) -> tuple[str, int]:
    require(script and len(script) < 25000 and "\r" not in script,
            "SCRIPT_SIZE_OR_EOL")
    try:
        tree = ast.parse(script)
    except SyntaxError as exc:
        raise UnsafeRepair("R16_SQLITE_REPAIR_SOURCE_PYTHON_UNPARSABLE") from exc
    imports = [node for node in tree.body if isinstance(node, ast.Import)
               and any(alias.name == "sqlite3" and alias.asname is None
                       for alias in node.names)]
    require(len(imports) == 1, "SQLITE_IMPORT_UNTRUSTED")
    require(not any(isinstance(n, (ast.Import, ast.ImportFrom)) and any(
        alias.name == "contextlib" or alias.asname == "contextlib" for alias in n.names)
        for n in ast.walk(tree)), "ALREADY_REPAIRED_OR_IMPORT_DRIFT")
    require(any(isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "tempfile"
                and n.func.attr == "TemporaryDirectory"
                for n in ast.walk(tree)), "NO_TEMPORARY_DATABASE_SCOPE")
    changes: list[tuple[int, int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        items = [item for item in node.items if _sqlite_connect(item.context_expr)]
        if not items:
            continue
        require(isinstance(node, ast.With) and len(node.items) == 1,
                "CONNECTION_CONTEXT_COMPLEX")
        context = items[0].context_expr
        require(context.lineno == context.end_lineno,
                "MULTILINE_CONTEXT_UNSUPPORTED")
        raw = ast.get_source_segment(script, context)
        require(isinstance(raw, str) and raw.startswith("sqlite3.connect(")
                and raw.endswith(")") and "\n" not in raw,
                "SOURCE_CONTEXT_DRIFT")
        # Preserve the transaction manager's commit/rollback, then close.
        # A closing() replacement by itself rolls back pending writes.
        binding = items[0].optional_vars
        require(isinstance(binding, ast.Name)
                and binding.lineno == context.lineno
                and binding.end_lineno == context.lineno,
                "CONNECTION_BINDING_REQUIRED")
        changes.append((context.lineno - 1, context.col_offset,
                        binding.end_col_offset,
                        "contextlib.closing(" + raw + ") as " +
                        binding.id + ", " + binding.id))
    require(1 <= len(changes) <= 6, "NO_BOUNDED_CONNECTION_LEAK")
    imp = imports[0]
    require(imp.lineno == imp.end_lineno, "COMPLEX_IMPORT")
    lines = script.splitlines(keepends=True)
    line = lines[imp.lineno - 1]
    prefix, rest = line[:imp.col_offset], line[imp.col_offset:]
    require(rest.startswith("import ") and "contextlib" not in rest,
            "IMPORT_STATEMENT_DRIFT")
    lines[imp.lineno - 1] = (
        prefix + "import contextlib, " + rest[len("import "):])
    for idx, start, end, replacement in sorted(changes, reverse=True):
        old = lines[idx]
        require(len(old[:start].encode("utf-8")) == start
                and old[start:end].startswith("sqlite3.connect("),
                "CONTEXT_COLUMN_DRIFT")
        lines[idx] = old[:start] + replacement + old[end:]
    repaired = "".join(lines)
    try:
        next_tree = ast.parse(repaired)
    except SyntaxError as exc:
        raise UnsafeRepair("R16_SQLITE_REPAIR_INVALID_GENERATION") from exc
    closing = [
        n for n in ast.walk(next_tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "contextlib"
        and n.func.attr == "closing"
    ]
    # For every closing(), a second comma-separated context must enter the
    # same sqlite3.Connection before closing() exits, preserving transaction
    # commit on success and rollback on exception.
    managed = []
    for node in ast.walk(next_tree):
        if not isinstance(node, ast.With) or len(node.items) != 2:
            continue
        first, second = node.items
        if (isinstance(first.context_expr, ast.Call)
                and isinstance(first.context_expr.func, ast.Attribute)
                and isinstance(first.context_expr.func.value, ast.Name)
                and first.context_expr.func.value.id == "contextlib"
                and first.context_expr.func.attr == "closing"):
            managed.append(
                isinstance(first.optional_vars, ast.Name)
                and isinstance(second.context_expr, ast.Name)
                and second.context_expr.id == first.optional_vars.id
                and second.optional_vars is None)
    require(len(closing) == len(changes) == len(managed)
            and all(managed) and repaired != script,
            "POST_REPAIR_AST_DRIFT")
    return repaired, len(changes)


def synthesize_workflow_repair(workflow: str,
                               failure_class: str) -> tuple[str, int]:
    """Rewrite only one embedded PowerShell Python script, not workflow policy.

    Caller must authenticate the failure, pinned preimage and independent tests.
    The generated candidate is never authorized to run on the owner.
    """
    require(failure_class == FAILURE_CLASS, "UNKNOWN_FAILURE")
    require(type(workflow) is str and 0 < len(workflow) < 50000
            and "\r" not in workflow, "WORKFLOW_INVALID")
    matches = list(re.finditer(r"(?m)^\s*\$script = @'\n", workflow))
    require(len(matches) == 1, "SCRIPT_HEREDOC_AMBIGUOUS")
    match = matches[0]
    end = re.search(r"(?m)^          '@(?=\n)", workflow[match.end():])
    require(end is not None
            and workflow.find("$script = @'", match.end()) == -1,
            "SCRIPT_HEREDOC_MISSING_END")
    a, b = match.end(), match.end() + end.start()
    lines = workflow[a:b].splitlines(keepends=True)
    require(lines and all(line.startswith("          ") for line in lines),
            "SCRIPT_YAML_INDENTATION_DRIFT")
    script = "".join(line[10:] for line in lines)
    repaired, count = _repair_python(script)
    replacement = "".join(
        "          " + line for line in repaired.splitlines(keepends=True))
    candidate = workflow[:a] + replacement + workflow[b:]
    require(candidate[:a] == workflow[:a]
            and candidate[a + len(replacement):] == workflow[b:],
            "YAML_SCOPE_DRIFT")
    return candidate, count
