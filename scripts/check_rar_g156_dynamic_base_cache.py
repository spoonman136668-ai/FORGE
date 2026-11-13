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

from check_rar_g145_pr_scope import (admit_original_pr, github_event_base, negative_controls,
    V41_STATUS_BRANCH, V41_STATUS_RESULT, V41_STATUS_BASE,
    V41_BACKUP_BRANCH, V41_BACKUP_RESULT, V41_BACKUP_BASE,
    V41_PAUSE_BRANCH, V41_PAUSE_RESULT, V41_PAUSE_BASE)
from check_rar_g148_go_cache import CAP, ROOT, git, identity, stable, compiled_graph

BRANCH = "engineering/rar-g156-dynamic-main-cache-release-20261108"
BASE = "a62f469de1d5316c04d063246c30a5812bc8857d"
BASE_TREE = "e306a28616fa4c3ccb8d17e77ed2020154c2a083"
BASE_GRAPH = "39c27c4f51e81fb12d3b5dc573a99793d80c1b692943d7fbb9ed9cd7501cad47"
BASE_KEY = "rar-g148-win-go-db3730bf1158ebde65edf14ced6077aaf11ff6b3267f56377207d0432a3b3d2e"
FILES = {
    "docs/FORGE-G156-DYNAMIC-MAIN-GO-CACHE-RELEASE.md",
    ".github/workflows/qualify.yml",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
}
FROZEN = "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT"
COMPAT_BRANCH = "engineering/rar-g158-optional-helper-compat-20261108"
COMPAT_BASE = "6a9bd9b87bc8d12cb0e8237c1da606aecf28c39b"
COMPAT_TREE = "f08b8d897bb7b3adcd62956c44142d56f41415f4"
COMPAT_FILES = {
    "docs/FORGE-G158-OPTIONAL-HELPER-COMPAT.md",
    ".github/workflows/qualify.yml",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
}



PRE = "G156 derive exact same-repo PR-base Go cache key (original Go still runs)"
RESTORE = "G156 restore optional exact event-main compiled Go cache seed"
POST = "G156 attest optional exact main compiler cache seed before full Go"
HEAD_EXPR = "${{ github.event.pull_request.head.sha }}"
CACHE_HIT_EXPR = "${{ steps.g148cache.outputs['cache-hit'] }}"
BASE_HIT_EXPR = "${{ steps.g156base.outputs['cache-hit'] }}"

def _step(src: str, name: str) -> str:
    marker = "      - name: " + name + "\n"
    if src.count(marker) != 1:
        raise ValueError("G156_WORKFLOW_STEP_MISSING_OR_DUPLICATED_" + name)
    return src.split(marker, 1)[1].split("\n      - name: ", 1)[0] + "\n"

# Exact workflow dependency contract. These tests run in both original native
# jobs on the frozen release candidate and in Windows PR fallback preflight.
BASECOND = ("github.event_name == 'pull_request' && "
            "github.event.pull_request.head.repo.full_name == github.repository && "
            "steps.g148cache.outputs['cache-hit'] != 'true'")
PRECOND = BASECOND + " && hashFiles('scripts/check_rar_g156_dynamic_base_cache.py') != ''"
SEEDCOND = BASECOND + " && env.G156_BASE_CACHE_ELIGIBLE == 'true'"


def _assert_contract(src: str) -> None:
    pre, restore, post = (_step(src, n) for n in (PRE, RESTORE, POST))
    orig = src.index("      - name: G148 restore exact-key Windows Go compiler artifacts")
    a = src.index("      - name: " + PRE)
    b = src.index("      - name: " + RESTORE)
    c = src.index("      - name: " + POST)
    d = src.index("      - name: Native Windows source qualification")
    if not orig < a < b < c < d:
        raise ValueError("G156_ORIGINAL_FULL_GO_STEP_ORDER_CHANGED")
    for label, part, condition, is_post in (("pre", pre, PRECOND, False),
                                            ("post", post, SEEDCOND, True)):
        if "        if: " + condition not in part:
            raise ValueError("G156_" + label + "_SAME_REPO_CACHE_CONDITION")
        want = {"G156_HEAD": HEAD_EXPR, "G148_HEAD": HEAD_EXPR,
                "G148_CACHE_HIT": CACHE_HIT_EXPR}
        if is_post:
            want["G156_BASE_HIT"] = BASE_HIT_EXPR
        for key, value in want.items():
            if ("\n          " + key + ": " + value + "\n") not in ("\n" + part):
                raise ValueError("G156_" + label + "_ENV_" + key)
        if "python -B scripts/check_rar_g156_dynamic_base_cache.py --" + label not in part:
            raise ValueError("G156_" + label + "_CHECKER_ABSENT")
    if ("        if: " + SEEDCOND not in restore
            or "        id: g156base\n" not in restore
            or "        uses: actions/cache/restore@v4\n" not in restore
            or "          path: ${{ env.G148_CACHE_PATH }}\n" not in restore
            or "          key: ${{ env.G156_BASE_CACHE_KEY }}\n" not in restore
            or "restore-keys:" in restore
            or "actions/cache/save" in restore):
        raise ValueError("G156_UNTRUSTED_CACHE_RESTORE_CONFIGURATION")
    for original in ("Native Windows source qualification",
                     "G148 attest cache and complete original native Go controls"):
        if src.count("      - name: " + original) != 1:
            raise ValueError("G156_ORIGINAL_NATIVE_TESTS_MISSING_OR_DUPLICATE")
    for platform in ("Linux", "Windows"):
        if src.count("      - name: G156 static source-guard and mutation audit on "
                     + platform + " (release)") != 1:
            raise ValueError("G156_STATIC_PLATFORM_MISSING_" + platform)


def _assert_contract_and_negatives() -> None:
    src = (ROOT / ".github/workflows/qualify.yml").read_text(encoding="utf-8")
    _assert_contract(src)
    def mutate(name: str, original: str, changed: str) -> str:
        chunk = _step(src, name)
        if chunk.count(original) != 1:
            raise ValueError("G156_NEGATIVE_TEST_ANCHOR_CHANGED")
        return src.replace(chunk, chunk.replace(original, changed))
    cases = (
        ("pre_missing_g148", mutate(PRE, "          G148_HEAD: " + HEAD_EXPR + "\n", "")),
        ("post_missing_g148", mutate(POST, "          G148_HEAD: " + HEAD_EXPR + "\n", "")),
        ("pre_wrong_g148", mutate(PRE, "          G148_HEAD: " + HEAD_EXPR + "\n", "          G148_HEAD: ${{ github.sha }}\n")),
        ("post_wrong_g148", mutate(POST, "          G148_HEAD: " + HEAD_EXPR + "\n", "          G148_HEAD: ${{ github.sha }}\n")),
        ("pre_wrong_g156", mutate(PRE, "          G156_HEAD: " + HEAD_EXPR + "\n", "          G156_HEAD: ${{ github.sha }}\n")),
        ("post_wrong_g156", mutate(POST, "          G156_HEAD: " + HEAD_EXPR + "\n", "          G156_HEAD: ${{ github.sha }}\n")),
        ("pre_wrong_cache_hit", mutate(PRE, "          G148_CACHE_HIT: " + CACHE_HIT_EXPR + "\n", "          G148_CACHE_HIT: true\n")),
        ("post_wrong_cache_hit", mutate(POST, "          G148_CACHE_HIT: " + CACHE_HIT_EXPR + "\n", "          G148_CACHE_HIT: true\n")),
        ("post_wrong_base_hit", mutate(POST, "          G156_BASE_HIT: " + BASE_HIT_EXPR + "\n", "          G156_BASE_HIT: false\n")),
        ("restore_wrong_key", mutate(RESTORE, "          key: ${{ env.G156_BASE_CACHE_KEY }}\n", "          key: hardcoded-key\n")),
        ("restore_wrong_path", mutate(RESTORE, "          path: ${{ env.G148_CACHE_PATH }}\n", "          path: /tmp/wrong-cache\n")),
        ("restore_prefix", mutate(RESTORE, "          key: ${{ env.G156_BASE_CACHE_KEY }}\n", "          key: ${{ env.G156_BASE_CACHE_KEY }}\n          restore-keys: rar-g148-win-go-\n")),
        ("restore_wrong_action", mutate(RESTORE, "actions/cache/restore@v4", "actions/cache/save@v4")),
        ("pre_missing_optional_helper_guard", mutate(PRE, " && hashFiles('scripts/check_rar_g156_dynamic_base_cache.py') != ''", "")),
        ("pre_wrong_repository", mutate(PRE, "github.event.pull_request.head.repo.full_name == github.repository", "true")),
        ("post_wrong_repository", mutate(POST, "github.event.pull_request.head.repo.full_name == github.repository", "true")),
        ("restore_missing", src.replace("      - name: " + RESTORE + "\n" + _step(src, RESTORE), "")),
    )
    for label, altered in cases:
        try:
            _assert_contract(altered)
        except (ValueError, IndexError):
            continue
        raise ValueError("G156_NEGATIVE_MUTANT_ACCEPTED_" + label)
    print("FORGE_RAR_G156_CONTRACT=PASS negatives=" + str(len(cases)), flush=True)


# Reconstruct exactly G148's ls-files stage row semantics from a pinned
# committed Git tree. No base checkout, remote fetch or working-tree change.
MODES = {b"100644": b"blob", b"100755": b"blob",
         b"120000": b"blob", b"160000": b"commit"}
SUFFIXES = (b".go", b".c", b".h", b".s", b".S",
            b".syso", b".inc", b".proto", b".mod", b".sum")


def _parse_tree(raw: bytes) -> list[tuple[bytes, bytes, bytes]]:
    if not raw or not raw.endswith(b"\0"):
        raise ValueError("G156_GIT_TREE_TRUNCATED")
    result = []
    seen = set()
    for record in raw[:-1].split(b"\0"):
        if record.count(b"\t") != 1:
            raise ValueError("G156_GIT_TREE_MALFORMED")
        meta, path = record.split(b"\t", 1)
        parts = meta.split(b" ")
        if (len(parts) != 3 or parts[0] not in MODES
            or MODES[parts[0]] != parts[1]
            or re.fullmatch(b"[0-9a-f]{40}", parts[2]) is None
            or not path or path.startswith(b"/")
            or b"\\" in path
            or any(p in (b"", b".", b"..") for p in path.split(b"/"))
            or path in seen):
            raise ValueError("G156_GIT_TREE_INVALID_OR_DUPLICATE_RECORD")
        seen.add(path)
        result.append((parts[0] + b" " + parts[2] + b" 0\t" + path,
                       path, parts[2]))
    return result


def _tree_mutation_negatives() -> None:
    good = b"100644 blob " + b"a" * 40 + b"\tprobe.go\0"
    rows = _parse_tree(good)
    if len(rows) != 1 or rows[0][0] != b"100644 " + b"a" * 40 + b" 0\tprobe.go":
        raise ValueError("G156_GIT_TREE_STAGE_EQUIVALENCE_FAILED")
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
        raise ValueError("G156_INVALID_TREE_MUTANT_ACCEPTED")
    print("FORGE_RAR_G156_TREE_NEGATIVES=PASS count=" + str(len(invalid)),
          flush=True)


def _reference_graph(revision: str) -> tuple[str, int]:
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("G156_REFERENCE_REVISION_INVALID")
    raw = subprocess.check_output(
        ["git", "ls-tree", "-r", "-z", revision], cwd=ROOT, timeout=80
    )
    rows = _parse_tree(raw)
    dirs = {path.rpartition(b"/")[0] for _, path, _ in rows
            if path.endswith(b".go")}
    if len(rows) < 1200 or len(dirs) < 130:
        raise ValueError("G156_REFERENCE_SOURCE_INVENTORY_TOO_SMALL")
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
        raise ValueError("G156_REFERENCE_SEMANTIC_INPUTS_INCOMPLETE")
    return hashlib.sha256(b"\0".join(selected) + b"\0").hexdigest(), len(selected)



def _release_scope(base: str, tree: str, head: str) -> None:
    admission = admit_original_pr(head, git)
    if os.environ.get("GITHUB_HEAD_REF") == V41_PAUSE_BRANCH:
        # Exact original owner PR1735 and immutable base tree; no cache bypass.
        if (admission != V41_PAUSE_RESULT
                or base != V41_PAUSE_BASE
                or tree != "c7cc4ace902da2b131e686a2bbc396af3f41c521"):
            raise ValueError("G156_V41_PAUSE_FROZEN_OWNER_SCOPE_REQUIRED")
        return
    if os.environ.get("GITHUB_HEAD_REF") == V41_BACKUP_BRANCH:
        # Exact, owner-only PR1734. No generic runner workflow/harness admission.
        if (admission != V41_BACKUP_RESULT
                or base != V41_BACKUP_BASE
                or tree != "1fb6187444af8a979ee00549e9d2115947daff37"):
            raise ValueError("G156_V41_BACKUP_FROZEN_SCOPE_REQUIRED")
        return
    if os.environ.get("GITHUB_HEAD_REF") == V41_STATUS_BRANCH:
        # Exact PR1731 owner-authored, pinned workflow blob permission only.
        # This does not grant cache/test reuse, live owner or release authority.
        if (admission != V41_STATUS_RESULT
                or base != V41_STATUS_BASE
                or tree != "2eae7f1826a93a584563d77eeaa94a46201956e7"):
            raise ValueError("G156_V41_OWNER_READONLY_FROZEN_SCOPE_REQUIRED")
        return
    if os.environ.get("GITHUB_HEAD_REF") == "engineering/f139-v41-native-original-install-entry-20261113":
        if (admission != FROZEN
                or base != "98ec09b732a7764d1f2a38b98abd5927dab03dac"
                or tree != "8eb75695d6ba6a4c038f0a9e6faf2583d5278dd7"):
            raise ValueError("G156_V41_INSTALL_EXACT_BASE_OR_TREE_REQUIRED")
        return
    if os.environ.get("GITHUB_HEAD_REF") == "engineering/f139-v41-owner-native-stage-workflow-20261113":
        if (admission != FROZEN
                or base != "2a7f2f58f829e9de9bdf47fe963d3edbf9335982"
                or tree != "620b6945a8621bc2971610cabe7906b5e91c43c2"):
            raise ValueError("G156_V41_STAGE_EXACT_BASE_OR_TREE_REQUIRED")
        return
    if os.environ.get("GITHUB_HEAD_REF") == 'engineering/f139-v40-explicit-owner-handoff-20261109':
        if (admission != FROZEN or base != 'feb75e7490256a6930698742a43b8d12384fbbca'
                or tree != '548dd8a0cc7b9ea3db278aa82dc6a22e0c350929'):
            raise ValueError("G156_V40_HANDOFF_FROZEN_SCOPE_REQUIRED")
        return
    if os.environ.get("GITHUB_HEAD_REF") == 'engineering/f139-v40-source-bound-copy-qualification-20261109':
        if (admission != FROZEN or base != 'fa1a0477996bf1fb0568290a3692c57ee8b29b91'
                or tree != '0554ee925e18e5d77b321b817e1bd42b11fd18d5'):
            raise ValueError("G156_V40_COPY_FROZEN_SCOPE_REQUIRED")
        return
    if os.environ.get("GITHUB_HEAD_REF") == 'engineering/f139-v40-qualified-readonly-route-20261109':
        if (admission != FROZEN or base != '32de33753c874102de9672d2768e4b7c0b866b25'
                or tree != "22d135f137c371c395604315605dbf5cb4f776a2"):
            raise ValueError("G156_V40_READONLY_FROZEN_SCOPE_REQUIRED")
    elif os.environ.get("GITHUB_HEAD_REF") == "engineering/f139-exact-worker-release-scope-20261109":
        if (admission != FROZEN or base != "0e122eb8e571ddddee1dea4168cf18cfc7dc019d"
                or tree != "4dd3ad8fcd4ab039192994ebfa679ced30af6b1a"):
            raise ValueError("G156_HYBRID_GOVERNANCE_FROZEN_SCOPE_REQUIRED")
    elif os.environ.get("GITHUB_HEAD_REF") == "release/f139-hybrid-qualified-worker-governance-20261109":
        if admission != "EXACT_PR1642_HYBRID_WORKER_BLOB_QUALIFICATION_ONLY":
            raise ValueError("G156_EXACT_HYBRID_WORKER_SCOPE_REQUIRED")
    elif os.environ.get("GITHUB_HEAD_REF") == BRANCH:
        if (admission != FROZEN or base != BASE or tree != BASE_TREE):
            raise ValueError("G156_FROZEN_RELEASE_BASE_OR_ADMISSION_MISMATCH")
        changed = git("diff", "--no-renames", "--name-only", BASE, head).splitlines()
        if len(changed) != len(FILES) or set(changed) != FILES:
            raise ValueError("G156_FROZEN_FIVE_FILE_RELEASE_SCOPE_CHANGED")
    elif os.environ.get("GITHUB_HEAD_REF") == COMPAT_BRANCH:
        if (admission != FROZEN or base != COMPAT_BASE or tree != COMPAT_TREE):
            raise ValueError("G158_FROZEN_BASE_OR_ADMISSION_MISMATCH")
        changed = git("diff", "--no-renames", "--name-only", base, head).splitlines()
        if len(changed) != len(COMPAT_FILES) or set(changed) != COMPAT_FILES:
            raise ValueError("G158_EXACT_FIVE_PATH_COMPAT_SCOPE_CHANGED")
    elif os.environ.get("GITHUB_HEAD_REF") == "engineering/rar-g160-partial-go-diagnostics-20261109":
        if (admission != FROZEN or base != "21b8649569bd9577c325da1ea99ecac81ff5df89" or tree != "ddf7d95fe7883b0d12b700c9a19c89a87a1aaa6f"):
            raise ValueError("G160_FROZEN_BASE_OR_ADMISSION_MISMATCH")
        changed = git("diff", "--no-renames", "--name-only", base, head).splitlines()
        expected = {
            "docs/FORGE-G160-G141-PARTIAL-GO-DIAGNOSTICS.md",
            "scripts/check_rar_g141_parallel_go.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        }
        if len(changed) != len(expected) or set(changed) != expected:
            raise ValueError("G160_EXACT_FIVE_PATH_DIAGNOSTIC_SCOPE_CHANGED")
    elif os.environ.get("GITHUB_HEAD_REF") == "engineering/rar-g161-verified-pr-ancestry-20261109":
        if (admission != FROZEN or base != "ad9026d2e551b054fc944d536ded37fe20a1aaa4" or tree != "9f7ac8adb3a2665cf86c92c47fef482f6097feb5"):
            raise ValueError("G161_FROZEN_BASE_OR_ADMISSION_MISMATCH")
        changed = git("diff", "--no-renames", "--name-only", base, head).splitlines()
        expected = {
            "docs/FORGE-G161-G145-PR-ANCESTRY.md",
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        }
        if len(changed) != len(expected) or set(changed) != expected:
            raise ValueError("G161_EXACT_FIVE_PATH_SCOPE_CHANGED")
    elif admission != "EXACT_MAIN_ANCESTOR_GENERIC_SOURCE_PR":
        raise ValueError("G156_UNAUTHORIZED_GENERIC_PR_SOURCE")


def _reference(data: dict) -> dict:
    head = data["source_sha"]
    base = github_event_base(head)
    if git("merge-base", base, head) != base:
        raise ValueError("G156_EVENT_BASE_NOT_ANCESTOR")
    tree = git("rev-parse", base + "^{tree}")
    if re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        raise ValueError("G156_EVENT_BASE_TREE_NOT_CONTENT_ADDRESSED")
    _release_scope(base, tree, head)
    current_digest, current_count = _reference_graph(head)
    if (current_digest != data["source_graph_digest"]
            or current_count != data["source_graph_files"]):
        raise ValueError("G156_GIT_TREE_INDEX_SEMANTIC_DIVERGENCE")
    base_digest, base_count = _reference_graph(base)
    if os.environ.get("GITHUB_HEAD_REF") == BRANCH and base_digest != BASE_GRAPH:
        raise ValueError("G156_FROZEN_RELEASE_GO_GRAPH_CHANGED")
    fp = dict(data["fingerprint"])
    fp["source_graph"] = base_digest
    baseline_key = "rar-g148-win-go-" + hashlib.sha256(json.dumps(
        fp, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    eligible = base_digest != current_digest and baseline_key != data["cache_key"]
    if os.environ.get("GITHUB_HEAD_REF") == BRANCH and baseline_key != BASE_KEY:
        raise ValueError("G156_FROZEN_RELEASE_BASE_KEY_MISMATCH")
    return dict(base_source_sha=base, base_source_tree=tree,
                base_graph_digest=base_digest, base_graph_files=base_count,
                derived_base_key=baseline_key, eligible=eligible)


def _static() -> int:
    head = git("rev-parse", "HEAD")
    stable(head)
    negative_controls()
    _assert_contract_and_negatives()
    _tree_mutation_negatives()
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_EVENT_NAME") != "pull_request"
            or os.environ.get("GITHUB_HEAD_REF") not in (BRANCH, COMPAT_BRANCH)
            or os.environ.get("G156_HEAD") != head):
        raise ValueError("G156_STATIC_ONLY_FROZEN_RELEASE_SOURCE")
    base = github_event_base(head)
    if git("merge-base", base, head) != base:
        raise ValueError("G156_STATIC_PR_BASE_NOT_ANCESTOR")
    tree = git("rev-parse", base + "^{tree}")
    _release_scope(base, tree, head)
    digest, count = compiled_graph()
    tree_digest, tree_count = _reference_graph(head)
    base_digest, base_count = _reference_graph(base)
    if (digest != tree_digest or count != tree_count
            or base_digest != BASE_GRAPH or base_count < 470):
        raise ValueError("G156_STATIC_TREE_INDEX_OR_BASE_GRAPH_MISMATCH")
    print("FORGE_RAR_G156_STATIC=PASS"
          + " source_sha=" + head
          + " base_sha=" + base
          + " head_graph=" + digest
          + " base_graph=" + base_digest, flush=True)
    return 0


def _provenance() -> dict:
    head = git("rev-parse", "HEAD")
    stable(head)
    negative_controls()
    _assert_contract_and_negatives()
    _tree_mutation_negatives()
    if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_OS") != "Windows"
            or os.environ.get("GITHUB_EVENT_NAME") != "pull_request"
            or os.environ.get("G156_HEAD") != head
            or os.environ.get("G148_CACHE_HIT", "").lower() not in ("", "false")):
        raise ValueError("G156_PRECONDITIONS_NOT_WINDOWS_EXACT_SOURCE_MISS")
    data = identity()
    if (data["mode"] != "pr"
            or data["source_sha"] != head
            or os.environ.get("G148_CACHE_KEY") != data["cache_key"]
            or os.environ.get("G148_CACHE_PATH") != data["cache_path"]
            or os.environ.get("G148_MODE") != data["mode"]):
        raise ValueError("G156_EXACT_G148_CURRENT_SOURCE_IDENTITY_DRIFT")
    data.update(_reference(data))
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--static", action="store_true")
    group.add_argument("--pre", action="store_true")
    group.add_argument("--post", action="store_true")
    args = parser.parse_args()
    if args.static:
        return _static()
    data = _provenance()
    if args.pre:
        target = os.environ.get("GITHUB_ENV")
        if not target:
            raise ValueError("G156_GITHUB_ENV_ABSENT")
        with open(target, "a", encoding="utf-8") as out:
            out.write("G156_BASE_CACHE_ELIGIBLE="
                      + str(data["eligible"]).lower() + "\n"
                      + "G156_BASE_CACHE_KEY=" + data["derived_base_key"] + "\n"
                      + "G156_BASE_SOURCE_SHA=" + data["base_source_sha"] + "\n"
                      + "G156_BASE_GRAPH=" + data["base_graph_digest"] + "\n")
        print("FORGE_RAR_G156=PASS_DYNAMIC_BASE_PRECHECK"
              + " eligible=" + str(data["eligible"]).lower()
              + " base_sha=" + data["base_source_sha"]
              + " source_graph=" + data["source_graph_digest"]
              + " base_graph=" + data["base_graph_digest"]
              + " current_key=" + data["cache_key"]
              + " derived_base_key=" + data["derived_base_key"], flush=True)
        return 0
    if (not data["eligible"]
            or os.environ.get("G156_BASE_CACHE_ELIGIBLE") != "true"
            or os.environ.get("G156_BASE_CACHE_KEY") != data["derived_base_key"]
            or os.environ.get("G156_BASE_SOURCE_SHA") != data["base_source_sha"]
            or os.environ.get("G156_BASE_GRAPH") != data["base_graph_digest"]):
        raise ValueError("G156_BETWEEN_STEPS_BASE_SOURCE_DRIFT")
    hit = os.environ.get("G156_BASE_HIT", "").lower() == "true"
    cache_bytes = 0
    cache_files = 0
    if hit:
        folder = Path(data["cache_path"])
        if not folder.is_dir() or folder == ROOT or ROOT in folder.parents:
            raise ValueError("G156_SEEDED_GO_CACHE_PATH_OUTSIDE_BOUNDARY")
        for item in folder.rglob("*"):
            if item.is_file():
                cache_files += 1
                cache_bytes += item.stat().st_size
                if cache_bytes > CAP:
                    raise ValueError("G156_CACHE_EXCEEDS_2GIB")
        if not cache_files or not cache_bytes:
            raise ValueError("G156_EMPTY_SEEDED_GO_CACHE")
    stable(data["source_sha"])
    receipt = {
        "schema": "forge.rar-g156.dynamic-main-go-cache.v1",
        "source_sha": data["source_sha"],
        "source_tree": data["source_tree"],
        "base_sha": data["base_source_sha"],
        "base_tree": data["base_source_tree"],
        "current_graph": data["source_graph_digest"],
        "base_graph": data["base_graph_digest"],
        "current_key": data["cache_key"],
        "base_key": data["derived_base_key"],
        "base_hit": hit,
        "base_cache_bytes": cache_bytes,
        "base_cache_files": cache_files,
        "original_go_commands_unchanged": True,
        "no_test_results_skipped_or_restored": True,
        "owner_and_science_untouched": True,
    }
    path = Path(os.environ["RUNNER_TEMP"]) / "rar-g156-dynamic-main-cache.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print("FORGE_RAR_G156=PASS_SOURCE_BOUND_OPTIONAL_COMPILER_SEED"
          + " base_hit=" + str(hit).lower()
          + " bytes=" + str(cache_bytes), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
