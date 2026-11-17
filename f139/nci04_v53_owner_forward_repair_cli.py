"""F139 V53 detached rehearsals and quiesced original-owner commit CLI.

The live mode must be called only by the separate GitHub owner-authenticated
Windows workflow after checking exact main, CI, issue approval, original SID,
task and source. This CLI independently enforces the existing task's hold.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v41_cold_copy_verifier as cold
from f139.nci04_v50_original_native_activation import original_task_quiesced
from f139.nci04_v53_owner_forward_repair import (
    FROM_SOURCE, HEAD_SEQ, HEAD_SHA, need, original_snapshot,
    make_proof, apply_copy_or_original,
)

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def require_owner_path(path, *, must_exist=True):
    p = Path(path).absolute()
    need(p.is_absolute() and not p.is_symlink()
         and (not must_exist or p.is_file()), "ORIGINAL_PATH_MISSING")
    return p


def read_frozen(path):
    with closing(Database.open_readonly(path)) as db:
        prior = original_snapshot(db)
        return {
            "source_sha": db.meta()["source_sha"],
            "head_seq": db.meta()["head_seq"],
            "head_sha256": db.meta()["head_hash"],
            "terminal_tasks_sha256": prior["terminal_tasks_sha256"],
        }


def backed_up(source, copy_path):
    """SQLite native online backup from RO source; never copy WAL bytes raw."""
    source = require_owner_path(source)
    copy_path = Path(copy_path).absolute()
    need(not copy_path.exists() and
         copy_path.parent.is_dir() and
         not copy_path.parent.is_symlink() and
         copy_path != source,
         "BACKUP_DESTINATION_NOT_FRESH")
    before = read_frozen(source)
    read = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True,
                           isolation_level=None, timeout=10)
    read.execute("PRAGMA query_only=ON")
    write = sqlite3.connect(str(copy_path), isolation_level=None, timeout=10)
    try:
        read.backup(write, pages=256, sleep=0.02)
        write.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        write.execute("PRAGMA journal_mode=DELETE")
    finally:
        write.close()
        read.close()
    # A detached SQLite database is not a complete cold restore by itself.
    # Database.verify() also checks the original historical negative ZIPs
    # relative to db.filename.parent. Reuse the existing hash-bound,
    # create-only two-artifact copier; never symlink, download or regenerate.
    # Nested live-rehearsal copies within one verified custody directory
    # already share those adjuncts and must not overwrite them.
    if source.parent.resolve() != copy_path.parent.resolve():
        with closing(Database.open_readonly(source)) as verified_source:
            negatives = cold.required_negative_custody(verified_source)
            need(verified_source.conn.total_changes == 0,
                 "SOURCE_CUSTODY_READ_WROTE")
        adjunct = copy_path.parent / "native-negative"
        need(not adjunct.is_symlink(), "DETACHED_NEGATIVE_CUSTODY_SYMLINK")
        # GitHub's self-hosted RUNNER_TEMP can persist across two distinct
        # owner-authenticated jobs. Recheck every original and copied SHA if
        # already staged; otherwise create files once, with exclusive 'xb'.
        # An incomplete or altered prior copy fails closed, never overwritten.
        cold.copy_negative_custody(
            source.parent, copy_path.parent, negatives,
            copy_files=not adjunct.exists())
    copied = read_frozen(copy_path)
    after = read_frozen(source)
    need(before == copied == after and
         copy_path.stat().st_size > 1024 and
         len(sha256(copy_path)) == 64,
         "BACKUP_COPY_OR_SOURCE_DRIFT")
    return sha256(copy_path)


def rehearsal(copy_path, args, backup_sha):
    path = require_owner_path(copy_path)
    need(sha256(path) == backup_sha,
         "DETACHED_BACKUP_SHA_CHANGED")
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database(path)) as db:
            proof = make_proof(db, target=args.target,
                owner_comment_id=args.owner_comment_id,
                main_run_id=args.main_run_id,
                rehearsal_run_id=args.rehearsal_run_id,
                backup_sha256=backup_sha)
            outcome = apply_copy_or_original(db, proof)
    need(outcome["head_seq"] == HEAD_SEQ+2,
         "DETACHED_EVENT1839_MISSING")
    return outcome


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--mode", choices=("preflight","rehearse","backup","commit"),
                   required=True)
    p.add_argument("--db",required=True)
    p.add_argument("--copy")
    p.add_argument("--target")
    p.add_argument("--owner-comment-id",type=int)
    p.add_argument("--main-run-id",type=int)
    p.add_argument("--rehearsal-run-id",type=int)
    p.add_argument("--backup-sha")
    args=p.parse_args(argv)
    db_path=require_owner_path(args.db)
    need(db_path.name=="state.sqlite" and
         db_path.parent.name=="FORGE-F139" and
         os.environ.get("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE"
         and os.environ.get("RUNNER_NAME")=="FORGE-CODEX-REMOTE"
         and os.environ.get("GITHUB_EVENT_NAME")=="issue_comment"
         and os.environ.get("GITHUB_ACTOR")=="spoonman136668-ai"
         and os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
         and not os.environ.get("OPENAI_API_KEY"),
         "EXACT_ORIGINAL_OWNER_ENVIRONMENT_REQUIRED")
    frozen=read_frozen(db_path)
    if args.mode=="preflight":
        print("F139_V53_PREFLIGHT="+json.dumps(frozen,sort_keys=True))
        return 0
    need(args.target == os.environ.get("GITHUB_SHA") and
         args.owner_comment_id and args.owner_comment_id > 6935011550 and
         args.main_run_id and args.main_run_id > 0 and
         args.rehearsal_run_id and args.rehearsal_run_id > 0,
         "SOURCE_TARGET_OR_OWNER_RECEIPT_MISSING")
    if args.mode=="rehearse":
        copy_path=require_owner_path(args.copy,must_exist=False)
        backup_sha=backed_up(db_path,copy_path)
        result=rehearsal(copy_path,args,backup_sha)
        need(read_frozen(db_path)==frozen,"ORIGINAL_CHANGED_DURING_REHEARSAL")
        print("F139_V53_DETACHED_REHEARSAL="+json.dumps({
            **result,"original_mutations":0,
            "backup_sha256":backup_sha},sort_keys=True))
        return 0
    # Both backup and commit are forbidden until the actual original task is
    # disabled, stopped and child-free. Reusing the existing V50 guard is
    # intentional: a new helper must not enlarge original-owner authority.
    need(os.name=="nt" and sys.platform=="win32"
         and os.environ.get("F139_V53_NATIVE_LIVE_AUTHENTICATED")=="1",
         "LIVE_AUTHENTICATED_WINDOWS_ONLY")
    original_task_quiesced(db_path)
    if args.mode=="backup":
        copy_path=require_owner_path(args.copy,must_exist=False)
        backup_sha=backed_up(db_path,copy_path)
        original_task_quiesced(db_path)
        print("F139_V53_COLD_BACKUP="+json.dumps({
            "backup_sha256":backup_sha,"original":frozen,
            "source_mutations":0},sort_keys=True))
        return 0
    need(args.mode=="commit" and args.copy and args.backup_sha,
         "UNKNOWN_LIVE_OPERATION")
    copy_path=require_owner_path(args.copy)
    need(sha256(copy_path)==args.backup_sha and
         read_frozen(copy_path)==frozen,
         "COLD_BACKUP_NOT_EXACT_PREIMAGE")
    # Exercise the exact material source repair on a separate fresh clone of
    # the previously verified backup before committing original SQLite.
    test_path=copy_path.with_name(copy_path.stem+"-rehearsal.sqlite")
    need(not test_path.exists(), "DETACHED_REHEARSAL_ALREADY_CONSUMED")
    rehearsal_hash=backed_up(copy_path,test_path)
    need(read_frozen(test_path) == frozen,
         "BACKUP_LOGICAL_CUSTODY_CHANGED")
    rehearsal(test_path,args,rehearsal_hash)
    original_task_quiesced(db_path)
    need(read_frozen(db_path)==frozen,
         "ORIGINAL_CHANGED_PRECOMMIT")
    with SingleOwner(db_path.with_suffix(".lock")):
        original_task_quiesced(db_path)
        with closing(Database(db_path)) as db:
            proof=make_proof(db,target=args.target,
                owner_comment_id=args.owner_comment_id,
                main_run_id=args.main_run_id,
                rehearsal_run_id=args.rehearsal_run_id,
                backup_sha256=args.backup_sha)
            result=apply_copy_or_original(db,proof)
    original_task_quiesced(db_path)
    with closing(Database.open_readonly(db_path)) as verified:
        verified.verify()
        need(verified.meta()["source_sha"]==args.target and
             verified.meta()["head_seq"]==HEAD_SEQ+2 and
             verified.meta()["head_hash"]==result["head_sha256"],
             "POSTCOMMIT_ORIGINAL_SOURCE_DRIFT")
    print("F139_V53_ORIGINAL_EVENT1839="+json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("F139_V53_DENIED "+type(exc).__name__+": "+str(exc),
              file=sys.stderr,flush=True)
        raise SystemExit(1) from exc
