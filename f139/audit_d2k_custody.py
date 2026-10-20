"""F139-D2K-CUSTODY: nonintrusive, content-addressed read-only custody preflight.

This deliberately does not start/stop any controller or transition accepted refs.
An externally sealed 23-event head is mandatory; the local DB is not its own witness.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from f139.local_controller import (
    ZERO, MAX_ZIP_BYTES, canonical, hash_bytes, receipt_from_zip, d2j_plan,
)

SHA40=re.compile(r"[a-f0-9]{40}\Z")
SHA64=re.compile(r"[a-f0-9]{64}\Z")
MAX_SOURCE_BYTES=16_000_000
OS_LABELS=("ubuntu-latest","windows-latest")


class CustodyBlocked(RuntimeError):
    pass


def check(condition, reason):
    if not condition:
        raise CustodyBlocked("F139_D2K_CUSTODY_"+reason)

# Exact authenticated GitHub provider metadata, fixed by the reviewed source commit.
# The provider manifest is not an independently signed Windows SQLite head.
D2C_SOURCE = "f569b827aeeddcbb2865bec49c062d2a7e523886"
D2J_SOURCE = "4a5665d9d01b6e68effc00be244ac39b6794a222"
# Authenticated protected-main merge sequence. Allowed suffixes are strictly
# append-only transitions, not admission of work or independent science.
ALLOWED_SOURCE_SUCCESSORS = (
    "99be12f448c27aea7f74a5224c9ebccf6e9d7c21",
    "c0eaa5eef08d38417fe2875bbdd352362e130b5f",
    "5ca118a0425dd4c6b3fa67a2f575cfda491cb8ba",
    "e8166b1ef2f52ad935029ee583a5a0827b8a25d8",
    "41263bb8aec510b293fc93b81b58df689f089aae",
    "6842e97126ebb31790681e86c54dc01d0aae652f",
    "296f2784621b92006f3e217012fafa54b8aed1f6",
    "365e5eb8b888c11716376973ad2551523a869bab",
)
# Immutable, source-authenticated D2C repair path followed by two original D2J
# provider terminals. D2C repairs are NOT PROVIDER_VERIFIED_TERMINAL events.
# Preserve the earlier quarantine decisions; neither a repair nor an audit is
# a scientific original first-use grant.
REAL_23_EVENT_KINDS = (
    "TASK_INTAKE", "TASK_INTAKE", "CUTOVER_ACTIVATED",
    "BEFORE_DISPATCH_INTENT", "DISPATCH_POST_RETURNED", "ATTEMPT_QUARANTINED",
    "BEFORE_DISPATCH_INTENT", "DISPATCH_POST_RETURNED", "ATTEMPT_QUARANTINED",
    "QUARANTINE_ORIGINAL_RECONCILED", "QUARANTINE_ORIGINAL_RECONCILED",
    "SOURCE_TRANSITION_ADMITTED", "SOURCE_TRANSITION_ADMITTED",
    "SOURCE_TRANSITION_ADMITTED", "UNATTENDED_SUCCESSION_ADMITTED",
    "TASK_INTAKE", "TASK_INTAKE",
    "BEFORE_DISPATCH_INTENT", "DISPATCH_POST_RETURNED", "PROVIDER_VERIFIED_TERMINAL",
    "BEFORE_DISPATCH_INTENT", "DISPATCH_POST_RETURNED", "PROVIDER_VERIFIED_TERMINAL",
)

EXPECTED_RUNS = {
    "f139-d2c-qualification-659bb1f4d751": (39178196331, D2C_SOURCE),
    "f139-d2c-wingless-659bb1f4d751": (39178299792, D2C_SOURCE),
    "f139-d2j-wingless-4a5665d9d01b": (39221544338, D2J_SOURCE),
    "f139-d2j-yggdrasil-4a5665d9d01b": (39221731257, D2J_SOURCE),
}


def load_provider_anchor():
    """Load source-pinned GitHub metadata; never substitute a local DB export."""
    anchor_path = Path(__file__).with_name("d2k_provider_anchor.json")
    check(anchor_path.is_file() and not anchor_path.is_symlink()
          and anchor_path.stat().st_size <= 8192, "EXTERNAL_ANCHOR_MISSING")
    try:
        value=json.loads(anchor_path.read_bytes())
    except (ValueError,OSError) as exc:
        raise CustodyBlocked("F139_D2K_CUSTODY_EXTERNAL_ANCHOR_INVALID") from exc
    check(isinstance(value,dict)
          and set(value)=={"schema","repository","workflow_id","provenance","records"}
          and value["schema"]=="forge.f139.d2k-custody.provider-anchor.v1"
          and value["repository"]=="spoonman136668-ai/FORGE"
          and value["workflow_id"]==388797257
          and isinstance(value["provenance"],str)
          and isinstance(value["records"],list)
          and len(value["records"])==4, "EXTERNAL_ANCHOR_SCHEMA")
    by_ticket={}
    for record in value["records"]:
        check(isinstance(record,dict) and set(record)=={
            "ticket","run_id","source_sha","artifacts"},"EXTERNAL_ANCHOR_RECORD_FIELDS")
        ticket=record["ticket"]
        check(isinstance(ticket,str) and ticket in EXPECTED_RUNS
              and record["run_id"]==EXPECTED_RUNS[ticket][0]
              and record["source_sha"]==EXPECTED_RUNS[ticket][1]
              and ticket not in by_ticket
              and isinstance(record["artifacts"],dict)
              and set(record["artifacts"])==set(OS_LABELS),
              "EXTERNAL_ANCHOR_RUN_SOURCE")
        for label in OS_LABELS:
            artifact=record["artifacts"][label]
            check(isinstance(artifact,dict)
                  and set(artifact)=={"artifact_id","sha256","size_in_bytes"}
                  and type(artifact["artifact_id"]) is int and artifact["artifact_id"]>0
                  and isinstance(artifact["sha256"],str)
                  and SHA64.fullmatch(artifact["sha256"])
                  and type(artifact["size_in_bytes"]) is int
                  and 0<artifact["size_in_bytes"]<MAX_ZIP_BYTES,
                  "EXTERNAL_ANCHOR_ARTIFACT_FIELDS")
        by_ticket[ticket]=record
    check(set(by_ticket)==set(EXPECTED_RUNS),"EXTERNAL_ANCHOR_INCOMPLETE")
    return by_ticket


def copied_snapshot(source: Path, scratch: Path):
    """Copy DB/WAL/SHM bytes; fail if any source file changes during the copy."""
    source=Path(source)
    check(source.is_file() and not source.is_symlink(), "DATABASE_NOT_REGULAR")
    candidates=(source,Path(str(source)+"-wal"),Path(str(source)+"-shm"))
    def read():
        output={}
        for p in candidates:
            check(not p.is_symlink(), "DATABASE_SIDECAR_SYMLINK")
            if p.exists():
                check(p.is_file() and p.stat().st_size<=MAX_SOURCE_BYTES,
                      "DATABASE_FILE_OVERSIZE")
                output[p.name]=p.read_bytes()
        return output
    original=read()
    check(source.name in original, "DATABASE_MISSING")
    for filename,data in original.items():
        (scratch/filename).write_bytes(data)
    check(original==read(),"DATABASE_CHANGED_DURING_COPY")
    return scratch/source.name


def verify_chain(events, expected_head: str, *, qualified_main_sha: str | None = None):
    """Require the sealed 23-event prefix and strictly source-only successors.

    The optional final target is NOT an authorization: callers must obtain
    qualified_main_sha from an independently authenticated protected-main
    provider read. The native CLI enforces that check before accepting it.

    The caller must supply the *original*, independently sealed head. Checking
    a later local head against itself would permit fabricated post-merge custody.
    """
    check(isinstance(expected_head,str) and SHA64.fullmatch(expected_head),
          "UNSEALED_EXPECTED_EVENT_HEAD")
    check(qualified_main_sha is None or
          (isinstance(qualified_main_sha,str) and SHA40.fullmatch(qualified_main_sha)
           and qualified_main_sha not in ALLOWED_SOURCE_SUCCESSORS
           and qualified_main_sha != D2J_SOURCE), "QUALIFIED_MAIN_SHA_INVALID")
    check(23 <= len(events) <= 23+len(ALLOWED_SOURCE_SUCCESSORS)
          +(1 if qualified_main_sha is not None else 0),
          "EVENT_COUNT_UNSUPPORTED")
    prior=ZERO
    kinds=[]
    terminals=[]
    current_source=D2J_SOURCE
    approved_index=-1
    for number,row in enumerate(events,1):
        check(row["seq"]==number and row["prior_sha"]==prior,
              "EVENT_SEQUENCE_OR_PREDECESSOR")
        try:
            payload=json.loads(row["payload"])
        except (ValueError,TypeError) as exc:
            raise CustodyBlocked("F139_D2K_CUSTODY_INVALID_EVENT_JSON") from exc
        check(canonical(payload).decode()==row["payload"],"EVENT_NOT_CANONICAL")
        record={"seq":number,"prior_sha":prior,
                "kind":row["kind"],"payload":payload}
        digest=hash_bytes(canonical(record))
        check(digest==row["sha"],"EVENT_HASH_MISMATCH")
        if number<=23:
            kinds.append(row["kind"])
            check(row["kind"] == REAL_23_EVENT_KINDS[number-1],
                  "D2J_HISTORY_SHAPE_INVALID")
            if row["kind"]=="QUARANTINE_ORIGINAL_RECONCILED":
                # D2C was genuinely quarantined then recovered using the exact
                # immutable original provider ZIPs. Require this DIFFERENT
                # payload contract rather than fabricating two terminal events.
                ticket=list(EXPECTED_RUNS)[number-10]
                check(isinstance(payload,dict) and set(payload)=={
                    "ticket","run_id","previous_reason","manifest_sha256",
                    "original_head_sha256","original_science","replay"}
                    and payload["ticket"]==ticket
                    and type(payload["run_id"]) is int and payload["run_id"]>0
                    and payload["previous_reason"]=="PROVIDER_SOURCE_EVENT_SPOOFED"
                    and isinstance(payload["manifest_sha256"],str)
                    and SHA64.fullmatch(payload["manifest_sha256"])
                    and payload["original_head_sha256"]==events[8]["sha"]
                    and payload["original_science"] is False
                    and payload["replay"] is False,
                    "D2C_ORIGINAL_RECONCILIATION_INVALID")
                terminals.append({"ticket":ticket,"run_id":payload["run_id"],
                                  "evidence_sha":payload["manifest_sha256"]})
            if row["kind"]=="PROVIDER_VERIFIED_TERMINAL":
                # D2J ticket identity is derived from the authenticated
                # admission at event 15; the provider-anchor check later
                # requires the exact production run ID and source SHA.
                admission=json.loads(events[14]["payload"])
                admitted_source=admission.get("source_sha") if isinstance(admission,dict) else None
                check(isinstance(admitted_source,str) and SHA40.fullmatch(admitted_source),
                      "D2J_SOURCE_ADMISSION_INVALID")
                lane_suffix="wingless" if number==20 else "yggdrasil"
                ticket="f139-d2j-"+lane_suffix+"-"+admitted_source[:12]
                check(isinstance(payload,dict) and set(payload)=={
                    "ticket","run_id","evidence_sha"}
                    and payload["ticket"]==ticket
                    and type(payload["run_id"]) is int and payload["run_id"]>0
                    and isinstance(payload["evidence_sha"],str)
                    and SHA64.fullmatch(payload["evidence_sha"]),
                    "TERMINAL_EVENT_FIELDS_INVALID")
                terminals.append(payload)
            if number==23:
                check(digest==expected_head,"SEALED_EVENT_HEAD_MISMATCH")
        else:
            check(row["kind"]=="SOURCE_TRANSITION_ADMITTED",
                  "NON_SOURCE_EVENT_AFTER_SEALED_PREFIX")
            check(isinstance(payload,dict) and set(payload)=={
                "schema","from_source_sha","to_source_sha",
                "prior_event_head_sha256","verified_historical_tasks",
                "new_dispatches","scientific_first_use"},
                  "SOURCE_SUFFIX_FIELDS_INVALID")
            target=payload["to_source_sha"]
            static_index=(ALLOWED_SOURCE_SUCCESSORS.index(target)
                          if target in ALLOWED_SOURCE_SUCCESSORS else None)
            static_approved=(static_index is not None
                             and static_index>approved_index)
            live_main_approved=(qualified_main_sha is not None
                                and target==qualified_main_sha
                                and number==len(events)
                                and approved_index<len(ALLOWED_SOURCE_SUCCESSORS))
            check(payload["schema"]=="forge.f139.source-transition.v1"
                  and payload["from_source_sha"]==current_source
                  and payload["prior_event_head_sha256"]==prior
                  and (static_approved or live_main_approved)
                  and type(payload["verified_historical_tasks"]) is int
                  and payload["verified_historical_tasks"]==4
                  and type(payload["new_dispatches"]) is int
                  and payload["new_dispatches"]==0
                  and payload["scientific_first_use"] is False,
                  "SOURCE_SUFFIX_AUTHORITY_OR_ORDER_DRIFT")
            current_source=target
            approved_index=(static_index if static_approved
                            else len(ALLOWED_SOURCE_SUCCESSORS))
        prior=digest
    check(tuple(kinds)==REAL_23_EVENT_KINDS,
          "D2J_HISTORY_SHAPE_INVALID")
    admission=json.loads(events[14]["payload"])
    source=admission.get("source_sha") if isinstance(admission,dict) else None
    check(isinstance(source,str) and SHA40.fullmatch(source),
          "D2J_SOURCE_ADMISSION_INVALID")
    expected_tickets=set(list(EXPECTED_RUNS)[:2]) | {
        "f139-d2j-wingless-"+source[:12],
        "f139-d2j-yggdrasil-"+source[:12]}
    check(len(terminals)==4 and len({x["ticket"] for x in terminals})==4
          and {x["ticket"] for x in terminals}==expected_tickets,
          "FOUR_DISTINCT_AUTHENTIC_COMPLETION_EVENTS_REQUIRED")
    return {x["ticket"]:x for x in terminals}, prior, current_source


def verify_d2j_task_bindings(events, tasks):
    """Verify native-controller D2J manifest/rows without writing to SQLite.

    A head-sealed event proves only immutable event bytes; mutable task rows
    must still match the admitted manifest. Use the controller's frozen planner
    instead of constructing a second, less strict manifest definition.
    """
    admissions=[row for row in events if row["kind"]=="UNATTENDED_SUCCESSION_ADMITTED"]
    check(len(admissions)==1 and admissions[0]["seq"]==15,
          "D2J_ADMISSION_EVENT_ABSENT")
    event=admissions[0]
    try:
        doc=json.loads(event["payload"])
    except (TypeError,ValueError) as exc:
        raise CustodyBlocked("F139_D2K_CUSTODY_D2J_ADMISSION_INVALID_JSON") from exc
    check(isinstance(doc,dict) and set(doc)=={
        "schema","source_sha","prior_event_head_sha256","manifest_sha256",
        "tickets","new_dispatches","scientific_first_use"},
        "D2J_ADMISSION_FIELDS_INVALID")
    source=doc["source_sha"]
    check(isinstance(source,str) and SHA40.fullmatch(source)
          and doc["schema"]=="forge.f139.d2j-once-only-succession.v1"
          and doc["prior_event_head_sha256"]==event["prior_sha"]
          and type(doc["new_dispatches"]) is int and doc["new_dispatches"]==0
          and doc["scientific_first_use"] is False,
          "D2J_ADMISSION_INVALID")
    plan=d2j_plan(source,event["prior_sha"])
    manifest_sha256=hash_bytes(canonical(plan))
    expected_items={task["ticket"]:task for task in plan["tasks"]}
    check(doc["manifest_sha256"]==manifest_sha256
          and doc["tickets"]==[task["ticket"] for task in plan["tasks"]],
          "D2J_ADMISSION_MANIFEST_DRIFT")
    actual={task["ticket"]:task for task in tasks}
    check(set(expected_items).issubset(actual)
          and len(expected_items)==2
          and all(actual[ticket]["lane"]==planned["lane"]
                  and actual[ticket]["source_sha"]==planned["source_sha"]
                  and actual[ticket]["manifest_sha"]==manifest_sha256
                  for ticket,planned in expected_items.items()),
          "D2J_ADMISSION_TASK_BINDING_DRIFT")
    return manifest_sha256


def verify_evidence(root: Path, row: dict, epoch: int, anchor: dict):
    check(row["stage"]=="VERIFIED" and type(row["run_id"]) is int
          and row["run_id"]>0 and isinstance(row["evidence_sha"],str)
          and SHA64.fullmatch(row["evidence_sha"]), "RECEIPT_ROW_NOT_VERIFIED")
    ticket=row["ticket"]
    check(ticket in anchor and row["run_id"]==anchor[ticket]["run_id"]
          and row["source_sha"]==anchor[ticket]["source_sha"],
          "EXTERNAL_PROVIDER_RUN_OR_SOURCE_DRIFT")
    check(isinstance(ticket,str) and ticket.startswith("f139-d2")
          and isinstance(row["source_sha"],str)
          and SHA40.fullmatch(row["source_sha"]),"RECEIPT_SOURCE_INVALID")
    base=root/"evidence"
    check(base.is_dir() and not base.is_symlink(),"EVIDENCE_ROOT_INVALID")
    folder=Path(row["evidence_dir"])
    check(folder.is_dir() and not folder.is_symlink()
          and folder.resolve()==(base/ticket/str(row["run_id"])).resolve()
          and folder.resolve().is_relative_to(base.resolve()),
          "EVIDENCE_PATH_NOT_BOUND")
    check(not any(p.is_symlink() for p in (base/ticket,base/ticket/str(row["run_id"]))),
          "EVIDENCE_SYMLINK")
    names={"manifest.json","ubuntu-latest.zip","windows-latest.zip"}
    check({p.name for p in folder.iterdir()}==names,"EVIDENCE_MEMBER_SET")
    manifest_file=folder/"manifest.json"
    check(not manifest_file.is_symlink() and manifest_file.stat().st_size<=8192,
          "MANIFEST_UNTRUSTED")
    raw=manifest_file.read_bytes()
    check(hash_bytes(raw)==row["evidence_sha"],"MANIFEST_DIGEST_CHANGED")
    try: manifest=json.loads(raw)
    except ValueError as exc: raise CustodyBlocked("F139_D2K_CUSTODY_MANIFEST_JSON") from exc
    check(canonical(manifest)==raw
          and manifest.get("schema")=="forge.f139.windows-evidence-manifest.v1"
          and manifest.get("ticket")==ticket and manifest.get("run_id")==row["run_id"]
          and manifest.get("scientific_originals")==0
          and manifest.get("approved_science") is False
          and isinstance(manifest.get("sha256"),dict)
          and set(manifest["sha256"])==set(OS_LABELS),
          "MANIFEST_IDENTITY_OR_AUTHORITY")
    for oslabel in OS_LABELS:
        p=folder/(oslabel+".zip")
        check(p.is_file() and not p.is_symlink()
              and 0<p.stat().st_size<MAX_ZIP_BYTES,"ARCHIVE_UNTRUSTED")
        blob=p.read_bytes()
        provider=anchor[ticket]["artifacts"][oslabel]
        check(hash_bytes(blob)==manifest["sha256"][oslabel],
              "ARCHIVE_SHA_CHANGED")
        check(len(blob)==provider["size_in_bytes"]
              and hash_bytes(blob)==provider["sha256"],
              "EXTERNAL_PROVIDER_ARTIFACT_DRIFT")
        receipt_from_zip(blob,{"digest":"sha256:"+hash_bytes(blob),
                               "size_in_bytes":len(blob)},
                         row,row["run_id"],oslabel,epoch)
    return {"ticket":ticket,"run_id":row["run_id"],
            "manifest_sha256":row["evidence_sha"]}


def audit(dbpath: Path, expected_source: str, expected_head: str,
          *, qualified_main_sha: str | None = None):
    check(isinstance(expected_source,str) and SHA40.fullmatch(expected_source),
          "EXPECTED_SOURCE_INVALID")
    check(isinstance(expected_head,str) and SHA64.fullmatch(expected_head),
          "EXPECTED_PREFIX_NOT_SUPPLIED")
    provider_anchor=load_provider_anchor()
    dbpath=Path(dbpath)
    with tempfile.TemporaryDirectory(prefix="f139-d2l-readonly-") as tmp:
        local=copied_snapshot(dbpath,Path(tmp))
        connection=sqlite3.connect(str(local),timeout=0.25)
        connection.row_factory=sqlite3.Row
        try:
            connection.execute("PRAGMA query_only=ON")
            check(connection.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
                  "SQLITE_INTEGRITY_FAILURE")
            meta=connection.execute("SELECT * FROM meta WHERE id=1").fetchone()
            check(meta is not None and meta["enabled"]==1
                  and meta["legacy_suspended"]==1
                  and meta["source_sha"]==expected_source,
                  "SEALED_METADATA_NOT_MATCHED")
            events=connection.execute("SELECT * FROM events ORDER BY seq").fetchall()
            terminals,observed_head,derived_source=verify_chain(
                events,expected_head,qualified_main_sha=qualified_main_sha)
            check(meta["head_seq"]==len(events)
                  and meta["head_hash"]==observed_head
                  and meta["source_sha"]==(derived_source if len(events)>23 else expected_source),
                  "SOURCE_SUFFIX_METADATA_DRIFT")
            tasks=[dict(row) for row in connection.execute("SELECT * FROM tasks ORDER BY ticket")]
            admitted_manifest=verify_d2j_task_bindings(events,tasks)
            check(len(tasks)==4
                  and sum(t["ticket"].startswith("f139-d2c-") for t in tasks)==2
                  and sum(t["ticket"].startswith("f139-d2j-") for t in tasks)==2,
                  "FOUR_HISTORICAL_TASKS_REQUIRED")
            check({t["ticket"] for t in tasks}==set(terminals)
                  and all(terminals[t["ticket"]]["run_id"]==t["run_id"]
                          and terminals[t["ticket"]]["evidence_sha"]==t["evidence_sha"]
                          for t in tasks),
                  "TERMINAL_EVENT_TASK_OR_RECEIPT_DRIFT")
            reports=[verify_evidence(dbpath.parent,t,meta["epoch"],provider_anchor) for t in tasks]
        finally:
            connection.close()
    return {"schema":"forge.f139.d2k-custody.readonly-audit.v1",
            "disposition":"LOCAL_CUSTODY_SNAPSHOT_VERIFIED_NOT_SOURCE_TRANSITION",
            "event_count":len(events),"historical_prefix_event_count":23,
            "source_only_suffix_count":len(events)-23,
            "observed_current_head_sha256":observed_head,
            "task_count":4,"archive_count":8,
            "expected_source_sha":expected_source,"sealed_event_head_sha256":expected_head,
            "external_provider_anchor_records":4,
            "external_provider_artifacts_checked":8,
            "d2j_admission_manifest_sha256":admitted_manifest,
            "d2j_task_bindings_verified":2,
            "original_database_writes":0,"controller_actions":0,
            "scientific_first_use":False,
            "qualified_protected_main_sha":qualified_main_sha,
            "live_main_source_suffix_verified":bool(
                qualified_main_sha and derived_source==qualified_main_sha
                and len(events)>23),
            "receipts":reports}


def main():
    parser=argparse.ArgumentParser(description="F139 read-only copy-and-verify; no transitions")
    parser.add_argument("--db",required=True,type=Path)
    parser.add_argument("--expected-source-sha",required=True)
    parser.add_argument("--sealed-event-head-sha256",required=True)
    parser.add_argument("--qualified-protected-main-sha")
    args=parser.parse_args()
    check(os.name=="nt","NATIVE_WINDOWS_RUNNER_REQUIRED")
    if args.qualified_protected_main_sha is not None:
        # Source only. GitHub checks branch protection and exact HEAD in the
        # owner profile. This does NOT sign historical custody or permit writes.
        from f139.local_controller import GitHub
        check(GitHub().protected_main()==args.qualified_protected_main_sha,
              "LIVE_PROTECTED_MAIN_NOT_MATCHED")
    result=audit(args.db,args.expected_source_sha,args.sealed_event_head_sha256,
                 qualified_main_sha=args.qualified_protected_main_sha)
    print(json.dumps(result,sort_keys=True,separators=(",",":")))


if __name__=="__main__":
    try: main()
    except (CustodyBlocked,sqlite3.DatabaseError,OSError,ValueError) as exc:
        raise SystemExit("F139_D2K_CUSTODY_FAIL_CLOSED "+str(exc)) from exc
