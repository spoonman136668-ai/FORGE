"""F139-D2L: nonintrusive, content-addressed read-only custody preflight.

This deliberately does not start/stop any controller or transition accepted refs.
An externally sealed 23-event head is mandatory; the local DB is not its own witness.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from f139.local_controller import (
    ZERO, MAX_ZIP_BYTES, canonical, hash_bytes, receipt_from_zip,
)

SHA40=re.compile(r"[a-f0-9]{40}\\Z")
SHA64=re.compile(r"[a-f0-9]{64}\\Z")
MAX_SOURCE_BYTES=16_000_000
OS_LABELS=("ubuntu-latest","windows-latest")


class CustodyBlocked(RuntimeError):
    pass


def check(condition, reason):
    if not condition:
        raise CustodyBlocked("F139_D2L_"+reason)


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


def verify_chain(events, expected_head: str):
    check(isinstance(expected_head,str) and SHA64.fullmatch(expected_head),
          "UNSEALED_EXPECTED_EVENT_HEAD")
    check(len(events)==23, "EVENT_COUNT_NOT_23")
    prior=ZERO
    kinds=[]
    for number,row in enumerate(events,1):
        check(row["seq"]==number and row["prior_sha"]==prior,
              "EVENT_SEQUENCE_OR_PREDECESSOR")
        try:
            payload=json.loads(row["payload"])
        except (ValueError,TypeError) as exc:
            raise CustodyBlocked("F139_D2L_INVALID_EVENT_JSON") from exc
        check(canonical(payload).decode()==row["payload"],"EVENT_NOT_CANONICAL")
        record={"seq":number,"prior_sha":prior,
                "kind":row["kind"],"payload":payload}
        prior=hash_bytes(canonical(record))
        check(prior==row["sha"],"EVENT_HASH_MISMATCH")
        kinds.append(row["kind"])
    observed=Counter(kinds)
    check(observed["SOURCE_TRANSITION_ADMITTED"]==3
          and observed["UNATTENDED_SUCCESSION_ADMITTED"]==1
          and observed["PROVIDER_VERIFIED_TERMINAL"]==4
          and kinds[14]=="UNATTENDED_SUCCESSION_ADMITTED",
          "D2J_HISTORY_SHAPE_INVALID")
    check(prior==expected_head,"SEALED_EVENT_HEAD_MISMATCH")
    return prior


def verify_evidence(root: Path, row: dict, epoch: int):
    check(row["stage"]=="VERIFIED" and type(row["run_id"]) is int
          and row["run_id"]>0 and isinstance(row["evidence_sha"],str)
          and SHA64.fullmatch(row["evidence_sha"]), "RECEIPT_ROW_NOT_VERIFIED")
    ticket=row["ticket"]
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
    except ValueError as exc: raise CustodyBlocked("F139_D2L_MANIFEST_JSON") from exc
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
        check(hash_bytes(blob)==manifest["sha256"][oslabel],
              "ARCHIVE_SHA_CHANGED")
        receipt_from_zip(blob,{"digest":"sha256:"+hash_bytes(blob),
                               "size_in_bytes":len(blob)},
                         row,row["run_id"],oslabel,epoch)
    return {"ticket":ticket,"run_id":row["run_id"],
            "manifest_sha256":row["evidence_sha"]}


def audit(dbpath: Path, expected_source: str, expected_head: str):
    check(isinstance(expected_source,str) and SHA40.fullmatch(expected_source),
          "EXPECTED_SOURCE_INVALID")
    check(isinstance(expected_head,str) and SHA64.fullmatch(expected_head),
          "EXPECTED_PREFIX_NOT_SUPPLIED")
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
            check(meta is not None and meta["head_seq"]==23
                  and meta["head_hash"]==expected_head
                  and meta["source_sha"]==expected_source
                  and meta["enabled"]==1 and meta["legacy_suspended"]==1,
                  "SEALED_METADATA_NOT_MATCHED")
            events=connection.execute("SELECT * FROM events ORDER BY seq").fetchall()
            verify_chain(events,expected_head)
            tasks=[dict(row) for row in connection.execute("SELECT * FROM tasks ORDER BY ticket")]
            check(len(tasks)==4
                  and sum(t["ticket"].startswith("f139-d2c-") for t in tasks)==2
                  and sum(t["ticket"].startswith("f139-d2j-") for t in tasks)==2,
                  "FOUR_HISTORICAL_TASKS_REQUIRED")
            reports=[verify_evidence(dbpath.parent,t,meta["epoch"]) for t in tasks]
        finally:
            connection.close()
    return {"schema":"forge.f139.d2l.readonly-audit.v1",
            "disposition":"LOCAL_CUSTODY_SNAPSHOT_VERIFIED_NOT_SOURCE_TRANSITION",
            "event_count":23,"task_count":4,"archive_count":8,
            "expected_source_sha":expected_source,"sealed_event_head_sha256":expected_head,
            "original_database_writes":0,"controller_actions":0,
            "scientific_first_use":False,"receipts":reports}


def main():
    parser=argparse.ArgumentParser(description="F139 read-only copy-and-verify; no transitions")
    parser.add_argument("--db",required=True,type=Path)
    parser.add_argument("--expected-source-sha",required=True)
    parser.add_argument("--sealed-event-head-sha256",required=True)
    args=parser.parse_args()
    check(os.name=="nt","NATIVE_WINDOWS_RUNNER_REQUIRED")
    result=audit(args.db,args.expected_source_sha,args.sealed_event_head_sha256)
    print(json.dumps(result,sort_keys=True,separators=(",",":")))


if __name__=="__main__":
    try: main()
    except (CustodyBlocked,sqlite3.DatabaseError,OSError,ValueError) as exc:
        raise SystemExit("F139_D2L_FAIL_CLOSED "+str(exc)) from exc
