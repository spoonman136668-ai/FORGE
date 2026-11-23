"""F138-B read-only fail-closed analysis of source-bound development continuity.

Only authenticated provider snapshots and downloaded artifacts are inputs.
This script never dispatches science, changes repository settings or creates runs.
SHA256 receipt verification is integrity, not a digital signature.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re

REPO = "spoonman136668-ai/FORGE"
INTEGRATED = ".github/workflows/forge-integrated-synthetic-cycle.yml"
CONTROLLER = ".github/workflows/forge-development-succession.yml"
INAME = "FORGE integrated two-lane safe research-cycle acceptance"
CNAME = "FORGE source-qualified development completion succession"
WINDOWS = "f137-windows-recovery"
OS = ("ubuntu-latest", "windows-latest")
HEX = re.compile(r"^[a-f0-9]{40}$")
DIGEST = re.compile(r"^sha256:[a-f0-9]{64}$")
MAX_RECORDS = 500
REQUIRED_JOBS = {"two-lane-synthetic (ubuntu-latest)",
                 "two-lane-synthetic (windows-latest)",
                 "f129-durable-cross-run-proof"}

class Quarantine(ValueError):
    pass

def need(value, reason):
    if not value:
        raise Quarantine("F138_" + reason)

def when(value):
    need(type(value) is str, "TIME_MISSING")
    try:
        time = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as ex:
        raise Quarantine("F138_TIME_INVALID") from ex
    need(time.tzinfo is not None, "TIMEZONE_MISSING")
    return time.astimezone(dt.timezone.utc)

def strict(raw):
    need(type(raw) is bytes and 0 < len(raw) < 2_000_000, "JSON_BOUNDS")
    def pairs(items):
        result = {}
        for k, value in items:
            need(k not in result, "DUPLICATE_JSON_KEY")
            result[k] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: need(False, "NONFINITE_JSON"))
    except (ValueError, UnicodeError) as ex:
        if isinstance(ex, Quarantine):
            raise
        raise Quarantine("F138_MALFORMED_JSON") from ex

def index(document, field, limit=MAX_RECORDS):
    need(type(document) is dict and type(document.get("total_count")) is int
         and type(document.get(field)) is list, "INDEX_INVALID")
    rows = document[field]
    need(len(rows) == document["total_count"] and len(rows) <= limit,
         "INDEX_INCOMPLETE")
    ids = [r.get("id") for r in rows if type(r) is dict]
    need(len(ids) == len(rows) and all(type(i) is int and i > 0 for i in ids)
         and len(set(ids)) == len(ids), "INDEX_REPLAY")
    return rows

def run_identity(row, path, name):
    need(type(row) is dict and type(row.get("id")) is int
         and row.get("name") == name and row.get("path") == path
         and row.get("head_branch") == "main"
         and type(row.get("head_sha")) is str
         and HEX.fullmatch(row["head_sha"]) is not None
         and type(row.get("run_attempt")) is int
         and row["run_attempt"] >= 1
         and row.get("repository", {}).get("full_name") == REPO
         and row.get("head_repository", {}).get("full_name") == REPO,
         "PROVIDER_IDENTITY")
    start, launched, end = (when(row.get(k)) for k in
                           ("created_at", "run_started_at", "updated_at"))
    need(start <= launched <= end + dt.timedelta(seconds=5), "RUN_CLOCK")

def archives(snapshot, run, names):
    name = str(run["id"])
    need(type(snapshot.get("artifacts")) is dict
         and name in snapshot["artifacts"], "ARTIFACT_INDEX_MISSING")
    records = index(snapshot["artifacts"][name], "artifacts", 100)
    found = {}
    for row in records:
        need(type(row.get("name")) is str and row["name"] not in found,
             "ARTIFACT_NAME_COLLISION")
        found[row["name"]] = row
    for title in names:
        need(title in found, "REQUIRED_ARTIFACT_MISSING")
        row = found[title]
        need(row.get("expired") is False
             and type(row.get("size_in_bytes")) is int
             and row["size_in_bytes"] > 0
             and type(row.get("digest")) is str
             and DIGEST.fullmatch(row["digest"]) is not None
             and row.get("workflow_run", {}).get("id") == run["id"]
             and row["workflow_run"].get("head_sha") == run["head_sha"],
             "ARTIFACT_CUSTODY")
    return found

def check_jobs(snapshot, run):
    key = str(run["id"])
    need(type(snapshot.get("jobs")) is dict and key in snapshot["jobs"],
         "JOB_INDEX_MISSING")
    rows = index(snapshot["jobs"][key], "jobs", 100)
    seen = set()
    for job in rows:
        label = job.get("name")
        need(type(label) is str and label not in seen, "JOB_NAME_COLLISION")
        seen.add(label)
        if label in REQUIRED_JOBS:
            need(job.get("status") == "completed"
                 and job.get("conclusion") == "success", "REQUIRED_JOB_FAILURE")
    need(REQUIRED_JOBS <= seen, "REQUIRED_JOB_ABSENT")

def check_lineage(folder, run, osname):
    path = folder / str(run["id"]) / osname
    raw = (path / "f138-lineage.json").read_bytes()
    receipt = (path / "f138-lineage.sha256").read_bytes()
    need(receipt == (hashlib.sha256(raw).hexdigest()
                    + "  f138-lineage.json\n").encode("ascii"),
         "LINEAGE_SHA256_INVALID")
    value = strict(raw)
    need(type(value) is dict
         and value.get("schema") == "forge.autonomy.f138.development-lineage.v1"
         and value.get("run_id") == run["id"]
         and value.get("run_attempt") == 1
         and value.get("event") == run["event"]
         and value.get("source_sha") == run["head_sha"]
         and value.get("ref") == "refs/heads/main"
         and value.get("repository") == REPO
         and value.get("development_only") is True
         and value.get("scientific_first_use_authorized") is False
         and value.get("scientific_originals_dispatched") == 0
         and value.get("accepted_ref_mutations") == 0
         and value.get("optimizer_promotions") == 0
         and value.get("codex_calls") == 0
         and value.get("paid_model_calls") == 0,
         "LINEAGE_FALSE_AUTHORITY")
    return value

def check_parent(snapshot, folder, controllers, child, parent_id):
    need(type(parent_id) is int and parent_id in controllers,
         "PARENT_NOT_IN_GITHUB_HISTORY")
    parent = controllers[parent_id]
    run_identity(parent, CONTROLLER, CNAME)
    need(parent["head_sha"] == child["head_sha"]
         and parent["event"] == "workflow_dispatch"
         and parent["status"] == "completed" and parent["conclusion"] == "success"
         and parent["run_attempt"] == 1
         and parent.get("actor", {}).get("login") == "spoonman136668-ai"
         and parent.get("triggering_actor", {}).get("login") == "spoonman136668-ai"
         and when(parent["created_at"]) < when(child["created_at"])
         and when(child["created_at"]) - when(parent["created_at"])
             < dt.timedelta(minutes=5),
         "PARENT_RUN_NOT_QUALIFIED")
    archives(snapshot, parent, ["forge-f137-windows-decision-" + str(parent_id)])
    proof = strict((folder / str(parent_id) / "decision.json").read_bytes())
    need(type(proof) is dict
         and proof.get("schema") == "forge.autonomy.f137.windows-development-wake.v1"
         and proof.get("controller_run_id") == parent_id
         and proof.get("source_sha") == child["head_sha"]
         and proof.get("origin") == WINDOWS
         and proof.get("dispatch") is True
         and proof.get("reasons") == []
         and proof.get("genuine_schedule_claim") is False
         and proof.get("scientific_first_use_authorized") is False
         and proof.get("science_originals") == 0
         and proof.get("accepted_ref_mutations") == 0
         and proof.get("paid_api_calls") == 0 and proof.get("codex_calls") == 0
         and type(proof.get("wake_nonce")) is str
         and re.fullmatch(r"[a-f0-9]{32}", proof["wake_nonce"]),
         "PARENT_DECISION_UNQUALIFIED")
    return proof["wake_nonce"]

def assess(snapshot, folder):
    need(type(snapshot) is dict
         and snapshot.get("schema") == "forge.autonomy.f138.provider-snapshot.v1",
         "SNAPSHOT_INVALID")
    source = snapshot.get("source_sha")
    need(type(source) is str and HEX.fullmatch(source) is not None,
         "SOURCE_SHA_MISSING")
    epoch, now = when(snapshot.get("merged_at")), when(snapshot.get("observed_at"))
    need(epoch < now, "EPOCH_AFTER_OBSERVATION")
    children = index(snapshot.get("integrated_index"), "workflow_runs")
    parent_rows = index(snapshot.get("controller_index"), "workflow_runs")
    need(bool(children) and bool(parent_rows)
         and when(children[-1]["created_at"]) < epoch
         and when(parent_rows[-1]["created_at"]) < epoch,
         "HISTORY_NOT_SPANNING_SOURCE_EPOCH")
    for rows in (children, parent_rows):
        dates = [when(r.get("created_at")) for r in rows]
        need(dates == sorted(dates, reverse=True), "PROVIDER_HISTORY_UNSORTED")
    controllers = {r["id"]: r for r in parent_rows}
    relevant, unattended, witnesses = [], [], []
    for child in children:
        if when(child["created_at"]) < epoch:
            continue
        run_identity(child, INTEGRATED, INAME)
        need(when(child["created_at"]) <= now and child["head_sha"] == source,
             "PROTECTED_SOURCE_DRIFT")
        relevant.append(child)
        if child.get("event") in ("schedule", "workflow_dispatch"):
            unattended.append(child)
    # The latest six candidate runs bound artifact downloads. The provider's
    # full post-epoch history is still checked for source drift and overlap.
    unattended = sorted(unattended, key=lambda x: when(x["created_at"]))[-6:]
    for child in unattended:
        need(child["status"] == "completed"
             and child["conclusion"] == "success"
             and child["run_attempt"] == 1, "RUN_FAILED_OR_REPLAYED")
        archives(snapshot, child, ["forge-f138-lineage-" + osname for osname in OS])
        check_jobs(snapshot, child)
        a, b = [check_lineage(folder, child, osname) for osname in OS]
        need(a == b, "LINUX_WINDOWS_LINEAGE_DRIFT")
        origin, parent = a.get("origin"), a.get("parent_run_id")
        if child["event"] == "schedule":
            need(origin == "schedule" and parent is None
                 and a.get("parent_source_sha") is None
                 and a.get("genuine_integrated_schedule") is True,
                 "FALSE_DIRECT_SCHEDULE")
            nonce = None
        else:
            need(origin == WINDOWS and type(parent) is int
                 and a.get("parent_source_sha") == source
                 and a.get("genuine_integrated_schedule") is False,
                 "UNSUPPORTED_OR_SPOOFED_RELAY")
            nonce = check_parent(snapshot, folder, controllers, child, parent)
        witnesses.append({"run_id":child["id"], "origin":origin,
                          "parent_run_id":parent, "nonce":nonce,
                          "created_at":child["created_at"],
                          "updated_at":child["updated_at"]})
    relevant.sort(key=lambda x: when(x["created_at"]))
    for earlier, later in zip(relevant, relevant[1:]):
        need(when(earlier["updated_at"]) <= when(later["created_at"]),
             "OVERLAPPING_INTEGRATED_RUNS")
    need(len({r["parent_run_id"] for r in witnesses if r["parent_run_id"]})
         == sum(r["parent_run_id"] is not None for r in witnesses),
         "DUPLICATE_PARENT_DISPATCH")
    need(len({r["nonce"] for r in witnesses if r["nonce"]})
         == sum(r["nonce"] is not None for r in witnesses),
         "DUPLICATE_WINDOWS_WAKE")
    windows_trio, mixed_trio = None, None
    for pos in range(max(0,len(witnesses)-2)):
        trio = witnesses[pos:pos+3]
        times = [when(x["created_at"]) for x in trio]
        if (times[-1]-times[0] < dt.timedelta(minutes=20)
                or any(y-x > dt.timedelta(minutes=30)
                       for x,y in zip(times,times[1:]))):
            continue
        origins = [x["origin"] for x in trio]
        if all(x == WINDOWS for x in origins):
            windows_trio = trio
        if WINDOWS in origins and "schedule" in origins:
            mixed_trio = trio
    return {
        "schema":"forge.autonomy.f138.continuity-decision.v1",
        "source_sha":source,"observed_at":snapshot["observed_at"],
        "verdict":"PASS" if mixed_trio else "PENDING",
        "verified_unattended_runs":len(witnesses),
        "windows_recovery_continuity_verified":windows_trio is not None,
        "windows_continuity_run_ids":[x["run_id"] for x in windows_trio] if windows_trio else [],
        "qualifying_three_run_ids":[x["run_id"] for x in mixed_trio] if mixed_trio else [],
        "genuine_scheduled_count":sum(x["origin"]=="schedule" for x in witnesses),
        "windows_recovery_count":sum(x["origin"]==WINDOWS for x in witnesses),
        "no_overlap_and_replay_verified":True,"evidence":witnesses,
        "permanent_custody_verified":False,
        "scientific_first_use_authorized":False,"accepted_ref_mutations":0
    }

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",type=Path,required=True)
    p.add_argument("--evidence-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        result=assess(strict(a.snapshot.read_bytes()),a.evidence_dir)
        with a.output.open("xb") as out:
            out.write((json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode())
        print("F138_ROLLING_CONTINUITY="+result["verdict"])
    except (Quarantine,OSError,TypeError,KeyError) as ex:
        raise SystemExit("F138_QUARANTINED "+str(ex)) from ex
