"""F139 native V3 distinct original-owner claim and worker release path.

Version-distinct from V1 and V2 until original owner admits V3 and alters
its sole existing dispatcher. V1 native issue HMAC never authorizes V3 without this distinct signed claim.
"""
from __future__ import annotations
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess

from f139.nci04_native_contract import canonical, digest, parse_intent
from f139.nci04_owner_issue import NativeIssue, make_signed_dispatch_inputs
from f139.nci04_signed_native import NativeAdmission, _identity
from f139.nci04_worker_entry import (
    authorize, common_source, git, intent_raw, native_provider_pin,
    execute_v3_development,
)
from f139.nci04_worker_v3 import TARGET

SCHEMA = "forge.f139.nci04.v3-owner-predispatch.v1"
DOMAIN = b"FORGE-F139-NCI04-PREDISPATCH-V3\0"
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
NUMBER = re.compile(r"[1-9][0-9]*\Z")
FIRST_NEW_EVENT = 322


class G36Denied(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise G36Denied("F139_G36_" + reason)


def _bound(issue: NativeIssue, epoch: int,
           event_seq: int, event_sha: str,
           claim_seq: int, claim_sha: str):
    c = issue.candidate
    need(isinstance(issue, NativeIssue)
         and type(epoch) is int and epoch > 0
         and type(event_seq) is int and event_seq > FIRST_NEW_EVENT
         and type(claim_seq) is int and claim_seq > event_seq
         and type(event_sha) is str and SHA64.fullmatch(event_sha)
         and type(claim_sha) is str and SHA64.fullmatch(claim_sha)
         and issue.lane == c.lane == "Yggdrasil"
         and re.fullmatch(r"[a-f0-9]{40}",c.target_commit) is not None
         and re.fullmatch(r"[a-f0-9]{40}",c.target_tree_sha) is not None
         and c.path == TARGET
         and issue.native_intent_sha256 == c.intent_sha256
         and issue.qualification_key == c.qualification_key
         and issue.ticket == "f139-nci04-i" + str(issue.number) + "-"
                + issue.source_sha[:12] + "-" + c.intent_sha256[:8],
         "FRESH_YGG_OWNER_ADMISSION_REQUIRED")
    return {
        "schema": SCHEMA, "workflow": "forge-f139-development-worker.yml",
        "protocol": "v3", "ticket": issue.ticket, "lane": issue.lane,
        "source_sha": issue.source_sha, "epoch": epoch,
        "issue_number": issue.number, "issue_id": issue.issue_id,
        "issue_body_sha256": issue.issue_body_sha256,
        "native_intent_sha256": c.intent_sha256,
        "qualification_key": c.qualification_key,
        "native_target_commit": c.target_commit,
        "native_target_tree": c.target_tree_sha,
        "native_candidate_sha256": c.after_sha256,
        "original_native_event_seq": event_seq,
        "original_native_event_sha256": event_sha,
        "original_claim_event_seq": claim_seq,
        "original_claim_event_sha256": claim_sha,
        "scientific_first_use": False, "paid_model_calls": 0,
    }


def signature(owner_key: str, issue: NativeIssue, epoch: int,
              event_seq: int, event_sha: str,
              claim_seq: int, claim_sha: str):
    need(type(owner_key) is str and 32 <= len(owner_key) <= 4096,
         "OWNER_SECRET_INVALID")
    record = _bound(issue, epoch, event_seq, event_sha, claim_seq, claim_sha)
    return hmac.new(owner_key.encode("utf-8"), DOMAIN + canonical(record),
                    hashlib.sha256).hexdigest()


def verify_claim(owner_key: str, issue: NativeIssue, epoch: int,
                 event_seq: int, event_sha: str,
                 claim_seq: int, claim_sha: str, signed: str):
    need(type(signed) is str and SHA64.fullmatch(signed),
         "V3_SIGNATURE_INVALID")
    expected = signature(owner_key, issue, epoch,
                         event_seq, event_sha, claim_seq, claim_sha)
    need(hmac.compare_digest(signed, expected),
         "V3_OWNER_PRE_DISPATCH_SIGNATURE_REJECTED")
    return digest(canonical(_bound(
        issue, epoch, event_seq, event_sha, claim_seq, claim_sha)))


def original_owner_v3_fields(db, ticket: str, *, owner_hmac_key: str):
    """Pre-POST on ONLY existing owner, after claim under its lock.

    No controller hook is installed by G36. The original owner must still
    integrate this under SingleOwner, protect exactly-once admission and POST.
    """
    from f139.local_controller import Database
    from f139.nci04_owner_ledger import (
        KIND, frozen_native_issue, verify_native_activation,
    )
    need(type(db) is Database, "ORIGINAL_DATABASE_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and verify_native_activation(db),
         "ORIGINAL_NATIVE_ACTIVATION_INVALID")
    issue = frozen_native_issue(db, ticket)
    need(meta["source_sha"] == issue.source_sha,
         "ORIGINAL_SOURCE_DRIFT")
    task = db.conn.execute(
        "SELECT stage,source_sha,run_id FROM tasks WHERE ticket=?",
        (ticket,)).fetchone()
    need(task is not None and task["stage"] == "START_RISK"
         and task["source_sha"] == meta["source_sha"]
         and task["run_id"] is None,
         "PRE_DISPATCH_START_RISK_REQUIRED")
    def read_events(kind):
        out = []
        for row in db.conn.execute(
                "SELECT seq,sha,payload FROM events WHERE kind=? ORDER BY seq",
                (kind,)):
            if json.loads(row["payload"]).get("ticket") == ticket:
                out.append(row)
        return out
    admitted = read_events(KIND)
    claimed = read_events("BEFORE_DISPATCH_INTENT")
    posted = read_events("DISPATCH_POST_RETURNED")
    need(len(admitted) == 1 and len(claimed) == 1 and not posted
         and admitted[0]["seq"] > FIRST_NEW_EVENT
         and claimed[0]["seq"] > admitted[0]["seq"]
         and meta["head_seq"] == claimed[0]["seq"]
         and meta["head_hash"] == claimed[0]["sha"],
         "NEW_EXCLUSIVE_ORIGINAL_CLAIM_REQUIRED")
    fields = make_signed_dispatch_inputs(
        issue, owner_hmac_key=owner_hmac_key, epoch=meta["epoch"])
    sig = signature(
        owner_hmac_key, issue, meta["epoch"],
        admitted[0]["seq"], admitted[0]["sha"],
        claimed[0]["seq"], claimed[0]["sha"])
    # A V1 dispatch without this signature MUST stay on the V1 job.
    fields.update({
        "native_protocol": "v3",
        "v3_original_event_seq": str(admitted[0]["seq"]),
        "v3_original_event_sha256": admitted[0]["sha"],
        "v3_claim_event_seq": str(claimed[0]["seq"]),
        "v3_claim_event_sha256": claimed[0]["sha"],
        "v3_owner_signature": sig,
    })
    need(owner_hmac_key not in repr(fields),
         "OWNER_SECRET_IN_DISPATCH_FIELDS")
    return fields


def _issue_from_env(source, c):
    num = os.environ.get("F139_ISSUE_NUMBER", "")
    ident = os.environ.get("F139_ISSUE_ID", "")
    body = os.environ.get("F139_BODY_SHA256", "")
    ticket = os.environ.get("F139_TICKET", "")
    need(type(num) is str and NUMBER.fullmatch(num)
         and type(ident) is str and NUMBER.fullmatch(ident)
         and type(body) is str and SHA64.fullmatch(body),
         "ISSUE_FIELDS_MISSING")
    return NativeIssue(
        number=int(num), issue_id=int(ident), ticket=ticket,
        lane=c.lane, source_sha=source, issue_body_sha256=body,
        native_intent_sha256=c.intent_sha256,
        qualification_key=c.qualification_key,
        intent_raw=b"", candidate=c)


def authorize_v3():
    """Credentialed original GitHub authorizer only, never candidate stage."""
    need(os.environ.get("F139_NATIVE_PROTOCOL") == "v3"
         and os.environ.get("F139_RUNNER_OS") == "ubuntu-latest",
         "V3_CREDENTIALLED_AUTH_JOB_REQUIRED")
    original = authorize()  # existing V1 + independent native signature
    source = common_source()
    commit, tree = native_provider_pin()
    c = parse_intent(intent_raw(), protected_main=source,
                     target_commit=commit, target_tree_sha=tree)
    issue = _issue_from_env(source, c)
    sequence = os.environ.get("F139_V3_ORIGINAL_EVENT_SEQ", "")
    claim = os.environ.get("F139_V3_CLAIM_EVENT_SEQ", "")
    need(NUMBER.fullmatch(sequence or "") is not None
         and NUMBER.fullmatch(claim or "") is not None,
         "V3_ORIGINAL_EVENTS_MISSING")
    owner_key = os.environ.get("F139_WORKER_HMAC_KEY", "")
    proof = verify_claim(
        owner_key, issue, int(os.environ["F139_EPOCH"]),
        int(sequence), os.environ.get("F139_V3_ORIGINAL_EVENT_SHA256", ""),
        int(claim), os.environ.get("F139_V3_CLAIM_EVENT_SHA256", ""),
        os.environ.get("F139_V3_OWNER_SIGNATURE", ""))
    need(original["native_intent_sha256"] == c.intent_sha256
         and original["native_target_tree"] == tree
         and original["source_sha"] == source,
         "ORIGINAL_DUAL_HMAC_V3_DRIFT")
    return {
        "schema": "forge.f139.nci04.v3-authorized-job.v1",
        "authorization_sha256": original["authorization_sha256"],
        "v3_owner_claim_sha256": proof,
        "source_sha": source, "ticket": issue.ticket,
        "scientific_first_use": False, "paid_model_calls": 0,
    }


def execute_v3(native_root: Path, scratch: Path, output: Path):
    """Credential-free GitHub worker path behind native-authorize-v3 needs."""
    source = common_source()
    need(os.environ.get("F139_NATIVE_PROTOCOL") == "v3"
         and os.environ.get("F139_NATIVE_V3_AUTHORIZATION_PASSED") == "true"
         and os.environ.get("F139_NATIVE_AUTHENTICATION_PASSED") == "true",
         "V3_AUTH_JOB_NOT_SUCCESS")
    need(not any(os.environ.get(k) for k in (
        "F139_WORKER_HMAC_KEY", "GH_TOKEN", "GITHUB_TOKEN",
        "OPENAI_API_KEY", "CLOUDFLARE_API_TOKEN")),
        "CREDENTIAL_EXPOSURE_TO_NATIVE_CODE")
    auth = os.environ.get("F139_NATIVE_AUTHORIZATION_SHA256", "")
    bound = os.environ.get("F139_V3_OWNER_CLAIM_SHA256", "")
    need(type(auth) is str and SHA64.fullmatch(auth)
         and type(bound) is str and SHA64.fullmatch(bound),
         "SIGNED_AUTHORIZATION_HANDOFF_MISSING")
    commit, tree = native_provider_pin()
    root = Path(native_root).resolve(strict=True)
    need(root.is_dir() and git(root, "rev-parse", "HEAD") == commit
         and git(root, "rev-parse", "HEAD^{tree}") == tree,
         "PINNED_NATIVE_SOURCE_DRIFT")
    c = parse_intent(intent_raw(), protected_main=source,
                     target_commit=commit, target_tree_sha=tree)
    issue = _issue_from_env(source, c)
    epoch = int(os.environ.get("F139_EPOCH", "0"))
    record = _bound(issue, epoch,
           int(os.environ.get("F139_V3_ORIGINAL_EVENT_SEQ", "0")),
           os.environ.get("F139_V3_ORIGINAL_EVENT_SHA256", ""),
           int(os.environ.get("F139_V3_CLAIM_EVENT_SEQ", "0")),
           os.environ.get("F139_V3_CLAIM_EVENT_SHA256", ""))
    need(digest(canonical(record)) == bound,
         "V3_OWNER_COMMITMENT_HANDOFF_DRIFT")
    original_sig = os.environ.get("F139_SIGNATURE", "")
    need(type(original_sig) is str and SHA64.fullmatch(original_sig),
         "ORIGINAL_CONTROLLER_SIGNATURE_MISSING")
    legacy = _identity(
        {"ticket": issue.ticket, "lane": issue.lane,
         "source_sha": source, "epoch": str(epoch),
         "signature": original_sig},
        str(issue.number), str(issue.issue_id),
        issue.issue_body_sha256, c)
    need(digest(canonical(legacy)) == auth,
         "SIGNED_V1_NATIVE_ADMISSION_HANDOFF_DRIFT")
    need(os.environ.get("F139_QUALIFICATION_KEY") == c.qualification_key,
         "CANDIDATE_QUALIFICATION_DRIFT")
    label = os.environ.get("F139_RUNNER_OS", "")
    need(label in ("ubuntu-latest", "windows-latest")
         and ((os.name == "nt") == (label == "windows-latest")),
         "RUNNER_OS_DRIFT")
    a = NativeAdmission(
        ticket=os.environ["F139_TICKET"], lane=c.lane, source_sha=source,
        run_id=int(os.environ["GITHUB_RUN_ID"]), runner_os=label,
        issue_number=int(os.environ["F139_ISSUE_NUMBER"]),
        issue_id=int(os.environ["F139_ISSUE_ID"]), intent=c,
        authorization_sha256=auth)
    receipt, completed = execute_v3_development(
        a, root, Path(scratch), Path(output))
    return receipt, completed


def cli():
    p = argparse.ArgumentParser()
    verb = p.add_subparsers(dest="action", required=True)
    verb.add_parser("authorize-v3")
    execute = verb.add_parser("execute-v3")
    for arg in ("native-root", "scratch", "output"):
        execute.add_argument("--" + arg, required=True, type=Path)
    args = p.parse_args()
    if args.action == "authorize-v3":
        print(json.dumps(authorize_v3(), sort_keys=True, separators=(",", ":")))
    else:
        _, passed = execute_v3(args.native_root, args.scratch, args.output)
        print("F139_NCI04_V3_DEVELOPMENT=" +
              ("PASS" if passed else "NEGATIVE_RETAINED"))
        print("F139_SCIENTIFIC_FIRST_USE=FALSE")
        if not passed:
            raise SystemExit(1)


if __name__ == "__main__":
    try:
        cli()
    except (G36Denied, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit("F139_G36_V3_FAIL_CLOSED " + str(exc)) from exc
