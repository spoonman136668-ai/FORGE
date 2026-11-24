"""Read-only, owner-signed forward source certificate for the SAME fresh F139 task.

This is NOT an installer, scheduler, new controller or worker release. It lets
a separately qualified original-owner cutover prove an exact newer checkout
without rewriting the historical signed worker release or original SQLite.
Absent certificate means the old source pin remains mandatory; invalid cert
fails closed. This verifier never writes any repository or local state.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import re

from f139.nci04_native_contract import canonical
from f139.nci04_fresh_worker_protocol import SOURCE, FRESH_RUN

SCHEMA = "forge.f139.fresh-original-owner-source-forward.v1"
DOMAIN = b"FORGE-F139-FRESH-ORIGINAL-OWNER-SOURCE-FORWARD-V1\0"
NAME = "fresh-original-owner-source-forward.json"
FORGE = "repos/spoonman136668-ai/FORGE"
WORKFLOW = ".github/workflows/f139-fresh-owner-source-forward.yml"
JOB = "fresh-original-owner-source-forward"
PREFIX = "F139-FRESH-OWNER-SOURCE-FORWARD "
# One distinct, owner-merged source-recovery PR; no blanket forward acceptance.
RECOVERY_PR = 1865
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
FIELDS = frozenset({
    "schema", "admission_source_sha", "worker_release_sha",
    "worker_release_tree", "owner_source_sha", "owner_source_tree",
    "pr_number", "pr_head_sha", "owner_run_id", "owner_comment_id",
    "regression_run_id", "source_run_id", "rehearsal_run_id",
    "terminal_seq", "terminal_hash", "task_name", "development_only",
    "worker_release_unchanged", "scientific_first_use", "paid_model_calls",
    "owner_signature",
})

class ForwardSourceDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise ForwardSourceDenied("F139_FRESH_FORWARD_" + reason)


def _sha40(s):
    return type(s) is str and SHA40.fullmatch(s) is not None


def _sha64(s):
    return type(s) is str and SHA64.fullmatch(s) is not None


def _positive(v):
    return type(v) is int and 0 < v < 2**63


def sign(unsigned, key):
    """Pure canonical HMAC helper; the owner controls access to the key."""
    need(type(unsigned) is dict and set(unsigned) == FIELDS - {"owner_signature"}
         and type(key) is str and 32 <= len(key) <= 4096,
         "SIGNING_INPUT_INVALID")
    return hmac.new(key.encode("utf-8"), DOMAIN + canonical(unsigned),
                    hashlib.sha256).hexdigest()


def inspect_forward(doc, *, db, api, release, key,
                    expected_current_source_sha=None):
    """A positive result binds provider, owner, immutable ledger and SHA/tree.

    This validates metadata only. The caller STILL verifies the actual
    installed, clean local checkout, original task, SID, PID and legacy fences.
    """
    need(type(doc) is dict and set(doc) == FIELDS
         and doc["schema"] == SCHEMA
         and doc["admission_source_sha"] == release["admission_source_sha"] == SOURCE
         and doc["worker_release_sha"] == release["worker_release_sha"]
         and doc["worker_release_tree"] == release["worker_release_tree"]
         and _sha40(doc["owner_source_sha"])
         and _sha40(doc["owner_source_tree"])
         and doc["owner_source_sha"] != release["worker_release_sha"]
         and _sha40(doc["pr_head_sha"])
         and _sha64(doc["terminal_hash"])
         and _sha64(doc["owner_signature"])
         and doc["terminal_seq"] == 9
         and doc["task_name"] == "FORGE-F139-UnifiedController"
         and type(doc["pr_number"]) is int
         and doc["pr_number"] in (1863, RECOVERY_PR)
         and all(_positive(doc[k]) for k in (
             "owner_run_id", "owner_comment_id", "regression_run_id",
             "source_run_id", "rehearsal_run_id"))
         and doc["development_only"] is True
         and doc["worker_release_unchanged"] is True
         and doc["scientific_first_use"] is False
         and type(doc["paid_model_calls"]) is int
         and doc["paid_model_calls"] == 0,
         "RECORD_SCOPE_OR_AUTHORITY_INVALID")
    calculated = sign({k: v for k, v in doc.items()
                       if k != "owner_signature"}, key)
    need(hmac.compare_digest(calculated, doc["owner_signature"]),
         "OWNER_SIGNATURE_INVALID")
    terminal = db.conn.execute(
        "SELECT kind,sha FROM events WHERE seq=9").fetchone()
    need(terminal is not None
         and terminal["kind"] == "FRESH_WORKER_PROVIDER_CUSTODY"
         and terminal["sha"] == doc["terminal_hash"]
         and db.meta()["head_seq"] >= 9,
         "ORIGINAL_TERMINAL_LEDGER_DRIFT")
    branch = api.get(FORGE + "/branches/main")
    commit = api.get(FORGE + "/git/commits/" + doc["owner_source_sha"])
    # Only the separately signed V2 successor may make this historical V1
    # signature an ARCHIVED source check after current main moves. No V1-only
    # caller changes its original strict main requirement.
    current = (doc["owner_source_sha"] if expected_current_source_sha is None
               else expected_current_source_sha)
    need(_sha40(current) and
         (expected_current_source_sha is None
          or current != doc["owner_source_sha"]),
         "FORWARD_EXPECTED_MAIN_INVALID")
    need(branch.get("name") == "main"
         and branch.get("protected") is True
         and branch.get("commit", {}).get("sha") == current
         and commit.get("sha") == doc["owner_source_sha"]
         and commit.get("tree", {}).get("sha") == doc["owner_source_tree"],
         "PROTECTED_FORWARD_SOURCE_DRIFT")
    pr = api.get(FORGE + "/pulls/" + str(doc["pr_number"]))
    need(pr.get("merged") is True and pr.get("state") == "closed"
         and pr.get("merge_commit_sha") == doc["owner_source_sha"]
         and pr.get("head", {}).get("sha") == doc["pr_head_sha"]
         and pr.get("base", {}).get("repo", {}).get("full_name")
             == "spoonman136668-ai/FORGE"
         and pr.get("head", {}).get("repo", {}).get("full_name")
             == "spoonman136668-ai/FORGE"
         and pr.get("user", {}).get("login") == "spoonman136668-ai",
         "MERGED_OWNER_PR_CUSTODY_INVALID")

    for field, expected_names in (
        ("regression_run_id", {
            "windows_f139", "linux_f139", "windows_genenv", "linux_genenv",
            "windows_native", "linux_native", "windows", "linux"}),
        ("source_run_id", {"source (ubuntu-latest)", "source (windows-latest)"}),
        ("rehearsal_run_id", {
            "development-rehearsal (ubuntu-latest)",
            "development-rehearsal (windows-latest)"}),
    ):
        run_id = doc[field]
        r = api.get(FORGE + "/actions/runs/" + str(run_id))
        jobs = api.get(FORGE + "/actions/runs/" + str(run_id) + "/jobs?per_page=100")
        rows = jobs.get("jobs") if type(jobs) is dict else None
        need(r.get("id") == run_id and r.get("head_sha") == doc["pr_head_sha"]
             and r.get("event") == "pull_request"
             and r.get("run_attempt") == 1
             and r.get("status") == "completed"
             and r.get("conclusion") == "success"
             and type(rows) is list and jobs["total_count"] == len(rows)
             and {j.get("name") for j in rows} == expected_names
             and all(j.get("status") == "completed"
                     and j.get("conclusion") == "success" for j in rows),
             "EXACT_SOURCE_QUALIFICATION_NOT_ACCEPTED")

    comment = api.get(FORGE + "/issues/comments/" + str(doc["owner_comment_id"]))
    owner_body = (PREFIX + doc["owner_source_sha"] + " " +
                  doc["pr_head_sha"] + " " + str(doc["pr_number"]) + " " +
                  str(doc["regression_run_id"]) + " " +
                  str(doc["source_run_id"]) + " " +
                  str(doc["rehearsal_run_id"]))
    need(comment.get("id") == doc["owner_comment_id"]
         and comment.get("issue_url") ==
             "https://api.github.com/" + FORGE + "/issues/1830"
         and comment.get("body") == owner_body
         and comment.get("user", {}).get("login") == "spoonman136668-ai"
         and comment.get("author_association") == "OWNER",
         "OWNER_SOURCE_COMMENT_UNAUTHENTICATED")
    r = api.get(FORGE + "/actions/runs/" + str(doc["owner_run_id"]))
    jobs = api.get(FORGE + "/actions/runs/" + str(doc["owner_run_id"])
                   + "/jobs?per_page=100")
    rows = jobs.get("jobs") if type(jobs) is dict else None
    need(r.get("id") == doc["owner_run_id"]
         and r.get("event") == "issue_comment"
         and r.get("path") == WORKFLOW
         and r.get("head_sha") == doc["owner_source_sha"]
         and r.get("run_attempt") == 1
         and r.get("status") == "completed" and r.get("conclusion") == "success"
         and r.get("actor", {}).get("login") == "spoonman136668-ai"
         and type(rows) is list and jobs.get("total_count") == len(rows)
         and sum(j.get("name") == JOB and
                 j.get("runner_name") == "FORGE-CODEX-REMOTE" and
                 j.get("status") == "completed" and
                 j.get("conclusion") == "success" for j in rows) == 1
         and all(j.get("name") == JOB or
                 (j.get("status") == "completed"
                  and j.get("conclusion") == "skipped") for j in rows),
         "ORIGINAL_WINDOWS_SOURCE_FORWARD_NOT_ACCEPTED")
    need(api.get(FORGE + "/branches/main") == branch,
         "SOURCE_MOVED_DURING_FORWARD_CHECK")
    return doc["owner_source_sha"], doc["owner_source_tree"]


def installed_forward_source(db, api, release, key):
    """Return source+tree; fallback only on an ABSENT, not invalid, certificate."""
    path = db.filename.parent / NAME
    # V2 never replaces V1. The presence of a later certificate requires the
    # full independent V1+V2, old and latest source, owner and ledger audit.
    # An invalid V2 blocks; there is no fallback to V1 after partial cutover.
    from f139.nci04_fresh_owner_source_forward_v3 import (
        NAME as NAME_V3, inspect_installed_v3,
    )
    v3_path = db.filename.parent / NAME_V3
    if v3_path.exists() or v3_path.is_symlink():
        return inspect_installed_v3(db, api, release, key)
    from f139.nci04_fresh_owner_source_forward_v2 import (
        NAME as NAME_V2, inspect_installed_v2,
    )
    new_path = db.filename.parent / NAME_V2
    if new_path.exists() or new_path.is_symlink():
        return inspect_installed_v2(db, api, release, key)
    if not path.exists() and not path.is_symlink():
        return release["worker_release_sha"], release["worker_release_tree"]
    need(path.is_file() and not path.is_symlink()
         and not getattr(path, "is_junction", lambda: False)()
         and 0 < path.stat().st_size <= 8192,
         "CERTIFICATE_FILE_INVALID")
    raw = path.read_bytes()
    try:
        doc = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ForwardSourceDenied("F139_FRESH_FORWARD_CERTIFICATE_NOT_JSON") from exc
    need(raw == canonical(doc), "CERTIFICATE_NONCANONICAL")
    return inspect_forward(doc, db=db, api=api, release=release, key=key)


def _transport_main(argv=None):
    """Bounded metadata-only certificate transport without inline Python."""
    import base64
    import binascii
    import os
    import sys

    args = sys.argv[1:] if argv is None else argv
    need(len(args) == 3 and args[0] in ("sign-cert", "verify-cert"),
         "TRANSPORT_ARGUMENTS_INVALID")
    need(0 < len(args[2]) <= 16384, "TRANSPORT_METADATA_SIZE_INVALID")
    try:
        raw = base64.b64decode(args[2], validate=True)
        need(0 < len(raw) <= 8192, "TRANSPORT_METADATA_SIZE_INVALID")
        unsigned = json.loads(raw)
    except (binascii.Error, UnicodeError, ValueError) as exc:
        raise ForwardSourceDenied("F139_FRESH_FORWARD_TRANSPORT_METADATA_INVALID") from exc
    signature = sign(unsigned, os.environ["F139_WORKER_HMAC_KEY"])
    if args[0] == "sign-cert":
        signed = dict(unsigned, owner_signature=signature)
        with Path(args[1]).open("xb") as file:
            file.write(canonical(signed))
            file.flush()
            os.fsync(file.fileno())
        print("F139_FRESH_FORWARD_CERTIFICATE=CREATE_ONLY_SIGNED")
    else:
        need(hmac.compare_digest(args[1], signature),
             "TRANSPORT_SIGNATURE_INVALID")
        print("F139_FORWARD_HMAC_VERIFIED")


if __name__ == "__main__":
    _transport_main()
