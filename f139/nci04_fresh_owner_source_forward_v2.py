"""Read-only signed V2 source-forward certificate for the SAME F139 Windows owner.

This is not an installer and has no GitHub write, owner task, controller or
scheduler action. An original owner's separately qualified PREPARE must create
the new certificate only after a cold, append-only multi-ticket audit. The
original V1 certificate is preserved and independently reverified as archived
custody. V2 is scoped to the named, exact-source development PR only.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_fresh_worker_protocol import SOURCE, TARGET, TARGET_TREE
from f139.nci04_fresh_owner_source_forward import (
    FORGE, NAME as PREVIOUS_NAME, inspect_forward, ForwardSourceDenied,
)

SCHEMA = "forge.f139.fresh-original-owner-source-forward.v2"
DOMAIN = b"FORGE-F139-FRESH-ORIGINAL-OWNER-SOURCE-FORWARD-V2\0"
NAME = "fresh-original-owner-source-forward-v2.json"
WORKFLOW = ".github/workflows/f139-fresh-owner-source-forward-v2.yml"
OWNER_JOB = "fresh-original-owner-source-forward-v2-prepare"
PREFIX = "F139-FRESH-OWNER-SOURCE-FORWARD-V2 "
PR = 1869
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
CI_JOBS = (
    ("regression_run_id", frozenset({
        "windows_f139", "linux_f139", "windows_genenv", "linux_genenv",
        "windows_native", "linux_native", "windows", "linux",
    })),
    ("source_run_id", frozenset({"source (ubuntu-latest)", "source (windows-latest)"})),
    ("rehearsal_run_id", frozenset({
        "development-rehearsal (ubuntu-latest)",
        "development-rehearsal (windows-latest)",
    })),
)
FIELDS = frozenset({
    "schema", "admission_source_sha", "worker_release_sha",
    "previous_certificate_sha256", "previous_owner_source_sha",
    "previous_owner_source_tree", "owner_source_sha", "owner_source_tree",
    "pr_number", "pr_head_sha", "regression_run_id", "source_run_id",
    "rehearsal_run_id", "owner_run_id", "owner_comment_id",
    "terminal_seq", "terminal_hash", "terminal_count",
    "last_ticket", "task_name", "development_only",
    "worker_release_unchanged", "scientific_first_use", "paid_model_calls",
    "owner_signature",
})


class ForwardV2Denied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise ForwardV2Denied("F139_FRESH_FORWARD_V2_" + reason)


def sha40(v):
    return type(v) is str and HEX40.fullmatch(v) is not None


def sha64(v):
    return type(v) is str and HEX64.fullmatch(v) is not None


def pos(v):
    return type(v) is int and 0 < v < (1 << 63)


def sign(unsigned, key):
    need(type(unsigned) is dict and set(unsigned) == FIELDS - {"owner_signature"}
         and type(key) is str and 32 <= len(key) <= 4096,
         "SIGNING_INPUT_INVALID")
    return hmac.new(key.encode(), DOMAIN + canonical(unsigned),
                    hashlib.sha256).hexdigest()


def _sealed(path):
    need(path.is_file() and not path.is_symlink()
         and not getattr(path, "is_junction", lambda: False)()
         and 0 < path.stat().st_size <= 8192, "CERTIFICATE_FILE_INVALID")
    data = path.read_bytes()
    try:
        doc = json.loads(data)
    except (UnicodeError, ValueError) as e:
        raise ForwardV2Denied("F139_FRESH_FORWARD_V2_CERTIFICATE_JSON_INVALID") from e
    need(type(doc) is dict and canonical(doc) == data,
         "CERTIFICATE_NOT_CANONICAL")
    return doc, data


def _qualified_run(api, ident, head, jobs):
    run = api.get(FORGE + "/actions/runs/" + str(ident))
    page = api.get(FORGE + "/actions/runs/" + str(ident) + "/jobs?per_page=100")
    records = page.get("jobs") if type(page) is dict else None
    need(type(run) is dict and run.get("id") == ident
         and run.get("head_sha") == head and run.get("event") == "pull_request"
         and run.get("run_attempt") == 1
         and run.get("status") == "completed"
         and run.get("conclusion") == "success"
         and type(records) is list
         and page.get("total_count") == len(records)
         and {z.get("name") for z in records} == jobs
         and all(z.get("status") == "completed"
                 and z.get("conclusion") == "success" for z in records),
         "FINAL_HEAD_QUALIFICATION_DRIFT")


def inspect_v2(doc, *, db, api, release, key, previous, previous_bytes):
    """Authenticate exact newest main, original signed V1 and full cold ledger.

    The ledger may grow AFTER the signed V2 checkpoint, but its immutable
    checkpoint event and all historical provider-evidence archives must still
    survive the existing read_lifecycle cold verifier on every owner tick.
    """
    need(type(doc) is dict and set(doc) == FIELDS
         and doc["schema"] == SCHEMA
         and doc["admission_source_sha"] == release["admission_source_sha"] == SOURCE
         and doc["worker_release_sha"] == release["worker_release_sha"]
         and doc["task_name"] == "FORGE-F139-UnifiedController"
         and type(doc["pr_number"]) is int and doc["pr_number"] >= PR
         and sha40(doc["previous_owner_source_sha"])
         and sha40(doc["previous_owner_source_tree"])
         and sha40(doc["owner_source_sha"])
         and sha40(doc["owner_source_tree"])
         and sha40(doc["pr_head_sha"])
         and doc["owner_source_sha"] != doc["previous_owner_source_sha"]
         and sha64(doc["previous_certificate_sha256"])
         and sha64(doc["terminal_hash"])
         and sha64(doc["owner_signature"])
         and pos(doc["owner_run_id"])
         and pos(doc["owner_comment_id"])
         and pos(doc["regression_run_id"])
         and pos(doc["source_run_id"])
         and pos(doc["rehearsal_run_id"])
         and type(doc["terminal_seq"]) is int
         and doc["terminal_seq"] > 9
         and type(doc["terminal_count"]) is int
         and 2 <= doc["terminal_count"] <= 4096
         and type(doc["last_ticket"]) is str
         and 0 < len(doc["last_ticket"]) <= 160
         and doc["development_only"] is True
         and doc["worker_release_unchanged"] is True
         and doc["scientific_first_use"] is False
         and type(doc["paid_model_calls"]) is int
         and doc["paid_model_calls"] == 0,
         "EXACT_SIGNED_SCOPE_INVALID")
    actual = sign({k: v for k, v in doc.items() if k != "owner_signature"}, key)
    need(hmac.compare_digest(actual, doc["owner_signature"]),
         "OWNER_SIGNATURE_INVALID")
    need(type(previous_bytes) is bytes and
         digest(previous_bytes) == doc["previous_certificate_sha256"]
         and type(previous) is dict
         and previous.get("pr_number") == 1865
         and previous.get("owner_source_sha") == PREVIOUS_OWNER_MAIN
         and doc["previous_owner_source_sha"] == PREVIOUS_OWNER_MAIN
         and previous.get("owner_source_sha") == doc["previous_owner_source_sha"]
         and previous.get("owner_source_tree") == doc["previous_owner_source_tree"],
         "PREVIOUS_CERTIFICATE_CHAIN_DRIFT")
    # The V1 owner source was the protected main when V1 was created; after
    # the authorized V2 merge it is an archived source, never rewritten.
    try:
        prior_source = inspect_forward(
            previous, db=db, api=api, release=release, key=key,
            expected_current_source_sha=doc["owner_source_sha"])
    except ForwardSourceDenied as e:
        raise ForwardV2Denied("F139_FRESH_FORWARD_V2_PREVIOUS_CUSTODY_INVALID") from e
    need(prior_source == (
        doc["previous_owner_source_sha"], doc["previous_owner_source_tree"]),
        "PREVIOUS_OWNER_SOURCE_MISMATCH")

    # Original owner's signed SQLite and BOTH immutable OS receipt ZIPs are
    # validated by read_lifecycle under the original kernel mutex.
    from f139.nci04_fresh_lifecycle import read_lifecycle, CUSTODY_KIND
    _, entries = read_lifecycle(db, key)
    meta = db.meta()
    seq = doc["terminal_seq"]
    row = db.conn.execute(
        "SELECT kind,sha FROM events WHERE seq=?", (seq,)).fetchone()
    nterm = db.conn.execute(
        "SELECT COUNT(*) FROM events WHERE kind=? AND seq<=?",
        (CUSTODY_KIND, seq)).fetchone()[0]
    need(meta["head_seq"] >= seq and row is not None
         and row["kind"] == CUSTODY_KIND and row["sha"] == doc["terminal_hash"]
         and nterm == doc["terminal_count"]
         and len(entries) >= nterm
         and entries[nterm - 1]["record"]["ticket"] == doc["last_ticket"]
         and all(e["stage"] == "VERIFIED" and not e.get("negative")
                 for e in entries[:nterm]),
         "MULTITICKET_COLD_TERMINAL_DRIFT")

    branch = api.get(FORGE + "/branches/main")
    commit = api.get(FORGE + "/git/commits/" + doc["owner_source_sha"])
    pr = api.get(FORGE + "/pulls/" + str(doc["pr_number"]))
    need(branch.get("name") == "main" and branch.get("protected") is True
         and branch.get("commit", {}).get("sha") == doc["owner_source_sha"]
         and commit.get("sha") == doc["owner_source_sha"]
         and commit.get("tree", {}).get("sha") == doc["owner_source_tree"]
         and pr.get("merged") is True and pr.get("state") == "closed"
         and pr.get("merge_commit_sha") == doc["owner_source_sha"]
         and pr.get("head", {}).get("sha") == doc["pr_head_sha"]
         and pr.get("user", {}).get("login") == "spoonman136668-ai"
         and pr.get("base", {}).get("repo", {}).get("full_name")
             == "spoonman136668-ai/FORGE"
         and pr.get("head", {}).get("repo", {}).get("full_name")
             == "spoonman136668-ai/FORGE",
         "MERGED_MAIN_PR_OR_TREE_DRIFT")
    for field, expected in CI_JOBS:
        _qualified_run(api, doc[field], doc["pr_head_sha"], expected)

    body = (PREFIX + doc["owner_source_sha"] + " " +
            doc["pr_head_sha"] + " " + str(doc["pr_number"]) + " " +
            str(doc["regression_run_id"]) + " " +
            str(doc["source_run_id"]) + " " +
            str(doc["rehearsal_run_id"]) + " " +
            str(doc["terminal_seq"]) + " " + doc["terminal_hash"])
    comment = api.get(FORGE + "/issues/comments/" + str(doc["owner_comment_id"]))
    need(comment.get("id") == doc["owner_comment_id"]
         and comment.get("issue_url") == "https://api.github.com/" + FORGE + "/issues/1830"
         and comment.get("body") == body
         and comment.get("user", {}).get("login") == "spoonman136668-ai"
         and comment.get("author_association") == "OWNER",
         "OWNER_COMMENT_CUSTODY_DRIFT")
    owner = api.get(FORGE + "/actions/runs/" + str(doc["owner_run_id"]))
    page = api.get(FORGE + "/actions/runs/" + str(doc["owner_run_id"])
                   + "/jobs?per_page=100")
    jobs = page.get("jobs") if type(page) is dict else None
    need(owner.get("id") == doc["owner_run_id"]
         and owner.get("event") == "issue_comment"
         and owner.get("path") == WORKFLOW
         and owner.get("head_sha") == doc["owner_source_sha"]
         and owner.get("run_attempt") == 1
         and owner.get("status") == "completed"
         and owner.get("conclusion") == "success"
         and owner.get("actor", {}).get("login") == "spoonman136668-ai"
         and type(jobs) is list and page.get("total_count") == len(jobs)
         and sum(z.get("name") == OWNER_JOB
                 and z.get("runner_name") == "FORGE-CODEX-REMOTE"
                 and z.get("status") == "completed"
                 and z.get("conclusion") == "success" for z in jobs) == 1
         and all(z.get("name") == OWNER_JOB or
                 (z.get("status") == "completed"
                  and z.get("conclusion") == "skipped") for z in jobs),
         "OWNER_PREPARE_WINDOWS_CUSTODY_DRIFT")
    need(api.get(FORGE + "/branches/main") == branch,
         "PROTECTED_MAIN_CHANGED_DURING_CHECK")
    return doc["owner_source_sha"], doc["owner_source_tree"]


def inspect_installed_v2(db, api, release, key):
    """Read V2+archived V1 create-only JSON; absence means no V2 authority."""
    folder = db.filename.parent
    v2_path = folder / NAME
    need(v2_path.exists() or v2_path.is_symlink(),
         "V2_CERTIFICATE_NOT_INSTALLED")
    doc, _ = _sealed(v2_path)
    previous, previous_raw = _sealed(folder / PREVIOUS_NAME)
    return inspect_v2(doc, db=db, api=api, release=release, key=key,
                      previous=previous, previous_bytes=previous_raw)


PREVIOUS_OWNER_MAIN = "f24251e0d95938e593a54c1577a34efadc8080d8"


def preflight_v2_unsigned(db, api, release, key, *, head, candidate,
                          regression_run_id, source_run_id,
                          rehearsal_run_id, pr_number=PR):
    """Generate bounded unsigned V2 metadata AFTER a cold, locked owner audit.

    No cert write, task change, POST, dispatch or scientific first-use occurs.
    The owner-only Windows PREPARE must separately authenticate its exact SID,
    Git checkout, old task action and disabled/stopped state before signing.
    """
    from f139.nci04_fresh_lifecycle import (
        CUSTODY_KIND, read_lifecycle,
    )
    from f139.local_controller import SingleOwner
    need(SingleOwner.held(db.filename.with_suffix(".lock")),
         "PREFLIGHT_ORIGINAL_KERNEL_LOCK_REQUIRED")
    need(sha40(candidate) and sha40(head)
         and type(pr_number) is int and pr_number >= PR
         and all(pos(x) for x in (
             regression_run_id, source_run_id, rehearsal_run_id)),
         "PREFLIGHT_INPUT_INVALID")
    root = db.filename.parent
    need(not (root / NAME).exists() and not (root / NAME).is_symlink(),
         "PREFLIGHT_V2_CERT_ALREADY_SPENT")
    prior, raw = _sealed(root / PREVIOUS_NAME)
    need(prior.get("pr_number") == 1865
         and prior.get("owner_source_sha") == PREVIOUS_OWNER_MAIN,
         "PREFLIGHT_WRONG_HISTORICAL_OWNER_SOURCE")
    older_source = inspect_forward(
        prior, db=db, api=api, release=release, key=key,
        expected_current_source_sha=candidate)
    need(older_source[0] == PREVIOUS_OWNER_MAIN,
         "PREFLIGHT_PREVIOUS_CUSTODY_DRIFT")

    verified_release, entries = read_lifecycle(db, key)
    need(verified_release == release
         and 2 <= len(entries) <= 4096
         and all(e["stage"] == "VERIFIED"
                 and e.get("negative") is None
                 and e.get("custody") is not None for e in entries)
         and entries[-1].get("publication_attempt") is None,
         "PREFLIGHT_TERMINAL_OR_REMOTE_EFFECT_UNCERTAIN")
    # Database has no ready()/actives() methods. Query the authenticated
    # original SQLite task inventory through its read-only connection.
    # The cold read_lifecycle auditor has already bound each task row to its
    # immutable event chain; this additional guard rejects any unfinished row.
    unfinished = db.conn.execute(
        "SELECT COUNT(*) FROM tasks "
        "WHERE stage IN ('READY','START_RISK','WAIT_PROVIDER','QUARANTINED')"
    ).fetchone()[0]
    need(type(unfinished) is int and unfinished == 0,
         "PREFLIGHT_UNFINISHED_TASK_HOLD")
    meta = db.meta()
    seq = meta["head_seq"]
    event = db.conn.execute(
        "SELECT kind,sha FROM events WHERE seq=?", (seq,)).fetchone()
    need(event is not None and event["kind"] == CUSTODY_KIND
         and sha64(event["sha"])
         and seq > 9,
         "PREFLIGHT_LATEST_TERMINAL_INVALID")
    count = db.conn.execute(
        "SELECT COUNT(*) FROM events WHERE kind=?", (CUSTODY_KIND,)
    ).fetchone()[0]
    need(count == len(entries), "PREFLIGHT_COLD_ARCHIVE_COUNT_DRIFT")

    branch = api.get(FORGE + "/branches/main")
    commit = api.get(FORGE + "/git/commits/" + candidate)
    pr = api.get(FORGE + "/pulls/" + str(pr_number))
    need(branch.get("name") == "main"
         and branch.get("protected") is True
         and branch.get("commit", {}).get("sha") == candidate
         and commit.get("sha") == candidate
         and sha40(commit.get("tree", {}).get("sha"))
         and pr.get("merged") is True and pr.get("state") == "closed"
         and pr.get("merge_commit_sha") == candidate
         and pr.get("head", {}).get("sha") == head
         and pr.get("user", {}).get("login") == "spoonman136668-ai"
         and pr.get("base", {}).get("repo", {}).get("full_name")
             == "spoonman136668-ai/FORGE"
         and pr.get("head", {}).get("repo", {}).get("full_name")
             == "spoonman136668-ai/FORGE",
         "PREFLIGHT_MERGED_OWNER_SOURCE_DRIFT")
    runs = {
        "regression_run_id": regression_run_id,
        "source_run_id": source_run_id,
        "rehearsal_run_id": rehearsal_run_id,
    }
    for field, names in CI_JOBS:
        _qualified_run(api, runs[field], head, names)
    need(api.get(FORGE + "/branches/main") == branch
         and db.meta()["head_seq"] == seq
         and db.meta()["head_hash"] == event["sha"],
         "PREFLIGHT_SOURCE_OR_LEDGER_MOVED")
    return {
        "schema": SCHEMA, "admission_source_sha": SOURCE,
        "worker_release_sha": release["worker_release_sha"],
        "previous_certificate_sha256": digest(raw),
        "previous_owner_source_sha": older_source[0],
        "previous_owner_source_tree": older_source[1],
        "owner_source_sha": candidate,
        "owner_source_tree": commit["tree"]["sha"],
        "pr_number": pr_number, "pr_head_sha": head,
        **runs,
        "terminal_seq": seq, "terminal_hash": event["sha"],
        "terminal_count": count,
        "last_ticket": entries[-1]["record"]["ticket"],
        "task_name": "FORGE-F139-UnifiedController",
        "development_only": True, "worker_release_unchanged": True,
        "scientific_first_use": False, "paid_model_calls": 0,
    }


def _transport_main(argv=None):
    """Owned Windows CLI: bounded metadata and read-only cold owner check."""
    import base64
    import binascii
    import os
    import sys

    args = sys.argv[1:] if argv is None else argv
    need(type(args) is list and len(args) == 3
         and args[0] in ("sign-cert", "verify-cert", "preflight"),
         "TRANSPORT_ARGUMENTS_INVALID")
    need(type(args[2]) is str and 0 < len(args[2]) <= 16384,
         "TRANSPORT_METADATA_SIZE_INVALID")
    try:
        raw = base64.b64decode(args[2], validate=True)
        need(0 < len(raw) <= 8192, "TRANSPORT_METADATA_SIZE_INVALID")
        doc = json.loads(raw)
        # Windows PowerShell has no canonical JSON producer. The only signing
        # path accepts one bounded decoded object, then writes canonical bytes
        # under a different HMAC domain. Read-only preflight and verification
        # still require exact canonical argument bytes.
        need(type(doc) is dict
             and (args[0] == "sign-cert" or canonical(doc) == raw),
             "TRANSPORT_METADATA_NONCANONICAL")
    except (binascii.Error, ValueError, UnicodeError) as exc:
        raise ForwardV2Denied("F139_FRESH_FORWARD_V2_TRANSPORT_INVALID") from exc
    key = os.environ["F139_WORKER_HMAC_KEY"]
    if args[0] == "sign-cert":
        signed = dict(doc, owner_signature=sign(doc, key))
        path = Path(args[1])
        need(path.name == NAME
             and not path.exists() and not path.is_symlink(),
             "TRANSPORT_CERT_ALREADY_EXISTS")
        with path.open("xb") as stream:
            stream.write(canonical(signed))
            stream.flush()
            os.fsync(stream.fileno())
        print("F139_FRESH_FORWARD_V2_SIGNED_CREATE_ONLY")
        return
    need(len(args[1]) > 0 and args[1].endswith("state.sqlite"),
         "TRANSPORT_EXPECTED_DATABASE_INVALID")
    from f139.local_controller import Database, SingleOwner, GitHub
    from f139.nci04_fresh_lifecycle import read_lifecycle
    database = Path(args[1]).resolve()
    with SingleOwner(database.with_suffix(".lock")):
        db = Database.open_readonly(database)
        try:
            release, _ = read_lifecycle(db, key)
            class _RetryingReadOnlyGitHub:
                def __init__(self, inner):
                    self._inner = inner
                def get(self, route):
                    import time
                    last = None
                    for attempt in range(3):
                        try:
                            return self._inner.get(route)
                        except Exception as exc:
                            last = exc
                            if attempt < 2:
                                time.sleep(2)
                    raise last
            api = _RetryingReadOnlyGitHub(GitHub())
            if args[0] == "preflight":
                req_keys = {
                    "head", "candidate", "regression_run_id",
                    "source_run_id", "rehearsal_run_id",
                }
                need(req_keys <= set(doc) <= (req_keys | {"pr_number"}),
                     "TRANSPORT_PREFLIGHT_FIELDS")
                unsigned = preflight_v2_unsigned(
                    db, api, release, key, **doc)
                print(canonical(unsigned).decode("utf-8"))
            else:
                # The START phase checks full live-source, archived source,
                # owner-prepare run + signed old/new cold receipts.
                need(doc == {"expected_source_sha": doc.get("expected_source_sha")}
                     and sha40(doc["expected_source_sha"]),
                     "TRANSPORT_VERIFY_INPUT_INVALID")
                result = inspect_installed_v2(db, api, release, key)
                need(result[0] == doc["expected_source_sha"],
                     "TRANSPORT_VERIFY_SOURCE_DRIFT")
                print("F139_FRESH_FORWARD_V2_OWNER_CUSTODY_VERIFIED")
        finally:
            db.close()


if __name__ == "__main__":
    _transport_main()
