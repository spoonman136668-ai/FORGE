"""Original F139 single-owner V3 signed provider terminal, development-only.

This is not a controller, scheduler, queue, replay tool or science approval.
Requires the existing original Windows SingleOwner lock, immutable signed
admission, independent GitHub provider ZIPs and an atomic SQLite terminal.
"""
from __future__ import annotations
import io
import json
from pathlib import Path
import re
import zipfile

from f139.local_controller import Database, GitHub, SingleOwner,     store_evidence, canonical as owner_canonical, utc_now
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import make_signed_dispatch_inputs
from f139.nci04_owner_ledger import frozen_native_issue, verify_native_activation
from f139.nci04_signed_native import NativeAdmission, admit_native_intent
from f139.nci04_owner_v3_dispatch import signature, verify_claim
from f139.nci04_worker_v3 import SCHEMA as REPORT_SCHEMA, RECEIPT as RECEIPT_SCHEMA, receipt_v3
from f139.nci04_g32_owner_custody import event_rows

OS=("ubuntu-latest","windows-latest")
KIND="NATIVE_V_THREE_PROVIDER_CUSTODY"
SCHEMA="forge.f139.original-owner-v3-provider-custody.v1"
REPO="spoonman136668-ai/FORGE"
WORKFLOW="forge-f139-development-worker.yml"
WORKFLOW_ID=388797257
MEMBERS={"f139-v3-native-report.json","f139-v3-native-receipt.json"}
MAX_BYTES=2_000_000
SHA64=re.compile(r"[a-f0-9]{64}\Z")


class V3TerminalDenied(ValueError):
    pass


def need(value,reason):
    if not value: raise V3TerminalDenied("F139_ORIGINAL_V3_"+reason)


def admission_for_original(db, ticket, run_id, owner_key):
    issue=frozen_native_issue(db,ticket)
    meta=db.meta()
    need(type(owner_key) is str and len(owner_key)>=32
         and issue.number>1138
         and issue.source_sha==meta["source_sha"]
         and issue.source_sha!="0743ca22b76ebd943a66f05a36ea919301676be0"
         and verify_native_activation(db)
         and issue.lane=="Yggdrasil"
         and issue.candidate.path=="yggdrasil/public_causal_cells.py",
         "NEW_ACTIVATED_SOURCE_ISSUE_ONLY")
    a=event_rows(db,"NATIVE_DEVELOPMENT_ADMITTED",ticket)
    c=event_rows(db,"BEFORE_DISPATCH_INTENT",ticket)
    d=event_rows(db,"DISPATCH_POST_RETURNED",ticket)
    verified=event_rows(db,"PROVIDER_VERIFIED_TERMINAL",ticket)
    prior=event_rows(db,KIND,ticket)
    need(len(a)==len(c)==len(d)==1 and not verified and not prior
         and 322<a[0][0]["seq"]<c[0][0]["seq"]<d[0][0]["seq"],
         "FRESH_UNIQUE_ORIGINAL_SIGNED_CLAIM_REQUIRED")
    # Reconstruct exactly the original owner's signature and intent.
    owner_fields=make_signed_dispatch_inputs(
        issue,owner_hmac_key=owner_key,epoch=meta["epoch"])
    proof=signature(owner_key,issue,meta["epoch"],a[0][0]["seq"],
                    a[0][0]["sha"],c[0][0]["seq"],c[0][0]["sha"])
    verify_claim(owner_key,issue,meta["epoch"],a[0][0]["seq"],
                 a[0][0]["sha"],c[0][0]["seq"],c[0][0]["sha"],proof)
    admissions={}
    for oslabel in OS:
        provider={
            "key":owner_key,"ticket":ticket,"lane":issue.lane,
            "source_sha":issue.source_sha,"epoch":str(meta["epoch"]),
            "signature":owner_fields["signature"],
            "repository":REPO,
            "ref":"refs/heads/main","event":"workflow_dispatch",
            "head_sha":meta["source_sha"],"run_attempt":"1",
            "run_id":str(run_id),"os":oslabel,
        }
        admission=admit_native_intent(
            provider,issue.intent_raw,
            native_signature=owner_fields["native_signature"],
            issue_number=str(issue.number),issue_id=str(issue.issue_id),
            issue_body_sha256=issue.issue_body_sha256,
            authenticated_main_sha=meta["source_sha"],
            authenticated_target_commit=issue.candidate.target_commit,
            authenticated_target_tree=issue.candidate.target_tree_sha)
        need(type(admission) is NativeAdmission
             and admission.runner_os==oslabel
             and admission.ticket==ticket and admission.run_id==run_id,
             "RECONSTRUCTED_SIGNED_ADMISSION_DRIFT")
        admissions[oslabel]=admission
    return issue, admissions, a[0][0],c[0][0]


def inner_zip(raw,meta,admission):
    need(type(meta) is dict and type(raw) is bytes
         and 0<len(raw)<MAX_BYTES
         and meta.get("size_in_bytes")==len(raw)
         and meta.get("digest")=="sha256:"+digest(raw)
         and meta.get("expired") is False,
         "GITHUB_ARTIFACT_SIZE_DIGEST_OR_EXPIRY_INVALID")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zip:
            info=zip.infolist()
            need(len(info)==2 and {x.filename for x in info}==MEMBERS
                 and all(not x.is_dir() and not x.flag_bits&1
                         and 0<x.file_size<128000
                         and 0<x.compress_size<MAX_BYTES for x in info),
                 "SIGNED_PROVIDER_ARTIFACT_INVENTORY_INVALID")
            blobs={name:zip.read(name) for name in MEMBERS}
    except (zipfile.BadZipFile,OSError,RuntimeError,ValueError) as exc:
        if isinstance(exc,V3TerminalDenied):raise
        raise V3TerminalDenied("F139_ORIGINAL_V3_ZIP_UNREADABLE") from exc
    try:
        report=json.loads(blobs["f139-v3-native-report.json"])
        receipt=json.loads(blobs["f139-v3-native-receipt.json"])
    except (UnicodeError,ValueError) as exc:
        raise V3TerminalDenied("F139_ORIGINAL_V3_REPORT_JSON_INVALID") from exc
    need(type(report) is dict and type(receipt) is dict
         and canonical(report)==blobs["f139-v3-native-report.json"]
         and canonical(receipt)==blobs["f139-v3-native-receipt.json"]
         and report.get("schema")==REPORT_SCHEMA
         and receipt.get("schema")==RECEIPT_SCHEMA,
         "SIGNED_PROVIDER_SCHEMA_OR_CANONICAL_BYTES_DRIFT")
    expected=receipt_v3(admission,report)
    need(receipt==expected and receipt.get("native_qualified") is True
         and receipt.get("development_only") is True
         and receipt.get("scientific_first_use_authorized") is False
         and receipt.get("accepted_ref_mutations")==0,
         "V3_POSITIVE_SIGNED_REPORT_UNQUALIFIED")
    return {"receipt_sha256":digest(blobs["f139-v3-native-receipt.json"]),
            "report_sha256":digest(blobs["f139-v3-native-report.json"])}


def qualified_original_github_run(api,run_id,ticket,source,started_at,admissions):
    path="repos/"+REPO+"/actions/runs/"+str(run_id)
    run=api.get(path)
    from f139.local_controller import parse_time
    import datetime as dt
    need(type(run) is dict and run.get("id")==run_id
         and run.get("display_title")=="F139 "+ticket
         and run.get("name")=="F139 "+ticket
         and run.get("event")=="workflow_dispatch"
         and run.get("workflow_id")==WORKFLOW_ID
         and run.get("path")==".github/workflows/"+WORKFLOW
         and run.get("head_sha")==source
         and run.get("head_branch") in ("main","f139-owner-release-"+source)
         and run.get("run_attempt")==1
         and run.get("status")=="completed"
         and run.get("conclusion")=="success"
         and run.get("repository",{}).get("full_name")==REPO
         and parse_time(run["created_at"])>=
             parse_time(started_at)-dt.timedelta(minutes=2),
         "ORIGINAL_GITHUB_SIGNED_PROVIDER_RUN_NOT_POSITIVE")
    jobs=api.get(path+"/jobs?per_page=100")
    arts=api.get(path+"/artifacts?per_page=100")
    rows=jobs.get("jobs") if type(jobs) is dict else None
    artifacts=arts.get("artifacts") if type(arts) is dict else None
    need(type(rows) is list and 3<=len(rows)<=16
         and jobs.get("total_count")==len(rows)
         and type(artifacts) is list and len(artifacts)==2
         and arts.get("total_count")==len(artifacts),
         "GITHUB_PROVIDER_JOB_AND_ARTIFACT_INVENTORY_DRIFT")
    live={"native-authorize-v3"} | {
        "native-execute-v3 ("+x+")" for x in OS}
    need(len(set(j.get("name") for j in rows))==len(rows)
         and all((j.get("name") in live and j.get("conclusion")=="success"
                  and j.get("status")=="completed")
                 or (j.get("name") not in live
                     and j.get("status")=="completed"
                     and j.get("conclusion")=="skipped")
                 for j in rows)
         and {j.get("name") for j in rows if j.get("conclusion")=="success"}==live,
         "V1_V2_OR_UNAUTHORIZED_JOB_EXECUTED")
    auth=[j for j in rows if j.get("name")=="native-authorize-v3"]
    need(len(auth)==1 and type(auth[0].get("id")) is int and auth[0]["id"]>0,
         "ORIGINAL_SIGNED_AUTHORIZER_JOB_MISSING")
    proof,archives={},{}
    for label in OS:
        name="forge-f139-v3-native-receipt-"+label
        matches=[x for x in artifacts if x.get("name")==name]
        job=[x for x in rows if x.get("name")=="native-execute-v3 ("+label+")"]
        need(len(matches)==len(job)==1
             and type(matches[0].get("id")) is int and matches[0]["id"]>0
             and type(job[0].get("id")) is int and job[0]["id"]>0
             and matches[0].get("workflow_run",{}).get("id")==run_id
             and matches[0].get("workflow_run",{}).get("head_sha")==source,
             "EXACT_TWO_PROVIDER_ARTIFACTS_OR_JOBS_REQUIRED")
        raw=api.artifact(matches[0]["id"])
        verified=inner_zip(raw,matches[0],admissions[label])
        archives[label]=raw
        proof[label]=dict(
            verified,job_id=job[0]["id"],artifact_id=matches[0]["id"],
            outer_sha256=digest(raw))
    return proof,archives,auth[0]["id"]


def settle_original_v3(db,api,db_path,*,ticket,run_id,started_at,owner_key):
    """One ORIGINAL SQLite positive terminal; no source/worker/queue creation."""
    need(type(db) is Database and type(api) is GitHub
         and isinstance(db_path, Path) and type(run_id) is int and run_id>0
         and SingleOwner.held(db_path.with_suffix(".lock")),
         "SINGLE_ORIGINAL_OWNER_ONLY")
    db.verify()
    meta=db.meta()
    task=db.conn.execute("SELECT * FROM tasks WHERE ticket=?",(ticket,)).fetchone()
    need(task is not None and task["stage"]=="WAIT_PROVIDER"
         and task["run_id"] is None and task["source_sha"]==meta["source_sha"]
         and task["started_at"]==started_at,
         "NEW_UNSETTLED_ORIGINAL_TASK_REQUIRED")
    issue,admissions,a,c=admission_for_original(db,ticket,run_id,owner_key)
    evidence,archives,auth_id=qualified_original_github_run(
        api,run_id,ticket,meta["source_sha"],started_at,admissions)
    directory,manifest=store_evidence(
        db_path.parent,ticket,run_id,archives)
    receipt={
        "schema":SCHEMA,"ticket":ticket,
        "source_sha":meta["source_sha"],"run_id":run_id,
        "original_admission_event_seq":a["seq"],
        "original_admission_event_sha256":a["sha"],
        "original_claim_event_seq":c["seq"],
        "original_claim_event_sha256":c["sha"],
        "authorize_job_id":auth_id,
        "provider_platforms":evidence,
        "evidence_dir":directory,"evidence_manifest_sha256":manifest,
        "development_qualified":True,"scientific_first_use":False,
        "accepted_ref_mutations":0,"paid_model_calls":0}
    with db.transaction():
        db.verify()
        row=db.conn.execute(
            "SELECT stage,run_id,source_sha,started_at FROM tasks WHERE ticket=?",
            (ticket,)).fetchone()
        need(row is not None and row["stage"]=="WAIT_PROVIDER"
             and row["run_id"] is None
             and row["source_sha"]==meta["source_sha"]
             and row["started_at"]==started_at
             and not event_rows(db,KIND,ticket),
             "CONCURRENT_SIGNED_PROVIDER_SETTLEMENT")
        db.conn.execute(
            "UPDATE tasks SET stage='VERIFIED',run_id=?,evidence_dir=?,"
            "evidence_sha=?,completed_at=? WHERE ticket=?",
            (run_id,directory,manifest,utc_now(),ticket))
        db.event("PROVIDER_VERIFIED_TERMINAL",
                 {"ticket":ticket,"run_id":run_id,"evidence_sha":manifest})
        db.event(KIND,receipt)
        db.verify()
    return {"schema":SCHEMA,"ticket":ticket,"run_id":run_id,
            "source_sha":meta["source_sha"],"development_qualified":True,
            "scientific_first_use":False,
            "original_sqlite_terminal_verified":True}


def audit_v3_original_custody(db):
    """Cold reopen verifies original evidence bytes, terminal and no duplicate."""
    seen=set()
    for row in db.conn.execute(
            "SELECT payload FROM events WHERE kind=? ORDER BY seq",(KIND,)):
        doc=json.loads(row["payload"])
        ticket=doc.get("ticket")
        need(doc.get("schema")==SCHEMA
             and ticket not in seen and isinstance(ticket,str)
             and doc.get("development_qualified") is True
             and doc.get("scientific_first_use") is False
             and doc.get("accepted_ref_mutations")==0
             and doc.get("paid_model_calls")==0
             and set(doc.get("provider_platforms",{}))==set(OS),
             "COLD_PROVIDER_CUSTODY_INVALID_OR_REPLAY")
        seen.add(ticket)
        task=db.conn.execute(
            "SELECT stage,source_sha,run_id,evidence_dir,evidence_sha FROM tasks WHERE ticket=?",
            (ticket,)).fetchone()
        need(task is not None and task["stage"]=="VERIFIED"
             and task["source_sha"]==doc["source_sha"]
             and task["run_id"]==doc["run_id"]
             and task["evidence_dir"]==doc["evidence_dir"]
             and task["evidence_sha"]==doc["evidence_manifest_sha256"]
             and len(event_rows(db,"PROVIDER_VERIFIED_TERMINAL",ticket))==1,
             "COLD_ORIGINAL_SQLITE_TERMINAL_DRIFT")
        folder=Path(doc["evidence_dir"])
        need(folder.is_dir() and not folder.is_symlink()
             and folder.name==str(doc["run_id"])
             and folder.parent.name==ticket
             and {x.name for x in folder.iterdir()}==
                 {"ubuntu-latest.zip","windows-latest.zip","manifest.json"},
             "COLD_EVIDENCE_FOLDER_INVALID")
        manifest={"schema":"forge.f139.windows-evidence-manifest.v1",
                  "ticket":ticket,"run_id":doc["run_id"],
                  "sha256":{},"scientific_originals":0,"approved_science":False}
        for label in OS:
            path=folder/(label+".zip")
            need(path.is_file() and not path.is_symlink()
                 and digest(path.read_bytes())==
                     doc["provider_platforms"][label]["outer_sha256"],
                 "COLD_ZIP_BYTES_DRIFT")
            manifest["sha256"][label]=digest(path.read_bytes())
        need((folder/"manifest.json").read_bytes()==owner_canonical(manifest)
             and digest(owner_canonical(manifest))==
                 doc["evidence_manifest_sha256"],
             "COLD_MANIFEST_SHA256_DRIFT")
