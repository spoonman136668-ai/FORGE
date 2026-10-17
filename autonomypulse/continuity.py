#!/usr/bin/env python3
"""Read-only, independently check two completed scheduled FORGE lane observations.

Green push, PR and manual runs never count. This checks operational supervision,
not science admission, first-use custody or dispatch authority.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request

REPOSITORY = "spoonman136668-ai/FORGE"
WORKFLOW = "forge-native-autonomy-supervision.yml"
ARTIFACT = "forge-native-autonomy-operational-verified-only"
SOURCE_PATHS = (
    ".github/workflows/" + WORKFLOW,
    "autonomypulse/pulse.py",
    "autonomypulse/test_pulse.py",
    "autonomypulse/continuity.py",
)
API_ROOT = "https://api.github.com/repos/" + REPOSITORY
SHA40 = re.compile(r"^[a-f0-9]{40}$")
SHA256 = re.compile(r"^sha256:[a-f0-9]{64}$")
SCHEMA = "forge.autonomy.native-schedule-continuity.v1"
MAX_BODY = 500000

class EvidenceError(ValueError):
    pass

def require(condition, reason):
    if not condition:
        raise EvidenceError(reason)

def utc(value):
    require(isinstance(value, str), "UNVERIFIED_TIMESTAMP")
    try:
        date = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("UNVERIFIED_TIMESTAMP") from exc
    require(date.tzinfo is not None, "TIMEZONE_MISSING")
    return date.astimezone(dt.timezone.utc)

class API:
    def __init__(self, token):
        require(bool(token), "TOKEN_MISSING")
        self.token = token
        self.calls = 0
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        self.opener = urllib.request.build_opener(NoRedirect())

    def get(self, path):
        require(isinstance(path, str) and path.startswith("/") and
                not path.startswith("//") and ".." not in path and
                len(path) < 500 and "://" not in path,
                "UNSAFE_API_PATH")
        self.calls += 1
        require(self.calls <= 24, "API_BUDGET_EXCEEDED")
        url = API_ROOT + path
        req = urllib.request.Request(url, method="GET", headers={
            "Authorization": "Bearer " + self.token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "FORGE-native-continuity-qualification",
        })
        try:
            with self.opener.open(req, timeout=12) as reply:
                require(reply.status == 200 and reply.url == url,
                        "ORIGIN_OR_STATUS_UNVERIFIED")
                raw = reply.read(MAX_BODY + 1)
        except (OSError, urllib.error.URLError) as exc:
            raise EvidenceError("API_ORIGIN_UNAVAILABLE") from exc
        require(0 < len(raw) <= MAX_BODY, "UNVERIFIED_RESPONSE_SIZE")
        def unique(pairs):
            result = {}
            for k, v in pairs:
                require(k not in result, "DUPLICATE_JSON_KEY")
                result[k] = v
            return result
        data = json.loads(raw, object_pairs_hook=unique)
        require(type(data) is dict, "API_OBJECT_REQUIRED")
        return data

def source_blob(api, sha, path):
    require(isinstance(sha, str) and SHA40.fullmatch(sha) is not None,
            "SHA_INVALID")
    data = api.get("/contents/" + path + "?ref=" + sha)
    blob = data.get("sha")
    require(data.get("type") == "file" and isinstance(blob, str) and
            SHA40.fullmatch(blob) is not None, "SOURCE_BLOB_UNVERIFIED")
    return blob

def acknowledge_previous_failed_observation(report):
    """Acknowledge one bounded *negative* without qualifying continuity.

    A healthy current read-only observation can survive an old failed run.
    This never proves science or cross-run continuity: qualification still
    requires two distinct genuinely scheduled successful marked observations.
    """
    require(type(report) is dict and set(report) == {
        "schema", "qualified", "status", "reason", "science_dispatches",
        "scientific_first_use_authorized", "ckb_plane_accessed"},
        "NEGATIVE_REPORT_SCHEMA_UNVERIFIED")
    require(report["schema"] == SCHEMA and
            report["qualified"] is False and
            report["status"] == "QUARANTINED_UNVERIFIED" and
            report["reason"] == "RECENT_SCHEDULE_UNSUCCESSFUL_OR_UNVERIFIED" and
            type(report["science_dispatches"]) is int and
            report["science_dispatches"] == 0 and
            report["scientific_first_use_authorized"] is False and
            report["ckb_plane_accessed"] is False,
            "NEGATIVE_OBSERVATION_NOT_NARROWLY_ADMISSIBLE")
    return "HISTORICAL_SUPERVISION_FAILURE_ACKNOWLEDGED_NO_CONTINUITY_OR_SCIENCE"


def artifact(api, run_id, head_sha):
    data = api.get("/actions/runs/" + str(run_id) + "/artifacts?per_page=100")
    rows = data.get("artifacts")
    require(isinstance(rows, list) and len(rows) <= 100,
            "ARTIFACT_LIST_INVALID")
    matches = [a for a in rows if isinstance(a, dict) and a.get("name") == ARTIFACT]
    require(len(matches) == 1, "ARTIFACT_NOT_UNIQUE")
    a = matches[0]
    source = a.get("workflow_run") or {}
    require(a.get("expired") is False and isinstance(a.get("id"), int) and
            isinstance(a.get("size_in_bytes"), int) and a["size_in_bytes"] > 0 and
            isinstance(a.get("digest"), str) and SHA256.fullmatch(a["digest"]) and
            source.get("id") == run_id and source.get("head_branch") == "main" and
            source.get("head_sha") == head_sha,
            "ARTIFACT_PROVENANCE_UNVERIFIED")
    return {"id": a["id"], "sha256": a["digest"]}

def qualify(api, now, current_sha, current_run_id=None):
    require(isinstance(current_sha, str) and SHA40.fullmatch(current_sha),
            "CURRENT_SOURCE_SHA_INVALID")
    wf = api.get("/actions/workflows/" + WORKFLOW)
    workflow_id = wf.get("id")
    require(isinstance(workflow_id, int) and workflow_id > 0 and
            wf.get("path") == ".github/workflows/" + WORKFLOW and
            wf.get("state") == "active", "WORKFLOW_IDENTITY_UNVERIFIED")
    page = api.get("/actions/workflows/" + str(workflow_id) + "/runs?event=schedule&per_page=25")
    rows = page.get("workflow_runs")
    require(isinstance(rows, list) and len(rows) <= 100,
            "SCHEDULE_HISTORY_UNVERIFIED")
    relevant = [r for r in rows if isinstance(r, dict) and
                r.get("workflow_id") == workflow_id]
    ids = [r.get("id") for r in relevant]
    require(len(set(ids)) == len(ids), "REPEATED_SCHEDULE_RUN_ID")
    # GitHub lists the currently executing scheduled job before its artifact
    # exists. It is not historical completed evidence and must not poison
    # a genuine earlier successful pair. Only exclude the exact trusted
    # GITHUB_RUN_ID after checking its immutable origin and in-flight status.
    current_excluded = False
    if current_run_id is not None:
        require(type(current_run_id) is int and current_run_id > 0,
                "CURRENT_RUN_ID_INVALID")
        own = [r for r in relevant if r.get("id") == current_run_id]
        if own:
            active = own[0]
            require(active.get("event") == "schedule" and
                    active.get("workflow_id") == workflow_id and
                    active.get("head_branch") == "main" and
                    active.get("head_sha") == current_sha and
                    active.get("run_attempt") == 1 and
                    active.get("status") in ("queued", "in_progress", "waiting") and
                    active.get("conclusion") is None,
                    "CURRENT_RUN_SELF_IDENTITY_UNVERIFIED")
            relevant = [r for r in relevant if r.get("id") != current_run_id]
            current_excluded = True
    if len(relevant) < 2:
        return {"status": "PENDING_TWO_COMPLETED_SCHEDULED_RUNS",
                "scheduled_runs_found": len(relevant),
                "qualified": False, "current_scheduled_run_excluded": current_excluded,
                "observations": []}
    selected = sorted(relevant,
                      key=lambda r: utc(r.get("created_at")), reverse=True)[:2]
    # Failed earlier observations must be reported as failed BEFORE
    # irregular scheduling is assessed. A delayed GitHub schedule may bring
    # two runs less than three hours apart; this cannot change the negative
    # into an unacknowledgeable cadence error and recreate a failure loop.
    # A genuine cadence violation for two successful runs stays blocked.
    for recent in selected:
        require(recent.get("status") == "completed" and
                recent.get("conclusion") == "success" and
                recent.get("run_attempt") == 1 and
                recent.get("event") == "schedule" and
                recent.get("head_branch") == "main",
                "RECENT_SCHEDULE_UNSUCCESSFUL_OR_UNVERIFIED")
    interval = (utc(selected[0]["created_at"]) -
                utc(selected[1]["created_at"])).total_seconds()
    age = (now - utc(selected[0]["updated_at"])).total_seconds()
    require(3 * 3600 <= interval <= 9 * 3600 and 0 <= age <= 9 * 3600,
            "SCHEDULE_CADENCE_OR_FRESHNESS_UNVERIFIED")
    identities = {path: source_blob(api, current_sha, path)
                  for path in SOURCE_PATHS}
    observations = []
    for r in selected:
        run_id, sha = r.get("id"), r.get("head_sha")
        require(type(run_id) is int and run_id > 0 and
                isinstance(sha, str) and SHA40.fullmatch(sha) is not None and
                r.get("workflow_id") == workflow_id and
                r.get("event") == "schedule" and
                r.get("head_branch") == "main" and
                r.get("status") == "completed" and
                r.get("conclusion") == "success" and
                r.get("run_attempt") == 1,
                "RECENT_SCHEDULE_UNSUCCESSFUL_OR_UNVERIFIED")
        start, stop = utc(r.get("created_at")), utc(r.get("updated_at"))
        require(start <= stop <= now, "SCHEDULE_CLOCK_UNVERIFIED")
        for path, blob in identities.items():
            require(source_blob(api, sha, path) == blob,
                    "QUALIFICATION_SOURCE_DRIFT")
        observations.append({"run_id": run_id, "head_sha": sha,
                             "created_at": start.isoformat(),
                             "artifact": artifact(api, run_id, sha)})
    observations.reverse()
    return {"status": "QUALIFIED_TWO_COMPLETED_SCHEDULED_OBSERVATIONS",
            "scheduled_runs_found": len(relevant), "qualified": True,
            "current_scheduled_run_excluded": current_excluded,
            "source_blob_sha": identities, "observations": observations}

def report(api, now=None, current_sha=None, current_run_id=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    require(now.tzinfo is not None, "CLOCK_TIMEZONE_REQUIRED")
    if current_sha is None:
        current_sha = os.environ.get("GITHUB_SHA", "")
    if current_run_id is None and os.environ.get("GITHUB_RUN_ID"):
        raw_id = os.environ["GITHUB_RUN_ID"]
        require(re.fullmatch(r"[1-9][0-9]{6,17}", raw_id) is not None,
                "CURRENT_RUN_ID_INVALID")
        current_run_id = int(raw_id)
    evidence = qualify(api, now, current_sha, current_run_id=current_run_id)
    return {"schema": SCHEMA, "observed_at_utc": now.isoformat(),
            "repository": REPOSITORY, "workflow": WORKFLOW, **evidence,
            "scientific_evidence_authenticated": False,
            "scientific_first_use_authorized": False,
            "science_dispatches": 0, "accepted_ref_mutations": 0,
            "optimizer_promotions": 0, "ckb_plane_accessed": False}

if __name__ == "__main__":
    try:
        data = report(API(os.environ.get("GH_TOKEN", "")))
        print(json.dumps(data, sort_keys=True, separators=(",", ":")))
        print("FORGE_NATIVE_CONTINUITY=" + data["status"])
    except (EvidenceError, ValueError, TypeError, KeyError, UnicodeError) as error:
        print(json.dumps({"schema": SCHEMA, "qualified": False,
                          "status": "QUARANTINED_UNVERIFIED",
                          "reason": str(error),
                          "science_dispatches": 0,
                          "scientific_first_use_authorized": False,
                          "ckb_plane_accessed": False}, sort_keys=True))
        raise SystemExit(1)
