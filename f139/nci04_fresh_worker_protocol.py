"""Fresh-epoch signed worker transport for the existing F139 worker.

Admission identity is immutable (the original fresh epoch source). Execution
identity is a distinct, protected, qualified worker release. No legacy V3
sequence is fabricated, and this module never schedules or dispatches work.
The existing controller must reserve a real claim in its SQLite before POST.
"""
from __future__ import annotations

import argparse
import base64
import hmac
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from f139.nci04_native_contract import canonical, digest, parse_intent
from f139.nci04_owner_issue import NativeIssue, inspect_owner_issue
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_worker_entry import git
from f139.nci04_worker_v3 import run_v3, receipt_v3
from f139.nci04_fresh_worker_release_gate import SOURCE, TARGET, TARGET_TREE

REPO = "spoonman136668-ai/FORGE"
WORKFLOW = "forge-f139-development-worker.yml"
PREFIX = "f139-owner-release-"
OWNER = "spoonman136668-ai"
FRESH_RUN = 44831323193
PROTOCOL = "f139-nci04-fresh"
SCHEMA = "forge.f139.fresh-native-worker-claim.v1"
DOMAIN = b"FORGE-F139-FRESH-NATIVE-CLAIM-V1\0"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
OS = ("ubuntu-latest", "windows-latest")
CLAIM_FIELDS = frozenset({
    "schema", "repository", "workflow", "protocol", "epoch", "activation_run_id",
    "admission_source_sha", "worker_release_sha", "worker_release_tree",
    "ticket", "lane", "issue_number", "issue_id", "issue_body_sha256",
    "intent_sha256", "qualification_key", "target_commit", "target_tree",
    "native_path", "before_sha256", "after_sha256", "admission_seq",
    "admission_sha256", "claim_seq", "claim_sha256", "scientific_first_use",
    "model_continuation_authorized", "paid_model_calls", "accepted_ref_mutations",
})


class FreshProtocolDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise FreshProtocolDenied("F139_FRESH_PROTOCOL_" + reason)


def unique_object(pairs):
    doc = {}
    for key, value in pairs:
        need(key not in doc, "DUPLICATE_FIELD")
        doc[key] = value
    return doc


def _sha(pattern, value):
    return type(value) is str and pattern.fullmatch(value) is not None


def _positive(value):
    return type(value) is int and 0 < value < 2**63


def make_claim(issue: NativeIssue, *, release_sha: str, release_tree: str,
               admission_seq: int, admission_sha: str,
               claim_seq: int, claim_sha: str) -> dict:
    """Pure serialization of a committed owner claim; not authority to POST."""
    need(isinstance(issue, NativeIssue), "NATIVE_ISSUE_REQUIRED")
    c = issue.candidate
    claim = {
        "schema": SCHEMA, "repository": REPO, "workflow": WORKFLOW,
        "protocol": PROTOCOL, "epoch": 1, "activation_run_id": FRESH_RUN,
        "admission_source_sha": issue.source_sha, "worker_release_sha": release_sha,
        "worker_release_tree": release_tree,
        "ticket": issue.ticket, "lane": issue.lane, "issue_number": issue.number,
        "issue_id": issue.issue_id, "issue_body_sha256": issue.issue_body_sha256,
        "intent_sha256": c.intent_sha256, "qualification_key": c.qualification_key,
        "target_commit": c.target_commit, "target_tree": c.target_tree_sha,
        "native_path": c.path, "before_sha256": c.before_sha256,
        "after_sha256": c.after_sha256, "admission_seq": admission_seq,
        "admission_sha256": admission_sha, "claim_seq": claim_seq,
        "claim_sha256": claim_sha, "scientific_first_use": False,
        "model_continuation_authorized": False, "paid_model_calls": 0,
        "accepted_ref_mutations": 0,
    }
    inspect_claim(claim, issue.intent_raw)
    return claim


def inspect_claim(claim, raw):
    need(type(claim) is dict and set(claim) == CLAIM_FIELDS
         and claim["schema"] == SCHEMA and claim["repository"] == REPO
         and claim["workflow"] == WORKFLOW and claim["protocol"] == PROTOCOL
         and type(claim["epoch"]) is int and claim["epoch"] == 1
         and type(claim["activation_run_id"]) is int
         and claim["activation_run_id"] == FRESH_RUN
         and claim["admission_source_sha"] == SOURCE
         and _sha(SHA40, claim["worker_release_sha"])
         and claim["worker_release_sha"] != SOURCE
         and _sha(SHA40, claim["worker_release_tree"])
         and claim["lane"] == "Yggdrasil"
         and _positive(claim["issue_number"]) and claim["issue_number"] >= 1849
         and _positive(claim["issue_id"])
         and _positive(claim["admission_seq"])
         and _positive(claim["claim_seq"])
         and claim["admission_seq"] >= 3
         and claim["claim_seq"] >= claim["admission_seq"] + 2
         and ((claim["issue_number"] == 1849 and claim["admission_seq"] == 3)
              or (claim["issue_number"] > 1849 and claim["admission_seq"] > 3))
         and claim["target_commit"] == TARGET
         and claim["target_tree"] == TARGET_TREE
         and claim["native_path"] == "yggdrasil/public_causal_cells.py"
         and claim["scientific_first_use"] is False
         and claim["model_continuation_authorized"] is False
         and type(claim["paid_model_calls"]) is int and claim["paid_model_calls"] == 0
         and type(claim["accepted_ref_mutations"]) is int
         and claim["accepted_ref_mutations"] == 0,
         "CLAIM_SCOPE_INVALID")
    for field in ("issue_body_sha256", "intent_sha256", "qualification_key",
                  "before_sha256", "after_sha256", "admission_sha256", "claim_sha256"):
        need(_sha(SHA64, claim[field]), "CLAIM_HASH_INVALID")
    need(claim["admission_sha256"] != claim["claim_sha256"],
         "CLAIM_EVENT_IDENTITY_REUSED")
    c = parse_intent(raw, protected_main=SOURCE,
                     target_commit=TARGET, target_tree_sha=TARGET_TREE)
    need(claim["ticket"] == "f139-nci04-i" + str(claim["issue_number"])
         + "-" + SOURCE[:12] + "-" + c.intent_sha256[:8]
         and c.intent_sha256 == claim["intent_sha256"]
         and c.qualification_key == claim["qualification_key"]
         and c.lane == claim["lane"] and c.path == claim["native_path"]
         and c.before_sha256 == claim["before_sha256"]
         and c.after_sha256 == claim["after_sha256"],
         "SIGNED_INTENT_DRIFT")
    return c


def sign_claim(key, claim, raw):
    inspect_claim(claim, raw)
    need(type(key) is str and 32 <= len(key) <= 4096, "OWNER_KEY_INVALID")
    return hmac.new(key.encode("utf-8"), DOMAIN + canonical(claim),
                    hashlib.sha256).hexdigest()


def verify_signature(key, claim, raw, signature):
    need(_sha(SHA64, signature) and
         hmac.compare_digest(sign_claim(key, claim, raw), signature),
         "OWNER_SIGNATURE_INVALID")
    return digest(canonical(claim))


def encode_bundle(claim, raw):
    inspect_claim(claim, raw)
    encoded = base64.b64encode(canonical({
        "claim": claim, "intent_base64": base64.b64encode(raw).decode("ascii"),
    })).decode("ascii")
    need(len(encoded) <= 60000, "BUNDLE_TOO_LARGE")
    return encoded


def decode_bundle(encoded):
    need(type(encoded) is str and 0 < len(encoded) <= 60000,
         "BUNDLE_SIZE_INVALID")
    try:
        packed = base64.b64decode(encoded, validate=True)
        doc = json.loads(packed, object_pairs_hook=unique_object)
        need(type(doc) is dict and set(doc) == {"claim", "intent_base64"},
             "BUNDLE_FIELDS_INVALID")
        raw = base64.b64decode(doc["intent_base64"], validate=True)
        need(packed == canonical(doc)
             and base64.b64encode(packed).decode("ascii") == encoded
             and base64.b64encode(raw).decode("ascii") == doc["intent_base64"],
             "BUNDLE_NONCANONICAL")
    except (TypeError, UnicodeError, ValueError) as exc:
        raise FreshProtocolDenied("F139_FRESH_PROTOCOL_BUNDLE_INVALID") from exc
    c = inspect_claim(doc["claim"], raw)
    return doc["claim"], raw, c


def authenticate_provider(claim, raw, get):
    """Read-only independent release, Yggdrasil and original issue verification."""
    c = inspect_claim(claim, raw)
    forge = "repos/" + REPO
    ygg = "repos/" + OWNER + "/Yggdrasil"
    branch_route = forge + "/branches/" + PREFIX + claim["worker_release_sha"]
    commit_route = forge + "/git/commits/" + claim["worker_release_sha"]
    issue_route = forge + "/issues/" + str(claim["issue_number"])
    target_route = ygg + "/git/commits/" + TARGET
    main_route = ygg + "/branches/main"
    old_route = forge + "/branches/" + PREFIX + SOURCE
    branch = get(branch_route)
    old = get(old_route)
    release = get(commit_route)
    main = get(main_route)
    target = get(target_route)
    issue_doc = get(issue_route)
    need(branch.get("protected") is True
         and branch.get("name") == PREFIX + claim["worker_release_sha"]
         and branch.get("commit", {}).get("sha") == claim["worker_release_sha"]
         and old.get("protected") is True and old.get("name") == PREFIX + SOURCE
         and old.get("commit", {}).get("sha") == SOURCE
         and release.get("sha") == claim["worker_release_sha"]
         and release.get("tree", {}).get("sha") == claim["worker_release_tree"]
         and main.get("protected") is True
         and main.get("name") == "main"
         and main.get("commit", {}).get("sha") == TARGET
         and target.get("sha") == TARGET
         and target.get("tree", {}).get("sha") == TARGET_TREE,
         "RELEASE_OR_TARGET_DRIFT")
    original = inspect_owner_issue(
        issue_doc, protected_main=SOURCE,
        authenticated_target_commit=TARGET, authenticated_target_tree=TARGET_TREE)
    need(original.ticket == claim["ticket"]
         and original.number == claim["issue_number"]
         and original.issue_id == claim["issue_id"]
         and original.issue_body_sha256 == claim["issue_body_sha256"]
         and original.intent_raw == raw
         and original.candidate == c,
         "ORIGINAL_ISSUE_IDENTITY_DRIFT")
    need(get(branch_route) == branch and get(old_route) == old
         and get(issue_route) == issue_doc and get(main_route) == main,
         "PROVIDER_READBACK_DRIFT")
    return original


def worker_context(env, claim, *, label):
    """The worker release, not the historical admission SHA, is GITHUB_SHA."""
    need(env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("GITHUB_REF") == "refs/heads/" + PREFIX + claim["worker_release_sha"]
         and env.get("GITHUB_SHA") == claim["worker_release_sha"]
         and env.get("GITHUB_WORKFLOW_REF") ==
             REPO + "/.github/workflows/" + WORKFLOW
             + "@refs/heads/" + PREFIX + claim["worker_release_sha"]
         and env.get("F139_SOURCE_SHA") == claim["worker_release_sha"]
         and env.get("F139_TICKET") == claim["ticket"]
         and env.get("F139_LANE") == claim["lane"]
         and env.get("F139_EPOCH") == str(claim["epoch"])
         and env.get("F139_FRESH_PROTOCOL") == PROTOCOL
         and env.get("F139_RUNNER_OS") == label and label in OS
         and re.fullmatch(r"[1-9][0-9]{0,18}", env.get("GITHUB_RUN_ID", "")),
         "WORKER_CONTEXT_DRIFT")
    return int(env["GITHUB_RUN_ID"])


def authorize(env, get, *, checkout: Path):
    """Credentialed job, no candidate checkout or execution."""
    claim, raw, _ = decode_bundle(env.get("F139_NATIVE_BUNDLE", ""))
    worker_context(env, claim, label="ubuntu-latest")
    need(git(checkout, "rev-parse", "HEAD") == claim["worker_release_sha"]
         and git(checkout, "rev-parse", "HEAD^{tree}") == claim["worker_release_tree"],
         "WORKER_CHECKOUT_DRIFT")
    commitment = verify_signature(env.get("F139_WORKER_HMAC_KEY", ""),
                                  claim, raw, env.get("F139_SIGNATURE", ""))
    authenticate_provider(claim, raw, get)
    return {"authorization_sha256": commitment,
            "target_commit": claim["target_commit"],
            "ticket": claim["ticket"], "scientific_first_use": False}


def admission_for_run(claim, raw, *, commitment, run_id, oslabel):
    c = inspect_claim(claim, raw)
    need(_sha(SHA64, commitment) and commitment == digest(canonical(claim))
         and _positive(run_id) and oslabel in OS, "WORKER_COMMITMENT_DRIFT")
    return NativeAdmission(
        ticket=claim["ticket"], lane=claim["lane"], source_sha=SOURCE,
        run_id=run_id, runner_os=oslabel, issue_number=claim["issue_number"],
        issue_id=claim["issue_id"], intent=c, authorization_sha256=commitment)


def execute(env, *, checkout: Path, native: Path, scratch: Path, output: Path):
    """Run the existing fixed V3 diagnostic, behind the new signed claim only."""
    need(not any(env.get(k) for k in ("F139_WORKER_HMAC_KEY", "GH_TOKEN",
                                      "GITHUB_TOKEN", "OPENAI_API_KEY",
                                      "CLOUDFLARE_API_TOKEN"))
         and env.get("F139_FRESH_AUTHORIZED") == "true",
         "EXECUTION_AUTHORITY_OR_CREDENTIAL_DRIFT")
    claim, raw, _ = decode_bundle(env.get("F139_NATIVE_BUNDLE", ""))
    label = "windows-latest" if os.name == "nt" else "ubuntu-latest"
    run_id = worker_context(env, claim, label=label)
    a = admission_for_run(claim, raw,
                          commitment=env.get("F139_FRESH_AUTHORIZATION_SHA256"),
                          run_id=run_id, oslabel=label)
    need(git(checkout, "rev-parse", "HEAD") == claim["worker_release_sha"]
         and git(checkout, "rev-parse", "HEAD^{tree}") == claim["worker_release_tree"],
         "EXECUTION_RELEASE_DRIFT")
    need(native.is_dir() and not native.is_symlink()
         and scratch.is_dir() and not scratch.is_symlink()
         and output.is_dir() and not output.is_symlink() and not any(output.iterdir())
         and git(native, "rev-parse", "HEAD") == TARGET
         and git(native, "rev-parse", "HEAD^{tree}") == TARGET_TREE,
         "EXECUTION_PATH_OR_TARGET_DRIFT")
    report = run_v3(a.intent, native, scratch, oslabel=label)
    receipt = receipt_v3(a, report)
    for name, doc in (("f139-v3-native-report.json", report),
                      ("f139-v3-native-receipt.json", receipt)):
        with (output / name).open("xb") as fp:
            fp.write(canonical(doc))
            fp.flush()
            os.fsync(fp.fileno())
    return bool(receipt["native_qualified"])



def dispatch_arguments(key, claim, raw):
    """Build one exact existing-worker POST from a committed claim.

    No call is made here. The existing SQLite controller must commit the
    claim, authenticate the owner and re-read the release before one POST;
    after any ambiguity it must only reconcile, never call this again.
    """
    bundle = encode_bundle(claim, raw)
    signature = sign_claim(key, claim, raw)
    fields = {
        "ticket": claim["ticket"], "lane": claim["lane"],
        "source_sha": claim["worker_release_sha"],
        "epoch": str(claim["epoch"]), "signature": signature,
        "target_package": PROTOCOL, "native_bundle": bundle,
    }
    args = ["--method", "POST", "repos/" + REPO + "/actions/workflows/"
            + WORKFLOW + "/dispatches",
            "-f", "ref=" + PREFIX + claim["worker_release_sha"]]
    for k, v in fields.items():
        args.extend(("-f", "inputs[" + k + "]=" + v))
    need(key not in repr(args), "OWNER_SECRET_IN_TRANSPORT")
    return args


def qualify_provider_terminal(api, key, claim, raw, *, run_id, started_at):
    """Verify both actual provider ZIPs under this fresh claim.

    Caller must hold the existing owner lock, verify the committed SQLite
    claim and authenticate the owner release. The returned archives are
    uncommitted until the controller retains bytes and atomically settles.
    """
    from f139.nci04_original_v3_terminal import qualified_original_github_run
    signature = sign_claim(key, claim, raw)
    commitment = verify_signature(key, claim, raw, signature)
    authenticate_provider(claim, raw, api.native_repo_get)
    admissions = {
        label: admission_for_run(claim, raw, commitment=commitment,
                                 run_id=run_id, oslabel=label)
        for label in OS
    }
    return qualified_original_github_run(
        api, run_id, claim["ticket"], claim["worker_release_sha"],
        started_at, admissions, fresh=True)


def _get(route):
    # Routes come exclusively from authenticate_provider's validated claim.
    need(route.startswith(("repos/" + REPO + "/", "repos/" + OWNER + "/Yggdrasil/"))
         and ".." not in route and "?" not in route, "PROVIDER_ROUTE_DENIED")
    p = subprocess.run(["gh", "api", "--method", "GET", route],
                       capture_output=True, stdin=subprocess.DEVNULL,
                       timeout=30, check=False)
    need(p.returncode == 0 and 0 < len(p.stdout) <= 512000,
         "PROVIDER_READ_FAILED")
    data = json.loads(p.stdout, object_pairs_hook=unique_object)
    need(type(data) is dict, "PROVIDER_DOCUMENT_INVALID")
    return data


def cli():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("authorize")
    a.add_argument("--checkout", type=Path, required=True)
    e = sub.add_parser("execute")
    for arg in ("checkout", "native", "scratch", "output"):
        e.add_argument("--" + arg, type=Path, required=True)
    args = p.parse_args()
    if args.action == "authorize":
        print(canonical(authorize(os.environ, _get, checkout=args.checkout)).decode("ascii"))
    elif not execute(os.environ, checkout=args.checkout, native=args.native,
                     scratch=args.scratch, output=args.output):
        raise SystemExit("F139_FRESH_DEVELOPMENT_NEGATIVE_RETAINED")
    else:
        print("F139_FRESH_DEVELOPMENT=PASS")


if __name__ == "__main__":
    cli()
