"""V19 original owner CLI / workflow release gates: no real Windows task or API."""
from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest

from f139.local_controller import Database, cli
from f139.nci04_v19_owner_readonly_preflight import (
    V19PreflightDenied, build_v19_readonly_preflight, FROM_V18,
)


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/f139-v19-original-owner-cutover.yml"


class V19OriginalOwnerReleaseGateTests(unittest.TestCase):
    def test_original_owner_does_not_gain_automatic_v19_transition(self):
        source = inspect.getsource(cli)
        self.assertIn('transition_v19=sub.add_parser("transition-qualified-native-v19")',
                      source)
        self.assertIn('transition_v19.add_argument("--approval",type=Path,required=True)',
                      source)
        self.assertIn('elif args.verb=="transition-qualified-native-v19"', source)
        self.assertIn("verify_v19_readonly_preflight(validator_db,approval)", source)
        self.assertIn("native_original_owner_profile(args.db)", source)
        self.assertIn("legacy_windows_task_disabled()", source)
        self.assertIn("allow_v19=True", source)
        self.assertIn("V19_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED", source)
        self.assertIn("V19_PROTECTED_MAIN_SHA_DRIFT", source)
        self.assertIn('with SingleOwner(args.db.with_suffix(".lock")):', source)
        # A bounded CLI invocation is never silently inserted into tick/loop.
        self.assertNotIn('transition-qualified-native-v19', inspect.getsource(
            __import__("f139.local_controller",fromlist=["run_once"]).run_once))

    def test_real_disposable_original_db_rejects_unheld_owner_mutex(self):
        with tempfile.TemporaryDirectory(prefix="v19-owner-mutex-test-") as td:
            p = Path(td) / "disposable.sqlite"
            db = Database.initialize(p, FROM_V18)
            try:
                before = db.meta().copy()
                with self.assertRaisesRegex(
                    V19PreflightDenied, "ORIGINAL_OWNER_MUTEX_NOT_HELD"):
                    build_v19_readonly_preflight(db, "e"*40, 945672)
                self.assertEqual(db.meta(), before)
                db.verify()
            finally:
                db.close()

    def test_release_job_is_owner_only_exact_source_and_one_attempt(self):
        s = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("on:\n  issue_comment:\n    types: [created]",s)
        self.assertNotIn("workflow_dispatch:",s)
        self.assertNotIn("\n  schedule:",s)
        self.assertIn("github.event.issue.number == 807",s)
        self.assertIn("github.actor == 'spoonman136668-ai'",s)
        self.assertIn("F139-V19-OWNER-CUTOVER ",s)
        self.assertIn("GITHUB_RUN_ATTEMPT -cne '1'",s)
        self.assertIn("RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'",s)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]",s)
        self.assertIn("$old='d8bccc604f8607bf10f9d8bc6aa568d1f98af559'",s)
        self.assertIn("git rev-parse HEAD",s)
        self.assertIn("gh api repos/spoonman136668-ai/FORGE/branches/main",s)
        self.assertIn("F139_V19_IMMUTABLE_RELEASE_REF_NOT_QUALIFIED",s)
        self.assertIn("F139_V19_RELEASE_RULESET_SCOPE_OR_BYPASS_DRIFT",s)
        self.assertIn("F139_V19_ORIGINAL_OWNER_SID_DRIFT",s)
        self.assertIn("Stop-ScheduledTask",s)
        self.assertIn("F139_V19_ORIGINAL_OWNER_NOT_QUIESCENT",s)

    def test_release_backup_is_portable_and_contains_exact_historical_custody(self):
        s = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("$backupDir=Join-Path",s)
        self.assertIn("$backup=Join-Path $backupDir 'state.sqlite'",s)
        self.assertIn("(FIRST_TICKET,FIRST_RUN,FIRST_SHA)",s)
        self.assertIn("(SECOND_TICKET,SECOND_RUN,SECOND_SHA)",s)
        self.assertIn('pathlib.Path("native-negative")',s)
        self.assertIn('"ubuntu-latest.zip"',s)
        self.assertIn("source.is_file() and not source.is_symlink()",s)
        self.assertIn("copied.parent.is_dir() and not copied.parent.is_symlink()",s)
        self.assertIn("source.stat().st_size <= 2_000_000",s)
        self.assertIn("hashlib.sha256(source.read_bytes()).hexdigest()==expected_sha",s)
        self.assertIn("hashlib.sha256(copied.read_bytes()).hexdigest()==expected_sha",s)
        self.assertIn('custody_manifest["state.sqlite"]=',s)
        self.assertIn('"manifest.sha256.json"',s)
        self.assertIn("cold=Database.open_readonly(backup)",s)
        self.assertNotIn("cold=Database(backup)",s)
        self.assertIn("F139_V19_ORIGINAL_COLD_CUSTODY_BUNDLE=PASS",s)
        self.assertEqual(s.count("transition-qualified-native-v19 --approval $approval"),1)

    def test_cold_backed_up_before_sqlite_transaction_and_policy_promotion(self):
        s = WORKFLOW.read_text(encoding="utf-8")
        def pos(x):
            i = s.find(x)
            self.assertNotEqual(i,-1,x)
            return i
        self.assertLess(pos("Disable-ScheduledTask"),pos("db.conn.backup(out)"))
        self.assertLess(pos("db.conn.backup(out)"),pos("cold=Database.open_readonly(backup)"))
        self.assertLess(pos("shutil.copyfile(source,copied)"),pos("db.conn.backup(out)"))
        self.assertLess(pos("cold=Database.open_readonly(backup)"),pos("F139_V19_COLD_BACKUP_RECEIPT_MISSING"))
        self.assertLess(pos("F139_V19_COLD_BACKUP_RECEIPT_MISSING"),
                        pos("transition-qualified-native-v19 --approval $approval"))
        self.assertLess(pos("transition-qualified-native-v19 --approval $approval"),
                        pos("gh api -X PATCH repos/spoonman136668-ai/FORGE/issues/807"))
        self.assertLess(pos("gh api -X PATCH repos/spoonman136668-ai/FORGE/issues/807"),
                        pos("Enable-ScheduledTask -TaskName $name"))
        self.assertIn("Get-FileHash -LiteralPath $backup -Algorithm SHA256",s)
        self.assertIn("F139_V19_PARTIAL_CUSTODY_EXISTING_TASK_HELD_DISABLED",s)
        self.assertIn("$mutationPossible=$true",s)
        self.assertIn("scientific_first_use",s)
        self.assertIn("paid_api_calls",s)
        self.assertEqual(s.count("transition-qualified-native-v19 --approval $approval"),1)
        self.assertEqual(s.count("gh api -X PATCH repos/spoonman136668-ai/FORGE/issues/807"),1)


if __name__ == "__main__":
    unittest.main()
