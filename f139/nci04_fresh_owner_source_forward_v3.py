"""Read-only signed V3 source-forward certificate chaining on archived V2 + V1.

Advances the SAME original Windows owner (`FORGE-F139-UnifiedController`) from
the verified Gate 6 V2 release (`32c8d3fcad7209d4331595a7fbad42d361a55b94`) to
protected `main` containing the Gate 7/8 preregistered hypothesis engine,
scientific evaluator, and live `PUBLISH_SCHEMA_HYPOTHESIS_V3` lane.

Archived V1 and V2 certificates remain immutable and are independently
reverified on every tick. No new controller, scheduler, or scientific first-use.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import re

from f139.nci04_fresh_owner_source_forward import FORGE
from f139.nci04_fresh_owner_source_forward_v2 import (
    CI_JOBS, FIELDS, NAME as PREVIOUS_NAME, OWNER_JOB, PREFIX, WORKFLOW,
    ForwardV2Denied, _qualified_run, _sealed, inspect_v2, pos, sha40, sha64,
)
from f139.nci04_fresh_worker_protocol import SOURCE
from f139.nci04_native_contract import canonical, digest

SCHEMA = "forge.f139.fresh-original-owner-source-forward.v3"
DOMAIN = b"FORGE-F139-FRESH-ORIGINAL-OWNER-SOURCE-FORWARD-V3\0"
NAME = "fresh-original-owner-source-forward-v3.json"
PREVIOUS_OWNER_MAIN = "32c8d3fcad7209d4331595a7fbad42d361a55b94"
PR_FLOOR = 1894


class ForwardV3Denied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise ForwardV3Denied("F139_FRESH_FORWARD_V3_" + reason)


def sign(unsigned: dict, key: str) -> str:
    need(type(unsigned) is dict and set(unsigned) == FIELDS - {"owner_signature"}
         and type(key) is str and 32 <= len(key) <= 4096,
         "SIGNING_INPUT_INVALID")
    return hmac.new(key.encode(), DOMAIN + canonical(unsigned),
                    hashlib.sha256).hexdigest()


def inspect_v3(doc, *, db, api, release, key, previous_v2, previous_v2_bytes,
               previous_v1, previous_v1_bytes):
    """Authenticate current protected main + archived V2 + archived V1 + cold ledger."""
    need(type(doc) is dict and set(doc) == FIELDS
         and doc["schema"] == SCHEMA
         and doc["admission_source_sha"] == release["admission_source_sha"] == SOURCE
         and doc["worker_release_sha"] == release["worker_release_sha"]
         and doc["task_name"] == "FORGE-F139-UnifiedController"
         and type(doc["pr_number"]) is int and doc["pr_number"] >= PR_FLOOR
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
         and type(doc["terminal_seq"]) is int and doc["terminal_seq"] > 23
         and type(doc["terminal_count"]) is int and 3 <= doc["terminal_count"] <= 4096
         and type(doc["last_ticket"]) is str and 0 < len(doc["last_ticket"]) <= 160
         and doc["development_only"] is True
         and doc["worker_release_unchanged"] is True
         and doc["scientific_first_use"] is False
         and type(doc["paid_model_calls"]) is int and doc["paid_model_calls"] == 0,
         "EXACT_SIGNED_SCOPE_INVALID")
    actual = sign({k: v for k, v in doc.items() if k != "owner_signature"}, key)
    need(hmac.compare_digest(actual, doc["owner_signature"]),
         "OWNER_SIGNATURE_INVALID")
    need(type(previous_v2_bytes) is bytes
         and digest(previous_v2_bytes) == doc["previous_certificate_sha256"]
         and type(previous_v2) is dict
         and previous_v2.get("owner_source_sha") == PREVIOUS_OWNER_MAIN
         and doc["previous_owner_source_sha"] == PREVIOUS_OWNER_MAIN
         and previous_v2.get("owner_source_tree") == doc["previous_owner_source_tree"],
         "PREVIOUS_V2_CERTIFICATE_CHAIN_DRIFT")
    try:
        prior_source = inspect_v2(
            previous_v2, db=db, api=api, release=release, key=key,
            previous=previous_v1, previous_bytes=previous_v1_bytes,
            expected_current_source_sha=doc["owner_source_sha"],
        )
    except ForwardV2Denied as exc:
        raise ForwardV3Denied("F139_FRESH_FORWARD_V3_PREVIOUS_V2_CUSTODY_INVALID") from exc
    need(prior_source == (
        doc["previous_owner_source_sha"], doc["previous_owner_source_tree"]),
        "PREVIOUS_V2_OWNER_SOURCE_MISMATCH")

    from f139.nci04_fresh_lifecycle import CUSTODY_KIND, read_lifecycle
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
         and pr.get("base", {}).get("repo", {}).get("full_name") == "spoonman136668-ai/FORGE"
         and pr.get("head", {}).get("repo", {}).get("full_name") == "spoonman136668-ai/FORGE",
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
    page = api.get(FORGE + "/actions/runs/" + str(doc["owner_run_id"]) + "/jobs?per_page=100")
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


def inspect_installed_v3(db, api, release, key):
    """Read V3 + archived V2 + archived V1 create-only JSON certificates."""
    from f139.nci04_fresh_owner_source_forward import NAME as V1_NAME
    folder = db.filename.parent
    v3_path = folder / NAME
    need(v3_path.exists() or v3_path.is_symlink(), "V3_CERTIFICATE_NOT_INSTALLED")
    doc, _ = _sealed(v3_path)
    prev_v2, prev_v2_raw = _sealed(folder / PREVIOUS_NAME)
    prev_v1, prev_v1_raw = _sealed(folder / V1_NAME)
    return inspect_v3(
        doc, db=db, api=api, release=release, key=key,
        previous_v2=prev_v2, previous_v2_bytes=prev_v2_raw,
        previous_v1=prev_v1, previous_v1_bytes=prev_v1_raw,
    )


def preflight_v3_unsigned(db, api, release, key, *, head, candidate,
                          regression_run_id, source_run_id, rehearsal_run_id,
                          pr_number):
    """Generate unsigned V3 metadata AFTER cold, locked V1+V2+SQLite audit."""
    from f139.local_controller import SingleOwner
    from f139.nci04_fresh_lifecycle import CUSTODY_KIND, read_lifecycle
    from f139.nci04_fresh_owner_source_forward import NAME as V1_NAME

    need(SingleOwner.held(db.filename.with_suffix(".lock")),
         "PREFLIGHT_ORIGINAL_KERNEL_LOCK_REQUIRED")
    need(sha40(candidate) and sha40(head)
         and type(pr_number) is int and pr_number >= PR_FLOOR
         and all(pos(x) for x in (regression_run_id, source_run_id, rehearsal_run_id)),
         "PREFLIGHT_INPUT_INVALID")
    root = db.filename.parent
    need(not (root / NAME).exists() and not (root / NAME).is_symlink(),
         "PREFLIGHT_V3_CERT_ALREADY_SPENT")
    prior_v2, raw_v2 = _sealed(root / PREVIOUS_NAME)
    prior_v1, raw_v1 = _sealed(root / V1_NAME)
    need(prior_v2.get("owner_source_sha") == PREVIOUS_OWNER_MAIN,
         "PREFLIGHT_WRONG_HISTORICAL_V2_SOURCE")
    older_source = inspect_v2(
        prior_v2, db=db, api=api, release=release, key=key,
        previous=prior_v1, previous_bytes=raw_v1,
        expected_current_source_sha=candidate,
    )
    need(older_source[0] == PREVIOUS_OWNER_MAIN, "PREFLIGHT_PREVIOUS_V2_CUSTODY_DRIFT")

    verified_release, entries = read_lifecycle(db, key)
    need(verified_release == release
         and 3 <= len(entries) <= 4096
         and all(e["stage"] == "VERIFIED"
                 and e.get("negative") is None
                 and e.get("custody") is not None for e in entries)
         and entries[-1].get("publication_attempt") is None,
         "PREFLIGHT_TERMINAL_OR_REMOTE_EFFECT_UNCERTAIN")
    unfinished = db.conn.execute(
        "SELECT COUNT(*) FROM tasks "
        "WHERE stage IN ('READY','START_RISK','WAIT_PROVIDER','QUARANTINED')"
    ).fetchone()[0]
    need(type(unfinished) is int and unfinished == 0, "PREFLIGHT_UNFINISHED_TASK_HOLD")
    meta = db.meta()
    seq = meta["head_seq"]
    event = db.conn.execute(
        "SELECT kind,sha FROM events WHERE seq=?", (seq,)).fetchone()
    need(event is not None and event["kind"] == CUSTODY_KIND
         and sha64(event["sha"]) and seq > 23,
         "PREFLIGHT_LATEST_TERMINAL_INVALID")
    count = db.conn.execute(
        "SELECT COUNT(*) FROM events WHERE kind=?", (CUSTODY_KIND,)
    ).fetchone()[0]
    need(count == len(entries), "PREFLIGHT_COLD_ARCHIVE_COUNT_DRIFT")

    branch = api.get(FORGE + "/branches/main")
    commit = api.get(FORGE + "/git/commits/" + candidate)
    pr = api.get(FORGE + "/pulls/" + str(pr_number))
    need(branch.get("name") == "main" and branch.get("protected") is True
         and branch.get("commit", {}).get("sha") == candidate
         and commit.get("sha") == candidate
         and sha40(commit.get("tree", {}).get("sha"))
         and pr.get("merged") is True and pr.get("state") == "closed"
         and pr.get("merge_commit_sha") == candidate
         and pr.get("head", {}).get("sha") == head
         and pr.get("user", {}).get("login") == "spoonman136668-ai"
         and pr.get("base", {}).get("repo", {}).get("full_name") == "spoonman136668-ai/FORGE"
         and pr.get("head", {}).get("repo", {}).get("full_name") == "spoonman136668-ai/FORGE",
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
        "previous_certificate_sha256": digest(raw_v2),
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
    """Owned Windows CLI for V3 preflight, create-only sign-cert, and verify-cert."""
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
        need(type(doc) is dict
             and (args[0] == "sign-cert" or canonical(doc) == raw),
             "TRANSPORT_METADATA_NONCANONICAL")
    except (binascii.Error, ValueError, UnicodeError) as exc:
        raise ForwardV3Denied("F139_FRESH_FORWARD_V3_TRANSPORT_INVALID") from exc
    key = os.environ["F139_WORKER_HMAC_KEY"]
    if args[0] == "sign-cert":
        signed = dict(doc, owner_signature=sign(doc, key))
        path = Path(args[1])
        need(path.name == NAME and not path.exists() and not path.is_symlink(),
             "TRANSPORT_CERT_ALREADY_EXISTS")
        with path.open("xb") as stream:
            stream.write(canonical(signed))
            stream.flush()
            os.fsync(stream.fileno())
        print("F139_FRESH_FORWARD_V3_SIGNED_CREATE_ONLY")
        return
    need(len(args[1]) > 0 and args[1].endswith("state.sqlite"),
         "TRANSPORT_EXPECTED_DATABASE_INVALID")
    from f139.local_controller import Database, GitHub, SingleOwner
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
                need(set(doc) == {
                    "head", "candidate", "pr_number",
                    "regression_run_id", "source_run_id", "rehearsal_run_id",
                }, "TRANSPORT_PREFLIGHT_FIELDS")
                unsigned = preflight_v3_unsigned(db, api, release, key, **doc)
                print(canonical(unsigned).decode("utf-8"))
            else:
                need(doc == {"expected_source_sha": doc.get("expected_source_sha")}
                     and sha40(doc["expected_source_sha"]),
                     "TRANSPORT_VERIFY_INPUT_INVALID")
                result = inspect_installed_v3(db, api, release, key)
                need(result[0] == doc["expected_source_sha"],
                     "TRANSPORT_VERIFY_SOURCE_DRIFT")
                print("F139_FRESH_FORWARD_V3_OWNER_CUSTODY_VERIFIED")
        finally:
            db.close()


if __name__ == "__main__":
    _transport_main()
