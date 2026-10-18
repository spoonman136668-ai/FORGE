"""F138-B GitHub-native read-only evidence acquisition for an existing completion event.

Only GET actions/branches/commits/archives are permitted. Every outcome is
PENDING, PASS or QUARANTINED; no workflow is dispatched and science stays denied.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"nativeevidence"))
import f138_continuity as f

API="repos/"+f.REPO
INTEGRATED="forge-integrated-synthetic-cycle.yml"
CONTROLLER="forge-development-succession.yml"

def call(route,binary=False):
    f.need(type(route) is str and route.startswith(API+"/")
           and ".." not in route and " " not in route and "\n" not in route,
           "API_ROUTE_INVALID")
    try:
        result=subprocess.run(["gh","api",route],stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,timeout=35,check=False)
    except (OSError,subprocess.TimeoutExpired) as ex:
        raise f.Quarantine("F138_GITHUB_READ_TIMEOUT") from ex
    f.need(result.returncode==0 and 0<len(result.stdout)
           <(20_000_000 if binary else 10_000_000),
           "GITHUB_GET_FAILED")
    return result.stdout

def get(route):
    try:
        value=json.loads(call(route))
    except ValueError as ex:
        raise f.Quarantine("F138_GITHUB_RESPONSE_INVALID") from ex
    f.need(type(value) is dict,"GITHUB_RESPONSE_NOT_OBJECT")
    return value

def slim_run(row):
    fields=("id","name","path","head_branch","head_sha","run_attempt",
            "event","status","conclusion","created_at","updated_at","run_started_at")
    return {**{key:row.get(key) for key in fields},
            "repository":{"full_name":row.get("repository",{}).get("full_name")},
            "head_repository":{"full_name":row.get("head_repository",{}).get("full_name")},
            "actor":{"login":row.get("actor",{}).get("login")},
            "triggering_actor":{"login":row.get("triggering_actor",{}).get("login")}}

def runs(workflow):
    rows=[]
    total=None
    for page in range(1,7):
        entry=get(API+"/actions/workflows/"+workflow+
                  "/runs?branch=main&per_page=100&page="+str(page))
        items=entry.get("workflow_runs")
        f.need(type(items) is list and type(entry.get("total_count")) is int,
               "GITHUB_RUNS_INVALID")
        if total is None:
            total=entry["total_count"]
        f.need(entry["total_count"]==total,"GITHUB_RUN_HISTORY_CHANGED")
        rows.extend(slim_run(x) for x in items)
        f.need(len(rows)<=f.MAX_RECORDS,"GITHUB_RUN_HISTORY_TOO_LARGE")
        if len(rows)==total:
            return {"total_count":total,"workflow_runs":rows}
        f.need(len(items)==100 and len(rows)<total,"GITHUB_RUNS_TRUNCATED")
    raise f.Quarantine("F138_GITHUB_PAGINATION_EXHAUSTED")

def item_index(run_id,kind):
    f.need(type(run_id) is int and run_id>0 and kind in ("jobs","artifacts"),
           "PROVIDER_INDEX_ROUTE_INVALID")
    response=get(API+"/actions/runs/"+str(run_id)+"/"+kind+"?per_page=100")
    items=response.get(kind)
    f.need(type(items) is list and type(response.get("total_count")) is int
           and len(items)==response["total_count"] and len(items)<=100,
           "PROVIDER_INDEX_INCOMPLETE")
    if kind=="jobs":
        rows=[{k:item.get(k) for k in ("id","name","status","conclusion")}
              for item in items]
    else:
        rows=[{**{k:item.get(k) for k in
                 ("id","name","expired","size_in_bytes","digest")},
               "workflow_run":{"id":item.get("workflow_run",{}).get("id"),
                               "head_sha":item.get("workflow_run",{}).get("head_sha")}}
              for item in items]
    return {"total_count":len(rows),kind:rows}

def download(item,expected,folder):
    f.need(item.get("expired") is False
           and type(item.get("id")) is int
           and type(item.get("digest")) is str
           and f.DIGEST.fullmatch(item["digest"]) is not None,
           "ARTIFACT_ENVELOPE_INVALID")
    zip_bytes=call(API+"/actions/artifacts/"+str(item["id"])+"/zip",True)
    f.need(hashlib.sha256(zip_bytes).hexdigest()==item["digest"][7:]
           and len(zip_bytes)==item.get("size_in_bytes"),
           "GITHUB_ARTIFACT_ZIP_DIGEST_INVALID")
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            members=archive.infolist()
            names=[x.filename for x in members]
            f.need(sorted(names)==sorted(expected)
                   and len(names)==len(set(names))
                   and all(x.file_size<=2_000_000
                           and x.compress_size<=5_000_000 for x in members),
                   "ZIP_MEMBER_SET_UNQUALIFIED")
            folder.mkdir(parents=True,exist_ok=False)
            for name in expected:
                with (folder/name).open("xb") as out:
                    out.write(archive.read(name))
    except (OSError,ValueError,zipfile.BadZipFile) as ex:
        if isinstance(ex,f.Quarantine):
            raise
        raise f.Quarantine("F138_PROVIDER_ZIP_UNREADABLE") from ex

def capture(folder,main_sha):
    f.need(folder.is_dir() and type(main_sha) is str
           and f.HEX.fullmatch(main_sha) is not None,
           "COLLECTOR_INPUT_INVALID")
    f.need(get(API+"/branches/main").get("commit",{}).get("sha")==main_sha,
           "MAIN_NOT_AT_EXPECTED_SOURCE")
    source=get(API+"/commits/"+main_sha)
    epoch=source.get("commit",{}).get("committer",{}).get("date")
    f.when(epoch)
    snapshot={"schema":"forge.autonomy.f138.provider-snapshot.v1",
              "source_sha":main_sha,"merged_at":epoch,
              "observed_at":dt.datetime.now(dt.timezone.utc).isoformat(),
              "integrated_index":runs(INTEGRATED),
              "controller_index":runs(CONTROLLER),
              "artifacts":{},"jobs":{}}
    choices=[x for x in snapshot["integrated_index"]["workflow_runs"]
             if f.when(x["created_at"])>=f.when(epoch)
             and x["event"] in ("schedule","workflow_dispatch")]
    choices=sorted(choices,key=lambda x:x["created_at"])[-6:]
    controllers={x["id"]:x for x in snapshot["controller_index"]["workflow_runs"]}
    for child in choices:
        rid=child["id"]
        idx=item_index(rid,"artifacts")
        snapshot["artifacts"][str(rid)]=idx
        snapshot["jobs"][str(rid)]=item_index(rid,"jobs")
        for os_name in f.OS:
            name="forge-f138-lineage-"+os_name
            matches=[x for x in idx["artifacts"] if x["name"]==name]
            f.need(len(matches)==1,"LINEAGE_ARTIFACT_MISSING")
            download(matches[0],("f138-lineage.json","f138-lineage.sha256"),
                     folder/str(rid)/os_name)
        witness=json.loads((folder/str(rid)/f.OS[0]/"f138-lineage.json").read_text())
        if witness.get("origin")==f.WINDOWS:
            pid=witness.get("parent_run_id")
            f.need(type(pid) is int and pid in controllers,
                   "WINDOWS_PARENT_NOT_IN_GITHUB_HISTORY")
            snap=item_index(pid,"artifacts")
            snapshot["artifacts"][str(pid)]=snap
            name="forge-f137-windows-decision-"+str(pid)
            matches=[x for x in snap["artifacts"] if x["name"]==name]
            f.need(len(matches)==1,"WINDOWS_DECISION_ARTIFACT_MISSING")
            download(matches[0],("decision.json",),folder/str(pid))
    f.need(get(API+"/branches/main").get("commit",{}).get("sha")==main_sha,
           "MAIN_CHANGED_DURING_READBACK")
    return snapshot

def write_once(path,value):
    payload=(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
    with path.open("xb") as out:
        out.write(payload)
    with (path.parent/(path.name+".sha256")).open("xb") as out:
        out.write((hashlib.sha256(payload).hexdigest()+"  "+path.name+"\n").encode())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,required=True)
    ap.add_argument("--expected-main",required=True)
    args=ap.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=False)
    try:
        f.need(bool(os.environ.get("GH_TOKEN")),"READ_TOKEN_NOT_AVAILABLE")
        snapshot=capture(args.output_dir,args.expected_main)
        write_once(args.output_dir/"snapshot.json",snapshot)
        report=f.assess(snapshot,args.output_dir)
    except (f.Quarantine,OSError,ValueError,KeyError,TypeError) as ex:
        report={"schema":"forge.autonomy.f138.continuity-decision.v1",
                "verdict":"QUARANTINED","reason":str(ex),
                "permanent_custody_verified":False,
                "scientific_first_use_authorized":False,
                "accepted_ref_mutations":0}
    write_once(args.output_dir/"decision.json",report)
    print("F138_READONLY_VERDICT="+report["verdict"])
    print("F138_SCIENTIFIC_ORIGINALS=ZERO")
    print("F138_NEW_DEVELOPMENT_DISPATCHES=ZERO")
    print("F138_DURABLE_CUSTODY=NOT_YET_QUALIFIED")

if __name__=="__main__":
    main()
