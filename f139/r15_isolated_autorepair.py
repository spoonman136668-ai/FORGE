"""R15: bounded, model-free replay of one already-qualified R14 repair.

SOURCE-ONLY hosted engineering rehearsal. No controller, protected-ref mutation,
paid API, scientific original, or reusable general-purpose repair authority.
An unrecognized preimage, candidate or observable failure aborts without repair.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

BASE = "536b91a392b7bbc50200a6e8842d152f2e23d8bb"
REPAIRED = "6068f39b5b85cdb4b7770e6700a72077636af679"
OLD_BLOB = "e2c2cfa30805ed79d9228e4ebd2737925676f16d"
NEW_BLOB = "c92d0002a2882bc171a66526da64f24962369847"
TEST_BLOB = "d8bfcbd88a71e7bd2cde827ab2cc90a9705c4a91"
WORKER = "f139/nci04_native_worker.py"
TEST = "f139/test_nci04_output_capture.py"

# Identical independent reproducer before and after the verified patch.
# The original fake-runner seam returned unlimited output. R14 must retain at
# most 1 MB and preserve schema-compatible negative failure evidence.
PROBE = r"""
import subprocess
from f139.nci04_native_worker import MAX_CAPTURE_BYTES, stage_candidate, verify_fixed_commands
from f139.test_nci04_native_worker import NativeWorkerTests
f=NativeWorkerTests("test_only_fixed_commands_no_secrets_and_full_regression")
f.setUp()
try:
    stage=stage_candidate(f.intent(), f.repo, f.sandbox)
    def produce(argv, **kw):
        return subprocess.CompletedProcess(argv, 0, b'Q'*(MAX_CAPTURE_BYTES+101))
    report=verify_fixed_commands(f.intent(),stage,runner=produce)
    record=report["commands"][0]
    print("R15_OBSERVED_BYTES="+str(record["output_bytes"]))
    print("R15_OBSERVED_OUTCOME="+record["outcome"])
    print("R15_OBSERVED_QUALIFIED="+str(report["qualification_complete"]))
finally:
    f.doCleanups()
"""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError("R15_" + reason)


def run(argv: list[str], *, cwd: Path | None = None, timeout: int = 120) -> bytes:
    result = subprocess.run(argv, cwd=cwd, check=False, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            timeout=timeout)
    need(result.returncode == 0,
         "PROCESS_FAILED: " + repr(argv[:3]) + ": " +
         result.stdout[-1200:].decode("utf-8", "replace"))
    return result.stdout


def git(root: Path, *args: str) -> str:
    return run(["git", "-C", str(root), *args], timeout=30).decode().strip()


def inspect(root: Path, commit: str) -> None:
    need(root.is_dir() and not root.is_symlink(), "SOURCE_PATH_UNTRUSTED")
    need(git(root, "rev-parse", "HEAD") == commit, "SOURCE_COMMIT_DRIFT")
    need(git(root, "status", "--porcelain", "--untracked-files=all") == "",
         "SOURCE_CHECKOUT_DIRTY")


def probe(root: Path, *, expect_repair: bool) -> None:
    output = run([sys.executable, "-B", "-c", PROBE], cwd=root, timeout=40)
    observed = output.decode("utf-8", "replace").strip()
    if expect_repair:
        need(("R15_OBSERVED_BYTES=1000000" in observed and
              "R15_OBSERVED_OUTCOME=TEST_FAILURE" in observed and
              "R15_OBSERVED_QUALIFIED=False" in observed),
             "KNOWN_FAILURE_NOT_REPAIRED: " + observed)
        print("R15_AUTOMATED_KNOWN_REPAIR=PASS")
    else:
        need(("R15_OBSERVED_BYTES=1000101" in observed and
              "R15_OBSERVED_OUTCOME=PASS" in observed and
              "R15_OBSERVED_QUALIFIED=True" in observed),
             "FROZEN_FAILURE_NOT_REPRODUCED: " + observed)
        print("R15_ORIGINAL_UNBOUNDED_FAILURE=REPRODUCED")


def main() -> None:
    need(len(sys.argv) == 3, "TWO_SOURCE_PATHS_REQUIRED")
    original, repaired = (Path(s).resolve(strict=True) for s in sys.argv[1:])
    need(original != repaired and original not in repaired.parents and
         repaired not in original.parents, "SOURCES_NOT_DISJOINT")
    inspect(original, BASE)
    inspect(repaired, REPAIRED)
    need(git(original, "hash-object", WORKER) == OLD_BLOB, "OLD_BLOB_DRIFT")
    need(git(repaired, "hash-object", WORKER) == NEW_BLOB, "REPAIR_BLOB_DRIFT")
    need(git(repaired, "hash-object", TEST) == TEST_BLOB, "TEST_BLOB_DRIFT")
    git(repaired, "merge-base", "--is-ancestor", BASE, REPAIRED)
    probe(original, expect_repair=False)

    with tempfile.TemporaryDirectory(prefix="forge-r15-offline-repair-") as temporary:
        sandbox = Path(temporary) / "checkout"
        run(["git", "clone", "--quiet", "--no-hardlinks", str(original),
             str(sandbox)], timeout=90)
        run(["git", "-C", str(sandbox), "checkout", "--quiet",
             "--detach", BASE], timeout=30)
        inspect(sandbox, BASE)
        patch = run(["git", "-C", str(repaired), "diff", "--binary",
                     BASE, REPAIRED, "--", WORKER, TEST], timeout=40)
        need(1000 < len(patch) < 50000 and
             b"diff --git a/f139/nci04_native_worker.py" in patch and
             b"diff --git a/f139/test_nci04_output_capture.py" in patch,
             "R14_PATCH_SCOPE_DRIFT")
        patchfile = Path(temporary) / "r14.patch"
        patchfile.write_bytes(patch)
        run(["git", "-C", str(sandbox), "apply", "--check",
             str(patchfile)], timeout=30)
        run(["git", "-C", str(sandbox), "apply", str(patchfile)], timeout=30)
        need(git(sandbox, "hash-object", WORKER) == NEW_BLOB and
             git(sandbox, "hash-object", TEST) == TEST_BLOB,
             "ISOLATED_REPAIR_RESULT_DIFFERS")
        probe(sandbox, expect_repair=True)
        print("R15_REPAIR_PATCH_SHA256=" + hashlib.sha256(patch).hexdigest())
        print("R15_ISOLATED_REPAIR_FILES=2")
        print("R15_VERIFIED_CODE_IDENTITIES=PASS")

        # This suite verifies the genuine signed-native negative receipt schema.
        focused = run([sys.executable, "-B", "-m", "unittest", "-v",
                       "f139.test_nci04_native_worker",
                       "f139.test_nci04_output_capture"],
                      cwd=sandbox, timeout=180)
        print(focused.decode("utf-8", "replace").splitlines()[-3:])
        print("R15_FOCUSED_NATIVE_WORKER=PASS")
        regression = run([sys.executable, "-B", "-m", "unittest",
                          "discover", "-s", "f139", "-p", "test_nci04*.py", "-v"],
                         cwd=sandbox, timeout=240)
        print(regression.decode("utf-8", "replace").splitlines()[-3:])
        print("R15_FULL_AFFECTED_REGRESSION=PASS")
    inspect(original, BASE)
    inspect(repaired, REPAIRED)
    print("R15_BOTH_ORIGINAL_SOURCES_UNMODIFIED=PASS")
    print("R15_CONTROLLER_RESTARTS=0")
    print("R15_SCIENTIFIC_FIRST_USE=FALSE")
    print("R15_AUTONOMOUS_GENERAL_REPAIR=NOT_PROVEN")


if __name__ == "__main__":
    main()
