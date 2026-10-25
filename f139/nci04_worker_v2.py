"""G13: independently versioned *development-only* F139 signed-admission qualification.

This module is NOT the live V1 worker, V1 receipt format, controller or dispatcher.
A V2 result must never be interpreted as a V1 result or scientific first-use.
The authenticated original Git commit/tree and complete test-file inventory are
prerequisites, not exemptions from a full supported behavioral regression.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from f139.nci04_native_contract import Candidate, canonical, digest, require
from f139.nci04_native_worker import (
    _bounded_capture, _git, _inspect_checkout, stage_candidate,
)
from f139.nci04_signed_native import NativeAdmission

REPORT_SCHEMA = "forge.f139.nci04.native-development-diagnostic.v2"
RECEIPT_SCHEMA = "forge.f139.nci04.native-execution-receipt.v2"
SOURCE_SHA = "992ef142aaa551156749a1de484a971b9a0c092f"
SOURCE_TREE = "7e37c56e42dbd47a87da7a75210657a040f47a71"
EXPECTED_MODULES = frozenset({
    "test_code_atlas.py", "test_free_fanout_sidecar.py",
    "test_native_cells.py", "test_portable_checkpoint.py",
})
FROZEN_COUNTS = {
    "test_code_atlas.py": 4,
    "test_free_fanout_sidecar.py": 20,
    "test_native_cells.py": 8,
    "test_portable_checkpoint.py": 13,
}
SUPPORTED_OS = ("ubuntu-latest", "windows-latest")
ATLAS = "test_code_atlas.py"
COMPILE = ("python", "-B", "-m", "compileall", "-q", "yggdrasil", "scripts")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
TEST_SUMMARY = re.compile(rb"\bRan\s+([0-9]+)\s+tests?\s+in\b")


def supported_modules(oslabel: str):
    require(oslabel in SUPPORTED_OS, "V2_OS_FORBIDDEN")
    skipped = ("test_free_fanout_sidecar.py",) if oslabel == "windows-latest" else ()
    supported = tuple(sorted(EXPECTED_MODULES - {ATLAS} - set(skipped)))
    require(len(supported) == (2 if skipped else 3), "V2_MODULE_SET_INVALID")
    return supported, skipped


def unit_argv(module: str):
    require(module in EXPECTED_MODULES, "V2_MODULE_FORBIDDEN")
    return ("python", "-B", "-m", "unittest", "discover", "-s", "tests",
            "-p", module, "-v")


def _original_source(candidate: Candidate, original: Path):
    require(isinstance(candidate, Candidate) and candidate.lane == "Yggdrasil"
            and candidate.target_commit == SOURCE_SHA
            and candidate.target_tree_sha == SOURCE_TREE
            and candidate.path == "yggdrasil/public_causal_cells.py",
            "V2_FROZEN_ORIGINAL_IDENTITY_MISMATCH")
    original = _inspect_checkout(original, candidate)
    require(_git(original, "rev-parse", "--is-shallow-repository") == "false",
            "V2_COMPLETE_ANCESTRY_REQUIRED")
    tracked = _git(original, "ls-tree", "-r", "--name-only", "HEAD", "tests").splitlines()
    test_names = {
        item.removeprefix("tests/") for item in tracked
        if re.fullmatch(r"tests/test_[A-Za-z0-9_]+\.py", item)
    }
    actual = {p.name for p in (original / "tests").glob("test_*.py")}
    require(test_names == EXPECTED_MODULES and actual == EXPECTED_MODULES,
            "V2_ORIGINAL_TEST_INVENTORY_DRIFT")
    return original


def _child_env():
    allow = {"PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR",
             "SYSTEMDRIVE", "PATHEXT", "COMSPEC", "TMP", "TEMP", "TMPDIR",
             "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL", "GOPATH",
             "GOROOT", "GOCACHE", "GOMODCACHE", "CGO_ENABLED", "PYTHONPATH"}
    env = {k: v for k, v in os.environ.items() if k.upper() in allow}
    env.update({"GIT_TERMINAL_PROMPT": "0", "GOPROXY": "off",
                "GOSUMDB": "off", "GOTOOLCHAIN": "local",
                "PYTHONDONTWRITEBYTECODE": "1"})
    return env


def _command(argv, root: Path, runner=None):
    started = time.monotonic()
    if runner is None:
        output, returncode, status = _bounded_capture(
            argv, cwd=root, env=_child_env(), timeout_seconds=120)
    else:
        proc = runner(list(argv), cwd=root, env=_child_env(),
                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                      stdin=subprocess.DEVNULL, check=False, timeout=120)
        output, returncode = proc.stdout or b"", proc.returncode
        status = "PASS" if returncode == 0 else "TEST_FAILURE"
    require(isinstance(output, bytes) and len(output) <= 1_000_000,
            "V2_CHILD_OUTPUT_INVALID")
    if status in ("OUTPUT_LIMIT", "ORPHANED_OUTPUT"):
        status, returncode = "TEST_FAILURE", 1
    require(status in ("PASS", "TEST_FAILURE", "TIMEOUT")
            and type(returncode) is int, "V2_CHILD_STATUS_INVALID")
    module = argv[argv.index("-p") + 1] if "-p" in argv else None
    summary = TEST_SUMMARY.findall(output) if module else ()
    count = int(summary[-1]) if summary else None
    if module and (count is None or count != FROZEN_COUNTS[module]):
        status, returncode = "TEST_FAILURE", 1
    if status == "TEST_FAILURE" and returncode <= 0:
        returncode = 1
    if status == "TIMEOUT":
        returncode = -1
    return {
        "argv": list(argv), "outcome": status, "returncode": returncode,
        "test_count": count,
        "output_sha256": digest(output),
        "output_bytes": len(output),
        "elapsed_ms": int((time.monotonic() - started) * 1000),
    }


def run_v2(candidate: Candidate, original: Path, scratch: Path, *,
           oslabel: str, runner=None):
    """Source atlas on pristine original; exhaustive supported tests on dirty staged copy.

    This is a DEV probe only, not a V1 workflow entrypoint or replay facility.
    """
    modules, unsupported = supported_modules(oslabel)
    require((os.name == "nt") == (oslabel == "windows-latest"),
            "V2_ACTUAL_RUNNER_OS_DRIFT")
    original = _original_source(candidate, Path(original))
    require(Path(scratch).is_dir() and not Path(scratch).is_symlink(),
            "V2_SCRATCH_INVALID")
    pristine = _command(unit_argv(ATLAS), original, runner=runner)
    behavioral = []
    build = None
    stage = None
    try:
        if pristine["outcome"] == "PASS":
            stage = stage_candidate(candidate, original, Path(scratch))
            checkout = stage / "checkout"
            require(_git(checkout, "rev-parse", "HEAD") == SOURCE_SHA
                    and _git(checkout, "remote") == ""
                    and _git(checkout, "status", "--porcelain",
                             "--untracked-files=all") == "M " + candidate.path,
                    "V2_CANDIDATE_STAGE_IDENTITY_DRIFT")
            for module in modules:
                outcome = _command(unit_argv(module), checkout, runner=runner)
                behavioral.append(outcome)
                if outcome["outcome"] != "PASS":
                    break
            if len(behavioral) == len(modules) and all(
                    e["outcome"] == "PASS" for e in behavioral):
                build = _command(COMPILE, checkout, runner=runner)
    finally:
        if stage is not None:
            import shutil
            import stat
            def readonly_git_file(function, path, exc):
                # Windows marks Git pack/index objects read-only. A chmod on
                # just the failed disposable path is permitted; a locked file
                # still raises and the result is never declared qualified.
                if not isinstance(exc[1], PermissionError):
                    raise exc[1]
                os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
                function(path)
            shutil.rmtree(stage, onerror=readonly_git_file if os.name == "nt" else None)
    completed = (pristine["outcome"] == "PASS" and len(behavioral) == len(modules)
                 and all(x["outcome"] == "PASS" for x in behavioral)
                 and build is not None and build["outcome"] == "PASS")
    report = {
        "schema": REPORT_SCHEMA,
        "intent_sha256": candidate.intent_sha256,
        "qualification_key": candidate.qualification_key,
        "target_commit": candidate.target_commit,
        "target_tree_sha": candidate.target_tree_sha,
        "candidate_path": candidate.path,
        "candidate_sha256": candidate.after_sha256,
        "os": oslabel,
        "complete_git_ancestry": True,
        "original_tracked_test_modules": sorted(EXPECTED_MODULES),
        "pristine_source_atlas": pristine,
        "supported_behavior_modules": list(modules),
        "explicit_unsupported_modules": list(unsupported),
        "candidate_behavior": behavioral,
        "candidate_compile": build,
        "qualification_complete": completed,
        "development_only": True,
        "scientific_first_use": False,
        "protected_holdouts_accessed": 0,
        "accepted_ref_mutations": 0,
        "paid_model_calls": 0,
    }
    validate_v2(candidate, report)
    return report


def _valid_result(value, argv, expected_count):
    if not isinstance(value, dict) or set(value) != {
            "argv", "outcome", "returncode", "test_count",
            "output_sha256", "output_bytes", "elapsed_ms"}:
        return False
    outcome, ret, n = value["outcome"], value["returncode"], value["test_count"]
    return (value["argv"] == list(argv) and outcome in (
        "PASS", "TEST_FAILURE", "TIMEOUT")
        and type(ret) is int
        and ((outcome == "PASS" and ret == 0)
             or (outcome == "TEST_FAILURE" and ret > 0)
             or (outcome == "TIMEOUT" and ret == -1))
        and (n is None if expected_count is None else
             (n == expected_count if outcome == "PASS" else
              (n is None or (type(n) is int and n >= 0))))
        and isinstance(value["output_sha256"], str)
        and SHA256.fullmatch(value["output_sha256"]) is not None
        and type(value["output_bytes"]) is int and 0 <= value["output_bytes"] <= 1_000_000
        and type(value["elapsed_ms"]) is int and value["elapsed_ms"] >= 0)


def validate_v2(candidate: Candidate, r: dict):
    """Rigid V2 layout/sequence; an incomplete or altered suite can never pass."""
    require(isinstance(candidate, Candidate) and isinstance(r, dict)
            and set(r) == {
                "schema", "intent_sha256", "qualification_key",
                "target_commit", "target_tree_sha", "candidate_path", "candidate_sha256",
                "os", "complete_git_ancestry", "original_tracked_test_modules",
                "pristine_source_atlas", "supported_behavior_modules",
                "explicit_unsupported_modules", "candidate_behavior",
                "candidate_compile", "qualification_complete", "development_only",
                "scientific_first_use", "protected_holdouts_accessed",
                "accepted_ref_mutations", "paid_model_calls"},
            "V2_REPORT_FIELDS_INVALID")
    modules, unsupported = supported_modules(r["os"])
    require(r["schema"] == REPORT_SCHEMA and r["intent_sha256"] == candidate.intent_sha256
            and r["qualification_key"] == candidate.qualification_key
            and r["target_commit"] == SOURCE_SHA == candidate.target_commit
            and r["target_tree_sha"] == SOURCE_TREE == candidate.target_tree_sha
            and r["candidate_path"] == candidate.path == "yggdrasil/public_causal_cells.py"
            and r["candidate_sha256"] == candidate.after_sha256
            and r["complete_git_ancestry"] is True
            and r["original_tracked_test_modules"] == sorted(EXPECTED_MODULES)
            and r["supported_behavior_modules"] == list(modules)
            and r["explicit_unsupported_modules"] == list(unsupported)
            and r["development_only"] is True and r["scientific_first_use"] is False
            and type(r["protected_holdouts_accessed"]) is int
            and r["protected_holdouts_accessed"] == 0
            and type(r["accepted_ref_mutations"]) is int
            and r["accepted_ref_mutations"] == 0
            and type(r["paid_model_calls"]) is int and r["paid_model_calls"] == 0,
            "V2_REPORT_AUTHORITY_OR_IDENTITY_INVALID")
    src = r["pristine_source_atlas"]
    require(_valid_result(src, unit_argv(ATLAS), FROZEN_COUNTS[ATLAS]),
            "V2_SOURCE_INTEGRITY_EVIDENCE_INVALID")
    rows = r["candidate_behavior"]
    require(isinstance(rows, list) and len(rows) <= len(modules),
            "V2_BEHAVIOR_LENGTH_INVALID")
    for row, module in zip(rows, modules):
        require(_valid_result(row, unit_argv(module), FROZEN_COUNTS[module]),
                "V2_BEHAVIOR_EVIDENCE_INVALID")
    build = r["candidate_compile"]
    require(build is None or _valid_result(build, COMPILE, None),
            "V2_COMPILE_EVIDENCE_INVALID")
    if src["outcome"] != "PASS":
        require(not rows and build is None, "V2_SOURCE_FAILURE_BYPASSED")
    if any(row["outcome"] != "PASS" for row in rows):
        require(rows[-1]["outcome"] != "PASS" and build is None,
                "V2_BEHAVIOR_FAILURE_BYPASSED")
    if build is not None:
        require(src["outcome"] == "PASS" and len(rows) == len(modules)
                and all(row["outcome"] == "PASS" for row in rows),
                "V2_INCOMPLETE_SUITE_COMPILED")
    qualified = (src["outcome"] == "PASS"
                 and len(rows) == len(modules)
                 and all(row["outcome"] == "PASS" for row in rows)
                 and build is not None and build["outcome"] == "PASS")
    require(type(r["qualification_complete"]) is bool
            and r["qualification_complete"] is qualified, "V2_FALSE_QUALIFICATION")
    require(len(canonical(r)) <= 64_000, "V2_REPORT_OVERSIZE")
    return qualified


def receipt_v2(admission: NativeAdmission, report: dict):
    """Bound to the existing independently authenticated signed admission.

    SHA256 is a digest, not a new MAC: trust still depends on original signer,
    source-bound provider artifact integrity and original ledger custody.
    """
    require(isinstance(admission, NativeAdmission), "V2_SIGNED_ADMISSION_REQUIRED")
    c = admission.intent
    require(c.lane == "Yggdrasil" and admission.runner_os in SUPPORTED_OS
            and admission.runner_os == report.get("os")
            and admission.lane == c.lane
            and type(admission.issue_number) is int and admission.issue_number > 0
            and type(admission.issue_id) is int and admission.issue_id > 0
            and isinstance(admission.source_sha, str)
            and re.fullmatch(r"[a-f0-9]{40}", admission.source_sha) is not None
            and admission.ticket == ("f139-nci04-i"+str(admission.issue_number)+"-"
                 +admission.source_sha[:12]+"-"+c.intent_sha256[:8])
            and isinstance(admission.authorization_sha256, str)
            and SHA256.fullmatch(admission.authorization_sha256) is not None
            and type(admission.run_id) is int and admission.run_id > 0,
            "V2_ADMISSION_BINDING_INVALID")
    qualified = validate_v2(c, report)
    return {
        "schema": RECEIPT_SCHEMA,
        "ticket": admission.ticket,
        "source_sha": admission.source_sha,
        "run_id": admission.run_id,
        "os": admission.runner_os,
        "original_signed_admission_sha256": admission.authorization_sha256,
        "native_intent_sha256": c.intent_sha256,
        "qualification_key": c.qualification_key,
        "v2_report_sha256": digest(canonical(report)),
        "native_qualified": qualified,
        "development_only": True,
        "scientific_first_use_authorized": False,
        "accepted_ref_mutations": 0,
        "paid_model_calls": 0,
    }
