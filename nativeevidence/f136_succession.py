"""F136: fail-closed source/receipt-gated completion-driven development succession.

No GPT/Codex invocation, science dispatch, original result acceptance or main write.
This controller only authorizes a *single* development workflow_dispatch from
an independently completed GitHub integrated cycle on protected main.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f136-development-succession-freeze.json"
FROZEN_BLOB="d340488a3e9263ee75d8088426004712d314afa4"
HEX=re.compile(r"^[a-f0-9]{40}$")
DIGEST=re.compile(r"^sha256:[a-f0-9]{64}$")
REPO="spoonman136668-ai/FORGE"
WORKFLOW=".github/workflows/forge-integrated-synthetic-cycle.yml"
ARTIFACTS={
    "f124":("forge-f124-autonomy-", "state.json", "state.sha256"),
    "f126":("forge-f126-original-negative-agenda-",
            "f126-original-negative-selected-agenda.json",
            "f126-original-negative-selected-agenda.sha256"),
    "f129":("forge-f129-admission-", "f129-admission.json", "f129-admission.sha256"),
}
class Invalid(ValueError):pass

def need(ok:bool,reason:str):
    if not ok:raise Invalid("F136_"+reason)

def stamp(iso:str)->dt.datetime:
    need(type(iso) is str,"TIME_MISSING")
    try:
        t=dt.datetime.fromisoformat(iso.replace("Z","+00:00"))
    except ValueError as exc:
        raise Invalid("F136_TIME_INVALID") from exc
    need(t.tzinfo is not None,"TIME_NAIVE")
    return t.astimezone(dt.timezone.utc)

def strict(data:bytes)->Any:
    need(type(data) is bytes and 0<len(data)<2_000_000,"BOUNDED_JSON")
    def pairs(rows):
        result={}
        for k,v in rows:
            need(k not in result,"DUPLICATE_KEY")
            result[k]=v
        return result
    try:
        return json.loads(data,object_pairs_hook=pairs,
                          parse_constant=lambda _:need(False,"NONFINITE_JSON"))
    except (ValueError,UnicodeError) as exc:
        if isinstance(exc,Invalid):raise
        raise Invalid("F136_JSON_INVALID") from exc

def frozen():
    data=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    blob=b"blob "+str(len(data)).encode()+b"\0"+data
    need(hashlib.sha1(blob).hexdigest()==FROZEN_BLOB,
         "FROZEN_PROTOCOL_DRIFT")
    p=strict(data)
    need(p["schema"]=="forge.autonomy.f136.frozen-completion-driven-development.v1"
         and p["base_sha"]=="69eed33007007815923ffc0fc05ff9cc31a3b794"
         and p["target_minutes"]==7 and p["fallback_minutes"]==10
         and p["max_daily_initiated_development_cycles"]==96
         and all(p["restrictions"].values())
         and all(p["scientific"].values()),"FROZEN_SOURCE_OR_AUTHORITY_INVALID")
    return p,hashlib.sha256(data).hexdigest()

def identify(trigger,main_sha,now):
    need(type(trigger) is dict and type(main_sha) is str
         and HEX.fullmatch(main_sha)
         and type(now) is dt.datetime and now.tzinfo,
         "CONTROLLER_SOURCE_IDENTITY_INVALID")
    need(trigger.get("repository",{}).get("full_name")==REPO
         and trigger.get("head_repository",{}).get("full_name")==REPO
         and trigger.get("path")==WORKFLOW
         and trigger.get("head_branch")=="main"
         and trigger.get("head_sha")==main_sha,
         "TRIGGER_WRONG_PROTECTED_SOURCE")
    need(trigger.get("status")=="completed"
         and trigger.get("conclusion")=="success"
         and trigger.get("run_attempt")==1
         and trigger.get("event") in ("schedule","workflow_dispatch")
         and type(trigger.get("id")) is int and trigger["id"]>0
         and type(trigger.get("created_at")) is str
         and type(trigger.get("run_started_at")) is str
         and type(trigger.get("updated_at")) is str,
         "TRIGGER_NOT_COMPLETED_GENUINE_DEVELOPMENT")
    begin=stamp(trigger["created_at"])
    started=stamp(trigger["run_started_at"])
    end=stamp(trigger["updated_at"])
    need(begin<=started<=end<=now+dt.timedelta(minutes=2)
         and now-end<=dt.timedelta(minutes=20),
         "TRIGGER_STALE_OR_TIME_TRAVEL")
    return int((end-begin).total_seconds())

def evidence_index(trigger,index):
    need(type(index) is dict and type(index.get("total_count")) is int
         and type(index.get("artifacts")) is list
         and index["total_count"]==len(index["artifacts"])
         and len(index["artifacts"])<=100,
         "PRIOR_INDEX_TRUNCATED")
    records=index["artifacts"]
    ids=[r.get("id") for r in records if type(r) is dict]
    need(len(ids)==len(records) and len(set(ids))==len(ids),
         "ARTIFACT_ID_COLLISION")
    for section,(prefix,_,_) in ARTIFACTS.items():
        for os in ("ubuntu-latest","windows-latest"):
            name=prefix+os
            matches=[r for r in records if r.get("name")==name]
            need(len(matches)==1,"MISSING_TWO_OS_EVIDENCE_"+section)
            row=matches[0]
            need(row.get("expired") is False
                 and type(row.get("size_in_bytes")) is int
                 and row["size_in_bytes"]>0
                 and type(row.get("digest")) is str
                 and DIGEST.fullmatch(row["digest"])
                 and type(row.get("workflow_run")) is dict
                 and row["workflow_run"].get("id")==trigger["id"]
                 and row["workflow_run"].get("head_sha")==trigger["head_sha"],
                 "ARTIFACT_CUSTODY_UNQUALIFIED_"+section)

def decision(trigger,index,recent,main_sha,now,paused=False):
    p,freeze_sha=frozen()
    seconds=identify(trigger,main_sha,now)
    evidence_index(trigger,index)
    need(type(recent) is dict and type(recent.get("total_count")) is int
         and type(recent.get("workflow_runs")) is list,
         "RECENT_RUN_API_INVALID")
    rows=recent["workflow_runs"]
    need(1<=len(rows)<=300 and
         len({r.get("id") for r in rows if type(r) is dict})==len(rows),
         "RECENT_RUN_INDEX_UNTRUSTED")
    need(any(r.get("id")==trigger["id"] for r in rows),
         "TRIGGER_ABSENT_FROM_RECENT_RUNS")
    # We supply up to the 300 newest workflow runs from the hosted API;
    # require the oldest observed record to precede the present UTC day.
    today=now.date()
    need(stamp(rows[-1]["created_at"]).date()<today,
         "DAILY_BUDGET_INDEX_INCOMPLETE")
    in_day=[]
    for run in rows:
        need(type(run) is dict and type(run.get("id")) is int
             and type(run.get("created_at")) is str
             and type(run.get("event")) is str
             and type(run.get("status")) is str
             and type(run.get("head_branch")) is str
             and type(run.get("head_sha")) is str,
             "RECENT_RUN_ROW_UNVERIFIED")
        if stamp(run["created_at"]).date()==today and run["head_branch"]=="main":
            in_day.append(run)
    today_count=sum(1 for r in in_day if r["event"] in ("schedule","workflow_dispatch"))
    reasons=[]
    if paused:reasons.append("OPERATOR_PAUSED")
    if today_count>=p["max_daily_initiated_development_cycles"]:
        reasons.append("DAILY_START_CAP")
    if any(r["id"]!=trigger["id"] and r["head_branch"]=="main"
           and r["status"] in ("in_progress","queued","pending","waiting","requested")
           for r in rows):
        reasons.append("ACTIVE_OR_PENDING_INTEGRATED_RUN")
    if any(r["id"]>trigger["id"] and r["head_branch"]=="main" and
           r["event"] in ("schedule","workflow_dispatch") and
           r["status"]=="completed" and r.get("conclusion")=="success"
           for r in rows):
        reasons.append("NOT_LATEST_QUALIFIED_COMPLETION")
    # Offset schedule at :07,:17,...; do not race a near due fallback.
    seconds_into_hour=now.minute*60+now.second
    seconds_until_fallback=(7*60-seconds_into_hour)%(10*60)
    if seconds_until_fallback<=120:
        reasons.append("FALLBACK_SLOT_IMMINENT")
    return {"schema":"forge.autonomy.f136.development-succession-decision.v1",
        "trigger_run_id":trigger["id"],"source_sha":main_sha,
        "event":trigger["event"],"run_seconds":seconds,
        "observed_end_to_end_target_met":seconds<=7*60,
        "target_seconds":7*60,
        "utc_day":str(today),"daily_main_development_starts":today_count,
        "daily_cap":p["max_daily_initiated_development_cycles"],
        "prior_evidence_two_os_index_verified":True,
        "dispatch":not reasons,"reasons":reasons,
        "frozen_protocol_sha256":freeze_sha,
        "scientific_originals_dispatched":0,
        "first_use_authorized":False,"accepted_ref_mutations":0,
        "optimizer_promotions":0,"paid_API_calls":0,"Codex_calls":0,
        "scheduled_main_continuity_proven_by_dispatch":False}

def validate_contents(report_dir,expected_source,run_id):
    folder=Path(report_dir)
    results={}
    for section,(prefix,filename,receipt) in ARTIFACTS.items():
        seen=[]
        for os in ("ubuntu-latest","windows-latest"):
            location=folder/(prefix+os)
            raw=(location/filename).read_bytes()
            proof=(location/receipt).read_bytes().strip()
            digest=hashlib.sha256(raw).hexdigest()
            need(proof==(digest+"  "+filename).encode(),
                 "REPORT_SHA_MISMATCH_"+section)
            state=strict(raw)
            need(type(state) is dict
                 and state.get("source_sha")==expected_source
                 and state.get("run_id")==run_id
                 and state.get("scientific_first_use_authorized") is not True
                 and state.get("accepted_ref_mutations")==0
                 and state.get("optimizer_promotions")==0,
                 "ORIGINAL_SCIENCE_AUTHORITY_"+section)
            if section=="f124":
                need(state.get("scientific_originals")==0,
                     "F124_ORIGINAL_SCIENCE")
            if section=="f126":
                need(state.get("new_accepted_scientific_originals")==0
                     and state.get("real_scientific_first_use") is False,
                     "F126_SCIENCE_ORIGINALS")
            if section=="f129":
                need(state.get("scientific_originals_dispatched")==0
                     and state.get("two_genuine_scheduled_main_runs_proven") is False,
                     "F129_FALSE_CONTINUITY")
            seen.append(raw)
        need(seen[0]==seen[1],"PLATFORM_REPORT_DRIFT_"+section)
        results[section]=hashlib.sha256(seen[0]).hexdigest()
    return results

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--trigger",required=True)
    p.add_argument("--artifacts-index",required=True)
    p.add_argument("--recent",required=True)
    p.add_argument("--main-sha",required=True)
    p.add_argument("--now",required=True)
    p.add_argument("--paused",default="false")
    p.add_argument("--report-dir",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    need(a.paused in ("true","false"),"PAUSE_STATE_INVALID")
    trigger=strict(Path(a.trigger).read_bytes())
    metadata=strict(Path(a.artifacts_index).read_bytes())
    recent=strict(Path(a.recent).read_bytes())
    outcome=decision(trigger,metadata,recent,a.main_sha,stamp(a.now),
                     paused=a.paused=="true")
    if outcome["dispatch"]:
        outcome["verified_extracted_sha256"]=validate_contents(
            a.report_dir,a.main_sha,trigger["id"])
    else:
        outcome["verified_extracted_sha256"]={}
    target=Path(a.output)
    need(target.parent.is_dir() and not target.exists(),"NON_APPEND_ONLY_OUTPUT")
    target.write_bytes((json.dumps(outcome,sort_keys=True,
                         separators=(",",":"))+"\n").encode())
    print("F136_"+("DISPATCH_ELIGIBLE" if outcome["dispatch"]
                  else "NO_DISPATCH")+" "+",".join(outcome["reasons"]))



# F137: independent schedule-fed development recovery via the EXISTING
# read-only metadata observer. This never establishes integrated scheduled
# science ancestry and never grants any scientific first use.
OBSERVER_WORKFLOW=".github/workflows/forge-live-research-observer.yml"
OBSERVER_NAME="FORGE live two-lane research metadata observer"
OBSERVER_ARCHIVES=("forge-observed-research-metadata",
                   "forge-observed-crosslane-pr-sources")

def observer_bootstrap_decision(observer,index,recent,main_sha,now,paused=False):
    protocol,freeze_sha=frozen()
    need(type(observer) is dict and type(main_sha) is str
         and HEX.fullmatch(main_sha) and type(now) is dt.datetime
         and now.tzinfo is not None,"F137_INPUT_INVALID")
    need(observer.get("repository",{}).get("full_name")==REPO
         and observer.get("head_repository",{}).get("full_name")==REPO
         and observer.get("path")==OBSERVER_WORKFLOW
         and observer.get("name")==OBSERVER_NAME
         and observer.get("head_branch")=="main"
         and observer.get("head_sha")==main_sha,
         "F137_OBSERVER_PROTECTED_SOURCE_INVALID")
    need(observer.get("event")=="schedule"
         and observer.get("status")=="completed"
         and observer.get("conclusion")=="success"
         and observer.get("run_attempt")==1
         and type(observer.get("id")) is int and observer["id"]>0
         and all(type(observer.get(k)) is str for k in
                 ("created_at","run_started_at","updated_at")),
         "F137_NOT_AUTHENTIC_SUCCESSFUL_SCHEDULE")
    begin=stamp(observer["created_at"])
    started=stamp(observer["run_started_at"])
    ended=stamp(observer["updated_at"])
    need(begin<=started<=ended<=now+dt.timedelta(minutes=2)
         and dt.timedelta(0)<=now-ended<=dt.timedelta(minutes=30),
         "F137_SCHEDULE_OBSERVER_STALE")

    need(type(index) is dict and type(index.get("total_count")) is int
         and type(index.get("artifacts")) is list
         and index["total_count"]==len(index["artifacts"])
         and 2<=len(index["artifacts"])<=100,
         "F137_OBSERVER_ARCHIVES_INDEX_INVALID")
    artifacts=index["artifacts"]
    ids=[a.get("id") for a in artifacts if type(a) is dict]
    need(len(ids)==len(artifacts) and
         all(type(i) is int and i>0 for i in ids) and
         len(ids)==len(set(ids)), "F137_OBSERVER_ARTIFACT_IDS_INVALID")
    for name in OBSERVER_ARCHIVES:
        matches=[a for a in artifacts if a.get("name")==name]
        need(len(matches)==1,"F137_OBSERVER_ARCHIVE_MISSING_"+name)
        a=matches[0]
        need(a.get("expired") is False
             and type(a.get("size_in_bytes")) is int
             and a["size_in_bytes"]>0
             and type(a.get("digest")) is str
             and DIGEST.fullmatch(a["digest"])
             and type(a.get("workflow_run")) is dict
             and a["workflow_run"].get("id")==observer["id"]
             and a["workflow_run"].get("head_sha")==main_sha,
             "F137_OBSERVER_RECEIPT_IDENTITY_INVALID")

    need(type(recent) is dict and type(recent.get("total_count")) is int
         and type(recent.get("workflow_runs")) is list,
         "F137_INTEGRATED_HISTORY_INVALID")
    rows=recent["workflow_runs"]
    need(1<=len(rows)<=300 and recent["total_count"]>=len(rows)
         and len({r.get("id") for r in rows if type(r) is dict})==len(rows),
         "F137_INTEGRATED_HISTORY_INCOMPLETE")
    today=now.date()
    # Use the same full UTC-day coverage and budget as the frozen F136 gate.
    need(stamp(rows[-1]["created_at"]).date()<today,
         "F137_INTEGRATED_DAILY_BUDGET_INCOMPLETE")
    day_runs=[]
    for run in rows:
        need(type(run) is dict
             and type(run.get("id")) is int
             and type(run.get("created_at")) is str
             and type(run.get("event")) is str
             and type(run.get("status")) is str
             and type(run.get("head_branch")) is str
             and type(run.get("head_sha")) is str,
             "F137_INTEGRATED_HISTORY_ROW_INVALID")
        created=stamp(run["created_at"])
        need(created<=now+dt.timedelta(minutes=2),
             "F137_INTEGRATED_HISTORY_TIME_TRAVEL")
        if created.date()==today and run["head_branch"]=="main":
            day_runs.append(run)
    initiated=sum(r["event"] in ("schedule","workflow_dispatch")
                  for r in day_runs)
    reasons=[]
    if paused: reasons.append("OPERATOR_PAUSED")
    if initiated>=protocol["max_daily_initiated_development_cycles"]:
        reasons.append("DAILY_START_CAP")
    if any(r["head_branch"]=="main" and
           r["status"] in ("queued","waiting","in_progress","pending","requested")
           for r in rows):
        reasons.append("ACTIVE_OR_PENDING_INTEGRATED_RUN")
    if any(r["head_branch"]=="main" and
           dt.timedelta(0)<=now-stamp(r["created_at"])<dt.timedelta(minutes=10)
           for r in rows):
        reasons.append("INTEGRATED_CYCLE_RECENTLY_STARTED")
    if any(r["head_branch"]=="main" and r["event"]=="schedule"
           and dt.timedelta(0)<=now-stamp(r["created_at"])<dt.timedelta(hours=1)
           for r in rows):
        reasons.append("GENUINE_INTEGRATED_SCHEDULE_ALREADY_PRESENT")
    return {"schema":"forge.autonomy.f137.schedule-fed-development-recovery.v1",
            "observer_run_id":observer["id"],
            "observer_event":"schedule",
            "observer_workflow":OBSERVER_WORKFLOW,
            "source_sha":main_sha,
            "utc_day":str(today),
            "daily_main_development_starts":initiated,
            "daily_cap":protocol["max_daily_initiated_development_cycles"],
            "observer_two_artifact_provenance_verified":True,
            "dispatch":not reasons,
            "reasons":reasons,
            "frozen_f136_protocol_sha256":freeze_sha,
            "development_only":True,
            "genuine_integrated_schedule_claimed":False,
            "first_use_authorized":False,
            "scientific_originals_dispatched":0,
            "accepted_ref_mutations":0,
            "optimizer_promotions":0,
            "paid_API_calls":0,
            "Codex_calls":0,
            "ckb_plane_accessed":False,
            "mind_palace_written":False}

if __name__=="__main__":
    try:main()
    except (Invalid,ValueError,TypeError,KeyError,OSError) as ex:
        print("F136_SOURCE_QUARANTINE "+str(ex),file=sys.stderr)
        sys.exit(1)
