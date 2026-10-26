"""F139 G35 — authenticated GitHub CLI provider observation for a future V2 run.

NO dispatch, ticket minting, credentials in candidate code, owner ledger writes,
source transition, science admission or assumption that G34 PR artifacts are real
native work. MUST be invoked only by the existing authorized original owner.
"""
from __future__ import annotations

import io
import json
import re
import zipfile

from f139.local_controller import GitHub, REPO, WORKFLOW, parse_time
from f139.nci04_native_contract import digest
from f139.nci04_provider_receipt_v2 import verify_v2_provider_zip
from f139.nci04_signed_native import NativeAdmission

OWNER_WORKFLOW_ID = 388797257
OWNER_REPOSITORY_ID = 1413298198
RUN_JOB_V2 = "native-execute-v2 ("
AUTH_JOB_V2 = "native-authorize-v2"
ARTIFACT_PREFIX = "forge-f139-v2-native-receipt-"
INNER_FILENAME = "f139-v2-development-provider.zip"
OS_LABELS = ("ubuntu-latest", "windows-latest")
MAX_OUTER_BYTES = 2_500_000
MAX_INNER_BYTES = 2_000_000
DIGEST = re.compile(r"sha256:[a-f0-9]{64}\Z")


class G35ProviderDenied(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise G35ProviderDenied("F139_G35_" + message)


def _extract_inner(raw: bytes, outer_sha256: str) -> bytes:
    require(type(raw) is bytes and 0 < len(raw) <= MAX_OUTER_BYTES
            and type(outer_sha256) is str
            and DIGEST.fullmatch(outer_sha256) is not None
            and outer_sha256 == "sha256:" + digest(raw),
            "OUTER_GITHUB_ARTIFACT_BYTES_OR_DIGEST_DRIFT")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            require(len(entries) == 1
                    and entries[0].filename == INNER_FILENAME
                    and not entries[0].is_dir()
                    and not (entries[0].flag_bits & 1)
                    and 0 < entries[0].file_size < MAX_INNER_BYTES
                    and 0 < entries[0].compress_size < MAX_OUTER_BYTES,
                    "OUTER_SINGLE_V2_MEMBER_REQUIRED")
            inner = archive.read(INNER_FILENAME)
    except G35ProviderDenied:
        raise
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile,
            zipfile.LargeZipFile) as exc:
        raise G35ProviderDenied("F139_G35_OUTER_ARTIFACT_ZIP_UNREADABLE") from exc
    require(type(inner) is bytes and 0 < len(inner) < MAX_INNER_BYTES,
            "INNER_V2_ZIP_BOUNDS_INVALID")
    return inner


def inspect_v2_provider_run(api: GitHub, *, run_id: int, ticket: str,
                            started_at: str, admissions: dict) -> dict:
    """Original owner's read-only Github API + exact V2 inner ZIP audit.

    The caller must separately verify SQLite admission, native V2 permit,
    exclusive original owner lock and installed source. This function never
    reports a terminal, success of unattended work or science authority.
    """
    require(isinstance(api, GitHub)
            and type(run_id) is int and run_id > 0
            and isinstance(ticket, str) and ticket.startswith("f139-nci04-")
            and type(admissions) is dict and set(admissions) == set(OS_LABELS)
            and all(isinstance(admissions[label], NativeAdmission)
                    and admissions[label].ticket == ticket
                    and admissions[label].runner_os == label
                    and admissions[label].run_id == run_id
                    for label in OS_LABELS),
            "ORIGINAL_PROVIDER_CLIENT_AND_SIGNED_ADMISSIONS_REQUIRED")
    base = admissions[OS_LABELS[0]]
    require(all(admissions[label].source_sha == base.source_sha
                and admissions[label].intent == base.intent
                and admissions[label].lane == base.lane == "Yggdrasil"
                and admissions[label].issue_number == base.issue_number
                and admissions[label].issue_id == base.issue_id
                and admissions[label].authorization_sha256 ==
                    base.authorization_sha256 for label in OS_LABELS),
            "SIGNED_CROSS_OS_CANDIDATE_DRIFT")
    path = "repos/" + REPO + "/actions/runs/" + str(run_id)
    run = api.get(path)
    require(type(run) is dict
            and type(run.get("id")) is int and run["id"] == run_id
            and run.get("display_title") == "F139 " + ticket
            and run.get("name") == "F139 " + ticket
            and run.get("event") == "workflow_dispatch"
            and run.get("workflow_id") == OWNER_WORKFLOW_ID
            and run.get("path") == ".github/workflows/" + WORKFLOW
            and run.get("head_sha") == base.source_sha
            and run.get("head_branch") in (
                "main", "f139-owner-release-" + base.source_sha)
            and type(run.get("run_attempt")) is int
            and run["run_attempt"] == 1
            and type(run.get("repository")) is dict
            and run["repository"].get("id") == OWNER_REPOSITORY_ID
            and run["repository"].get("full_name") == REPO,
            "ORIGINAL_WORKFLOW_EVENT_SOURCE_OR_VERSION_DRIFT")
    try:
        started = parse_time(started_at)
        created = parse_time(run["created_at"])
        from datetime import timedelta
        require(created >= started - timedelta(minutes=2),
                "RUN_PRECEDES_REAL_ORIGINAL_DISPATCH")
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        raise G35ProviderDenied("F139_G35_PROVIDER_CLOCK_INVALID") from exc
    require(run.get("status") == "completed"
            and run.get("conclusion") in ("success", "failure"),
            "RUN_NOT_TERMINAL_OR_CUSTODY_RETRY_UNSAFE")
    jobs_doc = api.get(path + "/jobs?per_page=100")
    artifacts_doc = api.get(path + "/artifacts?per_page=100")
    jobs = jobs_doc.get("jobs") if type(jobs_doc) is dict else None
    arts = artifacts_doc.get("artifacts") if type(artifacts_doc) is dict else None
    require(type(jobs) is list and 3 <= len(jobs) <= 10
            and jobs_doc.get("total_count") == len(jobs)
            and type(arts) is list and len(arts) == 2
            and artifacts_doc.get("total_count") == len(arts),
            "PROVIDER_JOB_ARTIFACT_INVENTORY_INCOMPLETE_OR_EXTRA")
    # GitHub includes skipped old V1 jobs in the same workflow run. Those
    # are required to remain skipped, not absent by assumption. Accept
    # only known legacy job identities, never arbitrary extra execution.
    live = {AUTH_JOB_V2} | {
        RUN_JOB_V2 + label + ")" for label in OS_LABELS}
    legacy_skipped = {
        "execute", "execute (ubuntu-latest)", "execute (windows-latest)",
        "native-authorize", "native-execute",
        "native-execute (ubuntu-latest)",
        "native-execute (windows-latest)",
    }
    names = [j.get("name") for j in jobs]
    require(len(set(names)) == len(names)
            and all(isinstance(j, dict)
                    and (j.get("name") in live or
                         (j.get("name") in legacy_skipped
                          and j.get("status") == "completed"
                          and j.get("conclusion") == "skipped"))
                    for j in jobs),
            "UNEXPECTED_OR_LIVE_V1_JOB_ON_V2_RUN")
    authorizers = [j for j in jobs if j.get("name") == AUTH_JOB_V2]
    require(len(authorizers) == 1
            and authorizers[0].get("status") == "completed"
            and authorizers[0].get("conclusion") == "success"
            and type(authorizers[0].get("id")) is int
            and authorizers[0]["id"] > 0,
            "SEPARATE_V2_AUTHORIZER_NOT_VERIFIED")
    parts = {}
    verified_jobs = {}
    outer_archives = {}
    for label in OS_LABELS:
        matching = [j for j in jobs
                    if j.get("name") == RUN_JOB_V2 + label + ")"]
        require(len(matching) == 1
                and matching[0].get("status") == "completed"
                and matching[0].get("conclusion") in ("success", "failure")
                and type(matching[0].get("id")) is int
                and matching[0]["id"] > 0,
                "V2_OS_WORKER_JOB_NOT_VERIFIED")
        name = ARTIFACT_PREFIX + label
        matches = [a for a in arts if a.get("name") == name]
        require(len(matches) == 1, "V2_OS_ARTIFACT_NOT_UNIQUE")
        meta = matches[0]
        require(type(meta.get("id")) is int and meta["id"] > 0
                and meta.get("expired") is False
                and type(meta.get("size_in_bytes")) is int
                and 0 < meta["size_in_bytes"] <= MAX_OUTER_BYTES
                and isinstance(meta.get("digest"), str)
                and DIGEST.fullmatch(meta["digest"]) is not None
                and type(meta.get("workflow_run")) is dict
                and meta["workflow_run"].get("id") == run_id
                and meta["workflow_run"].get("repository_id") ==
                    OWNER_REPOSITORY_ID
                and meta["workflow_run"].get("head_repository_id") ==
                    OWNER_REPOSITORY_ID
                and meta["workflow_run"].get("head_sha") ==
                    base.source_sha,
                "V2_OS_ARTIFACT_PROVIDER_IDENTITY_DRIFT")
        raw = api.artifact(meta["id"])
        require(type(raw) is bytes
                and len(raw) == meta["size_in_bytes"],
                "V2_GITHUB_ARTIFACT_SIZE_MISMATCH")
        inner = _extract_inner(raw, meta["digest"])
        # Actual authenticated outer GitHub artifact bytes, retained by
        # the existing original-owner crash-safe evidence store in G38.
        outer_archives[label] = raw
        signed = admissions[label]
        g14_meta = {
            "digest": "sha256:" + digest(inner),
            "size_in_bytes": len(inner),
            "run_id": signed.run_id,
            "runner_os": label,
            "source_sha": signed.source_sha,
        }
        check = verify_v2_provider_zip(
            inner, g14_meta, signed, require_qualified=False)
        expected_job = "success" if check["qualified"] else "failure"
        require(matching[0]["conclusion"] == expected_job,
                "V2_REPORT_JOB_CONCLUSION_MISMATCH")
        parts[label] = {
            "zip_bytes": inner, "metadata": g14_meta,
        }
        verified_jobs[label] = {
            "job_id": matching[0]["id"],
            "artifact_id": meta["id"],
            "outer_artifact_sha256": digest(raw),
            "inner_v2_sha256": digest(inner),
            "development_qualified": check["qualified"],
        }
    qualified = all(verified_jobs[x]["development_qualified"]
                    for x in OS_LABELS)
    require(run["conclusion"] == ("success" if qualified else "failure"),
            "RUN_CONCLUSION_AND_V2_RESULTS_DIVERGE")
    return {
        "schema": "forge.f139.g35.original-provider-v2-review.v1",
        "ticket": ticket, "run_id": run_id,
        "source_sha": base.source_sha,
        "authorize_job_id": authorizers[0]["id"],
        "platforms": verified_jobs,
        "provider_payloads": parts,
        "outer_archives": outer_archives,
        "both_platforms_development_qualified": qualified,
        "disposition": ("V2_PROVIDER_POSITIVE_NOT_TERMINAL" if qualified
                        else "V2_PROVIDER_NEGATIVE_RETAINED"),
        "provider_api_metadata_crosschecked": True,
        "original_ledger_and_v2_permit_independently_verified": False,
        "original_terminal_written": False,
        "unattended_progression_verified": False,
        "scientific_first_use_authorized": False,
    }
