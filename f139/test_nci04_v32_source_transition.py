"""Cold source/binary handoff controls; no live owner or release authority."""
import ast
from contextlib import closing
import fnmatch
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from f139 import nci04_v32_source_transition as route
from f139.local_controller import Database, SingleOwner, store_evidence, v2_owner_terminal_release_guard
from f139.nci04_v32_original_owner_transition_cli import copy_provider_archives

ROOT = Path(__file__).resolve().parents[1]


def proof():
    return dict(schema=route.SCHEMA, from_source_sha=route.FROM_V31, to_source_sha="f"*40,
        owner_event_id=41400000000, prior_event_head_sha256=route.ORIGINAL_HEAD,
        verified_historical_tasks=33, custodied_negative_tasks=18,
        custodied_negative_tickets=["negative-%d"%i for i in range(18)],
        terminal_tasks_sha256="a"*64, history_sha256="b"*64, v31_transition_sha256="c"*64,
        genenv_executable_sha256="d"*64, genenv_toolchain=route.TOOLCHAIN,
        new_dispatches=0, scientific_first_use=False, v2_receipt_authorized=False)


class V32ColdBoundaryTests(unittest.TestCase):
    def test_real_missing_original_history_cannot_change_source(self):
        with tempfile.TemporaryDirectory() as temp, closing(Database.initialize(
                Path(temp)/"fixture.sqlite", route.FROM_V31)) as db:
            db.enable(legacy_suspended=True)
            before = db.meta().copy()
            with SingleOwner(db.filename.with_suffix(".lock")):
                with self.assertRaises(route.MaintenanceDenied):
                    route.commit_transition(db, proof(), owner_witness=lambda: True)
            self.assertEqual(db.meta(), before)
            db.verify()

    def test_cold_event_rejects_binary_toolchain_history_authority_and_replay_drift(self):
        doc = proof()
        state = {k:doc[k] for k in ("verified_historical_tasks", "custodied_negative_tasks",
            "custodied_negative_tickets", "terminal_tasks_sha256", "history_sha256", "v31_transition_sha256")}
        previous = [dict(schema="forge.f139.source-transition.v26", from_source_sha="e"*40,
                         to_source_sha=route.FROM_V31)]
        row = dict(seq=402, prior_sha=route.ORIGINAL_HEAD)
        with patch.object(route, "snapshot", return_value=state):
            route.verify_cold_event(None, row, doc, previous)
            for change in (dict(genenv_executable_sha256="not-a-pin"), dict(genenv_toolchain="go1.24"),
                           dict(history_sha256="e"*64), dict(scientific_first_use=True),
                           dict(new_dispatches=1), dict(v2_receipt_authorized=True),
                           dict(to_source_sha=route.FROM_V31), dict(owner_event_id=0), dict(extra="denied")):
                with self.subTest(change=change), self.assertRaises(route.MaintenanceDenied):
                    route.verify_cold_event(None, row, {**doc, **change}, previous)
            with self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(None, row, doc, previous+[doc])
            with self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(None, {**row,"prior_sha":"a"*64}, doc, previous)

    def test_failed_post_transition_verification_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp, closing(Database.initialize(
                Path(temp)/"fixture.sqlite", route.FROM_V31)) as db:
            db.enable(legacy_suspended=True)
            before = db.meta().copy()
            with SingleOwner(db.filename.with_suffix(".lock")), patch.object(
                    route, "build_proof", return_value=proof()), patch.object(
                    db, "verify", side_effect=ValueError("post-transition failure")):
                with self.assertRaisesRegex(ValueError, "post-transition failure"):
                    route.commit_transition(db, proof(), owner_witness=lambda: True)
            self.assertEqual(db.meta(), before)
            db.verify()

    def test_owner_revocation_and_stale_binary_proof_cannot_commit(self):
        with tempfile.TemporaryDirectory() as temp, closing(Database.initialize(
                Path(temp)/"fixture.sqlite", route.FROM_V31)) as db:
            before = db.meta().copy()
            with SingleOwner(db.filename.with_suffix(".lock")), patch.object(
                    route, "build_proof", return_value=proof()):
                for witness in (Mock(return_value=False), Mock(side_effect=[True,False])):
                    with self.assertRaises(route.MaintenanceDenied):
                        route.commit_transition(db, proof(), owner_witness=witness)
                with self.assertRaisesRegex(route.MaintenanceDenied,"APPROVAL_OR_LEDGER_DRIFT"):
                    route.commit_transition(db, {**proof(),"genenv_executable_sha256":"e"*64},
                                            owner_witness=lambda:True)
            self.assertEqual(db.meta(), before)

    def test_modern_v2_guard_accepts_only_the_explicitly_verified_new_schema(self):
        with tempfile.TemporaryDirectory() as temp, closing(Database.initialize(
                Path(temp)/"fixture.sqlite", "f"*40)) as db:
            db.enable(legacy_suspended=True)
            db.event("SOURCE_TRANSITION_ADMITTED", dict(schema=route.SCHEMA,
                to_source_sha="f"*40, v2_receipt_authorized=False))
            with patch.object(db,"verify"), patch("f139.local_controller.g54_original_canonical"), \
                    patch("f139.nci04_g49_prepost_negative.verify_g49_custody", return_value=True), \
                    patch("f139.nci04_owner_ledger.verify_native_activation", return_value=True):
                self.assertTrue(v2_owner_terminal_release_guard("f"*40,db))
                db.event("SOURCE_TRANSITION_ADMITTED", dict(schema="forge.f139.source-transition.v28",
                         to_source_sha="f"*40, v2_receipt_authorized=False))
                self.assertFalse(v2_owner_terminal_release_guard("f"*40,db))

    def test_snapshot_preserves_old_terminal_tasks_and_spent_requests_across_future_work(self):
        from f139.nci04_negative_owner_store import TICKET as FIRST
        from f139.nci04_split_negative_owner_store import TICKET as SECOND
        from f139.nci04_g49_prepost_negative import TICKET as PREPOST
        negatives = [FIRST,SECOND,PREPOST,"g54"]+["failed-%d"%i for i in range(14)]
        previous = [dict(schema="forge.f139.source-transition.v26",from_source_sha="d"*40,
                         to_source_sha=route.FROM_V31)]
        with tempfile.TemporaryDirectory() as temp, closing(Database.initialize(
                Path(temp)/"fixture.sqlite",route.FROM_V31)) as db:
            db.enable(legacy_suspended=True)
            for i,ticket in enumerate(negatives+["good-%d"%i for i in range(33)]):
                db.conn.execute("INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) VALUES(?,?,?,?,?)",
                    (ticket,"Yggdrasil",route.FROM_V31,"QUARANTINED" if i<18 else "VERIFIED","a"*64))
            db.event("SOURCE_TRANSITION_ADMITTED",previous[-1])
            for kind,count in (("FREE_REASONER_ATTEMPTED",8),("MODEL_DRAFT_ATTEMPTED",7),
                               ("MODEL_DRAFT_AUTHENTICATED",7)):
                for i in range(count):
                    db.event(kind,dict(synthetic=i))
            while db.meta()["head_seq"] < 401:
                db.event("UNTRUSTED_TEST_FIXTURE",dict(synthetic=db.meta()["head_seq"]))
            with patch.object(route,"ORIGINAL_HEAD",db.meta()["head_hash"]), patch.object(
                    db,"verified_native_provider_failures",return_value={t:None for t in negatives[4:]}), \
                    patch.object(route,"g54_original_canonical",return_value={"ticket":"g54"}):
                first = route.snapshot(db,dict(seq=402),previous)
                self.assertEqual(first["verified_historical_tasks"],33)
                self.assertEqual(first["custodied_negative_tasks"],18)
                db.conn.execute("INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) VALUES(?,?,?,?,?)",
                    ("future","Wingless","f"*40,"READY","a"*64))
                self.assertEqual(route.snapshot(db,dict(seq=402),previous),first)
                db.conn.execute("UPDATE tasks SET stage='READY' WHERE ticket='good-0'")
                with self.assertRaisesRegex(route.MaintenanceDenied,"NOT_TERMINAL"):
                    route.snapshot(db,dict(seq=402),previous)


class ProviderArchiveCopyTests(unittest.TestCase):
    def test_independent_backup_archive_hashes_reject_tamper_without_changing_originals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ticket = "f139-nci04-fixture"
            archives = {"ubuntu-latest":b"linux fixture", "windows-latest":b"windows fixture"}
            directory, manifest = store_evidence(root/"original", ticket, 1, archives)
            with closing(sqlite3.connect(":memory:")) as con:
                con.row_factory = sqlite3.Row
                con.execute("CREATE TABLE events(seq INTEGER,kind TEXT,payload TEXT)")
                con.execute("INSERT INTO events VALUES(1,?,?)", ("NATIVE_V_TWO_PROVIDER_CUSTODY",
                    json.dumps(dict(ticket=ticket,run_id=1,evidence_dir=directory,
                                    evidence_manifest_sha256=manifest))))
                db = SimpleNamespace(conn=con, verify=Mock())
                destination = root/"backup"
                destination.mkdir()
                copied = copy_provider_archives(db,destination)
                self.assertEqual(len(copied),3)
                self.assertEqual(copy_provider_archives(db,destination,copy_files=False),copied)
                target = destination/"provider-custody"/ticket/"1"/"ubuntu-latest.zip"
                target.write_bytes(b"tampered")
                with self.assertRaisesRegex(route.MaintenanceDenied,"ARCHIVE_COPY_HASH"):
                    copy_provider_archives(db,destination,copy_files=False)
                self.assertEqual((Path(directory)/"ubuntu-latest.zip").read_bytes(),archives["ubuntu-latest"])


class V32InstallerTests(unittest.TestCase):
    def test_only_v32_receives_new_release_pushes_and_old_v31_is_immutable(self):
        routes = []
        for version in range(27,33):
            text = (ROOT/f".github/workflows/f139-v{version}-original-owner-release.yml").read_text()
            patterns = ast.literal_eval(re.findall(r"^    branches: (\[.*\])$",text,re.M)[0])
            if any(fnmatch.fnmatchcase("f139-owner-release-"+"f"*40,p) for p in patterns):
                routes.append(version)
        self.assertEqual(routes,[32])
        old = (ROOT/".github/workflows/f139-v31-original-owner-release.yml").read_text()
        self.assertIn("branches: ['f139-owner-release-"+route.FROM_V31+"']",old)

    def test_release_retains_guards_and_rehearses_before_original_mutation(self):
        source = (ROOT/".github/workflows/f139-v32-original-owner-release.yml").read_text()
        for token in ("$event.before -cne ('0'*40)", "$env:GITHUB_RUN_ATTEMPT -cne '1'",
                      "EXACT_QUALIFICATION_REQUIRED", "FINAL_LINUX_WINDOWS_RECEIPTS_REQUIRED",
                      "bypass_actors", "ZeroFreeBSTR($ptr)", "Remove-Item Env:F139_WORKER_HMAC_KEY",
                      "go build -trimpath -buildvcs=false", "copy_provider_archives(db, backup.parent)",
                      "POSTMUTATION_EXISTING_TASK_DISABLED_AND_QUIESCENT"):
            self.assertIn(token,source)
        cli = (ROOT/"f139/nci04_v32_original_owner_transition_cli.py").read_text()
        self.assertLess(cli.index("report = rehearse_generator(copy"),cli.index("result = commit_transition(db"))
        self.assertNotIn("run_once(",cli)
        self.assertNotIn(".dispatch",cli)
        self.assertNotIn("schedule:",source)
        self.assertNotIn("issue_comment:",source)

    def test_windows_powershell_inert_parse(self):
        if os.name != "nt":
            self.skipTest("Windows PowerShell syntax parser")
        executable = shutil.which("powershell.exe")
        self.assertIsNotNone(executable)
        text = (ROOT/".github/workflows/f139-v32-original-owner-release.yml").read_text()
        for block in text.split("        run: |\n")[1:]:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp)/"inert-parse.ps1"
                path.write_text("\n".join(line[10:] if line.startswith(" "*10) else line
                                          for line in block.splitlines()),encoding="utf-8")
                parsed = subprocess.run([executable,"-NoProfile","-NonInteractive","-Command",
                    "$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('"
                    +str(path).replace("'","''")+"',[ref]$t,[ref]$e);if($e.Count){$e|%{$_.Message};exit 1}"],
                    capture_output=True,check=False)
                self.assertEqual(parsed.returncode,0,parsed.stdout.decode(errors="replace"))
