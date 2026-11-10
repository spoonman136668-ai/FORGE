"""G148 main-safe Windows Go *compiler* cache, with unchanged original tests.

Every build input has an immutable tracked-Git blob in the semantic key.
No test result caching. No new runners, controllers, owner or authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from check_rar_g145_pr_scope import admit_original_pr, negative_controls

ROOT = Path(__file__).resolve().parents[1]
REPO = "spoonman136668-ai/FORGE"
BASE = "ab2d239e2d079d2500ec5d91b253c11e6bd3b132"
BRANCH = "engineering/rar-g148-main-safe-go-cache-20261108"
DOC = "docs/FORGE-G148-GO-CACHE-RELEASE.md"
PATHS = {
    DOC, ".github/workflows/qualify.yml",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
}
SEED = "perf(g148): enable main-safe Go compiler-cache CI"
WARM = "docs(g148): run preregistered warmed release candidate"
CAP = 2 * 1024**3
SUFFIXES = (b".go", b".c", b".h", b".s", b".S",
            b".syso", b".inc", b".proto", b".mod", b".sum")


def git(*a):
    return subprocess.check_output(
        ["git", *a], text=True, cwd=ROOT, timeout=80
    ).strip()


def stable(sha):
    if git("rev-parse", "HEAD") != sha:
        raise ValueError("G148_HEAD_SHA_CHANGED")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("G148_WORKTREE_DIRTY")


def compiled_graph() -> tuple[str, int]:
    raw = subprocess.check_output(
        ["git", "ls-files", "--stage", "-z"], cwd=ROOT, timeout=80
    )
    if not raw.endswith(b"\0"):
        raise ValueError("G148_MISSING_GIT_INDEX_TERMINATOR")
    all_rows = []
    paths = set()
    package_dirs = set()
    for row in raw[:-1].split(b"\0"):
        if b"\t" not in row:
            raise ValueError("G148_INVALID_INDEX_RECORD")
        meta, path = row.split(b"\t", 1)
        tokens = meta.split(b" ")
        if (len(tokens) != 3 or len(tokens[1]) != 40
                or tokens[2] != b"0" or path in paths):
            raise ValueError("G148_INVALID_OR_DUPLICATE_GIT_BLOB")
        paths.add(path)
        all_rows.append((row, path))
        if path.endswith(b".go"):
            package_dirs.add(path.rpartition(b"/")[0])
    if len(all_rows) < 1200 or len(package_dirs) < 130:
        raise ValueError("G148_UNEXPECTED_PACKAGE_SOURCE_INVENTORY")
    # Go embeds cannot cross package roots; include package descendants.
    # The root package is special (would swallow entire repository): include
    # all tracked root files, and fall back to the entire index if root embeds.
    root_embed = any(
        b"//go:embed" in (ROOT / p.decode("utf-8")).read_bytes()
        for _, p in all_rows if p.endswith(b".go") and b"/" not in p
    )
    selected = []
    for row, path in all_rows:
        folder = path.rpartition(b"/")[0]
        relevant = (
            root_embed
            or b"/" not in path
            or path.endswith(SUFFIXES)
            or any(path.startswith(d + b"/") for d in package_dirs if d)
        )
        if relevant:
            selected.append(row)
    if len(selected) < 470 or len(selected) > len(all_rows):
        raise ValueError("G148_SEMANTIC_INPUTS_INCOMPLETE")
    return hashlib.sha256(
        b"\0".join(selected) + b"\0"
    ).hexdigest(), len(selected)


def event_mode(head):
    if (
        sys.platform != "win32"
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != REPO
        or os.environ.get("RUNNER_OS") != "Windows"
        or os.environ.get("G148_HEAD") != head
        or not os.environ.get("RUNNER_TEMP")
    ):
        raise ValueError("G148_HOSTED_EXACT_WINDOWS_SOURCE_REQUIRED")
    stable(head)
    negative_controls()
    event = os.environ.get("GITHUB_EVENT_NAME")
    if event == "push":
        if (os.environ.get("GITHUB_REF") != "refs/heads/main"
                or os.environ.get("GITHUB_SHA") != head):
            raise ValueError("G148_ONLY_PROTECTED_MAIN_PUSH")
        return "main"
    if (event != "pull_request"
            or os.environ.get("GITHUB_BASE_REF") != "main"
            or not os.environ.get("GITHUB_HEAD_REF")):
        raise ValueError("G148_ONLY_SAME_REPO_MAIN_PR")
    admiss = admit_original_pr(head, git)
    branch = os.environ["GITHUB_HEAD_REF"]
    if branch == "engineering/rar-g167-f24-f11-canonical-validation-ab-20261109":
        if admiss != "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT":
            raise ValueError("G178_EXACT_SOURCE_SCOPE_REQUIRED")
        return "pr"
    if branch == 'engineering/f139-v40-explicit-owner-handoff-20261109':
        if admiss != "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT":
            raise ValueError("G148_V40_HANDOFF_FROZEN_SCOPE_REQUIRED")
        return "pr"
    if branch == 'engineering/f139-v40-source-bound-copy-qualification-20261109':
        if admiss != "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT":
            raise ValueError("G148_V40_COPY_FROZEN_SCOPE_REQUIRED")
        return "pr"
    if branch == 'engineering/f139-v40-qualified-readonly-route-20261109':
        if admiss != "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT":
            raise ValueError("G148_V40_READONLY_FROZEN_SCOPE_REQUIRED")
        return "pr"
    if branch == "engineering/f139-exact-worker-release-scope-20261109":
        if admiss != "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT":
            raise ValueError("G148_HYBRID_GOVERNANCE_FROZEN_SCOPE_REQUIRED")
        return "pr"
    if branch == "release/f139-hybrid-qualified-worker-governance-20261109":
        if admiss != "EXACT_PR1642_HYBRID_WORKER_BLOB_QUALIFICATION_ONLY":
            raise ValueError("G148_EXACT_HYBRID_WORKER_SCOPE_REQUIRED")
        return "pr"
    if branch == "engineering/rar-g156-dynamic-main-cache-release-20261108":
        if admiss != "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT":
            raise ValueError("G156_RELEASE_FROZEN_SCOPE_REQUIRED")
        return "pr"
    if branch == "engineering/rar-g158-optional-helper-compat-20261108":
        if admiss != "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT":
            raise ValueError("G158_FROZEN_HELPER_COMPAT_SCOPE_REQUIRED")
        return "pr"
    if branch == "engineering/rar-g160-partial-go-diagnostics-20261109":
        if admiss != "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT":
            raise ValueError("G160_FROZEN_DIAGNOSTIC_SCOPE_REQUIRED")
        return "pr"
    if branch == "engineering/rar-g161-verified-pr-ancestry-20261109":
        if admiss != "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT":
            raise ValueError("G161_FROZEN_ANCESTRY_SCOPE_REQUIRED")
        return "pr"
    if branch != BRANCH:
        if admiss != "EXACT_MAIN_ANCESTOR_GENERIC_SOURCE_PR":
            raise ValueError("G148_ONLY_ORDINARY_TRUSTED_SOURCE_PR")
        return "pr"
    if admiss != "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT":
        raise ValueError("G148_EXACT_FROZEN_DEV_SCOPE_REQUIRED")
    changes = git("diff", "--no-renames", "--name-only", BASE, head).splitlines()
    if len(changes) != 4 or set(changes) != PATHS:
        raise ValueError("G148_DEV_SCOPE_CHANGED")
    subject = git("log", "-1", "--format=%s")
    if subject == SEED:
        return "seed"
    if (subject == WARM
            and git("log", "-1", "--format=%s", "HEAD^") == SEED
            and git("diff", "--no-renames", "--name-only", "HEAD^", "HEAD") == DOC):
        return "warm"
    raise ValueError("G148_UNEXPECTED_COHORT_PROVENANCE")


def identity():
    head = git("rev-parse", "HEAD")
    mode = event_mode(head)
    if (os.environ.get("GOFLAGS") != "-p=2"
            or os.environ.get("GOMAXPROCS") != "2"
            or os.environ.get("GOMEMLIMIT") != "1536MiB"):
        raise ValueError("G148_ORIGINAL_GO_RESOURCE_FLAGS_DRIFT")
    digest, selected = compiled_graph()
    fields = ("GOOS", "GOARCH", "GOAMD64", "CGO_ENABLED", "GOEXPERIMENT",
              "GOTOOLCHAIN", "GOROOT", "GOTOOLDIR", "GOPATH", "GOWORK",
              "GOPROXY", "GOFLAGS", "GOCACHE")
    goenv = json.loads(subprocess.check_output(
        ["go", "env", "-json", *fields], text=True, cwd=ROOT, timeout=40
    ))
    cache = Path(goenv.pop("GOCACHE")).resolve()
    if not cache.is_absolute() or cache == ROOT or ROOT in cache.parents:
        raise ValueError("G148_BUILD_CACHE_MUST_BE_OUTSIDE_WORKTREE")
    version = subprocess.check_output(
        ["go", "version"], text=True, cwd=ROOT, timeout=40
    ).strip()
    fingerprint = dict(
        source_graph=digest, go_env=goenv, go_version=version,
        gomaxprocs=os.environ["GOMAXPROCS"],
        gomemlimit=os.environ["GOMEMLIMIT"],
        runner_os=os.environ.get("RUNNER_OS"),
        runner_arch=os.environ.get("RUNNER_ARCH"),
        image_os=os.environ.get("ImageOS"),
        image_version=os.environ.get("ImageVersion"),
    )
    key = "rar-g148-win-go-" + hashlib.sha256(json.dumps(
        fingerprint, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    return dict(
        schema="forge.rar-g148.main-safe-go-cache.v1",
        source_sha=head, source_tree=git("rev-parse", "HEAD^{tree}"),
        mode=mode, cache_key=key, cache_path=str(cache),
        source_graph_digest=digest, source_graph_files=selected,
        fingerprint=fingerprint,
    )


def main():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--emit-env", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = p.parse_args()
    data = identity()
    if args.emit_env:
        target = os.environ.get("GITHUB_ENV")
        if not target:
            raise ValueError("G148_GITHUB_ENV_MISSING")
        with Path(target).open("a", encoding="utf-8") as out:
            out.write("G148_CACHE_KEY=" + data["cache_key"] + "\n"
                      + "G148_CACHE_PATH=" + data["cache_path"] + "\n"
                      + "G148_MODE=" + data["mode"] + "\n")
        print("G148_COMPILE_SOURCE=" + data["source_graph_digest"]
              + " key=" + data["cache_key"] + " mode=" + data["mode"],
              flush=True)
        return 0
    if (os.environ.get("G148_CACHE_KEY") != data["cache_key"]
            or os.environ.get("G148_CACHE_PATH") != data["cache_path"]
            or os.environ.get("G148_MODE") != data["mode"]):
        raise ValueError("G148_BETWEEN_STEPS_KEY_DRIFT")
    hit = os.environ.get("G148_CACHE_HIT", "").lower() == "true"
    if (data["mode"] == "seed" and hit) or (data["mode"] == "warm" and not hit):
        raise ValueError("G148_PREREGISTERED_COHORT_HIT_MISMATCH")
    root = Path(data["cache_path"])
    if not root.is_dir():
        raise ValueError("G148_BUILD_CACHE_NOT_FOUND")
    size = 0
    files = 0
    for child in root.rglob("*"):
        if child.is_file():
            size += child.stat().st_size
            files += 1
            if size > CAP:
                raise ValueError("G148_BUILD_CACHE_EXCEEDS_2GIB")
    if files == 0 or size == 0:
        raise ValueError("G148_EMPTY_COMPILED_CACHE")
    stable(data["source_sha"])
    data.update(status="PASS", cache_hit=hit, cache_bytes=size,
                cache_file_count=files,
                original_go_test_results_always_run=True,
                original_go_test_command="go test -count=1 ./...")
    receipt = Path(os.environ["RUNNER_TEMP"]) / "rar-g148-cache.json"
    receipt.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("FORGE_RAR_G148=PASS mode=" + data["mode"]
          + " hit=" + str(hit).lower() + " bytes=" + str(size), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
