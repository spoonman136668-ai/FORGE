"""Inactive FORGE RSI-R3 source-grammar growth experiment, no owner authority.

Exactly one reviewed edit to the pinned original R3 proposer code. This is
human-authored DEV infrastructure, not autonomous self-improvement or science.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from hashlib import sha1, sha256
import re

SCHEMA = "forge.f139.rsi-r3.grammar-growth-development.v1"
TARGET = "f139/rsi_r3_source_cycle.py"
ORIGINAL_BLOB = "a643c4320654223820ca2666300767465e0cdc3c"
MAX_BYTES = 32768
RANK = '    "row[0] + row[3] - row[1]",       # Distinct correct solutions\n)\n'
GROWN = ('    "row[0] + row[3] - row[1]",       # Distinct correct solutions\n'
         '    "row[0] + min(row[2], row[3]) - row[1]",  # Balanced criteria\n)\n')
BUILTIN = '    env = {"__builtins__": {"max": max}}\n'
GROWN_BUILTIN = '    env = {"__builtins__": {"max": max, "min": min}}\n'
SHA64 = re.compile(r"[0-9a-f]{64}\Z")


class GrammarGrowthDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise GrammarGrowthDenied("FORGE_RSI_R3_GRAMMAR_" + reason)


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def git_blob(value: bytes) -> str:
    return sha1(b"blob " + str(len(value)).encode("ascii") + b"\0" + value).hexdigest()


def rewrite(before: bytes) -> bytes:
    need(type(before) is bytes and 0 < len(before) <= MAX_BYTES
         and git_blob(before) == ORIGINAL_BLOB, "PINNED_SOURCE_DRIFT")
    try:
        text = before.decode("utf-8", "strict")
        need(text.count(RANK) == 1 and text.count(BUILTIN) == 1 and
             "\r" not in text, "SOURCE_ANCHOR_DRIFT")
        after = text.replace(RANK, GROWN, 1).replace(
            BUILTIN, GROWN_BUILTIN, 1)
        raw = after.encode("utf-8")
        need(raw != before and len(raw) <= MAX_BYTES, "SOURCE_BOUNDS")
        original_tree = ast.parse(text, filename=TARGET)
        candidate_tree = ast.parse(after, filename=TARGET)
        need(len(original_tree.body) == len(candidate_tree.body),
             "MODULE_STRUCTURE_CHANGED")
        changes = []
        for old, new in zip(original_tree.body, candidate_tree.body):
            if ast.dump(old, include_attributes=False) == ast.dump(
                    new, include_attributes=False):
                continue
            if (isinstance(old, ast.Assign) and
                    isinstance(new, ast.Assign) and
                    len(old.targets) == len(new.targets) == 1 and
                    isinstance(old.targets[0], ast.Name) and
                    isinstance(new.targets[0], ast.Name) and
                    old.targets[0].id == new.targets[0].id == "RANK_EXPRESSIONS"):
                changes.append("RANK_EXPRESSIONS")
            elif (isinstance(old, ast.FunctionDef) and
                  isinstance(new, ast.FunctionDef) and
                  old.name == new.name == "_run_verified_parent"):
                changes.append("_run_verified_parent")
            else:
                need(False, "UNRELATED_AST_DRIFT")
        need(changes == ["RANK_EXPRESSIONS", "_run_verified_parent"],
             "REQUIRED_AST_EDITS_MISSING")
        compile(after, TARGET, "exec")
    except (SyntaxError, UnicodeError, ValueError) as exc:
        if isinstance(exc, GrammarGrowthDenied):
            raise
        raise GrammarGrowthDenied("FORGE_RSI_R3_GRAMMAR_SOURCE_INVALID") from exc
    return raw


@dataclass(frozen=True)
class Growth:
    schema: str
    path: str
    original_blob: str
    before_sha256: str
    after_sha256: str
    source: bytes
    original_owner_admitted: bool = False
    autonomous_rsi_proven: bool = False
    scientific_first_use: bool = False
    worker_dispatched: bool = False
    deployed: bool = False


def propose(*, original: bytes, consumed: frozenset[str]) -> Growth:
    need(type(consumed) is frozenset and len(consumed) <= 64 and
         all(type(key) is str and SHA64.fullmatch(key) is not None
             for key in consumed), "CONSUMED_INPUT_UNTRUSTED")
    after = rewrite(original)
    need(digest(after) not in consumed, "SOURCE_ALREADY_CONSUMED")
    return Growth(SCHEMA, TARGET, ORIGINAL_BLOB, digest(original),
                  digest(after), after)


def verify(record: Growth, original: bytes, consumed: frozenset[str]) -> bool:
    need(type(record) is Growth and
         record == propose(original=original, consumed=consumed),
         "SOURCE_OR_RECEIPT_DRIFT")
    return True
