"""F137 Windows wake bootstrap: bounded development-only fallback, never science evidence.

Executed inside the existing F136 controller after an independently initiated
workflow_dispatch. A successful decision permits at most one existing synthetic
development workflow dispatch, not first-use science or a genuine schedule claim.
"""
import datetime as dt
import re
import f136_succession as f

CONTROLLER=".github/workflows/forge-development-succession.yml"
NONCE=re.compile(r"^[a-f0-9]{32}$")
SOURCE=re.compile(r"^[a-f0-9]{40}$")
DEVELOPMENT=f.WORKFLOW
OWNER="spoonman136668-ai"
MAX_WAKE_AGE=dt.timedelta(minutes=5)
QUIET_FOR=dt.timedelta(minutes=9)
COMPLETION_GRACE=dt.timedelta(minutes=5)
WAKE_COLLISION=dt.timedelta(minutes=10)


def decision(wake, integrated, wake_runs, main_sha, pinned_sha, nonce, now,
             paused=False, enabled=False):
    """Fail closed on untrusted indexes and permit only a bounded idle bootstrap."""
    freeze, digest=f.frozen()
    f.need(type(now) is dt.datetime and now.tzinfo is not None,
           "F137_CLOCK_INVALID")
    now=now.astimezone(dt.timezone.utc)
    f.need(type(main_sha) is str and SOURCE.fullmatch(main_sha)
           and pinned_sha==main_sha, "F137_MAIN_SOURCE_DRIFT")
    f.need(type(nonce) is str and NONCE.fullmatch(nonce),
           "F137_WAKE_NONCE_INVALID")
    f.need(type(wake) is dict and
           wake.get("repository",{}).get("full_name")==f.REPO and
           wake.get("head_repository",{}).get("full_name")==f.REPO and
           wake.get("path")==CONTROLLER and
           wake.get("head_branch")=="main" and
           wake.get("head_sha")==main_sha and
           wake.get("event")=="workflow_dispatch" and
           wake.get("status")=="in_progress" and
           wake.get("run_attempt")==1 and
           type(wake.get("id")) is int and wake["id"]>0 and
           wake.get("actor",{}).get("login")==OWNER and
           wake.get("triggering_actor",{}).get("login")==OWNER,
           "F137_WAKE_PROVIDER_IDENTITY_INVALID")
    created=f.stamp(wake.get("created_at"))
    f.need(now-dt.timedelta(minutes=2)<=now and
           created<=now+dt.timedelta(minutes=2) and
           now-created<=MAX_WAKE_AGE, "F137_WAKE_STALE_OR_FUTURE")

    f.need(type(integrated) is dict and
           type(integrated.get("total_count")) is int and
           type(integrated.get("workflow_runs")) is list,
           "F137_INTEGRATED_HISTORY_INVALID")
    rows=integrated["workflow_runs"]
    f.need(1<=len(rows)<=300 and len(rows)<=integrated["total_count"] and
           len({x.get("id") for x in rows if type(x) is dict})==len(rows),
           "F137_INTEGRATED_HISTORY_BOUNDS")
    # When history cannot demonstrate a full UTC day, daily-cap proof fails.
    f.need(f.stamp(rows[-1]["created_at"]).date()<now.date(),
           "F137_DAILY_HISTORY_INCOMPLETE")
    for x in rows:
        f.need(type(x) is dict and type(x.get("id")) is int and
               x.get("head_branch")=="main" and
               x.get("head_sha") is not None and
               type(x.get("created_at")) is str and
               x.get("event") in ("schedule","workflow_dispatch","push","pull_request") and
               x.get("status") in ("completed","in_progress","queued",
                                  "requested","pending","waiting"),
               "F137_UNTRUSTED_INTEGRATED_ROW")
        f.need(f.stamp(x["created_at"])<=now+dt.timedelta(minutes=2),
               "F137_FUTURE_INTEGRATED_RUN")
    dates=[f.stamp(x["created_at"]) for x in rows]
    f.need(dates==sorted(dates,reverse=True), "F137_UNSORTED_HISTORY")

    f.need(type(wake_runs) is dict and
           type(wake_runs.get("total_count")) is int and
           type(wake_runs.get("workflow_runs")) is list,
           "F137_WAKE_HISTORY_INVALID")
    other=wake_runs["workflow_runs"]
    f.need(1<=len(other)<=100 and len(other)<=wake_runs["total_count"] and
           len({x.get("id") for x in other if type(x) is dict})==len(other) and
           any(x.get("id")==wake["id"] for x in other),
           "F137_WAKE_HISTORY_UNTRUSTED")
    for x in other:
        f.need(type(x) is dict and type(x.get("id")) is int and
               x.get("event")=="workflow_dispatch" and
               x.get("head_branch")=="main" and
               type(x.get("created_at")) is str,
               "F137_OTHER_WAKE_IDENTITY")
        f.need(f.stamp(x["created_at"])<=now+dt.timedelta(minutes=2),
               "F137_OTHER_WAKE_FUTURE")
    # If the first page is saturated within the collision horizon we cannot
    # prove we observed every competing wake; avoid any dispatch.
    oldest_wake=min(f.stamp(x["created_at"]) for x in other)
    f.need(len(other)<100 or now-oldest_wake>WAKE_COLLISION,
           "F137_WAKE_HISTORY_TRUNCATED")

    daily_count=sum(x["event"] in ("schedule","workflow_dispatch")
                    and f.stamp(x["created_at"]).date()==now.date()
                    for x in rows)
    reasons=[]
    if not enabled: reasons.append("OPERATOR_ENABLE_NOT_GRANTED")
    if paused: reasons.append("OPERATOR_PAUSED")
    if daily_count>=freeze["max_daily_initiated_development_cycles"]:
        reasons.append("DAILY_START_CAP")
    if any(x["status"]!="completed" for x in rows):
        reasons.append("INTEGRATED_RUN_ACTIVE")
    if now-max(dates)<QUIET_FOR:
        reasons.append("RECENT_INTEGRATED_RUN")
    if any(x.get("conclusion")=="success" and
           f.stamp(x.get("updated_at"))>now-COMPLETION_GRACE
           for x in rows):
        reasons.append("COMPLETION_CONTROLLER_GRACE")
    if any(x["id"]!=wake["id"] and
           now-f.stamp(x["created_at"])<WAKE_COLLISION
           for x in other):
        reasons.append("COMPETING_WAKE")
    # Preserve the frozen near-fallback veto; this mechanism is only a
    # fallback and must not displace a forthcoming legitimate schedule.
    sec=(7*60-(now.minute*60+now.second))%(10*60)
    if sec<=120: reasons.append("FALLBACK_SLOT_IMMINENT")
    return {
        "schema":"forge.autonomy.f137.windows-development-wake.v1",
        "dispatch":not reasons,"reasons":reasons,
        "controller_run_id":wake["id"],"wake_nonce":nonce,
        "source_sha":main_sha,"utc_day":str(now.date()),
        "daily_starts":daily_count,
        "daily_cap":freeze["max_daily_initiated_development_cycles"],
        "frozen_f136_sha256":digest,
        "origin":"f137-windows-recovery",
        "scientific_first_use_authorized":False,
        "genuine_schedule_claim":False,
        "accepted_ref_mutations":0,"science_originals":0,
        "codex_calls":0,"paid_api_calls":0,
    }
