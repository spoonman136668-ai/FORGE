"""Isolated real-SQLite controls, never original-owner execution evidence."""
from dataclasses import replace
import datetime as dt
import json
import sqlite3
import shutil
import subprocess
import tempfile
import os
from pathlib import Path
import unittest
from unittest import mock

from scripts import f139_i1464_negative_once as recovery
from f139.local_controller import Database, F139Error, SingleOwner
from f139.nci04_owner_ledger import admit_native_issue
import test_nci04_owner_ledger as ledger_fixture
from test_nci04_owner_issue import issue as make_issue


class ExactNegativeCustodyTests(unittest.TestCase):
    def setUp(self):
        fixture = ledger_fixture.LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.db, self.path, native = fixture.db, fixture.path, fixture.native
        self.started = "2026-10-21T10:00:00Z"
        admit_native_issue(self.db, native, self.started)
        self.db.claim(native.ticket, self.started)
        self.db.verify()
        meta = self.db.meta()
        self.scope = recovery.Scope(meta["source_sha"], native.ticket, self.started,
            meta["head_seq"], meta["head_hash"], native.number, native.lane, meta["source_sha"])
        self.backup = self.path.with_name("before.sqlite")
        self.elapsed = 0
        self.origin = dt.datetime.fromisoformat(self.started.replace("Z", "+00:00")) + dt.timedelta(hours=2)
        scope = self.scope
        class API:
            count = 0
            results = [None, None]
            continuity = True
            raw = make_issue()
            def get(self, route):
                if route != f"repos/spoonman136668-ai/FORGE/issues/{scope.issue}":
                    raise AssertionError("unbounded API route")
                return self.raw
            def protected_main(self): return scope.protected_main
            def deployed_release_continuity(self, *args): return self.continuity
            def candidates_for_source(self, *args):
                if args != (scope.ticket, scope.started, scope.source):
                    raise AssertionError("wrong provider scope")
                value = self.results[self.count]
                self.count += 1
                if isinstance(value, Exception): raise value
                return value
        self.api = API()
        # Synthetic native activation witness only; all SQLite, hash-chain,
        # original admission reconstruction and mutex operations are real.
        p = mock.patch("f139.nci04_owner_ledger.verify_native_activation", return_value=True)
        self.activation = p.start()
        self.addCleanup(p.stop)
        self.before = list(self.db.conn.execute("SELECT seq,kind,payload,sha FROM events ORDER BY seq"))

    def pause(self, seconds): self.elapsed += seconds

    def execute(self, **kwargs):
        return recovery.reconcile(self.db, self.api, kwargs.pop("scope", self.scope), self.backup,
            clock=kwargs.pop("clock", lambda: self.origin + dt.timedelta(seconds=self.elapsed)),
            pause=kwargs.pop("pause", self.pause), monotonic=lambda: self.elapsed, **kwargs)

    def assert_unspent(self):
        self.assertEqual(recovery.seal(self.db), (self.scope.sequence, self.scope.head))
        self.assertEqual(recovery.task(self.db, self.scope.ticket)["stage"], "START_RISK")

    def test_one_event_private_backup_and_cold_readback(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            receipt = self.execute()
        self.assertEqual(receipt["original_events_appended"], 1)
        self.assertEqual(receipt["redispatches"], 0)
        self.assertFalse(receipt["scientific_first_use"])
        with sqlite3.connect(self.backup) as backup:
            self.assertEqual(backup.execute("SELECT head_seq FROM meta").fetchone()[0], self.scope.sequence)
        after = list(self.db.conn.execute("SELECT seq,kind,payload,sha FROM events ORDER BY seq"))
        self.assertEqual([tuple(x) for x in after[:-1]], [tuple(x) for x in self.before])
        self.assertEqual(after[-1]["kind"], "ATTEMPT_QUARANTINED")
        reopened = Database(self.path)
        try:
            reopened.verify()
            self.assertEqual(recovery.task(reopened, self.scope.ticket)["stage"], "QUARANTINED")
        finally:
            reopened.close()

    def test_no_mutex_no_write(self):
        with self.assertRaisesRegex(recovery.RecoveryDenied, "LOCK_REQUIRED"):
            self.execute()
        self.assert_unspent()

    def test_identity_and_seal_drift_are_closed(self):
        for scope in (replace(self.scope, source="9" * 40), replace(self.scope, head="9" * 64),
                      replace(self.scope, started="2026-10-21T09:00:00Z"),
                      replace(self.scope, ticket=self.scope.ticket + "-wrong"),
                      replace(self.scope, issue=self.scope.issue + 1)):
            with self.subTest(scope=scope), SingleOwner(self.path.with_suffix(".lock")):
                with self.assertRaises(Exception): self.execute(scope=scope)
                self.assert_unspent()

    def test_present_provider_on_either_view_is_not_quarantined(self):
        for views in ([{"id": 123}, None], [None, {"id": 123}]):
            self.api.count = 0
            self.api.results = views
            with self.subTest(views=views), SingleOwner(self.path.with_suffix(".lock")):
                with self.assertRaisesRegex(recovery.RecoveryDenied, "PROVIDER_RUN_EXISTS"):
                    self.execute()
                self.assert_unspent()

    def test_api_failure_is_not_absence(self):
        self.api.results = [F139Error("F139_GITHUB_API_FAILED")]
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaises(F139Error): self.execute()
        self.assert_unspent()

    def test_observation_gap_cannot_be_skipped(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaisesRegex(recovery.RecoveryDenied, "INTERVAL_REQUIRED"):
                self.execute(pause=lambda _: None)
        self.assert_unspent()

    def test_grace_period_is_required(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaisesRegex(recovery.RecoveryDenied, "GRACE_PERIOD"):
                self.execute(clock=lambda: self.origin - dt.timedelta(hours=2))
        self.assert_unspent()

    def test_remote_body_and_continuity_are_independent_guards(self):
        changed = json.loads(make_issue()["body"])
        changed["paid_model_calls"] = 1
        self.api.raw = {**make_issue(), "body": json.dumps(changed)}
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaisesRegex(recovery.RecoveryDenied, "ISSUE_IDENTITY"):
                self.execute()
        self.assert_unspent()
        self.api.raw = make_issue()
        self.api.continuity = False
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaisesRegex(recovery.RecoveryDenied, "CONTINUITY"):
                self.execute()
        self.assert_unspent()

    def test_inactive_owner_fails(self):
        self.activation.return_value = False
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaisesRegex(recovery.RecoveryDenied, "ACTIVATION"):
                self.execute()
        self.assert_unspent()

    def test_backup_collision_cannot_overwrite_or_commit(self):
        self.backup.write_bytes(b"preserve")
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaises(FileExistsError): self.execute()
        self.assertEqual(self.backup.read_bytes(), b"preserve")
        self.assert_unspent()

    def test_preview_failure_does_not_commit_original(self):
        verify = Database.verify
        def reject_preview(db):
            if db.filename.name.startswith("f139-i1464-preview-"):
                raise recovery.RecoveryDenied("F139_I1464_PREVIEW_REJECTED")
            return verify(db)
        with SingleOwner(self.path.with_suffix(".lock")), mock.patch.object(Database, "verify", reject_preview):
            with self.assertRaisesRegex(recovery.RecoveryDenied, "PREVIEW_REJECTED"):
                self.execute()
        self.assert_unspent()
        self.assertEqual(list(self.path.parent.glob("f139-i1464-preview-*")), [])

    def test_all_private_connections_close_before_return(self):
        connect = sqlite3.connect
        opened = []
        def tracked(*args, **kwargs):
            connection = connect(*args, **kwargs)
            opened.append(connection)
            return connection
        with SingleOwner(self.path.with_suffix(".lock")), mock.patch.object(sqlite3, "connect", tracked):
            self.execute()
        self.assertEqual(len(opened), 3)
        for connection in opened:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")
        self.assertEqual(list(self.path.parent.glob("f139-i1464-preview-*")), [])

    def test_ledger_drift_during_observations_is_not_overwritten(self):
        def drift(seconds):
            self.pause(seconds)
            with self.db.transaction():
                self.db.event("FIXTURE_UNTRUSTED", {"injected_drift": True})
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaisesRegex(recovery.RecoveryDenied, "STATE_CHANGED"):
                self.execute(pause=drift)
        self.assertEqual(recovery.task(self.db, self.scope.ticket)["stage"], "START_RISK")
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind='ATTEMPT_QUARANTINED'").fetchone()[0], 0)

    def test_second_execution_cannot_append_a_second_quarantine(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            self.execute()
            head = recovery.seal(self.db)
            with self.assertRaisesRegex(recovery.RecoveryDenied, "LEDGER_SEAL"):
                self.execute()
            self.assertEqual(recovery.seal(self.db), head)


class RecoveryWorkflowSyntaxTests(unittest.TestCase):
    def powershell(self, source):
        executable = shutil.which("pwsh")
        if executable is None:
            if os.name == "nt": self.fail("Windows PowerShell qualification required")
            self.skipTest("PowerShell parser unavailable on this host")
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "check.ps1"
            script.write_text(source, encoding="utf-8")
            return subprocess.run([executable, "-NoProfile", "-NonInteractive", "-File", str(script)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)

    def job_source(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / ".github/workflows/f139-g54-quarantine-989-ambiguous-start.yml").read_text()
        job = text.split("  quarantine-i1464:\n", 1)[1]
        run = job.split("        run: |\n", 1)[1].split("      - uses:", 1)[0]
        return "\n".join(line[10:] for line in run.splitlines())

    def test_original_host_guard_script_parses_without_execution(self):
        source = self.job_source().replace("'", "''")
        result = self.powershell("$tokens=$null; $parseErrors=$null\n"
            "$null=[System.Management.Automation.Language.Parser]::ParseInput('" + source +
            "',[ref]$tokens,[ref]$parseErrors)\nif($parseErrors.Count){throw 'GUARD_SYNTAX_INVALID'}")
        self.assertEqual(result.returncode, 0, result.stderr[-1000:])

    def test_original_task_argument_parser_preserves_windows_paths(self):
        source = self.job_source()
        function = source[source.index("function Field("):source.index("$root=Field")]
        result = self.powershell("$task=[pscustomobject]@{Actions=@([pscustomobject]@{Arguments='-RepositoryRoot \"C:\\Safe Root\\FORGE\" -Database \"C:\\Safe Root\\state.sqlite\" -PythonExe \"C:\\Python\\python.exe\"'})}\n" + function +
            "\nif((Field 'RepositoryRoot') -cne 'C:\\Safe Root\\FORGE'){throw 'ROOT_PARSE_FAILED'}\n"
            "if((Field 'Database') -cne 'C:\\Safe Root\\state.sqlite'){throw 'DB_PARSE_FAILED'}")
        self.assertEqual(result.returncode, 0, result.stderr[-1000:])


if __name__ == "__main__":
    unittest.main()
