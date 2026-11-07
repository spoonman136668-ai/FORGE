"""Materialize reviewed RSI-R3 G1/G2 source into separate local Git clones.

Development only. No owner runner, protected Git ref, science first use, CI
promotion, arbitrary text execution, or autonomous RSI benefit is inferred.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys

from f139.rsi_r3_source_cycle import (
    Generation, R3Denied, TARGET, fingerprint, verify,
)

SCHEMA = "forge.f139.rsi-r3.disposable-source-tree.v1"
MARKER = b"\n\n# FORGE_RSI_R3_STAGED_SELECTOR_BEGIN\n"
END = b"# FORGE_RSI_R3_STAGED_SELECTOR_END\n"


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise R3Denied("FORGE_RSI_R3_STAGE_" + reason)


def git(repo: Path, *args: str) -> str:
    # Fixed argv; no shell, network remote, user-provided command, or hooks.
    result = subprocess.run(["git", "-C", str(repo), *args],
                            capture_output=True, text=True, timeout=40, check=False)
    need(result.returncode == 0, "GIT_COMMAND_FAILED")
    return result.stdout.strip()


@dataclass(frozen=True)
class Staged:
    schema: str
    generation: int
    origin_head: str
    parent_head: str
    staged_head: str
    parent_source_sha256: str
    generated_source_sha256: str
    target_sha256: str
    relative_path: str


def staged_source(original: bytes, generation: Generation) -> bytes:
    """Replace only the fixed generated block in FORGE's maintained module."""
    need(type(original) is bytes and type(generation) is Generation,
         "SOURCE_INPUT_INVALID")
    prior = original.split(MARKER)
    need(len(prior) <= 2, "MULTIPLE_GENERATED_BLOCKS")
    if len(prior) == 2:
        need(prior[1].endswith(END), "UNTRUSTED_GENERATED_TRAILER")
    base = prior[0]
    need(b"def rehearsal(" in base and b"MAX_GENERATIONS = 2" in base,
         "FORGE_TARGET_SHAPE_DRIFT")
    block = (MARKER + generation.source + END)
    output = base + block
    compile(output, TARGET, "exec")
    need(fingerprint(generation.source) == generation.source_sha256,
         "GENERATED_SHA_DRIFT")
    return output


def _safe_source(repo: Path, scratch: Path, expected_head: str,
                 expected_target_sha256: str) -> None:
    need(repo.is_dir() and scratch.is_dir() and
         not repo.is_symlink() and not scratch.is_symlink(), "ROOT_INVALID")
    repo, scratch = repo.resolve(strict=True), scratch.resolve(strict=True)
    need(repo != scratch and repo not in scratch.parents
         and scratch not in repo.parents, "STAGING_ROOT_NOT_DISJOINT")
    need(len(expected_head) == 40 and all(c in "0123456789abcdef" for c in expected_head),
         "EXPECTED_HEAD_INVALID")
    need(len(expected_target_sha256) == 64 and
         all(c in "0123456789abcdef" for c in expected_target_sha256),
         "EXPECTED_TARGET_INVALID")
    # Git for Windows returns forward slashes (D:/...) while Path.__str__
    # uses backslashes. Compare resolved paths, not spelling or separators.
    need(Path(git(repo, "rev-parse", "--show-toplevel")).resolve(strict=True)
         == repo, "NOT_GIT_ROOT")
    need(git(repo, "rev-parse", "HEAD") == expected_head, "SOURCE_HEAD_DRIFT")
    need(not git(repo, "status", "--porcelain", "--untracked-files=all"),
         "SOURCE_DIRTY")
    target = repo / TARGET
    need(target.is_file() and not target.is_symlink(), "TARGET_NOT_REGULAR")
    need(fingerprint(target.read_bytes()) == expected_target_sha256,
         "TARGET_PREIMAGE_DRIFT")


def stage_generations(repo: Path, scratch: Path,
                      generations: tuple[Generation, ...], *,
                      expected_head: str, expected_target_sha256: str) -> tuple[Staged, ...]:
    """Clone baseline to G1 and G1 to G2, committing only inside scratch.

    The staged source files are actual tracked FORGE module changes with
    independently verifiable Git commits, but never protected-repo commits.
    No qualification is implied; focused/full regression is a separate gate.
    """
    repo, scratch = Path(repo), Path(scratch)
    need(verify(generations), "SOURCE_LINEAGE_INVALID")
    _safe_source(repo, scratch, expected_head, expected_target_sha256)
    origin, parent, parent_head = expected_head, repo, expected_head
    receipts: list[Staged] = []
    for g in generations:
        child = scratch / ("rsi-r3-g%d" % g.generation)
        need(not child.exists() and not child.is_symlink(), "CHILD_ALREADY_EXISTS")
        subprocess_result = subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", "--", str(parent), str(child)],
            capture_output=True, text=True, timeout=90, check=False)
        need(subprocess_result.returncode == 0, "LOCAL_CLONE_FAILED")
        need(git(child, "rev-parse", "HEAD") == parent_head,
             "STAGED_PARENT_HEAD_DRIFT")
        if git(child, "remote"):
            git(child, "remote", "remove", "origin")
        target = child / TARGET
        before = target.read_bytes()
        after = staged_source(before, g)
        need(before != after, "UNCHANGED_FORGE_MODULE")
        target.write_bytes(after)
        git(child, "diff", "--check")
        git(child, "add", "--", TARGET)
        # Fixed local development authorship. No remote write or push.
        git(child, "-c", "user.name=FORGE-RSI-R3-DEV",
            "-c", "user.email=forge-rsi-r3-dev@invalid.local",
            "-c", "core.hooksPath=/dev/null",
            "commit", "-q", "-m", "dev: materialize source generation %d" % g.generation,
            "--", TARGET)
        current = git(child, "rev-parse", "HEAD")
        need(git(child, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD")
             == TARGET, "UNEXPECTED_STAGED_PATHS")
        need(git(child, "status", "--porcelain", "--untracked-files=all") == "",
             "STAGED_TREE_DIRTY")
        need(target.read_bytes() == after, "STAGED_BYTES_DRIFT")
        receipts.append(Staged(SCHEMA, g.generation, origin, parent_head,
                               current, g.parent_sha256, g.source_sha256,
                               fingerprint(after), TARGET))
        parent, parent_head = child, current
    need(git(repo, "rev-parse", "HEAD") == origin and
         git(repo, "status", "--porcelain", "--untracked-files=all") == "",
         "ORIGINAL_REPO_CHANGED")
    return tuple(receipts)
