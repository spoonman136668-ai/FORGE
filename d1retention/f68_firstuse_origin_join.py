"""F68: join actual pinned original evidence to separately classified transport runs.

Source-only, current authenticated GitHub GET operations; never issue an original,
dispatch a workflow, mutate any repo, clear an uncertain seed, deploy D1 or mint
a worker permit. Historical GitHub artifacts do not independently authenticate
owner signing, prospective first-use or all seed leases.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import hashlib
import json
import re

import f67_dual_lane_readonly as f67

SCHEMA="forge.f68.real-original-vs-transport-custody-readonly.v1"
MANIFEST=Path(__file__).resolve().parents[1]/"reference/research-originals/20261013-dual-lane-manifest.json"
YGG="spoonman136668-ai/Yggdrasil"
EXPECTED={
    38869660982: ("transport_proxy","ckb-research-write-proxy-pump.yml","CKB proxy pump Yggdrasil 38869660982"),
    38864578731: ("transport_proxy","ckb-research-write-proxy-pump.yml","CKB proxy pump Yggdrasil 38864578731"),
    38868746675: ("research_continuation","research-auto-launch.yml","Yggdrasil research continuation launcher"),
}
EXACT_MANIFEST_LANES={"Wingless","Yggdrasil"}
HEX64=re.compile(r"^[0-9a-f]{64}$")

class Denied(ValueError):
    pass

def need(value,reason):
    if not value:raise Denied("F68_"+reason)

def file_manifest(path=MANIFEST):
    need(isinstance(path,Path) and path.is_file() and not path.is_symlink() and
         100<=path.stat().st_size<=32768,"MANIFEST_MISSING_OR_UNBOUNDED")
    raw=path.read_bytes()
    need(len(raw)==path.stat().st_size,"MANIFEST_CHANGED_DURING_READ")
    try: doc=json.loads(raw)
    except (ValueError,UnicodeError) as exc:raise Denied("F68_MANIFEST_INVALID_JSON") from exc
    need(type(doc) is dict and doc.get("schema")=="forge.original-evidence-inventory.v1"
         and type(doc.get("pins")) is list and len(doc["pins"])==2,"MANIFEST_SCHEMA_OR_LANE_COUNT")
    lanes=set()
    for p in doc["pins"]:
        need(type(p) is dict and p.get("lane") in EXACT_MANIFEST_LANES and
             p.get("lane") not in lanes and
             p.get("repo")=="spoonman136668-ai/"+p["lane"] and
             type(p.get("run_id")) is int and p["run_id"]>0 and
             type(p.get("artifact_id")) is int and p["artifact_id"]>0 and
             type(p.get("artifact_name")) is str and 0<len(p["artifact_name"])<150 and
             type(p.get("commit_sha")) is str and f67.HEX40.fullmatch(p["commit_sha"]) and
             type(p.get("raw_sha256")) is str and HEX64.fullmatch(p["raw_sha256"]),
             "MANIFEST_ORIGINAL_ID_INVALID")
        lanes.add(p["lane"])
    need(lanes==EXACT_MANIFEST_LANES,"MANIFEST_MISSING_LANE")
    return doc["pins"],hashlib.sha256(raw).hexdigest()

def verify_original(api,pin):
    repo=pin["repo"]
    run_id=pin["run_id"]
    run=api.get(repo,"/actions/runs/"+str(run_id))
    need(run.get("id")==run_id and
         run.get("head_sha")==pin["commit_sha"] and
         run.get("status")=="completed" and run.get("conclusion")=="success" and
         run.get("event")=="push" and
         type(run.get("path")) is str and
         run["path"].startswith(".github/workflows/qualify-") and
         run["path"].endswith(".yml"),
         "PINNED_ORIGINAL_WORKFLOW_DRIFT")
    artifacts=api.get(repo,"/actions/runs/"+str(run_id)+"/artifacts?per_page=100")
    need(type(artifacts) is dict and type(artifacts.get("artifacts")) is list and
         len(artifacts["artifacts"])<=100,"ORIGINAL_ARTIFACT_LIST_UNTRUSTED")
    candidates=[a for a in artifacts["artifacts"] if
                a.get("id")==pin["artifact_id"]]
    need(len(candidates)==1 and candidates[0].get("name")==pin["artifact_name"] and
         candidates[0].get("expired") is False and
         isinstance(candidates[0].get("size_in_bytes"),int) and
         candidates[0]["size_in_bytes"]>0 and
         type(candidates[0].get("digest")) is str and
         re.fullmatch(r"sha256:[0-9a-f]{64}",candidates[0]["digest"]),
         "ARCHIVE_METADATA_MISSING_OR_CHANGED")
    # A GitHub artifact ZIP digest ≠ the pinned scientific report/raw SHA.
    # This must never substitute for raw SHA, independent scientific
    # acceptance, external owner custody, or authorized first use.
    return {
        "lane":pin["lane"],
        "historical_original_run_id":run_id,
        "source_commit_sha":pin["commit_sha"],
        "archived_artifact_id":pin["artifact_id"],
        "github_zip_digest":candidates[0]["digest"],
        "github_original_workflow_metadata_verified":True,
        "pinned_artifact_metadata_and_nonexpiration_verified":True,
        "pinned_scientific_raw_sha256_content_verified_now":False,
        "independent_signed_original_firstuse_verified":False,
        "scientific_original_execution_authorized":False,
        "firstuse_replay_authorized":False,
    }

def verify_ygg_run(api,run_id,main_sha):
    kind,workflow,name=EXPECTED[run_id]
    r=api.get(YGG,"/actions/runs/"+str(run_id))
    need(type(r) is dict and r.get("id")==run_id and
         r.get("head_sha")==main_sha and
         r.get("head_branch")=="main" and
         r.get("path")==".github/workflows/"+workflow and
         r.get("name")==name and r.get("event")=="workflow_dispatch" and
         type(r.get("run_attempt")) is int and r.get("run_attempt")==1,
         "YGG_RUN_ORIGIN_OR_REATTEMPT_DRIFT")
    status=r.get("status")
    conclusion=r.get("conclusion")
    if status=="completed":
        need(conclusion in ("success","failure","cancelled","timed_out",
                            "skipped","neutral","action_required","stale","startup_failure"),
             "COMPLETED_STATUS_UNRECOGNIZED")
    else:
        need(status in ("in_progress","pending","queued","requested","waiting") and
             conclusion is None,"NONTERMINAL_RUN_CONCLUSION_CONFLICT")
    # None of the pinned Ygg run IDs is a protected scientific original;
    # even a future success for a proxy run remains transport-only.
    jobs=api.get(YGG,"/actions/runs/"+str(run_id)+"/jobs?per_page=100")
    need(type(jobs) is dict and type(jobs.get("jobs")) is list and
         len(jobs["jobs"])<=100,"JOB_CENSUS_INVALID")
    item=jobs["jobs"]
    expected_job="pump" if kind=="transport_proxy" else "cycle"
    need(len(item)<=1 and all(j.get("name")==expected_job and
         j.get("status") in ("queued","pending","in_progress","completed","waiting") and
         (j.get("conclusion") is None or
          j.get("conclusion") in ("success","failure","cancelled","skipped","timed_out"))
         for j in item),"JOB_ROLE_UNBOUND")
    if status=="completed":
        need(len(item)==1 and item[0]["status"]=="completed" and
             item[0]["conclusion"]==conclusion,"RUN_JOB_TERMINAL_MISMATCH")
    if status=="in_progress":
        need(len(item)==1 and item[0]["status"] in ("in_progress","completed"),
             "ACTIVE_PUMP_JOB_MISSING")
    if status in ("pending","queued","requested","waiting"):
        need(not item or all(j["status"] in ("queued","pending","waiting") for j in item),
             "PENDING_RUN_JOB_STATE_INVALID")
    category=("RESOURCE_LIMITED_RESEARCH_CONTINUATION_NO_NEW_RESULT"
              if kind=="research_continuation" and conclusion=="failure"
              else "UNRESOLVED_RESEARCH_TRANSPORT_NOT_SCIENTIFIC_ORIGINAL"
              if status!="completed"
              else "COMPLETED_RESEARCH_TRANSPORT_NOT_SCIENTIFIC_ORIGINAL"
              if kind=="transport_proxy"
              else "RESEARCH_CONTINUATION_NOT_PROTECTED_ORIGINAL")
    # The quota detail is additionally grounded by the independently
    # inspected job logs; GitHub run metadata ALONE proves only failure.
    return {
        "run_id":run_id,"kind":kind,
        "status":status,"conclusion":conclusion,
        "failure_cause_independently_verified_by_this_api":False,
        "classification":category,
        "scientific_original_workflow":False,
        "original_firstuse_consumed_by_transport":False,
        "original_execution_authorized":False,
        "retry_of_uncertain_original_authorized":False,
    }

def audit(api, pins=None):
    # F67 verifies both live repository-local research-only identities and
    # active branch source continuity. It never grants external science.
    prior=f67.audit(api)
    need(prior["schema"]==f67.SCHEMA and
         len(prior["lanes"])==2 and
         all(x["last_completed_run_github_confirmed"] for x in prior["lanes"]),
         "F67_CROSSLANE_PROVENANCE_NOT_PRESENT")
    manifest,sha=file_manifest() if pins is None else pins
    need(type(manifest) is list and len(manifest)==2 and
         isinstance(sha,str) and HEX64.fullmatch(sha),
         "FROZEN_ORIGINAL_MANIFEST_NOT_PINNED")
    originals=[verify_original(api,p) for p in manifest]
    ygg=next(x for x in prior["lanes"] if x["program"]=="Yggdrasil")
    runs=[verify_ygg_run(api,i,ygg["main_control_sha"]) for i in sorted(EXPECTED)]
    need(all(x["original_execution_authorized"] is False for x in runs) and
         all(x["scientific_original_execution_authorized"] is False for x in originals),
         "UNEXPECTED_SCIENCE_RELEASE")
    return {
        "schema":SCHEMA,
        "original_manifest_sha256":sha,
        "authenticated_archived_original_metadata":originals,
        "classified_ygg_transport_and_continuation":runs,
        "both_research_lanes_historic_provenance_joined":True,
        "complete_both_lanes_scientific_firstuse_seed_ledger_observed":False,
        "independently_authenticated_ckb_science_owner_epoch":False,
        "deployed_cloudflare_d1_firstuse_claim":False,
        "existing_worker_one_use_permit_issued":False,
        "new_protected_originals_dispatched":0,
        "protected_original_replay_authorized":False,
        "scientific_owner_cutover_authorized":False,
        "disposition":"ARCHIVED_ORIGINALS_PRESERVED_TRANSPORT_SEPARATED_FIRSTUSE_STILL_BLOCKED",
    }

if __name__=="__main__":
    try:
        report=audit(f67.GitHubReadonly(__import__("os").environ.get("GITHUB_TOKEN","")))
        print(json.dumps(report,sort_keys=True,separators=(",",":")))
        print("F68_ACTUAL_ORIGINAL_AND_TRANSPORT_CUSTODY=READONLY_PASS")
    except (Denied,f67.Blocked,ValueError,TypeError,KeyError,IndexError) as exc:
        print("F68_CROSSLANE_FIRSTUSE_CUSTODY=BLOCKED",file=__import__("sys").stderr)
        print("F68_CAUSE="+type(exc).__name__,file=__import__("sys").stderr)
        raise SystemExit(1)
