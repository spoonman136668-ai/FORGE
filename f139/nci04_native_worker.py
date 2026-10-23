"""F139 NCI-04 candidate staging and fixed native verification.

Qualification-only entry point. NOT connected to F139 controller, issue intake,
production workflow or signed worker. Requires an independently authenticated
source-pinned checkout and no secrets in the worker environment.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time

from f139.nci04_native_contract import Candidate, NativeContractError, digest, parse_intent

MAX_CAPTURE_BYTES = 1_000_000
# The signed provider limits each command excerpt to 4096 UTF-8 bytes.
MAX_EXCERPT_BYTES = 4096
# No user text, issue contents or candidate code may select the command line.
COMMANDS = {
    "Wingless": (
        ("go", "test", "-count=1", "./cognition"),
        ("go", "vet", "./cognition"),
        ("go", "test", "-count=1", "./..."),  # one final full regression
        ("go", "build", "./..."),
    ),
    "Yggdrasil": (
        ("python", "-B", "-m", "unittest", "discover", "-s", "tests",
         "-p", "test_native_cells.py", "-v"),
        ("python", "-B", "-m", "unittest", "discover", "-s", "tests",
         "-p", "test_*.py", "-v"),  # one final full regression
        ("python", "-B", "-m", "compileall", "-q", "yggdrasil", "scripts"),
    ),
}


def require(ok, reason):
    if not ok:
        raise NativeContractError("F139_NCI04_" + reason)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        timeout=15, stdin=subprocess.DEVNULL)
    require(result.returncode == 0 and len(result.stdout) < 4096,
            "GIT_READ_FAILED")
    return result.stdout.decode("utf-8").strip()


def _inspect_checkout(checkout: Path, candidate: Candidate):
    require(not checkout.is_symlink(), "CHECKOUT_SYMLINK_REJECTED")
    checkout = checkout.resolve(strict=True)
    require(checkout.is_dir(), "CHECKOUT_MISSING")
    require(_git(checkout, "rev-parse", "--is-inside-work-tree") == "true",
            "CHECKOUT_NOT_GIT")
    require(_git(checkout, "rev-parse", "HEAD") == candidate.target_commit,
            "CHECKOUT_COMMIT_DRIFT")
    require(_git(checkout, "rev-parse", "HEAD^{tree}") == candidate.target_tree_sha,
            "CHECKOUT_TREE_DRIFT")
    require(_git(checkout, "status", "--porcelain", "--untracked-files=all") == "",
            "CHECKOUT_DIRTY")
    require(Path(_git(checkout, "rev-parse", "--show-toplevel")).resolve() == checkout,
            "CHECKOUT_NOT_EXACT_ROOT")
    # A copied symlink could escape the sandbox when the candidate file is
    # materialized or when native tests execute. A native checkout with
    # ambiguous paths is rejected, never blindly followed.
    for current, folders, files in os.walk(checkout, followlinks=False):
        folders[:] = [d for d in folders if d != ".git"]
        for entry in folders + files:
            require(not (Path(current) / entry).is_symlink(),
                    "CHECKOUT_SYMLINK_REJECTED")
    return checkout


def stage_candidate(candidate: Candidate, checkout: Path,
                    sandbox_parent: Path) -> Path:
    """Only write inside a fresh isolated snapshot; preserve original checkout."""
    require(isinstance(candidate, Candidate), "CANDIDATE_UNTRUSTED")
    source = _inspect_checkout(Path(checkout), candidate)
    sandbox_parent = Path(sandbox_parent).resolve(strict=True)
    require(sandbox_parent.is_dir() and sandbox_parent != source
            and sandbox_parent not in source.parents
            and source not in sandbox_parent.parents,
            "SANDBOX_NOT_DISJOINT")
    stage = Path(tempfile.mkdtemp(prefix="f139-nci04-", dir=sandbox_parent))
    try:
        # Disallow symlinks rather than letting copytree dereference unknown
        # providers or allowing a candidate to mutate outside the sandbox.
        root = stage / "checkout"
        if candidate.lane == "Yggdrasil":
            # The original Yggdrasil baseline regression binds its source
            # atlas to a Git commit. A bare file copy was falsely negative.
            # Clone only the independently verified local source commit into
            # a disjoint temporary Git repository, then discard all remotes
            # so the candidate cannot write back to the original checkout.
            result = subprocess.run(
                ["git", "clone", "--no-local", "--no-checkout", "--quiet",
                 "--", str(source), str(root)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL, timeout=90, check=False)
            require(result.returncode == 0, "SANDBOX_GIT_CLONE_FAILED")
            for command in (
                ["git", "-C", str(root), "checkout", "--detach",
                 candidate.target_commit],
                ["git", "-C", str(root), "remote", "remove", "origin"],
            ):
                result = subprocess.run(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL, timeout=40, check=False)
                require(result.returncode == 0,
                        "SANDBOX_GIT_HISTORY_ORIGIN_REJECTED")
            require(_git(root, "rev-parse", "HEAD") ==
                    candidate.target_commit, "SANDBOX_HEAD_IDENTITY_DRIFT")
            require(_git(root, "rev-parse", "HEAD^{tree}") ==
                    candidate.target_tree_sha, "SANDBOX_TREE_IDENTITY_DRIFT")
            require(_git(root, "remote") == "", "SANDBOX_REMOTE_NOT_REMOVED")
            # Reinspect to reject symlinks brought in by the clone.
            _inspect_checkout(root, candidate)
        else:
            shutil.copytree(
                source, root, ignore=shutil.ignore_patterns(".git"),
                symlinks=True, dirs_exist_ok=False)
        rel = Path(*candidate.path.split("/"))
        dest = root / rel
        require(dest.resolve(strict=False).is_relative_to(root.resolve())
                and not dest.is_symlink(), "TARGET_PATH_ESCAPE")
        before = dest.read_bytes() if dest.exists() else b""
        after = candidate.materialize_bytes(before)
        require(dest.is_file() or not dest.exists(), "TARGET_NOT_FILE")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as f:
            f.write(after)
            f.flush()
            os.fsync(f.fileno())
        require(digest(dest.read_bytes()) == candidate.after_sha256,
                "MATERIALIZED_BYTES_DRIFT")
        return stage
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _stop_native_tree(process):
    """Terminate fixed native test commands and inherited descendants.

    This is best-effort process-tree cleanup, NOT a full OS-job security
    sandbox; the worker must remain credential-free and separately isolated.
    """
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass


def _bounded_capture(argv, *, cwd, env, timeout_seconds):
    """Capture at most 1 MB without blocking on a descendant-held pipe.

    os.read returns available pipe bytes without waiting to fill 64 KiB.
    A new process group permits best-effort cleanup of native descendants.
    No untrusted argv, shell commands, credentials or native policy flags.
    """
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(list(argv), cwd=cwd, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL, creationflags=flags,
                               start_new_session=(os.name != "nt"))
    output = bytearray()
    over_limit = threading.Event()
    capture_errors = []

    def drain():
        try:
            while True:
                # BufferedIOBase.read(65536) could block while descendants
                # held stdout open, even if the parent already overproduced.
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    break
                remaining = MAX_CAPTURE_BYTES - len(output)
                if len(chunk) > remaining:
                    output.extend(chunk[:remaining])
                    over_limit.set()
                    _stop_native_tree(process)
                    break
                output.extend(chunk)
        except OSError as exc:
            if not over_limit.is_set():
                capture_errors.append(exc)
                _stop_native_tree(process)

    reader = threading.Thread(target=drain, name="f139-native-output", daemon=True)
    reader.start()
    timed_out = False
    try:
        returncode = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _stop_native_tree(process)
        returncode = process.wait(timeout=5)
    # A successful parent must not conceal native descendants still writing.
    reader.join(timeout=2)
    orphaned_output = reader.is_alive() and not timed_out and not over_limit.is_set()
    if reader.is_alive():
        _stop_native_tree(process)
        reader.join(timeout=5)
    if reader.is_alive() or capture_errors:
        raise NativeContractError("F139_NCI04_NATIVE_OUTPUT_READ_FAILED")
    process.stdout.close()
    if over_limit.is_set():
        return bytes(output), -1, "OUTPUT_LIMIT"
    if timed_out:
        return bytes(output), -1, "TIMEOUT"
    if orphaned_output:
        return bytes(output), -1, "ORPHANED_OUTPUT"
    return bytes(output), returncode, "PASS" if returncode == 0 else "TEST_FAILURE"


def verify_fixed_commands(candidate: Candidate, stage: Path, *,
                          runner=None, timeout_seconds=600):
    """Run the fixed focused/complete/build inventory with no shell commands.

    This function does NOT isolate network or OS process capabilities. It may
    run only in a separately isolated, credential-free native-development
    worker; it is intentionally not wired to the existing HMAC-bearing worker.
    """
    require(isinstance(candidate, Candidate), "CANDIDATE_UNTRUSTED")
    stage = Path(stage).resolve(strict=True)
    root = stage / "checkout"
    require(root.is_dir() and root.parent == stage, "STAGING_ROOT_INVALID")
    require(type(timeout_seconds) is int and 15 <= timeout_seconds <= 900,
            "TIMEOUT_NOT_BOUNDED")
    run = runner or subprocess.run
    # Positive allowlist, not a secret-name blacklist: signing keys, cloud
    # credentials, GitHub runner tokens and arbitrary inherited variables must
    # not cross from controller/test harness into candidate native subprocesses.
    allow = {"PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR",
             "SYSTEMDRIVE", "PATHEXT", "COMSPEC", "TMP", "TEMP", "TMPDIR",
             "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL", "GOPATH",
             "GOROOT", "GOCACHE", "GOMODCACHE", "CGO_ENABLED", "PYTHONPATH"}
    env = {k: v for k, v in os.environ.items() if k.upper() in allow}
    env.update({"GIT_TERMINAL_PROMPT": "0", "GOPROXY": "off",
                "GOSUMDB": "off", "GOTOOLCHAIN": "local", "PYTHONDONTWRITEBYTECODE": "1"})
    results = []
    for argv in COMMANDS[candidate.lane]:
        started = time.monotonic()
        try:
            if runner is None:
                output, returncode, outcome = _bounded_capture(
                    argv, cwd=root, env=env, timeout_seconds=timeout_seconds)
            else:
                # An injected test runner retains the prior fixed-command API.
                p = run(list(argv), cwd=root, env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL, check=False,
                        timeout=timeout_seconds)
                output = p.stdout or b""
                returncode = p.returncode
                outcome = "PASS" if returncode == 0 else "TEST_FAILURE"
                if len(output) > MAX_CAPTURE_BYTES:
                    output = output[:MAX_CAPTURE_BYTES]
                    returncode, outcome = -1, "OUTPUT_LIMIT"
        except subprocess.TimeoutExpired as ex:
            output = (ex.stdout or b"") if isinstance(ex.stdout, bytes) else b""
            output = output[:MAX_CAPTURE_BYTES]
            returncode = -1
            outcome = "TIMEOUT"
        require(isinstance(output, bytes), "CHILD_OUTPUT_INVALID")
        # The existing F139 provider receipt contract permits only PASS,
        # TEST_FAILURE (positive exit code), and TIMEOUT (-1). An internal
        # OUTPUT_LIMIT must become an explicitly annotated, schema-compatible
        # negative; otherwise the original failure cannot be custodied.
        diagnostic = ""
        if outcome == "OUTPUT_LIMIT":
            diagnostic = ("F139_NATIVE_OUTPUT_LIMIT: worker-generated "
                          "TEST_FAILURE/1; native child killed; first "
                          f"{MAX_CAPTURE_BYTES} bytes retained; tail unknown\n")
            outcome, returncode = "TEST_FAILURE", 1
        elif outcome == "ORPHANED_OUTPUT":
            diagnostic = ("F139_NATIVE_ORPHANED_STDOUT_PIPE: native parent "
                          "exited but descendants held the pipe; "
                          "worker-generated TEST_FAILURE/1; "
                          "process-tree cleanup attempted\n")
            outcome, returncode = "TEST_FAILURE", 1
        elif outcome == "TEST_FAILURE" and returncode <= 0:
            diagnostic = ("F139_NATIVE_ABNORMAL_EXIT: "
                          f"native_returncode={returncode}; worker-generated "
                          "TEST_FAILURE/1\n")
            returncode = 1
        if outcome == "TIMEOUT" and len(output) == MAX_CAPTURE_BYTES:
            diagnostic = "F139_NATIVE_TIMEOUT_CAPTURE_TRUNCATED\n"
        # unittest discover exits with status 0 even when its pattern matches
        # zero tests. The existing Yggdrasil main has no test_native_cells.py;
        # accepting that as a focused qualification would fabricate coverage.
        # Count only the native process's unmodified merged output. A missing,
        # ambiguous, or empty summary is a *negative*, with original bytes and
        # SHA256 preserved in the report. Do not substitute a mock success.
        if (candidate.lane == "Yggdrasil" and outcome == "PASS"
                and tuple(argv[:4]) == ("python", "-B", "-m", "unittest")):
            summaries = re.findall(rb"(?m)^Ran ([0-9]+) tests? in [0-9.]+s\s*$",
                                   output)
            if len(summaries) != 1 or int(summaries[0]) == 0:
                diagnostic = ("F139_YGGDRASIL_ZERO_OR_UNVERIFIED_TESTS: "
                              "native unittest reported no proven executed "
                              "tests; worker-generated TEST_FAILURE/1\n")
                outcome, returncode = "TEST_FAILURE", 1
        # Preserve the digest/byte count of actually captured native stdout;
        # annotate truncation in the excerpt, never forge a full-output hash.
        preview = (diagnostic + output[:MAX_EXCERPT_BYTES].decode(
            "utf-8", errors="replace")).encode("utf-8")[:MAX_EXCERPT_BYTES]
        excerpt = preview.decode("utf-8", errors="ignore")
        results.append({
            "command": list(argv), "outcome": outcome,
            "returncode": returncode,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "output_sha256": digest(output),
            "output_bytes": len(output),
            "excerpt": excerpt,
        })
        if outcome != "PASS":
            break
    return {
        "schema": "forge.f139.nci04.native-development-diagnostic.v1",
        "intent_sha256": candidate.intent_sha256,
        "qualification_key": candidate.qualification_key,
        "target_commit": candidate.target_commit,
        "target_tree_sha": candidate.target_tree_sha,
        "candidate_file": candidate.path,
        "candidate_sha256": candidate.after_sha256,
        "lane": candidate.lane,
        "qualification_complete": len(results) == len(COMMANDS[candidate.lane])
                                  and all(x["outcome"] == "PASS" for x in results),
        "real_code_changed_in_isolated_copy": True,
        "commands": results,
        "child_peak_rss_bytes": None,  # unknown; must not fabricate resource parity
        "scientific_first_use": False,
        "protected_holdouts_accessed": 0,
        "accepted_ref_mutations": 0,
        "paid_model_calls": 0,
        "durable_controller_custody_verified": False,
        "unattended_controller_dispatch_verified": False,
    }


def read_only_report_bytes(report: dict) -> bytes:
    return (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode()


def qualification_from_bytes(intent_raw: bytes, *, protected_main: str,
                             target_commit: str, target_tree_sha: str,
                             checkout: Path, sandbox_parent: Path):
    candidate = parse_intent(intent_raw, protected_main=protected_main,
                             target_commit=target_commit,
                             target_tree_sha=target_tree_sha)
    stage = stage_candidate(candidate, checkout, sandbox_parent)
    return candidate, stage, verify_fixed_commands(candidate, stage)
