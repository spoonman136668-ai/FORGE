"""V37 entry point into the existing original-owner custody handoff."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

from f139.nci04_native_contract import canonical
from f139.nci04_v32_original_owner_transition_cli import guarded_transition
from f139 import nci04_v37_source_transition as contract


def rehearse_private_history(db, target, event_id):
    """Authentic read-only input -> disposable copy. Never changes the owner.

    Reuse the prior custodied utility only as a development compatibility
    control. Production still builds and qualifies its own exact-source utility.
    """
    from f139.local_controller import Database, GitHub, SingleOwner
    from f139.nci04_native_contract import digest
    from f139.nci04_genenv_owner_backend import executable_custody
    from f139.nci04_v32_original_owner_transition_cli import (
        copy_provider_archives, copy_generation_executable, reactivate,
        rehearse_typed_generator)
    from f139.nci04_negative_owner_store import (
        TICKET as FIRST, RUN_ID as FIRST_RUN, ARTIFACT_SHA as FIRST_SHA)
    from f139.nci04_split_negative_custody import (
        TICKET as SECOND, RUN_ID as SECOND_RUN, ARTIFACT_SHA256 as SECOND_SHA)
    contract.need(type(db) is Database and getattr(db, "_readonly_opened", False) is True
        and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
        "READONLY_ORIGINAL_REQUIRED")
    before = db.meta().copy()
    binary, expected = executable_custody(db, contract.FROM_V36)
    with tempfile.TemporaryDirectory(prefix="f139-v37-private-rehearsal-") as temp:
        root = Path(temp)
        for ticket, run, wanted in ((FIRST, FIRST_RUN, FIRST_SHA), (SECOND, SECOND_RUN, SECOND_SHA)):
            relative = Path("native-negative")/ticket/str(run)/"ubuntu-latest.zip"
            source = db.filename.parent/relative
            contract.need(source.is_file() and not source.is_symlink()
                and source.stat().st_size <= 2_000_000 and digest(source.read_bytes()) == wanted,
                "PRIVATE_ORIGINAL_CUSTODY_DRIFT")
            for parent in source.parents:
                contract.need(not parent.is_symlink(), "PRIVATE_CUSTODY_PARENT_SYMLINK")
            destination = root/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            contract.need(digest(destination.read_bytes()) == wanted, "PRIVATE_CUSTODY_COPY_DRIFT")
        copy_provider_archives(db, root)
        copy_generation_executable(db, root)
        utility = root/"genenv-source"/target/"f139-genenv-source.exe"
        utility.parent.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(binary, utility)
        contract.need(digest(utility.read_bytes()) == expected, "PRIVATE_UTILITY_COPY_DRIFT")
        path = root/"state.sqlite"
        with closing(sqlite3.connect(str(path))) as output:
            db.conn.backup(output)
        private = Database.__new__(Database)
        try:
            Database.__init__(private, path)
            contract.need(private.meta() == before, "PRIVATE_SNAPSHOT_HEAD_DRIFT")
            with SingleOwner(path.with_suffix(".lock")):
                proof = contract.build_proof(private, target, event_id, expected, contract.TOOLCHAIN)
                contract.commit_transition(private, proof, owner_witness=lambda: True)
                reactivate(private, target)
                report = rehearse_typed_generator(private, GitHub(), target)
                after = private.meta().copy()
                contract.need(after["head_seq"] == before["head_seq"]+2, "PRIVATE_EVENT_COUNT_DRIFT")
        finally:
            if getattr(private, "conn", None) is not None:
                private.close()
        with closing(Database.open_readonly(path)) as cold:
            contract.need(cold.meta() == after, "PRIVATE_COLD_HEAD_DRIFT")
        contract.need(db.meta() == before and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
            "ORIGINAL_READONLY_STATE_DRIFT")
        return dict(copied_history_only=True, cold_transition_verified=True,
            native_activation_in_copy_verified=True, actual_typed_generator=report,
            prior_utility_reused_for_development_only=True,
            production_executable_qualified=False, original_owner_mutations=0,
            new_dispatches=0, scientific_first_use=False)



def readonly_publication_diagnostic(db):
    """Bounded original-history evidence only; never resolve or retry a write."""
    contract.need(getattr(db, "_readonly_opened", False) is True
        and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
        "READONLY_ORIGINAL_REQUIRED")
    kinds = ("MODEL_DRAFT_ATTEMPTED", "MODEL_DRAFT_AUTHENTICATED")
    counts = {kind: db.conn.execute("SELECT COUNT(*) FROM events WHERE kind=?",
                                  (kind,)).fetchone()[0] for kind in kinds}
    row = db.conn.execute("SELECT seq,sha,payload FROM events WHERE kind=? ORDER BY seq DESC LIMIT 1",
                          (kinds[0],)).fetchone()
    latest = None
    if row is not None:
        doc = json.loads(row["payload"])
        keys = ("schema", "candidate_identity", "source_after_sha256", "source_sha",
                "parent_commit", "branch", "prior_event_head_sha256",
                "scientific_first_use", "retry_allowed")
        latest = dict(seq=row["seq"], sha=row["sha"],
                      attempt={k:doc[k] for k in keys if k in doc})
    meta = db.meta()
    return dict(schema="forge.f139.v37.readonly-publication-diagnostic.v1",
        source_sha=meta["source_sha"], original_head_seq=meta["head_seq"],
        original_head_sha256=meta["head_hash"], counts=counts, latest_attempt=latest,
        owner_mutations=0, remote_writes=0, retry_authorized=False,
        source_transition_authorized=False, scientific_first_use=False)

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--event-id", type=int)
    parser.add_argument("--genenv-executable", type=Path)
    parser.add_argument("--genenv-toolchain")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--rehearse-copy", action="store_true")
    args = parser.parse_args(argv)
    import re
    contract.need(re.fullmatch(r"[a-f0-9]{40}", args.target) is not None, "TARGET_SHA_INVALID")
    if args.preflight_only:
        from f139.local_controller import Database
        db = Database.open_readonly(args.db)
        try:
            # A consistent read snapshot; never a source/owner mutation lease.
            db.conn.execute("BEGIN")
            from f139.local_controller import GitHub
            from f139.nci04_partial_publication_custody import verify_remote_readback
            verify_remote_readback(GitHub().native_repo_get)
            try:
                report = contract.readonly_snapshot(db)
            except contract.MaintenanceDenied:
                print("F139_V37_READONLY_DIAGNOSTIC=" + canonical(
                    readonly_publication_diagnostic(db)).decode("ascii"), file=sys.stderr)
                raise
            report["candidate_source_sha"] = args.target
            if args.rehearse_copy:
                report["copied_history_rehearsal"] = rehearse_private_history(
                    db, args.target, int(os.environ["GITHUB_RUN_ID"]))
            print(canonical(report).decode("ascii"))
        finally:
            db.conn.rollback()
            db.close()
        return
    if args.rehearse_copy:
        parser.error("private rehearsal is only available with --preflight-only")
    if any(x is None for x in (args.backup, args.event_id, args.genenv_executable, args.genenv_toolchain)):
        parser.error("live transition requires the complete existing owner handoff arguments")
    result = guarded_transition(args.db, args.backup, args.target, args.event_id,
        args.genenv_executable, args.genenv_toolchain, _contract=contract)
    print(canonical(result).decode("ascii"))


if __name__ == "__main__":
    main()
