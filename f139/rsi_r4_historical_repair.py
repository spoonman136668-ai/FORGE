"""Read-only, original-Git-blob custody for authentic FORGE repair history.

This development inventory cannot execute repair code, select scientific first
use, dispatch work, accept a fix, mutate original owner, or prove RSI. The
frozen reference AFTER blobs are public historical outcomes, never blind tests.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Callable

SCHEMA = "forge.f139.rsi-r4.historical-repair-replay.v1"
PREREG_PATH = "docs/FORGE-RSI-R4-AUTHENTIC-REPAIR-PREREG.md"
PREREG_BLOB = "8c5400b0f738ebaff423d7bbf5b7976b5ac4d202"
ORIGIN = "cf727267007d0637abd8d8cd98a0fbbbd37f2752"
MAX_BYTES = 400_000
COHORTS = frozenset({"train", "validation", "historic_holdout", "format_negative"})
SHA40 = re.compile(r"[0-9a-f]{40}\Z")


class ReplayDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise ReplayDenied("RSI_R4_REPLAY_" + reason)


def git_blob(raw: bytes) -> str:
    need(type(raw) is bytes, "SOURCE_BYTES_REQUIRED")
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class Task:
    pr: int
    cohort: str
    path: str
    before_commit: str
    after_commit: str
    before_blob: str
    after_blob: str


# Every identity is copied from the earlier separately committed preregistration
# and checked against actual GitHub before/after file blobs, not from a model.
TASKS = (
    Task(1434, "train", "f139/nci04_prompt_program.py",
         "259cd6f2e26a655ec1c2d6150482e85806c70b00",
         "27c5fcdb0a53e1ea96a2e53c419a1a18fa688e1c",
         "253a2c4ec692f6d6d7ce7d60bd453795a3a502b7",
         "9773d30a66338014420550edfd7cb1ba4c2b9cca"),
    Task(1508, "train", "f139/nci04_prompt_program.py",
         "860825eda4790f89f9b54c9100216af1322fc557",
         "c4ea247de49b655675f89166d783fb816943047c",
         "8781f3226ce3fed9e80f0c68bc845fe0639a2d2f",
         "643214ee8a581a4268bbd5bc8563d82e40c1ce9c"),
    Task(1517, "validation", "f139/nci04_v32_original_owner_transition_cli.py",
         "6988f1ebfe53fe54b13c5decbd58246b74ac2ad7",
         "3d8478427b9182c49b6931fa69043753ed7b2d5a",
         "dc597064fa83c1b996b2541c92c51ae342aa705d",
         "569ad130d0421df95f270ee7575985bff39a623d"),
    Task(1525, "historic_holdout", "nativefirstuse/f74_live_native_intake.py",
         "ceb5f69097848992fa476d43054dea9120bd3696",
         "61086e05e38b43c48cea6eb82826659c6afe48a4",
         "d58ce0ee847acf2e40d3ba509a37887e43007622",
         "f3ccf502ef1f7a4a87972485a780e3e9d225d658"),
    Task(1334, "historic_holdout", "f139/local_controller.py",
         "80ae30719bcd9f179da4aa4e8f14dc36fd15818e",
         "cf4ab24e3f95f37e2e79860edd1c99ee00290bf3",
         "bbaacc407fa4590e111fa19a395c62b2ddeccc86",
         "90fa3b593b3ff7b6c9110118ba06d865d902a42a"),
    Task(1543, "format_negative", "nativediscovery/f2_world.go",
         "9527029d93aef61fc54f09c054fde9cd98f4f043",
         "fdf584ca1a83d50505062a118c6bdd67bd5504e6",
         "7aea7bbf2896c4ecbdf3b027dcf3f1f78b3b992b",
         "2d3cc4bfb673e032ae6d7b40df77f0e7bf067b22"),
)


def validate_catalog(tasks: tuple[Task, ...] = TASKS) -> bool:
    need(type(tasks) is tuple and len(tasks) == 6 and
         all(type(t) is Task for t in tasks), "CATALOG_TYPE_OR_COUNT")
    need(tuple(t.pr for t in tasks) == (1434, 1508, 1517, 1525, 1334, 1543),
         "FROZEN_TASK_IDENTITIES")
    need(tasks == TASKS, "FROZEN_CATALOG_DRIFT")
    families: dict[str, set[str]] = {}
    for t in tasks:
        need(t.cohort in COHORTS and
             (t.path.startswith("f139/") or t.path.startswith("nativefirstuse/")
              or t.path.startswith("nativediscovery/")) and
             ".." not in t.path and t.path.endswith((".py", ".go")),
             "COHORT_OR_PATH")
        need(all(SHA40.fullmatch(s) for s in (
            t.before_commit, t.after_commit, t.before_blob, t.after_blob)),
            "SHA_IDENTITY_INVALID")
        need(t.before_commit != t.after_commit and t.before_blob != t.after_blob,
             "HISTORICAL_EDIT_IDENTICAL")
        families.setdefault(t.path, set()).add(t.cohort)
    need(all(len(group) == 1 for group in families.values()),
         "SOURCE_FAMILY_SPLIT_LEAK")
    return True


def check_prereg_bytes(raw: bytes) -> bool:
    need(type(raw) is bytes and git_blob(raw) == PREREG_BLOB,
         "PREREG_NOT_ORIGINAL")
    return True


def _checked_source(raw: bytes, expected_blob: str, path: str) -> bytes:
    need(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES,
         "SOURCE_TYPE_OR_SIZE")
    need(git_blob(raw) == expected_blob, "SOURCE_GIT_BLOB_DRIFT")
    if path.endswith(".py"):
        try:
            ast.parse(raw.decode("utf-8", "strict"), filename=path)
        except (UnicodeError, SyntaxError, ValueError) as exc:
            raise ReplayDenied("RSI_R4_REPLAY_SOURCE_PYTHON_INVALID") from exc
    return raw


@dataclass(frozen=True)
class ReadOnlyReceipt:
    schema: str
    pr: int
    cohort: str
    before_sha256: str
    after_sha256: str
    source_pair_sha256: str
    reference_only: bool = True
    first_use_authorized: bool = False
    repair_success: bool = False
    independent_qualification: bool = False
    owner_execution: bool = False
    rsi_proven: bool = False


def inspect_original_pair(
    task: Task, source_get: Callable[[str, str], bytes],
) -> ReadOnlyReceipt:
    """Authenticate a public historic repair pair from an injected read-only get.

    No network, workspace reads, subprocess, checkout or writes in this module.
    The reference AFTER source is disclosed only for retrospective audit; it
    must not be used as a hidden holdout oracle or to train a claimant.
    """
    validate_catalog()
    need(type(task) is Task and task in TASKS, "UNDECLARED_REPAIR_TASK")
    need(callable(source_get), "READ_ONLY_SOURCE_GET_REQUIRED")
    before = _checked_source(
        source_get(task.before_commit, task.path), task.before_blob, task.path)
    after = _checked_source(
        source_get(task.after_commit, task.path), task.after_blob, task.path)
    need(before != after, "NO_HISTORICAL_SOURCE_CHANGE")
    payload = json.dumps(
        {"schema": SCHEMA, "pr": task.pr, "cohort": task.cohort,
         "path": task.path, "before_commit": task.before_commit,
         "after_commit": task.after_commit,
         "before_blob": task.before_blob, "after_blob": task.after_blob,
         "before_sha256": sha256(before), "after_sha256": sha256(after)},
        sort_keys=True, separators=(",", ":")).encode("utf-8")
    return ReadOnlyReceipt(SCHEMA, task.pr, task.cohort, sha256(before),
                           sha256(after), sha256(payload))


def candidate_source_identity(task: Task, original: bytes,
                              generated: bytes) -> str:
    """Syntactic provenance ONLY, never 'repair works' or actual solution score."""
    validate_catalog()
    need(type(task) is Task and task in TASKS, "UNDECLARED_REPAIR_TASK")
    need(task.cohort != "format_negative", "FORMAT_CHANGE_NOT_LEARNING")
    _checked_source(original, task.before_blob, task.path)
    need(type(generated) is bytes and 0 < len(generated) <= MAX_BYTES,
         "GENERATED_SOURCE_TYPE_OR_SIZE")
    need(generated != original, "UNCHANGED_GENERATED_SOURCE")
    if task.path.endswith(".py"):
        try:
            old = ast.parse(original.decode("utf-8", "strict"))
            new = ast.parse(generated.decode("utf-8", "strict"))
        except (SyntaxError, UnicodeError, ValueError) as exc:
            raise ReplayDenied("RSI_R4_REPLAY_GENERATED_PYTHON_INVALID") from exc
        need(ast.dump(old, include_attributes=False) !=
             ast.dump(new, include_attributes=False), "NONSEMANTIC_PYTHON_EDIT")
    return sha256(generated)
