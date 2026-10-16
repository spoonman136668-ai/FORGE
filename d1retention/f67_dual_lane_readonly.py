"""F67: live dual-lane GitHub research provenance / uncertain-run census.

No research runs, branches, refs, Cloudflare, controller or secrets are changed.
Github repo-local RESEARCH evidence is not independently witnessed once-only
ORIGINAL first-use custody. This gate cannot authorize protected science.
"""
from __future__ import annotations
import base64
from collections import Counter
from datetime import datetime, timezone
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

SCHEMA="forge.f67.github-two-lane-evidence-census.readonly.v1"
ORIGIN="https://api.github.com"
LANES=(("Wingless","spoonman136668-ai/Wingless"),
       ("Yggdrasil","spoonman136668-ai/Yggdrasil"))
HEX40=re.compile(r"[0-9a-f]{40}\Z")
HEX64=re.compile(r"[0-9a-f]{64}\Z")
RUN_ID=re.compile(r"[1-9][0-9]{7,15}\Z")
EVIDENCE=".research-autonomy/evidence/"
MAX_API_BYTES=1_800_000
class Blocked(ValueError):pass

def need(ok,why):
    if not ok:raise Blocked("F67_"+why)

def parsed_utc(v):
    need(type(v) is str and len(v)<90,"TIME_INVALID")
    try:
        ts=datetime.fromisoformat(v.replace("Z","+00:00"))
    except (TypeError,ValueError) as exc:
        raise Blocked("F67_TIME_INVALID") from exc
    need(ts.tzinfo is not None,"TIMEZONE_REQUIRED")
    return ts.astimezone(timezone.utc)

class GitHubReadonly:
    def __init__(self,token=""):
        self.token=token
        self.calls=0
        self.opener=urllib.request.build_opener(
          type("NoRedirect",(urllib.request.HTTPRedirectHandler,),{
            "redirect_request":lambda *args,**kwargs:None})())
    def get(self,repo,route):
        need(repo in dict((r,p) for p,r in LANES),"REPO_NOT_ALLOWLISTED")
        need(type(route) is str and len(route)<500 and route.startswith("/")
             and ".." not in route and not route.startswith("//"),
             "ROUTE_NOT_ALLOWLISTED")
        self.calls+=1
        need(self.calls<=35,"API_BUDGET_EXHAUSTED")
        url=ORIGIN+"/repos/"+repo+route
        headers={"Accept":"application/vnd.github+json",
                 "User-Agent":"FORGE-F67-READONLY-SCIENCE-CENSUS",
                 "X-GitHub-Api-Version":"2022-11-28"}
        if self.token:
            headers["Authorization"]="Bearer "+self.token
        request=urllib.request.Request(url,headers=headers,method="GET")
        try:
            with self.opener.open(request,timeout=15) as response:
                need(response.status==200 and response.url==url,
                     "GITHUB_API_REDIRECT_OR_STATUS")
                data=response.read(MAX_API_BYTES+1)
                need(0<len(data)<=MAX_API_BYTES,"API_PAYLOAD_SIZE")
                return json.loads(data.decode("utf-8"))
        except (urllib.error.URLError,TimeoutError) as exc:
            raise Blocked("F67_GITHUB_API_UNREACHABLE") from exc

def get_content(api,repo,path,sha):
    need(HEX40.fullmatch(sha) is not None,"CONTENT_SOURCE_SHA_INVALID")
    obj=api.get(repo,"/contents/"+path+"?ref="+sha)
    need(type(obj) is dict and obj.get("encoding")=="base64" and
         obj.get("type")=="file" and
         type(obj.get("content")) is str,"CONTENT_NOT_PINNED_FILE")
    try:
        raw=base64.b64decode(obj["content"],validate=False)
        doc=json.loads(raw.decode("utf-8-sig"))
    except (ValueError,UnicodeError) as exc:
        raise Blocked("F67_PINNED_CONTENT_MALFORMED") from exc
    need(type(doc) is dict,"DOCUMENT_NOT_OBJECT")
    return doc

def evidence_census(tree):
    need(type(tree) is dict and tree.get("truncated") is False
         and type(tree.get("tree")) is list and len(tree["tree"])<100000,
         "ACTIVE_BRANCH_TREE_INCOMPLETE")
    files=[]
    for obj in tree["tree"]:
        need(type(obj) is dict and type(obj.get("path")) is str and
             len(obj["path"])<500 and obj.get("type") in ("blob","tree"),
             "SOURCE_TREE_INVALID")
        path=obj["path"]
        if obj["type"]=="blob" and path.startswith(EVIDENCE):
            files.append(path[len(EVIDENCE):])
    need(files and len(files)<=30000,"RESEARCH_EVIDENCE_TREE_EMPTY_OR_UNBOUNDED")
    groups={}
    standalone=0
    for item in files:
        if "/" not in item:
            standalone+=1
            continue
        folder,leaf=item.split("/",1)
        need(folder and leaf and "/" not in leaf,"RESEARCH_EVIDENCE_NESTING_UNEXPECTED")
        groups.setdefault(folder,set()).add(leaf)
    dossiers=len(groups)
    summary=sum("summary.json" in s for s in groups.values())
    result=sum(bool(s & {"probe.json","result.json"}) for s in groups.values())
    missing=sum("summary.json" not in s for s in groups.values())
    return {
        "evidence_files_observed":len(files),
        "versioned_evidence_dossiers_observed":dossiers,
        "dossiers_with_summary":summary,
        "dossiers_with_probe_or_result":result,
        "dossiers_missing_summary":missing,
        "standalone_blocker_or_exception_evidence_files":standalone,
        "every_scientific_result_independently_authenticated":False,
    }

def audit_lane(program,repo,api):
    need((program,repo) in LANES,"LANE_INVALID")
    main=api.get(repo,"/branches/main")
    main_sha=main.get("commit",{}).get("sha")
    need(type(main_sha) is str and HEX40.fullmatch(main_sha) is not None,
         "MAIN_SOURCE_NOT_PINNED")
    config=get_content(api,repo,".research-autonomy/config.json",main_sha)
    need(config.get("schema")=="research.autonomy.v2"
         and config.get("program")==program
         and config.get("enabled") is True
         and config.get("authority")=="research-only"
         and config.get("ckb_plane_role")=="governance-only"
         and config.get("mode")=="repo-local-self-chain",
         "REPO_LOCAL_AUTHORITY_CONFIG_DRIFT")
    branch=config.get("active_branch")
    need(type(branch) is str and branch.startswith("research/autonomy-")
         and len(branch)<125 and re.fullmatch(r"[a-z0-9/_-]+",branch) is not None,
         "ACTIVE_BRANCH_UNSAFE")
    branch_obj=api.get(repo,"/branches/"+branch)
    sha=branch_obj.get("commit",{}).get("sha")
    need(type(sha) is str and HEX40.fullmatch(sha) is not None,
         "ACTIVE_RESEARCH_SOURCE_INVALID")
    state=get_content(api,repo,".research-autonomy/state.json",sha)
    need(state.get("schema")=="research.repo-local-state.v1"
         and state.get("program")==program
         and state.get("active_branch")==branch
         and state.get("north_star_sha256")==config.get("north_star_sha256")
         and state.get("north_star_path")==config.get("north_star_path")
         and state.get("authority")=="research-only"
         and state.get("ckb_plane_role")=="governance-only"
         and isinstance(state.get("experiment"),str)
         and 0<len(state["experiment"])<256
,"STATE_CONFIG_DRIFT")
    # GitHub-linked state run ID may be encoded as string OR number.
    run_id=state.get("github_run_id")
    need((type(run_id) is str and RUN_ID.fullmatch(run_id) is not None)
         or (type(run_id) is int and RUN_ID.fullmatch(str(run_id)) is not None),
         "LATEST_COMPLETED_RUN_ID_INVALID")
    run_id=int(run_id)
    qualified_sha=state.get("qualified_head_sha")
    need(type(qualified_sha) is str and HEX40.fullmatch(qualified_sha) is not None,
         "QUALIFIED_SCIENTIFIC_SOURCE_MISSING")
    need(type(config.get("north_star_sha256")) is str and
         HEX64.fullmatch(config["north_star_sha256"]) is not None,
         "NORTH_STAR_SOURCE_UNPINNED")
    run=api.get(repo,"/actions/runs/"+str(run_id))
    need(run.get("id")==run_id and
         run.get("head_sha")==main_sha and
         run.get("head_branch")=="main" and
         run.get("name")==program+" research continuation launcher" and
         run.get("status")=="completed" and
         run.get("conclusion")=="success",
         "SELF_REPORTED_RUN_NOT_GITHUB_CONFIRMED")
    last=parsed_utc(state.get("last_completed_utc"))
    need(parsed_utc(run.get("created_at"))<=last and
         last<=parsed_utc(run.get("updated_at")),
         "LATEST_COMPLETION_TIME_NOT_ORIGIN_BOUND")
    commit=api.get(repo,"/commits/"+qualified_sha)
    need(commit.get("sha")==qualified_sha,"QUALIFIED_SOURCE_COMMIT_NOT_FOUND")
    tree=api.get(repo,"/git/trees/"+sha+"?recursive=1")
    evidence=evidence_census(tree)
    listing=api.get(repo,"/actions/runs?per_page=100&page=1")
    need(type(listing) is dict and
         type(listing.get("total_count")) is int and
         listing["total_count"]>=0 and
         type(listing.get("workflow_runs")) is list and
         len(listing["workflow_runs"])<=100,"ACTIONS_WINDOW_INVALID")
    counts=Counter()
    uncertain=[]
    for entry in listing["workflow_runs"]:
        need(type(entry) is dict and
             entry.get("status") in ("completed","queued","in_progress","pending","requested","waiting"),
             "ACTIONS_STATUS_UNKNOWN")
        status=entry["status"]
        conclusion=entry.get("conclusion")
        if status=="completed":
            need(conclusion in ("success","failure","cancelled","timed_out",
                                 "skipped","neutral","action_required",
                                 "stale","startup_failure"),
                 "COMPLETED_CONCLUSION_UNKNOWN")
            counts["completed_"+conclusion]+=1
        else:
            counts["unresolved_"+status]+=1
        if (status!="completed" or conclusion not in ("success","skipped")):
            if len(uncertain)<12:
                uncertain.append({"run_id":entry["id"],
                                  "status":status,
                                  "conclusion":conclusion,
                                  "workflow_name":entry.get("name","")[:100]})
    # Detect source ref movement during read, but never force-stabilize science.
    again=api.get(repo,"/branches/"+branch)
    need(again.get("commit",{}).get("sha")==sha,
         "ACTIVE_RESEARCH_BRANCH_MOVED_DURING_CENSUS")
    return {
        "program":program,"repository":repo,
        "research_authority":"research-only",
        "repo_local_continuation_enabled":True,
        "ckb_plane_role":"governance-only",
        "main_control_sha":main_sha,
        "active_research_source_sha":sha,
        "last_reported_qualified_source_sha":qualified_sha,
        "last_completed_experiment":state["experiment"],
        "last_completed_workflow_run_id":run_id,
        "last_completed_run_github_confirmed":True,
        "evidence_inventory":evidence,
        "github_actions_total_run_count":listing["total_count"],
        "last_100_github_actions_status_counts":dict(sorted(counts.items())),
        "observed_failed_or_unresolved_runs":uncertain,
        "last_100_window_complete":listing["total_count"]<=100,
        "all_historical_run_pages_exhausted":listing["total_count"]<=100,
        "original_science_firstuse_lease_history_complete":False,
        "uncertain_scientific_original_attempts_all_resolved":False,
        "new_protected_original_authorized":False,
    }

def audit(api):
    lanes=[audit_lane(program,repo,api) for program,repo in LANES]
    need(len(lanes)==2 and lanes[0]["repository"]!=lanes[1]["repository"],
         "SINGLE_LANE_OR_DUPLICATE_REPO")
    return {
        "schema":SCHEMA,"lanes":lanes,
        "crosslane_architectures_remain_independent":True,
        "current_owner_epoch_and_research_firstuse_independently_proven":False,
        "all_active_consumed_uncertain_original_seed_leases_reconciled":False,
        "cloudflare_atomic_firstuse_deployed":False,
        "worker_execution_permit_issued":False,
        "new_scientific_originals_dispatched":0,
        "controller_cutover_authorized":False,
        "disposition":"REAL_REPO_LOCAL_RUNS_OBSERVED_FIRSTUSE_OWNER_AUTHORITY_STILL_BLOCKED",
    }

if __name__=="__main__":
    try:
        report=audit(GitHubReadonly(os.getenv("GITHUB_TOKEN","")))
        print(json.dumps(report,sort_keys=True,separators=(",",":")))
        print("F67_REAL_TWO_LANE_GITHUB_HISTORY=OBSERVED_NOT_FIRSTUSE_RELEASE")
    except (Blocked,ValueError,KeyError,TypeError) as exc:
        print("F67_LIVE_RESEARCH_AUDIT=BLOCKED",file=__import__("sys").stderr)
        print("F67_BLOCK_REASON="+(str(exc) if isinstance(exc,Blocked)
            else type(exc).__name__),file=__import__("sys").stderr)
        raise SystemExit(1)
