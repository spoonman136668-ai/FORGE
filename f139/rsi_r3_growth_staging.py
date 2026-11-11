"""Stage pinned RSI-R3 grammar growth through real disposable Git G1/G2 trees.

Development ONLY. No original-owner, remote Git, network, model, science
first-use, runner or deployment. The revised generator source is preauthored
and already reviewed; this does not demonstrate autonomous RSI benefit.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from f139.rsi_r3_disposable_tree import END, MARKER, git
from f139.rsi_r3_source_grammar_growth import (
    Growth, ORIGINAL_BLOB, TARGET, digest, git_blob,
    verify as verify_growth,
)

SCHEMA = "forge.f139.rsi-r3.growth-disposable-two-generation.v1"
G1_FEEDBACK = ((2, (12, 2, 8, 3)), (3, (12, 3, 4, 9)))
G2_FEEDBACK = ((3, (12, 5, 5, 4)), (4, (12, 3, 9, 9)))


class GrowthStagingDenied(ValueError):
    pass


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise GrowthStagingDenied("FORGE_RSI_R3_GROWTH_STAGE_" + reason)


def git_bytes(repo: Path, *args: str) -> bytes:
    """Read original Git bytes without text decoding or trailing-newline loss."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, timeout=40, check=False)
    need(result.returncode == 0, "GIT_ORIGINAL_BLOB_READ_FAILED")
    return result.stdout


def source_parts(source: bytes) -> tuple[bytes, bytes]:
    need(type(source) is bytes and len(source) <= 32768,
         "STAGED_SOURCE_BYTES_INVALID")
    parts = source.split(MARKER)
    need(len(parts) == 2 and parts[1].endswith(END),
         "STAGED_MARKER_OR_TRAILER_INVALID")
    core, selector = parts[0], parts[1][:-len(END)]
    need(core and 0 < len(selector) < 2048,
         "STAGED_SOURCE_EMPTY_OR_OVERSIZED")
    return core, selector


def render(core: bytes, selector: bytes) -> bytes:
    need(type(core) is bytes and type(selector) is bytes
         and 0 < len(core) < 32768
         and 0 < len(selector) < 2048
         and MARKER not in core and END not in core
         and MARKER not in selector and END not in selector,
         "GENERATED_SOURCE_BOUNDARY_INVALID")
    result = core + MARKER + selector + END
    need(len(result) <= 32768, "STAGED_SOURCE_LIMIT")
    compile(result, TARGET, "exec")
    return result


def _authentic_root(repo: Path, scratch: Path, expected_head: str) -> bytes:
    need(repo.is_dir() and scratch.is_dir()
         and not repo.is_symlink() and not scratch.is_symlink(),
         "ROOT_INVALID")
    repo, scratch = repo.resolve(strict=True), scratch.resolve(strict=True)
    need(repo != scratch and repo not in scratch.parents
         and scratch not in repo.parents
         and not any(scratch.iterdir()), "SCRATCH_NOT_EMPTY_OR_DISJOINT")
    need(type(expected_head) is str and len(expected_head) == 40 and
         all(c in "0123456789abcdef" for c in expected_head),
         "EXPECTED_HEAD_INVALID")
    need(Path(git(repo, "rev-parse", "--show-toplevel")).resolve(strict=True)
         == repo and git(repo, "rev-parse", "HEAD") == expected_head
         and git(repo, "status", "--porcelain", "--untracked-files=all") == "",
         "ORIGINAL_HEAD_OR_CLEANLINESS_DRIFT")
    target = repo / TARGET
    need(target.is_file() and not target.is_symlink(),
         "ORIGINAL_TARGET_NOT_REGULAR")
    original = git_bytes(repo, "show", "HEAD:" + TARGET)
    need(git_blob(original) == ORIGINAL_BLOB,
         "ORIGINAL_PINNED_GIT_BLOB_DRIFT")
    worktree = target.read_bytes()
    need(worktree in (original, original.replace(b"\n", b"\r\n")),
         "ORIGINAL_CHECKOUT_BYTES_DRIFT")
    return original


def _reviewed_program(growth: Growth, original: bytes) -> dict:
    need(type(growth) is Growth, "GROWTH_RECORD_TYPE_INVALID")
    try:
        need(verify_growth(growth, original, frozenset()),
             "GROWTH_RECORD_NOT_REPLAYABLE")
    except ValueError as exc:
        raise GrowthStagingDenied(
            "FORGE_RSI_R3_GROWTH_STAGE_GROWTH_RECORD_INVALID") from exc
    # Execute only the exact, authenticated AST-local revised FORGE source.
    # This is an ordinary test process, not a sandbox for arbitrary code.
    env = {"__name__": "forge_rsi_r3_disposable_dev"}
    exec(compile(growth.source, TARGET, "exec"), env)
    return env


def _clone_commit(parent: Path, scratch: Path, label: str, expected_parent: str,
                  source: bytes) -> tuple[str, Path]:
    need(label in ("rsi-r3-growth-g1", "rsi-r3-growth-g2"),
         "CLONE_LABEL_INVALID")
    child = scratch / label
    need(not child.exists() and not child.is_symlink(),
         "CHILD_EXISTS_OR_SYMLINK")
    result = subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", "--",
         str(parent), str(child)],
        capture_output=True, timeout=90, check=False)
    need(result.returncode == 0, "LOCAL_CLONE_FAILED")
    need(git(child, "rev-parse", "HEAD") == expected_parent,
         "CLONE_PARENT_HEAD_DRIFT")
    if git(child, "remote"):
        git(child, "remote", "remove", "origin")
    need(git(child, "remote") == "",
         "CLONE_REMOTE_NOT_REMOVED")
    target = child / TARGET
    need(target.is_file() and not target.is_symlink()
         and git(child, "status", "--porcelain", "--untracked-files=all") == "",
         "CLONE_WORKTREE_UNTRUSTED")
    target.write_bytes(source)
    git(child, "diff", "--check")
    git(child, "add", "--", TARGET)
    git(child, "-c", "user.name=FORGE-RSI-R3-DEV",
        "-c", "user.email=forge-rsi-r3-dev@invalid.local",
        "-c", "core.hooksPath=/dev/null",
        "commit", "-q", "-m", "dev: stage reviewed RSI-R3 growth " + label,
        "--", TARGET)
    head = git(child, "rev-parse", "HEAD")
    need(git(child, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD")
         == TARGET and git(child, "remote") == ""
         and git(child, "status", "--porcelain", "--untracked-files=all") == "",
         "STAGED_COMMIT_PATH_OR_DIRTY")
    need(git_bytes(child, "show", "HEAD:" + TARGET) == source,
         "STAGED_COMMITTED_BYTES_DRIFT")
    return head, child


@dataclass(frozen=True)
class GrowthStage:
    generation: int
    origin_head: str
    parent_head: str
    staged_head: str
    module_sha256: str
    selector_sha256: str
    generator_sha256: str
    path: str = TARGET
    schema: str = SCHEMA
    original_owner_admitted: bool = False
    scientific_first_use: bool = False
    deployment_authorized: bool = False
    autonomous_rsi_proven: bool = False


def stage_growth(repo: Path, scratch: Path, *,
                 expected_head: str, growth: Growth) -> tuple[GrowthStage, GrowthStage]:
    """Stage source-checked G1, then re-execute ACTUAL G1 bytes to stage G2.

    Historical synthetic feedback only. No external tests or science implied.
    A failure leaves scratch for examination; never perform uncertain retries.
    """
    repo, scratch = Path(repo), Path(scratch)
    original = _authentic_root(repo, scratch, expected_head)
    env = _reviewed_program(growth, original)
    first = env["generate"](
        parent_source=env["source_for"](0), generation=1,
        feedback=G1_FEEDBACK, used_operators=frozenset({0}))
    need(first.operator == 2 and
         first.source == env["source_for"](2), "G1_FROZEN_RESULT_DRIFT")
    source_g1 = render(growth.source, first.source)
    g1_head, g1_root = _clone_commit(
        repo, scratch, "rsi-r3-growth-g1", expected_head, source_g1)
    committed_g1 = git_bytes(g1_root, "show", "HEAD:" + TARGET)
    need(committed_g1 == source_g1 and
         git(g1_root, "rev-parse", "HEAD") == g1_head and
         git(g1_root, "status", "--porcelain", "--untracked-files=all") == "",
         "COMMITTED_G1_CHANGED")
    core, parent_selector = source_parts(committed_g1)
    need(core == growth.source and parent_selector == first.source,
         "PARENT_G1_CORE_OR_SELECTOR_DRIFT")
    # G2 is generated using the authenticated G1 checkout selector, never
    # using the original four-program selector or an uncommitted substitute.
    second = env["generate"](
        parent_source=parent_selector, generation=2,
        feedback=G2_FEEDBACK, used_operators=frozenset({0, first.operator}))
    need(second.operator == 4
         and second.parent_sha256 == first.source_sha256
         and second.source == env["source_for"](4)
         and env["verify"]((first, second)),
         "G2_FEEDBACK_OR_LINEAGE_DRIFT")
    source_g2 = render(growth.source, second.source)
    need(source_g2 != source_g1, "G2_IDENTICAL_SOURCE")
    g2_head, g2_root = _clone_commit(
        g1_root, scratch, "rsi-r3-growth-g2", g1_head, source_g2)
    need(git_bytes(g2_root, "show", "HEAD:" + TARGET) == source_g2,
         "COMMITTED_G2_SOURCE_DRIFT")
    need(git(repo, "rev-parse", "HEAD") == expected_head and
         git(repo, "status", "--porcelain", "--untracked-files=all") == "",
         "ORIGINAL_REPO_CHANGED")
    gen = digest(growth.source)
    return (
        GrowthStage(1, expected_head, expected_head, g1_head,
                    digest(source_g1), digest(first.source), gen),
        GrowthStage(2, expected_head, g1_head, g2_head,
                    digest(source_g2), digest(second.source), gen),
    )
