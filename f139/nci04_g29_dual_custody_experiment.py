"""F139 G29 dual-custody research gate. Not called by the live V19 worker.

Independent frozen-baseline source-atlas/full-suite qualification + isolated
candidate-only applicable tests. A FAIL of modified-source G29 is *expected*
and remains recorded as a negative, never misrepresented as a native PASS.
No native worker protocol changes, retries, source writes or promotions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

BASE = "021423311027517c9096c76bed7d35ac53c4a229"
BASE_TREE = "93620bd8e46bfbae1dbcd8e4ce397e27044de4f1"
HEAD = "339276862e42a067344990dc20d907f203009b90"
HEAD_TREE = "de431210951f1f0e79e447a532914cdfa431d25f"
TARGET = "yggdrasil/public_causal_cells.py"
ATLAS = "test_code_atlas.py"
TEST_PATTERN = re.compile(r"test_[A-Za-z0-9_]+\.py\Z")
SOURCE = "0743ca22b76ebd943a66f05a36ea919301676be0"
MAX_OUTPUT = 1_000_000


def require(value, reason):
    if not value:
        raise RuntimeError("F139_G29_DUAL_CUSTODY_" + reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *args):
    p = subprocess.run(["git", "-C", str(root), *args], stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=35, check=False)
    require(p.returncode == 0 and len(p.stdout) < 32768, "GIT_READ_FAILED")
    return p.stdout.decode("utf-8").strip()


def check_clean(root, commit, tree):
    require(root.is_dir() and not root.is_symlink(), "SOURCE_ROOT_INVALID")
    require(git(root, "rev-parse", "HEAD") == commit, "COMMIT_IDENTITY_DRIFT")
    require(git(root, "rev-parse", "HEAD^{tree}") == tree, "TREE_IDENTITY_DRIFT")
    require(git(root, "status", "--porcelain", "--untracked-files=all") == "",
            "SOURCE_CHECKOUT_DIRTY")
    require(Path(git(root, "rev-parse", "--show-toplevel")).resolve() == root.resolve(),
            "SOURCE_ROOT_NOT_TOPLEVEL")
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d != ".git"]
        require(all(not (Path(current) / p).is_symlink() for p in dirs + files),
                "SOURCE_SYMLINK_REJECTED")


def candidate_only_delta(root, before, after):
    require(root.is_dir() and git(root, "remote") == "", "SANDBOX_REMOTE_OR_ROOT")
    require(git(root, "rev-parse", "HEAD") == BASE, "SANDBOX_BASE_DRIFT")
    require(git(root, "rev-parse", "HEAD^{tree}") == BASE_TREE,
            "SANDBOX_TREE_DRIFT")
    require(git(root, "diff", "--name-only") == TARGET,
            "SECOND_OR_MISSING_CANDIDATE_DELTA")
    file = root / TARGET
    require(file.is_file() and not file.is_symlink() and sha(file.read_bytes()) == after,
            "CANDIDATE_POSTIMAGE_HASH_DRIFT")
    require(sha(git_bytes(root, "HEAD:" + TARGET)) == before,
            "CANDIDATE_PREIMAGE_HASH_DRIFT")


def git_bytes(root, object_name):
    p = subprocess.run(["git", "-C", str(root), "show", object_name],
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, check=False, timeout=30)
    require(p.returncode == 0 and len(p.stdout) <= 10_000_000, "BLOB_READ_FAILED")
    return p.stdout


def fixed_run(root, args, *, expect_atlas_negative=False, max_seconds=210):
    # Only known Python interpreter and unittest/compileall are executable.
    require(args and args[0] == sys.executable
            and len(args) >= 4 and args[1:4] == ["-B", "-m", "unittest"]
            or args[:4] == [sys.executable, "-B", "-m", "compileall"],
            "COMMAND_INVENTORY_NOT_FIXED")
    whitelist = {"PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR",
                 "SYSTEMDRIVE", "PATHEXT", "COMSPEC", "TMP", "TEMP", "TMPDIR",
                 "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL"}
    env = {k: v for k, v in os.environ.items() if k.upper() in whitelist}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "GIT_TERMINAL_PROMPT": "0",
                "GOPROXY": "off", "GOSUMDB": "off", "GOTOOLCHAIN": "local"})
    t = time.monotonic()
    p = subprocess.run(args, cwd=root, env=env, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=max_seconds, check=False)
    output = p.stdout
    require(len(output) <= MAX_OUTPUT, "REGRESSION_OUTPUT_OVERSIZED")
    counts = re.findall(rb"Ran\s+(\d+)\s+tests?\b", output)
    unittest = args[3] == "unittest"
    count = int(counts[-1]) if counts else 0
    if unittest:
        require(count > 0, "ZERO_DISCOVERED_TESTS")
    negative = (p.returncode != 0 and
                b"working source mismatch: " + TARGET.encode() in output)
    passed = negative if expect_atlas_negative else p.returncode == 0
    return {"argv": args[1:], "exit_code": p.returncode, "test_count": count,
            "elapsed_ms": int((time.monotonic() - t) * 1000),
            "output_sha256": sha(output), "output_bytes": len(output),
            "output_tail": output[-2500:].decode("utf-8", errors="replace"),
            "status": ("EXPECTED_FROZEN_ATLAS_REJECTION" if negative and expect_atlas_negative
                       else "PASS" if passed else "FAIL"),
            "peak_rss_bytes": None, "pass": passed}


def run_gate(base, head, output):
    require(base.resolve() != head.resolve(), "BASE_AND_HEAD_SAME_CHECKOUT")
    check_clean(base, BASE, BASE_TREE)
    check_clean(head, HEAD, HEAD_TREE)
    require(git(head, "rev-parse", "HEAD^") == BASE, "HEAD_PARENT_NOT_BASE")
    require(git(head, "diff", "--name-only", BASE, HEAD) == TARGET,
            "HEAD_NOT_EXACTLY_SINGLE_ALLOWED_SOURCE_DELTA")
    before = git_bytes(base, BASE + ":" + TARGET)
    after = git_bytes(head, HEAD + ":" + TARGET)
    require(0 < len(before) <= 32768 and 0 < len(after) <= 32768,
            "SOURCE_DELTA_SIZE_DENIED")
    require(before != after and sha(before) == sha((base / TARGET).read_bytes().replace(b"\r\n", b"\n"))
            and sha(after) == sha((head / TARGET).read_bytes().replace(b"\r\n", b"\n")),
            "SOURCE_BYTES_NOT_AUTHENTICATED")
    atlasfiles = (".ice/code-atlas.json", ".ice/code-atlas.html", ".ice/code-atlas.ice")
    for name in atlasfiles:
        require((base / name).read_bytes().replace(b"\r\n", b"\n") ==
                git_bytes(base, BASE + ":" + name).replace(b"\r\n", b"\n"),
                "HISTORIC_G29_ATLAS_DRIFT")
    original_test_files = sorted(p.name for p in (base / "tests").iterdir()
                                 if p.is_file() and TEST_PATTERN.fullmatch(p.name))
    candidate_test_files = sorted(p.name for p in (head / "tests").iterdir()
                                if p.is_file() and TEST_PATTERN.fullmatch(p.name))
    require(original_test_files == candidate_test_files
            and len(original_test_files) >= 5
            and original_test_files.count(ATLAS) == 1,
            "FULL_TEST_INVENTORY_OR_ATLAS_DRIFT")
    assert original_test_files[0] == ATLAS
    report = {
        "schema": "forge.f139.v19.g29.dual-custody-experiment.v1",
        "controller_source_sha": SOURCE,
        "baseline_commit": BASE, "baseline_tree": BASE_TREE,
        "candidate_head": HEAD, "candidate_tree": HEAD_TREE,
        "path": TARGET, "before_sha256": sha(before), "after_sha256": sha(after),
        "source_diff_exact_one_file": True, "test_inventory": original_test_files,
        "frozen_atlas_maintained": True, "modified_candidate_full_regression_pass": False,
        "production_v19_worker_unchanged": True, "signed_provider_success": False,
        "scientific_first_use": False, "paid_api_calls": 0, "github_writes": 0,
        "worker_replay": False, "results": {}, "negative_controls": {},
        "resource_accounting": "timing_only; peak RSS unavailable"
    }
    def apply(label, command, cwd, *, negative=False):
        result = fixed_run(cwd, command, expect_atlas_negative=negative)
        report["results"][label] = result
        require(result["pass"], label.upper() + "_FAILED")
    try:
        # Frozen atlas retains its exact historical source/tree and must pass.
        apply("baseline_g29", [sys.executable, "-B", "-m", "unittest", "discover",
                               "-s", "tests", "-p", ATLAS, "-v"], base)
        apply("baseline_full", [sys.executable, "-B", "-m", "unittest", "discover",
                                "-s", "tests", "-p", "test_*.py", "-v"], base)
        with tempfile.TemporaryDirectory(prefix="f139-g29-dualcustody-") as tmp:
            clone = Path(tmp) / "checkout"
            c = subprocess.run(["git", "clone", "--no-local", "--no-checkout", "--quiet",
                                "--", str(base), str(clone)], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               check=False, timeout=100)
            require(c.returncode == 0, "LOCAL_SANDBOX_GIT_CLONE_FAILED")
            for argv in (["git", "-C", str(clone), "config", "core.autocrlf", "false"],
                         ["git", "-C", str(clone), "checkout", "--detach", BASE],
                         ["git", "-C", str(clone), "remote", "remove", "origin"]):
                c = subprocess.run(argv, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   check=False, timeout=45)
                require(c.returncode == 0, "SANDBOX_GIT_SETUP_FAILED")
            check_clean(clone, BASE, BASE_TREE)
            (clone / TARGET).write_bytes(after)
            candidate_only_delta(clone, sha(before), sha(after))
            # Required negatives: extra delta and incorrect expected candidate hash.
            second = clone / "tests/test_native_cells.py"
            old = second.read_bytes()
            try:
                second.write_bytes(old + b"\n# deliberate extra-file negative\n")
                try:
                    candidate_only_delta(clone, sha(before), sha(after))
                except RuntimeError as e:
                    report["negative_controls"]["second_source_delta_rejected"] = (
                        "SECOND_OR_MISSING_CANDIDATE_DELTA" in str(e))
                else:
                    report["negative_controls"]["second_source_delta_rejected"] = False
            finally:
                second.write_bytes(old)
            try:
                candidate_only_delta(clone, sha(before), "0" * 64)
            except RuntimeError as e:
                report["negative_controls"]["bad_candidate_digest_rejected"] = (
                    "CANDIDATE_POSTIMAGE_HASH_DRIFT" in str(e))
            else:
                report["negative_controls"]["bad_candidate_digest_rejected"] = False
            candidate_only_delta(clone, sha(before), sha(after))
            require(all(report["negative_controls"].values()), "NEGATIVE_CONTROLS_FAILED")
            # G29's original entire test still MUST FAIL on the deliberately modified
            # source and its failure is retained, never rewritten as success.
            apply("candidate_g29_negative", [sys.executable, "-B", "-m", "unittest",
                                              "discover", "-s", "tests",
                                              "-p", ATLAS, "-v"], clone, negative=True)
            # Every other exact test module from the ORIGINAL full inventory is
            # executed in the candidate workspace. No catch-all wildcard ignore.
            for filename in original_test_files:
                if filename == ATLAS:
                    continue
                apply("candidate_" + filename,
                      [sys.executable, "-B", "-m", "unittest", "discover",
                       "-s", "tests", "-p", filename, "-v"], clone)
            apply("candidate_compile", [sys.executable, "-B", "-m", "compileall",
                                        "-q", "yggdrasil", "scripts"], clone)
            candidate_only_delta(clone, sha(before), sha(after))
        report["baseline_g29_pass"] = True
        report["baseline_full_unmodified_regression_pass"] = True
        report["candidate_changed_source_applicable_tests_pass"] = True
        report["historical_modified_source_g29_negative"] = True
        report["experimental_split_complete"] = True
        print("F139_V19_G29_DUAL_CUSTODY_EXPERIMENT=PASS")
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as f:
            json.dump(report, f, sort_keys=True, separators=(",", ":"))
            f.write("\n")
        print("F139_V19_G29_EXPERIMENT_REPORT_SHA256=" + sha(output.read_bytes()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    a = parser.parse_args()
    run_gate(a.baseline.resolve(strict=True), a.candidate.resolve(strict=True),
             a.output)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as e:
        raise SystemExit("F139_V19_G29_EXPERIMENT_FAIL_CLOSED " + str(e)) from e
