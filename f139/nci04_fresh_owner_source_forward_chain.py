"""Generalized create-only V5+ source-forward certificate chain for FORGE F139.

Eliminates per-release boilerplate (`v5.py`, `v6.py`, ...) while preserving
100% of FORGE's fail-closed custody guarantees:
- Every certificate `fresh-original-owner-source-forward-v{N}.json` (N >= 5)
  uses distinct HMAC domain separation
  `b"FORGE-F139-FRESH-ORIGINAL-OWNER-SOURCE-FORWARD-V{N}\\0"`.
- Recursively verifies the entire immutable certificate chain
  `v{N} -> v{N-1} -> ... -> v4 -> v3 -> v2 -> v1` on every tick.
- Enforces create-only certificate signing (`"xb"`), exact protected `main`,
  merged owner PR, all 12 CI checks, owner Issue #1830 comment,
  `FORGE-CODEX-REMOTE` run custody, and cold SQLite verified prefix.
- Supports clean anchoring across an interrupted in-flight publication tail
  without deleting or mutating any SQLite history.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import re

from f139.nci04_fresh_owner_source_forward import FORGE
from f139.nci04_fresh_owner_source_forward_v2 import (
    CI_JOBS, FIELDS, OWNER_JOB, PREFIX, WORKFLOW,
    _qualified_run, _sealed, pos, sha40, sha64,
)
from f139.nci04_fresh_owner_source_forward_v4 import (
    NAME as V4_NAME, ForwardV4Denied, inspect_v4,
)
from f139.nci04_fresh_worker_protocol import SOURCE
from f139.nci04_native_contract import canonical, digest

MIN_CHAIN_VERSION = 5
MAX_CHAIN_VERSION = 99
PR_FLOOR = 1915
CERT_NAME_RE = re.compile(r"^fresh-original-owner-source-forward-v([0-9]+)\.json\Z")


class ForwardChainDenied(ValueError):
    """Fail-closed denial for invalid generalized V5+ certificate chain."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise ForwardChainDenied("F139_FRESH_FORWARD_CHAIN_" + reason)


def version_schema(version: int) -> str:
    need(type(version) is int and MIN_CHAIN_VERSION <= version <= MAX_CHAIN_VERSION,
         "VERSION_OUT_OF_RANGE")
    return f"forge.f139.fresh-original-owner-source-forward.v{version}"


def version_domain(version: int) -> bytes:
    need(type(version) is int and MIN_CHAIN_VERSION <= version <= MAX_CHAIN_VERSION,
         "VERSION_OUT_OF_RANGE")
    return f"FORGE-F139-FRESH-ORIGINAL-OWNER-SOURCE-FORWARD-V{version}\0".encode("ascii")


def version_filename(version: int) -> str:
    need(type(version) is int and 2 <= version <= MAX_CHAIN_VERSION,
         "VERSION_OUT_OF_RANGE")
    return f"fresh-original-owner-source-forward-v{version}.json"


def highest_installed_chain_version(folder: Path) -> int | None:
    """Return the highest installed V5+ certificate version in `folder`, or None."""
    if not folder.is_dir():
        return None
    versions: list[int] = []
    for entry in folder.iterdir():
        m = CERT_NAME_RE.fullmatch(entry.name)
        if m:
            ver = int(m.group(1))
            if ver >= MIN_CHAIN_VERSION:
                versions.append(ver)
    return max(versions) if versions else None


def sign_version(unsigned: dict, key: str, version: int) -> str:
    need(type(unsigned) is dict and set(unsigned) == FIELDS - {"owner_signature"}
         and type(key) is str and 32 <= len(key) <= 4096,
         "SIGNING_INPUT_INVALID")
    return hmac.new(key.encode(), version_domain(version) + canonical(unsigned),
                    hashlib.sha256).hexdigest()


def _verify_prior_chain(
    folder: Path, *, prior_version: int, db, api, release, key,
    expected_current_source_sha: str,
) -> tuple[tuple[str, str], dict, bytes]:
    """Verify archived v{prior_version} all the way down to v1."""
    from f139.nci04_fresh_owner_source_forward import NAME as V1_NAME
    from f139.nci04_fresh_owner_source_forward_v2 import NAME as V2_NAME
    from f139.nci04_fresh_owner_source_forward_v3 import NAME as V3_NAME

    if prior_version == 4:
        prev_v4, raw_v4 = _sealed(folder / V4_NAME)
        prev_v3, raw_v3 = _sealed(folder / V3_NAME)
        prev_v2, raw_v2 = _sealed(folder / V2_NAME)
        prev_v1, raw_v1 = _sealed(folder / V1_NAME)
        try:
            src = inspect_v4(
                prev_v4, db=db, api=api, release=release, key=key,
                previous_v3=prev_v3, previous_v3_bytes=raw_v3,
                previous_v2=prev_v2, previous_v2_bytes=raw_v2,
                previous_v1=prev_v1, previous_v1_bytes=raw_v1,
                expected_current_source_sha=expected_current_source_sha,
            )
        except ForwardV4Denied as exc:
            raise ForwardChainDenied("F139_FRESH_FORWARD_CHAIN_PRIOR_V4_INVALID") from exc
        return src, prev_v4, raw_v4

    need(prior_version >= MIN_CHAIN_VERSION, "UNSUPPORTED_PRIOR_VERSION")
    prev_doc, raw_prev = _sealed(folder / version_filename(prior_version))
    src = inspect_chain_version(
        prev_doc, version=prior_version, folder=folder,
        db=db, api=api, release=release, key=key,
        expected_current_source_sha=expected_current_source_sha,
    )
    return src, prev_doc, raw_prev


def inspect_chain_version(
    doc: dict, *, version: int, folder: Path, db, api, release, key,
    expected_current_source_sha: str | None = None,
) -> tuple[str, str]:
    """Authenticate V{version} (N >= 5) + entire archived chain down to V1."""
    schema = version_schema(version)
    need(type(doc) is dict and set(doc) == FIELDS
         and doc["schema"] == schema
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
         and type(doc["terminal_seq"]) is int and doc["terminal_seq"] >= 157
         and type(doc["terminal_count"]) is int and 12 <= doc["terminal_count"] <= 4096
         and type(doc["last_ticket"]) is str and 0 < len(doc["last_ticket"]) <= 160
         and doc["development_only"] is True
         and doc["worker_release_unchanged"] is True
         and doc["scientific_first_use"] is False
         and type(doc["paid_model_calls"]) is int and doc["paid_model_calls"] == 0,
         "EXACT_SIGNED_SCOPE_INVALID")
    actual = sign_version({k: v for k, v in doc.items() if k != "owner_signature"}, key, version)
    need(hmac.compare_digest(actual, doc["owner_signature"]),
         "OWNER_SIGNATURE_INVALID")

    current = (doc["owner_source_sha"] if expected_current_source_sha is None
               else expected_current_source_sha)
    need(sha40(current), "EXPECTED_CURRENT_SOURCE_INVALID")

    prior_source, prev_doc, raw_prev = _verify_prior_chain(
        folder, prior_version=version - 1, db=db, api=api, release=release,
        key=key, expected_current_source_sha=current,
    )
    need(digest(raw_prev) == doc["previous_certificate_sha256"]
         and prev_doc.get("owner_source_sha") == doc["previous_owner_source_sha"]
         and prev_doc.get("owner_source_tree") == doc["previous_owner_source_tree"]
         and prior_source == (doc["previous_owner_source_sha"], doc["previous_owner_source_tree"]),
         "PRIOR_CERTIFICATE_CHAIN_DRIFT")

    from f139.nci04_fresh_lifecycle import CUSTODY_KIND, read_lifecycle
    _, entries = read_lifecycle(db, key)
    meta = db.meta()
    seq = doc["terminal_seq"]
    row = db.conn.execute("SELECT kind,sha FROM events WHERE seq=?", (seq,)).fetchone()
    nterm = db.conn.execute(
        "SELECT COUNT(*) FROM events WHERE kind=? AND seq<=?",
        (CUSTODY_KIND, seq)).fetchone()[0]
    need(meta["head_seq"] >= seq and row is not None
         and row["sha"] == doc["terminal_hash"]
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
         and branch.get("commit", {}).get("sha") == current
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


def inspect_installed_chain(db, api, release, key) -> tuple[str, str]:
    """Verify the highest installed V5+ certificate and its complete prior chain."""
    folder = db.filename.parent
    ver = highest_installed_chain_version(folder)
    need(ver is not None, "CHAIN_CERTIFICATE_NOT_INSTALLED")
    doc, _ = _sealed(folder / version_filename(ver))
    return inspect_chain_version(
        doc, version=ver, folder=folder, db=db, api=api, release=release, key=key,
    )


def preflight_chain_unsigned(
    db, api, release, key, *, version: int, head: str, candidate: str,
    regression_run_id: int, source_run_id: int, rehearsal_run_id: int,
    pr_number: int,
) -> dict:
    """Generate unsigned V{version} metadata after cold locked chain+SQLite audit."""
    from f139.local_controller import SingleOwner
    from f139.nci04_fresh_lifecycle import CUSTODY_KIND, read_lifecycle

    schema = version_schema(version)
    need(SingleOwner.held(db.filename.with_suffix(".lock")),
         "PREFLIGHT_ORIGINAL_KERNEL_LOCK_REQUIRED")
    need(sha40(candidate) and sha40(head)
         and type(pr_number) is int and pr_number >= PR_FLOOR
         and all(pos(x) for x in (regression_run_id, source_run_id, rehearsal_run_id)),
         "PREFLIGHT_ARGUMENTS_INVALID")
    folder = db.filename.parent
    target_cert = folder / version_filename(version)
    need(not target_cert.exists() and not target_cert.is_symlink(),
         "PREFLIGHT_CERT_ALREADY_PRESENT")

    prior_source, _, raw_prev = _verify_prior_chain(
        folder, prior_version=version - 1, db=db, api=api, release=release,
        key=key, expected_current_source_sha=candidate,
    )
    need(prior_source[0] != candidate, "PREFLIGHT_CANDIDATE_SAME_AS_PRIOR")

    _, entries = read_lifecycle(db, key)
    meta = db.meta()
    seq = meta["head_seq"]
    event = db.conn.execute("SELECT kind,sha FROM events WHERE seq=?", (seq,)).fetchone()
    count = db.conn.execute(
        "SELECT COUNT(*) FROM events WHERE kind=? AND seq<=?",
        (CUSTODY_KIND, seq)).fetchone()[0]
    verified_entries = [
        e for e in entries if e["stage"] == "VERIFIED" and not e.get("negative")
    ]
    need(seq >= 157 and count >= 12 and len(verified_entries) == count
         and len(entries) in (count, count + 1)
         and event is not None and event["sha"] == meta["head_hash"]
         and all(not e.get("negative") for e in entries)
         and all(e["stage"] == "VERIFIED" and not e.get("negative")
                 for e in entries[:count]),
         "PREFLIGHT_NOT_CLEAN_VERIFIED_COLD_TERMINAL")

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
        "schema": schema, "admission_source_sha": SOURCE,
        "worker_release_sha": release["worker_release_sha"],
        "previous_certificate_sha256": digest(raw_prev),
        "previous_owner_source_sha": prior_source[0],
        "previous_owner_source_tree": prior_source[1],
        "owner_source_sha": candidate,
        "owner_source_tree": commit["tree"]["sha"],
        "pr_number": pr_number, "pr_head_sha": head,
        **runs,
        "terminal_seq": seq, "terminal_hash": event["sha"],
        "terminal_count": count,
        "last_ticket": entries[count - 1]["record"]["ticket"],
        "task_name": "FORGE-F139-UnifiedController",
        "development_only": True, "worker_release_unchanged": True,
        "scientific_first_use": False, "paid_model_calls": 0,
    }


def _transport_main(argv=None):
    """Owned Windows CLI for V5+ preflight, create-only sign-cert, and verify-cert."""
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
        raise ForwardChainDenied("F139_FRESH_FORWARD_CHAIN_TRANSPORT_INVALID") from exc
    key = os.environ["F139_WORKER_HMAC_KEY"]
    if args[0] == "sign-cert":
        path = Path(args[1])
        m = CERT_NAME_RE.fullmatch(path.name)
        need(m is not None, "TRANSPORT_CERT_FILENAME_INVALID")
        ver = int(m.group(1))
        need(doc.get("schema") == version_schema(ver), "TRANSPORT_SCHEMA_VERSION_MISMATCH")
        signed = dict(doc, owner_signature=sign_version(doc, key, ver))
        need(not path.exists() and not path.is_symlink(), "TRANSPORT_CERT_ALREADY_EXISTS")
        with path.open("xb") as stream:
            stream.write(canonical(signed))
            stream.flush()
            os.fsync(stream.fileno())
        print(f"F139_FRESH_FORWARD_V{ver}_SIGNED_CREATE_ONLY")
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
                    "version", "head", "candidate", "pr_number",
                    "regression_run_id", "source_run_id", "rehearsal_run_id",
                }, "TRANSPORT_PREFLIGHT_FIELDS")
                unsigned = preflight_chain_unsigned(db, api, release, key, **doc)
                print(canonical(unsigned).decode("utf-8"))
            else:
                need(doc == {"expected_source_sha": doc.get("expected_source_sha")}
                     and sha40(doc["expected_source_sha"]),
                     "TRANSPORT_VERIFY_INPUT_INVALID")
                ver = highest_installed_chain_version(database.parent)
                need(ver is not None, "TRANSPORT_NO_CHAIN_CERT")
                result = inspect_installed_chain(db, api, release, key)
                need(result[0] == doc["expected_source_sha"],
                     "TRANSPORT_VERIFY_SOURCE_DRIFT")
                print(f"F139_FRESH_FORWARD_V{ver}_OWNER_CUSTODY_VERIFIED")
        finally:
            db.close()


if __name__ == "__main__":
    _transport_main()
