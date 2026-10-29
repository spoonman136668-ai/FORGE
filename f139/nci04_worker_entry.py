"""F139 NCI04-A6 split credentialed authorization and credential-free native execution.

The authorize command never executes native code. Execute cannot read any
F139 signing secret and runs only a fixed focused/full/build inventory.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from f139.nci04_native_contract import canonical, digest, parse_intent
from f139.nci04_native_worker import stage_candidate, verify_fixed_commands, read_only_report_bytes
from f139.nci04_signed_native import NativeAdmission, admit_native_intent, receipt_from_report, Untrusted
from f139.verify_ticket import inputs_from_env

SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class NativeWorkerBlocked(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise NativeWorkerBlocked("F139_NCI04_A6_" + reason)


def intent_raw():
    encoded = os.environ.get("F139_INTENT_BASE64", "")
    require(0 < len(encoded) < 59000, "INTENT_NOT_BOUNDED")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, UnicodeError) as exc:
        raise NativeWorkerBlocked("F139_NCI04_A6_INTENT_NOT_BASE64") from exc
    require(base64.b64encode(raw).decode("ascii") == encoded, "INTENT_NONCANONICAL")
    return raw


def common_source():
    env = os.environ
    source = env.get("F139_SOURCE_SHA")
    require(isinstance(source, str) and SHA40.fullmatch(source) is not None
            and env.get("GITHUB_SHA") == source
            and env.get("GITHUB_REF") in (
                "refs/heads/main",
                "refs/heads/f139-owner-release-"+source)
            and env.get("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE"
            and env.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
            and env.get("GITHUB_RUN_ATTEMPT") == "1"
            and re.fullmatch(r"[1-9][0-9]*", env.get("GITHUB_RUN_ID", "")) is not None,
            "GITHUB_SOURCE_OR_EVENT_DRIFT")
    return source


def issue_args():
    env = os.environ
    return {
        "issue_number": env.get("F139_ISSUE_NUMBER", ""),
        "issue_id": env.get("F139_ISSUE_ID", ""),
        "issue_body_sha256": env.get("F139_BODY_SHA256", ""),
    }


def native_provider_pin():
    env = os.environ
    commit = env.get("F139_TARGET_COMMIT", "")
    tree = env.get("F139_TARGET_TREE_SHA", "")
    require(SHA40.fullmatch(commit) is not None
            and SHA40.fullmatch(tree) is not None,
            "NATIVE_TARGET_IDENTITY_INVALID")
    return commit, tree


def authorize():
    source = common_source()
    inp = inputs_from_env()
    raw = intent_raw()
    commit, tree = native_provider_pin()
    real_tree = os.environ.get("F139_AUTHENTICATED_TARGET_TREE", "")
    require(real_tree == tree, "TARGET_PROVIDER_TREE_DRIFT")
    record = admit_native_intent(
        inp, raw, native_signature=os.environ.get("F139_NATIVE_SIGNATURE", ""),
        authenticated_main_sha=source,
        authenticated_target_commit=commit,
        authenticated_target_tree=real_tree, **issue_args())
    require(record.intent.qualification_key ==
            os.environ.get("F139_QUALIFICATION_KEY", ""),
            "QUALIFICATION_KEY_DRIFT")
    return {
        "schema": "forge.f139.nci04.native-authorized-job.v1",
        "authorization_sha256": record.authorization_sha256,
        "native_intent_sha256": record.intent.intent_sha256,
        "native_target_tree": tree, "source_sha": source,
        "scientific_first_use": False,
    }


def git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(root), *args],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       check=False, timeout=15, stdin=subprocess.DEVNULL)
    require(p.returncode == 0 and len(p.stdout) < 2048,
            "READONLY_GIT_SOURCE_FAILED")
    return p.stdout.decode("ascii").strip()


def execute(native_root: Path, scratch: Path, output: Path):
    source = common_source()
    require(not any(os.environ.get(k) for k in (
        "F139_WORKER_HMAC_KEY", "GH_TOKEN", "GITHUB_TOKEN",
        "OPENAI_API_KEY", "CLOUDFLARE_API_TOKEN")),
        "WORKER_CREDENTIAL_INHERITANCE")
    require(os.environ.get("F139_NATIVE_AUTHENTICATION_PASSED") == "true",
            "NATIVE_AUTH_JOB_NOT_SUCCESS")
    auth_sha = os.environ.get("F139_NATIVE_AUTHORIZATION_SHA256", "")
    require(SHA64.fullmatch(auth_sha) is not None,
            "AUTHENTICATION_BINDING_ABSENT")
    commit, tree = native_provider_pin()
    root = native_root.resolve(strict=True)
    require(root.is_dir() and git(root, "rev-parse", "HEAD") == commit
            and git(root, "rev-parse", "HEAD^{tree}") == tree,
            "NATIVE_CHECKOUT_COMMIT_TREE_MISMATCH")
    candidate = parse_intent(intent_raw(), protected_main=source,
                             target_commit=commit, target_tree_sha=tree)
    require(candidate.qualification_key ==
            os.environ.get("F139_QUALIFICATION_KEY", ""),
            "NATIVE_QUALIFICATION_KEY_DRIFT")
    require(candidate.lane == os.environ.get("F139_LANE"),
            "NATIVE_LANE_DRIFT")
    num, ident = os.environ.get("F139_ISSUE_NUMBER", ""), os.environ.get("F139_ISSUE_ID", "")
    require(re.fullmatch(r"[1-9][0-9]*", num) is not None
            and re.fullmatch(r"[1-9][0-9]*", ident) is not None,
            "NATIVE_ISSUE_DRIFT")
    require(os.environ.get("F139_TICKET") ==
            "f139-nci04-i"+num+"-"+source[:12]+"-"+candidate.intent_sha256[:8],
            "NATIVE_TICKET_DRIFT")
    oslabel = os.environ.get("F139_RUNNER_OS", "")
    require(oslabel in ("ubuntu-latest", "windows-latest"), "RUNNER_OS_DRIFT")
    admission = NativeAdmission(
        ticket=os.environ["F139_TICKET"], lane=candidate.lane,
        source_sha=source, run_id=int(os.environ["GITHUB_RUN_ID"]),
        runner_os=oslabel, issue_number=int(num), issue_id=int(ident),
        intent=candidate, authorization_sha256=auth_sha)
    require(scratch.is_dir() and not scratch.is_symlink()
            and output.is_dir() and not output.is_symlink()
            and not any(output.iterdir()),
            "OUTPUT_NOT_EMPTY_OR_ROOT_MISSING")
    stage = stage_candidate(candidate, root, scratch)
    report = verify_fixed_commands(candidate, stage)
    receipt = receipt_from_report(admission, report)
    body = canonical(receipt)
    report_body = read_only_report_bytes(report)
    for filename, raw in (
        ("f139-receipt.json", body),
        ("f139-receipt.sha256",
         (digest(body)+"  f139-receipt.json\n").encode()),
        ("f139-native-report.json", report_body),
    ):
        path = output / filename
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    return receipt, bool(receipt["native_qualified"])



def execute_v2_development(admission: NativeAdmission, native_root: Path,
                           scratch: Path, output: Path):
    """Inert DEV Python API; deliberately NOT in the production V1 CLI.

    An authenticated admission MUST be supplied by independent original-owner
    signed custody. G30 cannot produce a live V2 approval, nor upcast V1.
    """
    from f139.nci04_worker_v2 import (
        SOURCE_SHA, SOURCE_TREE, run_v2, receipt_v2,
    )
    require(isinstance(admission, NativeAdmission),
            "V2_SIGNED_ADMISSION_REQUIRED")
    c = admission.intent
    require(c.lane == admission.lane == "Yggdrasil"
            and c.target_commit == SOURCE_SHA
            and c.target_tree_sha == SOURCE_TREE
            and c.path == "yggdrasil/public_causal_cells.py",
            "V2_FROZEN_SOURCE_REQUIRED")
    require(admission.runner_os in ("ubuntu-latest", "windows-latest")
            and ((os.name == "nt") == (admission.runner_os == "windows-latest")),
            "V2_RUNNER_OS_DRIFT")
    require(not any(os.environ.get(k) for k in (
        "F139_WORKER_HMAC_KEY", "GH_TOKEN", "GITHUB_TOKEN",
        "OPENAI_API_KEY", "CLOUDFLARE_API_TOKEN")),
        "V2_CREDENTIAL_INHERITANCE")
    require(native_root.is_dir() and not native_root.is_symlink()
            and scratch.is_dir() and not scratch.is_symlink()
            and output.is_dir() and not output.is_symlink()
            and not any(output.iterdir()),
            "V2_ISOLATED_ROOT_OR_OUTPUT_INVALID")
    report = run_v2(c, native_root, scratch, oslabel=admission.runner_os)
    receipt = receipt_v2(admission, report)
    # Deliberately different artifacts. The V1 provider cannot interpret
    # these files as the old signed native-execution-receipt.v1.
    for filename, obj in (
        ("f139-v2-development-receipt.json", receipt),
        ("f139-v2-development-report.json", report),
    ):
        with (output / filename).open("xb") as stream:
            stream.write(canonical(obj))
            stream.flush()
            os.fsync(stream.fileno())
    from f139.nci04_v2_artifact_package import package_v2_development_output
    package_v2_development_output(output, admission)
    return receipt, bool(receipt["native_qualified"])



def execute_v3_development(admission: NativeAdmission, native_root: Path,
                           scratch: Path, output: Path):
    """New native V3 candidate producer inside the ORIGINAL worker module.

    No V1/V2 contract changes. A genuine original-owner V3-specific signature
    and GitHub authorization job must precede any call to this function.
    Until the source-specific original signer and provider verifier are added,
    the report is ALWAYS negative and cannot be a production terminal.
    """
    from f139.nci04_worker_v3 import run_v3, receipt_v3, TARGET
    require(isinstance(admission, NativeAdmission)
            and admission.lane == admission.intent.lane == "Yggdrasil"
            and admission.intent.path == TARGET
            and admission.runner_os in ("ubuntu-latest", "windows-latest")
            and ((os.name == "nt") == (admission.runner_os == "windows-latest")),
            "V3_ORIGINAL_SIGNED_ADMISSION_REQUIRED")
    require(os.environ.get("F139_NATIVE_PROTOCOL") == "v3"
            and os.environ.get("F139_NATIVE_V3_AUTHORIZATION_PASSED") == "true",
            "V3_AUTHORIZED_SOURCE_ROUTE_MISSING")
    require(not any(os.environ.get(k) for k in (
        "F139_WORKER_HMAC_KEY", "GH_TOKEN", "GITHUB_TOKEN",
        "OPENAI_API_KEY", "CLOUDFLARE_API_TOKEN")),
        "V3_SIGNER_OR_API_CREDENTIAL_EXPOSURE")
    require(native_root.is_dir() and not native_root.is_symlink()
            and scratch.is_dir() and not scratch.is_symlink()
            and output.is_dir() and not output.is_symlink()
            and not any(output.iterdir()),
            "V3_OUTPUT_OR_ROOT_ISOLATION_INVALID")
    report = run_v3(admission.intent, native_root, scratch,
                    oslabel=admission.runner_os)
    receipt = receipt_v3(admission, report)
    for name, obj in (
        ("f139-v3-native-report.json", report),
        ("f139-v3-native-receipt.json", receipt),
    ):
        with (output / name).open("xb") as stream:
            stream.write(canonical(obj))
            stream.flush()
            os.fsync(stream.fileno())
    # Positive V3 DEVELOPMENT results may finish their worker job; only the
    # original Windows owner may authenticate both provider ZIPs and settle
    # the SQLite terminal. This never grants scientific-first-use or a merge.
    require(receipt["native_qualified"] is report["native_qualified"]
            and receipt["development_only"] is True
            and receipt["scientific_first_use_authorized"] is False
            and receipt["accepted_ref_mutations"] == 0
            and receipt["paid_model_calls"] == 0,
            "V3_SIGNED_RESOURCE_AND_DEVELOPMENT_AUTHORITY_DRIFT")
    return receipt, bool(receipt["native_qualified"])


def cli():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="verb", required=True)
    commands.add_parser("authorize")
    ex = commands.add_parser("execute")
    ex.add_argument("--native-root", type=Path, required=True)
    ex.add_argument("--scratch", type=Path, required=True)
    ex.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.verb == "authorize":
        print(json.dumps(authorize(), sort_keys=True, separators=(",", ":")))
    else:
        _, completed = execute(args.native_root, args.scratch, args.output)
        print("F139_NCI04_NATIVE_FIXED_CODE_REGRESSION="+
              ("PASS" if completed else "NEGATIVE_RETAINED"))
        print("F139_NCI04_SCIENTIFIC_FIRST_USE=FALSE")
        if not completed:
            raise SystemExit(1)


if __name__ == "__main__":
    try:
        cli()
    except (NativeWorkerBlocked, Untrusted, ValueError, OSError,
            subprocess.TimeoutExpired) as exc:
        raise SystemExit("F139_NCI04_WORKER_FAIL_CLOSED "+str(exc)) from exc
