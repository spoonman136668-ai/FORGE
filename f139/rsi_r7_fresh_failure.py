"""Bounded, read-only discovery of *new* FORGE R6 repair opportunities.

Development-only. This does not run an owner tick, dispatch a worker, mutate
SQLite, publish a PR, or authorize the FORGE-self lane. A caller-provided
consumed set is advisory; original owner durable no-replay custody is NOT
established by this scanner.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from f139.local_controller import GitHub, REPO
from f139.rsi_r6_known_repair_cycle import (
    PATH, HEAD, DIGEST, RepairDenied,
)
from f139.rsi_r6_provider_readback import Readback, acquire

SCHEMA = "forge.f139.rsi-r7.readonly-fresh-failure-discovery.v1"
JOB_NAMES = frozenset({"windows_f139", "windows_native",
                       "original-owner-cold-audit"})
MAX_PAGES = 2
PER_PAGE = 30
MAX_RELEVANT_RUNS = 8


class DiscoveryDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise DiscoveryDenied("F139_RSI_R7_" + code)


def utc(value: str) -> datetime:
    need(type(value) is str and len(value) == 20
         and value.endswith("Z"), "UTC_FORMAT")
    try:
        stamp = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise DiscoveryDenied("F139_RSI_R7_UTC_INVALID") from exc
    return stamp.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class Report:
    schema: str
    after_run_id: int
    not_before_utc: str
    target_path: str
    examined_run_ids: tuple[int, ...]
    rejection_codes: tuple[tuple[int, str], ...]
    proposals: tuple[Readback, ...]
    # Two bounded pages are never proof that no newer failures exist.
    complete_repository_history: bool = False
    original_owner_admitted: bool = False
    repair_source_qualified: bool = False
    authorized_to_dispatch: bool = False
    scientific_first_use: bool = False
    deployed: bool = False
    autonomous_rsi_proven: bool = False


def scan(*, provider: GitHub, after_run_id: int, not_before_utc: str,
         target_path: str, consumed_scopes: frozenset[str]) -> Report:
    """Review at most eight new main/push failures from two fixed GET pages.

    The caller must independently authenticate/anchor the cutoff and complete
    original owner no-replay ledger before ANY later effect. No read result is
    an approval or new scientific/RSI acceptance.
    """
    need(type(provider) is GitHub, "PROVIDER_TYPE")
    need(type(after_run_id) is int and after_run_id > 0, "RUN_CUTOFF")
    threshold = utc(not_before_utc)
    need(type(target_path) is str and PATH.fullmatch(target_path) is not None,
         "TARGET_NOT_ALLOWLISTED")
    need(type(consumed_scopes) is frozenset
         and all(type(x) is str and DIGEST.fullmatch(x) is not None
                 for x in consumed_scopes), "CONSUMED_INPUT_INVALID")

    base = "repos/" + REPO + "/"
    seen: set[int] = set()
    examined: list[int] = []
    rejected: list[tuple[int, str]] = []
    accepted: list[Readback] = []
    for page in range(1, MAX_PAGES + 1):
        catalog = provider.get(
            base + "actions/runs?branch=main&event=push&status=failure&per_page=" +
            str(PER_PAGE) + "&page=" + str(page))
        need(type(catalog) is dict and type(catalog.get("workflow_runs")) is list
             and len(catalog["workflow_runs"]) <= PER_PAGE,
             "RUN_CATALOG_INVALID")
        for run in catalog["workflow_runs"]:
            need(type(run) is dict and type(run.get("id")) is int
                 and run["id"] > 0 and run["id"] not in seen,
                 "RUN_DUPLICATE_OR_INVALID")
            rid = run["id"]
            seen.add(rid)
            # A provider that ignores the server filters cannot silently
            # dilute discovery or certify an empty main/push result.
            need(run.get("event") == "push"
                 and run.get("head_branch") == "main"
                 and run.get("status") == "completed"
                 and run.get("conclusion") == "failure",
                 "FILTERED_RUN_SCOPE_DRIFT")
            if rid <= after_run_id:
                continue
            created = utc(run.get("created_at"))
            if created <= threshold:
                continue
            need(type(run.get("head_sha")) is str
                 and HEAD.fullmatch(run["head_sha"]) is not None
                 and run.get("status") == "completed"
                 and run.get("conclusion") == "failure"
                 and run.get("run_attempt") == 1
                 and type(run.get("repository")) is dict
                 and run["repository"].get("full_name") == REPO
                 and type(run.get("head_repository")) is dict
                 and run["head_repository"].get("full_name") == REPO
                 and type(run.get("actor")) is dict
                 and run["actor"].get("login") == "spoonman136668-ai",
                 "RUN_ORIGIN_UNVERIFIED")
            need(len(examined) < MAX_RELEVANT_RUNS,
                 "BOUND_REACHED_NO_EXHAUSTIVE_CLAIM")
            examined.append(rid)
            index = provider.get(
                base + "actions/runs/" + str(rid) + "/jobs?per_page=100")
            need(type(index) is dict
                 and type(index.get("total_count")) is int
                 and 0 <= index["total_count"] <= 100
                 and type(index.get("jobs")) is list
                 and len(index["jobs"]) == index["total_count"],
                 "JOB_CATALOG_INCOMPLETE")
            for job in index["jobs"]:
                need(type(job) is dict
                     and type(job.get("id")) is int
                     and job.get("run_id") == rid,
                     "JOB_RUN_IDENTITY_DRIFT")
            selected = [job for job in index["jobs"]
                        if job.get("name") in JOB_NAMES
                        and job.get("conclusion") == "failure"
                        and job.get("status") == "completed"]
            if not selected:
                rejected.append((rid, "NO_MATCHING_FAILED_WINDOWS_JOB"))
                continue
            need(len(selected) == 1, "AMBIGUOUS_FAILED_WINDOWS_JOB")
            try:
                row = acquire(
                    provider=provider, run_id=rid,
                    job_id=selected[0]["id"], path=target_path,
                    expected_head=run["head_sha"],
                    consumed_scopes=consumed_scopes)
            except RepairDenied as exc:
                # Expected unsupported/consumed authentic failures are retained
                # as negatives. Never retry, infer success or print raw logs.
                rejected.append((rid, str(exc)))
                continue
            accepted.append(row)
    return Report(SCHEMA, after_run_id, not_before_utc, target_path,
                  tuple(examined), tuple(rejected), tuple(accepted))
