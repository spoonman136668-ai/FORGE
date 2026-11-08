"""One-shot DEV-only exact-main Go compiler seed; no tests or owner skipped."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

from check_rar_g145_pr_scope import admit_original_pr, github_event_base, negative_controls
from check_rar_g148_go_cache import CAP, ROOT, git, identity, stable

BRANCH = "engineering/rar-g151-exact-main-cache-seed-dev-20261108"
BASE = "1363cadc0f20155798ef52d72f85ac6df8a81ed6"
BASE_TREE = "61d683215b4c7be8e9a4db921f04a15354279152"
BASE_GRAPH = "39c27c4f51e81fb12d3b5dc573a99793d80c1b692943d7fbb9ed9cd7501cad47"
BASE_KEY = "rar-g148-win-go-db3730bf1158ebde65edf14ced6077aaf11ff6b3267f56377207d0432a3b3d2e"
FILES = {
    "docs/FORGE-G151-EXACT-MAIN-COMPILER-SEED-DEV.md",
    ".github/workflows/qualify.yml",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g151_base_cache_dev.py",
    "nativediscovery/g151_compiler_cache_dev_test.go",
}
FROZEN = "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT"


def provenance() -> dict:
    head = git("rev-parse", "HEAD")
    stable(head)
    negative_controls()
    if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_OS") != "Windows"
            or os.environ.get("GITHUB_EVENT_NAME") != "pull_request"
            or os.environ.get("GITHUB_HEAD_REF") != BRANCH
            or os.environ.get("G151_HEAD") != head
            or github_event_base(head) != BASE
            or git("merge-base", BASE, head) != BASE
            or git("rev-parse", BASE + "^{tree}") != BASE_TREE
            or admit_original_pr(head, git) != FROZEN):
        raise ValueError("G151_FROZEN_HEAD_BASE_EVENT_OR_SCOPE_MISMATCH")
    changed = git("diff", "--no-renames", "--name-only", BASE, head).splitlines()
    if len(changed) != len(FILES) or set(changed) != FILES:
        raise ValueError("G151_EXACT_SIX_PATH_SCOPE_FAILED")
    data = identity()
    if (data["mode"] != "pr"
            or data["source_graph_digest"] == BASE_GRAPH
            or data["cache_key"] == BASE_KEY
            or os.environ.get("G148_CACHE_KEY") != data["cache_key"]
            or os.environ.get("G148_CACHE_PATH") != data["cache_path"]
            or os.environ.get("G148_MODE") != "pr"
            or os.environ.get("G148_CACHE_HIT", "").lower() not in ("", "false")):
        raise ValueError("G151_CHANGED_GRAPH_OR_MISS_IDENTITY_FAILED")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--pre", action="store_true")
    g.add_argument("--post", action="store_true")
    args = parser.parse_args()
    data = provenance()
    if args.pre:
        print("FORGE_RAR_G151=PASS_FROZEN_PRECHECK current_key="
              + data["cache_key"] + " main_key=" + BASE_KEY, flush=True)
        return 0
    if os.environ.get("G151_BASE_HIT") != "true":
        raise ValueError("G151_EXACT_TRUSTED_MAIN_CACHE_NOT_RESTORED")
    folder = Path(data["cache_path"])
    if not folder.is_dir() or ROOT in folder.parents or folder == ROOT:
        raise ValueError("G151_BASE_COMPILER_CACHE_PATH_UNTRUSTED")
    size = 0
    count = 0
    for entry in folder.rglob("*"):
        if entry.is_file():
            count += 1
            size += entry.stat().st_size
            if size > CAP:
                raise ValueError("G151_RESTORED_BASE_CACHE_EXCEEDS_2GIB")
    if count == 0 or size == 0:
        raise ValueError("G151_RESTORED_MAIN_GO_CACHE_EMPTY")
    stable(data["source_sha"])
    receipt = {
        "schema": "forge.rar-g151.exact-main-base-seed-dev.v1",
        "source_sha": data["source_sha"],
        "source_tree": data["source_tree"],
        "base_sha": BASE,
        "base_tree": BASE_TREE,
        "current_graph": data["source_graph_digest"],
        "base_graph": BASE_GRAPH,
        "current_key": data["cache_key"],
        "base_key": BASE_KEY,
        "exact_main_cache_hit": True,
        "main_cache_bytes_after_restore": size,
        "main_cache_file_count": count,
        "source_graph_changed": True,
        "original_go_test_results_reexecute": True,
        "original_go_commands_unchanged": True,
        "dev_only_no_owner_or_science_execution": True,
    }
    out = Path(os.environ["RUNNER_TEMP"]) / "rar-g151-main-seed.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FORGE_RAR_G151=PASS_EXACT_MAIN_COMPILER_SEED bytes="
          + str(size) + " files=" + str(count), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
