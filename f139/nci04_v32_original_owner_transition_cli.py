"""Guarded source/binary custody handoff; never calls the live research tick."""
from contextlib import closing
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3

from f139.local_controller import Database, GitHub, SingleOwner, native_original_owner_profile, legacy_windows_task_disabled
from f139.nci04_native_contract import canonical, digest
from f139.nci04_model_owner_bridge import inspect_policy, FORGE_REPO, POLICY_ISSUE, owner_history
from f139.nci04_v31_original_owner_transition_cli import git, reactivate
from f139.nci04_v32_source_transition import (
    FROM_V31, ORIGINAL_SEQ, TOOLCHAIN, build_proof, commit_transition, validate_idle, need,
)


def copy_provider_archives(db, destination, *, copy_files=True):
    """Copy every filesystem-dependent V2/V3 custody record without rebasing it.

    The SQLite documents retain their immutable original absolute paths. The
    bundle independently hashes each copied archive against those records,
    so recovery has the exact bytes needed to restore the recorded paths.
    """
    db.verify()
    manifest = {}
    for row in db.conn.execute("SELECT payload FROM events WHERE kind IN "
            "('NATIVE_V_TWO_PROVIDER_CUSTODY','NATIVE_V_THREE_PROVIDER_CUSTODY') ORDER BY seq"):
        doc = json.loads(row["payload"])
        ticket, run = doc["ticket"], doc["run_id"]
        need(type(ticket) is str and re.fullmatch(r"f139-nci04-[a-z0-9-]{1,180}", ticket)
             and type(run) is int and run > 0, "ARCHIVE_IDENTITY")
        folder = Path(doc["evidence_dir"])
        need(folder.is_absolute() and folder.is_dir() and not folder.is_symlink(), "ARCHIVE_FOLDER")
        for parent in folder.parents:
            need(not parent.is_symlink(), "ARCHIVE_PARENT_SYMLINK")
        raw = (folder/"manifest.json").read_bytes()
        need(0 < len(raw) <= 16384 and digest(raw) == doc["evidence_manifest_sha256"], "ARCHIVE_MANIFEST")
        parsed = json.loads(raw)
        need(parsed["ticket"] == ticket and parsed["run_id"] == run
             and set(parsed["sha256"]) == {"ubuntu-latest", "windows-latest"}, "ARCHIVE_SCOPE")
        relative = Path("provider-custody")/ticket/str(run)
        target = destination/relative
        if copy_files:
            target.mkdir(parents=True, exist_ok=False)
        expected = {"manifest.json": doc["evidence_manifest_sha256"], **{
            label+".zip": value for label, value in parsed["sha256"].items()}}
        need({p.name for p in folder.iterdir()} == set(expected), "ARCHIVE_FILE_SET")
        if not copy_files:
            need(target.is_dir() and not target.is_symlink()
                 and {p.name for p in target.iterdir()} == set(expected), "ARCHIVE_BACKUP_FILE_SET")
        for name, wanted in expected.items():
            source = folder/name
            need(source.is_file() and not source.is_symlink() and source.stat().st_size <= 2_000_000,
                 "ARCHIVE_FILE")
            data = source.read_bytes()
            need(digest(data) == wanted, "ARCHIVE_SOURCE_HASH")
            if copy_files:
                (target/name).write_bytes(data)
            need((target/name).is_file() and not (target/name).is_symlink()
                 and digest((target/name).read_bytes()) == wanted, "ARCHIVE_COPY_HASH")
            manifest[(relative/name).as_posix()] = wanted
    return manifest


def rehearse_generator(db, api, target):
    """Actual authenticated copied history -> qualified Go utility -> source.

    This never publishes, submits a queue item or consumes a native attempt.
    """
    from f139 import nci04_model_free_search as search
    from f139.nci04_genenv_owner_backend import build_request, executable_custody, invoke
    from f139.nci04_genenv_source import compile_operator_vectors
    from f139.nci04_autonomy_feed import _decode_content
    history = owner_history(db)
    consumed, asts = search.consumed_source_identities(db, history["consumed_after_hashes"])
    before, _ = _decode_content(api.native_repo_get(
        "repos/spoonman136668-ai/Yggdrasil/contents/"+search.PATH+"?ref="+search.PARENT))
    request = build_request(before, consumed, asts, history["history_sha256"])
    need(request is not None, "NO_FRESH_ORIGINAL_SOURCE_RECIPE")
    binary, expected = executable_custody(db, target)
    raw = invoke(binary, expected, request)
    root = Path(__file__).resolve().parents[1]
    names = ("genenv/genenv.go", "cmd/f139-genenv-source/main.go",
             "f139/nci04_genenv_source.py", "f139/nci04_model_free_search.py",
             "f139/nci04_genenv_owner_backend.py")
    mechanism = b"".join(n.encode()+b"\0"+(root/n).read_bytes() for n in names)
    batch = compile_operator_vectors(raw, result_sha256=digest(raw),
        frozen_sha256=request["frozen_sha256"], history_sha256=request["history_sha256"],
        mechanism=mechanism, mechanism_sha256=digest(mechanism), before=before,
        historical_sha256=frozenset(consumed), historical_ast_sha256=frozenset(asts))
    need(len(batch.candidates) > 0, "NO_GENUINE_SOURCE_OUTPUT")
    return dict(generator_result_sha256=batch.generator_result_sha256,
                fresh_source_sha256=[c.after_sha256 for c, _ in batch.candidates],
                executable_sha256=expected, original_history_sha256=history["history_sha256"],
                model_calls=0, publications=0, native_dispatches=0)


def rehearse_typed_generator(db, api, target):
    """Copied original history -> real existing Promptbreeder -> new source."""
    from f139 import nci04_model_free_search as search
    from f139.nci04_genenv_owner_backend import executable_custody, generate_typed_batch
    from f139.nci04_autonomy_feed import _decode_content
    history = owner_history(db)
    consumed, asts = search.consumed_source_identities(db,history["consumed_after_hashes"])
    before, _ = _decode_content(api.native_repo_get(
        "repos/spoonman136668-ai/Yggdrasil/contents/"+search.PATH+"?ref="+search.PARENT))
    binary, expected = executable_custody(db,target)
    batch = generate_typed_batch(db,before=before,consumed=consumed,historical_asts=asts,
        history_sha256=history["history_sha256"],source_sha=target,binary=binary,binary_sha=expected)
    need(batch is not None and len(batch.candidates)>0,"NO_GENUINE_TYPED_SOURCE_OUTPUT")
    return dict(generator_result_sha256=batch.generator_result_sha256,
        fresh_source_sha256=[c.after_sha256 for c,_ in batch.candidates],
        executable_sha256=expected,original_history_sha256=history["history_sha256"],
        frozen_sha256=batch.frozen_sha256,source_bindings_sha256=batch.bindings_sha256,
        generation_mechanism_sha256=batch.mechanism_sha256,
        model_calls=0,publications=0,native_dispatches=0)


def copy_generation_executable(db, destination, *, copy_files=True):
    """Back up the previously released utility as well as provider custody."""
    from f139.nci04_genenv_owner_backend import executable_custody
    source_sha = db.meta()["source_sha"]
    binary, expected = executable_custody(db,source_sha)
    relative = Path("prior-generation-custody")/source_sha/binary.name
    target = destination/relative
    if copy_files:
        target.parent.mkdir(parents=True,exist_ok=False)
        shutil.copyfile(binary,target)
    need(target.is_file() and not target.is_symlink()
         and 0 < target.stat().st_size <= 16_000_000
         and digest(target.read_bytes()) == expected,"PRIOR_GENERATOR_BACKUP_HASH")
    return {relative.as_posix():expected}


def guarded_transition(path, backup, target, event_id, binary, toolchain, *, _contract=None):
    # Reuse the qualified original-owner handoff, not another controller.
    from f139 import nci04_v32_source_transition as v32
    from f139 import nci04_v33_source_transition as v33
    from f139 import nci04_v34_source_transition as v34
    from f139 import nci04_v35_source_transition as v35
    from f139 import nci04_v36_source_transition as v36
    globals()["need"](_contract is None or _contract is v33 or _contract is v34 or _contract is v35 or _contract is v36,
                      "UNKNOWN_SOURCE_CONTRACT")
    contract = v32 if _contract is None else _contract
    FROM_V31 = (v32.FROM_V31 if contract is v32 else
                v33.FROM_V32 if contract is v33 else
                v34.FROM_V33 if contract is v34 else
                v35.FROM_V34 if contract is v35 else v36.FROM_V35)
    ORIGINAL_SEQ, TOOLCHAIN = getattr(contract, "ORIGINAL_SEQ", None), contract.TOOLCHAIN
    build_proof, commit_transition = contract.build_proof, contract.commit_transition
    validate_idle, need = contract.validate_idle, contract.need
    rehearse_generator = globals()["rehearse_generator"] if _contract is None else rehearse_typed_generator
    version = "V32" if contract is v32 else "V33" if contract is v33 else "V34" if contract is v34 else "V35" if contract is v35 else "V36"
    need(os.name == "nt" and re.fullmatch(r"[a-f0-9]{40}", target)
         and type(event_id) is int and event_id > 0 and toolchain == TOOLCHAIN,
         "WINDOWS_EXACT_TARGET_AND_TOOLCHAIN_REQUIRED")
    root = Path(__file__).resolve().parents[1]
    need(git(root, "rev-parse", "HEAD") == target and
         not git(root, "status", "--porcelain", "--untracked-files=all"), "EXACT_CLEAN_CHECKOUT_REQUIRED")
    need(path.is_absolute() and backup.is_file() and not backup.is_symlink()
         and backup.resolve() != path.resolve(), "ISOLATED_COLD_BACKUP_REQUIRED")
    expected_binary = path.parent / "genenv-source" / target / "f139-genenv-source.exe"
    need(binary.is_absolute() and binary == expected_binary and binary.is_file()
         and not binary.is_symlink() and 0 < binary.stat().st_size <= 16_000_000,
         "EXACT_SOURCE_UTILITY_REQUIRED")
    for parent in (binary.parent, binary.parent.parent):
        need(not parent.is_symlink(), "UTILITY_PARENT_SYMLINK")
    binary_sha = digest(binary.read_bytes())
    native_original_owner_profile(path)
    legacy_windows_task_disabled()
    key = os.environ.get("F139_WORKER_HMAC_KEY", "")
    need(32 <= len(key) <= 4096, "ORIGINAL_DPAPI_KEY_REQUIRED")
    api = GitHub()
    protected = api.protected_main()
    compare = api.native_repo_get("repos/"+FORGE_REPO+"/compare/"+target+"..."+protected)
    need(compare.get("status") in ("ahead", "identical") and compare.get("behind_by") == 0
         and compare.get("merge_base_commit", {}).get("sha") == target, "QUALIFIED_RELEASE_NOT_IN_MAIN")
    policy = api.native_repo_get("repos/"+FORGE_REPO+"/issues/"+str(POLICY_ISSUE))
    need(inspect_policy(policy, FROM_V31)["enabled"] is False, "ORIGINAL_POLICY_NOT_PAUSED")
    release = api.native_repo_get("repos/"+FORGE_REPO+"/branches/f139-owner-release-"+target)
    need(release.get("protected") is True and release.get("commit", {}).get("sha") == target,
         "IMMUTABLE_RELEASE_REF_REQUIRED")
    api.legacy_dispatchers_disabled()
    db = Database(path)
    try:
        with SingleOwner(path.with_suffix(".lock")):
            validate_idle(db)
            before = db.meta().copy()
            if contract in (v34, v35, v36):
                ORIGINAL_SEQ = before["head_seq"]
            copy_provider_archives(db, backup.parent, copy_files=False)
            if version in ("V33", "V34", "V35", "V36"):
                copy_generation_executable(db,backup.parent,copy_files=False)
            rehearsal = backup.with_name(version.lower()+"-source-and-executable-rehearsal.sqlite")
            need(not rehearsal.exists(), "REHEARSAL_COLLISION")
            cold = Database.open_readonly(backup)
            try:
                cold.verify()
                need(cold.meta() == before, "BACKUP_HEAD_DRIFT")
                with closing(sqlite3.connect(str(rehearsal))) as destination:
                    cold.conn.backup(destination)
            finally:
                cold.close()
            copied_binary = backup.parent / "genenv-source" / target / binary.name
            copied_binary.parent.mkdir(parents=True, exist_ok=False)
            shutil.copyfile(binary, copied_binary)
            need(digest(copied_binary.read_bytes()) == binary_sha, "COPIED_UTILITY_DRIFT")
            copy = Database(rehearsal)
            try:
                with SingleOwner(rehearsal.with_suffix(".lock")):
                    proof = build_proof(copy, target, event_id, binary_sha, toolchain)
                    commit_transition(copy, proof, owner_witness=lambda: True)
                    reactivate(copy, target)
                    report = rehearse_generator(copy, api, target)
                    expected_meta = copy.meta().copy()
            finally:
                copy.close()
            reopened = Database.open_readonly(rehearsal)
            try:
                reopened.verify()
                need(reopened.meta() == expected_meta, "REHEARSAL_COLD_HEAD_DRIFT")
            finally:
                reopened.close()
            print("F139_"+version+"_COPIED_ORIGINAL_HISTORY_AND_ACTUAL_SOURCE_COMPILER=PASS")
            print("F139_"+version+"_REHEARSAL="+canonical(report).decode("ascii"))
            need(db.meta() == before and native_original_owner_profile(path), "ORIGINAL_OWNER_MOVED")
            need(api.protected_main() == protected and api.native_repo_get(
                "repos/"+FORGE_REPO+"/issues/"+str(POLICY_ISSUE)).get("body") == policy.get("body"),
                "MAIN_OR_POLICY_MOVED_DURING_REHEARSAL")
            need(digest(binary.read_bytes()) == binary_sha, "ORIGINAL_UTILITY_CHANGED")
            proof = build_proof(db, target, event_id, binary_sha, toolchain)
            result = commit_transition(db, proof, owner_witness=lambda: native_original_owner_profile(path))
            reactivate(db, target)
            need(db.meta() == expected_meta and db.meta()["head_seq"] == ORIGINAL_SEQ+2,
                 "ORIGINAL_DIVERGED_FROM_AUTHENTIC_REHEARSAL")
            from f139.nci04_genenv_owner_backend import executable_custody
            need(executable_custody(db, target)[1] == binary_sha, "ORIGINAL_EXECUTABLE_NOT_CUSTODIED")
            return {**result, "activation_event_seq": db.meta()["head_seq"],
                    "event_head_sha256": db.meta()["head_hash"], "source_rehearsal": report,
                    "native_reactivated": True, "new_dispatches": 0, "paid_model_calls": 0}
    finally:
        db.close()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--event-id", type=int, required=True)
    parser.add_argument("--genenv-executable", type=Path, required=True)
    parser.add_argument("--genenv-toolchain", required=True)
    args = parser.parse_args(argv)
    print(canonical(guarded_transition(args.db, args.backup, args.target, args.event_id,
        args.genenv_executable, args.genenv_toolchain)).decode("ascii"))


if __name__ == "__main__":
    main()
