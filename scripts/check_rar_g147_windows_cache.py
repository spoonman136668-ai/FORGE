"""G147 experimental Windows Go compilation-cache identity; never caches test results."""
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
BASE = "ab2d239e2d079d2500ec5d91b253c11e6bd3b132"
BRANCH = "engineering/rar-g147-semantic-go-cache-firstpass-20261108"
DOC = b"docs/FORGE-G147-SEMANTIC-GO-CACHE.md"
EXPECTED = {
    DOC.decode(),
    ".github/workflows/qualify.yml",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g147_windows_cache.py",
}
SEED = "perf(g147): add source-correct Windows Go build-cache seed"
WARM = "docs(g147): execute preregistered warmed-cache cohort"
CAP = 2 * 1024 ** 3


def git(*args):
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, timeout=60
    ).strip()


def stable(sha):
    if git("rev-parse", "HEAD") != sha or git(
        "status", "--porcelain", "--untracked-files=all"
    ):
        raise ValueError("G147_SOURCE_DRIFT_OR_DIRTY")


def material():
    raw = subprocess.check_output(
        ["git", "ls-files", "--stage", "-z"], cwd=ROOT, timeout=60
    )
    parts = raw.split(b"\0")
    if parts[-1] or len(parts) < 1200:
        raise ValueError("G147_INDEX_INCOMPLETE")
    rows = []
    paths = set()
    exclusions = 0
    for row in parts[:-1]:
        if b"\t" not in row:
            raise ValueError("G147_INDEX_CORRUPT")
        meta, path = row.split(b"\t", 1)
        tokens = meta.split(b" ")
        if len(tokens) != 3 or len(tokens[1]) != 40 or tokens[2] != b"0" or path in paths:
            raise ValueError("G147_INDEX_UNSTAGED_OR_DUPLICATE")
        paths.add(path)
        if path == DOC:
            exclusions += 1
        else:
            rows.append(row)
    if exclusions != 1 or len(rows) < 1200:
        raise ValueError("G147_INDEX_DOC_EXCLUSION_INVALID")
    return hashlib.sha256(b"\0".join(rows) + b"\0").hexdigest(), len(rows)


def identity():
    sha = git("rev-parse", "HEAD")
    if not (
        sys.platform == "win32"
        and os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE"
        and os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
        and os.environ.get("GITHUB_HEAD_REF") == BRANCH
        and os.environ.get("RUNNER_OS") == "Windows"
        and os.environ.get("G147_HEAD") == sha
        and os.environ.get("GITHUB_BASE_REF") == "main"
        and os.environ.get("RUNNER_TEMP")
    ):
        raise ValueError("G147_ORIGINAL_WINDOWS_PR_ONLY")
    stable(sha)
    negative_controls()
    if admit_original_pr(sha, git) != "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT":
        raise ValueError("G147_FROZEN_ADMISSION_INVALID")
    diff = git("diff", "--no-renames", "--name-only", BASE, sha).splitlines()
    if len(diff) != 4 or set(diff) != EXPECTED:
        raise ValueError("G147_FOUR_FILE_SCOPE_CHANGED")
    if (os.environ.get("GOFLAGS") != "-p=2"
            or os.environ.get("GOMAXPROCS") != "2"
            or os.environ.get("GOMEMLIMIT") != "1536MiB"):
        raise ValueError("G147_GO_RESOURCE_DRIFT")
    subject = git("log", "-1", "--format=%s")
    if subject == SEED:
        phase = "seed"
    elif subject == WARM and git("log", "-1", "--format=%s", "HEAD^") == SEED and git(
        "diff", "--no-renames", "--name-only", "HEAD^", "HEAD"
    ) == DOC.decode():
        phase = "warm"
    else:
        raise ValueError("G147_UNEXPECTED_PHASE_OR_PARENT")
    source, count = material()
    envnames = ("GOOS", "GOARCH", "GOAMD64", "CGO_ENABLED", "GOEXPERIMENT",
                "GOTOOLCHAIN", "GOROOT", "GOTOOLDIR", "GOPATH", "GOWORK",
                "GOPROXY", "GOFLAGS", "GOCACHE")
    goenv = json.loads(subprocess.check_output(
        ["go", "env", "-json", *envnames], cwd=ROOT, text=True, timeout=50
    ))
    cache = Path(goenv.pop("GOCACHE")).resolve()
    if ROOT == cache or ROOT in cache.parents or not cache.is_absolute():
        raise ValueError("G147_CACHE_PATH_INVALID")
    version = subprocess.check_output(
        ["go", "version"], cwd=ROOT, text=True, timeout=40
    ).strip()
    fingerprint = {
        "source": source, "goenv": goenv, "go_version": version,
        "gomaxprocs": os.environ["GOMAXPROCS"],
        "gomemlimit": os.environ["GOMEMLIMIT"],
        "runner_os": os.environ["RUNNER_OS"],
        "runner_arch": os.environ.get("RUNNER_ARCH"),
        "image_os": os.environ.get("ImageOS"),
        "image_version": os.environ.get("ImageVersion"),
    }
    token = json.dumps(fingerprint, sort_keys=True, separators=(",", ":"))
    key = "rar-g147-windows-go-" + hashlib.sha256(token.encode()).hexdigest()
    return dict(schema="forge.rar-g147.windows-go-cache.v1",
                phase=phase, source_sha=sha, source_tree=git("rev-parse", "HEAD^{tree}"),
                cache_key=key, cache_path=str(cache),
                source_graph_digest=source, source_graph_files=count,
                fingerprint=fingerprint)


def main():
    p = argparse.ArgumentParser()
    opts = p.add_mutually_exclusive_group(required=True)
    opts.add_argument("--emit-env", action="store_true")
    opts.add_argument("--verify", action="store_true")
    args = p.parse_args()
    proof = identity()
    if args.emit_env:
        with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as out:
            out.write("G147_CACHE_KEY=" + proof["cache_key"] + "\n"
                      + "G147_GO_CACHE=" + proof["cache_path"] + "\n"
                      + "G147_PHASE=" + proof["phase"] + "\n")
        print("G147_SOURCE_KEY=" + proof["source_graph_digest"]
              + " phase=" + proof["phase"] + " key=" + proof["cache_key"], flush=True)
        return 0
    if (os.environ.get("G147_CACHE_KEY") != proof["cache_key"]
            or os.environ.get("G147_GO_CACHE") != proof["cache_path"]
            or os.environ.get("G147_PHASE") != proof["phase"]):
        raise ValueError("G147_CACHE_IDENTITY_CHANGED_BETWEEN_STEPS")
    hit = os.environ.get("G147_CACHE_HIT", "").lower() == "true"
    if (proof["phase"] == "seed" and hit) or (proof["phase"] == "warm" and not hit):
        raise ValueError("G147_FROZEN_COHORT_CACHE_STATE_INVALID")
    root = Path(proof["cache_path"])
    if not root.is_dir():
        raise ValueError("G147_CACHE_NOT_FOUND")
    size = 0
    n = 0
    for f in root.rglob("*"):
        if f.is_file():
            n += 1
            size += f.stat().st_size
            if size > CAP:
                raise ValueError("G147_CACHE_OVER_2GIB")
    if n == 0 or size == 0:
        raise ValueError("G147_EMPTY_GO_CACHE")
    stable(proof["source_sha"])
    proof.update(status="PASS", exact_cache_hit=hit, cache_bytes=size,
                 cache_files=n, full_go_result_cache_allowed=False,
                 original_go_test_flag="-count=1")
    path = Path(os.environ["RUNNER_TEMP"]) / "rar-g147-cache.json"
    path.write_text(json.dumps(proof, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")
    print("FORGE_RAR_G147=PASS phase=" + proof["phase"]
          + " hit=" + str(hit).lower() + " bytes=" + str(size), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
