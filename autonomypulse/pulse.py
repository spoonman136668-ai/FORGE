#!/usr/bin/env python3
"""FORGE-native unattended operational supervision for two real research lanes.

This is a source/continuation health pulse, NOT science-admission, a CKB-plane
client, a worker dispatcher, or an optimizer. No PUT/POST/PATCH/DELETE.
Each lane can be quarantined without suppressing the other's diagnostics.
"""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SCHEMA="forge.autonomy.native-lane-supervision.v1"
LANES=(("Wingless","spoonman136668-ai/Wingless"),
       ("Yggdrasil","spoonman136668-ai/Yggdrasil"))
HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")
API="https://api.github.com/repos/"
MAX_BODY=600000
STALE_AFTER_SECONDS=24*3600

class Blocked(ValueError):
    def __init__(self,reason):
        super().__init__("FORGE_AUTONOMY_"+reason)
def need(value,reason):
    if not value:raise Blocked(reason)
def parse_utc(value):
    need(type(value) is str and 12<len(value)<75,"INVALID_TIME")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:raise Blocked("INVALID_TIME") from exc
    need(dt.tzinfo is not None,"TIMEZONE_NOT_GROUNDED")
    return dt.astimezone(timezone.utc)
def strict_json(raw):
    def unique(pairs):
        obj={}
        for k,v in pairs:
            need(k not in obj,"DUPLICATE_JSON_KEY")
            obj[k]=v
        return obj
    return json.loads(raw,object_pairs_hook=unique,
      parse_constant=lambda _:(_ for _ in ()).throw(Blocked("NONFINITE_JSON")))
def no_redirect():
    class NoneRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*a,**kw):return None
    return urllib.request.build_opener(NoneRedirect())
class GitHub:
    def __init__(self,token=""):
        self.token=token
        self.opener=no_redirect()
        self.calls=0
    def get(self,repo,route):
        need(repo in dict((r,l) for l,r in LANES),"FOREIGN_REPOSITORY")
        need(type(route) is str and len(route)<500 and route.startswith("/")
             and not route.startswith("//") and ".." not in route and
             "#" not in route and "://" not in route,"UNSAFE_API_ROUTE")
        self.calls+=1
        need(self.calls<=24,"REQUEST_BUDGET_EXCEEDED")
        url=API+repo+route
        hdr={"Accept":"application/vnd.github+json",
             "X-GitHub-Api-Version":"2022-11-28",
             "User-Agent":"FORGE-NATIVE-AUTONOMY-SUPERVISION"}
        if self.token:hdr["Authorization"]="Bearer "+self.token
        req=urllib.request.Request(url,headers=hdr,method="GET")
        try:
            with self.opener.open(req,timeout=14) as rsp:
                need(rsp.status==200 and rsp.url==url,"REDIRECT_OR_BAD_STATUS")
                raw=rsp.read(MAX_BODY+1)
        except (OSError,urllib.error.URLError) as exc:
            raise Blocked("ORIGIN_UNREACHABLE") from exc
        need(0<len(raw)<=MAX_BODY,"OVERSIZE_OR_EMPTY_RESPONSE")
        obj=strict_json(raw.decode("utf-8-sig"))
        need(type(obj) is dict,"API_EXPECTED_OBJECT")
        return obj
def source_file(api,repo,sha,path):
    need(type(sha) is str and HEX40.fullmatch(sha),"SOURCE_SHA_INVALID")
    obj=api.get(repo,"/contents/"+path+"?ref="+sha)
    need(obj.get("type")=="file" and obj.get("encoding")=="base64"
         and type(obj.get("content")) is str and
         obj.get("size",0)<=65536,"PINNED_FILE_INVALID")
    try:raw=base64.b64decode(obj["content"],validate=False)
    except ValueError as exc:raise Blocked("BASE64_SOURCE_INVALID") from exc
    need(0<len(raw)<=65536,"PINNED_FILE_SIZE_INVALID")
    v=strict_json(raw.decode("utf-8-sig"))
    need(type(v) is dict,"PINNED_JSON_NOT_OBJECT")
    return v
def lane(api,program,repo,now):
    need((program,repo) in LANES,"INVALID_LANE")
    main=api.get(repo,"/branches/main")
    main_sha=main.get("commit",{}).get("sha")
    need(type(main_sha) is str and HEX40.fullmatch(main_sha),"MAIN_SHA_INVALID")
    cfg=source_file(api,repo,main_sha,".research-autonomy/config.json")
    need(cfg.get("schema")=="research.autonomy.v2" and
         cfg.get("program")==program and cfg.get("enabled") is True and
         cfg.get("authority")=="research-only" and
         cfg.get("ckb_plane_role")=="governance-only" and
         cfg.get("mode")=="repo-local-self-chain" and
         type(cfg.get("north_star_sha256")) is str and
         HEX64.fullmatch(cfg["north_star_sha256"]),
         "RESEARCH_ONLY_AUTHORITY_DRIFT")
    branch=cfg.get("active_branch")
    need(type(branch) is str and len(branch)<120 and
         branch.startswith("research/autonomy-") and
         re.fullmatch(r"[a-z0-9/_-]+",branch),"ACTIVE_BRANCH_UNSAFE")
    active=api.get(repo,"/branches/"+branch)
    source=active.get("commit",{}).get("sha")
    need(type(source) is str and HEX40.fullmatch(source),"ACTIVE_SOURCE_INVALID")
    state=source_file(api,repo,source,".research-autonomy/state.json")
    need(state.get("schema")=="research.repo-local-state.v1"
         and state.get("program")==program
         and state.get("active_branch")==branch
         and state.get("north_star_sha256")==cfg["north_star_sha256"]
         and state.get("authority")=="research-only"
         and state.get("ckb_plane_role")=="governance-only"
         and type(state.get("experiment")) is str
         and 0<len(state["experiment"])<=200
         and type(state.get("classification")) is str
         and 0<len(state["classification"])<=100,
         "RESEARCH_STATE_INVALID")
    run_id=state.get("github_run_id")
    need((type(run_id) is str and re.fullmatch(r"[1-9][0-9]{7,15}",run_id))
         or (type(run_id) is int and run_id>=10000000),
         "STATE_RUN_UNQUALIFIED")
    run_id=int(run_id)
    run=api.get(repo,"/actions/runs/"+str(run_id))
    need(run.get("id")==run_id and
         run.get("name")==program+" research continuation launcher" and
         type(run.get("workflow_id")) is int and run["workflow_id"]>0 and
         run.get("status")=="completed" and
         run.get("conclusion")=="success" and
         run.get("head_branch")=="main" and
         run.get("run_attempt")==1 and
         type(run.get("head_sha")) is str and
         HEX40.fullmatch(run["head_sha"]),
         "COMPLETED_RUN_SOURCE_UNVERIFIED")
    created=parse_utc(run.get("created_at"))
    completed=parse_utc(run.get("updated_at"))
    finished=parse_utc(state.get("last_completed_utc"))
    need(created<=finished<=completed and completed<=now
         and (now-completed).total_seconds()>=0,
         "RUN_COMPLETION_TIME_CONFLICT")
    # GitHub should still possess the exact historical main commit that
    # produced the state even if current main advanced since that run.
    commit=api.get(repo,"/commits/"+run["head_sha"])
    need(commit.get("sha")==run["head_sha"],"RUN_COMMIT_UNAVAILABLE")
    # A previously successful state run cannot prove current continuity.
    # Read only the bounded workflow-specific history; a newer failure, rerun,
    # or in-flight attempt is a real degraded research-continuation condition.
    need(cfg.get("controller_workflow")=="research-auto-launch.yml",
         "CONTINUATION_WORKFLOW_IDENTITY_DRIFT")
    history=api.get(repo,"/actions/workflows/research-auto-launch.yml/runs?per_page=10")
    attempts=history.get("workflow_runs")
    need(type(attempts) is list and 0<len(attempts)<=10,
         "CONTINUATION_ATTEMPT_HISTORY_UNVERIFIED")
    checked=[]
    observed_ids=set()
    for attempt in attempts:
        need(type(attempt) is dict and type(attempt.get("id")) is int and
             attempt["id"]>0 and attempt["id"] not in observed_ids and
             attempt.get("workflow_id")==run["workflow_id"] and
             attempt.get("name")==program+" research continuation launcher" and
             attempt.get("head_branch")=="main" and
             attempt.get("head_sha")==main_sha and
             type(attempt.get("head_sha")) is str and
             HEX40.fullmatch(attempt["head_sha"]) and
             attempt.get("event") in ("schedule","workflow_dispatch","workflow_run","push"),
             "CONTINUATION_ATTEMPT_IDENTITY_DRIFT")
        observed_ids.add(attempt["id"])
        stamp=parse_utc(attempt.get("created_at"))
        need(stamp<=now,"CONTINUATION_ATTEMPT_FUTURE_CLOCK")
        checked.append((stamp,attempt))
    latest_created,latest=max(checked,key=lambda x:(x[0],x[1]["id"]))
    need(latest_created>=created,"CONTINUATION_ATTEMPT_HISTORY_STALE")
    need(latest.get("status")=="completed" and
         latest.get("conclusion")=="success" and
         latest.get("run_attempt")==1,
         "LATEST_RESEARCH_CONTINUATION_NOT_SUCCESSFUL")
    latest_finished=parse_utc(latest.get("updated_at"))
    need(latest_created<=latest_finished<=now,
         "LATEST_CONTINUATION_CLOCK_UNVERIFIED")
    # A moving research branch is an explicit uncertainty, not a reason to
    # silently pair new state with a previously frozen source identity.
    again=api.get(repo,"/branches/"+branch)
    need(again.get("commit",{}).get("sha")==source,
         "RESEARCH_BRANCH_MOVED_DURING_READ")
    age=int((now-finished).total_seconds())
    classification=state["classification"]
    if classification=="qualified-scientific-result":
        disposition="REPO_REPORTED_QUALIFIED_NOT_INDEPENDENT_SCIENCE_ACCEPTANCE"
    elif classification=="preregistered-blocked":
        disposition="REPO_REPORTED_BLOCKED_DO_NOT_DISPATCH"
    else:
        disposition="UNKNOWN_OR_OTHER_RESEARCH_STATE_REQUIRES_REVIEW"
    return {
        "lane":program,"repository":repo,
        "main_sha":main_sha,"active_research_sha":source,
        "last_reported_run_id":run_id,
        "last_reported_run_source_sha":run["head_sha"],
        "latest_launcher_run_id":latest["id"],
        "latest_launcher_event":latest["event"],
        "latest_launcher_conclusion":latest["conclusion"],
        "latest_launcher_run_created_utc":latest_created.isoformat(),
        "last_experiment":state["experiment"],
        "reported_classification":classification,
        "last_reported_completion_utc":finished.isoformat(),
        "observed_age_seconds":age,
        "stale_over_24_hours":age>STALE_AFTER_SECONDS,
        "source_and_workflow_confirmed":True,
        "operational_disposition":disposition,
        "science_first_use_approved":False,
        "scientific_result_independently_accepted":False,
    }
def scan(api,now=None):
    now=now or datetime.now(timezone.utc)
    need(now.tzinfo is not None,"CLOCK_MISSING_TIMEZONE")
    results=[]
    for program,repo in LANES:
        try:results.append(lane(api,program,repo,now))
        except (Blocked,ValueError,TypeError,KeyError,UnicodeError,OSError) as exc:
            results.append({
                "lane":program,"repository":repo,
                "quarantine_reason":str(exc) if isinstance(exc,Blocked)
                     else "FORGE_AUTONOMY_UNVERIFIED_SOURCE_OR_ORIGIN",
                "source_and_workflow_confirmed":False,
                "operational_disposition":"QUARANTINED_UNVERIFIED_NO_REPLAY",
                "science_first_use_approved":False,
                "scientific_result_independently_accepted":False,
            })
    return {
        "schema":SCHEMA,
        "observed_at_utc":now.isoformat(),
        "lanes":results,
        "both_lanes_operationally_verified":all(
           x["source_and_workflow_confirmed"] for x in results),
        "separate_lanes_preserved":True,
        "mind_palace_only_optional_advisory_bridge":True,
        "ckb_plane_accessed":False,
        "workflow_mutations":0,
        "originals_dispatched":0,
        "first_use_claims_written":0,
        "owner_or_worker_permit_issued":False,
        "optimizer_policy_updated":False,
        "scientific_firstuse_authorized":False,
        "disposition":"SOURCE_SUPERVISION_ONLY_NO_SCIENTIFIC_RELEASE",
    }
if __name__=="__main__":
    report=scan(GitHub(os.getenv("GH_TOKEN","")))
    print(json.dumps(report,sort_keys=True,separators=(",",":")))
    print("FORGE_AUTONOMY_NATIVE_SUPERVISION="+
          ("VERIFIED" if report["both_lanes_operationally_verified"] else "QUARANTINED"))
    print("FORGE_AUTONOMY_FIRSTUSE_OR_SCIENCE_DISPATCH=DENIED")
    if not report["both_lanes_operationally_verified"]:
        raise SystemExit(1)
