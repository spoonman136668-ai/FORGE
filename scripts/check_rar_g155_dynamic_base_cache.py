"""One-shot DEV-only exact-main Go compiler seed; no tests or owner skipped."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
import sys

from check_rar_g145_pr_scope import admit_original_pr, github_event_base, negative_controls
from check_rar_g148_go_cache import CAP, ROOT, git, identity, stable

BRANCH = "engineering/rar-g155-dynamic-main-cache-dev-20261108"
BASE = "a62f469de1d5316c04d063246c30a5812bc8857d"
BASE_TREE = "e306a28616fa4c3ccb8d17e77ed2020154c2a083"
BASE_GRAPH = "39c27c4f51e81fb12d3b5dc573a99793d80c1b692943d7fbb9ed9cd7501cad47"
BASE_KEY = "rar-g148-win-go-db3730bf1158ebde65edf14ced6077aaf11ff6b3267f56377207d0432a3b3d2e"
FILES = {
    "docs/FORGE-G155-DYNAMIC-MAIN-GO-CACHE-DEV.md",
    ".github/workflows/qualify.yml",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g155_dynamic_base_cache.py",
    "nativediscovery/g155_compiler_cache_dev_test.go",
}
FROZEN = "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT"



PRE = "G155 derive dynamic exact-main Go seed from original event base (DEV)"
RESTORE = "G155 restore dynamically derived qualified-main compiled Go seed (DEV)"
POST = "G155 attest dynamic protected-main compiler seed before full original Go (DEV)"
HEAD_EXPR = "${{ github.event.pull_request.head.sha }}"
CACHE_HIT_EXPR = "${{ steps.g148cache.outputs['cache-hit'] }}"
BASE_HIT_EXPR = "${{ steps.g155base.outputs['cache-hit'] }}"

def _step(src: str, name: str) -> str:
    marker = "      - name: " + name + "\n"
    if src.count(marker) != 1:
        raise ValueError("G155_WORKFLOW_STEP_MISSING_OR_DUPLICATED_" + name)
    return src.split(marker, 1)[1].split("\n      - name: ", 1)[0] + "\n"

def _assert_contract(src: str) -> None:
    pre, restore, post = (_step(src, name) for name in (PRE, RESTORE, POST))
    a = src.index("      - name: G148 restore exact-key Windows Go compiler artifacts")
    b = src.index("      - name: " + PRE)
    c = src.index("      - name: " + RESTORE)
    d = src.index("      - name: " + POST)
    e = src.index("      - name: Native Windows source qualification")
    if not (a < b < c < d < e):
        raise ValueError("G155_ORIGINAL_NATIVE_ORDER_CHANGED")
    condition = ("github.event_name == 'pull_request' && github.head_ref == '"
                 + BRANCH + "' && github.event.pull_request.head.repo.full_name == github.repository")
    for label, part, is_post in (("pre", pre, False), ("post", post, True)):
        if "        if: " + condition not in part:
            raise ValueError("G155_" + label + "_EVENT_BRANCH_OR_REPO_GUARD")
        expected = {"G155_HEAD": HEAD_EXPR, "G148_HEAD": HEAD_EXPR,
                    "G148_CACHE_HIT": CACHE_HIT_EXPR}
        if is_post:
            expected["G155_BASE_HIT"] = BASE_HIT_EXPR
        for name, value in expected.items():
            if ("\n          " + name + ": " + value + "\n") not in ("\n" + part):
                raise ValueError("G155_" + label + "_EXACT_ENV_" + name)
        if "python -B scripts/check_rar_g155_dynamic_base_cache.py --" + label not in part:
            raise ValueError("G155_" + label + "_CHECKER_MISSING")
    if ("        if: " + condition not in restore
        or "        id: g155base\n" not in restore
        or "        uses: actions/cache/restore@v4\n" not in restore
        or "          path: ${{ env.G148_CACHE_PATH }}\n" not in restore
        or "          key: ${{ env.G155_BASE_CACHE_KEY }}\n" not in restore
        or "restore-keys:" in restore):
        raise ValueError("G155_UNTRUSTED_CACHE_RESTORE_CONFIG")
    for original in ("      - name: Native Windows source qualification",
                     "      - name: G148 attest cache and complete original native Go controls"):
        if src.count(original) != 1:
            raise ValueError("G155_ORIGINAL_GO_CONTROL_MISSING")

def _assert_contract_and_negatives() -> None:
    src = (ROOT / ".github/workflows/qualify.yml").read_text(encoding="utf-8")
    _assert_contract(src)
    def mutate(name: str, needle: str, replacement: str) -> str:
        part = _step(src, name)
        if part.count(needle) != 1:
            raise ValueError("G155_NEGATIVE_MUTATION_ANCHOR_DRIFT")
        return src.replace(part, part.replace(needle, replacement))
    cases = (
        ("pre_missing_g148", mutate(PRE, "          G148_HEAD: " + HEAD_EXPR + "\n", "")),
        ("post_missing_g148", mutate(POST, "          G148_HEAD: " + HEAD_EXPR + "\n", "")),
        ("pre_wrong_g148", mutate(PRE, "          G148_HEAD: " + HEAD_EXPR + "\n", "          G148_HEAD: ${{ github.sha }}\n")),
        ("post_wrong_g148", mutate(POST, "          G148_HEAD: " + HEAD_EXPR + "\n", "          G148_HEAD: ${{ github.sha }}\n")),
        ("pre_wrong_g155", mutate(PRE, "          G155_HEAD: " + HEAD_EXPR + "\n", "          G155_HEAD: ${{ github.sha }}\n")),
        ("post_wrong_g155", mutate(POST, "          G155_HEAD: " + HEAD_EXPR + "\n", "          G155_HEAD: ${{ github.sha }}\n")),
        ("pre_wrong_cache_hit", mutate(PRE, "          G148_CACHE_HIT: " + CACHE_HIT_EXPR + "\n", "          G148_CACHE_HIT: false\n")),
        ("post_wrong_cache_hit", mutate(POST, "          G148_CACHE_HIT: " + CACHE_HIT_EXPR + "\n", "          G148_CACHE_HIT: false\n")),
        ("post_wrong_base_hit", mutate(POST, "          G155_BASE_HIT: " + BASE_HIT_EXPR + "\n", "          G155_BASE_HIT: false\n")),
        ("restore_wrong_key", mutate(RESTORE, "          key: ${{ env.G155_BASE_CACHE_KEY }}\n", "          key: invalid-cache-key\n")),
        ("restore_wrong_path", mutate(RESTORE, "          path: ${{ env.G148_CACHE_PATH }}\n", "          path: /tmp/wrong-cache\n")),
        ("restore_prefix", mutate(RESTORE, "          key: ${{ env.G155_BASE_CACHE_KEY }}\n", "          key: ${{ env.G155_BASE_CACHE_KEY }}\n          restore-keys: rar-g148-win-go-\n")),
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
        raise ValueError("G155_MUTANT_WRONGLY_ADMITTED_" + label)
    print("FORGE_RAR_G155_CONTRACT=PASS negatives=" + str(len(cases)), flush=True)



# Reconstruct exactly G148's ls-files stage row semantics from a pinned
# committed Git tree. No base checkout, remote fetch or working-tree change.
MODES = {b"100644": b"blob", b"100755": b"blob",
         b"120000": b"blob", b"160000": b"commit"}
SUFFIXES = (b".go", b".c", b".h", b".s", b".S",
            b".syso", b".inc", b".proto", b".mod", b".sum")


def _parse_tree(raw: bytes) -> list[tuple[bytes, bytes, bytes]]:
    if not raw or not raw.endswith(b"\0"):
        raise ValueError("G155_GIT_TREE_TRUNCATED")
    result = []
    seen = set()
    for record in raw[:-1].split(b"\0"):
        if record.count(b"\t") != 1:
            raise ValueError("G155_GIT_TREE_MALFORMED")
        meta, path = record.split(b"\t", 1)
        parts = meta.split(b" ")
        if (len(parts) != 3 or parts[0] not in MODES
            or MODES[parts[0]] != parts[1]
            or re.fullmatch(b"[0-9a-f]{40}", parts[2]) is None
            or not path or path.startswith(b"/")
            or b"\\" in path
            or any(p in (b"", b".", b"..") for p in path.split(b"/"))
            or path in seen):
            raise ValueError("G155_GIT_TREE_INVALID_OR_DUPLICATE_RECORD")
        seen.add(path)
        result.append((parts[0] + b" " + parts[2] + b" 0\t" + path,
                       path, parts[2]))
    return result


def _tree_mutation_negatives() -> None:
    good = b"100644 blob " + b"a" * 40 + b"\tprobe.go\0"
    rows = _parse_tree(good)
    if len(rows) != 1 or rows[0][0] != b"100644 " + b"a" * 40 + b" 0\tprobe.go":
        raise ValueError("G155_GIT_TREE_STAGE_EQUIVALENCE_FAILED")
    invalid = (
        good[:-1],
        good + good,
        good.replace(b"blob", b"tree"),
        good.replace(b"100644", b"160000"),
        good.replace(b"a" * 40, b"x" * 40),
        good.replace(b"probe.go", b"../probe.go"),
        good.replace(b"probe.go", b"dir//probe.go"),
        good.replace(b"probe.go", b"/probe.go"),
        good.replace(b"\t", b" "),
        good.replace(b"probe.go", b"dir\\probe.go"),
    )
    for candidate in invalid:
        try:
            _parse_tree(candidate)
        except ValueError:
            continue
        raise ValueError("G155_INVALID_TREE_MUTANT_ACCEPTED")
    print("FORGE_RAR_G155_TREE_NEGATIVES=PASS count=" + str(len(invalid)),
          flush=True)


def _reference_graph(revision: str) -> tuple[str, int]:
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("G155_REFERENCE_REVISION_INVALID")
    raw = subprocess.check_output(
        ["git", "ls-tree", "-r", "-z", revision], cwd=ROOT, timeout=80
    )
    rows = _parse_tree(raw)
    dirs = {path.rpartition(b"/")[0] for _, path, _ in rows
            if path.endswith(b".go")}
    if len(rows) < 1200 or len(dirs) < 130:
        raise ValueError("G155_REFERENCE_SOURCE_INVENTORY_TOO_SMALL")
    embeds = False
    for _, path, blob in rows:
        if path.endswith(b".go") and b"/" not in path:
            data = subprocess.check_output(
                ["git", "cat-file", "blob", blob.decode("ascii")],
                cwd=ROOT, timeout=40
            )
            if b"//go:embed" in data:
                embeds = True
                break
    selected = []
    for stage_row, path, _ in rows:
        relevant = (embeds or b"/" not in path or path.endswith(SUFFIXES)
                    or any(path.startswith(d + b"/") for d in dirs if d))
        if relevant:
            selected.append(stage_row)
    if not 470 <= len(selected) <= len(rows):
        raise ValueError("G155_REFERENCE_SEMANTIC_INPUTS_INCOMPLETE")
    return hashlib.sha256(b"\0".join(selected) + b"\0").hexdigest(), len(selected)


def _dynamic_base(data: dict) -> dict:
    base = github_event_base(data["source_sha"])
    if base != BASE or git("merge-base", base, data["source_sha"]) != base:
        raise ValueError("G155_BASE_EVENT_SOURCE_DRIFT")
    if git("rev-parse", base + "^{tree}") != BASE_TREE:
        raise ValueError("G155_BASE_TREE_DRIFT")
    _tree_mutation_negatives()
    current_graph, current_count = _reference_graph(data["source_sha"])
    if (current_graph != data["source_graph_digest"]
            or current_count != data["source_graph_files"]):
        raise ValueError("G155_HEAD_GIT_TREE_VS_INDEX_GRAPH_MISMATCH")
    base_graph, base_count = _reference_graph(base)
    if base_graph != BASE_GRAPH or base_graph == current_graph:
        raise ValueError("G155_BASE_GRAPH_WRONG_OR_NOT_CHANGED")
    same_environment = dict(data["fingerprint"])
    same_environment["source_graph"] = base_graph
    derived_key = "rar-g148-win-go-" + hashlib.sha256(json.dumps(
        same_environment, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    if derived_key != BASE_KEY or derived_key == data["cache_key"]:
        raise ValueError("G155_DYNAMIC_BASE_KEY_NOT_QUALIFIED")
    return {"derived_base_key": derived_key, "base_graph_digest": base_graph,
            "base_source_sha": base, "base_source_tree": BASE_TREE,
            "base_graph_files": base_count}

def provenance() -> dict:
    head = git("rev-parse", "HEAD")
    stable(head)
    negative_controls()
    _assert_contract_and_negatives()
    if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_OS") != "Windows"
            or os.environ.get("GITHUB_EVENT_NAME") != "pull_request"
            or os.environ.get("GITHUB_HEAD_REF") != BRANCH
            or os.environ.get("G155_HEAD") != head
            or github_event_base(head) != BASE
            or git("merge-base", BASE, head) != BASE
            or git("rev-parse", BASE + "^{tree}") != BASE_TREE
            or admit_original_pr(head, git) != FROZEN):
        raise ValueError("G155_FROZEN_HEAD_BASE_EVENT_OR_SCOPE_MISMATCH")
    changed = git("diff", "--no-renames", "--name-only", BASE, head).splitlines()
    if len(changed) != len(FILES) or set(changed) != FILES:
        raise ValueError("G155_EXACT_SIX_PATH_SCOPE_FAILED")
    data = identity()
    if (data["mode"] != "pr"
            or data["source_graph_digest"] == BASE_GRAPH
            or data["cache_key"] == BASE_KEY
            or os.environ.get("G148_CACHE_KEY") != data["cache_key"]
            or os.environ.get("G148_CACHE_PATH") != data["cache_path"]
            or os.environ.get("G148_MODE") != "pr"
            or os.environ.get("G148_CACHE_HIT", "").lower() not in ("", "false")):
        raise ValueError("G155_CHANGED_GRAPH_OR_MISS_IDENTITY_FAILED")
    data.update(_dynamic_base(data))
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--pre", action="store_true")
    g.add_argument("--post", action="store_true")
    args = parser.parse_args()
    data = provenance()
    if args.pre:
        target = os.environ.get("GITHUB_ENV")
        if not target:
            raise ValueError("G155_GITHUB_ENV_ABSENT")
        with open(target, "a", encoding="utf-8") as out:
            out.write("G155_BASE_CACHE_KEY=" + data["derived_base_key"] + "\n"
                      + "G155_BASE_SOURCE_SHA=" + data["base_source_sha"] + "\n"
                      + "G155_BASE_GRAPH=" + data["base_graph_digest"] + "\n")
        print("FORGE_RAR_G155=PASS_DYNAMIC_MAIN_KEY"
              + " head_graph=" + data["source_graph_digest"]
              + " base_graph=" + data["base_graph_digest"]
              + " current_key=" + data["cache_key"]
              + " derived_base_key=" + data["derived_base_key"], flush=True)
        return 0
    if (os.environ.get("G155_BASE_CACHE_KEY") != data["derived_base_key"]
            or os.environ.get("G155_BASE_SOURCE_SHA") != data["base_source_sha"]
            or os.environ.get("G155_BASE_GRAPH") != data["base_graph_digest"]):
        raise ValueError("G155_BETWEEN_STEPS_BASE_DERIVATION_DRIFT")
    if os.environ.get("G155_BASE_HIT") != "true":
        raise ValueError("G155_EXACT_TRUSTED_MAIN_CACHE_NOT_RESTORED")
    folder = Path(data["cache_path"])
    if not folder.is_dir() or ROOT in folder.parents or folder == ROOT:
        raise ValueError("G155_BASE_COMPILER_CACHE_PATH_UNTRUSTED")
    size = 0
    count = 0
    for entry in folder.rglob("*"):
        if entry.is_file():
            count += 1
            size += entry.stat().st_size
            if size > CAP:
                raise ValueError("G155_RESTORED_BASE_CACHE_EXCEEDS_2GIB")
    if count == 0 or size == 0:
        raise ValueError("G155_RESTORED_MAIN_GO_CACHE_EMPTY")
    stable(data["source_sha"])
    receipt = {
        "schema": "forge.rar-g155.exact-main-base-seed-dev.v1",
        "source_sha": data["source_sha"],
        "source_tree": data["source_tree"],
        "base_sha": data["base_source_sha"],
        "base_tree": data["base_source_tree"],
        "current_graph": data["source_graph_digest"],
        "base_graph": data["base_graph_digest"],
        "current_key": data["cache_key"],
        "base_key": data["derived_base_key"],
        "exact_main_cache_hit": True,
        "main_cache_bytes_after_restore": size,
        "main_cache_file_count": count,
        "source_graph_changed": True,
        "original_go_test_results_reexecute": True,
        "original_go_commands_unchanged": True,
        "dev_only_no_owner_or_science_execution": True,
    }
    out = Path(os.environ["RUNNER_TEMP"]) / "rar-g155-main-seed.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FORGE_RAR_G155=PASS_EXACT_MAIN_COMPILER_SEED bytes="
          + str(size) + " files=" + str(count), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
