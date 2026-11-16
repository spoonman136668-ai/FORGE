"""Fail-closed, GET-only evidence join for the original V44 rehearsal.

This is an engineering input to a future original-owner V45 release design,
not a release permission or fresh observation of the installed Windows task.
The original V44 log must still be checked separately for proof bytes.
"""
from __future__ import annotations

from f139 import nci04_v42_owner_source_readiness as readiness
from f139 import nci04_v44_event1836_copy_rehearsal as v44

SCHEMA = "forge.f139.v45.original-v44-rehearsal-remote-gate.v1"
V44_MAIN = "aef92773f342f9c4d82c1cd441919b2b16e4b6e4"
V44_COMMENT = 6917006014
V44_RUN = 43870931448
V44_JOB = 133311600131
V44_JOB_NAME = "v44-original-owner-copy-rehearsal"
V44_WORKFLOW = "FORGE G54 guarded V9 original-owner cutover"
V43_JOB_NAME = "v43-original-owner-cold-backup"
V43_JOB = 133297431631


class V45ReadinessDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise V45ReadinessDenied("F139_V45_READINESS_" + code)


def _get(get, path):
    need(callable(get) and type(path) is str and
         path.startswith("repos/" + readiness.REPO + "/"),
         "PROVIDER_SCOPE")
    data = get(path)
    need(type(data) is dict, "PROVIDER_OBJECT")
    return data


def _single_successful_job(get, prefix, run_id, job_id, name):
    jobs = _get(get, prefix + "actions/runs/" + str(run_id) +
                "/jobs?per_page=100")
    rows = jobs.get("jobs")
    need(type(rows) is list and
         type(jobs.get("total_count")) is int and
         jobs["total_count"] == len(rows) and len(rows) <= 100,
         "COMPLETE_JOBS_LIST_REQUIRED")
    found = [j for j in rows if type(j) is dict and
             j.get("name") == name]
    need(len(found) == 1 and found[0].get("id") == job_id and
         found[0].get("run_id") == run_id and
         found[0].get("conclusion") == "success" and
         found[0].get("status") == "completed" and
         found[0].get("runner_name") == "FORGE-CODEX-REMOTE",
         "EXACT_SUCCESSFUL_ORIGINAL_JOB_REQUIRED")


def _snapshot(get, main_sha):
    p = "repos/" + readiness.REPO + "/"
    main = _get(get, p + "branches/main")
    need(main.get("name") == "main" and
         main.get("protected") is True and
         main.get("commit", {}).get("sha") == main_sha,
         "PROTECTED_MAIN_DRIFT")
    cmp = _get(get, p + "compare/" + V44_MAIN + "..." +
               main_sha + "?per_page=1&page=2")
    need(cmp.get("status") in ("ahead", "identical") and
         cmp.get("behind_by") == 0 and
         cmp.get("merge_base_commit", {}).get("sha") == V44_MAIN,
         "V44_MAIN_ANCESTRY_MISSING")
    comment = _get(get, p + "issues/comments/" + str(V44_COMMENT))
    need(comment.get("id") == V44_COMMENT and
         comment.get("body") == "F139-V44-COPY-REHEARSAL " +
         V44_MAIN + " " + v44.RELEASE_SOURCE + " 6916414055" and
         comment.get("user", {}).get("login") == readiness.OWNER and
         comment.get("author_association") == "OWNER" and
         comment.get("issue_url") ==
         "https://api.github.com/repos/" + readiness.REPO + "/issues/807",
         "ORIGINAL_OWNER_COMMENT_NOT_AUTHENTIC")
    run = _get(get, p + "actions/runs/" + str(V44_RUN))
    need(run.get("id") == V44_RUN and
         run.get("name") == V44_WORKFLOW and
         run.get("head_sha") == V44_MAIN and
         run.get("event") == "issue_comment" and
         run.get("status") == "completed" and
         run.get("conclusion") == "success" and
         run.get("run_attempt") == 1 and
         run.get("actor", {}).get("login") == readiness.OWNER,
         "V44_FIRST_ATTEMPT_RUN_NOT_SUCCESSFUL")
    _single_successful_job(get, p, V44_RUN, V44_JOB, V44_JOB_NAME)
    backup = _get(get, p + "actions/runs/" + str(v44.BACKUP_RUN))
    need(backup.get("id") == v44.BACKUP_RUN and
         backup.get("name") == V44_WORKFLOW and
         backup.get("head_sha") == v44.RELEASE_SOURCE and
         backup.get("event") == "issue_comment" and
         backup.get("status") == "completed" and
         backup.get("conclusion") == "success" and
         backup.get("run_attempt") == 1 and
         backup.get("actor", {}).get("login") == readiness.OWNER,
         "V43_BACKUP_FIRST_ATTEMPT_FAILED")
    _single_successful_job(get, p, v44.BACKUP_RUN, V43_JOB, V43_JOB_NAME)
    readiness._policy(get)
    return (main_sha, V44_MAIN, V44_COMMENT, V44_RUN, V44_JOB,
            v44.BACKUP_RUN, V43_JOB, v44.RELEASE_SOURCE)


def qualify(get, *, main_sha):
    """Twice-recheck public custody; never mutate main, the owner or policy."""
    need(type(main_sha) is str and
         readiness.SHA40.fullmatch(main_sha) is not None,
         "MAIN_SHA_INVALID")
    first = _snapshot(get, main_sha)
    second = _snapshot(get, main_sha)
    need(first == second, "REMOTE_EVIDENCE_CHANGED")
    return {
        "schema": SCHEMA,
        "workflow_main_sha": main_sha,
        "prior_rehearsal_source_sha": V44_MAIN,
        "target_source_sha": v44.RELEASE_SOURCE,
        "original_source_sha": readiness.BEFORE,
        "v44_owner_comment_id": V44_COMMENT,
        "v44_run_id": V44_RUN,
        "v44_original_owner_job_id": V44_JOB,
        "v43_backup_run_id": v44.BACKUP_RUN,
        "v43_original_owner_job_id": V43_JOB,
        "v44_original_job_status": "success",
        "v43_backup_job_status": "success",
        "original_database_freshly_read": False,
        "v44_receipt_log_independently_parsed": False,
        "live_source_transition_authorized": False,
        "original_task_mutations": 0,
        "original_sqlite_mutations": 0,
        "new_dispatches": 0,
        "scientific_first_use": False,
    }
