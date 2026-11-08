"""One-shot DEV-only exact-main Go compiler seed; no tests or owner skipped."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

from check_rar_g145_pr_scope import admit_original_pr, github_event_base, negative_controls
from check_rar_g148_go_cache import CAP, ROOT, git, identity, stable

BRANCH = "engineering/rar-g154-base-go-cache-seed-first-use-20261108"
BASE = "b26aaf6b656e3cb2793445d94b689ea96f306645"
BASE_TREE = "835facbb86ca41908dd21eefc0cd2227e6af6f1f"
BASE_GRAPH = "39c27c4f51e81fb12d3b5dc573a99793d80c1b692943d7fbb9ed9cd7501cad47"
BASE_KEY = "rar-g148-win-go-db3730bf1158ebde65edf14ced6077aaf11ff6b3267f56377207d0432a3b3d2e"
FILES = {
    "docs/FORGE-G154-BASE-GO-CACHE-FIRST-USE.md",
    ".github/workflows/qualify.yml",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g154_base_cache_dev.py",
    "nativediscovery/g154_compiler_cache_dev_test.go",
}
FROZEN = "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT"



PRE = "G154 frozen exact-main Go compiler source and cache preflight (DEV ONLY)"
RESTORE = "G154 restore literal exact qualified main compiled Go cache (DEV ONLY)"
POST = "G154 attest exact trusted main compiled cache before original Go (DEV ONLY)"
HEAD_EXPR = "${{ github.event.pull_request.head.sha }}"
CACHE_HIT_EXPR = "${{ steps.g148cache.outputs['cache-hit'] }}"
BASE_HIT_EXPR = "${{ steps.g154base.outputs['cache-hit'] }}"

def _step(src: str, name: str) -> str:
    marker = "      - name: " + name + "\n"
    if src.count(marker) != 1:
        raise ValueError("G154_WORKFLOW_STEP_MISSING_OR_DUPLICATED_" + name)
    return src.split(marker, 1)[1].split("\n      - name: ", 1)[0] + "\n"

def _assert_contract(src: str) -> None:
    pre, restore, post = (_step(src, name) for name in (PRE, RESTORE, POST))
    a = src.index("      - name: G148 restore exact-key Windows Go compiler artifacts")
    b = src.index("      - name: " + PRE)
    c = src.index("      - name: " + RESTORE)
    d = src.index("      - name: " + POST)
    e = src.index("      - name: Native Windows source qualification")
    if not (a < b < c < d < e):
        raise ValueError("G154_ORIGINAL_NATIVE_ORDER_CHANGED")
    condition = ("github.event_name == 'pull_request' && github.head_ref == '"
                 + BRANCH + "' && github.event.pull_request.head.repo.full_name == github.repository")
    for label, part, is_post in (("pre", pre, False), ("post", post, True)):
        if "        if: " + condition not in part:
            raise ValueError("G154_" + label + "_EVENT_BRANCH_OR_REPO_GUARD")
        expected = {"G154_HEAD": HEAD_EXPR, "G148_HEAD": HEAD_EXPR,
                    "G148_CACHE_HIT": CACHE_HIT_EXPR}
        if is_post:
            expected["G154_BASE_HIT"] = BASE_HIT_EXPR
        for name, value in expected.items():
            if ("\n          " + name + ": " + value + "\n") not in ("\n" + part):
                raise ValueError("G154_" + label + "_EXACT_ENV_" + name)
        if "python -B scripts/check_rar_g154_base_cache_dev.py --" + label not in part:
            raise ValueError("G154_" + label + "_CHECKER_MISSING")
    if ("        if: " + condition not in restore
        or "        id: g154base\n" not in restore
        or "        uses: actions/cache/restore@v4\n" not in restore
        or "          path: ${{ env.G148_CACHE_PATH }}\n" not in restore
        or "          key: " + BASE_KEY + "\n" not in restore
        or "restore-keys:" in restore):
        raise ValueError("G154_UNTRUSTED_CACHE_RESTORE_CONFIG")
    for original in ("      - name: Native Windows source qualification",
                     "      - name: G148 attest cache and complete original native Go controls"):
        if src.count(original) != 1:
            raise ValueError("G154_ORIGINAL_GO_CONTROL_MISSING")

def _assert_contract_and_negatives() -> None:
    src = (ROOT / ".github/workflows/qualify.yml").read_text(encoding="utf-8")
    _assert_contract(src)
    def mutate(name: str, needle: str, replacement: str) -> str:
        part = _step(src, name)
        if part.count(needle) != 1:
            raise ValueError("G154_NEGATIVE_MUTATION_ANCHOR_DRIFT")
        return src.replace(part, part.replace(needle, replacement))
    cases = (
        ("pre_missing_g148", mutate(PRE, "          G148_HEAD: " + HEAD_EXPR + "\n", "")),
        ("post_missing_g148", mutate(POST, "          G148_HEAD: " + HEAD_EXPR + "\n", "")),
        ("pre_wrong_g148", mutate(PRE, "          G148_HEAD: " + HEAD_EXPR + "\n", "          G148_HEAD: ${{ github.sha }}\n")),
        ("post_wrong_g148", mutate(POST, "          G148_HEAD: " + HEAD_EXPR + "\n", "          G148_HEAD: ${{ github.sha }}\n")),
        ("pre_wrong_g154", mutate(PRE, "          G154_HEAD: " + HEAD_EXPR + "\n", "          G154_HEAD: ${{ github.sha }}\n")),
        ("post_wrong_g154", mutate(POST, "          G154_HEAD: " + HEAD_EXPR + "\n", "          G154_HEAD: ${{ github.sha }}\n")),
        ("pre_wrong_cache_hit", mutate(PRE, "          G148_CACHE_HIT: " + CACHE_HIT_EXPR + "\n", "          G148_CACHE_HIT: false\n")),
        ("post_wrong_cache_hit", mutate(POST, "          G148_CACHE_HIT: " + CACHE_HIT_EXPR + "\n", "          G148_CACHE_HIT: false\n")),
        ("post_wrong_base_hit", mutate(POST, "          G154_BASE_HIT: " + BASE_HIT_EXPR + "\n", "          G154_BASE_HIT: false\n")),
        ("restore_wrong_key", mutate(RESTORE, "          key: " + BASE_KEY + "\n", "          key: invalid-cache-key\n")),
        ("restore_wrong_path", mutate(RESTORE, "          path: ${{ env.G148_CACHE_PATH }}\n", "          path: /tmp/wrong-cache\n")),
        ("restore_prefix", mutate(RESTORE, "          key: " + BASE_KEY + "\n", "          key: " + BASE_KEY + "\n          restore-keys: rar-g148-win-go-\n")),
        ("restore_wrong_action", mutate(RESTORE, "actions/cache/restore@v4", "actions/cache/save@v4")),
        ("pre_wrong_branch", mutate(PRE, "github.head_ref == '" + BRANCH + "'", "github.head_ref == 'main'")),
        ("post_wrong_repo", mutate(POST, "github.event.pull_request.head.repo.full_name == github.repository", "true")),
        ("restore_missing", src.replace("      - name: " + RESTORE + "\n" + _step(src, RESTORE), "")),
    )
    for label, bad in cases:
        try:
            _assert_contract(bad)
        except (ValueError, IndexError):
            continue
        raise ValueError("G154_MUTANT_WRONGLY_ADMITTED_" + label)
    print("FORGE_RAR_G154_CONTRACT=PASS negatives=" + str(len(cases)), flush=True)


def provenance() -> dict:
    head = git("rev-parse", "HEAD")
    stable(head)
    negative_controls()
    _assert_contract_and_negatives()
    if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_OS") != "Windows"
            or os.environ.get("GITHUB_EVENT_NAME") != "pull_request"
            or os.environ.get("GITHUB_HEAD_REF") != BRANCH
            or os.environ.get("G154_HEAD") != head
            or github_event_base(head) != BASE
            or git("merge-base", BASE, head) != BASE
            or git("rev-parse", BASE + "^{tree}") != BASE_TREE
            or admit_original_pr(head, git) != FROZEN):
        raise ValueError("G154_FROZEN_HEAD_BASE_EVENT_OR_SCOPE_MISMATCH")
    changed = git("diff", "--no-renames", "--name-only", BASE, head).splitlines()
    if len(changed) != len(FILES) or set(changed) != FILES:
        raise ValueError("G154_EXACT_SIX_PATH_SCOPE_FAILED")
    data = identity()
    if (data["mode"] != "pr"
            or data["source_graph_digest"] == BASE_GRAPH
            or data["cache_key"] == BASE_KEY
            or os.environ.get("G148_CACHE_KEY") != data["cache_key"]
            or os.environ.get("G148_CACHE_PATH") != data["cache_path"]
            or os.environ.get("G148_MODE") != "pr"
            or os.environ.get("G148_CACHE_HIT", "").lower() not in ("", "false")):
        raise ValueError("G154_CHANGED_GRAPH_OR_MISS_IDENTITY_FAILED")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--pre", action="store_true")
    g.add_argument("--post", action="store_true")
    args = parser.parse_args()
    data = provenance()
    if args.pre:
        print("FORGE_RAR_G154=PASS_FROZEN_PRECHECK current_key="
              + data["cache_key"] + " main_key=" + BASE_KEY, flush=True)
        return 0
    if os.environ.get("G154_BASE_HIT") != "true":
        raise ValueError("G154_EXACT_TRUSTED_MAIN_CACHE_NOT_RESTORED")
    folder = Path(data["cache_path"])
    if not folder.is_dir() or ROOT in folder.parents or folder == ROOT:
        raise ValueError("G154_BASE_COMPILER_CACHE_PATH_UNTRUSTED")
    size = 0
    count = 0
    for entry in folder.rglob("*"):
        if entry.is_file():
            count += 1
            size += entry.stat().st_size
            if size > CAP:
                raise ValueError("G154_RESTORED_BASE_CACHE_EXCEEDS_2GIB")
    if count == 0 or size == 0:
        raise ValueError("G154_RESTORED_MAIN_GO_CACHE_EMPTY")
    stable(data["source_sha"])
    receipt = {
        "schema": "forge.rar-g154.exact-main-base-seed-dev.v1",
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
    out = Path(os.environ["RUNNER_TEMP"]) / "rar-g154-main-seed.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FORGE_RAR_G154=PASS_EXACT_MAIN_COMPILER_SEED bytes="
          + str(size) + " files=" + str(count), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
