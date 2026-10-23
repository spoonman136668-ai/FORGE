"""One Q21 source-free development evaluator, behind the existing CKB owner gate.

No import-side cohorts, no standalone hidden/protected roles, no admission from
local JSON/flags. Authenticates current protected main workflow_dispatch using
GitHub's own metadata and checks byte-identical pinned FORGE Git objects.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

# CKB's installed Python 3.12 is embedded/isolated; unlike unittest discovery,
# direct script invocation does not automatically add its own directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import admit_exact as owner


class Blocked(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise Blocked("Q21_DEV_" + reason)


def git(path: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(path), *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=35, check=False)
    require(result.returncode == 0, "GIT_IDENTITY_UNAVAILABLE")
    return result.stdout.strip()


def verify_source(path: Path) -> None:
    require(path.is_dir(), "SOURCE_NOT_CHECKED_OUT")
    require(git(path, "rev-parse", "HEAD") == owner.SOURCE, "SOURCE_COMMIT_DRIFT")
    require(git(path, "rev-parse", "HEAD^{tree}") == owner.TREE, "SOURCE_TREE_DRIFT")
    require(git(path, "rev-parse", "HEAD:research/q21_information_budget/FROZEN_PROTOCOL.json")
            == owner.PROTOCOL, "PREREG_BLOB_DRIFT")
    require(git(path, "status", "--porcelain", "--untracked-files=all") == "",
            "SOURCE_WORKTREE_DIRTY")


def authenticated_owner(env: dict, get) -> dict:
    admission = owner.admit(env, get)
    require(admission["decision"] == "OWNER_AUTHENTICATED_SOURCEFREE_DEVELOPMENT_ONLY"
            and admission["scientific_execution_performed"] is False,
            "OWNER_ADMISSION_NOT_EXACT")
    return admission


def native_os() -> str:
    if sys.platform == "win32":
        return "Windows"
    if sys.platform.startswith("linux"):
        return "Linux"
    raise Blocked("Q21_DEV_UNSUPPORTED_OPERATING_SYSTEM")


def sourcefree_import(source: Path):
    lib = str(source / "research" / "q21_information_budget")
    require(Path(lib).is_dir(), "CANDIDATE_LIBRARY_MISSING")
    sys.path.insert(0, lib)
    import sourcefree
    import sourcefree_runner
    import reconcile_runner
    return sourcefree, sourcefree_runner, reconcile_runner


def run(source: Path, output: Path, env: dict, get) -> dict:
    # Important ordering: attest real owner and full run history *before*
    # loading the Q21 cohort generator or drawing a single development bit.
    identity = authenticated_owner(env, get)
    verify_source(source)
    system = native_os()
    sourcefree, executor, _reconciler = sourcefree_import(source)
    protocol = sourcefree.protocol()
    require(sourcefree.PROTOCOL_BLOB == owner.PROTOCOL,
            "PROTOCOL_MATCH_NOT_EXACT")
    require(output.is_absolute() and not output.exists(),
            "OUTPUT_MUST_BE_NEW_ABSOLUTE_PATH")
    report = executor.execute_development(protocol)
    envelope = {
        "schema": "forge.q21.external-readonly-envelope.v1",
        "os_name": system,
        "candidate_source_sha": owner.SOURCE,
        "ckb_owner_run_id": identity["ckb_run_id"],
        "ckb_owner_source_sha": identity["ckb_source_sha"],
        "ckb_owner_scope": identity["scope"],
        "scientific_first_use": False,
        "runner_report": report,
    }
    # The original generator source is never amended. The envelope records
    # the full negative outcome as well as a positive one; write exclusively.
    raw = (json.dumps(envelope, sort_keys=True,
                      separators=(",", ":"), allow_nan=False) + "\n").encode()
    with output.open("xb") as fd:
        fd.write(raw)
    return {"os": system, "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "frozen_preliminary_decision": report["frozen_preliminary_decision"],
            "ckb_owner_run_id": identity["ckb_run_id"],
            "scientific_first_use": False}


def reconcile(source: Path, win: Path, lin: Path, out: Path) -> dict:
    verify_source(source)
    require(out.is_absolute() and not out.exists(), "RECONCILE_DESTINATION_EXISTS")
    data = []
    for filename, expected_os in ((win, "Windows"), (lin, "Linux")):
        require(filename.is_file(), "MISSING_REAL_NATIVE_RUN")
        envelope = json.loads(filename.read_text(encoding="utf-8"))
        require(envelope.get("os_name") == expected_os and
                envelope.get("candidate_source_sha") == owner.SOURCE and
                envelope.get("scientific_first_use") is False and
                envelope.get("ckb_owner_scope") == "FRESH_Q21_FIT_TRAIN_FIT_VALID_DEV_ONLY",
                "ENVELOPE_IDENTITY_DRIFT")
        data.append(envelope)
    require(data[0].get("ckb_owner_run_id") == data[1].get("ckb_owner_run_id") and
            isinstance(data[0].get("ckb_owner_run_id"), int),
            "DIFFERENT_OWNER_ADMISSIONS")
    require(data[0].get("ckb_owner_source_sha") ==
            data[1].get("ckb_owner_source_sha"),
            "DIFFERENT_CKB_AUTHORITY_SOURCE")
    # Reject invalid or mismatched owner receipts before Q21 model import.
    sourcefree, _executor, checker = sourcefree_import(source)
    decision = checker.compare(data[0], data[1], sourcefree.protocol())
    decision["ckb_owner_run_id"] = data[0]["ckb_owner_run_id"]
    decision["science_receipts_sha256"] = {
        "Windows": hashlib.sha256(win.read_bytes()).hexdigest(),
        "Linux": hashlib.sha256(lin.read_bytes()).hexdigest(),
    }
    raw = (json.dumps(decision, sort_keys=True,
                      separators=(",", ":"), allow_nan=False) + "\n").encode()
    with out.open("xb") as fd:
        fd.write(raw)
    return decision


def preflight() -> dict:
    return {"status": "Q21_CKB_TWO_OS_CONSUMER_SOURCE_READY",
            "development_cohorts_generated": 0,
            "protected_or_original_first_use": False,
            "no_network_or_model_calls": True,
            "owner_admission": "NOT_REQUESTED",
            "science_execution": "NOT_PERFORMED"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True,
                        choices=("preflight", "run", "reconcile"))
    parser.add_argument("--candidate")
    parser.add_argument("--output")
    parser.add_argument("--windows")
    parser.add_argument("--linux")
    args = parser.parse_args()
    if args.mode == "preflight":
        print(json.dumps(preflight(), sort_keys=True))
        return
    require(bool(args.candidate and args.output), "MISSING_SOURCE_OR_OUTPUT")
    source = Path(args.candidate).resolve()
    output = Path(args.output).resolve()
    if args.mode == "reconcile":
        require(bool(args.windows and args.linux), "MISSING_OS_RECEIPTS")
        result = reconcile(source, Path(args.windows), Path(args.linux), output)
    else:
        token = os.environ.get("GH_TOKEN", "")
        try:
            result = run(source, output, dict(os.environ),
                         lambda route: owner.github_get(token, route))
        except Exception as exc:
            # A failed attempt is also a scientific event. Preserve the
            # conservative possibility that prospective cohorts were drawn.
            # A successful owner admission cannot be replayed to salvage it.
            if output.is_absolute() and not output.exists():
                abort = {"schema":"ckb.q21.science-abort-receipt.v1",
                         "state":"ABORTED_ONE_SHOT_DO_NOT_RETRY",
                         "ckb_run_id":os.environ.get("GITHUB_RUN_ID"),
                         "candidate_source_sha":owner.SOURCE,
                         "possible_development_data_consumption":True,
                         "original_or_protected_data_access":False,
                         "exception_type":type(exc).__name__,
                         "failure_code":str(exc)[:180]}
                try:
                    with output.open("xb") as fd:
                        fd.write((json.dumps(abort,sort_keys=True)+"\n").encode())
                except OSError:
                    pass
            raise
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
